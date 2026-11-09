"""A plant room drawn on a roof in the plan's backend (R352, study 37): the Building tool drawn inside a building's
outline makes a body standing on that roof (its base the roof height, 3 m high, moving with it); drawn outside, a
building as before; the room is picked before the building under it.

    python -m unittest quick.pianta.test_plant_room_plan
"""
import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

import _setup
from meridiana import i18n, model, move
from meridiana.quick.backend.plan import PlanController

APP = None


def setUpModule():
    global APP
    _setup.keep_global_state()
    APP = QApplication.instance() or QApplication([])
    i18n.setup('en')    # the names it reads are English: in the folder a module before had left Italian


class PlantRoomPlan(unittest.TestCase):
    def setUp(self):
        p = model.Project(name='Rooms')
        p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                          height=8.0))
        self.p = p
        self.c = PlanController(p, manage_layout=False)
        self.c.viewSettled(-5, -5, 65, 25, 0.05, 1.0)
        self.c.setPhase('model')

    def tearDown(self):
        self.c.close()

    def draw(self, ring):
        self.c.setTool('building')
        for x, y in ring:
            self.c.pointer(x, y, 1, 0.05)        # Ctrl: no snap
            self.c.click(x, y, 1)
        self.c.pointer(ring[0][0], ring[0][1], 1, 0.05)
        self.c.click(ring[0][0], ring[0][1], 1)

    def test_drawn_on_the_roof_it_stands_on_it(self):
        self.draw([(10, 5), (16, 5), (16, 10), (10, 10)])
        self.assertFalse(self.c.error)
        p = self.c.session.project
        self.assertEqual(len(p.buildings), 2)
        room = p.buildings[1]
        self.assertEqual((room.on, room.base, room.height, room.name), ('b1', 8.0, 11.0, 'Plant room 1'))
        self.assertEqual(move.members(p, 'b1'), ['b1', room.id])
        self.assertEqual(self.c.editor.pick((12.0, 7.0)), ('building', room.id, ''))     # the room first
        self.assertEqual(self.c.editor.pick((30.0, 15.0)), ('building', 'b1', ''))
        self.c.session.undo.undo()
        self.assertEqual(len(self.c.session.project.buildings), 1)

    def test_drawn_outside_it_is_a_building_from_the_ground(self):
        self.draw([(45, 0), (55, 0), (55, 10), (45, 10)])
        self.assertFalse(self.c.error)
        b = self.c.session.project.buildings[1]
        self.assertEqual((b.on, b.base, b.height, b.name), ('', 0.0, 6.0, 'Building 2'))

    def test_the_room_keeps_the_modules_of_the_roof_off_its_outline(self):
        self.draw([(10, 5), (16, 5), (16, 10), (10, 10)])
        p = self.c.session.project
        p.subfields.append(model.SubField('s1', 'Campo', [[1, 1], [39, 1], [39, 19], [1, 19]], building='b1',
                                          params={'tilt': 10.0}))
        result = p.fill(p.subfields[0])
        from shapely.geometry import Point, Polygon
        room = Polygon(p.buildings[1].footprint)
        self.assertTrue(result.modules)
        self.assertFalse(any(room.contains(Point(*m.centre)) for m in result.modules))


if __name__ == '__main__':
    unittest.main()
