"""Drive a real Meridiana window with native Windows messages, never with Qt events.

The messages enter Qt through its Windows platform plugin (WM_MOUSEMOVE and the
others, posted to the HWND under the point), the same path as a physical mouse.
QTest and QCoreApplication.sendEvent skip that path: see docs/quick/collaudo/.

The window runs on a separate Windows desktop, created for the purpose, so the
person using the PC keeps mouse, keyboard and focus: nothing is visible and
nothing can steal input. On that desktop Qt's own hit test (WindowFromPoint) is
true, which a WS_EX_TRANSPARENT window on the visible desktop cannot give: Qt
skips such a window and drops every move without buttons as "not over us".

    start: python tools/quick_native_input.py start --engine quick --ctl <dir> [--project <file>]
    run:   python tools/quick_native_input.py run --ctl <dir> <script.py or - for stdin>
    stop:  python tools/quick_native_input.py run --ctl <dir> --stop

A script runs inside the program, with these names: app, host, win, native, spin,
wait_until, grab, items, popups, find, visible_text, out. print() goes to the
caller. Tests use `run_journey` in tests/quick/percorsi/native_journey.py.
"""
import argparse
import contextlib
import ctypes
from ctypes import wintypes
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x0200, 0x0201, 0x0202, 0x0203
WM_RBUTTONDOWN, WM_RBUTTONUP, WM_MBUTTONDOWN, WM_MBUTTONUP = 0x0204, 0x0205, 0x0207, 0x0208
WM_MOUSEWHEEL, WM_MOUSELEAVE, WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x020A, 0x02A3, 0x0100, 0x0101, 0x0102
MK_LBUTTON, MK_RBUTTON, MK_MBUTTON = 1, 2, 16
_MK = {'shift': 0x0004, 'ctrl': 0x0008}       # MK_SHIFT, MK_CONTROL of the mouse messages
_LEFT_VARIANT = {'shift': 0xA0, 'ctrl': 0xA2, 'alt': 0xA4}
VK = {'esc': 0x1B, 'enter': 0x0D, 'tab': 0x09, 'space': 0x20, 'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
      'delete': 0x2E, 'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'f1': 0x70, 'z': 0x5A, 'y': 0x59, 'a': 0x41,
      ',': 0xBC, '.': 0xBE, '-': 0xBD}      # VK_OEM_COMMA, PERIOD, MINUS: a measure typed with its comma (r20)

user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.WindowFromPoint.argtypes = (wintypes.POINT,)
user32.WindowFromPoint.restype = wintypes.HWND
user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
user32.ScreenToClient.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
user32.GetCapture.restype = wintypes.HWND
user32.SetFocus.argtypes = (wintypes.HWND,)
user32.SetFocus.restype = wintypes.HWND
user32.SetActiveWindow.argtypes = (wintypes.HWND,)
user32.SetActiveWindow.restype = wintypes.HWND
user32.CreateDesktopW.restype = wintypes.HANDLE
user32.CreateDesktopW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID)
user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
user32.MapVirtualKeyW.restype = wintypes.UINT


def _lparam(x, y):
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


from PySide6.QtCore import QAbstractNativeEventFilter  # noqa: E402


class _LeaveFilter(QAbstractNativeEventFilter):
    allow = False

    def nativeEventFilter(self, kind, message):
        if wintypes.MSG.from_address(int(message)).message == WM_MOUSELEAVE and not self.allow:
            return True, 0
        return False, 0


class NativeInput:
    """A mouse and a keyboard made of window messages, for one top-level window.

    Coordinates are logical pixels of that window. The target HWND is what the
    system would pick: the capture if there is one, otherwise the window under
    the point, which also covers native popups such as a QMenu.
    """

    def __init__(self, window, app):
        self.window, self.app = window, app
        self.hwnd = int(window.winId())
        self.at = (0, 0)
        self.buttons = 0
        self.longest_turn = 0.0
        # Qt asks Windows for WM_MOUSELEAVE (TrackMouseEvent). The system
        # cursor is not on this desktop, so Windows answers at once, and every
        # posted move would become Enter + Leave. Only mouse_left() may pass.
        self.leave_filter = _LeaveFilter()
        app.installNativeEventFilter(self.leave_filter)

    def dpr(self):
        return float(self.window.devicePixelRatio()) if hasattr(self.window, 'devicePixelRatio') else 1.0

    def spin(self, ms):
        """Run the event loop for ms milliseconds, keeping the longest single turn of the GUI thread."""
        end = time.perf_counter() + ms/1000
        while time.perf_counter() < end:
            before = time.perf_counter()
            self.app.processEvents()
            self.longest_turn = max(self.longest_turn, time.perf_counter()-before)
            time.sleep(0.002)

    def activate(self):
        """Give the window keyboard focus on its own desktop. It is the only way Esc reaches Qt's shortcut map."""
        user32.SetActiveWindow(self.hwnd)
        user32.SetFocus(self.hwnd)
        self.spin(60)

    def _screen(self, x, y):
        scale = self.dpr()
        point = wintypes.POINT(round(x*scale), round(y*scale))
        user32.ClientToScreen(self.hwnd, ctypes.byref(point))
        return point

    def _post(self, message, wparam, x, y, *, screen_lparam=False):
        point = self._screen(x, y)
        target = user32.GetCapture() or user32.WindowFromPoint(point) or self.hwnd
        # Never post to another program. On the visible desktop the window under
        # the point can be someone else's: refuse rather than click into it.
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(target, ctypes.byref(owner))
        if owner.value != os.getpid():
            raise RuntimeError(f'The window under ({x}, {y}) belongs to process {owner.value}: nothing posted. '
                               'Run on the hidden desktop (the start command).')
        lparam = _lparam(point.x, point.y)
        if not screen_lparam:
            local = wintypes.POINT(point.x, point.y)
            user32.ScreenToClient(target, ctypes.byref(local))
            lparam = _lparam(local.x, local.y)
        if not user32.PostMessageW(target, message, wparam, lparam):
            raise ctypes.WinError(ctypes.get_last_error())

    def move(self, x, y, steps=8, gap_ms=12):
        """Move in small steps from the last point, as a hand does."""
        x0, y0 = self.at
        for i in range(1, steps+1):
            self._post(WM_MOUSEMOVE, self.buttons, x0+(x-x0)*i/steps, y0+(y-y0)*i/steps)
            self.spin(gap_ms)
        self.at = (x, y)

    def jump(self, x, y):
        self._post(WM_MOUSEMOVE, self.buttons, x, y)
        self.at = (x, y)
        self.spin(10)

    def press(self, button='left'):
        down, _, mask = _BUTTONS[button]
        self.buttons |= mask
        self._post(down, self.buttons, *self.at)
        self.spin(16)

    def release(self, button='left'):
        _, up, mask = _BUTTONS[button]
        self.buttons &= ~mask
        self._post(up, self.buttons, *self.at)
        self.spin(16)

    def click(self, x=None, y=None, button='left', steps=8, settle=120, modifiers=()):
        """A click; with `modifiers` ('shift', 'ctrl') held as a hand holds them (R529): the key state of this thread
        (as `key`) and the MK_ flags of the mouse messages, both read by Qt."""
        if x is not None:
            self.move(x, y, steps)
        state = (ctypes.c_ubyte*256)()
        flags = sum(_MK[mod] for mod in modifiers)
        if modifiers:
            user32.GetKeyboardState(state)
            for mod in modifiers:
                state[VK[mod]] = state[_LEFT_VARIANT[mod]] = 0x80
            user32.SetKeyboardState(state)
            self.buttons |= flags
        self.press(button)
        self.spin(40)
        self.release(button)
        if modifiers:
            self.buttons &= ~flags
            for mod in modifiers:
                state[VK[mod]] = state[_LEFT_VARIANT[mod]] = 0
            user32.SetKeyboardState(state)
        self.spin(settle)

    def double_click(self, x, y):
        self.move(x, y)
        self.press()
        self.release()
        self.spin(30)
        self._post(WM_LBUTTONDBLCLK, MK_LBUTTON, x, y)
        self.spin(16)
        self._post(WM_LBUTTONUP, 0, x, y)
        self.spin(100)

    def drag(self, x0, y0, x1, y1, button='left', steps=14):
        self.move(x0, y0)
        self.press(button)
        self.move(x1, y1, steps)
        self.release(button)
        self.spin(100)

    def wheel(self, x, y, notches=1):
        self.move(x, y, 3)
        self._post(WM_MOUSEWHEEL, (int(120*notches) & 0xFFFF) << 16, x, y, screen_lparam=True)
        self.spin(80)

    def mouse_left(self):
        """The window is told the pointer has gone, as Windows does when it leaves."""
        target = user32.GetCapture() or self.hwnd
        self.leave_filter.allow = True
        user32.PostMessageW(target, WM_MOUSELEAVE, 0, 0)
        self.spin(40)
        self.leave_filter.allow = False

    def key(self, name, modifiers=(), settle=120):
        """Press and release one key. A posted message does not update the key state Qt reads for the
        modifiers, so they are set for this thread only (SetKeyboardState never reaches other programs)."""
        vk = VK[name] if isinstance(name, str) and name in VK else ord(name.upper()) if isinstance(name, str) else name
        scan = user32.MapVirtualKeyW(vk, 0)
        target = user32.GetFocus() or self.hwnd
        state = (ctypes.c_ubyte*256)()
        if modifiers:
            user32.GetKeyboardState(state)
            for mod in modifiers:       # Qt reads the left and right variants, not only the generic key
                state[VK[mod]] = state[_LEFT_VARIANT[mod]] = 0x80
            user32.SetKeyboardState(state)
        user32.PostMessageW(target, WM_KEYDOWN, vk, (scan << 16) | 1)
        self.spin(16)
        user32.PostMessageW(target, WM_KEYUP, vk, (scan << 16) | 0xC0000001)
        self.spin(16)
        if modifiers:
            for mod in modifiers:
                state[VK[mod]] = state[_LEFT_VARIANT[mod]] = 0
            user32.SetKeyboardState(state)
        self.spin(settle)

    def type_text(self, text):
        for char in text:
            self.key(char, settle=10)


_BUTTONS = {'left': (WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON), 'right': (WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON),
            'middle': (WM_MBUTTONDOWN, WM_MBUTTONUP, MK_MBUTTON)}


# Looking at a Quick window.
def items(window):
    pending = [window.contentItem()]
    while pending:
        item = pending.pop(0)
        pending.extend(item.childItems())
        yield item


def _effectively_visible(item):
    return item.isVisible() and item.width() > 0 and item.height() > 0


def popups(window):
    """The popup items currently shown in the overlay, innermost text included. Only the overlay is looked through:
    the whole window is some 15 000 items, and a walk in Python would hide what is being timed."""
    root = window.contentItem()
    overlay = next((item for item in root.childItems() if item.metaObject().className().startswith('QQuickOverlay')), None)
    pool = overlay.childItems() if overlay is not None else items(window)
    return [item for item in pool if item.metaObject().className().startswith('QQuickPopupItem') and _effectively_visible(item)]


def visible_text(item):
    out, pending = [], [item]
    while pending:
        current = pending.pop(0)
        pending.extend(current.childItems())
        text = current.property('text') if current.isVisible() else None
        if isinstance(text, str) and text.strip():
            out.append(text.strip())
    return out


def center(item, window=None):
    from PySide6.QtCore import QPointF
    point = item.mapToScene(QPointF(item.width()/2, item.height()/2))
    return point.x(), point.y()


def find(window, *, text=None, name=None, tip=None, within=None):
    """The first visible item with this objectName, text or tooltip text."""
    for item in items(within or window) if within is None else _subtree(within):
        if not _effectively_visible(item):
            continue
        if name is not None and item.objectName() == name:
            return item
        if text is not None and str(item.property('text') or '').replace('&', '').split('\t')[0].strip() == text:
            return item
        if tip is not None and str(item.property('toolTipText') or item.property('tip') or '').split('\t')[0].strip() == tip:
            return item
    return None


def _subtree(item):
    pending = [item]
    while pending:
        current = pending.pop(0)
        pending.extend(current.childItems())
        yield current


# The hidden desktop.
class _StartupInfo(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD),
                ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD), ('lpReserved2', ctypes.c_void_p),
                ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE), ('dwProcessId', wintypes.DWORD),
                ('dwThreadId', wintypes.DWORD)]


def launch_on_hidden_desktop(argv, *, log, desktop='meridiana-collaudo', env=None, cwd=None):
    """Start a process on its own Windows desktop. Returns (process handle, pid)."""
    import msvcrt
    import subprocess
    GENERIC_ALL = 0x10000000
    handle = user32.CreateDesktopW(desktop, None, None, 0, GENERIC_ALL, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    startup = _StartupInfo()
    startup.cb = ctypes.sizeof(startup)
    startup.lpDesktop = 'WinSta0\\' + desktop
    out = open(log, 'wb')
    os_handle = msvcrt.get_osfhandle(out.fileno())
    kernel32.SetHandleInformation(wintypes.HANDLE(os_handle), 1, 1)
    startup.dwFlags = 0x100
    startup.hStdOutput = startup.hStdError = os_handle
    info = _ProcessInfo()
    block = ''.join(f'{k}={v}\0' for k, v in (env if env is not None else os.environ).items()) + '\0'
    if not kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(subprocess.list2cmdline(argv)), None, None, True,
                                   0x00000400 | 0x08000000, ctypes.create_unicode_buffer(block), str(cwd) if cwd else None,
                                   ctypes.byref(startup), ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    return info.hProcess, info.dwProcessId


# The program side.
def _quick_host(args, work):
    from PySide6.QtCore import QTimer
    from meridiana import model
    from meridiana.quick.app import QuickWindow, create_app
    from meridiana.quick.sample import recorded_weather
    app = create_app()
    project, notice = model.Project.load(args.project)
    # The same steps as meridiana.quick.app.main, on a temporary profile.
    recorded_weather(project, work)
    host = QuickWindow(project, work, real_views=True, theme={'theme': args.theme} if args.theme else None)
    host.window.resize(args.width, args.height)
    host.window.setPosition(0, 0)
    host.window.show()
    if not args.no_calc:
        QTimer.singleShot(0, host.bridge.recompute)
    return app, host, host.window


def _widgets_host(args, work):
    import unittest
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'tests'))
    import _setup
    from meridiana import config, i18n, model
    from meridiana.quick.sample import recorded_weather
    from meridiana.ui.theme import load_fonts
    app = _setup.qt_or_skip()
    i18n.setup('it')
    load_fonts('plex')
    project, notice = model.Project.load(args.project)
    case = unittest.TestCase()
    cfg = config.Config(theme=args.theme or 'light', font='plex', accent='indigo', backgrounds='grey', background='auto' if args.keep_maps else 'none',
                        network_tiles=args.keep_maps, network_pvgis=False, check_updates=False, assistant_animated=False)
    window = _setup.window(case, project, cfg, size=[args.width, args.height])
    recorded_weather(project, case.paths.cache)
    window.show()
    window.move(0, 0)
    case_holder = type('Host', (), {'case': case, 'window': window})()
    return app, case_holder, window


def serve(args):
    ctl = Path(args.ctl)
    ctl.mkdir(parents=True, exist_ok=True)
    work = Path(args.cache) if args.cache else Path(tempfile.mkdtemp(prefix='meridiana-native-'))
    work.mkdir(parents=True, exist_ok=True)
    project_copy = work/Path(args.project).name
    if Path(args.project).resolve() != project_copy.resolve():
        shutil.copy2(args.project, project_copy)
    args.project = project_copy
    app, host, window = (_quick_host if args.engine == 'quick' else _widgets_host)(args, work)
    native = NativeInput(window, app)
    native.spin(500)
    native.activate()
    # R529: the thread's key state can start with Shift down (as it was on the visible desktop when the program
    # started) and no key-up ever comes on this desktop: every click would be a Shift+click. Start from none.
    state = (ctypes.c_ubyte*256)()
    user32.GetKeyboardState(state)
    for vk in (0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5):
        state[vk] = 0
    user32.SetKeyboardState(state)

    def spin(seconds):
        native.spin(seconds*1000)

    def wait_until(condition, seconds=30):
        start = time.perf_counter()
        while time.perf_counter()-start < seconds:
            if condition():
                return time.perf_counter()-start
            app.processEvents()
            time.sleep(0.002)
        return None

    def grab(name):
        image = window.grabWindow() if args.engine == 'quick' else window.grab().toImage()
        path = ctl/name
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path))
        return str(path)

    names = dict(app=app, host=host, win=window, native=native, spin=spin, wait_until=wait_until, grab=grab,
                 items=items, popups=popups, find=find, visible_text=visible_text, center=center, out=ctl,
                 user32=user32, QT=__import__('PySide6.QtCore').QtCore)
    (ctl/'ready').write_text(str(os.getpid()), encoding='utf-8')
    index = 0
    last = time.time()
    while time.time()-last < args.idle_exit:
        script = ctl/f'cmd-{index}.py'
        if not script.exists():
            app.processEvents()
            time.sleep(0.005)
            continue
        try:
            code = script.read_text(encoding='utf-8')
        except PermissionError:     # the caller is still renaming it, or an antivirus has it open
            app.processEvents()
            time.sleep(0.02)
            continue
        if code.strip() == 'STOP':
            break
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            try:
                exec(compile(code, str(script), 'exec'), names)
            except BaseException:
                traceback.print_exc(file=buffer)
        partial = ctl/f'res-{index}.tmp'
        partial.write_text(buffer.getvalue(), encoding='utf-8')
        partial.rename(ctl/f'res-{index}.txt')
        index += 1
        last = time.time()
    if args.engine == 'quick':
        host.close()
    os._exit(0)


def start(args):
    ctl = Path(args.ctl)
    ctl.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, str(Path(__file__).resolve()), 'serve', '--engine', args.engine, '--ctl', str(ctl),
            '--project', str(args.project), '--width', str(args.width), '--height', str(args.height),
            '--idle-exit', str(args.idle_exit)]
    if args.theme:
        argv += ['--theme', args.theme]
    if args.no_calc:
        argv.append('--no-calc')
    if args.keep_maps:
        argv.append('--keep-maps')
    if args.cache:
        argv += ['--cache', str(args.cache)]
    handle, pid = launch_on_hidden_desktop(argv, log=ctl/'server.log', desktop=args.desktop)
    deadline = time.time()+args.timeout
    while time.time() < deadline and not (ctl/'ready').exists():
        if kernel32.WaitForSingleObject(handle, 200) == 0:
            raise SystemExit('The program ended before it was ready:\n'+(ctl/'server.log').read_text(errors='replace')[-3000:])
    if not (ctl/'ready').exists():
        raise SystemExit('Not ready in time')
    print('ready pid', pid)


def run_script(args):
    ctl = Path(args.ctl)
    index = 0
    while (ctl/f'cmd-{index}.py').exists():
        index += 1
    code = 'STOP' if args.stop else (sys.stdin.read() if args.script == '-' else Path(args.script).read_text(encoding='utf-8'))
    partial = ctl/f'cmd-{index}.tmp'
    partial.write_text(code, encoding='utf-8')
    partial.rename(ctl/f'cmd-{index}.py')
    if args.stop:
        return
    result = ctl/f'res-{index}.txt'
    deadline = time.time()+args.timeout
    while time.time() < deadline and not result.exists():
        time.sleep(0.05)
    if not result.exists():
        raise SystemExit('No answer in time: the program is busy or stopped. GUI thread blocked?')
    sys.stdout.write(result.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('start', 'serve'):
        command = sub.add_parser(name)
        command.add_argument('--engine', choices=('quick', 'widgets'), default='quick')
        command.add_argument('--ctl', required=True)
        home = Path(os.environ.get('MERIDIANA_REAL_HOME') or Path.home())
        command.add_argument('--project', default=str(home/'dev/meridiana-prove/Prova capannone Rho.meridiana'))
        command.add_argument('--width', type=int, default=1600)
        command.add_argument('--height', type=int, default=960)
        command.add_argument('--theme', choices=('light', 'dark'))
        command.add_argument('--no-calc', action='store_true')
        command.add_argument('--keep-maps', action='store_true')
        command.add_argument('--idle-exit', type=int, default=1800)
        command.add_argument('--desktop', default='meridiana-collaudo')
        command.add_argument('--cache', help='The folder of the program\'s cache, kept between two starts')
        command.add_argument('--timeout', type=int, default=120)
    run = sub.add_parser('run')
    run.add_argument('--ctl', required=True)
    run.add_argument('script', nargs='?', default='-')
    run.add_argument('--stop', action='store_true')
    run.add_argument('--timeout', type=int, default=280)
    args = parser.parse_args()
    {'start': start, 'serve': serve, 'run': run_script}[args.command](args)


if __name__ == '__main__':
    main()
