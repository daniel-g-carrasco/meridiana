"""The panels come back at the next start as the designer arranged them, not as the moment of closing had them (R323,
Daniel 02/11/2026: «in tutte le volte che ho aperto Meridiana dopo tuoi aggiornamenti, non mi appare all'inizio la
barra di sinistra con edifici, elementi, ecc. Devo ripristinare la disposizione predefinita per farla tornare»).

The Project panel goes by itself in the phases without a drawing (Production to Report, `_phase_panels`) and comes
back in Modelling and Plant. Closed in one of those phases (Meridiana is closed for every update), the saved layout
had it hidden; at the next start nothing knew it had gone by itself, and it never came back. The same with «Only the
drawing» (Ctrl+0), whose panels all went hidden into the file. And at the start a panel docked and shown but squeezed
under `Size.PANEL_MIN` gets its first size back."""

import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state


class PanelsSaved(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def paths(self):
        from meridiana.paths import Paths
        root = Path(tempfile.mkdtemp())
        return Paths(config=root / "config", state=root / "state", data=root / "data", cache=root / "cache")

    def again(self, paths):
        """The program closed (its layout saved) and opened again on the same folders."""
        _setup.dispose(self.win)
        _setup.window(self, capannone(), paths=paths, size=(1600, 1000))
        self.win.show_phase("model")
        _setup.turn_events(self.app, 300)
        return self.win

    def test_closed_in_a_phase_without_the_drawing_the_project_panel_comes_back(self):
        paths = self.paths()
        _setup.window(self, capannone(), paths=paths, size=(1600, 1000))
        self.win.show_phase("production")
        _setup.turn_events(self.app, 300)
        self.assertTrue(self.win.docks[0].isHidden())                 # gone by itself, as it should
        win = self.again(paths)
        self.assertTrue(win.restored)
        self.assertFalse(win.docks[0].isHidden())
        self.assertGreaterEqual(win.docks[0].width(), 200)

    def test_a_panel_the_designer_closed_stays_closed(self):
        paths = self.paths()
        _setup.window(self, capannone(), paths=paths, size=(1600, 1000))
        self.win.docks[0].hide()                                      # closed by hand, in Modelling
        self.win.show_phase("report")
        _setup.turn_events(self.app, 300)
        win = self.again(paths)
        self.assertTrue(win.docks[0].isHidden())

    def test_closed_with_only_the_drawing_the_panels_come_back(self):
        paths = self.paths()
        _setup.window(self, capannone(), paths=paths, size=(1600, 1000))
        self.win.clean_action.trigger()
        _setup.turn_events(self.app, 200)
        self.assertTrue(self.win.docks[1].isHidden())
        win = self.again(paths)
        for dock in (*win.docks, win.checks_dock, win.help_dock):
            self.assertFalse(dock.isHidden(), dock.objectName())

    def test_a_panel_squeezed_at_the_start_gets_its_first_size_back(self):
        from PySide6.QtCore import Qt

        from meridiana.ui.design import Size
        _setup.window(self, capannone(), size=(1600, 1000))
        win = self.win
        left = win.docks[0]
        left.setMinimumWidth(0)
        win.resizeDocks([left], [4], Qt.Orientation.Horizontal)
        _setup.turn_events(self.app, 100)
        if left.width() >= Size.PANEL_MIN:
            self.skipTest("Qt kept the panel at its minimum here: nothing to put back")
        win._settle_panel_sizes()
        _setup.turn_events(self.app, 100)
        self.assertGreaterEqual(left.width(), Size.PANEL_MIN)


if __name__ == "__main__":
    unittest.main()
