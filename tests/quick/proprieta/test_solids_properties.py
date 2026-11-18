"""Beyond the 2,5D model in the properties (study 37): the base height and what a body stands on (R453, R352), the
bodies of one building (R440), the inclined flat roof made level again (R455) and the saddle roof's parameters.

    python -m unittest quick.proprieta.test_solids_properties
"""
import unittest

from _fixtures import capannone
from meridiana import model
from meridiana import roof_vertices as rv
from meridiana.session import ProjectSession


class SolidsProperties(unittest.TestCase):
    def setUp(self):
        from meridiana.quick.backend.properties import PropertiesBackend
        p = capannone()
        p.buildings.append(model.Building(id='b2', name='Locale', footprint=[[10, 5], [16, 5], [16, 10], [10, 10]],
                                          height=12.0, group='ifc1'))
        p.buildings.append(model.Building(id='b3', name='Corpo', footprint=[[50, 0], [60, 0], [60, 10], [50, 10]],
                                          height=5.0, group='ifc1'))
        self.session = ProjectSession(p)
        self.backend = PropertiesBackend(self.session)
        self.addCleanup(self.backend.close)

    def select(self, bid):
        self.session.select('building', bid)

    def keys(self):
        return [f['id'] for s in self.backend.schema for f in s['fields']] if isinstance(self.backend.schema, list) else None

    def test_the_base_and_what_it_stands_on(self):
        self.select('b2')
        self.assertIsNotNone(self.backend.field('base'))
        self.assertTrue(self.backend.commit('on', 'b1'))
        room = self.session.project.buildings[1]
        self.assertEqual((room.on, room.base), ('b1', 9.5))      # the shed's roof under it
        self.assertFalse(self.backend.commit('base', '12 m'))     # above its own roof
        self.assertTrue(self.backend.error)
        self.assertTrue(self.backend.commit('base', '10 m'))
        self.assertEqual(room.base, 10.0)
        self.assertTrue(self.backend.commit('on', ''))
        self.assertEqual((room.on, room.base), ('', 0.0))
        self.backend.undo()
        room = self.session.project.buildings[1]              # the project is built again from the snapshot
        self.assertEqual((room.on, room.base), ('b1', 10.0))

    def test_the_bodies_of_an_imported_model_as_one_building(self):
        self.select('b2')
        self.assertIsNotNone(self.backend.field('bodies_as_one'))
        self.backend.trigger('bodies_as_one')
        p = self.session.project
        self.assertEqual([b.part_of for b in p.buildings], ['', '', 'b2'])
        self.assertEqual(p.shown_name(p.buildings[2]), 'Locale (body 2)')
        self.assertEqual(len(p.wholes()), 2)
        self.select('b3')
        self.assertIsNone(self.backend.field('bodies_as_one'))
        self.assertTrue(self.backend.commit('part_of', ''))
        self.assertEqual(self.session.project.buildings[2].part_of, '')
        self.assertTrue(self.backend.commit('part_of', 'b1'))
        self.assertEqual(self.session.project.buildings[2].part_of, 'b1')

    def test_the_inclined_flat_roof_says_so_and_goes_level_again(self):
        p = self.session.project
        b = p.buildings[0]
        self.session.edit('tilt', lambda q: rv.set_height(q, 'b1', rv.handles(q.buildings[0]).__getitem__(2).corners[0], 10.5))
        self.select('b1')
        self.assertIsNotNone(self.backend.field('plane_note'))
        self.assertEqual(b.roof.type, 'flat')
        self.assertTrue(self.backend.commit('height', '10 m'))     # the whole plane goes up by half a metre
        self.assertEqual([round(z, 2) for z in b.roof.plane], [10.0, 10.5, 11.0, 10.5])
        self.backend.trigger('flatten')
        self.assertIsNone(b.roof.plane)
        self.assertIsNone(self.backend.field('plane_note'))
        self.assertEqual(b.height, 10.0)

    def test_the_saddle_roof_and_its_parameters(self):
        self.select('b1')
        self.assertTrue(self.backend.commit('roof.type', 'saddles'))
        b = self.session.project.buildings[0]
        self.assertEqual(b.roof.type, 'saddles')
        self.assertEqual(b.roof.saddles['direction'], 90.0)        # along the long side
        n = len(b.pitches())
        self.assertGreater(n, 10)
        self.assertIsNotNone(self.backend.field('saddles.band'))
        self.assertTrue(self.backend.commit('saddles.band', '5'))
        self.assertEqual(b.roof.saddles['band'], 5.0)
        self.assertLess(len(b.pitches()), n)
        self.assertTrue(self.backend.commit('saddles.direction', '0'))
        self.assertEqual(b.roof.saddles['direction'], 0.0)
        self.assertTrue(self.backend.commit('roof.type', 'flat'))
        self.assertEqual(b.roof.type, 'flat')
        self.assertEqual(len(b.pitches()), 1)


if __name__ == '__main__':
    unittest.main()
