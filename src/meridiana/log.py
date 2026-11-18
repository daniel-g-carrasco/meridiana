"""Unexpected failures said out loud, and kept. What goes wrong in a thread, in a slot or in the main loop
reaches stderr (the console, the journal) with its traceback, and, once `setup` has given a file, the log in the
state folder, so that a build without a console loses nothing. Never `except Exception: pass`: a failure nobody
hears of is a bug nobody can fix (study 18, G 3.3: no excepthook and no file meant every error in a slot was
invisible)."""

from __future__ import annotations

import sys
import threading
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from . import SLUG

LOG_KEEP = 1 << 20              # bytes: beyond this the file is rotated once, to <name>.1

_file: Path | None = None
_tell: Callable[[str], None] | None = None


def setup(path: Path | None) -> None:
    """The file the failures are appended to (None: stderr only), rotated when it grows past LOG_KEEP."""
    global _file
    _file = Path(path) if path else None
    if _file is None:
        return
    try:
        _file.parent.mkdir(parents=True, exist_ok=True)
        if _file.exists() and _file.stat().st_size > LOG_KEEP:
            _file.replace(_file.with_name(_file.name + ".1"))
    except OSError as error:
        print(f"{SLUG}: log: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        _file = None


def file() -> Path | None:
    return _file


def _write(text: str) -> None:
    print(text, file=sys.stderr, flush=True)
    if _file is None:
        return
    try:
        with _file.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat(timespec='seconds')} {text}\n")
    except OSError:
        pass                    # the log itself has nowhere else to complain


def complain(where: str, error: BaseException) -> None:
    detail = "".join(traceback.format_exception(error)).rstrip()
    _write(f"{SLUG}: {where}: {type(error).__name__}: {error}\n{detail}")


def install_excepthook(tell: Callable[[str], None] | None = None) -> None:
    """Every exception nobody caught (in a slot, a timer, a thread) is logged and, with a teller, said to the
    designer in one line. PySide6 calls sys.excepthook for the exceptions of its slots (checked on 6.12,
    23/10/2026)."""
    global _tell
    _tell = tell

    def hook(kind, error, tb):
        complain("unhandled", error.with_traceback(tb) if tb is not None else error)
        if _tell is not None:
            try:
                _tell(f"{kind.__name__}: {error}")
            except Exception as again:          # noqa: BLE001  the teller failing must not hide the error
                _write(f"{SLUG}: telling: {type(again).__name__}: {again}")

    def thread_hook(args):
        hook(args.exc_type, args.exc_value, args.exc_traceback)

    sys.excepthook = hook
    threading.excepthook = thread_hook


def tell_with(tell: Callable[[str], None] | None) -> None:
    """The window gives itself as the teller once it exists."""
    global _tell
    _tell = tell
