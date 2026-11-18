"""R418, seguito (r22-modellazione). Daniel, 05/11/2026: «quando seleziono un vertice del sottocampo e lo deformo, i
pannelli devono ridisporsi in modo più furbo, non tutti disallineati». Le file restano sulla griglia del lato di
riferimento anche deformando il contorno:
- un sottocampo disegnato come moduli (a filo, R445) nasce su una griglia sola (colonne dritte), e un vertice trascinato
  tiene i moduli dove sono, toglie quelli che non ci stanno più e aggiunge sulla stessa griglia (come un lato, R445 B);
- un'area a posa automatica con l'azimut automatico non ruota le file quando il vertice cambia il rettangolo minimo."""
import math
import unittest

from shapely.geometry import Polygon

from meridiana import layout, manual, model
from meridiana.quick.backend.plan_edit import PlanEditor
from meridiana.session import ProjectSession

TRAPEZIO = [[0, 2.6], [16.2, 0], [20.0, 21.2], [0.6, 22.0]]


def columns(project, sf, result):
    """The column offsets (work u modulo the place step) of the modules of each row, rounded to the millimetre."""
    f, size, p = manual.frame(project, sf, result.rows)
    step = size.along + p.gap
    out = set()
    for row in result.rows:
        u_o = f.to_work(row.x, row.y)[0]
        out |= {round((u_o + u) % step, 3) % round(step, 3) for u in row.places}
    return out


def flush_project(ring):
    p = model.Project(name="prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[-10, -10], [60, -10], [60, 50], [-10, 50]],
                                      height=6.0))
    sf = p.new_subfield("s1", "S", ring, "b1")
    sf.filled = True
    p.subfields.append(sf)
    manual.make_flush(p, sf)
    return p, sf


class OneGrid(unittest.TestCase):
    def test_a_sub_field_drawn_as_modules_has_straight_columns(self):
        p, sf = flush_project(TRAPEZIO)
        r = p.fill(sf)
        self.assertGreater(r.count, 20)
        self.assertEqual(len(columns(p, sf, r)), 1, "every row on the same columns")


class VertexOfAFlushSubField(unittest.TestCase):
    def setUp(self):
        p, sf = flush_project([[0, 0], [20, 0], [20, 12], [0, 12]])
        self.session = ProjectSession(p)
        self.editor = PlanEditor(self.session)
        self.lay()
        self.editor.select("subfield", "s1")

    def lay(self):
        p = self.session.project
        self.result = p.fill(p.subfields[0])
        self.editor.set_results({"s1": self.result})
        return self.result

    def corners(self):
        return {m.key: [tuple(round(v, 4) for v in q) for q in m.corners] for m in self.result.modules}

    def test_a_vertex_dragged_out_keeps_the_modules_and_adds_on_the_grid(self):
        before = self.corners()
        ring = self.session.project.subfields[0].ring
        far = max(range(len(ring)), key=lambda i: ring[i][0] + ring[i][1])
        self.editor.move_vertex(far, (30.0, 20.0))
        sf = self.session.project.subfields[0]
        self.assertTrue(sf.flush and sf.manual)
        after = self.lay()
        now = self.corners()
        for key, corners in before.items():
            self.assertEqual(now.get(key), corners, key)
        self.assertGreater(after.count, len(before))
        self.assertEqual(len(columns(self.session.project, sf, after)), 1)
        self.assertEqual(self.session.undo.count(), 1)

    def test_a_vertex_dragged_in_takes_out_only_what_no_longer_fits(self):
        before = self.corners()
        ring = self.session.project.subfields[0].ring
        far = max(range(len(ring)), key=lambda i: ring[i][0] + ring[i][1])
        x, y = ring[far]
        self.editor.move_vertex(far, (x - 6.0, y - 4.0))
        after = self.lay()
        now = self.corners()
        self.assertLess(after.count, len(before))
        for key, corners in now.items():
            self.assertEqual(before.get(key), corners, key)


class VertexOfAnArea(unittest.TestCase):
    def test_the_rows_do_not_turn_with_the_outline(self):
        p = model.Project(name="prova")
        ring = [[0, 0], [30, 0], [30, 18], [0, 18]]
        p.subfields.append(model.SubField(id="s1", name="Campo", ring=ring, filled=True,
                                          params=model.new_params("ground")))
        session = ProjectSession(p)
        editor = PlanEditor(session)
        editor.set_results({"s1": p.fill(p.subfields[0])})
        before = p.fill(p.subfields[0]).azimuth
        moved = [list(q) for q in ring]
        moved[3] = [-20.0, 40.0]   # R551: [10, 30] made the two least rectangles equal, and a tie faces South now
        sf = session.project.subfields[0]
        self.assertGreater(abs(layout.row_azimuth(Polygon(moved), p.surface_of(sf), p.fill_params(sf)) - before), 1.0,
                           "precondition: the automatic azimuth of the new outline is another")
        editor.select("subfield", "s1")
        editor.move_vertex(3, (-20.0, 40.0))
        sf = session.project.subfields[0]
        self.assertEqual(sf.ring[3], [-20.0, 40.0])
        self.assertTrue(math.isclose(session.project.fill(sf).azimuth, before, abs_tol=0.01))
        session.undo.undo()
        self.assertNotIn("azimuth", session.project.subfields[0].params)


if __name__ == "__main__":
    unittest.main()
