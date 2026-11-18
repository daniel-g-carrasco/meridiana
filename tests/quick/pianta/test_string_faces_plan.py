"""R433 and R456 on the plan, in the DXF and in the report: a string that goes on over the other face of a capannone is
marked where it changes face (a diamond on the plan and in the DXF, its polyline through both faces); with optimizers on
some modules only the string is drawn as a plain one and an optimizer stands on each module that has one. Pure scene,
no window."""
import tempfile
import unittest
from pathlib import Path

from meridiana import dxf_export, jobs
from meridiana.energy import plant
from meridiana.quick.backend.plan_edit import PlanEditor
from meridiana.session import ProjectSession
from calcoli.test_string_faces import P2, capannone
from quick.pianta import test_edit_window as edit

setUpModule = edit.setUpModule


class OverTwoFaces(unittest.TestCase):

    def setUp(self):
        p = capannone(5.4, P2)
        self.results, _keys, _laid = jobs.layout_of(p)
        out = plant.proposal(p, self.results)
        p.energy["strings"] = plant.touched({}, plant.runs_of(out))
        self.project = p
        self.session = ProjectSession(p)
        self.editor = PlanEditor(self.session)
        self.editor.set_results(dict(self.results))
        self.editor.set_phase("plant")

    def diamonds(self, scene):
        return [o for o in scene["objects"] if o.get("face_change")]

    def test_the_plan_marks_where_the_string_changes_face(self):
        (run,) = self.project.energy["strings"]["runs"]
        self.assertEqual({k.split("/")[0] for k in run["modules"]}, {"s0", "s1"})
        scene = self.editor.wiring_scene(.02)
        changes = sum(1 for a, b in zip(run["modules"], run["modules"][1:], strict=False)
                      if a.split("/")[0] != b.split("/")[0])
        self.assertEqual(len(self.diamonds(scene)), changes)
        self.assertGreaterEqual(changes, 1)

    def test_partial_optimizers_stand_on_their_modules_only(self):
        (run,) = self.project.energy["strings"]["runs"]
        some = [k for k in run["modules"] if k.startswith("s1/")]
        plant.set_optimized(self.project.energy, some)
        self.editor.string_optimizers = {1: 1}
        self.editor.string_partial = {1: tuple(some)}
        scene = self.editor.wiring_scene(.02)
        kinds = [o["kind"] for o in scene["objects"]]
        self.assertIn("string_line", kinds, "drawn as a plain string")
        paths = " ".join(o["path"] for o in scene["optimizers"] if o["fill"] != "transparent")
        self.assertEqual(paths.count("M"), len(some), "one optimizer on each module that has one")

    def test_the_dxf_polyline_goes_over_both_faces_with_the_diamond(self):
        state = plant.build(self.project, self.results)
        path = Path(tempfile.mkdtemp()) / "faces.dxf"
        dxf_export.export(self.project, self.results, path, plant=state, parts=("modules", "strings"))
        import ezdxf
        doc = ezdxf.readfile(path)
        lines = [e for e in doc.modelspace().query("LWPOLYLINE") if e.dxf.layer == "FV-STRINGHE"]
        closed = [e for e in lines if e.closed and len(e) == 4]
        self.assertTrue(closed, "the diamond where the string changes face")
        # the optimizers of the inverter with MPPT: one block on each module (SUN2000-450W-P2, one module each)
        refs = [e for e in doc.modelspace().query("INSERT") if e.dxf.layer == "FV-OTTIMIZZATORI"]
        self.assertEqual(len(refs), 6)

    def test_the_3d_shows_the_string_climbing_over_the_ridge_and_the_optimizers(self):
        from meridiana import mesh, viewaids
        lines, crosses = viewaids.string_segments(self.project, self.results)
        (run,) = self.project.energy["strings"]["runs"]
        n = len(run["modules"])
        self.assertEqual(len(lines), n - 1 + 1, "one leg more: over the ridge through a point above it")
        self.assertEqual(len(crosses), 2 * n, "a cross on each module with an optimizer")
        ridge = max(z for z in (mesh.from_qt(*p)[2] if hasattr(mesh, "from_qt") else p[1] for seg in lines for p in seg))
        tops = [m.z for r in self.results.values() for m in r.modules]
        self.assertGreater(ridge, max(tops) + 0.2)
        some = [k for k in run["modules"] if k.startswith("s1/")]
        plant.set_optimized(self.project.energy, some)
        _lines, crosses = viewaids.string_segments(self.project, self.results)
        self.assertEqual(len(crosses), 2 * len(some))

    def test_the_report_says_the_string_over_two_faces(self):
        from meridiana.report_typst import chapters

        class Ctx:
            project = self.project

            def __init__(self, pl):
                self.pl = pl

            def get(self, key):
                return self.pl if key == "plant" else None

            def tabled(self, *a, **k):
                return []

        state = plant.build(self.project, self.results)
        from unittest import mock
        with mock.patch.object(chapters, "plant_plan_blocks", lambda ctx: []):
            parts = chapters.electrical(Ctx(state))
        text = repr(parts)
        self.assertIn("1.1.1", text)
        line = next(x["t"] for x in parts if x.get("k") == "p" and "1.1.1" in x.get("t", ""))
        self.assertEqual(line.count("Capannone"), 2, "both faces named")
        self.assertIn("%", line)


if __name__ == "__main__":
    unittest.main()
