"""The complete New Project journey in the real MainWindow, from File to the drawing phase."""

import unittest

import _setup
from _fixtures import capannone

from meridiana import config

setUpModule = _setup.keep_global_state


class NewProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), cfg=config.Config(background="none", network_tiles=False))

    def test_file_new_keeps_the_old_project_until_create_and_draw(self):
        old = self.win.project
        self.win._new()
        page = self.win.file_page.new_project
        self.assertTrue(self.win.file_page.isVisible())
        self.assertIs(self.win.project, old)
        page.query.setText(old.name)
        self.assertIn(old.name, page.suggestion_rows[next(
            key for key in page.suggestion_rows if key.endswith("project"))].name)
        page.query.setText("45.5226, 9.03")
        page.name.setText("Nuovo Rho")
        page.create.click()
        self.assertIsNot(self.win.project, old)
        self.assertEqual(self.win.project.name, "Nuovo Rho")
        self.assertEqual((self.win.project.site.lat, self.win.project.site.lon), (45.5226, 9.03))
        self.assertEqual(self.win.project.buildings, [])
        self.assertEqual(self.win.phase(), "model")
        self.assertEqual(self.win.plan.choice, "auto")
        self.assertFalse(self.win.file_page.isVisible())


if __name__ == "__main__":
    unittest.main()
