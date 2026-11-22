"""R705 (Daniel 17/11/2026: «vorrei aggiungere la possibilità, come nel widget, di scorrere tra le fasi con la rotella
del mouse quando ho il puntatore sulle linguette»). As a QTabBar: the wheel up goes to the phase before, down to the one
after, no wrap at the ends; a high-resolution wheel's small steps add up to a notch; two fingers on a touchpad
change nothing (a brush over the tabs would change phase by mistake); the wheel elsewhere in the header changes nothing.

    python -m unittest quick.shell.test_rotella_fasi_r705
"""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QInputDevice, QPointingDevice, QWheelEvent

import _setup
from _fixtures import capannone
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import pump

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def setUpModule():
    _setup.keep_global_state()


class WheelOverThePhaseTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone(), Path(cls.folder.name), theme={'theme': 'light', 'reducedMotion': True})
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1600, 900)
        pump(300)
        cls.touchpad = QPointingDevice('test touchpad', 9002, QInputDevice.DeviceType.TouchPad,
                                       QPointingDevice.PointerType.Finger,
                                       QInputDevice.Capability.Position | QInputDevice.Capability.Scroll, 5, 0)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.win.showPhase('model')
        pump(300)
        self.assertEqual(self.win.property('phase'), 'model')

    def item(self, name):
        pending = [self.win.contentItem()]
        while pending:
            node = pending.pop()
            if node.objectName() == name:
                return node
            pending.extend(node.childItems())
        raise AssertionError(name)

    def at(self, name):
        tab = self.item(name)
        return tab.mapToScene(QPointF(tab.width() / 2, tab.height() / 2))

    def wheel(self, at, dy, phase=Qt.ScrollPhase.NoScrollPhase, device=None):
        glob = QPointF(self.win.mapToGlobal(at.toPoint()))
        args = (at, glob, QPoint(0, dy // 4 if device else 0), QPoint(0, dy), Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier, phase, False)
        if device is not None:
            args += (Qt.MouseEventSource.MouseEventNotSynthesized, device)
        self.app.sendEvent(self.win, QWheelEvent(*args))
        pump(120)

    def test_down_next_up_previous_no_wrap(self):
        tab = self.at('modelTab')
        self.wheel(tab, -120)
        self.assertEqual(self.win.property('phase'), 'plant')
        self.wheel(tab, -120)
        self.assertEqual(self.win.property('phase'), 'production')
        self.wheel(tab, 120)
        self.assertEqual(self.win.property('phase'), 'plant')
        self.wheel(tab, 120)
        self.wheel(tab, 120)                       # already the first: it stays
        self.assertEqual(self.win.property('phase'), 'model')

    def test_a_high_resolution_wheel_adds_its_small_steps_up_to_a_notch(self):
        tab = self.at('modelTab')
        for _ in range(3):
            self.wheel(tab, -30)
        self.assertEqual(self.win.property('phase'), 'model', 'three quarters of a notch: not yet')
        self.wheel(tab, -30)
        self.assertEqual(self.win.property('phase'), 'plant', 'a whole notch: the next phase')

    def test_two_fingers_on_a_touchpad_change_no_phase(self):
        tab = self.at('modelTab')
        self.wheel(tab, 0, Qt.ScrollPhase.ScrollBegin, self.touchpad)
        for _ in range(8):
            self.wheel(tab, -60, Qt.ScrollPhase.ScrollUpdate, self.touchpad)
        self.wheel(tab, 0, Qt.ScrollPhase.ScrollEnd, self.touchpad)
        self.assertEqual(self.win.property('phase'), 'model', 'brushing the tabs with two fingers: no change')

    def test_the_wheel_off_the_tabs_changes_no_phase(self):
        bar = self.item('phaseBar')
        below = bar.mapToScene(QPointF(bar.width() / 3, bar.height() - 4))    # over the tools, under the tabs
        self.wheel(below, -120)
        self.assertEqual(self.win.property('phase'), 'model')


if __name__ == '__main__':
    unittest.main()
