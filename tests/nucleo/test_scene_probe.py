"""The 3D view's probe of the measuring tool (study 46, state r34-righello section 2.3): from the pointer's ray to the
point, with the corners, the middles and the edges of the project's geometry within the tolerance in pixels, the free
point on a face not exact, the hidden corners left out, the ground where the ray meets no face, nothing where it meets
the sky. The triangles are the ones the 3D view draws (mesh.project_scene, float32, Qt axes)."""

import math
import unittest

import _setup  # noqa: F401
import numpy as np

from meridiana import i18n
from meridiana.app.view.hit3d import Hits
from meridiana.app.view.measure_tool import SNAPS, MeasureTool, Wanted
from meridiana.app.view.scene_probe import SceneProbe, feature_edges, enu_triangles
from meridiana.core.geometry import mesh
from meridiana.core.model import model

T20 = math.tan(math.radians(20))
RIDGE = 6 + 6 * T20
EYE = (60.0, -45.0, 40.0)        # (East, North, height): the camera, south-east of the shed and above it
SPREAD = 0.001                  # a pixel is 1 mm a metre away: 10 px reach 0.7 m at the shed, 70 m away
ALL = Wanted(SNAPS, False, ())
NONE = Wanted(frozenset(), False, ())
_before = None


def setUpModule():
    global _before
    _before = i18n._translation
    i18n.setup("en")


def tearDownModule():
    i18n._translation = _before


def shed():
    """A shed 24 x 12 m, eaves at 6 m, a gable roof at 20° with its ridge along East at N 6."""
    p = model.Project(name="Probe")
    p.buildings.append(model.Building(id="b1", name="Shed", height=6, footprint=[[0, 0], [24, 0], [24, 12], [0, 12]],
                                      roof=model.Roof(type="gable", tilt=20)))
    return p


def qt(p):
    return (p[0], p[2], -p[1])


def ray_to(target, eye=EYE):
    """The ray from the camera through `target` (East, North, height), in the view's axes."""
    d = np.subtract(target, eye)
    return qt(eye), qt(d / np.linalg.norm(d))


class SceneProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (positions, _normals, _colours), _table, _segments = mesh.project_scene(shed(), {})
        cls.positions = positions
        cls.probe = SceneProbe(positions)

    def at(self, target, wanted=ALL, ground=True, eye=EYE):
        return self.probe.probe(*ray_to(target, eye), (0.0, SPREAD), wanted, ground=ground)

    def test_the_edges_are_the_faces_sides_without_the_diagonals(self):
        edges = feature_edges(enu_triangles(self.positions))
        # two eaves, four at the ground, four wall corners, the ridge, two rakes on each gable: no diagonal of a wall
        # or a pitch, and the gable's foot one side though its wall is triangulated from its middle
        lengths = sorted(round(float(np.linalg.norm(b - a)), 3) for a, b in edges)
        self.assertEqual(len(edges), 15, lengths)
        self.assertEqual(lengths.count(24.0), 5)
        self.assertEqual(lengths.count(12.0), 2)
        self.assertEqual(lengths.count(6.0), 4)
        self.assertEqual(lengths.count(round(6 / math.cos(math.radians(20)), 3)), 4)

    def test_a_corner_near_the_ray_is_the_corner_exact(self):
        p = self.at((24.2, 0.1, 6.15))
        self.assertEqual(p.kind, "vertex")
        self.assertTrue(p.exact)
        np.testing.assert_allclose(p.point, (24, 0, 6), atol=1e-5)
        self.assertIsNotNone(p.ray)
        self.assertIsNotNone(p.edge)                        # one of the corner's edges: the arrows' reference

    def test_the_middle_of_an_edge(self):
        p = self.at((12.2, 0.0, 5.9))
        self.assertEqual(p.kind, "midpoint")
        self.assertTrue(p.exact)
        np.testing.assert_allclose(p.point, (12, 0, 6), atol=1e-5)
        np.testing.assert_allclose(sorted(p.edge), sorted(((0, 0, 6), (24, 0, 6))), atol=1e-5)

    def test_a_point_on_an_edge(self):
        p = self.at((6.0, 0.05, 6.2))
        self.assertEqual(p.kind, "edge")
        self.assertTrue(p.exact)
        self.assertAlmostEqual(p.point[1], 0, places=5)
        self.assertAlmostEqual(p.point[2], 6, places=5)
        self.assertLess(abs(p.point[0] - 6), 0.5)

    def test_a_free_point_on_a_pitch_is_on_its_plane_and_not_exact(self):
        target = (12.0, 3.0, 6 + 3 * T20)
        p = self.at(target)
        self.assertEqual(p.kind, "face")
        self.assertFalse(p.exact)
        np.testing.assert_allclose(p.point, target, atol=1e-6)        # the face's own point, float64
        self.assertAlmostEqual(abs(p.normal[2]), math.cos(math.radians(20)), places=4)
        self.assertIsNone(p.edge)                                     # no edge within 10 px

    def test_the_tolerance_is_in_pixels_at_the_distance(self):
        corner = np.array((24.0, 0.0, 6.0))
        distance = np.linalg.norm(corner - EYE)
        reach = 10 * SPREAD * distance
        near = self.at(tuple(corner + (0, 0, -0.6 * reach)))
        far = self.at(tuple(corner + (0, 0, -2.0 * reach)))
        self.assertEqual(near.kind, "vertex")
        self.assertNotEqual(far.kind, "vertex")
        # an orthographic camera: a pixel is the same everywhere
        o, d = ray_to(tuple(corner + (0, 0, -0.6 * reach)))
        self.assertEqual(self.probe.probe(o, d, (SPREAD * distance, 0.0), ALL).kind, "vertex")
        self.assertNotEqual(self.probe.probe(o, d, (SPREAD * distance / 4, 0.0), ALL).kind, "vertex")

    def test_no_snaps_wanted_gives_the_face(self):
        p = self.at((24.2, 0.1, 5.8), NONE)
        self.assertEqual(p.kind, "face")
        self.assertFalse(p.exact)
        self.assertIsNone(p.edge)

    def test_a_hidden_corner_is_not_taken(self):
        # the north-west corner at the ground is behind the shed seen from the south-east: the ray meets the shed
        # first, the corner is far behind it
        p = self.at((0.0, 12.0, 0.0))
        self.assertNotEqual(p.kind, "vertex")
        self.assertGreater(math.dist(p.point, (0, 12, 0)), 3)

    def test_the_ground_where_the_ray_meets_no_face_and_nothing_in_the_sky(self):
        p = self.at((40.0, -20.0, 0.0))
        self.assertEqual(p.kind, "free")
        self.assertFalse(p.exact)
        np.testing.assert_allclose(p.point, (40, -20, 0), atol=1e-6)
        self.assertIsNone(self.at((40.0, -20.0, 0.0), ground=False))        # an IFC context shown: no probe
        self.assertIsNone(self.at((40.0, -20.0, 80.0)))                     # the sky
        self.assertIsNone(SceneProbe(()).probe(*ray_to((0, 0, 90)), (0.0, SPREAD), ALL))
        self.assertEqual(SceneProbe(()).probe(*ray_to((3, 3, 0)), (0.0, SPREAD), ALL).kind, "free")

    def test_hits_cast_finds_the_first_face(self):
        tri = enu_triangles(self.positions)
        hits = Hits(tri.reshape(-1, 3), [("scene", "", len(tri))])
        o, d = np.array((12.0, -10.0, 3.0)), np.array((0.0, 1.0, 0.0))
        distance, index = hits.cast(o, d)
        self.assertAlmostEqual(distance, 10.0, places=5)                     # the south wall, not the north one
        np.testing.assert_allclose(np.abs(hits.normal[index]), (0, 1, 0), atol=1e-6)
        self.assertIsNone(hits.cast(o, -d))

    def test_two_corners_measure_the_true_length_without_approx(self):
        tool = MeasureTool()
        tool.click(self.at((0.15, 0.1, 6.1)))
        tool.click(self.at((24.0, 6.1, RIDGE + 0.1)))
        tool.finish()
        made = tool.measures[-1]
        self.assertTrue(all(p.exact for p in made.points))
        expected = math.dist((0, 0, 6), (24, 6, RIDGE))
        self.assertAlmostEqual(made.spans()[0].length, expected, places=4)
        pill = tool.done("3d")[0]["segments"][0]["pill"]
        self.assertFalse(pill.get("approx"))


if __name__ == "__main__":
    unittest.main()
