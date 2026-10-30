"""The second start (R07): one window for every start (single_instance.py, as Quotario's: tried with real processes,
each on a channel of its own, so that a test never reaches the window the person has open); the recovery copy of a
Meridiana still running neither offered nor deleted by another start; a project asked for by name opened, and only
its own copy offered; a project handed over opened in the window already open, after its unsaved changes are asked
about."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

import _setup
from _fixtures import capannone
from _setup import wait_until

from meridiana import APP_ID, app, config, model, recovery, single_instance

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it
SRC = str(Path(recovery.__file__).resolve().parents[1])

RECEIVER = """
import json, sys
from PySide6.QtCore import QCoreApplication, QTimer
from meridiana.single_instance import Receiver
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
from meridiana.single_instance import hand_over
app = QCoreApplication([])
sys.exit(0 if hand_over(sys.argv[1], sys.argv[2:], "a-token") else 1)
"""


def unique_channel() -> str:
    name = f"meridiana-test-{uuid.uuid4().hex[:12]}"
    if sys.platform == "win32":
        return name
    return str(Path(tempfile.gettempdir()) / f"{name}.socket")


def environment(**extra: str) -> dict:
    env = dict(os.environ, PYTHONPATH=SRC, QT_QPA_PLATFORM="offscreen", **extra)
    env.pop("MERIDIANA_TEST_SCREEN", None)
    return env


class Channel(unittest.TestCase):
    def test_the_name_carries_the_app_id_and_the_user(self):
        mine = single_instance.channel_name(APP_ID, "first.person", environ={})
        theirs = single_instance.channel_name(APP_ID, "second.person", environ={})
        self.assertIn(APP_ID, mine)
        self.assertNotEqual(mine, theirs)
        self.assertNotIn("person", mine)

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
        self.assertIsNone(app.instance_channel({"MERIDIANA_SCREENSHOT": "shot.png"}))
        self.assertIsNone(app.instance_channel({"MERIDIANA_INSTANCE": "off"}))
        self.assertEqual("mine", app.instance_channel({"MERIDIANA_INSTANCE": "mine", "MERIDIANA_SCREENSHOT": "s.png"}))
        self.assertIsNotNone(app.instance_channel({}))


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

    def test_with_nobody_listening_the_second_process_says_so_at_once(self):
        start = time.monotonic()
        sender = subprocess.run([sys.executable, "-c", SENDER, unique_channel(), "x.mer"], env=environment(),
                                timeout=30, capture_output=True, text=True, check=False)
        self.assertEqual(1, sender.returncode, sender.stderr)
        self.assertLess(time.monotonic() - start, 15)


class TwoStarts(unittest.TestCase):
    """Two starts of Meridiana itself, offscreen, with settings in a temporary folder and a channel of their own: the
    second gives its project to the first window and ends; the first opens it (it is its last project)."""

    def test_a_second_start_with_a_project_gives_it_to_the_first_window(self):
        qt = _setup.qt_or_skip()
        with tempfile.TemporaryDirectory(prefix="meridiana-instance-") as scratch:
            folder = Path(scratch)
            channel = unique_channel()
            project = folder / "consegnato a lui.meridiana"
            capannone("Consegnato").save(project)
            settings = {"XDG_CONFIG_HOME": str(folder / "c"), "XDG_STATE_HOME": str(folder / "s"),
                        "XDG_DATA_HOME": str(folder / "d"), "XDG_CACHE_HOME": str(folder / "k"),
                        "MERIDIANA_INSTANCE": channel}
            from meridiana.paths import Paths
            paths = Paths.from_env(settings)
            config.save(config.Config(background="none", network_pvgis=False, tour_status="done"), paths.config_file)
            first = subprocess.Popen(
                [sys.executable, "-m", "meridiana"], cwd=str(folder), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=environment(MERIDIANA_SCREENSHOT=str(folder / "first.png"), MERIDIANA_SCREENSHOT_DELAY="15",
                                **settings))
            self.addCleanup(first.stderr.close)
            self.addCleanup(first.stdout.close)
            self.addCleanup(first.kill)
            deadline = time.monotonic() + 60
            while not single_instance.hand_over(channel, []):        # until the first start listens
                self.assertIsNone(first.poll(), "the first start ended early")
                self.assertLess(time.monotonic(), deadline, "the first start never listened")
                qt.processEvents()
                time.sleep(0.2)
            # the second start: no photograph of its own, so a window of its own would never end (timeout)
            second = subprocess.run([sys.executable, "-m", "meridiana", str(project)], cwd=str(folder), timeout=60,
                                    capture_output=True, text=True, check=False, env=environment(**settings))
            self.assertEqual(0, second.returncode, second.stderr[-2000:])
            _out, errors = first.communicate(timeout=90)
            self.assertEqual(0, first.returncode, errors[-2000:])
            self.assertTrue((folder / "first.png").exists())
            saved = json.loads(paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["last_project"], str(project.resolve()))
            # it ended as it should: its recovery mark let go
            self.assertEqual(list((paths.state / "recovery" / recovery.OWNERS).glob("*.lock")), [])

OWNER = """
import sys
from pathlib import Path
from meridiana import model, recovery
state = Path(sys.argv[1])
recovery.claim(state)
recovery.write(state, Path(sys.argv[2]), model.Project(name="Still open").to_json())
print("ready", flush=True)
sys.stdin.readline()
recovery.release(state)
"""


class SecondStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def owner(self, state: Path, project: Path):
        """Another Meridiana, still running, with a copy of `project` (a process of its own: the lock is the
        system's)."""
        src = str(Path(recovery.__file__).resolve().parents[1])
        process = subprocess.Popen([sys.executable, "-c", OWNER, str(state), str(project)],
                                   env=dict(os.environ, PYTHONPATH=src), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (process.kill(), process.wait(30), process.stdin.close(), process.stdout.close(),
                                 process.stderr.close()))
        self.assertEqual(process.stdout.readline().strip(), "ready")
        return process

    def test_the_copy_of_the_window_still_open_is_not_offered_and_survives_a_no(self):
        # D's case: Meridiana open with unsaved changes, a double click on a project starts another one; it asked
        # «Meridiana stopped without saving...», false, and its «No» (here the default answer) deleted the copy
        _setup.window(self, cfg=config.Config(background="none", network_pvgis=False))
        other = self.paths.data / "aperto altrove.meridiana"
        self.owner(self.paths.state, other)
        copy = recovery.slot(self.paths.state, other)
        self.assertTrue(copy.exists())
        self.assertFalse(self.win.offer_recovery())
        self.assertFalse(self.win.offer_recovery(other))
        self.assertEqual([d for d in self.dialogs if d[0] == "question"], [])
        self.assertTrue(copy.exists())

    def test_a_project_asked_for_by_name_is_opened_and_another_projects_copy_waits(self):
        from PySide6.QtWidgets import QMessageBox
        _setup.window(self, cfg=config.Config(background="none", network_pvgis=False, tour_status="done"),
                      answers={"question": QMessageBox.StandardButton.Yes})
        asked = self.paths.data / "chiesto.meridiana"
        asked.parent.mkdir(parents=True, exist_ok=True)
        capannone("Chiesto").save(asked)
        recovery.write(self.paths.state, self.paths.data / "altro.meridiana", model.Project(name="Altro").to_json())
        self.assertFalse(app.prepare_workspace(self.win, asked))
        self.assertEqual(self.win.path, asked)                  # «Yes» on the other copy had kept it closed
        self.assertEqual(self.win.project.name, "Chiesto")
        self.assertEqual([d for d in self.dialogs if d[0] == "question"], [])
        self.assertEqual(len(recovery.pending(self.paths.state)), 1)      # not deleted: offered at a plain start
        # the copy of the project asked for is offered, and «Yes» recovers it
        recovery.write(self.paths.state, asked, model.Project(name="Chiesto, modificato").to_json())
        self.assertFalse(app.prepare_workspace(self.win, asked))
        self.assertEqual(self.win.project.name, "Chiesto, modificato")
        self.assertEqual(self.win.path, asked)
        self.assertTrue(self.win._dirty())

    def test_a_project_handed_over_comes_into_the_open_window_after_its_changes_are_asked_about(self):
        _setup.window(self, project=capannone("Primo"))
        win = self.win
        second = self.paths.data / "secondo.meridiana"
        second.parent.mkdir(parents=True, exist_ok=True)
        capannone("Secondo").save(second)
        # the same project handed over again: the window to the front, nothing reloaded, nothing asked
        win._edited("project", "", {"name": "Primo, cambiato"})
        win.showMinimized()
        win.open_handed_over([str(self.file)], "")
        self.assertFalse(win.isMinimized())
        self.assertEqual(win.project.name, "Primo, cambiato")
        self.assertEqual(self.dialogs, [])
        # another project: the unsaved changes asked about first (Discard here), then it is opened
        win.open_file_page("open")
        win.open_handed_over([str(second)], "")
        self.assertEqual([d[0] for d in self.dialogs], ["question"])
        self.assertEqual(win.path, second)
        self.assertEqual(win.project.name, "Secondo")
        self.assertTrue(wait_until(self.app, lambda: not win.file_page.isVisible(), 5))
        # a start without a project only brings the window forward; a file that cannot be opened is said
        win.open_handed_over([], "")
        self.assertEqual(win.path, second)
        win.open_handed_over([str(self.paths.data / "non esiste.meridiana")], "")
        self.assertEqual(win.path, second)
        self.assertEqual(self.dialogs[-1][0], "warning")

    def test_an_opening_that_fails_is_said_by_meridio_and_brings_file_open_back(self):
        # open_path says whether it opened (R07): Meridio answered «opened» when the same file, reopened, failed;
        # a recent project gone left the window on an empty project, without File > Open
        from meridiana.ui.assistant_chat import WindowHost
        _setup.window(self, project=capannone("Primo"))
        win = self.win
        host = WindowHost(win)
        self.assertTrue(host.open_project(self.file))
        self.file.write_text("{", encoding="utf-8")            # damaged since
        self.assertFalse(host.open_project(self.file))
        self.assertEqual(win.path, self.file)
        gone = self.paths.data / "sparito.meridiana"
        win.open_file_page("open")
        self.assertTrue(wait_until(self.app, lambda: win.file_page.isVisible(), 5))
        win.file_page._open_recent(str(gone))
        self.assertEqual(self.dialogs[-1][0], "warning")
        self.app.processEvents()
        self.assertTrue(wait_until(self.app, lambda: win.file_page.isVisible() and win.file_page.exit is None, 5))
        self.assertIs(win.file_page.body.currentWidget(), win.file_page.sections["open"])


if __name__ == "__main__":
    unittest.main()
