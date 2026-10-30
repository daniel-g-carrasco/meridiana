"""One window for every start: a second start hands its project to the Meridiana already running, which comes to the
front, and ends (R07; the same module as Quotario's, the template's guide `docs/dal-template-gtk.md`, section 4
«Istanza unica»).

The channel is a QLocalServer: a named pipe on Windows, a socket on Linux. Its name carries the app id and the user,
because a named pipe is seen from every session of the computer: without the user, two people on the same PC would
hand each other their files. On Linux the socket goes in XDG_RUNTIME_DIR (only the user can enter it), and in the
Flatpak in $XDG_RUNTIME_DIR/app/$FLATPAK_ID, which the program's instances share; /tmp would be the sandbox's own.

The message is one line of JSON, `{"files": [...], "token": "..."}`, with absolute paths; the token is the Wayland
activation token the desktop gave the second start, if any. No window here: the module only carries the message."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from . import log

CONNECT_MS = 500            # a running program answers at once; a channel left by a crash refuses at once
WRITE_MS = 2000
LARGEST_MESSAGE = 64 * 1024  # the paths of a few hundred files; anything bigger is not from Meridiana


def channel_name(app_id: str, user: str | None = None, environ=None) -> str:
    """The channel's name, or on Linux the socket's whole path. The user's name goes in as a short hash: any
    character is allowed in it, none in a pipe's name."""
    environ = os.environ if environ is None else environ
    if user is None:
        try:
            user = getpass.getuser()
        except (KeyError, OSError):     # no user name in the environment nor in the system's records
            user = str(os.getuid()) if hasattr(os, "getuid") else "user"
    tag = hashlib.sha256(user.encode("utf-8")).hexdigest()[:12]
    name = f"{re.sub(r'[^A-Za-z0-9_.-]', '_', app_id)}-{tag}"
    if sys.platform == "win32":
        return name
    runtime = environ.get("XDG_RUNTIME_DIR", "")
    if runtime and os.path.isabs(runtime):
        flatpak = environ.get("FLATPAK_ID", "")
        folder = Path(runtime) / "app" / flatpak if flatpak else Path(runtime)
        return str(folder / f"{name}.socket")
    return name                     # Qt puts it in its temporary folder


def allow_foreground() -> None:
    """Windows lets the program already running come to the front only if the process that the person started
    allows it (otherwise its button only flashes in the taskbar)."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        allow = ctypes.windll.user32.AllowSetForegroundWindow
        allow.argtypes = [ctypes.c_uint32]
        allow.restype = ctypes.c_int
        allow(0xFFFFFFFF)           # ASFW_ANY
    except (AttributeError, OSError) as error:
        log.complain("allow the running window to the front", error)


def encode(files: list[str], token: str = "") -> bytes:
    return (json.dumps({"files": files, "token": token}) + "\n").encode("utf-8")


def decode(data: bytes) -> tuple[list[str], str]:
    """The files and the token of a message; ValueError for what is not a message of Meridiana."""
    message = json.loads(data.decode("utf-8"))
    files = message.get("files") if isinstance(message, dict) else None
    token = message.get("token", "") if isinstance(message, dict) else ""
    if not isinstance(files, list) or not all(isinstance(name, str) for name in files) or not isinstance(token, str):
        raise ValueError("not a message of Meridiana")
    return files, token


def hand_over(name: str, files: list[str], token: str = "") -> bool:
    """Sends the files to the program already running on the channel `name`. True if it took them: then this start
    has nothing more to do."""
    socket = QLocalSocket()
    socket.connectToServer(name)
    if not socket.waitForConnected(CONNECT_MS):
        return False
    allow_foreground()
    socket.write(encode(files, token))
    delivered = socket.waitForBytesWritten(WRITE_MS)
    socket.disconnectFromServer()
    if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
        socket.waitForDisconnected(WRITE_MS)
    return delivered


class Receiver(QObject):
    """The first start's side: listens on the channel and says what the later starts send."""

    received = Signal(list, str)        # absolute paths, activation token

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._connection)
        self._buffers: dict[QLocalSocket, bytearray] = {}

    def listen(self) -> bool:
        """Takes the channel. A socket left by a program that stopped without closing it is removed first."""
        if sys.platform != "win32" and os.path.isabs(self.name):
            Path(self.name).parent.mkdir(parents=True, exist_ok=True)
        QLocalServer.removeServer(self.name)
        if self.server.listen(self.name):
            return True
        log.complain("listen for later starts", OSError(self.server.errorString()))
        return False

    def _connection(self) -> None:
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self._buffers[socket] = bytearray()
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(lambda s=socket: self._done(s))

    def _read(self, socket: QLocalSocket) -> None:
        buffer = self._buffers.get(socket)
        if buffer is None:
            return
        buffer += bytes(socket.readAll())
        if len(buffer) > LARGEST_MESSAGE:
            log.complain("a later start", ValueError(f"message of more than {LARGEST_MESSAGE} bytes, dropped"))
            self._buffers.pop(socket, None)
            socket.abort()
            return
        if b"\n" in buffer:
            line = bytes(buffer).split(b"\n", 1)[0]
            self._buffers.pop(socket, None)
            socket.disconnectFromServer()
            try:
                files, token = decode(line)
            except ValueError as error:          # json.JSONDecodeError and UnicodeDecodeError are ValueErrors
                log.complain("a later start", error)
                return
            self.received.emit(files, token)

    def _done(self, socket: QLocalSocket) -> None:
        self._buffers.pop(socket, None)
        socket.deleteLater()
