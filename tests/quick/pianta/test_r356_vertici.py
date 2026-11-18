"""R356 (Daniel): «non c'è la possibilità di inserire più vertici alla volta». Letta dalla verifica del registro del
07/11 come «Aggiungi un vertice», che mancava: col tasto destro su un lato dell'oggetto scelto (edificio, sottocampo,
esclusione) il sottomenu «Aggiungi vertici su questo lato» mette un vertice dove si è cliccato, uno a metà, oppure
divide il lato in tre o quattro parti uguali (più vertici alla volta). Un solo Annulla. Sull'edificio i dati legati ai
lati e ai vertici seguono: i tipi dei lati del tetto, il lato di gronda della falda unica, le quote del piano inclinato."""
import unittest

from PySide6.QtWidgets import QApplication

from meridiana import model, sides
from meridiana.quick.backend.plan import PlanController
from meridiana.quick.backend.plan_edit import PlanEditor
from meridiana.session import ProjectSession

APP = None
RECT = [[0, 0], [30, 0], [30, 20], [0, 20]]


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication([])


class Insert(unittest.TestCase):
    def test_a_side_divided_in_equal_parts(self):
        new, added = sides.insert(RECT, 0, parts=3)
        self.assertEqual(added, 2)
        self.assertEqual(new, [[0, 0], [10.0, 0.0], [20.0, 0.0], [30, 0], [30, 20], [0, 20]])

    def test_one_vertex_where_clicked_on_the_closing_side(self):
        new, added = sides.insert(RECT, 3, at=(0.4, 5.0))
        self.assertEqual(added, 1)
        self.assertEqual(new[-1], [0.0, 5.0])
        self.assertEqual(len(new), 5)

    def test_a_point_on_a_corner_adds_nothing(self):
        with self.assertRaises(ValueError):
            sides.insert(RECT, 0, at=(0.0, 0.0))


class OnTheBuilding(unittest.TestCase):
    def editor(self, roof, **kw):
        p = model.Project(name="prova")
        p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[list(q) for q in RECT], height=6.0,
                                          roof=roof, **kw))
        session = ProjectSession(p)
        e = PlanEditor(session)
        e.select("building", "b1")
        return session, e

    def test_the_sides_of_the_roof_follow(self):
        session, e = self.editor(model.Roof(type="gable", tilt=20.0, edges=["eave", "gable", "eave", "gable"]))
        e.apply_command({"type": "add_vertices", "kind": "building", "oid": "b1", "index": 1, "parts": 2})
        b = session.project.buildings[0]
        self.assertEqual(b.footprint[2], [30.0, 10.0])
        self.assertEqual(b.roof.edges, ["eave", "gable", "gable", "eave", "gable"])
        self.assertEqual(session.undo.count(), 1)
        session.undo.undo()
        self.assertEqual(len(session.project.buildings[0].footprint), 4)

    def test_the_eave_of_a_mono_pitch_stays_on_its_side(self):
        session, e = self.editor(model.Roof(type="mono", tilt=10.0, eave_side=2))
        e.apply_command({"type": "add_vertices", "kind": "building", "oid": "b1", "index": 0, "parts": 4})
        self.assertEqual(session.project.buildings[0].roof.eave_side, 5)

    def test_the_inclined_plane_keeps_its_heights(self):
        session, e = self.editor(model.Roof(type="flat", plane=[6.0, 8.0, 8.0, 6.0]))
        e.apply_command({"type": "add_vertices", "kind": "building", "oid": "b1", "index": 0, "parts": 2})
        self.assertEqual(session.project.buildings[0].roof.plane, [6.0, 7.0, 8.0, 8.0, 6.0])


class FromTheMenu(unittest.TestCase):
    def setUp(self):
        p = model.Project(name="Menu")
        p.buildings.append(model.Building(id="b1", name="Roof", footprint=[list(q) for q in RECT], height=6.0))
        self.c = PlanController(p, manage_layout=False)
        self.c.refresh()
        self.c.editor.set_phase("modelling")
        self.c.editor.select("building", "b1")
        self.c.refresh()

    def tearDown(self):
        self.c.close()

    def test_the_submenu_on_a_side_adds_vertices_once_undone(self):
        self.c.contextAt(12.0, 0.05)
        items = {r["command"]: r for r in self.c.contextItems if not r["separator"]}
        for command in ("add_vertex_here", "add_vertices_2", "add_vertices_3", "add_vertices_4"):
            self.assertIn(command, items)
        self.assertTrue(items["add_vertices_3"]["menu"])
        self.c.contextCommand("add_vertices_3")
        self.assertEqual(self.c.session.project.buildings[0].footprint[:4], [[0, 0], [10.0, 0.0], [20.0, 0.0], [30, 0]])
        self.c.contextAt(12.0, 0.05)
        self.c.contextCommand("add_vertex_here")
        self.assertIn([12.0, 0.0], self.c.session.project.buildings[0].footprint)
        self.c.session.undo.undo()
        self.c.session.undo.undo()
        self.assertEqual(len(self.c.session.project.buildings[0].footprint), 4)

    def test_no_submenu_away_from_a_side(self):
        self.c.contextAt(15.0, 10.0)
        self.assertNotIn("add_vertices_2", [r["command"] for r in self.c.contextItems])



class MoreCornersTogether(unittest.TestCase):
    """R356, precisazione di Daniel dell'08/11: «intendevo selezionare e muovere più vertici alla volta». The rule of
    the selection (R529) on the corners of a building, a sub-field or an exclusion; moved together by a drag, the
    arrows or a measure; one Undo."""

    def setUp(self):
        p = model.Project(name="Vertici")
        p.buildings.append(model.Building(id="b1", name="Roof", footprint=[list(q) for q in RECT], height=6.0))
        p.exclusions.append(model.ExclusionItem(id="e1", ring=[[2, 2], [6, 2], [6, 6], [2, 6]], kind="vent",
                                                building="b1"))
        self.c = PlanController(p, manage_layout=False)
        self.c.refresh()
        self.c.editor.set_phase("modelling")
        self.choose("building", "b1")

    def choose(self, kind, oid):
        self.c.editor.select(kind, oid)
        self.c.refresh()

    def tearDown(self):
        self.c.close()

    def test_click_starts_again_shift_adds_ctrl_toggles(self):
        self.assertTrue(self.c.chooseCorner(1, 0))
        self.assertEqual(self.c.chosenCorners, [1])
        self.assertFalse(self.c.chooseCorner(1, 0))           # the second click goes to what lies there (R529)
        self.c.chooseCorner(2, 2)
        self.c.chooseCorner(2, 2)
        self.assertEqual(self.c.chosenCorners, [1, 2])        # Shift adds; once in, it stays
        self.c.chooseCorner(1, 1)
        self.assertEqual(self.c.chosenCorners, [2])           # Ctrl takes away
        self.c.chooseCorner(3, 1)
        self.assertEqual(self.c.chosenCorners, [2, 3])        # and adds
        self.c.chooseCorner(0, 0)
        self.assertEqual(self.c.chosenCorners, [0])           # a plain click starts again

    def test_a_window_takes_adds_and_takes_away(self):
        self.c.chooseCorners([1, 2], 0)
        self.assertEqual(self.c.chosenCorners, [1, 2])
        self.c.chooseCorners([3], 2)
        self.assertEqual(self.c.chosenCorners, [1, 2, 3])
        self.c.chooseCorners([2, 3], 1)
        self.assertEqual(self.c.chosenCorners, [1])
        self.c.chooseCorners([0], 0)
        self.assertEqual(self.c.chosenCorners, [0])

    def test_moved_together_in_one_undo_and_still_chosen(self):
        self.c.chooseCorners([1, 2], 0)
        undo = self.c.session.undo.count()
        self.c.moveCorners(2.0, 0.0)
        b = self.c.session.project.buildings[0]
        self.assertEqual(b.footprint, [[0, 0], [32.0, 0.0], [32.0, 20.0], [0, 20]])
        self.assertEqual(self.c.session.undo.count(), undo + 1)
        self.assertEqual(self.c.chosenCorners, [1, 2])        # the arrows can go on
        self.assertTrue(self.c.cornersTyped("0; -1,5"))
        self.assertEqual(self.c.session.project.buildings[0].footprint[1:3], [[32.0, -1.5], [32.0, 18.5]])
        self.assertTrue(self.c.cornersTyped("1"))             # along the last move: South
        self.assertEqual(self.c.session.project.buildings[0].footprint[1], [32.0, -2.5])
        self.assertFalse(self.c.cornersTyped("a; b"))
        for _i in range(3):
            self.c.session.undo.undo()
        self.assertEqual(self.c.session.project.buildings[0].footprint, [list(q) for q in RECT])

    def test_the_corners_of_an_exclusion_and_a_new_selection_lets_them_go(self):
        self.c.chooseCorners([0, 1], 0)
        self.choose("exclusion", "e1")
        self.assertEqual(self.c.chosenCorners, [])            # another thing: none of its corners chosen
        self.c.chooseCorners([2, 3], 0)
        self.c.moveCorners(0.0, 1.0)
        self.assertEqual(self.c.session.project.exclusions[0].ring, [[2, 2], [6, 2], [6.0, 7.0], [2.0, 7.0]])

    def test_a_move_that_crosses_the_outline_is_refused(self):
        self.c.chooseCorners([1], 0)
        self.c.moveCorners(-40.0, 0.0)
        self.assertEqual(self.c.session.project.buildings[0].footprint, [list(q) for q in RECT])


if __name__ == "__main__":
    unittest.main()
