"""Persistent BIM identity and independent support planes, including undo and actual layout heights."""
import copy
import math
import unittest
import uuid

import _setup  # noqa: F401
from _fixtures import capannone
from meridiana import mesh, model, move, session


class Support(unittest.TestCase):
    def test_new_projects_have_distinct_persistent_bim_namespaces(self):
        p, q = model.Project(), model.Project()
        self.assertNotEqual(p.bim_id, q.bim_id)
        uuid.UUID(p.bim_id)
        self.assertEqual(model.Project.from_json(p.to_json()).bim_id, p.bim_id)

    def test_legacy_migration_is_repeatable_and_does_not_mutate_its_input(self):
        raw = capannone().to_json()
        raw.pop('bim_id', None)
        raw['version'] = 18
        before = copy.deepcopy(raw)
        a, b = model.Project.from_json(raw), model.Project.from_json(raw)
        self.assertEqual(a.bim_id, b.bim_id)
        self.assertEqual(raw, before)
        self.assertIsNone(a.subfields[0].support)

    def test_independent_plane_preserves_host_and_drives_actual_layout_and_undo(self):
        p = capannone()
        sf = p.subfields[0]
        original = p.surface_of(sf)
        host = (sf.building, sf.pitch)
        sf.params = {**sf.params, 'mounting': 'coplanar', 'edge': 0.0}
        sf.filled = True
        s = session.ProjectSession(p)
        support = model.SupportPlane(z0=14.0, x0=5.0, y0=6.0, tilt=17.0, azimuth=33.0)
        s.edit('Plane', lambda project: setattr(project.subfields[0], 'support', support))
        sf = s.project.subfields[0]
        self.assertEqual((sf.building, sf.pitch), host)
        self.assertEqual(s.project.surface_of(sf).azimuth, 33.0)
        result = s.project.fill(sf)
        self.assertTrue(result.modules)
        for pm in result.modules:
            self.assertAlmostEqual(pm.z, s.project.surface_of(sf).z(*pm.centre) + sf.layout_params().stand_off)
        s.undo.undo()
        self.assertIsNone(s.project.subfields[0].support)
        self.assertEqual(s.project.surface_of(s.project.subfields[0]), original)
        s.undo.redo()
        self.assertIsInstance(s.project.subfields[0].support, model.SupportPlane)
        self.assertEqual(s.project.subfields[0].support.azimuth, 33.0)

    def test_disabled_plane_keeps_values_and_returns_to_host_surface(self):
        p = capannone()
        sf = p.subfields[0]
        original = p.surface_of(sf)
        sf.support = model.SupportPlane(enabled=False, z0=23.0, azimuth=45.0, tilt=20.0)
        self.assertEqual(p.surface_of(sf), original)
        back = model.Project.from_json(p.to_json())
        self.assertFalse(back.subfields[0].support.enabled)
        self.assertEqual(back.subfields[0].support.z0, 23.0)

    def test_bad_support_values_are_rejected_in_every_variant(self):
        for field, value in [('tilt', 90), ('azimuth', 181), ('z0', math.inf),
                             ('x0', math.nan), ('y0', 1e8), ('enabled', 'yes')]:
            p = capannone()
            raw = p.to_json()
            raw['variants'][0]['design']['subfields'][0]['support'] = {field: value}
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'support'):
                model.Project.from_json(raw)

    def test_independent_plane_moves_and_rotates_with_its_subfield(self):
        p = capannone()
        sf = p.subfields[0]
        sf.support = model.SupportPlane(z0=8.0, x0=1.0, y0=2.0, tilt=20.0, azimuth=45.0)
        host = sf.building
        move.translate(p, 'subfield', sf.id, 100.0, 200.0)(p)
        self.assertEqual((sf.support.x0, sf.support.y0), (101.0, 202.0))
        move.rotate(p, 'subfield', sf.id, 0.0, 0.0, 90.0)(p)
        self.assertAlmostEqual(sf.support.x0, -202.0)
        self.assertAlmostEqual(sf.support.y0, 101.0)
        self.assertEqual(sf.support.azimuth, -45.0)
        self.assertEqual(sf.building, host)
        self.assertAlmostEqual(move.height(p, 'subfield', sf.id, (-202, 101)), 8.0)

    def test_support_plane_is_real_geometry_in_the_scene_without_modules(self):
        p = model.Project()
        sf = model.SubField(id='s1', name='Plane', ring=[[0, 0], [12, 0], [12, 12], [0, 12]],
                            support=model.SupportPlane(z0=8, tilt=20, azimuth=33))
        p.subfields = [sf]
        geometry, modules, _edges = mesh.project_scene(p, {})
        self.assertEqual(len(modules), 0)
        self.assertGreater(len(geometry[0]), 0)
        for x, z, minus_y in geometry[0]:
            self.assertAlmostEqual(float(z), p.surface_of(sf).z(float(x), -float(minus_y)), places=4)

    def test_support_follows_its_free_pitch_and_view_aids_use_its_height(self):
        from meridiana import viewaids
        p = capannone()
        b, sf = p.buildings[0], p.subfields[0]
        b.roof = model.Roof(type='free', free_pitches=[
            dict(id='p1', ring=[[1, 1], [10, 1], [10, 10], [1, 10]], tilt=10, eave=6, eave_side=0)])
        sf.ring = [[2, 2], [8, 2], [8, 8], [2, 8]]
        sf.pitch = 0
        sf.support = model.SupportPlane(z0=9, x0=5, y0=5, tilt=22, azimuth=31)
        move.translate(p, 'pitch', b.id+':p1', 0.5, 0)(p)
        self.assertAlmostEqual(sf.support.x0, 5.5)
        self.assertAlmostEqual(viewaids.height_at(p, 'subfield', sf.id, 5.5, 5), 9)
        points = viewaids.outline(p, {}, 'subfield', sf.id)
        for x, z, minus_y in points.reshape(-1, 3):
            self.assertAlmostEqual(float(z), p.surface_of(sf).z(float(x), -float(minus_y)) + viewaids.LIFT, places=4)


if __name__ == '__main__':
    unittest.main()
