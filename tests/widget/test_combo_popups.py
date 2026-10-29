"""Focused drop-downs fit their choices; genuine overflow still scrolls."""

from __future__ import annotations

import os
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import _setup

setUpModule = _setup.keep_global_state

try:
    from PySide6.QtCore import QEvent, QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QComboBox, QVBoxLayout, QWidget
except ImportError as error:
    raise unittest.SkipTest(f"PySide6 is not installed: {error}") from error

class ComboPopupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.theme = _setup.meridiana_look("dark")
        self.host = QWidget()
        self.combo = QComboBox()
        QVBoxLayout(self.host).addWidget(self.combo)
        self.host.resize(220, 60)
        self.host.move(100, 100)
        self.addCleanup(self.dispose)

    def dispose(self):
        self.combo.hidePopup()
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def open_choices(self, count=4):
        choices = ["Piatto", "Per categorie", "Per tipo di lavoro", "Per WBS"]
        self.combo.addItems(choices if count == 4 else [f"Choice {i}" for i in range(count)])
        # Populate the popup while the combo is unfocused, as happens during application construction.
        self.combo.view()
        self.host.show()
        self.host.activateWindow()
        self.combo.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.qWait(30)
        self.assertTrue(self.combo.hasFocus())
        self.combo.showPopup()
        QTest.qWait(30)
        return self.combo.view()

    def assert_all_rows_fit(self, view):
        self.assertEqual(0, view.verticalScrollBar().maximum(), "A short list must not acquire a scroll strip")
        viewport = view.viewport().rect()
        for i in range(self.combo.count()):
            rect = view.visualRect(self.combo.model().index(i, self.combo.modelColumn()))
            self.assertGreaterEqual(rect.top(), viewport.top())
            self.assertLessEqual(rect.bottom(), viewport.bottom(), "The last choice must be completely visible")

    def test_four_choices_are_fully_visible_after_the_combo_gets_focus(self):
        self.assert_all_rows_fit(self.open_choices())

    def test_a_stretched_settings_field_opens_a_compact_list_with_all_choices(self):
        self.host.resize(1400, 60)
        view = self.open_choices()
        self.assertLessEqual(view.window().width(), 360)
        self.assertGreaterEqual(view.viewport().width(), view.sizeHintForColumn(0))
        self.assert_all_rows_fit(view)

    def test_bottom_of_last_choice_is_clickable_without_scrolling(self):
        view = self.open_choices()
        rect = view.visualRect(self.combo.model().index(3, 0))
        point = QPoint(view.viewport().width() // 2, rect.bottom() - 1)
        self.assertTrue(view.viewport().rect().contains(point), "The scroll strip covers the last choice")
        # The popup deliberately ignores the release which originally opened it.
        QTest.qWait(QApplication.doubleClickInterval() + 1)
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
        self.assertEqual(3, self.combo.currentIndex())

    def test_reopening_on_last_choice_and_switching_theme_keep_short_list_whole(self):
        view = self.open_choices()
        for name in ("light", "dark"):
            self.combo.hidePopup()
            self.combo.setCurrentIndex(3)
            self.theme.cfg.theme = name
            self.theme.apply()
            self.combo.setFocus(Qt.FocusReason.TabFocusReason)
            QTest.qWait(20)
            self.combo.showPopup()
            QTest.qWait(20)
            self.assert_all_rows_fit(view)
            self.assertEqual(3, view.currentIndex().row())

    def test_many_choices_keep_scrolling_and_keyboard_can_select_last(self):
        view = self.open_choices(100)
        self.assertGreater(view.verticalScrollBar().maximum(), 0)
        self.assertLessEqual(view.window().height(), self.host.screen().availableGeometry().height())
        QTest.keyClick(view, Qt.Key.Key_End)
        QTest.qWait(20)
        self.assertEqual(99, view.currentIndex().row())
        rect = view.visualRect(view.currentIndex())
        self.assertGreaterEqual(rect.top(), 0)
        self.assertLessEqual(rect.bottom(), view.viewport().height() - 1)
        QTest.keyClick(view, Qt.Key.Key_Return)
        self.assertEqual(99, self.combo.currentIndex())

    def test_short_popup_near_screen_bottom_moves_up_without_hiding_last_choice(self):
        room = self.host.screen().availableGeometry()
        self.host.move(room.left() + 100, room.bottom() - self.host.height())
        view = self.open_choices()
        self.assert_all_rows_fit(view)
        self.assertLessEqual(view.window().geometry().bottom(), room.bottom())


if __name__ == "__main__":
    unittest.main()
