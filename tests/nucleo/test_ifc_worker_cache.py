"""r24: the answer of a large IFC model read by the scan alone is kept next to its geometry, and the second reading of
the same file comes from it (the large test IFC's 1.6 GB: 25 s the second time before, 2-3 s after)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401  (paths and the common setup)
from meridiana import ifc_worker, resources
from nucleo.test_ifc_scan import SAMPLE


class Cache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "m.ifc"
        self.path.write_text(SAMPLE, encoding="utf-8")
        self.folder = str(Path(self.tmp.name) / "context")
        # the sample stands for a large model: past the limit the roofs are not looked for, the scan is the answer
        patch = mock.patch.object(ifc_worker, "IFCOS_LIMIT", 10)
        patch.start()
        self.addCleanup(patch.stop)

    def read(self):
        return ifc_worker.read(str(self.path), "direct", lambda f, w: None, None, self.folder)

    def test_the_second_reading_comes_from_the_kept_answer(self):
        first = self.read()
        self.assertEqual(first["mode"], "scan")
        self.assertTrue(os.path.isfile(ifc_worker.result_file(self.folder, str(self.path))))
        with mock.patch("meridiana.ifc_scan.scan", side_effect=AssertionError("the file was read again")):
            again = self.read()
        self.assertIn("cached", again["times"])
        self.assertEqual(again["solids"], json.loads(json.dumps(first["solids"])))
        self.assertEqual(again["context"]["mesh"], first["context"]["mesh"])
        self.assertEqual(again["listing"], json.loads(json.dumps(first["listing"], default=float)))

    def test_a_changed_file_or_a_lost_geometry_is_read_again(self):
        first = self.read()
        os.unlink(first["context"]["mesh"])                  # the geometry is gone: the answer is not enough
        self.assertIsNone(ifc_worker.cached_result(str(self.path), self.folder))
        again = self.read()
        self.assertNotIn("cached", again["times"])
        self.path.write_text(SAMPLE + "\n", encoding="utf-8")   # another size: another key
        self.assertIsNone(ifc_worker.cached_result(str(self.path), self.folder))

    def test_no_folder_no_cache(self):
        self.assertIsNone(ifc_worker.cached_result(str(self.path), None))
        found = ifc_worker.read(str(self.path), "direct", lambda f, w: None, None, None)
        self.assertNotIn("cached", found.get("times", {}))


class Priority(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "the priority classes are Windows'")
    def test_the_priority_classes_take(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetPriorityClass.argtypes = (wintypes.HANDLE,)
        me = kernel.GetCurrentProcess()
        before = kernel.GetPriorityClass(me)
        try:
            self.assertTrue(resources.raise_priority())
            self.assertEqual(kernel.GetPriorityClass(me), 0x8000)
            self.assertTrue(resources.lower_priority())
            self.assertEqual(kernel.GetPriorityClass(me), 0x4000)
        finally:
            kernel.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
            kernel.SetPriorityClass(me, before)


if __name__ == "__main__":
    unittest.main()
