"""The plan as a DXF in the window (R513): File > Export the plan as DXF, the File page's tile, the options' dialog
(coordinates and parts), the job with the IFC's bar, the deliverable of the Report made. One journey on one window
(study 18, D 7.1). PySide6, a display (offscreen will do) and ezdxf."""
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone as sample
from _setup import wait_until

from meridiana import dxf_export

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class DxfInTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        if not dxf_export.available():
            raise unittest.SkipTest("ezdxf is not installed")

    def setUp(self):
        _setup.window(self, sample())
        self.folder = Path(tempfile.mkdtemp())

    def test_the_plan_is_written_in_a_job_with_the_options_asked(self):
        from PySide6.QtWidgets import QLabel
        texts = [a.text() for a in self.win.menuBar().actions()[0].menu().actions()]
        self.assertIn(self.win.commands["export_dxf"].text(), texts)
        words = [w.text() for w in self.win.file_page.sections["export"].findChildren(QLabel)]
        self.assertIn("Plan as DXF", words)
        # the options: the frame of the imported file is off (the buildings were drawn here), with why
        from meridiana.ui.dxf_options import DxfOptionsDialog
        dialog = DxfOptionsDialog(dxf_export.frame_choices(self.win.project), dxf_export.part_names(),
                                  ("imported", ("modules",)), self.win)
        self.assertFalse(dialog.findChild(object, "frame-imported").isEnabled())
        self.assertTrue(dialog.findChild(object, "frame-imported").toolTip())
        self.assertEqual(dialog.choice(), ("local", ("modules",)))
        dialog.findChild(object, "frame-utm").setChecked(True)
        dialog.findChild(object, "part-strings").setChecked(True)
        self.assertEqual(dialog.choice(), ("utm", ("modules", "strings")))
        dialog.deleteLater()
        target = self.folder / "capannone.dxf"
        self.win._export_dxf(str(target), "utm", dxf_export.PARTS)
        self.assertIsNotNone(self.win.ifc_job)
        self.assertTrue(wait_until(self.app, lambda: self.win.ifc_job is None, 60), "the export did not end")
        self.assertTrue(target.exists())
        self.assertEqual(dxf_export.audit(target), [])
        self.assertIn("DXF written: capannone.dxf", self.win.statusBar().currentMessage())
        from meridiana import phases                        # the Report phase's deliverable, made
        made = {d.id: d for d in phases.deliverables(False, self.win.exports, self.win._state_key())}
        self.assertEqual(made["dxf"].state, "done")
        import ezdxf
        doc = ezdxf.readfile(str(target))
        modules = [e for e in doc.modelspace().query("INSERT") if e.dxf.layer == "FV-MODULI"]
        self.assertEqual(len(modules), sum(len(r.modules) for r in self.win.results.values()))
        first = modules[0].dxf.insert
        self.assertGreater(first.x, 400_000)                 # UTM: East and North of Rho, zone 32
        self.assertGreater(first.y, 5_000_000)


if __name__ == "__main__":
    unittest.main()
