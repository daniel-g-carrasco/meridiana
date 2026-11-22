"""The modelling journeys of quick/percorsi/modellazione.py, offscreen, with synthetic Qt events on the Quick window.

    QT_QPA_PLATFORM=offscreen QSG_RENDER_LOOP=basic python tests/quick/confronto/percorsi_offscreen.py quick <journey> <out dir>

The same Pilot and the same journeys as the collaudo of 05/11/2026 (native messages on a hidden desktop); here the
hand sends QMouseEvent and QKeyEvent to the window under the point, so nothing reaches the system's pointer or keyboard
and no window is shown on a screen. The profile, the settings and the caches are in a new temporary folder: APPDATA
and LOCALAPPDATA point there before Meridiana is imported. Each run writes <journey>-<engine>.json, .log and the
photos in <out dir>.
"""
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(tempfile.mkdtemp(prefix='meridiana-confronto-'))
for _var in ('APPDATA', 'LOCALAPPDATA'):
    os.environ[_var] = str(WORK/_var)
# The offscreen screen is 800x800 unless told: the Quick window keeps itself inside its screen (R430) and would shrink.
SCREEN = WORK/'offscreen.json'
SCREEN.write_text('{"screens": [{"name": "Confronto", "x": 0, "y": 0, "width": 2560, "height": 1440, '
                  '"logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}', encoding='utf8')
# Qt splits the platform's arguments on ':', so the file is named relative to the current folder, without a drive.
os.environ['QT_QPA_PLATFORM'] = 'offscreen:configfile=' + os.path.relpath(SCREEN, os.getcwd()).replace(os.sep, '/')
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'src')]

from PySide6.QtCore import QEvent, QEventLoop, QPoint, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication, QMouseEvent  # noqa: E402

KEYS = {'enter': Qt.Key.Key_Return, 'esc': Qt.Key.Key_Escape, 'delete': Qt.Key.Key_Delete, 'tab': Qt.Key.Key_Tab,
        'down': Qt.Key.Key_Down, 'up': Qt.Key.Key_Up, 'left': Qt.Key.Key_Left, 'right': Qt.Key.Key_Right,
        'backspace': Qt.Key.Key_Backspace, 'f3': Qt.Key.Key_F3, 'f5': Qt.Key.Key_F5, 'f8': Qt.Key.Key_F8,
        ',': Qt.Key.Key_Comma, '.': Qt.Key.Key_Period, '-': Qt.Key.Key_Minus, ';': Qt.Key.Key_Semicolon,
        'space': Qt.Key.Key_Space}
MODIFIERS = {'ctrl': Qt.KeyboardModifier.ControlModifier, 'shift': Qt.KeyboardModifier.ShiftModifier,
             'alt': Qt.KeyboardModifier.AltModifier}
BUTTONS = {'left': Qt.MouseButton.LeftButton, 'right': Qt.MouseButton.RightButton, 'middle': Qt.MouseButton.MiddleButton}


def pump(ms):
    loop = QEventLoop()
    QTimer.singleShot(max(0, int(ms)), loop.quit)
    loop.exec()


class OffscreenHand:
    """The calls of the real hand (modellazione.NativeHand) with synthetic events: global coordinates in, the window or
    widget under that point gets the event, as a real pointer would."""
    inputs = 0

    def __init__(self, app, window):
        self.app, self.window = app, window
        self.at = None
        self.held = Qt.MouseButton.NoButton

    def spin(self, ms):
        pump(ms)

    def _target(self, x, y):
        g = QPoint(int(x), int(y))
        from PySide6.QtGui import QGuiApplication
        for w in reversed(QGuiApplication.topLevelWindows()):
            if w.isVisible() and w.geometry().contains(g) and w is not self.window and w.flags() & Qt.WindowType.Popup:
                return w, QPointF(w.mapFromGlobal(g))
        return self.window, QPointF(self.window.mapFromGlobal(g))

    def _mouse(self, kind, x, y, button, buttons, modifiers=Qt.KeyboardModifier.NoModifier):
        target, local = self._target(x, y)
        g = QPointF(x, y)
        scene = local
        event = QMouseEvent(kind, scene, scene, g, button, buttons, modifiers)
        self.app.sendEvent(target, event)
        self.inputs += 1

    def move(self, x, y, steps=10, gap_ms=10):
        if self.at is None:
            self.at = (x, y)
        x0, y0 = self.at
        for i in range(1, steps+1):
            px, py = x0+(x-x0)*i/steps, y0+(y-y0)*i/steps
            self._mouse(QEvent.Type.MouseMove, px, py, Qt.MouseButton.NoButton, self.held)
            pump(gap_ms)
        self.at = (x, y)

    def click(self, x=None, y=None, button='left', steps=10, settle=120, popup=False, modifiers=()):
        if x is not None:
            self.move(x, y, steps)
        pump(settle)
        x, y = self.at
        b = BUTTONS[button]
        mods = self._mods(modifiers)
        self.held = b
        self._mouse(QEvent.Type.MouseButtonPress, x, y, b, b, mods)
        pump(50)
        self.held = Qt.MouseButton.NoButton
        self._mouse(QEvent.Type.MouseButtonRelease, x, y, b, Qt.MouseButton.NoButton, mods)
        pump(settle)

    def double_click(self, x, y, popup=False):
        self.click(x, y)
        b = Qt.MouseButton.LeftButton
        self._mouse(QEvent.Type.MouseButtonPress, x, y, b, b)
        self._mouse(QEvent.Type.MouseButtonDblClick, x, y, b, b)
        self._mouse(QEvent.Type.MouseButtonRelease, x, y, b, Qt.MouseButton.NoButton)
        pump(150)

    def drag(self, x0, y0, x1, y1, button='left', steps=14):
        self.move(x0, y0, 4)
        b = BUTTONS[button]
        self.held = b
        self._mouse(QEvent.Type.MouseButtonPress, x0, y0, b, b)
        pump(40)
        self.move(x1, y1, steps, 16)
        self.held = Qt.MouseButton.NoButton
        self._mouse(QEvent.Type.MouseButtonRelease, x1, y1, b, Qt.MouseButton.NoButton)
        pump(120)

    @staticmethod
    def _mods(modifiers):
        mods = Qt.KeyboardModifier.NoModifier
        for m in modifiers:
            mods |= MODIFIERS[m]
        return mods

    def key(self, name, modifiers=(), settle=120, popup=False):
        from PySide6.QtTest import QTest
        mods = self._mods(modifiers)
        code = KEYS[name] if name in KEYS else Qt.Key(ord(name.upper()))
        target = QGuiApplication.focusWindow() or self.window
        QTest.keyClick(target, code, mods)
        self.inputs += 1
        pump(settle)

    def type_text(self, text):
        for character in text:
            self.key(character, settle=40)

    def front(self, popup=False):
        return True


def quick_host(project_file, work):
    from meridiana.core.model import model
    from meridiana.gui.application import QuickWindow, create_app
    from meridiana.gui.sample import recorded_weather
    app = create_app()
    project, _notice = model.Project.load(project_file)
    recorded_weather(project, work)
    host = QuickWindow(project, work, real_views=True)
    host.window.resize(1600, 960)
    host.window.setPosition(0, 0)
    host.window.show()
    host.window.requestActivate()
    # as meridiana.gui.application.main and tools/quick_native_input.py: without this first computation the layouts asked by
    # the edits never come back (seen on the journeys of 05/11/2026: 0 modules after every «Posa»)
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, host.bridge.recompute)
    return app, host, host.window


def dispose(engine, host):
    host.close()


def main(engine, journey, out):
    from quick.percorsi import modellazione
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    project_file = modellazione.base_project(WORK, journey)
    if engine != 'quick':
        raise ValueError(f'only the Quick window is left, not {engine!r}')
    app, host, window = quick_host(project_file, WORK)
    hand = OffscreenHand(app, window)
    start = time.perf_counter()
    with (out/f'{journey}-{engine}.log').open('w', encoding='utf8') as log:
        pilot = modellazione.Pilot(engine, app, host, window, hand, out, journey, log)
        try:
            pilot.prepare()
            modellazione.run(pilot, journey)
        except Exception:
            import traceback
            traceback.print_exc(file=log)
            traceback.print_exc()
        print(f'durata {time.perf_counter()-start:.0f} s, input {hand.inputs}', file=log)
    print('fine', journey, engine, len(pilot.records))
    dispose(engine, host)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
