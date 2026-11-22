"""Shared test helpers: put src/ on sys.path, find the data of the tests, tell the platform, wait for a condition,
dispose of a window, put back what a module changes of the process. Every test module starts with `import _setup`.

The tests are in folders (study 18, D 7.1), each a package that `python -m unittest discover -s tests` finds from
the root: nucleo (the core, no Qt), calcoli (the energy and its references), formati (the files of every version),
quick (the Qt Quick window, one subgroup at a time), esterni (only when asked with an environment variable). The
projects and the data they share are in _fixtures.py."""

import atexit
import os
import sys
import tempfile
from pathlib import Path

_REAL_ENV = dict(os.environ)        # before the tests' home: where the user's own folders of Meridiana are
# The journeys on a hidden desktop open the proof project of the real profile, kept apart from the tests' home.
os.environ.setdefault("MERIDIANA_REAL_HOME", str(Path.home()))
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
# nothing prepared ahead behind a test's back (R548: the report's preview, the IFC model's geometry), whatever memory
# the PC has free: the tests of the precaching ask for it (MERIDIANA_PRELOAD=1)
os.environ.setdefault("MERIDIANA_PRELOAD", "0")
# study 56: Qt's disk caches of compiled QML and pipelines never in a test, also in a start of the program itself (the
# tests of qt_cache and of the start ask for them in a profile of their own)
os.environ["MERIDIANA_QT_DISK_CACHE"] = "0"
# and no thread that trims the caches behind a test's back when the PC is short of memory (resources.watch)
os.environ["MERIDIANA_MEMORY_WATCH"] = "0"
# R598, study 48 chapter 6 step 0: every session.photo() compared with the project in hand (app/session.py,
# CHECK_PHOTO): a job started on a photo that is not the project would compute something else. Off in the program.
os.environ.setdefault("MERIDIANA_CHECK_PHOTO", "1")

WINDOWS = sys.platform == "win32"


# R594: no test writes in the user's own folders of Meridiana (%APPDATA%\Meridiana and %LOCALAPPDATA%\Meridiana on
# Windows, the XDG folders elsewhere): a reading of an IFC put its geometry in %LOCALAPPDATA%\Meridiana\cache\ifc
# during tests/quick/pagine. Their files are taken at the start of the run and compared at its end
# (tools/run_tests.py, and the exit of «python -m unittest»): what is new, changed or gone is listed, and the run fails.

def profile_roots(environ=None) -> list[Path]:
    """The user's folders of Meridiana for an environment (the real one by default), none inside another."""
    from meridiana.app.platform.paths import Paths
    p = Paths.from_env(_REAL_ENV if environ is None else environ)
    roots = {p.config, p.state, p.data, p.cache}
    if os.name == "nt":
        roots.add(p.state.parent)                   # %LOCALAPPDATA%\Meridiana, its own files too
    roots = sorted(Path(r) for r in roots)
    return [r for r in roots if not any(o != r and o in r.parents for o in roots)]


def profile_files(roots: list[Path]) -> dict:
    """Every file under `roots`: its size and time of change."""
    out = {}
    for root in roots:
        for folder, _dirs, files in os.walk(root):
            for name in files:
                path = os.path.join(folder, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                out[path] = (st.st_size, st.st_mtime_ns)
    return out


def profile_changes(before: dict, after: dict) -> list[str]:
    """What changed between two profile_files: «new», «changed» or «gone», with the path."""
    return sorted([f"new {p}" for p in after if p not in before]
                  + [f"changed {p}" for p in after if p in before and after[p] != before[p]]
                  + [f"gone {p}" for p in before if p not in after])


PROFILE_ROOTS = profile_roots()
_PROFILE_BEFORE = profile_files(PROFILE_ROOTS)
_PROFILE_CHECKED = []


def profile_written() -> list[str]:
    """What the run has written in the user's folders of Meridiana since it started (once: the runner asks, or the exit
    of the interpreter)."""
    _PROFILE_CHECKED.append(True)
    return profile_changes(_PROFILE_BEFORE, profile_files(PROFILE_ROOTS))


def _profile_at_exit() -> None:
    if _PROFILE_CHECKED:
        return
    written = profile_written()
    if written:
        sys.stderr.write("FAILED: the tests wrote in the user's folders of Meridiana (R594):\n  "
                         + "\n  ".join(written) + "\n")
        sys.stderr.flush()
        os._exit(1)


atexit.register(_profile_at_exit)

_PHOTO_CHECKED = []


def photo_mismatches() -> list[str]:
    """Every session.photo() of the run that was not the project in hand (MERIDIANA_CHECK_PHOTO): the run fails with
    them even when the exception was raised in a slot Qt only printed (once: the runner asks, or the exit)."""
    _PHOTO_CHECKED.append(True)
    session = sys.modules.get("meridiana.app.session")
    return list(getattr(session, "PHOTO_MISMATCHES", []))


def _photo_at_exit() -> None:
    if _PHOTO_CHECKED:
        return
    found = photo_mismatches()
    if found:
        sys.stderr.write(f"FAILED: {len(found)} session.photo() not the project in hand:\n" + "\n".join(found) + "\n")
        sys.stderr.flush()
        os._exit(1)


atexit.register(_photo_at_exit)


def _italian_catalogue() -> None:
    """locale/ is not in git. In a new tree without it the program stays in English and says nothing, and the tests on
    words and numbers fail with misleading messages: it is compiled here, once, or the reason is said."""
    import subprocess
    po, mo = ROOT / "po" / "it.po", ROOT / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo"
    if po.exists() and (not mo.exists() or mo.stat().st_mtime < po.stat().st_mtime):
        done = subprocess.run([sys.executable, str(ROOT / "tools" / "compile_po.py"), "--python"], cwd=ROOT,
                              capture_output=True, text=True)
        if done.returncode:
            raise RuntimeError("The Italian catalogue could not be compiled: " + done.stdout + done.stderr)


_italian_catalogue()


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


def wait_until(app, condition, seconds: float = 20.0) -> bool:
    """The events of the application turned until `condition()` holds, at most `seconds`: whether it did. Never a
    fixed wait: a test waits for what it means (study 18, D 5.4)."""
    import time
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)  # wait: a breath between two looks at the condition, so the workers' threads run
    return condition()


def turn_events(app, ms: float) -> None:
    """The event loop for `ms` milliseconds, as the window runs it: only for the tests where the time itself is what
    is tested (a wait shown past its threshold, a job that reaches its next step); elsewhere wait_until."""
    import time
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.002)  # wait: a breath between two looks at the condition, so the workers' threads run


def _qt_state(app) -> dict:
    from PySide6.QtGui import QPalette
    from meridiana.gui import qt_translations
    # a QGuiApplication (the Quick's, quick.app.create_app) has no style sheet: None, and nothing to put back
    sheet = app.styleSheet() if hasattr(app, "styleSheet") else None
    return {"palette": QPalette(app.palette()), "sheet": sheet, "qt_words": list(qt_translations._INSTALLED),
            "wheel": getattr(app, "_meridiana_wheel_guard", None)}


def _restore_qt(app, state: dict) -> None:
    from meridiana.gui import qt_translations
    if qt_translations._INSTALLED != state["qt_words"]:
        qt_translations.install(app, "en")
        for t in state["qt_words"]:
            app.installTranslator(t)
            qt_translations._INSTALLED.append(t)
    guard = getattr(app, "_meridiana_wheel_guard", None)
    if guard is not None and state["wheel"] is None:
        app.removeEventFilter(guard)
        del app._meridiana_wheel_guard
    if state["sheet"] is not None and hasattr(app, "styleSheet") and app.styleSheet() != state["sheet"]:
        app.setStyleSheet(state["sheet"])
    if app.palette() != state["palette"]:
        app.setPalette(state["palette"])
    from meridiana.gui.style.theme import SystemAccent
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


def end_qt() -> None:
    """What Qt still holds at the end of a run, taken apart before the process ends (tools/run_tests.py, before its
    os._exit). A tearDown that calls engine.deleteLater() and processEvents() leaves the last engine and its window
    alive: processEvents() never delivers a DeferredDelete posted outside an event loop (only QTest.qWait in the next
    test did). With os._exit the DLLs' static destructors then ran on a live QQuickWindow and its scene graph: an
    access violation at every end of quick.pianta.test_aids_window (3 runs out of 3, 07/11/2026), and of the whole
    tests/quick/pianta, unseen because the exit code had already been set."""
    from PySide6.QtCore import QCoreApplication, QEvent
    app = QCoreApplication.instance()
    if app is None:
        return
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    try:
        from PySide6.QtGui import QGuiApplication
    except ImportError:
        return
    if isinstance(app, QGuiApplication):
        for window in QGuiApplication.topLevelWindows():
            window.close()
            window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


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


os.environ.setdefault("LANGUAGE", "en")        # the tests read the source strings


# ---------------------------------------------------------------------------------------------------------------------
# The Quick's common base (r23-f8, docs/revisioni/piano-riordino-r21.md F8, docs/quick/regole.md rule 10).
#
# tests/quick/__init__.py installs it, so it holds for every module of tests/quick whatever the module does itself (118
# of the 193 modules did not even import _setup). Order does not count any more:
#   - one application for the whole run, a QApplication made before the first module (crash 1 of 07/11/2026: a
#     QGuiApplication made first by quick.app.create_app took the QApplication away from every module after it);
#   - every module starts from the same state: the language of the strings (create_app calls i18n.setup('it'), 57
#     modules call it), Qt's default locale (backend/properties_page.py sets it_IT), the environment, the clipboard
#     of the offscreen platform; what the module left is taken apart before the next one: the visible Quick windows
#     closed, the objects given to deleteLater deleted (outside an event loop processEvents never delivers them: the
#     engines of a finished module lived on until a random qWait of another one), Python's garbage collected there
#     and not in the middle of another module;
#   - every test of a module gives back the language, the locale and the environment it found, and its deleteLater
#     objects are deleted when it ends.
# tools/run_tests.py adds faulthandler: the stacks of every thread on a crash, and on a test that does not end.

_QUICK: dict = {}


def _is_quick(name) -> bool:
    return bool(name) and (name == "quick" or name.startswith("quick."))


def quick_app():
    """The one application of a run of the Quick's tests, made once: a QApplication, whatever module comes first. None
    without PySide6 or without a display (the module then skips itself, as before)."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return None
    app = QApplication.instance()
    if app is None:
        if not WINDOWS and not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")
                                or os.environ.get("QT_QPA_PLATFORM")):
            return None
        app = QApplication(["meridiana-quick"])
        app._pristine = _qt_state(app)
    return app


def _quick_baseline() -> None:
    """The state every module of tests/quick starts from, taken once, before the first module's setUpModule: English
    (the source strings, as LANGUAGE=en above), the environment after the imports, Qt's default locale of the PC."""
    if _QUICK:
        return
    from meridiana import i18n
    app = quick_app()
    _QUICK["env"] = dict(os.environ)
    _QUICK["translation"] = i18n.translation_for("en")
    _QUICK["locale"] = None
    if app is not None:
        from PySide6.QtCore import QLocale
        _QUICK["locale"] = QLocale()


def _put_back(env: dict, translation, locale) -> None:
    from meridiana import i18n
    for key in set(os.environ) | set(env):
        if os.environ.get(key) != env.get(key):
            if key in env:
                os.environ[key] = env[key]
            else:
                del os.environ[key]
    i18n._translation = translation
    if locale is not None:
        from PySide6.QtCore import QLocale
        if QLocale() != locale:
            QLocale.setDefault(locale)


def _flush_deleted() -> None:
    """The objects given to deleteLater, deleted now (also outside an event loop, as end_qt does)."""
    try:
        from PySide6.QtCore import QCoreApplication, QEvent
    except ImportError:
        return
    if QCoreApplication.instance() is not None:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def _clear_clipboard(app) -> None:
    # only the clipboard of a platform of the tests: never the one of whoever works at the computer
    if app is not None and app.platformName() in ("offscreen", "minimal") and hasattr(app, "clipboard"):
        app.clipboard().clear()


def quick_module_end() -> None:
    """After a module of tests/quick (its tearDownModule and module cleanups done): what it left taken apart, and the
    state put back to the baseline, so that the next module finds what it would find alone."""
    import gc
    if not _QUICK:
        return
    try:
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtQuick import QQuickWindow
    except ImportError:
        QCoreApplication = None
    app = QCoreApplication.instance() if QCoreApplication is not None else None
    if app is not None:
        from PySide6.QtGui import QGuiApplication
        if isinstance(app, QGuiApplication):
            # closed, not deleted: the engine that made a window deletes it (a window deleted under its engine is a
            # crash later); a closed window stops its render loop, its animations and the timers they drive
            for window in QGuiApplication.topLevelWindows():
                if isinstance(window, QQuickWindow) and window.isVisible():
                    window.close()
        _flush_deleted()
        app.processEvents()
    gc.collect()
    _flush_deleted()
    _put_back(_QUICK["env"], _QUICK["translation"], _QUICK["locale"])
    _clear_clipboard(app)


def quick_isolation() -> None:
    """Installed once by tests/quick/__init__.py: the hooks of unittest that run the baseline before the first module,
    quick_module_end after each module of tests/quick, and give back to every test of tests/quick the state it found."""
    import faulthandler
    import unittest
    import unittest.suite as suite
    if getattr(suite.TestSuite, "_meridiana_quick", False):
        return
    if not faulthandler.is_enabled():
        faulthandler.enable()                       # a crash says where (exit code 139 alone said nothing)
    fixture, teardown, run = (suite.TestSuite._handleModuleFixture, suite.TestSuite._handleModuleTearDown,
                              unittest.TestCase.run)

    def handle_fixture(self, test, result):
        if _is_quick(test.__class__.__module__):
            _quick_baseline()
        return fixture(self, test, result)

    def handle_teardown(self, result):
        previous = self._get_previous_module(result)
        try:
            return teardown(self, result)
        finally:
            if _is_quick(previous):
                quick_module_end()

    def run_test(self, result=None):
        if not _is_quick(type(self).__module__):
            return run(self, result)
        from meridiana import i18n
        locale = None
        try:
            from PySide6.QtCore import QCoreApplication, QLocale
            app = QCoreApplication.instance()
            locale = QLocale() if app is not None else None
        except ImportError:
            app = None
        env, translation = dict(os.environ), i18n._translation
        try:
            return run(self, result)
        finally:
            _flush_deleted()
            _put_back(env, translation, locale)
            _clear_clipboard(app)

    suite.TestSuite._handleModuleFixture = handle_fixture
    suite.TestSuite._handleModuleTearDown = handle_teardown
    unittest.TestCase.run = run_test
    suite.TestSuite._meridiana_quick = True


def wait_for(condition, ms: int = 10000) -> bool:
    """The events turned (QTest.qWait in steps of 10 ms) until `condition()` holds, at most `ms`: whether it did, as
    Qt's QTest::qWaitFor, which PySide6 does not have. The wait of the Quick's tests in the place of a fixed
    QTest.qWait (rule 10): it ends as soon as the thing is there, and under load it waits longer instead of failing;
    the test then asserts what it asserted before."""
    import time
    from PySide6.QtTest import QTest
    end = time.monotonic() + ms / 1000
    while not condition():
        if time.monotonic() >= end:
            return bool(condition())
        QTest.qWait(10)
    return True


def native_reason() -> str:
    """Why the native journeys of tests/quick/percorsi (real mouse and keyboard on a hidden desktop) do not run here,
    or "" when they do. They are apart from the normal suite (r23-f8): only on Windows, only when asked with
    MERIDIANA_NATIVE=1, never with an offscreen platform (the program they start would inherit it) nor with
    MERIDIANA_NO_NATIVE. They cannot run while Daniel works at the PC, and under load they went red for no fault."""
    if not WINDOWS:
        return "Windows messages"
    if os.environ.get("MERIDIANA_NATIVE") != "1" or os.environ.get("MERIDIANA_NO_NATIVE"):
        return "native journey: only with MERIDIANA_NATIVE=1 (a free desktop, tools/quick_native_input.py)"
    if os.environ.get("QT_QPA_PLATFORM") in ("offscreen", "minimal"):
        return "native journey: not with an offscreen platform"
    return ""

