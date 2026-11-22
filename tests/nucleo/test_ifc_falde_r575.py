"""R575: the pitches of a roof whose plane comes in many faces, far from the file's origin.

A real model (model A) gave the main roof as a tessellation: a flat roof sloping 1.5 % to its drains, each plane a fan
of long triangles from one corner, the coordinates in a national grid (4.6 million metres east). The faces of one
plane were grouped by their plane's offset at the origin: there a normal off by a ten-thousandth of a radian (the
millimetres of the file) moves the offset by hundreds of metres, so each triangle stood alone. The roof came in as
158 slivers fanning from one corner (the «spokes» seen in plan and in the import's preview), the narrow ones were left
out, and a sub-field on one of them laid no module at all."""

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401
from _fixtures import RHO

from meridiana.app import jobs
from meridiana.app.exchange import ifc_export, ifc_import, ifc_read
from meridiana.core.model import model
from shapely.geometry import Polygon

EAST, NORTH = 4_642_700.0, 791_050.0       # a national grid's eastings and northings, as in the model met
SLOPE = 0.015                              # 1.5 % towards the drains: 0.86 degrees


def fan(width=40.0, depth=20.0, step=4.0, at=(EAST, NORTH), z=100.0):
    """A plane sloping SLOPE down to the north-east corner, as triangles from the south-west corner to the points of
    the far sides, every `step` metres; coordinates rounded to the millimetre, as a file writes them."""
    x0, y0 = at
    far = [(width, y) for y in np.arange(0.0, depth, step)] + [(x, depth) for x in np.arange(width, -1e-9, -step)]

    def point(x, y):
        return np.round((x0 + x, y0 + y, z - SLOPE * (x + y) / math.sqrt(2.0)), 3)
    return [np.array([point(0.0, 0.0), point(*a), point(*b)]) for a, b in zip(far, far[1:], strict=False)]


class PlaneInManyFaces(unittest.TestCase):
    def test_the_triangles_of_one_plane_far_from_the_origin_make_one_pitch(self):
        faces = fan()
        planes, left = ifc_read.roof_planes(faces, [1] * len(faces))
        self.assertEqual(1, len(planes), [round(p["area"], 1) for p in planes])
        self.assertAlmostEqual(800.0, planes[0]["area"], delta=0.5)
        self.assertEqual(0, left["small"])
        self.assertAlmostEqual(math.degrees(math.acos(planes[0]["normal"][2])), math.degrees(math.atan(SLOPE)),
                               delta=0.01)
        # the pitch is where the faces are, not moved by the arithmetic about a nearer origin
        self.assertTrue(Polygon(planes[0]["ring"]).buffer(0.01).contains(Polygon(faces[3][:, :2])))
        x, y = faces[3][:, :2].mean(axis=0)
        self.assertAlmostEqual(ifc_read.plane_z(planes[0], x, y), faces[3][:, 2].mean(), delta=0.005)

    def test_two_planes_that_meet_stay_two(self):
        # the other half of a drain's valley: the same slope the other way, the same height along the line they share
        a = fan(width=20.0, depth=20.0)
        b = [np.column_stack((2 * EAST - f[:, 0], f[:, 1], f[:, 2]))[::-1] for f in a]   # mirrored, still up
        planes, _left = ifc_read.roof_planes(a + b, [1] * (len(a) + len(b)))
        self.assertEqual(2, len(planes))
        self.assertEqual([400.0, 400.0], sorted(round(p["area"], 0) for p in planes))


def roof_file(path):
    """An IFC with one roof: the fan above as a tessellation, placed at the national grid's coordinates."""
    p = model.Project(site=model.Site(**RHO))
    w = ifc_export.Writer(p, {})
    w.setup()
    level = w.element("IfcBuildingStorey", "Level")
    w.api.run("aggregate.assign_object", w.f, products=[level], relating_object=w.building)
    w.place(level, (0, 0, 0), relative=w.building.ObjectPlacement)
    roof = w.element("IfcRoof", "Flat roof to the drains", predefined="FLAT_ROOF")
    w.place(roof, (0, 0, 0), relative=level.ObjectPlacement)
    faces = fan(z=12.0)
    points = np.vstack(faces)
    shape = w.f.createIfcTriangulatedFaceSet(w.f.createIfcCartesianPointList3D(points.tolist()), None, False,
                                             [(3 * k + 1, 3 * k + 2, 3 * k + 3) for k in range(len(faces))], None)
    rep = w.f.createIfcShapeRepresentation(w.ctx_body, "Body", "Tessellation", [shape])
    roof.Representation = w.f.createIfcProductDefinitionShape(None, None, [rep])
    w.contain([roof], level)
    w.relationships()
    w.f.write(str(path))


class SubFieldOnTheImportedRoof(unittest.TestCase):
    def test_a_sub_field_on_the_roof_lays_its_modules(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "drains.ifc"
            roof_file(path)
            found = ifc_read.read(path)
        project = model.Project(site=model.Site(**RHO))
        ifc_import.apply(project, ifc_import.plan(found, project, "origin", None, name="drains.ifc"))
        self.assertEqual(1, len(project.buildings))
        b = project.buildings[0]
        pitches = b.pitches()
        self.assertEqual(1, len(pitches), [round(Polygon(x.ring).area, 1) for x in pitches])
        sf = project.new_subfield("s1", "s1", [list(q) for q in pitches[0].ring], b.id, b.pitch_ref(0))
        sf.filled = True
        project.add_subfield(sf)
        results, _keys, _laid = jobs.layout_of(project)
        self.assertGreater(len(results["s1"].modules), 250)       # 800 m2 of roof; 0 to 3 on the slivers before


if __name__ == "__main__":
    unittest.main()
