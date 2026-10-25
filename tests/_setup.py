"""Shared test helpers: put src/ on sys.path, find the data of the tests, tell the platform, wait for a condition,
dispose of a window, put back what a module changes of the process. Every test module starts with `import _setup`.

The tests are in folders (study 18, D 7.1), each a package that `python -m unittest discover -s tests` finds from
the root: nucleo (the core, no Qt), calcoli (the energy and its references), formati (the files of every version),
widget (one widget at a time, offscreen), finestra (the MainWindow itself), esterni (only when asked with an
environment variable). The projects and the data they share are in _fixtures.py."""

import os
import sys
import tempfile
from pathlib import Path

_TEST_HOME = tempfile.TemporaryDirectory(prefix="meridiana-tests-")
os.environ["HOME"] = _TEST_HOME.name
os.environ["USERPROFILE"] = _TEST_HOME.name
os.environ.pop("MERIDIANA_KOKORO_DIR", None)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURES = HERE / "fixtures"                    # small data files (the sun's reference, an extract of the CEC list)
DATA = HERE / "data"                            # third-party files with their licence (PVsyst's PAN and OND)
FORMATS = HERE / "formati" / "file"             # the files of every version, frozen
REFERENCES = HERE / "calcoli" / "riferimenti"   # answers of the services, recorded
sys.path.insert(0, str(ROOT / "src"))
# the system's keyring is never touched by a test (Meridio's key, task 14): a keyring that keeps nothing, unless a
# test puts its own in memory (keyring.set_keyring)
os.environ.setdefault("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")

WINDOWS = sys.platform == "win32"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def qt_or_skip():
    """PySide6 and a display, or unittest.SkipTest: the window tests run where they can (the CI's
    window job, a desktop), and say why not elsewhere."""
    import unittest
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        raise unittest.SkipTest("PySide6") from None
    if not WINDOWS and not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")
                            or os.environ.get("QT_QPA_PLATFORM")):
        raise unittest.SkipTest("no display")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app._pristine = _qt_state(app)              # what keep_global_state puts back when it found no application
    _windows_on_screen(app)
    return app


_LOOKS: dict = {}


def meridiana_look(theme: str = "light", accent: str = "bronze"):
    """Meridiana's look on the application, as the window sets it before it builds its widgets (ui/theme.py): Fusion
    with its scroll bars (ui/scrollbars.py) and Inter once per process (as the program does: not put back), the
    fonts of the catalogue for Qt's classes, the palette and the style sheet of
    `theme` (put back by keep_global_state after the module). For a widget tested alone whose sizes or colours
    depend on it; the Theme object, kept alive here."""
    from meridiana import config
    from meridiana.ui.theme import Theme
    app = qt_or_skip()
    key = (theme, accent)
    if key not in _LOOKS:
        _LOOKS[key] = Theme(config.Config(theme=theme, accent=accent, background="none"), app=app)
    else:
        _LOOKS[key].applied = None
        _LOOKS[key].apply()
    return _LOOKS[key]


def wait_until(app, condition, seconds: float = 20.0) -> bool:
    """The events of the application turned until `condition()` holds, at most `seconds`: whether it did. Never a
    fixed wait: a test waits for what it means (study 18, D 5.4)."""
    import time
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def turn_events(app, ms: float) -> None:
    """The event loop for `ms` milliseconds, as the window runs it: only for the tests where the time itself is what
    is tested (a wait shown past its threshold, a job that reaches its next step); elsewhere wait_until."""
    import time
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.002)


def wait_settled(app, probe, turns: int = 5, seconds: float = 5.0) -> bool:
    """The events turned until `probe()` gives the same value `turns` times running (a layout of docks and splitters
    that settles after a resize): whether it did within `seconds`. A condition, in the place of a fixed wait."""
    import time
    end, last, same = time.monotonic() + seconds, object(), 0
    while time.monotonic() < end:
        app.processEvents()
        value = probe()
        same = same + 1 if value == last else 0
        if same >= turns:
            return True
        last = value
        time.sleep(0.01)
    return False


def keyboard_or_skip(test, widget) -> None:
    """The keyboard on `widget`, its window activated and waited for; or the test is skipped saying why. Wayland and
    some desktops of the CI give no focus to a window the user did not activate: what needs the keyboard is then
    not tried, and the result says so instead of passing in silence (study 18, D 5.4)."""
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    window = widget.window()
    window.activateWindow()
    if not QTest.qWaitForWindowActive(window, 2000):
        test.skipTest("the window did not get the keyboard (Wayland, a CI desktop): this part is not tried")
    # a field of a page just built is shown when the events turn (a layout shows what is added to it later, queued):
    # in a window active already nothing turned them, and a field not yet visible takes no keyboard
    QApplication.processEvents()
    widget.setFocus()
    QApplication.processEvents()
    focus = QApplication.focusWidget()
    if not (widget.hasFocus() or (focus is not None and widget.isAncestorOf(focus))):
        test.skipTest("the field did not get the keyboard (Wayland, a CI desktop): this part is not tried")


def _qt_state(app) -> dict:
    from PySide6.QtGui import QPalette
    from meridiana.ui import qt_translations
    return {"palette": QPalette(app.palette()), "sheet": app.styleSheet(), "qt_words": list(qt_translations._INSTALLED),
            "wheel": getattr(app, "_meridiana_wheel_guard", None)}


def _restore_qt(app, state: dict) -> None:
    from meridiana.ui import qt_translations
    if qt_translations._INSTALLED != state["qt_words"]:
        qt_translations.install(app, "en")
        for t in state["qt_words"]:
            app.installTranslator(t)
            qt_translations._INSTALLED.append(t)
    guard = getattr(app, "_meridiana_wheel_guard", None)
    if guard is not None and state["wheel"] is None:
        app.removeEventFilter(guard)
        del app._meridiana_wheel_guard
    if app.styleSheet() != state["sheet"]:
        app.setStyleSheet(state["sheet"])
    if app.palette() != state["palette"]:
        app.setPalette(state["palette"])
    from meridiana.ui.theme import SystemAccent
    system = app.findChild(SystemAccent)
    if system is not None:
        system.motion.emit(system.reduced_motion)  # the listeners back to what the system asks


def keep_global_state() -> None:
    """The setUpModule of a module that changes what the whole process shares: what the module found is put back
    after its last test, also when a test failed half way (study 18, D 5.7): the environment, the language of the
    strings, and where Qt runs the application's palette and style sheet, Qt's own words, the wheel's guard and
    the motion the system asks for. Without an application at the start, the one made later goes back to how it
    was made."""
    import unittest

    from meridiana import i18n
    env = dict(os.environ)
    translation = i18n._translation
    app = _application()
    found = _qt_state(app) if app is not None else None

    def restore():
        for key in set(os.environ) | set(env):
            if os.environ.get(key) != env.get(key):
                if key in env:
                    os.environ[key] = env[key]
                else:
                    del os.environ[key]
        i18n._translation = translation
        now = _application()
        state = found if found is not None else getattr(now, "_pristine", None)
        if now is not None and state is not None:
            _restore_qt(now, state)
    unittest.addModuleCleanup(restore)


def _application():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return None
    return QApplication.instance()


def _windows_on_screen(app) -> None:
    """MERIDIANA_TEST_SCREEN=1 opens the tests' windows on that screen (counted from 0), so that they do not
    stand in the way of whoever works at the computer; their content is the same, drawn on a real screen."""
    from PySide6.QtCore import QEvent, QObject
    wanted = os.environ.get("MERIDIANA_TEST_SCREEN", "")
    screens = app.screens()
    if not wanted.isdigit() or getattr(app, "_test_screen", None) is not None:
        return
    if int(wanted) >= len(screens):
        # the test screen is off or unplugged (24/10/2026: a night's run opened on Daniel's main screen): the
        # windows go left of the whole desktop, on the real platform but out of every screen
        left = min(s.geometry().left() for s in screens)
        print(f"MERIDIANA_TEST_SCREEN={wanted}: no such screen, the windows go out of every screen", file=sys.stderr)

        class Away(QObject):
            def eventFilter(self, obj, event):
                if event.type() in (QEvent.Type.Show, QEvent.Type.Resize) and getattr(obj, "isWindow", lambda: False)():
                    x, y = left - obj.frameGeometry().width() - 400, 20
                    if (obj.x(), obj.y()) != (x, y):
                        obj.move(x, y)
                return False

        app._test_screen = Away(app)
        app.installEventFilter(app._test_screen)
        return
    area = screens[int(wanted)].availableGeometry()

    class Mover(QObject):
        """Each window against the right edge of the screen: one wider than the screen (a test may widen
        it) goes over its left edge, out of every screen, and never onto the screen beside it."""
        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Type.Show, QEvent.Type.Resize) and getattr(obj, "isWindow", lambda: False)():
                frame = obj.frameGeometry().width()
                x, y = area.x() + area.width() - frame - 8, area.y() + 20
                if (obj.x(), obj.y()) != (x, y):
                    obj.move(x, y)
            return False

    app._test_screen = Mover(app)
    app.installEventFilter(app._test_screen)


def dispose(window) -> None:
    """Close a test's window and delete it now. A window only closed stays alive (the lambdas connected to its
    signals keep it), and every change of the application's palette or style sheet then polishes its widgets
    too: on the Windows runner the theme's tests went from seconds to minutes."""
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent
    if not shiboken6.isValid(window):
        return                                      # disposed of already (a test that made its window again)
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def window(test, project=None, cfg=None, size=(1200, 800), answers=None, cache=None, paths=None, pause=False):
    """The MainWindow of a test, the one way the tests of finestra/ make it (study 18, D 7.1): its folders in a new
    temporary place (or `paths`), `cfg` (no background by default: no network), `project` saved to `test.file` and
    opened, shown at `size`, its layouts waited for; a weather year written in the cache when `cache` is a Meteo.
    Every message box is answered at once and noted in `test.dialogs` as (kind, (title, text)); `answers` changes
    the answer of a kind ("question": Discard by default). The window is disposed of at the end of the test, after
    the patches are undone; the test gets `test.win`, `test.paths`, `test.cfg` and `test.file`.
    The layout asked by an edit or by a project opened starts at the next turn of the events, not after the 150 ms
    the window waits to gather what is typed (MainWindow.relayout_timer): every layout of every test waited for
    them, about 10 s of the suite (task 18e). `pause` keeps the window's pause, for a test that measures what an
    edit asks for (finestra/test_speed.py). The pause of the year (energy_timer, 500 ms) stays: a year started by
    itself would land in the middle of the tests that compute one."""
    import tempfile
    from unittest import mock

    from PySide6.QtWidgets import QMessageBox

    from meridiana import config as config_module
    from meridiana.paths import Paths
    from meridiana.ui.window import MainWindow
    app = qt_or_skip()
    test.dialogs = []
    chosen = {"question": QMessageBox.StandardButton.Discard, "information": QMessageBox.StandardButton.Ok,
              "warning": QMessageBox.StandardButton.Ok, **(answers or {})}
    for name, answer in chosen.items():
        patcher = mock.patch.object(QMessageBox, name, side_effect=lambda *a, n=name, r=answer, **k:
                                    (test.dialogs.append((n, a[1:3])), r)[1])
        patcher.start()
        test.addCleanup(patcher.stop)
    root = Path(tempfile.mkdtemp())
    test.paths = paths or Paths(config=root / "config", state=root / "state", data=root / "data", cache=root / "cache")
    if cache is not None:
        from _fixtures import write_cache
        write_cache(cache, test.paths.cache)
    test.cfg = cfg if cfg is not None else config_module.Config(background="none")
    win = MainWindow(test.paths, test.cfg)
    test.addCleanup(dispose, win)                  # cleanups run last first: the window goes before the patches
    if not pause:
        win.relayout_timer.setInterval(0)
    # Meridio's local model is not running here: said at once, without the two seconds Windows takes to refuse a
    # connection to a closed port (finestra/test_assistant_chat.py puts a fake server in its place)
    from _fakes import nothing_local, offline
    win.assistant_chat.make_local = offline
    # and nothing else on this PC: the search for local models (R105) does not knock at the PC's real ports
    win.assistant_chat.survey = nothing_local
    test.win = win
    test.file = None
    if project is not None:
        test.file = root / "prova.meridiana"
        project.save(test.file)
        win.open_path(test.file)
    win.resize(*size)
    win.show()
    wanted = [sf.id for sf in win.project.subfields if sf.filled]
    if not wait_until(app, lambda: all(sid in win.results for sid in wanted), 30):
        test.fail("the layout did not come back")
    app.processEvents()
    return win


os.environ.setdefault("LANGUAGE", "en")        # the tests read the source strings
