"""The cards carried as tabs under the native mouse and keyboard, on their own desktop (R527, R317): without Alt the
middle of a card under the pointer takes the carried one beside itself, never as a tab; Alt pressed with the mouse
still makes it a tab, let go takes it back; the card dropped with Alt held lies behind the other one as a tab, and the
Alt of the carry does not open the menu, while Alt alone afterwards still does.

    python -m unittest quick.percorsi.test_native_linguette
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from quick.percorsi.test_native import _run

JOURNEY = r'''
import ctypes, json
from ctypes import wintypes
from PySide6.QtCore import QPointF

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.GetFocus.restype = wintypes.HWND
WM_SYSKEYDOWN, WM_SYSKEYUP, VK_MENU, VK_LMENU = 0x0104, 0x0105, 0x12, 0xA4


def alt(down):
    """Alt as Windows sends it: WM_SYSKEYDOWN and WM_SYSKEYUP, the key state set for this thread only."""
    state = (ctypes.c_ubyte*256)()
    user32.GetKeyboardState(state)
    state[VK_MENU] = state[VK_LMENU] = 0x80 if down else 0
    user32.SetKeyboardState(state)
    scan = user32.MapVirtualKeyW(VK_MENU, 0)
    lparam = 1 | (scan << 16) | (1 << 29) | ((0xC0000000) if not down else 0)
    user32.PostMessageW(user32.GetFocus() or native.hwnd, WM_SYSKEYDOWN if down else WM_SYSKEYUP, VK_MENU, lparam)
    spin(0.15)


seen = {}
wait_until(lambda: find(win, name='workspace') is not None, 60)
spin(1.0)
workspace = find(win, name='workspace')


def middle(name, share=0.5):
    card = find(win, name=name)
    q = card.mapToScene(QPointF(card.width()/2, card.height()*share))
    return q.x(), q.y()


handle = find(win, name='checksTitleDrag')
start = handle.mapToScene(QPointF(handle.width()/2, handle.height()/2))
native.move(start.x(), start.y())
native.press()
x, y = middle('leftPanel')
native.move(x, y, 16)
spin(0.5)
# after the dwell the card under the pointer has made room for the carried one: to its middle as it is now
x, y = middle('leftPanel')
native.move(x, y, 4)
spin(0.5)
seen['plain'] = workspace.property('candidate')
hint = find(win, name='tabHint')
seen['hint_plain'] = bool(hint and hint.property('shown'))
alt(True)
seen['alt'] = workspace.property('candidate')
seen['hint_alt'] = bool(hint and hint.property('shown'))
alt(False)
seen['let_go'] = workspace.property('candidate')
alt(True)
spin(0.5)
seen['grouping'] = workspace.property('grouping')
native.release()
spin(0.5)
alt(False)
spin(0.3)
checks = find(win, name='checksPanel')
seen['dropped'] = [checks.property('zone'), checks.property('stacked')]
seen['menu_after_carry'] = win.property('menuOpen')
alt(True)
alt(False)
spin(0.3)
seen['menu_alone'] = win.property('menuOpen')
alt(True)
alt(False)
print(json.dumps(seen, default=str))
'''


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class Tabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        ctl = folder / 'ctl'
        args = ['--ctl', str(ctl), '--no-calc', '--desktop', 'meridiana-collaudo-linguette', '--timeout', '100']
        code, output = _run('start', *args, timeout=140)
        if code:
            raise unittest.SkipTest(f'no program: {output[-300:]}')
        script = folder / 'journey.py'
        script.write_text(JOURNEY, encoding='utf-8')
        try:
            code, output = _run('run', '--ctl', str(ctl), str(script), timeout=300)
            lines = [line for line in output.splitlines() if line.startswith('{')]
            if not lines:
                raise AssertionError(f'the journey said nothing: {output[-800:]}')
            cls.seen = json.loads(lines[-1])
            if os.environ.get('MERIDIANA_NATIVE_DUMP'):
                print(cls.seen)
        finally:
            _run('run', '--ctl', str(ctl), '--stop', timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_without_alt_the_middle_of_a_card_is_beside_it(self):
        self.assertEqual(self.seen['plain'], 'left|project|after')
        self.assertTrue(self.seen['hint_plain'])

    def test_alt_pressed_and_let_go_with_the_mouse_still(self):
        self.assertEqual(self.seen['alt'], 'left|project|tab')
        self.assertFalse(self.seen['hint_alt'])
        self.assertEqual(self.seen['let_go'], 'left|project|after')
        self.assertTrue(self.seen['grouping'])

    def test_dropped_with_alt_it_is_a_tab_and_the_menu_stays_shut(self):
        self.assertEqual(self.seen['dropped'], ['left', False])
        self.assertFalse(self.seen['menu_after_carry'])
        self.assertTrue(self.seen['menu_alone'])


if __name__ == '__main__':
    unittest.main()
