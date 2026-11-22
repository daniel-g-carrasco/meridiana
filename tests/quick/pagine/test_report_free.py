"""The report as jobs of the jobs' center (R598, study 48 chapter 6, step 3), with real processes: the guard of the
window on the preview and on the PDF (no call of the center on the window's thread over 5 ms, the beat under 50 ms,
the report's own deliveries named), the year read from the store of the years (never written by the window), and
what happens when the project changes or the program closes half way."""
import tempfile
import unittest
from pathlib import Path

import _setup
from meridiana.app.platform.config import Config
from meridiana.app.session import ProjectSession
from quick.aiuti.finestra_libera import window_stays_free
from quick.aiuti.tempi import timed

setUpModule = _setup.keep_global_state


def pdf_text(path):
    from pypdf import PdfReader
    return [page.extract_text() for page in PdfReader(str(path)).pages]


class ReportFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from _fixtures import clear_sky_meteo, write_cache
        from meridiana.app import jobs, pipeline, year_key
        from meridiana.data import year_store
        from meridiana.gui.backend.report import ReportBackend
        from quick.aiuti.differential import connected_fixture
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.session = ProjectSession(connected_fixture())
        weather = self.folder / "weather"
        write_cache(clear_sky_meteo(), weather)
        session = self.session
        session.results, session.layout_keys, _laid = jobs.layout_of(session.project)
        good = session.good_results()
        session.energy = pipeline.compute(session.project, good, weather, fetch=False).as_dict()
        session.energy_key_computed = session.expected_key()        # as a year computed
        # the year in the store of the years, as the year's own process writes it (shell_compute.worker)
        key = session.energy_key_computed
        year_store.write(weather, year_key.fingerprint(key), key, session.energy, session.results,
                         session.layout_keys)
        self.cache = self.folder / "cache"
        self.backend = ReportBackend(session, Config(), paths={"cache": self.cache, "state": self.folder / "state"},
                                     year_cache=weather)
        self.addCleanup(self.backend.close)
        self.center = self.backend.center

    def wait(self, condition, seconds=120):
        return _setup.wait_until(self.app, condition, seconds=seconds)

    def leftovers(self, target):
        return sorted(p.name for p in target.parent.iterdir() if p.name.startswith(target.name) and p != target)

    @timed('no call of the window over 5 ms')
    def test_the_window_stays_free_while_the_preview_is_made(self):
        self.addCleanup(self.backend.setActive, False)
        with window_stays_free(self.center, call_ms=5, beat_ms=50) as seen:
            self.backend.setActive(True)                    # the page entered: its preview asked after the quiet
            self.assertTrue(self.wait(lambda: not self.backend.busy and self.backend._swap is None
                                      and self.backend.pages), self.backend.error)
        print(f"\npreview: {seen}")
        names = self.center.stats()["by_name"]
        for name in ("submit:report", "report.on_partial", "report.on_done", "report.pages"):
            self.assertIn(name, names)
        self.assertFalse(self.backend.error, self.backend.error)
        self.assertEqual(len(self.backend.pages), self.backend.pageCount)
        self.assertTrue(self.backend.outline, "the chapters and their pages")
        self.assertTrue(all(row["page"] >= 1 for row in self.backend.outline))
        # the year came from the store: the window wrote none
        self.assertIsNone(self.backend._store_miss)
        self.assertFalse((self.cache / self.backend._root_name / "window-years").exists())

    @timed('no call of the window over 5 ms')
    def test_the_window_stays_free_while_the_pdf_is_written(self):
        target = self.folder / "out" / "relazione.pdf"
        target.parent.mkdir()
        done = []
        self.backend.completed.connect(done.append)
        with window_stays_free(self.center, call_ms=5, beat_ms=50) as seen:
            self.backend.exportPdf(str(target))
            self.assertTrue(self.backend.busy, self.backend.error)
            self.assertTrue(self.wait(lambda: not self.backend.busy), self.backend.error)
        print(f"\npdf: {seen}")
        names = self.center.stats()["by_name"]
        for name in ("submit:report", "report.on_done"):
            self.assertIn(name, names)
        self.assertFalse(self.backend.error, self.backend.error)
        self.assertEqual(done, [str(target)])
        self.assertTrue(target.is_file())
        self.assertEqual(self.leftovers(target), [])

    def test_a_change_half_way_makes_the_preview_again_for_the_project_as_it_is(self):
        self.backend.setActive(True)
        self.addCleanup(self.backend.setActive, False)
        self.backend.requestPreview()
        handle = self.backend._handle
        self.assertTrue(self.wait(lambda: any(r["fraction"] for r in self.center.rows()), 60))
        self.backend.setSetting("client", "Cliente cambiato a metà")
        # the kind's restart: the same job made again after its quiet, never a preview of before shown
        self.assertIs(self.backend._handle, handle)
        self.assertTrue(self.wait(lambda: not self.backend.busy and self.backend._swap is None
                                  and self.backend.pages), self.backend.error)
        self.assertFalse(self.backend.error, self.backend.error)
        made = Path(self.backend.pages[0]["path"])
        self.assertIn("Cliente cambiato a metà", "".join(pdf_text(made)))
        self.assertTrue(self.backend._fresh())

    def test_a_change_half_way_lets_the_pdf_end_on_its_photo(self):
        target = self.folder / "relazione.pdf"
        self.backend.exportPdf(str(target))
        handle = self.backend._handle
        self.assertTrue(self.wait(lambda: any(r["fraction"] for r in self.center.rows()), 60))
        self.session.edit("Client", lambda p: setattr(p, "report", {**(p.report or {}), "client": "Dopo"}))
        self.assertIs(self.backend._handle, handle)         # on_change "finish": not stopped, not made again
        self.assertTrue(self.wait(lambda: not self.backend.busy), self.backend.error)
        self.assertFalse(self.backend.error, self.backend.error)
        self.assertEqual(handle.state, "done")
        self.assertTrue(handle.stale)                       # what on_done was told
        self.assertTrue(target.is_file())
        self.assertNotIn("Dopo", "".join(pdf_text(target)))
        self.assertEqual(self.leftovers(target), [])

    def closed_half_way(self, start):
        start()
        self.assertTrue(self.wait(lambda: any(r["fraction"] for r in self.center.rows()), 60))
        runner = self.center.runner
        procs = [p.popen for p in runner.all_processes() if p.popen is not None]
        self.assertTrue(procs)
        self.backend.close()
        for popen in procs:
            self.assertIsNotNone(popen.poll(), "a job's process left after the close")
        self.assertFalse((self.cache / self.backend._root_name).exists(), "the report's folders left")

    def test_the_program_closed_half_way_through_the_pdf_leaves_nothing(self):
        target = self.folder / "kept.pdf"
        target.write_bytes(b"original")
        self.closed_half_way(lambda: self.backend.exportPdf(str(target)))
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual(self.leftovers(target), [])

    def test_the_program_closed_half_way_through_the_preview_leaves_nothing(self):
        self.backend.setActive(True)
        self.closed_half_way(self.backend.requestPreview)


if __name__ == "__main__":
    unittest.main()
