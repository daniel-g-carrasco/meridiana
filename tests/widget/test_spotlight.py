"""A temporary guide reveals a real control without editing it or taking its keyboard focus."""

import unittest
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state


class Spotlight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def controls(self):
        from PySide6.QtWidgets import QCheckBox, QLineEdit, QScrollArea, QVBoxLayout, QWidget
        window = QWidget()
        outer = QVBoxLayout(window)
        edit = QLineEdit("The keyboard stays here")
        outer.addWidget(edit)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QVBoxLayout(body)
        form.addSpacing(1100)
        control = QCheckBox("An option below the fold")
        form.addWidget(control)
        scroll.setWidget(body)
        outer.addWidget(scroll)
        window.resize(500, 350)
        window.show()
        self.addCleanup(_setup.dispose, window)
        self.app.processEvents()
        edit.setFocus()
        self.app.processEvents()
        return window, edit, scroll, control

    def test_reveal_scrolls_to_the_control_without_changing_value_or_focus(self):
        from PySide6.QtCore import Qt
        from meridiana.ui import spotlight
        window, edit, scroll, control = self.controls()
        before = control.isChecked()
        shown = spotlight.reveal(control)
        self.app.processEvents()
        self.assertGreater(scroll.verticalScrollBar().value(), 0)
        self.assertTrue(scroll.viewport().rect().contains(control.mapTo(scroll.viewport(), control.rect().center())))
        self.assertEqual(control.isChecked(), before)
        self.assertIs(self.app.focusWidget(), edit)
        self.assertEqual(shown.focusPolicy(), Qt.FocusPolicy.NoFocus)
        self.assertTrue(shown.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        self.assertIs(shown.parentWidget(), window)

    def test_the_guide_expires_and_repeated_requests_replace_the_old_guide(self):
        from meridiana.ui import spotlight
        window, _edit, _scroll, control = self.controls()
        first = spotlight.reveal(control, duration=50)
        second = spotlight.reveal(control, duration=50)
        self.assertFalse(first.isVisible())
        self.assertTrue(second.isVisible())
        self.assertTrue(_setup.wait_until(self.app, lambda: not any(
            child.isVisible() for child in window.findChildren(spotlight.Spotlight)), seconds=2))

    def test_reduced_motion_keeps_the_ring_still_and_the_control_can_be_destroyed(self):
        from meridiana.ui import motion, spotlight
        window, _edit, scroll, control = self.controls()
        with mock.patch.object(motion, "reduced", return_value=True):
            shown = spotlight.reveal(control)
            shown.animation.setCurrentTime(500)
            first = shown.ring_rect()
            shown.animation.setCurrentTime(800)
            self.assertEqual(shown.ring_rect(), first)
            control.deleteLater()
            self.assertTrue(_setup.wait_until(self.app, lambda: not window.findChildren(spotlight.Spotlight)))
        self.assertIsNotNone(scroll)

    def test_the_guide_uses_the_current_theme_accent_including_disabled_controls(self):
        from PySide6.QtGui import QColor, QPalette
        from meridiana.ui import spotlight
        _window, _edit, _scroll, control = self.controls()
        palette = control.palette()
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent, QColor("#c8a0ef"))
        control.setPalette(palette)
        control.setEnabled(False)
        shown = spotlight.reveal(control)
        self.assertEqual(shown.colour.name(), "#c8a0ef")


if __name__ == "__main__":
    unittest.main()
