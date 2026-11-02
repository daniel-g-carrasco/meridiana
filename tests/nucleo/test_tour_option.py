"""`meridiana --tour [STEP|new]` (R318): the option is taken out of the arguments before Qt sees them, a step is
named by its number or its id, a step that does not exist is an error said on the command line, and the run keeps
to a folder of settings of its own."""

import os
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401  (the path of the sources)

from meridiana import app, config, tour
from meridiana.paths import Paths


class TourOption(unittest.TestCase):
    def take(self, *args):
        return tour.take_option(["meridiana", *args])

    def test_without_the_option_nothing_changes(self):
        rest, request = self.take("project.meridiana", "-platform", "offscreen")
        self.assertEqual(rest, ["meridiana", "project.meridiana", "-platform", "offscreen"])
        self.assertIsNone(request)

    def test_alone_it_is_the_first_step(self):
        self.assertEqual(self.take("--tour"), (["meridiana"], tour.TourRequest(index=0)))

    def test_a_step_by_number_is_one_based(self):
        for number, index in (("1", 0), ("5", 4), (str(len(tour.steps())), len(tour.steps()) - 1)):
            rest, request = self.take("--tour", number)
            self.assertEqual(rest, ["meridiana"], number)       # the number is not taken for a project
            self.assertEqual(request, tour.TourRequest(index=index), number)

    def test_a_step_by_id_in_any_case_and_with_equals(self):
        ids = [s.id for s in tour.steps()]
        self.assertEqual(self.take("--tour", "plant")[1].index, ids.index("plant"))
        self.assertEqual(self.take("--tour", "PLANT")[1].index, ids.index("plant"))
        self.assertEqual(self.take("--tour=settings")[1].index, ids.index("settings"))
        self.assertEqual(self.take("--tour=3")[1].index, 2)

    def test_new_simulates_the_first_start(self):
        for word in ("nuovo", "new", "NUOVO"):
            self.assertEqual(self.take("--tour", word), (["meridiana"], tour.TourRequest(new=True)), word)

    def test_a_step_that_does_not_exist_is_a_clear_error(self):
        total = len(tour.steps())
        for bad in ("0", str(total + 1), "99", "nowhere", "-3"):
            with self.subTest(bad=bad), self.assertRaises(tour.TourOptionError) as caught:
                self.take(f"--tour={bad}")
            text = str(caught.exception)
            self.assertIn("--tour", text)
            self.assertIn(bad, text)
            self.assertIn(f"1 to {total}", text)
            self.assertIn("plant", text)
        with self.assertRaises(tour.TourOptionError):
            self.take("--tour", "nowhere")           # a word that is neither a step nor a file is not a project

    def test_a_project_after_the_option_stays_a_project(self):
        with tempfile.TemporaryDirectory() as folder:
            project = str(Path(folder) / "plant.meridiana")
            Path(project).write_text("{}", encoding="utf-8")
            rest, request = self.take("--tour", project)
            self.assertEqual(rest, ["meridiana", project])
            self.assertEqual(request, tour.TourRequest(index=0))
            rest, request = self.take("--tour", "4", project)
            self.assertEqual(rest, ["meridiana", project])
            self.assertEqual(request, tour.TourRequest(index=3))


class TourFolder(unittest.TestCase):
    def test_the_run_works_on_a_copy_of_the_settings_in_a_folder_of_its_own(self):
        with tempfile.TemporaryDirectory() as root:
            real_env = {"XDG_CONFIG_HOME": str(Path(root) / "real" / "config"),
                        "XDG_STATE_HOME": str(Path(root) / "real" / "state")}
            real = Paths.from_env(real_env)
            real.config.mkdir(parents=True)
            config.save(config.Config(language="it", tour_status="done"), real.config_file)
            before = real.config_file.read_bytes()
            environ = dict(real_env)
            folder = Path(root) / "tour"
            paths = app.isolate_for_tour(real, folder, environ)
            self.assertTrue(str(paths.config).startswith(str(folder)))
            self.assertTrue(str(paths.state).startswith(str(folder)))
            self.assertEqual(config.load(paths.config_file).language, "it")     # the person's language is kept
            config.save(config.Config(language="it", tour_status="active", tour_step=7), paths.config_file)
            self.assertEqual(real.config_file.read_bytes(), before)             # the real ones are not written
            self.assertTrue(os.path.commonpath([environ["XDG_DATA_HOME"], str(folder)]) == str(folder))


if __name__ == "__main__":
    unittest.main()
