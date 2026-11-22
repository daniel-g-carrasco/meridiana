"""One window for every start, in the Quick (R07, r30-struttura A1): a second start hands its project to the Meridiana
already running and ends; the window that is open takes it as File > Open does, after asking about the unsaved
changes. Tried with real processes on temporary profiles: the channel is the profile's (startup.instance_channel), so
a test never reaches the window the person has open. In the place of tests/finestra/test_second_start.py, which drove
the Widgets window.

    python -m unittest quick.sistema.test_second_start
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

from PySide6.QtCore import Qt

from _fixtures import capannone
from meridiana import PACKAGE_DIR
from meridiana import APP_ID
from meridiana.gui import single_instance, startup
from meridiana.core.model import model
from quick.gestures import pump

SRC = str(PACKAGE_DIR.parent)          # the folder the package is in (src/)

RECEIVER = """
import json, sys
from PySide6.QtCore import QCoreApplication, QTimer
from meridiana.gui.single_instance import Receiver
app = QCoreApplication([])
receiver = Receiver(sys.argv[1])
receiver.received.connect(lambda files, token: (print(json.dumps([files, token]), flush=True), app.quit()))
if not receiver.listen():
    sys.exit(3)
print("ready", flush=True)
QTimer.singleShot(20000, app.quit)
app.exec()
"""
SENDER = """
import sys
from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalSocket
from meridiana.gui.single_instance import CONNECT_MS, hand_over
app = QCoreApplication([])
if hand_over(sys.argv[1], sys.argv[2:], "a-token"):
    sys.exit(0)
# said for whoever reads a failure (seen once in four runs on 10/11/2026, never again in 440 hand-overs): is anybody there now?
probe = QLocalSocket()
probe.connectToServer(sys.argv[1])
print("not handed over; a connection now:", probe.waitForConnected(CONNECT_MS), probe.error(), file=sys.stderr)
sys.exit(1)
"""


def unique_channel() -> str:
    name = f"meridiana-test-{uuid.uuid4().hex[:12]}"
    if sys.platform == "win32":
        return name
    return str(Path(tempfile.gettempdir()) / f"{name}.socket")


def end(process) -> None:
    """A start ended with the processes it started (the computation's, the tasks'): on Windows a kill leaves them."""
    if process.poll() is None and sys.platform == "win32":
        stopped = subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                                 capture_output=True, text=True, errors="replace", timeout=30, check=False)
        if stopped.returncode and process.poll() is None:
            raise RuntimeError(f"Cannot stop test process tree {process.pid}: {stopped.stdout} {stopped.stderr}")
    elif process.poll() is None:
        process.kill()
    process.wait(30)


def environment(**extra: str) -> dict:
    env = dict(os.environ, PYTHONPATH=SRC, QT_QPA_PLATFORM="offscreen", QSG_RENDER_LOOP="basic",
               MERIDIANA_PRELOAD="0", **extra)
    for name in ("MERIDIANA_TEST_SCREEN", "MERIDIANA_INSTANCE", "MERIDIANA_SCREENSHOT"):
        if name not in extra:
            env.pop(name, None)
    return env


FLATPAK = {"XDG_RUNTIME_DIR": "/run/user/1000", "FLATPAK_ID": APP_ID}


def long_profile(scratch: str, size: int = 150) -> Path:
    """A profile folder whose path is `size` characters long."""
    return Path(scratch) / ("p" * max(1, size - len(scratch) - 1))


class Channel(unittest.TestCase):
    def test_the_name_carries_the_app_id_and_the_user(self):
        for platform in ("win32", "linux"):
            with self.subTest(platform=platform):
                mine = single_instance.channel_name(APP_ID, "first.person", environ={}, platform=platform)
                theirs = single_instance.channel_name(APP_ID, "second.person", environ={}, platform=platform)
                another_app = single_instance.channel_name("org.example.other", "first.person", environ={},
                                                           platform=platform)
                self.assertNotEqual(mine, theirs)
                self.assertNotEqual(mine, another_app)
                self.assertNotIn("person", mine)
                self.assertIn("meridiana", mine)
        # Windows: the pipe's name as before r34, so a start reaches a window of the version before
        self.assertIn(APP_ID, single_instance.channel_name(APP_ID, "u", environ={}, platform="win32"))

    def test_the_socket_stays_within_a_unix_sockets_limit_whatever_the_profile(self):
        # D1 of the Linux round of r32 (dc371024): in the Flatpak, with --profile, the socket's path was 123
        # characters, more than the 107 a Unix socket takes: «QLocalServer::listen: Name error», two windows
        with tempfile.TemporaryDirectory() as scratch:
            for size in (20, 150, 400):
                with self.subTest(size=size):
                    name = startup.instance_channel(FLATPAK, profile=long_profile(scratch, size), platform="linux")
                    self.assertLessEqual(len(name.encode("utf-8")), single_instance.SOCKET_PATH_MAX, name)
                    self.assertTrue(name.startswith(f"/run/user/1000/app/{APP_ID}/"), name)
            self.assertLessEqual(len(startup.instance_channel(FLATPAK, platform="linux").encode("utf-8")),
                                 single_instance.SOCKET_PATH_MAX)
            # the same profile written in another way is the same channel; another profile is another
            one = startup.instance_channel(FLATPAK, profile=long_profile(scratch), platform="linux")
            again = startup.instance_channel(FLATPAK, profile=long_profile(scratch) / "x" / "..", platform="linux")
            other = startup.instance_channel(FLATPAK, profile=Path(scratch) / "other", platform="linux")
        self.assertEqual(one, again)
        self.assertNotEqual(one, other)
        self.assertNotEqual(one, startup.instance_channel(FLATPAK, platform="linux"))

    @unittest.skipIf(sys.platform == "win32", "on Windows the channel is a named pipe, not a path")
    def test_a_socket_too_long_is_said_in_the_log_with_its_reason(self):
        from unittest import mock

        name = str(Path(tempfile.gettempdir()) / f"{'x' * 120}.socket")
        with mock.patch.object(single_instance.log, "complain") as complain:
            self.assertFalse(single_instance.Receiver(name).listen())
        where, error = complain.call_args.args
        self.assertIn("listen for later starts", where)
        self.assertIn(str(single_instance.SOCKET_PATH_MAX), str(error))
        self.assertIn("window of its own", str(error))

    @unittest.skipIf(sys.platform == "win32", "on Windows the channel is a named pipe, not a path")
    def test_on_linux_the_socket_is_in_the_users_runtime_folder_and_in_the_flatpaks(self):
        plain = single_instance.channel_name(APP_ID, "u", environ={"XDG_RUNTIME_DIR": "/run/user/1000"})
        self.assertTrue(plain.startswith("/run/user/1000/"))
        sandboxed = single_instance.channel_name(APP_ID, "u", environ={"XDG_RUNTIME_DIR": "/run/user/1000",
                                                                       "FLATPAK_ID": APP_ID})
        self.assertTrue(sandboxed.startswith(f"/run/user/1000/app/{APP_ID}/"))

    def test_a_message_goes_and_comes_back_and_junk_is_refused(self):
        self.assertEqual((["C:/a b/c.mer"], "t"), single_instance.decode(single_instance.encode(["C:/a b/c.mer"], "t")))
        for junk in (b"not json", b"[1, 2]", b'{"files": [1]}', b'{"files": "x"}', b"\xff\xfe"):
            with self.subTest(junk=junk), self.assertRaises(ValueError):
                single_instance.decode(junk)

    def test_tests_and_photographs_hand_nothing_to_the_open_window(self):
        self.assertIsNone(startup.instance_channel({"MERIDIANA_SCREENSHOT": "shot.png"}))
        self.assertIsNone(startup.instance_channel({"MERIDIANA_INSTANCE": "off"}))
        self.assertEqual("mine", startup.instance_channel({"MERIDIANA_INSTANCE": "mine",
                                                           "MERIDIANA_SCREENSHOT": "s.png"}))
        self.assertIsNotNone(startup.instance_channel({}))

    def test_every_profile_has_a_channel_of_its_own(self):
        # a start from a checkout, a test, a tool: never the window of the installed program, nor of another profile
        with tempfile.TemporaryDirectory() as scratch:
            one = startup.instance_channel({}, profile=Path(scratch) / "one")
            again = startup.instance_channel({}, profile=Path(scratch) / "other" / ".." / "one")
            other = startup.instance_channel({}, profile=Path(scratch) / "other")
        self.assertEqual(one, again)
        self.assertNotEqual(one, other)
        self.assertNotEqual(one, startup.instance_channel({}))
        self.assertIn("meridiana", one)
        self.assertEqual("mine", startup.instance_channel({"MERIDIANA_INSTANCE": "mine"}, profile=Path("p")))
        self.assertIsNone(startup.instance_channel({"MERIDIANA_INSTANCE": "off"}, profile=Path("p")))


class TwoProcesses(unittest.TestCase):
    """A receiver and a sender, each a process of its own."""

    def test_the_second_process_hands_its_files_to_the_first(self):
        channel = unique_channel()
        receiver = subprocess.Popen([sys.executable, "-c", RECEIVER, channel], env=environment(), text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(receiver.stderr.close)
        self.addCleanup(receiver.stdout.close)
        self.addCleanup(receiver.kill)
        self.assertEqual("ready", receiver.stdout.readline().strip(), receiver.stderr.read() if receiver.poll() else "")
        files = [str(Path(tempfile.gettempdir()) / "un tetto.mer"), "/b/è.mer"]
        sender = subprocess.run([sys.executable, "-c", SENDER, channel, *files], env=environment(), timeout=30,
                                capture_output=True, text=True, check=False)
        self.assertEqual(0, sender.returncode, sender.stderr)
        self.assertEqual([files, "a-token"], json.loads(receiver.stdout.readline()))
        self.assertEqual(0, receiver.wait(timeout=30))

    def test_with_a_profile_of_a_long_path_the_second_process_finds_the_first(self):
        # D1 of r32: the channel of a profile, whatever the length of its folder's path, is one a socket can take
        with tempfile.TemporaryDirectory() as scratch:
            here = {name: os.environ[name] for name in ("XDG_RUNTIME_DIR", "FLATPAK_ID") if name in os.environ}
            channel = startup.instance_channel(here, profile=long_profile(scratch))
        receiver = subprocess.Popen([sys.executable, "-c", RECEIVER, channel], env=environment(), text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(receiver.stderr.close)
        self.addCleanup(receiver.stdout.close)
        self.addCleanup(receiver.kill)
        self.assertEqual("ready", receiver.stdout.readline().strip(), receiver.stderr.read() if receiver.poll() else "")
        sender = subprocess.run([sys.executable, "-c", SENDER, channel, "x.mer"], env=environment(), timeout=30,
                                capture_output=True, text=True, check=False)
        self.assertEqual(0, sender.returncode, sender.stderr)
        self.assertEqual([["x.mer"], "a-token"], json.loads(receiver.stdout.readline()))
        self.assertEqual(0, receiver.wait(timeout=30))

    def test_with_nobody_listening_the_second_process_says_so_at_once(self):
        start = time.monotonic()
        sender = subprocess.run([sys.executable, "-c", SENDER, unique_channel(), "x.mer"], env=environment(),
                                timeout=30, capture_output=True, text=True, check=False)
        self.assertEqual(1, sender.returncode, sender.stderr)
        self.assertLess(time.monotonic() - start, 15)


class TwoStarts(unittest.TestCase):
    """Two starts of Meridiana itself (`python -m meridiana`, the Quick window), offscreen, on one temporary profile:
    the second gives its project to the first window and ends; the first opens it (it becomes its last project)."""

    def test_a_second_start_with_a_project_gives_it_to_the_first_window(self):
        with tempfile.TemporaryDirectory(prefix="meridiana-instance-", ignore_cleanup_errors=True) as scratch:
            folder = Path(scratch)
            profile = folder / "profile"
            project = folder / "consegnato a lui.mer"
            capannone("Consegnato").save(project)
            # the first start's own environment: on Linux the socket is in its XDG_RUNTIME_DIR, and with {} the test
            # looked for it in another folder (the first start «never listened», in the WSL and on the CI's runner)
            channel = startup.instance_channel(environment(), profile=profile)
            command = [sys.executable, "-m", "meridiana", "--profile", str(profile)]
            first = subprocess.Popen(command, cwd=str(folder), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                     text=True, errors="replace", env=environment())
            self.addCleanup(first.stderr.close)
            self.addCleanup(end, first)
            deadline = time.monotonic() + 120
            while not single_instance.hand_over(channel, []):        # until the first start listens
                self.assertIsNone(first.poll(), "the first start ended early")
                self.assertLess(time.monotonic(), deadline, "the first start never listened")
                pump(200)
            # the second start: a window of its own would never end (the time limit)
            second = subprocess.run([*command, str(project)], cwd=str(folder), timeout=120, capture_output=True,
                                    text=True, errors="replace", check=False, env=environment())
            self.assertEqual(0, second.returncode, second.stderr[-2000:])
            settings = profile / "quick-profile" / "config" / "config.json"

            def last_project():
                try:
                    return json.loads(settings.read_text(encoding="utf-8")).get("last_project", "")
                except (OSError, ValueError):
                    return ""
            deadline = time.monotonic() + 120
            while last_project() != str(project.resolve()):
                self.assertIsNone(first.poll(), "the first start ended instead of opening the project")
                self.assertLess(time.monotonic(), deadline, "the first window did not open the project handed over")
                pump(200)
            self.assertIsNone(first.poll())                         # still there: one window, the first


class HandedOver(unittest.TestCase):
    """What the open window does with what a later start hands over (QuickWindow.open_handed_over)."""

    @classmethod
    def setUpClass(cls):
        from meridiana.gui.application import create_app
        cls.app = create_app()

    def setUp(self):
        from meridiana.gui.application import QuickWindow
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.folder = Path(self.temp.name)
        self.file = self.folder / "primo.mer"
        capannone("Primo").save(self.file)
        self.second = self.folder / "secondo.mer"
        capannone("Secondo").save(self.second)
        project, _notice = model.Project.load(self.file)
        self.host = QuickWindow(project, self.folder / "cache", real_views=True, path=self.file)
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        pump(200)
        self.session = self.host.bridge.session
        self.files = self.host.parts.controllers["files"]

    def tearDown(self):
        self.host.close()
        pump(50)
        self.temp.cleanup()

    def wait(self, condition, seconds=20):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            pump(20)
            if condition():
                return True
        return False

    def test_the_same_project_is_only_brought_forward(self):
        self.session.edit("Rename", lambda p: setattr(p, "name", "Primo, cambiato"))
        self.win.showMinimized()
        pump(50)
        self.host.open_handed_over([str(self.file)], "")
        pump(100)
        from PySide6.QtGui import QWindow
        self.assertNotEqual(self.win.visibility(), QWindow.Visibility.Minimized)
        self.assertEqual(self.session.project.name, "Primo, cambiato")      # nothing read again, nothing asked
        self.assertFalse(self.files.property("confirmation"))
        self.assertFalse(self.win.property("fileOpen"))

    def test_another_project_is_opened_after_the_unsaved_changes_are_asked_about(self):
        self.session.edit("Rename", lambda p: setattr(p, "name", "Primo, cambiato"))
        self.host.open_handed_over([str(self.second)], "")
        pump(100)
        self.assertTrue(self.files.property("confirmation"), "the unsaved changes are asked about first")
        self.assertTrue(self.win.property("fileOpen"), "in the File page, where the question is")
        self.assertEqual(self.session.path, self.file)
        self.files.resolveChanges("discard")
        self.assertTrue(self.wait(lambda: self.session.path == self.second), self.files.property("error"))
        self.assertEqual(self.session.project.name, "Secondo")
        self.assertTrue(self.wait(lambda: not self.win.property("fileOpen")))

    def test_a_clean_window_opens_it_at_once_and_a_start_without_a_project_changes_nothing(self):
        self.host.open_handed_over([], "")
        pump(50)
        self.assertEqual(self.session.path, self.file)
        self.host.open_handed_over([str(self.second)], "a-token")
        self.assertTrue(self.wait(lambda: self.session.path == self.second), self.files.property("error"))
        self.assertFalse(self.files.property("confirmation"))
        # a file that cannot be opened is said, and the project in hand stays
        self.host.open_handed_over([str(self.folder / "non esiste.mer")], "")
        self.assertTrue(self.wait(lambda: self.files.property("error") != ""))
        self.assertEqual(self.session.path, self.second)

    def test_a_project_handed_over_while_a_dialog_is_open_waits_for_it(self):
        part = self.host.parts.controllers["filePart"]
        part.openDialog("about")
        pump(50)
        self.host.open_handed_over([str(self.second)], "")
        pump(200)
        self.assertEqual(self.session.path, self.file)
        part.dismissDialog()
        self.assertTrue(self.wait(lambda: self.session.path == self.second), self.files.property("error"))


if __name__ == "__main__":
    unittest.main()
