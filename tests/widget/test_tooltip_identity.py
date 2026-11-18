"""Tooltips keep Qt's original text identity and their own theme, even over coloured labels."""
import unittest
from unittest import mock

import _setup
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QLabel, QToolTip

from meridiana import config
from meridiana.ui import popups
from meridiana.ui.theme import Theme

setUpModule = _setup.keep_global_state


class TooltipIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.theme = Theme(config.Config(theme="light", background="none"), app=self.app)
        self.addCleanup(self.theme.deleteLater)
        self.host = QLabel("A coloured summary")
        self.host.setStyleSheet("color: #dc00dc; background: #c000c0; font-size: 24px;")
        self.host.resize(300, 70)
        self.host.move(100, 100)
        self.host.show()
        self.app.processEvents()
        self.addCleanup(_setup.dispose, self.host)
        self.addCleanup(QToolTip.hideText)

    def show_tip(self, text, offset=0):
        QToolTip.showText(self.host.mapToGlobal(QPoint(10 + offset, 20)), text, self.host)
        self.app.processEvents()
        return next(w for w in QApplication.topLevelWidgets() if isinstance(w, QLabel)
                    and w.windowType() == Qt.WindowType.ToolTip and w.isVisible())

    def test_repeated_requests_on_one_target_keep_the_same_layout_and_original_text(self):
        text = "A stable tooltip\nThe pointer can move within the same control."
        with mock.patch.object(popups, "tip_html", wraps=popups.tip_html) as layout:
            first = self.show_tip(text)
            size = first.size()
            for offset in (2, 4, 6):
                current = self.show_tip(text, offset)
                self.assertIs(current, first)
                self.assertEqual(current.size(), size)
            self.assertEqual(layout.call_count, 1, "Mouse motion must not reformat the same tooltip")
        self.assertEqual(first.text(), text, "Qt compares this original text when deciding whether to reuse a tip")

    def test_tooltip_ink_does_not_inherit_the_summary_labels_colour_in_either_theme(self):
        for mode in ("light", "dark"):
            self.theme.cfg.theme = mode
            self.theme.apply()
            tip = self.show_tip("An independent tooltip " + mode)
            image = tip.grab().toImage()
            magenta = [(x, y) for x in range(image.width()) for y in range(image.height())
                       if (lambda colour: colour.red() > 150 and colour.blue() > 150 and colour.green() < 50)(
                           image.pixelColor(x, y))]
            self.assertEqual(len(magenta), 0, "The tooltip must use its own ink, not the magenta label's colour")

    def test_tooltips_wake_quickly_and_come_with_a_fade_unless_less_motion_is_asked(self):
        from PySide6.QtCore import QVariantAnimation
        from PySide6.QtWidgets import QStyle
        from meridiana.ui import style
        for control_style in (self.host.style(), style.shared()):
            delay = control_style.styleHint(QStyle.StyleHint.SH_ToolTip_WakeUpDelay)
            self.assertGreater(delay, 0)
            self.assertLessEqual(delay, 250)
        previous = popups._STATE["motion"]
        self.addCleanup(popups.set_motion, previous)
        popups.set_motion(False)
        label = self.show_tip("A simple tooltip, at once")
        self.assertFalse(label.findChildren(QVariantAnimation))
        self.assertEqual(label.windowOpacity(), 1.0)
        QToolTip.hideText()
        _setup.turn_events(self.app, 400)
        popups.set_motion(True)
        label = self.show_tip("A simple tooltip, coming")
        self.assertLess(label.windowOpacity(), 1.0)
        _setup.turn_events(self.app, popups.TIP_MS + 150)
        self.assertEqual(label.windowOpacity(), 1.0)
        self.assertFalse(label.property(popups._RISING))
        self.assertEqual(label.pos(), popups.tip_place(QCursor.pos(), label.size(), label.screen().availableGeometry()))

    def test_a_long_tooltip_stands_beside_the_pointer_not_away_by_its_unwrapped_width(self):
        """Qt places it by the one line of its plain text: left of the pointer by all of that (Daniel, 03/11/2026)."""
        room = QRect(0, 0, 1920, 1080)
        size = QSize(popups.TIP_WIDTH, 80)
        self.assertEqual(popups.tip_place(QPoint(600, 300), size, room), QPoint(602, 321))
        at_the_right = popups.tip_place(QPoint(1900, 300), size, room)
        self.assertEqual(at_the_right, QPoint(1920 - popups.TIP_WIDTH, 321))    # pushed back, under the pointer
        at_the_bottom = popups.tip_place(QPoint(600, 1060), size, room)
        self.assertEqual(at_the_bottom, QPoint(602, 1060 - popups.TIP_ABOVE - 80))
        previous = popups._STATE["motion"]
        self.addCleanup(popups.set_motion, previous)
        popups.set_motion(False)
        screen = self.host.screen().availableGeometry()
        pointer = QPoint(screen.right() - 40, screen.top() + 100)
        with mock.patch.object(popups, "QCursor") as cursor:
            cursor.pos.return_value = pointer
            label = self.show_tip("A long explanation " * 12)
        self.assertLessEqual(label.width(), popups.TIP_WIDTH)
        self.assertLess(abs(label.x() + label.width() - 1 - pointer.x()), popups.TIP_WIDTH)
        self.assertLessEqual(label.x() + label.width() - 1, screen.right())
        self.assertEqual(label.y(), pointer.y() + popups.TIP_BELOW)
