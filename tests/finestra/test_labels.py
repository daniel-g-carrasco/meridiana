"""Wrapped labels give their form rows enough height in every theme, text size and window width (R193)."""

import unittest

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state


class Labels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.win = _setup.window(self, capannone())

    def test_no_visible_wrapped_label_is_shorter_than_its_text(self):
        from PySide6.QtWidgets import QLabel

        from meridiana.ui import theme
        # the text size back to medium afterwards: left at large, the tests after this one ran with it (28/10/2026)
        self.addCleanup(theme.change_text_size, "medium", self.app)
        failures = []
        for width in (1000, 1600):
            self.win.resize(width, 850)
            for text_size in ("medium", "large"):
                theme.change_text_size(text_size, self.app)
                for colour in ("light", "dark"):
                    self.win.cfg.theme = colour
                    self.win.theme.apply()
                    for phase in ("model", "plant", "production", "consumption", "economics", "report"):
                        self.win.show_phase(phase)
                        _setup.turn_events(self.app, 30)
                        for label in self.win.findChildren(QLabel):
                            needed = label.heightForWidth(label.width()) if label.wordWrap() else -1
                            if label.isVisibleTo(self.win) and needed > label.height():
                                where = label.parentWidget().title() if hasattr(label.parentWidget(), "title") else ""
                                failures.append((width, text_size, colour, phase, where, label.text(),
                                                 label.height(), needed))
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
