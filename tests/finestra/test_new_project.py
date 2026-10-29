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

    def test_client_and_job_follow_the_new_project_to_save_and_reopen(self):
        client = self.win.registry.create_client("Example client")
        job = self.win.registry.create_job("00125", "Example job", client["id"], reserved=True)
        self.win._new()
        page = self.win.file_page.new_project
        page.optional.setChecked(True)
        page.job.setCurrentIndex(page.job.findData(job["id"]))
        page.query.setText("45.5226, 9.03")
        page.name.setText("Linked design")
        page.create.click()
        self.assertEqual(self.win.current_job_id, job["id"])
        self.assertEqual(self.win.project.report["client"], "Example client")
        self.assertTrue(self.win.project.reserved)
        self.win.path = self.paths.data / "linked.meridiana"
        self.assertTrue(self.win._save())
        self.assertEqual(self.win.registry.project_at(self.win.path)["job_id"], job["id"])
        first = self.win.path
        series = self.win.current_project_id
        self.win._save_revision()
        self.assertNotEqual(self.win.path, first)
        self.assertEqual(self.win.current_project_id, series)
        self.win.current_job_id = self.win.current_project_id = ""
        self.win.open_path(first)
        self.assertEqual(self.win.current_job_id, job["id"])
        self.assertEqual(self.win.current_project_id, series)
        self.assertIn("registry", self.win.file_page.sections)


if __name__ == "__main__":
    unittest.main()
