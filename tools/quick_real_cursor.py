"""Run one modelling journey on Quick or on Widgets with the real cursor and real keys.

    python tools/quick_real_cursor.py <quick|widgets> <journey|probe> <out dir> [--until HH:MM] [--dry]

Safety, none of this may be removed:
- it stops if the cursor moves without it, and puts the cursor back at the end;
- it clicks only if WindowFromPoint gives the test window, at every click;
- it presses keys only if the test window is in front;
- it refuses all input after the time given by --until (13:55 by default);
- the test window stays on top, and the process leaves with os._exit, saying why.
A popup of the test window is a window of its own: `popup=True` also accepts a window of this very
process, never of another one. Every journey is in tests/quick/percorsi/modellazione.py.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'src')]
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
MOVE, ABSOLUTE, VIRTUAL, LDOWN, LUP, RDOWN, RUP, MDOWN, MUP, WHEEL = (
    0x0001, 0x8000, 0x4000, 0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0040, 0x0800)
BUTTONS = {'left': (LDOWN, LUP), 'right': (RDOWN, RUP), 'middle': (MDOWN, MUP)}
KEYS = {'esc': 0x1B, 'enter': 0x0D, 'tab': 0x09, 'backspace': 0x08, 'delete': 0x2E, 'up': 0x26, 'down': 0x28,
        'left': 0x25, 'right': 0x27, 'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'f3': 0x72, 'f8': 0x77,
        ',': 0xBC, '.': 0xBE, '-': 0xBD, ';': 0xBC}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.c_size_t)]


class HARDWARE(ctypes.Structure):
    _fields_ = [('a', wintypes.DWORD), ('b', wintypes.DWORD)]


class UNION(ctypes.Union):
    _fields_ = [('mi', MOUSEINPUT), ('ki', KEYBDINPUT), ('hi', HARDWARE)]


class INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('u', UNION)]


class Stop(Exception):
    """A safety check failed: nothing else may be pressed."""


class RealHand:
    """The interface of NativeInput in tools/quick_native_input.py, with the system's real cursor.
    Coordinates are Qt's global logical ones; the screen's scale is applied here."""

    def __init__(self, app, window, hwnd, until):
        self.app, self.window, self.hwnd, self.until = app, window, hwnd, until
        self.expected = None
        self.start = self.position()
        self.vx, self.vy, self.vw, self.vh = (user32.GetSystemMetrics(i) for i in (76, 77, 78, 79))
        self.pid = kernel32.GetCurrentProcessId()
        self.inputs = 0
        self.held = set()

    def position(self):
        p = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(p))
        return p.x, p.y

    def physical(self, x, y):
        screen = self.window.screen()
        g, scale = screen.geometry(), screen.devicePixelRatio()
        return round(g.x()+(x-g.x())*scale), round(g.y()+(y-g.y())*scale)

    def _send(self, item):
        if time.strftime('%H:%M') >= self.until:
            raise Stop(f'ora limite {self.until} raggiunta: niente piu input vero')
        self.inputs += 1
        if user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT)) != 1:
            raise Stop('SendInput rifiutato: sessione bloccata o desktop non attivo')

    def check(self):
        if self.expected is not None:
            x, y = self.position()
            if abs(x-self.expected[0]) > 4 or abs(y-self.expected[1]) > 4:
                raise Stop(f'mouse mosso: atteso {self.expected}, trovato {(x, y)}')

    def spin(self, ms):
        end = time.perf_counter()+ms/1000
        while time.perf_counter() < end:
            self.app.processEvents()
            time.sleep(0.002)
            self.check()

    def _warp(self, px, py):
        i = INPUT(type=0)
        i.u.mi = MOUSEINPUT(int((px-self.vx)*65535/(self.vw-1)), int((py-self.vy)*65535/(self.vh-1)), 0,
                            MOVE | ABSOLUTE | VIRTUAL, 0, 0)
        self._send(i)
        self.expected = (px, py)

    def move(self, x, y, steps=10, gap_ms=10):
        px, py = self.physical(x, y)
        x0, y0 = self.position()
        g = self.window.screen().geometry()
        if not (g.x() <= x0 < g.x()+g.width()*self.window.screen().devicePixelRatio()
                and g.y() <= y0 < g.y()+g.height()*self.window.screen().devicePixelRatio()):
            # From another screen a straight line stops at the border between them.
            self._warp(px, py)
            self.spin(50)
            return
        for n in range(1, steps+1):
            self.check()
            self._warp(round(x0+(px-x0)*n/steps), round(y0+(py-y0)*n/steps))
            self.spin(gap_ms)

    def own(self, px, py, popup=False):
        root = user32.GetAncestor(user32.WindowFromPoint(wintypes.POINT(px, py)), 2)
        if root == self.hwnd:
            return True
        if not popup or not root:
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
        return pid.value == self.pid

    def _button(self, flag):
        i = INPUT(type=0)
        i.u.mi = MOUSEINPUT(0, 0, 0, flag, 0, 0)
        self._send(i)

    def press(self, button='left', popup=False):
        px, py = self.position()
        if not self.own(px, py, popup):
            raise Stop(f'al punto {(px, py)} non c\'e la finestra di prova: non clicco')
        self._button(BUTTONS[button][0])

    def release(self, button='left'):
        self._button(BUTTONS[button][1])
        self.held.discard(button)

    def click(self, x=None, y=None, button='left', steps=10, settle=120, popup=False):
        if x is not None:
            self.move(x, y, steps)
        self.spin(settle)
        self.press(button, popup)
        self.spin(50)
        self.release(button)
        self.spin(settle)

    def double_click(self, x, y, popup=False):
        self.move(x, y)
        self.spin(120)
        for _n in range(2):
            self.press('left', popup)
            self.spin(25)
            self.release('left')
            self.spin(40)

    def drag(self, x0, y0, x1, y1, button='left', steps=14):
        self.move(x0, y0)
        self.spin(80)
        self.press(button)
        self.spin(60)
        self.move(x1, y1, steps, 16)
        self.spin(80)
        self.release(button)
        self.spin(120)

    def wheel(self, x, y, notches=1):
        self.move(x, y)
        px, py = self.position()
        if not self.own(px, py):
            raise Stop('rotella fuori dalla finestra di prova')
        i = INPUT(type=0)
        i.u.mi = MOUSEINPUT(0, 0, ctypes.c_ulong(120*notches & 0xFFFFFFFF).value, WHEEL, 0, 0)
        self._send(i)
        self.spin(120)

    def front(self, popup=False):
        fg = user32.GetForegroundWindow()
        if fg == self.hwnd:
            return True
        if not popup or not fg:
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
        return pid.value == self.pid

    def _vk(self, vk, flags):
        i = INPUT(type=1)
        i.u.ki = KEYBDINPUT(vk, 0, flags, 0, 0)
        self._send(i)

    def key(self, name, modifiers=(), settle=120, popup=False):
        if not self.front(popup):
            raise Stop(f'tasto {name} non premuto: la finestra di prova non e in primo piano')
        vk = KEYS.get(name.lower()) or ord(name.upper())
        held = [KEYS[m] for m in modifiers]
        try:
            for m in held:
                self._vk(m, 0)
            self._vk(vk, 0)
            self.spin(25)
            self._vk(vk, 2)
        finally:
            for m in reversed(held):
                self._vk(m, 2)
        self.spin(settle)

    def type_text(self, text):
        for character in text:
            self.key(character, settle=40)

    def restore(self):
        self.expected = None
        for button in list(self.held):     # never leave a button down, whatever stopped the journey
            i = INPUT(type=0)
            i.u.mi = MOUSEINPUT(0, 0, 0, BUTTONS[button][1], 0, 0)
            user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        x, y = self.start
        i = INPUT(type=0)
        i.u.mi = MOUSEINPUT(int((x-self.vx)*65535/(self.vw-1)), int((y-self.vy)*65535/(self.vh-1)), 0,
                            MOVE | ABSOLUTE | VIRTUAL, 0, 0)
        user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def start_quick(project_file, work):
    from meridiana import model
    from meridiana.quick.app import QuickWindow, create_app
    from meridiana.quick.sample import recorded_weather
    from PySide6.QtCore import Qt, QTimer
    app = create_app()
    project, notice = model.Project.load(project_file)
    recorded_weather(project, work)
    host = QuickWindow(project, work, real_views=True)
    w = host.window
    w.setFlags(w.flags() | Qt.WindowType.WindowStaysOnTopHint)
    w.resize(1600, 960)
    w.setPosition(60, 40)
    w.show()
    QTimer.singleShot(0, host.bridge.recompute)     # the same steps as quick.app.main: edits lay out from here on
    return app, host, w, int(w.winId()), notice


def start_widgets(project_file, work):
    from unittest import mock
    from PySide6.QtCore import QLocale, Qt
    from PySide6.QtWidgets import QApplication, QMessageBox
    from meridiana import config, i18n, model
    from meridiana.paths import Paths
    from meridiana.quick.sample import recorded_weather
    from meridiana.ui import qt_translations
    from meridiana.ui.theme import load_fonts
    from meridiana.ui.window import MainWindow
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    i18n.setup('it')
    QLocale.setDefault(QLocale('it_IT'))
    qt_translations.install(app, 'it')
    load_fonts('plex')
    paths = Paths.from_env()
    cfg = config.Config(theme='light', font='plex', accent='indigo', backgrounds='grey', language='it',
                        background='none', network_tiles=False, network_pvgis=False, network_geocoding=False,
                        check_updates=False, assistant_animated=False, assistant_voice=False, tour_status='done')
    project, notice = model.Project.load(project_file)
    recorded_weather(project, paths.cache)
    win = MainWindow(paths, cfg)
    dialogs = []

    def answer(kind):
        def side_effect(*args, **kwargs):
            dialogs.append((kind, str(args[1:3])[:300]))
            return QMessageBox.StandardButton.Yes if kind == 'question' else QMessageBox.StandardButton.Ok
        return side_effect
    for kind in ('question', 'information', 'warning', 'critical'):
        mock.patch.object(QMessageBox, kind, side_effect=answer(kind)).start()
    win.message_boxes = dialogs
    win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    win.resize(1600, 960)
    win.move(60, 40)
    win.show()
    win.open_path(project_file)
    return app, win, win.windowHandle(), int(win.winId()), notice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', choices=('quick', 'widgets'))
    parser.add_argument('journey')
    parser.add_argument('out', type=Path)
    parser.add_argument('--until', default='13:55')
    parser.add_argument('--dry', action='store_true', help='Open the window, write the facts, no input at all')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='meridiana-modellazione-'))
    for variable, child in (('XDG_CONFIG_HOME', 'config'), ('XDG_STATE_HOME', 'state'), ('XDG_DATA_HOME', 'data'),
                            ('XDG_CACHE_HOME', 'cache'), ('APPDATA', 'roaming'), ('LOCALAPPDATA', 'local')):
        os.environ[variable] = str(work/child)
    os.environ.update(MERIDIANA_INSTANCE='off', PYTHON_KEYRING_BACKEND='keyring.backends.null.Keyring',
                      QSG_RHI_BACKEND='d3d11', PYTHONUTF8='1')
    from quick.percorsi import modellazione
    project_file = modellazione.base_project(work, args.journey)
    starter = start_quick if args.engine == 'quick' else start_widgets
    app, host, window, hwnd, notice = starter(project_file, work)
    hand = RealHand(app, window, hwnd, args.until)
    log = (args.out/f'{args.journey}-{args.engine}.log').open('w', encoding='utf8')
    code = 0
    try:
        print(f'inizio {time.strftime("%H:%M:%S")} {args.engine} {args.journey} cursore {hand.start} '
              f'scala {window.devicePixelRatio()} hwnd {hwnd} avviso {notice!r}', file=log, flush=True)
        pilot = modellazione.Pilot(args.engine, app, host, window, hand, args.out, args.journey, log)
        pilot.prepare()
        if args.dry:
            modellazione.facts(pilot)
        else:
            modellazione.run(pilot, args.journey)
    except Stop as stop:
        code = 3
        print(f'FERMATO: {stop}', file=log, flush=True)
        print(f'FERMATO: {stop}', flush=True)
    except Exception:
        code = 4
        text = traceback.format_exc()
        print('ERRORE\n'+text, file=log, flush=True)
        print('ERRORE\n'+text, flush=True)
    finally:
        hand.restore()
        print(f'fine {time.strftime("%H:%M:%S")} input {hand.inputs}', file=log, flush=True)
        log.close()
        print(f'fine {time.strftime("%H:%M:%S")} input {hand.inputs} codice {code}', flush=True)
        os._exit(code)


if __name__ == '__main__':
    main()
