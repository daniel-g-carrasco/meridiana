"""The track of segments (R322, B1): the choice, the rectangle that slides, the keys, less motion, a QTabBar on it."""
import unittest

import _setup
from PySide6.QtCore import QEasingCurve, QRectF, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QTabBar

setUpModule = _setup.keep_global_state


class SegmentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui import motion
        self.addCleanup(motion.set_reduced, motion.reduced())
        motion.set_reduced(False)

    def track(self, exclusive=True):
        from meridiana.ui.segments import Segments
        track = Segments(exclusive)
        self.addCleanup(_setup.dispose, track)
        for word in ("Mesi", "Perdite", "Giorno tipo"):
            track.add(word, word.lower(), f"Il grafico: {word}")
        if exclusive:
            track.set_current("mesi")
        track.show()
        self.app.processEvents()
        track.repaint()
        self.app.processEvents()
        return track

    def settle(self, track, ms=400):
        _setup.wait_until(self.app, lambda: track.slide.source is None, ms / 1000)
        track.repaint()
        self.app.processEvents()

    def test_a_click_chooses_and_says_it_and_a_click_on_the_chosen_says_nothing(self):
        track = self.track()
        said = []
        track.chosen.connect(said.append)
        track.items[2].click()
        self.assertEqual(track.current(), "giorno tipo")
        self.assertEqual(said, ["giorno tipo"])
        track.items[2].click()
        self.assertEqual(said, ["giorno tipo"])
        self.assertTrue(track.items[2].isChecked())
        track.set_current("mesi")                       # by the program: not said
        self.assertEqual(said, ["giorno tipo"])
        track.items[1].click()
        self.assertEqual(said, ["giorno tipo", "perdite"])

    def test_the_rectangle_slides_with_the_phases_curve_and_lands_on_the_segment(self):
        from meridiana.ui.design import Motion
        track = self.track()
        before = QRectF(track.items[0].geometry())
        self.assertEqual(track.slide.shown, before)
        track.items[2].click()
        target = QRectF(track.items[2].geometry())
        self.assertEqual(track.slide.now(), before)     # held while the window works (R97)
        self.assertTrue(_setup.wait_until(self.app, lambda: track.slide.animation.state().name == "Running", 1))
        self.assertEqual(track.slide.animation.duration(), Motion.FAST)
        self.assertEqual(track.slide.animation.easingCurve().type(), QEasingCurve.Type.OutCubic)
        self.settle(track)
        self.assertEqual(track.slide.now(), target)
        self.assertEqual(track.slide.shown, target)

    def test_the_rectangle_midway_is_between_the_two(self):
        track = self.track()
        track.items[2].click()
        self.assertTrue(_setup.wait_until(self.app, lambda: track.slide.animation.state().name == "Running", 1))
        track.slide.animation.setCurrentTime(track.slide.animation.duration() // 2)
        r, a, b = track.slide.now(), track.items[0].geometry(), track.items[2].geometry()
        self.assertGreater(r.left(), a.left())
        self.assertLess(r.left(), b.left())
        track.slide.animation.stop()

    def test_with_less_motion_it_is_there_at_once(self):
        from meridiana.ui import motion
        track = self.track()
        motion.set_reduced(True)
        track.items[1].click()
        self.assertEqual(track.slide.now(), QRectF(track.items[1].geometry()))
        self.assertEqual(track.slide.animation.state().name, "Stopped")

    def test_the_arrows_choose_and_stop_at_the_ends_and_skip_a_disabled_segment(self):
        track = self.track()
        said = []
        track.chosen.connect(said.append)
        self.assertEqual(track.focusPolicy(), Qt.FocusPolicy.TabFocus)
        QTest.keyClick(track, Qt.Key.Key_Left)
        self.assertEqual(track.current(), "mesi")
        track.items[1].setEnabled(False)
        QTest.keyClick(track, Qt.Key.Key_Right)
        self.assertEqual(track.current(), "giorno tipo")
        self.assertEqual(said, ["giorno tipo"])
        QTest.keyClick(track, Qt.Key.Key_Right)
        self.assertEqual(track.current(), "giorno tipo")

    def test_the_accent_ring_only_with_the_keyboard_on_it(self):
        """Seen on the merged cards' tabs: the focus falls on a track when the widget that had it goes away (a panel
        closed, a page changed), and the ring in the accent stayed on with nobody at the keys."""
        from PySide6.QtGui import QFocusEvent, QKeyEvent
        from PySide6.QtCore import QEvent
        from meridiana.ui.segments import tokens
        track = self.track()
        accent = QColor(tokens()["accent"])

        def ring():
            track.repaint()
            image = track.grab().toImage()
            dpr = image.devicePixelRatio()
            r = track.items[0].geometry()
            return image.pixelColor(round(r.center().x() * dpr), round(r.top() * dpr)) == accent
        self.assertFalse(ring())

        def focus(reason):
            self.app.sendEvent(track, QFocusEvent(QEvent.Type.FocusIn, reason))
            seen = ring()
            self.app.sendEvent(track, QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.OtherFocusReason))
            self.assertFalse(ring())
            return seen
        # Qt says «Tab» too when a widget hidden hands its focus on (hide_helper, focusNextPrevChild): no key, no ring
        self.assertFalse(focus(Qt.FocusReason.TabFocusReason))
        self.assertFalse(focus(Qt.FocusReason.OtherFocusReason))
        for key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            self.app.sendEvent(track, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
            self.assertTrue(focus(Qt.FocusReason.TabFocusReason if key == Qt.Key.Key_Tab
                                  else Qt.FocusReason.BacktabFocusReason), key)
            self.app.sendEvent(track, QKeyEvent(QEvent.Type.KeyRelease, key, Qt.KeyboardModifier.NoModifier))
        self.assertFalse(focus(Qt.FocusReason.TabFocusReason))

    def test_each_segment_has_its_tooltip_and_is_cut_when_the_track_is_narrow(self):
        track = self.track()
        self.assertEqual(track.items[0].toolTip(), "Il grafico: Mesi")
        whole = track.sizeHint().width()
        track.setFixedWidth(whole // 2)
        self.app.processEvents()
        self.assertLessEqual(sum(b.width() for b in track.items), whole // 2)
        self.assertGreater(min(b.width() for b in track.items), 0)
        self.assertLess(track.minimumSizeHint().width(), whole)

    def test_the_theme_draws_the_track_and_the_rectangle(self):
        from meridiana.ui.segments import tokens
        track = self.track()
        t = tokens()
        image = track.grab().toImage()
        dpr = image.devicePixelRatio()
        at = lambda x, y: image.pixelColor(round(x * dpr), round(y * dpr))
        a, b = track.items[0].geometry(), track.items[1].geometry()
        self.assertEqual(at(b.left() + 3, b.top() + 3), QColor(t["field"]))
        self.assertEqual(at(a.left() + 4, a.center().y()), QColor(t["panel"]))

    def test_not_exclusive_each_keeps_its_own_state_with_its_rectangle(self):
        from meridiana.ui.segments import tokens
        track = self.track(exclusive=False)
        track.items[0].click()
        track.items[2].click()
        self.assertEqual([b.isChecked() for b in track.items], [True, False, True])
        _setup.wait_until(self.app, lambda: track.fading is None, 1)
        track.repaint()
        image = track.grab().toImage()
        dpr = image.devicePixelRatio()
        t = tokens()
        for i, colour in ((0, t["panel"]), (2, t["panel"]), (1, t["field"])):
            r = track.items[i].geometry()
            self.assertEqual(image.pixelColor(round((r.left() + 4) * dpr), round(r.center().y() * dpr)),
                             QColor(colour), i)
        track.items[2].click()
        self.assertFalse(track.items[2].isChecked())
        self.assertEqual(track.items[0].focusPolicy(), Qt.FocusPolicy.TabFocus)    # the space bar, one by one

    def test_a_tab_bar_gets_the_track_keeps_its_keys_and_its_rectangle_lands(self):
        from meridiana.ui.segments import BarTrack, on_bar, tokens
        from meridiana import config
        from meridiana.ui.theme import Theme
        theme = Theme(config.Config(theme="light", background="none"), app=self.app)    # the tabs' rule is the sheet's
        self.addCleanup(theme.deleteLater)
        bar = QTabBar()
        self.addCleanup(_setup.dispose, bar)
        for word in ("Mesi", "Perdite", "Come è calcolato"):
            bar.addTab(word)
        track = on_bar(bar)
        self.assertIs(on_bar(bar), track)
        self.assertIsInstance(track, BarTrack)
        self.assertFalse(bar.drawBase())
        bar.show()
        self.app.processEvents()
        bar.repaint()
        self.app.processEvents()
        t = tokens()
        image = bar.grab().toImage()
        dpr = image.devicePixelRatio()
        first, second = bar.tabRect(0), bar.tabRect(1)
        self.assertEqual(track.selection().left(), first.left() + 2)
        self.assertEqual(image.pixelColor(round((first.left() + 6) * dpr), round(first.center().y() * dpr)),
                         QColor(t["panel"]))
        self.assertEqual(image.pixelColor(round((second.right() - 3) * dpr), round(second.center().y() * dpr)),
                         QColor(t["field"]))
        bar.setFocus()
        QTest.keyClick(bar, Qt.Key.Key_Right)
        self.assertEqual(bar.currentIndex(), 1)
        self.assertTrue(_setup.wait_until(self.app, lambda: track.slide.source is None, 1))
        bar.repaint()
        self.assertEqual(track.slide.shown, track.selection())
        self.assertEqual(track.track().top(), first.top() + 2)
        self.assertEqual(track.track().height(), 28)


if __name__ == "__main__":
    unittest.main()
