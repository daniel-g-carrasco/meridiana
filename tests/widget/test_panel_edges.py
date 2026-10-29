"""The status bar's side commands include every card touching that edge."""
import unittest

import _setup
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

from meridiana.ui.panel_buttons import PanelButtons

setUpModule = _setup.keep_global_state


class PanelEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_corner_card_can_be_hidden_and_restored_from_either_touching_edge(self):
        window = QMainWindow()
        self.addCleanup(_setup.dispose, window)
        window.setCentralWidget(QWidget())
        right = QDockWidget("Properties", window)
        bottom = QDockWidget("Checks", window)
        help_dock = QDockWidget("Help", window)
        for dock in (right, bottom, help_dock):
            dock.setWidget(QWidget())
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, right)
        window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, bottom)
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, help_dock)
        window.splitDockWidget(right, help_dock, Qt.Orientation.Vertical)
        window.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        buttons = PanelButtons([(right, "panel-right", None), (bottom, "panel-bottom", None),
                                (help_dock, "circle-question-mark", None)], window)
        window.resize(1000, 700)
        window.show()
        self.app.processEvents()
        for command in (right, bottom):
            with self.subTest(command=command.windowTitle()):
                self.assertTrue(help_dock.isVisible())
                buttons.buttons[command].click()
                self.app.processEvents()
                self.assertTrue(help_dock.isHidden(), "Both edges include their shared corner card")
                buttons.buttons[command].click()
                self.app.processEvents()
                self.assertTrue(help_dock.isVisible())
