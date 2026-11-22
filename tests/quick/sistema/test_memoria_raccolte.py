"""Study 56, point 3 (d): what the window kept without a limit in bytes is now within the budget, each in its share
(resources.Kept): the report's preview pages (images; the underlays' pyramid: test_sottofondi_piramide.py), the readings of an IFC file kept,
the IFC geometry read ahead and the catalogue's 3D models (models). What somebody waits for (the page an Image asked
for, the model the 3D waits for) is still given whatever its size; what is let go is made again when asked."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
from meridiana.core.compute import resources

KIB, MIB = 1024, resources.MIB
setUpModule = _setup.keep_global_state


def limits(**kinds):
    """cache_limit answering `kinds` (bytes), 1 GB for the others."""
    return mock.patch.object(resources, "cache_limit", lambda kind: kinds.get(resources.KINDS.get(kind, kind), 1 << 30))


class ReportPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_preview_pages_are_within_the_images_share_and_the_one_asked_is_given(self):
        from meridiana.gui.backend import report_pages
        report_pages.publish([])
        self.addCleanup(report_pages.publish, [])
        page = 400 * round(400 * 297 / 210) * 4 + 256       # a white page 400 px wide (no rows: render's blank)
        with limits(images=int(2.5 * page)):
            for n in range(5):
                report_pages._Draw(f"x/{n}/400").run()
            self.assertEqual(list(report_pages._ready), ["x/3/400", "x/4/400"])
            self.assertLessEqual(report_pages._ready.bytes(), int(2.5 * page))
        with limits(images=page // 4):                      # a page larger than the share: the one asked stays
            report_pages._Draw("x/9/400").run()
            resources.give_back()
            self.assertEqual(list(report_pages._ready), ["x/9/400"])
            image = report_pages.take("x/9/400")
            self.assertEqual(image.width(), 400)
            self.assertEqual(report_pages._ready.bytes(), 0)


class IfcReadings(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_the_readings_kept_are_within_the_models_share(self):
        from meridiana.app.exchange import ifc_job
        self.addCleanup(ifc_job._KEPT.clear)
        ifc_job._KEPT.clear()
        files = []
        for n in range(3):
            path = Path(self.temp.name) / f"m{n}.ifc"
            path.write_text(f"ISO-10303-21; {n}", encoding="ascii")
            files.append(str(path))
        blobs = {f"piece/{i}": bytes(100 * KIB) for i in range(4)}      # 400 KB each
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}), limits(models=1 * MIB):
            for path in files:
                ifc_job.keep(path, [("buildings", 0, False)], blobs)
            self.assertEqual([ifc_job.kept(p) is not None for p in files], [False, True, True])   # two, as before
            with limits(models=500 * KIB):
                resources.give_back()
                self.assertEqual([ifc_job.kept(p) is not None for p in files], [False, False, True])
            with limits(models=300 * KIB):               # one reading larger than the share: not kept
                ifc_job.keep(files[0], [("buildings", 0, False)], blobs)
                self.assertIsNone(ifc_job.kept(files[0]))


class IfcGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_geometry_read_ahead_is_not_kept_beyond_the_models_share(self):
        import numpy as np
        from meridiana.gui.backend import scene_context
        self.addCleanup(scene_context.shutdown)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = str(Path(temp.name) / "ifc-56.npz")
        np.savez(path, vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 2]], "<f4"),
                 faces=np.array([[0, 1, 2]], "<u4"), centre=np.zeros(3), pieces=np.array([[0, 3, 0, 1]]),
                 colours=np.array([[0.5, 0.5, 0.5, 1.0]]), elements=np.zeros((0, 3), np.int64),
                 piece_of=np.zeros(0, np.int64))
        size = os.path.getsize(path)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}), limits(models=size - 1):
            self.assertFalse(scene_context.preload(path))                # larger than the share: not even read
            self.assertEqual(scene_context._READY, {})
            self.assertEqual(len(scene_context._prepared(path)[1]), 1)   # made when asked, as before
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}), limits(models=1 * MIB):
            self.assertTrue(scene_context.preload(path))
            scene_context._THREADS[-1].join(5)
            self.assertEqual(len(scene_context._READY), 1)
            self.assertGreater(scene_context._READY.bytes(), 36)


class CatalogueModels(unittest.TestCase):
    def test_the_catalogues_models_are_within_the_models_share(self):
        from meridiana.gui.backend import scene_assets
        keys = [row["key"] for row in scene_assets.catalog(active_only=True)][:3]
        self.addCleanup(scene_assets._MODELS.clear)
        scene_assets._MODELS.clear()
        first = scene_assets.load_model(keys[0])
        self.assertIs(scene_assets.load_model(keys[0]), first)          # kept: read once
        sizes = [sum(a.nbytes for a in scene_assets.load_model(k)) for k in keys]
        self.assertEqual(scene_assets._MODELS.bytes(), sum(sizes))
        with limits(models=max(sizes[1:]) + 1):
            resources.give_back()
            self.assertLessEqual(scene_assets._MODELS.bytes(), max(sizes[1:]) + 1)
            again = scene_assets.load_model(keys[0])                   # read again, the same arrays' values
        self.assertTrue(all((a == b).all() for a, b in zip(again, first, strict=True)))


if __name__ == "__main__":
    unittest.main()
