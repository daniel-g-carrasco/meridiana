"""Hidden phases keep their original ids and shortcuts without entering the navigation cycle."""
import unittest
import _setup
from _fixtures import capannone
setUpModule = _setup.keep_global_state
class HiddenPhaseNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
    def test_hidden_phases_are_skipped_by_menu_steps_and_direct_shortcuts(self):
        win = _setup.window(self, capannone())
        win.tabs.set_phase_visible("plant", False)
        win.show_phase("model")
        win.show_phase("plant")
        self.assertEqual(win.phase(), "model")
        win.commands["next_phase"].trigger()
        self.assertEqual(win.phase(), "production")
        win.commands["previous_phase"].trigger()
        self.assertEqual(win.phase(), "model")
        win.tabs.set_phase_visible("model", False)
        self.assertEqual(win.phase(), "production")
        win.tabs.set_phase_visible("plant", True)
        win.show_phase("plant")
        self.assertEqual(win.phase(), "plant")
if __name__ == "__main__":
    unittest.main()
