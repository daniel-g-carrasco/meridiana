"""The plan's «Place» mode for an imported IFC model (R454): the outlines follow the pointer and take the corner of the
building drawn, R and the wheel turn them, a click lays them in one undo step, Esc gives the import up; on the
building drawn the question (replace, keep both, beside, go on); the coordinates with the distance and the warning
beyond FAR_KM, the file's georeferencing proposed first; the help in the status bar. A model built by the test.

    python -m unittest quick.pianta.test_ifc_place_plan
"""
import unittest

from PySide6.QtCore import QCoreApplication

from meridiana import ifc_import, ifc_place, model
from meridiana.quick.backend.plan import PlanController

APP = None
MPP = 0.05


def setUpModule():
    global APP
    APP = QCoreApplication.instance() or QCoreApplication([])


def found(conversion=None):
    ring = [[100.0, 100.0], [120.0, 100.0], [120.0, 110.0], [100.0, 110.0]]
    return {"schema": "IFC4", "application": "Prova", "unit_m": 1.0, "true_north": 0.0, "map": conversion,
            "site": {"lat": 45.521, "lon": 9.041, "elevation": 0.0, "name": "Cantiere", "placement": [0.0, 0.0, 0.0]},
            "sites": 1, "address": "", "obstacles": [], "counts": {}, "supports": [], "times": {"total": 1.0},
            "buildings": [{"name": "Palazzetto", "ifc": "x", "ground": 0.0, "source": "roof", "footprint": ring,
                           "pitches": [{"ring": ring, "normal": [0.0, 0.0, 1.0], "point": [110.0, 105.0, 8.0],
                                        "area": 200.0, "holes": 0, "owners": [1]}]}]}


class PlacePlan(unittest.TestCase):
    def setUp(self):
        p = model.Project(name='Posa IFC', site=model.Site(lat=45.52, lon=9.04, address='Rho'))
        p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                          height=8.0))
        self.c = PlanController(p, manage_layout=False)
        self.c.viewSettled(-20, -20, 120, 60, MPP, 1.0)
        self.c.setPhase('model')
        self.data = found()
        self.plan = ifc_import.plan(self.data, p, 'hand', name='Palazzetto', source_name='palazzetto.ifc')
        self.place = ifc_import.place_of(self.data)
        self.asked, self.done = [], []
        self.c.placeAsked.connect(lambda title, text: self.asked.append(text))
        self.c.modelImported.connect(lambda ids: self.done.append(list(ids)))
        self.c.placeModel(self.plan, self.place, True, 'Palazzetto')

    def tearDown(self):
        self.c.close()

    def ghost(self):
        return [o for o in self.c.draftObjects if o.get('kind') == 'ghost']

    def test_it_follows_the_pointer_takes_a_corner_and_a_click_lays_it_in_one_undo(self):
        self.assertTrue(self.c.placing['active'])
        self.assertTrue(self.c.collecting)
        self.assertIn('Esc', self.c.hint)
        self.c.pointer(50.2, 5.1, 0, MPP)                 # its SW corner 0,2 m from the shed's SE corner
        self.assertTrue(self.ghost())
        self.assertEqual(self.c.placer.snap.kind, 'corner')
        self.c.click(50.2, 5.1, 0)
        self.assertEqual(self.asked, [])
        [ids] = self.done
        p = self.c.session.project
        self.assertEqual(len(p.buildings), 2)
        xs = [q[0] for q in p.building(ids[0]).footprint]
        ys = [q[1] for q in p.building(ids[0]).footprint]
        self.assertEqual((min(xs), min(ys)), (40.0, 0.0))
        self.assertFalse(self.c.placing['active'])
        self.assertEqual(self.c.editor.selection[:2], ('building', ids[0]))
        self.c.session.undo.undo()
        self.assertEqual([b.id for b in self.c.session.project.buildings], ['b1'])

    def test_ctrl_takes_no_snap_r_and_the_wheel_turn_it(self):
        self.c.pointer(50.2, 5.1, 1, MPP)                 # Ctrl
        self.assertEqual(self.c.placer.snap.kind, '')
        self.c.key('R', 'r', 0)
        self.assertAlmostEqual(self.c.placer.pl.turn, 15.0)
        self.c.placeWheel(-1.0, 2)                        # Shift held: one notch back
        self.c.placeWheel(-1.0, 3)                        # Shift and Ctrl: 5 degrees
        self.assertAlmostEqual(self.c.placer.pl.turn, -5.0)
        self.assertIn('°', self.c.hint)

    def test_esc_gives_the_import_up(self):
        said = []
        self.c.notice.connect(said.append)
        self.c.pointer(70.0, 30.0, 0, MPP)
        self.c.key('Escape', '', 0)
        self.assertFalse(self.c.placing['active'])
        self.assertEqual(len(self.c.session.project.buildings), 1)
        self.assertEqual(self.c.draftObjects and [o for o in self.c.draftObjects if o.get('kind') == 'ghost'], [])
        self.assertTrue(said)

    def test_on_the_shed_the_question_and_its_four_answers(self):
        self.c.pointer(20.0, 10.0, 1, MPP)
        from meridiana import view_colours
        self.assertEqual(self.ghost()[1]['stroke'], view_colours.PHOTO['sweep_remove'])      # red over the shed
        self.c.pointer(80.0, 40.0, 1, MPP)
        self.assertEqual(self.ghost()[1]['stroke'], view_colours.PHOTO['sel'])
        self.c.pointer(20.0, 10.0, 1, MPP)
        self.c.click(20.0, 10.0, 1)
        self.assertEqual(len(self.asked), 1)
        self.assertIn('Capannone', self.asked[0])
        self.assertTrue(self.c.placing['asking'])
        self.c.placeAnswer('back')
        self.assertTrue(self.c.placing['active'] and not self.c.placing['asking'])
        self.c.click(20.0, 10.0, 1)
        self.c.placeAnswer('beside')
        p = self.c.session.project
        self.assertEqual(len(p.buildings), 2)
        self.assertEqual(ifc_place.overlaps_rings(model.Project(buildings=[p.buildings[0]]), [p.buildings[1].footprint]), [])
        self.c.session.undo.undo()
        self.c.placeModel(self.plan, self.place, True)
        self.c.click(20.0, 10.0, 1)
        self.c.placeAnswer('replace')
        self.assertEqual([b.name for b in self.c.session.project.buildings], ['Palazzetto'])
        self.c.session.undo.undo()
        self.c.placeModel(self.plan, self.place, True)
        self.c.click(20.0, 10.0, 1)
        self.c.placeAnswer('keep')
        self.assertEqual(len(self.c.session.project.buildings), 2)

    def test_the_coordinates_with_the_distance_the_warning_and_the_files_proposal(self):
        info = self.c.placing
        self.assertEqual([s['value'] for s in info['systems']], ['utm', 'latlon', 'local'])
        self.assertIsNotNone(info['proposal'])                 # a named site: the file's place first
        self.assertEqual(info['proposal']['system'], 'latlon')
        near = self.c.checkCoordinates('local', '60', '30', '0')
        self.assertTrue(near['ok'] and not near['warning'], near)
        self.assertIn('km', near['text'])
        far = self.c.checkCoordinates('latlon', '45,62', '9,04', '0')
        self.assertTrue(far['ok'] and far['warning'], far)
        wrong = self.c.checkCoordinates('latlon', 'abc', '9', '0')
        self.assertFalse(wrong['ok'])
        self.assertTrue(self.c.placeCoordinates('local', '60', '30', '10'))
        self.assertFalse(self.c.placing['follow'])
        self.assertEqual(float(self.c.placing['values']['local']['a'].replace(',', '.')), 60.0)
        self.c.pointer(0.0, 0.0, 0, MPP)                      # it no longer follows the mouse
        self.assertEqual(self.c.placer.pl.at, (60.0, 30.0))
        self.c.key('Enter', '', 0)
        [ids] = self.done
        ref = self.c.session.project.resources['ifc_reference']
        self.assertEqual(ref['shift'], [60.0, 30.0])
        import math
        (x0, y0), (x1, y1) = self.c.session.project.building(ids[0]).footprint[:2]
        self.assertAlmostEqual(math.degrees(math.atan2(y1 - y0, x1 - x0)), 10.0, places=2)

    def test_a_model_far_away_is_refused_with_the_reason(self):
        self.assertFalse(self.c.placeCoordinates('local', '2000000', '0', '0'))
        self.assertIn('km', self.c.hint)


if __name__ == '__main__':
    unittest.main()
