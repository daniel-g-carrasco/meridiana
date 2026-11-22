"""R612: Meridio's tour in the real window (Daniel 14/11/2026, on the Linux laptop, in English).

1. «Il personaggio finisce dietro la barra degli strumenti» and 2. «l'evidenziatura resta dietro la linguetta della
   fase»: at every step the character is drawn whole (what he changes in the window's picture is his own square) and
   the ring is drawn whole around its target (what it changes is its own rectangle, its four sides).
5. «Premendo Previous Meridio non si sposta», and after it not with Next either: going 1 to 5, back to 3, on to 8,
   the character, the bubble and the ring stand at every step where they stood when the step was reached going on.
6. The keyboard on «Next» at every step: Enter alone walks the 13 steps, one at a press, to the end.
Synthetic events given to the window only (QTest's keys), offscreen.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from shiboken6 import delete

from _fixtures import capannone_rho
import _setup
from meridiana import i18n
from meridiana.gui.application import QuickWindow, create_app
from quick.meridio.support import KeyStore, Voice


class TourTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        i18n.setup('en')
        self.addCleanup(i18n.setup, 'it')
        temp = tempfile.TemporaryDirectory(prefix='r612-', ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        with patch('meridiana.gui.backend.assistant_chat.keys', KeyStore()), \
                patch('meridiana.gui.backend.voice.Voice', return_value=Voice()):
            self.host = QuickWindow(capannone_rho(), Path(temp.name), real_views=True, theme={'reducedMotion': True})
        self.window = self.host.window
        self.window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(self.window))
        self.layer = self.window.findChild(QObject, 'assistantLayer')
        _setup.wait_for(lambda: not self.layer.property('relocating'), 5000)

        def close():
            self.host.close()
            delete(self.host.engine)
        self.addCleanup(close)
        self.tour = self.host.parts.controllers['assistant_help']
        self.avatar = self.layer.findChild(QObject, 'assistantCharacter')
        self.bubble = self.layer.findChild(QObject, 'assistantBubble')
        self.ring = [k for k in self.layer.childItems() if k.objectName() == 'assistantSpotlight'][0]

    def settle(self):
        # the target is looked up a turn after the step (AssistantHost's tourTimer), then he slides there
        _setup.wait_for(lambda: self.layer.property('relocating'), 300)
        _setup.wait_for(lambda: not self.layer.property('relocating'), 3000)
        _setup.wait_for(lambda: False, 60)

    def places(self):
        a, b = self.avatar.mapToScene(QPointF(0, 0)), self.bubble.mapToScene(QPointF(0, 0))
        return (a.x(), a.y(), b.x(), b.y(), self.bubble.width(), self.bubble.height())

    def ring_on_target(self):
        # the ring around the step's item where that item is now (a step may open a panel that resizes the item of
        # another: the ring follows the item, it is not a place of its own)
        item, r = self.layer.property('highlightItem'), self.layer.property('highlightRect')
        if item is None:
            return 0.0
        t = item.mapToItem(self.layer, QPointF(0, 0))
        return max(abs(r.x() - t.x()), abs(r.y() - t.y()), abs(r.width() - item.width()), abs(r.height() - item.height()))

    def drawn(self, item):
        """The rectangle of the window's picture that `item` changes (its picture with it, less the one without)."""
        with_it = self.window.grabWindow()
        item.setVisible(False)
        without = self.window.grabWindow()
        item.setVisible(True)
        dpr = with_it.devicePixelRatio()
        xs, ys = [], []
        for y in range(with_it.height()):
            for x in range(with_it.width()):
                if with_it.pixel(x, y) != without.pixel(x, y):
                    xs.append(x)
                    ys.append(y)
        if not xs:
            return QRectF()
        return QRectF(min(xs) / dpr, min(ys) / dpr, (max(xs) - min(xs) + 1) / dpr, (max(ys) - min(ys) + 1) / dpr)

    def figure_box(self):
        """What the character draws now, in the scene (Character.extent): R619, the figure without the disc no longer
        fills his square, so "drawn whole" is his own drawing, white border and sign included."""
        from PySide6.QtCore import Q_RETURN_ARG, QMetaObject
        box = QMetaObject.invokeMethod(self.avatar, 'extent', Q_RETURN_ARG('QVariant'))
        return QRectF(self.avatar.mapToScene(box.topLeft()), box.size())

    def start(self):
        self.tour.startTour(False)
        _setup.wait_for(lambda: self.layer.property('opened'), 3000)
        self.settle()

    def test_places_depend_on_the_step_only(self):
        self.start()
        total = len(self.tour.property('tourSteps'))
        going = {0: self.places()}
        for i in range(1, total):
            self.tour.next()
            self.settle()
            going[i] = self.places()
        self.tour.pauseTour()
        self.start()
        # 1 to 5, back to 3, on to 8, as Daniel's «Previous» then «Next»
        path = [(self.tour.next, 1), (self.tour.next, 2), (self.tour.next, 3), (self.tour.next, 4),
                (self.tour.previous, 3), (self.tour.previous, 2),
                (self.tour.next, 3), (self.tour.next, 4), (self.tour.next, 5), (self.tour.next, 6), (self.tour.next, 7)]
        for step, index in path:
            step()
            self.settle()
            with self.subTest(step=index + 1, by=step.__name__):
                self.assertEqual(self.tour.property('tourIndex'), index)
                there, here = going[index], self.places()
                self.assertLessEqual(max(abs(a - b) for a, b in zip(there, here, strict=True)), 1.0,
                                     f'the place differs from the way on: {here} != {there}')
                self.assertLessEqual(self.ring_on_target(), 1.0, "the ring is not around the step's item")

    def test_the_character_and_the_ring_are_drawn_whole(self):
        self.start()
        total = len(self.tour.property('tourSteps'))
        for i in range(total):
            self.tour.goToStep(i)
            self.settle()
            with self.subTest(step=i + 1, what='character'):
                own = self.figure_box()
                seen = self.drawn(self.avatar)
                # what he changes is his own drawing, to a point at each side
                for a, b in ((seen.left(), own.left()), (seen.top(), own.top()), (seen.right(), own.right()),
                             (seen.bottom(), own.bottom())):
                    self.assertLessEqual(abs(a - b), 2, f'the character is not drawn whole: {seen} in {own}')
            if not self.ring.isVisible():
                continue
            with self.subTest(step=i + 1, what='ring'):
                own = QRectF(self.ring.mapToScene(QPointF(0, 0)), self.ring.size())
                seen = self.drawn(self.ring)
                for a, b in ((seen.left(), own.left()), (seen.top(), own.top()), (seen.right(), own.right()),
                             (seen.bottom(), own.bottom())):
                    self.assertLessEqual(abs(a - b), 2, f'the ring is not drawn whole: {seen} in {own}')

    def test_the_character_over_the_toolbar_is_drawn_whole(self):
        # Daniel's picture (a larger window: step 2 took him up to the bar): he stood over the bar of the tools, and only
        # his lower half showed under it. Put there by hand, over the tools of the phase, he is drawn whole.
        bar = self.window.findChild(QObject, 'phaseBar')
        at = bar.mapToItem(self.layer, QPointF(bar.width() / 2, bar.height() / 2))
        self.layer.setProperty('avatarX', at.x() - 23)
        self.layer.setProperty('avatarY', at.y() - 23)
        _setup.wait_for(lambda: False, 100)
        own = self.figure_box()
        seen = self.drawn(self.avatar)
        for a, b in ((seen.left(), own.left()), (seen.top(), own.top()), (seen.right(), own.right()),
                     (seen.bottom(), own.bottom())):
            self.assertLessEqual(abs(a - b), 2, f'the character is not drawn whole over the bar: {seen} in {own}')

    def test_enter_alone_walks_the_tour(self):
        self.start()
        total = len(self.tour.property('tourSteps'))
        for i in range(total):
            with self.subTest(step=i + 1):
                self.assertTrue(self.tour.property('tourActive'))
                self.assertEqual(self.tour.property('tourIndex'), i)
                _setup.wait_for(lambda: self.window.activeFocusItem() is not None
                                and self.window.activeFocusItem().objectName() == 'guideNext', 2000)
                focus = self.window.activeFocusItem()
                self.assertEqual(focus.objectName() if focus else None, 'guideNext', 'the keyboard is not on Next')
            QTest.keyClick(self.window, Qt.Key.Key_Return)
            self.settle()
        self.assertFalse(self.tour.property('tourActive'), 'Enter at the last step ends the tour')

    def test_enter_or_space_held_down_goes_on_once(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        self.start()
        for step, (key, text) in enumerate(((Qt.Key.Key_Return, '\r'), (Qt.Key.Key_Space, ' ')), start=1):
            with self.subTest(key=key.name):
                _setup.wait_for(lambda: self.window.activeFocusItem() is not None
                                and self.window.activeFocusItem().objectName() == 'guideNext', 2000)
                press = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, text, False)
                again = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, text, True)
                release = QKeyEvent(QEvent.Type.KeyRelease, key, Qt.KeyboardModifier.NoModifier, text, False)
                for event in (press, again, again, again, release):
                    self.app.sendEvent(self.window, event)
                self.settle()
                self.assertEqual(self.tour.property('tourIndex'), step, 'held down, the key went on more than once')

    def test_tab_leaves_next_and_a_click_elsewhere_keeps_the_keyboard(self):
        self.start()
        _setup.wait_for(lambda: self.window.activeFocusItem() is not None
                        and self.window.activeFocusItem().objectName() == 'guideNext', 2000)
        QTest.keyClick(self.window, Qt.Key.Key_Tab)
        with self.subTest(what='Tab'):
            self.assertNotEqual(self.window.activeFocusItem().objectName(), 'guideNext', 'Tab is held on Next')
        field = self.window.findChild(QObject, 'searchField') or self.window.findChild(QObject, 'commandSearch')
        if field is not None and field.isVisible():
            field.forceActiveFocus()
            _setup.wait_for(lambda: False, 200)
            with self.subTest(what='a field chosen elsewhere'):
                self.assertTrue(field.hasActiveFocus(), 'the tour took the keyboard back without a change of step')


if __name__ == '__main__':
    unittest.main()
