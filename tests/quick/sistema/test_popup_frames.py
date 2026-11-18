"""R476, R480, R491: a menu comes in without a flicker and stays still, its button follows it; read frame by frame
(offscreen, the basic render loop)."""

import os
import time
import unittest

import _setup
from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QUrl
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

from meridiana.quick.backend.controls import install_controls

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

SCENE = b'''import QtQuick
import Meridiana.Controls as M
Rectangle { width: 420; height: 420; color: "#808080"
    M.Button { id: title; objectName: "title"; text: "File"; x: 20; y: 10; tip: "Il menu dei file e dei progetti"
        menu: menu
        M.Menu { id: menu; objectName: "menu"
            M.MenuItem { objectName: "first"; text: "Nuovo progetto" } M.MenuItem { text: "Apri..." } M.MenuItem { text: "Salva" }
            M.MenuItem { objectName: "long"; text: "Salva con nome una copia del progetto" } M.MenuItem { text: "Esporta" }
            M.MenuItem { text: "Esci" } } }
    Rectangle { objectName: "elsewhere"; x: 300; y: 360; width: 100; height: 40; color: "#a0a0a0" } }'''


class MenuFramesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def scene(self):
        engine = QQmlEngine()
        install_controls(engine, dict(theme='light', reducedMotion=False))
        component = QQmlComponent(engine)
        component.setData(SCENE, QUrl())
        root = component.create()
        self.assertIsNotNone(root, [e.toString() for e in component.errors()])
        window = QQuickWindow()
        window.resize(420, 420)
        root.setParentItem(window.contentItem())
        window.show()
        QTest.qWait(200)
        self.addCleanup(window.close)
        self._keep = (engine, component, root, window)
        title = root.findChild(QObject, 'title')
        return window, root, title, title.findChild(QObject, 'menu')

    def mouse(self, window, kind, pos, buttons):
        button = Qt.MouseButton.LeftButton if kind != QEvent.Type.MouseMove else Qt.MouseButton.NoButton
        self.app.sendEvent(window, QMouseEvent(kind, pos, pos, QPointF(window.mapToGlobal(pos.toPoint())), button,
                                               buttons, Qt.KeyboardModifier.NoModifier))

    def click(self, window, item):
        pos = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        self.mouse(window, QEvent.Type.MouseMove, pos, Qt.MouseButton.NoButton)
        self.mouse(window, QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton)
        self.mouse(window, QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.NoButton)

    def record(self, window, menu, frames):
        def frame():
            frames.append((time.perf_counter(), menu.property('height'), menu.property('implicitHeight'),
                           menu.property('width'), menu.property('opacity')))
        window.frameSwapped.connect(frame, Qt.ConnectionType.DirectConnection)
        self.addCleanup(lambda: window.frameSwapped.disconnect(frame))

    def check_reveal(self, frames, final, attempt):
        shown = [f for f in frames if f[4] > 0]
        self.assertTrue(shown, attempt)
        self.assertLessEqual(shown[0][4], .5, f'{attempt}: the first frame already opaque')
        self.assertEqual({f[3] for f in shown}, {final[1]}, f'{attempt}: the width changed while it came')
        self.assertEqual({f[1] for f in shown}, {final[0]}, f'{attempt}: its height changed while it came')
        opacities = [f[4] for f in shown]
        self.assertEqual(opacities, sorted(opacities), f'{attempt}: it went back')
        self.assertGreaterEqual(len([o for o in opacities if o < 1]), 3, f'{attempt}: a jump, not a fade')
        self.assertEqual(opacities[-1], 1.0)

    def test_r476_a_menu_fades_in_from_nothing_with_its_size_known_before_the_first_frame(self):
        window, _root, _title, menu = self.scene()
        frames = []
        self.record(window, menu, frames)
        asked = []
        menu.aboutToShow.connect(lambda: asked.append((menu.property('implicitHeight'), menu.property('implicitWidth'))))
        for attempt in range(2):          # the first opening, when nothing of it was ever measured, and the next
            frames.clear()
            menu.setProperty('visible', True)
            QTest.qWait(350)
            final = (menu.property('implicitHeight'), menu.property('implicitWidth'))
            self.assertEqual(asked[-1], final, f'opening {attempt}: the menu was measured after it showed')
            self.check_reveal(frames, final, f'opening {attempt}')
            menu.setProperty('visible', False)
            QTest.qWait(150)

    def test_r476_under_load_a_slow_frame_slows_the_fade_and_does_not_skip_it(self):
        """The red of the suite (148 of 182 px at the first frame, green alone): the frames after the first came later
        than the time of the roll, as when the GUI thread has other work; here 250 ms of it after the first frame."""
        window, _root, _title, menu = self.scene()
        frames = []
        self.record(window, menu, frames)
        stalled = []

        def stall():
            if not stalled and menu.property('visible'):
                stalled.append(True)
                time.sleep(.25)
        window.frameSwapped.connect(stall, Qt.ConnectionType.DirectConnection)
        self.addCleanup(lambda: window.frameSwapped.disconnect(stall))
        menu.setProperty('visible', True)
        QTest.qWait(700)
        self.assertTrue(stalled)
        self.check_reveal(frames, (menu.property('implicitHeight'), menu.property('implicitWidth')), 'under load')

    def test_r480_the_button_stays_pressed_while_its_menu_is_open_and_a_second_click_closes_it(self):
        window, root, title, menu = self.scene()
        self.click(window, title)
        QTest.qWait(250)
        self.assertTrue(menu.property('visible'))
        self.assertTrue(title.property('menuShown'))
        self.assertEqual(menu.property('opener'), title)
        # under the button
        self.assertAlmostEqual(menu.property('y'), title.height(), delta=1)
        # pressed while open, the pointer gone elsewhere too
        self.mouse(window, QEvent.Type.MouseMove, QPointF(350, 300), Qt.MouseButton.NoButton)
        QTest.qWait(50)
        self.assertTrue(title.property('menuShown'))
        self.click(window, title)
        QTest.qWait(150)
        self.assertFalse(menu.property('visible'), 'the second click closes it')
        QTest.qWait(450)
        self.click(window, title)
        QTest.qWait(150)
        self.assertTrue(menu.property('visible'), 'and the third opens it again')
        self.app.sendEvent(window, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
        self.app.sendEvent(window, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
        QTest.qWait(150)
        self.assertFalse(menu.property('visible'), 'Esc closes it')
        QTest.qWait(450)
        self.click(window, title)
        QTest.qWait(150)
        self.assertTrue(menu.property('visible'))
        self.click(window, root.findChild(QObject, 'elsewhere'))
        QTest.qWait(150)
        self.assertFalse(menu.property('visible'), 'a click outside closes it')
        self.assertFalse(title.property('menuShown'))

    def test_r476_from_the_press_the_button_does_not_blink_and_no_tooltip_comes(self):
        """Daniel: the flicker is at the press, before the menu: the button's state frame by frame from the press."""
        window, _root, title, menu = self.scene()
        pos = title.mapToScene(QPointF(title.width() / 2, title.height() / 2))
        self.mouse(window, QEvent.Type.MouseMove, pos, Qt.MouseButton.NoButton)
        QTest.qWait(900)                                     # the tooltip shown, as when one rests on a button
        states = []

        def frame():
            tips = [t for t in title.findChildren(QObject) if t.objectName() == 'controlTip']
            states.append((bool(title.property('down') or title.property('menuShown')),
                           any(t.property('visible') and t.property('opacity') > 0 and not t.property('held') for t in tips)))
        window.frameSwapped.connect(frame, Qt.ConnectionType.DirectConnection)
        self.addCleanup(lambda: window.frameSwapped.disconnect(frame))
        self.mouse(window, QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton)
        QTest.qWait(60)
        self.mouse(window, QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.NoButton)
        QTest.qWait(300)
        self.assertTrue(menu.property('visible'))
        self.assertTrue(states and all(s[0] for s in states), f'the pressed ground went off in a frame: {states}')
        # the tooltip shown before the press goes at once (no fade under the menu that comes) and does not come back
        self.assertFalse(any(s[1] for s in states), f'a tooltip in a frame after the press: {states}')

    def test_r491_an_open_menu_keeps_its_width_when_an_entry_changes(self):
        window, root, title, menu = self.scene()
        self.click(window, title)
        QTest.qWait(250)
        width, x = menu.property('width'), menu.property('x')
        root.findChild(QObject, 'long').setProperty('text', 'Salva')     # the longest entry gets short
        QTest.qWait(100)
        self.assertEqual((menu.property('width'), menu.property('x')), (width, x))
        menu.setProperty('visible', False)
        QTest.qWait(100)


if __name__ == '__main__':
    unittest.main()
