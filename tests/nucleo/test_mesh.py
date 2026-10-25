"""Triangles for the 3D view: the roof covered once, walls up to the roof, modules turned the right way."""

import math
import unittest

import _setup  # noqa: F401
import numpy as np

from meridiana import layout, mesh, roofs

HOUSE = [(0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0)]
L_SHAPE = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (4.0, 4.0), (4.0, 10.0), (0.0, 10.0)]


def area_of_triangles(ring, tris):
    total = 0.0
    for i, j, k in tris:
        (ax, ay), (bx, by), (cx, cy) = ring[i], ring[j], ring[k]
        total += abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) / 2
    return total


class Triangulation(unittest.TestCase):
    def test_a_concave_outline_is_covered_exactly_once(self):
        tris = mesh.triangulate(L_SHAPE)
        self.assertEqual(len(tris), len(L_SHAPE) - 2)
        self.assertAlmostEqual(area_of_triangles(L_SHAPE, tris), abs(mesh.signed_area(L_SHAPE)), places=9)

    def test_a_clockwise_outline_too(self):
        ring = list(reversed(L_SHAPE))
        self.assertAlmostEqual(area_of_triangles(ring, mesh.triangulate(ring)), 64.0, places=9)


class Buildings(unittest.TestCase):
    def test_a_flat_roof_faces_up_and_the_walls_face_out(self):
        pos, nor, _col = mesh.building_triangles(HOUSE, roofs.flat(HOUSE, 6.0))
        self.assertEqual(len(pos), (2 + 4 * 2) * 3)          # two roof triangles, two per wall
        roof = nor[:6]
        self.assertTrue(np.all(roof[:, 1] > 0.99))
        centre = np.array([6.0, 3.0, -4.0])
        walls_pos, walls_nor = pos[6:].reshape(-1, 3, 3), nor[6::3]
        for tri_pos, n in zip(walls_pos, walls_nor, strict=True):
            self.assertGreater(float(np.dot(tri_pos.mean(axis=0) - centre, n)), 0)

    def test_an_l_shaped_building_faces_out_on_its_inner_corner(self):
        pos, nor, _col = mesh.building_triangles(L_SHAPE, roofs.flat(L_SHAPE, 6.0))
        # the side from (10, 4) to (4, 4) faces North (model +y, Qt -z)
        for tri_pos, n in zip(pos.reshape(-1, 3, 3), nor[::3], strict=True):
            xs, zs = tri_pos[:, 0], tri_pos[:, 2]
            if np.allclose(zs, -4.0) and xs.min() >= 4.0 - 1e-6:
                self.assertLess(n[2], -0.99)

    def test_gable_walls_rise_to_the_ridge(self):
        pitches = roofs.gable(HOUSE, eave=6.0, tilt=30.0)
        pos, _nor, _col = mesh.building_triangles(HOUSE, pitches)
        ridge = 6.0 + 4.0 * math.tan(math.radians(30))
        self.assertAlmostEqual(float(pos[:, 1].max()), ridge, places=5)

    def test_the_wall_of_a_gable_end_is_a_gable_with_no_code_of_its_own(self):
        """Task 16a: the skeleton's faces put the ridge's end on the gable side, and the wall rises there by
        itself: two pieces, eave to ridge and ridge to eave, two triangles each. On an L too."""
        for footprint, x, ridge in ((HOUSE, 12.0, 6.0 + 4.0 * math.tan(math.radians(30))),
                                    ([(0, 0), (20, 0), (20, 8), (8, 8), (8, 18), (0, 18)], 20.0,
                                     6.0 + 4.0 * math.tan(math.radians(30)))):
            with self.subTest(footprint=footprint):
                pitches = roofs.gable(footprint, eave=6.0, tilt=30.0)
                pos, _nor, _col = mesh.building_triangles(footprint, pitches)
                tris = pos.reshape(-1, 3, 3)
                wall = [t for t in tris if np.allclose(t[:, 0], x, atol=1e-5)]      # Qt x is the model's x
                self.assertEqual(len(wall), 4)
                self.assertAlmostEqual(max(float(t[:, 1].max()) for t in wall), ridge, places=5)


class Obstacles(unittest.TestCase):
    def test_an_obstacle_has_a_top_and_sides_facing_out(self):
        pos, nor, _col = mesh.prism_triangles(L_SHAPE, 6.0, 7.5)
        tops = nor[::3][:, 1] > 0.99
        self.assertEqual(int(tops.sum()), len(L_SHAPE) - 2)
        self.assertAlmostEqual(float(pos[:, 1].max()), 7.5, places=6)
        self.assertAlmostEqual(float(pos[:, 1].min()), 6.0, places=6)
        # the side from (10, 4) to (4, 4) faces North (model +y, Qt -z)
        for tri_pos, n in zip(pos.reshape(-1, 3, 3), nor[::3], strict=True):
            if np.allclose(tri_pos[:, 2], -4.0) and tri_pos[:, 0].min() >= 4.0 - 1e-6:
                self.assertLess(n[2], -0.99)


class Modules(unittest.TestCase):
    def test_a_south_facing_tilted_module_leans_back_towards_north(self):
        m = layout.PlacedModule(row=0, slot=0, group=0, corners=[], centre=(5.0, 3.0), z=7.0, tilt=30.0, azimuth=0.0)
        t = mesh.module_table([m], along=1.134, across=2.278)
        self.assertEqual(t.shape, (1, 20))
        rows = t[0, [0, 1, 2, 4, 5, 6, 8, 9, 10]].reshape(3, 3)
        # the local +z axis (up the module) once turned: towards the face, so South (Qt +z) and down
        z_axis = rows[:, 2] / np.linalg.norm(rows[:, 2])
        self.assertGreater(z_axis[2], 0.8)
        self.assertLess(z_axis[1], -0.4)
        self.assertEqual(tuple(t[0, [3, 7, 11]]), (5.0, 7.0, -3.0))

    def test_an_east_facing_module_faces_east(self):
        m = layout.PlacedModule(row=0, slot=0, group=0, corners=[], centre=(0.0, 0.0), z=0.0, tilt=0.0, azimuth=-90.0)
        rows = mesh.module_table([m], 1.0, 2.0)[0, [0, 1, 2, 4, 5, 6, 8, 9, 10]].reshape(3, 3)
        z_axis = rows[:, 2] / np.linalg.norm(rows[:, 2])
        self.assertAlmostEqual(float(z_axis[0]), 1.0, places=6)

    def test_a_module_turned_by_hand_has_its_long_side_along_the_row(self):
        upright = layout.PlacedModule(row=0, slot=0, group=0, corners=[], centre=(0.0, 0.0), z=0.0, tilt=0.0,
                                      azimuth=0.0)
        turned = layout.PlacedModule(row=0, slot=1, group=0, corners=[], centre=(3.0, 0.0), z=0.0, tilt=0.0,
                                     azimuth=0.0, turned=True)
        t = mesh.module_table([upright, turned], along=1.134, across=2.278)
        for row, (along, across) in zip(t, ((1.134, 2.278), (2.278, 1.134)), strict=True):
            m = row[[0, 1, 2, 4, 5, 6, 8, 9, 10]].reshape(3, 3)
            self.assertAlmostEqual(float(np.linalg.norm(m[:, 0])) * 100.0, along, places=4)
            self.assertAlmostEqual(float(np.linalg.norm(m[:, 2])) * 100.0, across, places=4)
        edges = mesh.module_edges(turned, 1.134, 2.278)
        xs = edges[:, :, 0].ravel()
        self.assertAlmostEqual(float(xs.max() - xs.min()), 2.278, places=4)

    def test_selected_modules_are_coloured(self):
        m = layout.PlacedModule(row=0, slot=0, group=0, corners=[], centre=(0.0, 0.0), z=0.0, tilt=0.0, azimuth=0.0)
        t = mesh.module_table([m, m], 1.0, 2.0, selected={1})
        self.assertEqual(tuple(np.round(t[1, 12:15], 2)), mesh.MODULE_SELECTED)

    def test_the_table_of_many_modules_is_the_transform_of_each_one(self):
        """The table built for all the modules at once (one multiplication per sub-field, task 18c) equals the
        one-by-one transform, for mixed tilts and azimuths (an east-west pair, a flat roof)."""
        modules = [layout.PlacedModule(row=r, slot=s, group=0, corners=[], centre=(1.7 * s, 2.9 * r), z=5.0 + 0.1 * s,
                                       tilt=tilt, azimuth=az)
                   for r, (tilt, az) in enumerate(((10.0, -90.0), (10.0, 90.0), (0.0, 0.0), (25.0, 17.5)))
                   for s in range(3)]
        t = mesh.module_table(modules, 1.134, 2.278, selected={4}, colour=(0.2, 0.3, 0.4))
        self.assertEqual(t.shape, (12, 20))
        for i, m in enumerate(modules):
            mat, (tx, ty, tz) = mesh._module_transform(m, 1.134, 2.278, 0.035)
            np.testing.assert_allclose(t[i, [0, 1, 2, 4, 5, 6, 8, 9, 10]].reshape(3, 3), mat, rtol=0, atol=1e-9)
            np.testing.assert_allclose(t[i, [3, 7, 11]], (tx, ty, tz), rtol=0, atol=1e-6)
            self.assertEqual(tuple(np.round(t[i, 12:15], 2)), mesh.MODULE_SELECTED if i == 4 else (0.2, 0.3, 0.4))
            self.assertEqual(float(t[i, 15]), 1.0)
        # a selection changes the colours only, on a copy: the table of the sub-field stays
        again = mesh.recoloured(t, selected={0, 99}, selected_colour=(1.0, 0.0, 0.0))
        self.assertIsNot(again, t)
        self.assertTrue(np.array_equal(again[:, :12], t[:, :12]) and np.array_equal(again[:, 15:], t[:, 15:]))
        self.assertEqual(tuple(again[0, 12:15]), (1.0, 0.0, 0.0))
        self.assertEqual(tuple(np.round(again[1, 12:15], 2)), (0.1, 0.16, 0.3))
        self.assertEqual(tuple(np.round(t[4, 12:15], 2)), mesh.MODULE_SELECTED)


class Outline(unittest.TestCase):
    """The edges of what is selected or under the pointer in 3D, drawn as ribbons a few pixels wide."""

    def test_a_gable_building_has_its_foot_its_corners_and_its_pitches(self):
        pitches = roofs.gable(HOUSE, eave=6.0, tilt=30.0)
        edges = mesh.building_edges(HOUSE, pitches)
        self.assertEqual(edges.shape[1:], (2, 3))
        self.assertEqual(len(edges), 4 + 4 + sum(len(p.ring) for p in pitches))
        ridge = 6.0 + 4.0 * math.tan(math.radians(30))
        self.assertAlmostEqual(float(edges[:, :, 1].max()), ridge, places=6)          # the ridge outlined
        self.assertAlmostEqual(float(edges[:, :, 1].min()), 0.0, places=6)            # and the foot
        corners = [e for e in edges if np.allclose(e[0][[0, 2]], e[1][[0, 2]])]       # the vertical edges
        self.assertEqual(sorted(round(float(c[1][1]), 6) for c in corners), [6.0] * 4)

    def test_a_prism_and_a_ring(self):
        edges = mesh.prism_edges(L_SHAPE, 6.0, 7.5)
        self.assertEqual(len(edges), 3 * len(L_SHAPE))
        ring = mesh.ring_edges([(0, 0, 1), (4, 0, 1), (4, 3, 2)])
        self.assertEqual(len(ring), 3)
        self.assertTrue(np.allclose(ring[2][1], mesh.to_qt(0, 0, 1)))                # closed

    def test_a_module_is_outlined_on_its_face(self):
        m = layout.PlacedModule(row=0, slot=0, group=0, corners=[], centre=(5.0, 3.0), z=7.0, tilt=0.0, azimuth=0.0)
        edges = mesh.module_edges(m, along=1.0, across=2.0)
        self.assertEqual(len(edges), 4)
        xs, zs = edges[:, :, 0], edges[:, :, 2]
        self.assertAlmostEqual(float(xs.max() - xs.min()), 1.0, places=6)
        self.assertAlmostEqual(float(zs.max() - zs.min()), 2.0, places=6)
        self.assertTrue(np.allclose(edges[:, :, 1], 7.0 + 0.035 / 2))               # on its upper face

    def test_ribbons_are_tubes_as_wide_as_asked_around_their_segments(self):
        seg = np.array([[[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], [[0.0, 0.0, 0.0], [0.0, 5.0, 0.0]]])
        pos, nor, col = mesh.ribbons(seg, 0.2, (1.0, 0.0, 1.0))
        self.assertEqual(pos.shape, (2 * 8 * 3, 3))                                  # 4 sides, 2 triangles each
        across, _n, _c = mesh.ribbons(seg[:1], 0.2, (1.0, 0.0, 1.0))
        self.assertAlmostEqual(float(across[:, 0].min()), -0.1, places=5)           # a little longer: corners close
        self.assertAlmostEqual(float(across[:, 0].max()), 10.1, places=5)
        self.assertAlmostEqual(float(np.hypot(across[:, 1], across[:, 2]).max()), 0.1 * math.sqrt(2), places=5)
        upright, _n, _c = mesh.ribbons(seg[1:], 0.2, (1.0, 0.0, 1.0))              # a vertical edge too
        self.assertAlmostEqual(float(upright[:, 1].max()), 5.1, places=5)
        self.assertTrue(np.allclose(np.linalg.norm(nor, axis=1), 1.0, atol=1e-5))
        self.assertTrue(np.allclose(col, (1.0, 0.0, 1.0)))
        self.assertEqual(len(mesh.ribbons(np.zeros((0, 2, 3)), 0.2, (1, 1, 1))[0]), 0)


class Rings(unittest.TestCase):
    """The pivot's cross-hair (task 16g): three orthogonal rings of 48 segments, a halo of flat bands under them."""

    def test_a_ring_is_a_closed_circle_in_the_plane_across_its_axis(self):
        for axis in range(3):
            segs = mesh.ring(2.5, axis)
            with self.subTest(axis=axis):
                self.assertEqual(segs.shape, (mesh.RING_SEGMENTS, 2, 3))
                self.assertEqual(mesh.RING_SEGMENTS, 48)
                self.assertTrue(np.allclose(segs[:, :, axis], 0.0))                         # flat across its axis
                self.assertTrue(np.allclose(np.linalg.norm(segs.reshape(-1, 3), axis=1), 2.5))   # a circle
                self.assertTrue(np.array_equal(segs[:-1, 1], segs[1:, 0]))                  # each starts where one ended
                self.assertTrue(np.array_equal(segs[-1, 1], segs[0, 0]))                    # and the last closes it
                around = segs[:, 1] - segs[:, 0]
                self.assertTrue(np.allclose(np.linalg.norm(around, axis=1), 2 * 2.5 * math.sin(math.pi / 48)))

    def test_a_ring_runs_counter_clockwise_seen_from_the_end_of_its_axis(self):
        for axis in range(3):
            segs = mesh.ring(1.0, axis)
            turn = np.cross(segs[:, 0], segs[:, 1])[:, axis]
            self.assertTrue(np.all(turn > 0), axis)

    def test_three_rings_are_three_tubes_of_forty_eight_sides_each(self):
        pos, nor, col = mesh.rings(0.2, (0.5, 1.0, 0.4))
        self.assertEqual(pos.shape, (3 * 48 * 8 * 3, 3))                                    # 4 faces, 2 triangles each
        self.assertTrue(np.allclose(np.linalg.norm(nor, axis=1), 1.0, atol=1e-5))
        self.assertTrue(np.allclose(col, (0.5, 1.0, 0.4)))
        distance = np.linalg.norm(pos, axis=1)
        self.assertGreater(float(distance.min()), 1.0 - 0.1 * math.sqrt(2) - 0.01)         # a tube 0.2 across the circle
        self.assertLess(float(distance.max()), 1.0 + 0.1 * math.sqrt(2) + 0.02)
        by_side = pos.reshape(8, 3 * 48, 3, 3)                                              # (triangle of a side, segment)
        for axis in range(3):                                                               # one ring across each axis
            ring_k = by_side[:, axis * 48:(axis + 1) * 48]
            self.assertLess(float(np.abs(ring_k[..., axis]).max()), 0.1 * math.sqrt(2) + 1e-5)

    def test_the_bands_under_the_rings_are_flat_and_wider_than_the_tubes(self):
        pos, nor, _col = mesh.ring_bands(0.6, (0.0, 0.0, 0.0))
        self.assertEqual(pos.shape, (3 * 48 * 6, 3))                                        # two triangles per segment
        distance = np.linalg.norm(pos, axis=1)
        self.assertAlmostEqual(float(distance.min()), 0.7, delta=0.002)                     # radius 1 less half the width
        self.assertAlmostEqual(float(distance.max()), 1.3, delta=0.002)
        for k in range(3):
            part = slice(k * 48 * 6, (k + 1) * 48 * 6)
            self.assertTrue(np.allclose(pos[part][:, k], 0.0))                              # in the plane across axis k
            self.assertTrue(np.allclose(nor[part], np.eye(3)[k]))
        tri = pos.reshape(-1, 3, 3)
        geometric = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        self.assertTrue(np.all(np.einsum("ij,ij->i", geometric, nor.reshape(-1, 3, 3)[:, 0]) > 0))   # the winding agrees


class Gizmo(unittest.TestCase):
    """The shapes of the gizmo of Move and Rotate (task 16b): solids turned about an axis, closed, facing out."""

    @staticmethod
    def volume(pos):
        tri = np.asarray(pos, dtype=np.float64).reshape(-1, 3, 3)
        return float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0)

    @staticmethod
    def disc(r, n):
        return 0.5 * n * r * r * math.sin(2 * math.pi / n)        # a regular polygon of n sides

    def test_an_arrow_is_a_closed_shaft_and_cone_facing_out_along_its_axis(self):
        pos, nor, col = mesh.arrow((1.0, 0.0, 0.0))
        t0, t1, rs = mesh.GIZMO_SHAFT
        _h, t2, rh = mesh.GIZMO_HEAD
        want = self.disc(rs, 16) * (t1 - t0) + self.disc(rh, 16) * (t2 - t1) / 3
        self.assertAlmostEqual(self.volume(pos), want, delta=want * 1e-4)     # closed, and positive: facing out
        self.assertAlmostEqual(float(pos[:, 0].max()), 1.0, places=6)          # the tip at one unit
        self.assertAlmostEqual(float(pos[:, 0].min()), t0, places=6)           # the middle left free
        self.assertTrue(np.allclose(np.linalg.norm(nor, axis=1), 1.0, atol=1e-5))
        self.assertTrue(np.allclose(col, 1.0))
        up = mesh.arrow((0.0, 1.0, 0.0))[0]
        self.assertAlmostEqual(float(up[:, 1].max()), 1.0, places=6)
        halo = mesh.arrow((1.0, 0.0, 0.0), halo=mesh.GIZMO_HALO)[0]
        self.assertGreater(self.volume(halo), self.volume(pos))                # the halo wraps it

    def test_the_ring_is_a_flat_cylinder_with_a_hole_of_48_sides(self):
        radius, w, h = mesh.GIZMO_RING
        pos, _nor, _col = mesh.annulus(radius, w, h)
        self.assertEqual(len(pos), 4 * 48 * 6)                                  # four faces, two triangles a side
        self.assertTrue(np.allclose(np.abs(pos[:, 1]), h))                      # flat: across the vertical
        distance = np.hypot(pos[:, 0], pos[:, 2])
        self.assertAlmostEqual(float(distance.min()), radius - w, places=5)
        self.assertAlmostEqual(float(distance.max()), radius + w, places=5)
        want = (self.disc(radius + w, 48) - self.disc(radius - w, 48)) * 2 * h
        self.assertAlmostEqual(self.volume(pos), want, delta=want * 1e-4)

    def test_the_square_of_the_plane_lies_between_east_and_north_both_faces(self):
        a, b = mesh.GIZMO_PLANE
        pos, nor, _col = mesh.square(a, b)
        self.assertEqual(len(pos), 12)
        self.assertTrue(np.allclose(pos[:, 1], 0.0))
        self.assertAlmostEqual(float(pos[:, 0].min()), a)
        self.assertAlmostEqual(float(-pos[:, 2].max()), a)                       # North is -z
        self.assertAlmostEqual(float(-pos[:, 2].min()), b)
        self.assertTrue(np.allclose(np.abs(nor[:, 1]), 1.0))


class ProjectScene(unittest.TestCase):
    """The project's scene as the report draws it (mesh.project_scene): the buildings, the obstacles, the modules
    laid in their colour, the buildings' edges."""

    def test_the_scene_has_the_buildings_the_obstacles_the_modules_in_their_colour_and_the_edges(self):
        from _fixtures import capannone_rho

        from meridiana import jobs
        p = capannone_rho()
        p.subfields[0].filled = True
        results, _keys, _laid = jobs.layout_of(p)
        n = len(results[p.subfields[0].id].modules)
        (pos, nor, col), table, edges = mesh.project_scene(p, results, {"module": (0.1, 0.2, 0.3), "wall": (1, 1, 1)})
        self.assertEqual(len(table), n)
        self.assertTrue(np.allclose(table[:, 12:15], (0.1, 0.2, 0.3)))
        self.assertEqual(len(pos), len(nor))
        self.assertEqual(len(pos), len(col))
        self.assertTrue(np.any(np.all(np.isclose(col, 1.0), axis=1)))     # the walls in the colour given
        self.assertTrue(np.any(np.all(np.isclose(col, mesh.OBSTACLE), axis=1)))     # the vent and the plant
        self.assertGreater(float(pos[:, 1].max()), 9.5 + 0.8 - 1e-6)                # the parapet on top
        self.assertEqual(edges.shape[1:], (2, 3))
        self.assertGreaterEqual(len(edges), 12)                                    # a box has twelve edges
        p.subfields[0].filled = False                                               # nothing laid: no modules
        self.assertEqual(len(mesh.project_scene(p, results)[1]), 0)


if __name__ == "__main__":
    unittest.main()
