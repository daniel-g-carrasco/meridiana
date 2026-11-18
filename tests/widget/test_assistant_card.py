"""Meridio's shared cards keep wrapped paths and task text fully visible (R151)."""

import unittest

import _setup
from meridiana.ui.assistant_chat import Card

setUpModule = _setup.keep_global_state


class AssistantCardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_wrapped_long_path_is_not_shrunk_below_the_card_size_hint(self):
        from PySide6.QtWidgets import QLabel, QLineEdit, QTextBrowser, QVBoxLayout, QWidget
        _setup.meridiana_look()
        card = Card("Open project", ["Path: /tmp/a-very-long-private-folder/with-many-segments/project_R05.meridiana",
                                     "Revision: R05"], [("discard", "Discard"), ("apply", "Open")])
        container = QWidget()
        box = QVBoxLayout(container)
        box.addWidget(QTextBrowser(), 1)
        box.addWidget(card)
        box.addWidget(QLineEdit())
        container.resize(320, 400)
        container.show()
        self.app.processEvents()
        self.assertGreaterEqual(card.height(), card.sizeHint().height())
        for label in card.findChildren(QLabel):
            self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()))
        container.close()


if __name__ == "__main__":
    unittest.main()
