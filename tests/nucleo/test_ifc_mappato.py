"""A mapped representation is read once for all its instances, and the terrain's layers are looked for only where
they can change the answer (r33). A Revit family placed hundreds of times read the same IfcFacetedBrep again, face by
face, for every instance: 44 % of the reading of a 214 MB model; and `get_layers` traversed the representation of every
proxy, a third of the reading of a 38 MB model. The answers stay the same to the last bit.

The sample `tests/data/ifc/mappato-ripetuto.ifc` (made by hand, no data of any real model): a flat roof of 12 x 8 m at
6 m and three instances (UNITA_A, UNITA_B, UNITA_C) of one IfcRepresentationMap holding an IfcFacetedBrep, a box of
1 x 1 x 1 m standing on the roof, at three placements, the third turned by 30 degrees by its mapping."""

import unittest
from pathlib import Path
from unittest import mock

import ifcopenshell
import ifcopenshell.util.element
import numpy as np

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_read, ifc_terrain

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "mappato-ripetuto.ifc"
TOPO = "C-TOPO-____-OTLN"


def units(f) -> list:
    return sorted(f.by_type("IfcBuildingElementProxy"), key=lambda e: e.Name)


def by_layers(e) -> bool:
    """The rule as it was: every layer of the element, through get_layers."""
    names = [e.Name, e.ObjectType]
    kind = ifcopenshell.util.element.get_type(e)
    if kind is not None:
        names.append(kind.Name)
    layers = [x.Name for x in ifcopenshell.util.element.get_layers(e.file, e)]
    materials = [m.Name for m in ifcopenshell.util.element.get_materials(e)]
    return ifc_terrain.is_terrain(e.is_a(), getattr(e, "PredefinedType", None), names, layers, materials)


class MappedOnce(unittest.TestCase):
    def setUp(self):
        self.f = ifcopenshell.open(str(SAMPLE))

    def test_each_instance_gets_the_same_faces_from_the_shared_source(self):
        shared: dict = {}
        for e in units(self.f):
            got = ifc_read.direct_faces(e, shared, 1.0)
            alone = ifc_read.direct_faces(e, {}, 1.0)
            self.assertEqual(len(got), 6, e.Name)
            for a, b in zip(got, alone, strict=True):
                np.testing.assert_array_equal(a, b)
        boxes = {e.Name: np.concatenate(ifc_read.direct_faces(e, shared, 1.0)) for e in units(self.f)}
        np.testing.assert_array_equal(boxes["UNITA_A"].min(axis=0), [2.0, 2.0, 6.0])
        np.testing.assert_array_equal(boxes["UNITA_B"].max(axis=0), [7.0, 3.0, 7.0])
        c = boxes["UNITA_C"]                                # turned by 30 degrees about its corner at (9, 5)
        np.testing.assert_allclose(c.min(axis=0), [9.0 - 0.5, 5.0, 6.0], atol=1e-12)
        np.testing.assert_allclose(c.max(axis=0), [9.0 + np.cos(np.radians(30)), 5.0 + 0.5 + np.cos(np.radians(30)),
                                                   7.0], atol=1e-12)

    def test_the_brep_of_the_source_is_read_once_for_the_three_instances(self):
        shared: dict = {}
        with mock.patch.object(ifc_read, "_loops", wraps=ifc_read._loops) as loops:
            for e in units(self.f):
                ifc_read.direct_faces(e, shared, 1.0)
                ifc_read.box_points(e, shared, 1.0)
        self.assertEqual(loops.call_count, 1, "the source's Brep is read once for all its instances")

    def test_what_a_caller_does_to_its_faces_leaves_the_next_instance_as_it_was(self):
        shared: dict = {}
        a, b = units(self.f)[:2]
        for face in ifc_read.direct_faces(a, shared, 1.0):
            face[:] = 0.0
        mine, alone = ifc_read.direct_faces(b, shared, 1.0), ifc_read.direct_faces(b, {}, 1.0)
        for got, expected in zip(mine, alone, strict=True):
            np.testing.assert_array_equal(got, expected)

    def test_a_source_not_read_directly_says_so_for_every_instance(self):
        source = self.f.by_type("IfcRepresentationMap")[0].MappedRepresentation
        sphere = self.f.createIfcSphere(self.f.by_type("IfcAxis2Placement3D")[0], 0.5)
        source.Items = list(source.Items) + [sphere]
        shared: dict = {}
        for e in units(self.f):
            with self.subTest(e.Name), self.assertRaises(ifc_read.Unsupported) as said:
                ifc_read.direct_faces(e, shared, 1.0)
            self.assertEqual(str(said.exception), "IfcSphere")


class TerrainLayers(unittest.TestCase):
    def setUp(self):
        self.f = ifcopenshell.open(str(SAMPLE))

    def layer(self, items) -> None:
        self.f.createIfcPresentationLayerAssignment(TOPO, None, items, None)

    def answers(self, shared: bool = True) -> tuple[list, list, int]:
        """of_entity of the three units (with one memo for the file, or none), the rule as it was, the traverses."""
        reference = [by_layers(e) for e in units(self.f)]
        memo: dict = {}
        with mock.patch.object(ifcopenshell.util.element, "get_layers",
                               wraps=ifcopenshell.util.element.get_layers) as spy:
            got = [ifc_terrain.of_entity(e, memo) if shared else ifc_terrain.of_entity(e) for e in units(self.f)]
        return got, reference, spy.call_count

    def test_a_file_without_a_terrain_layer_is_not_traversed(self):
        got, reference, calls = self.answers(shared=False)
        self.assertEqual(got, [False, False, False])
        self.assertEqual(got, reference)
        self.assertEqual(calls, 0)

    def test_the_layer_of_the_shared_source_makes_every_instance_terrain(self):
        self.layer([self.f.by_type("IfcFacetedBrep")[0]])
        got, reference, _calls = self.answers()
        self.assertEqual(got, [True, True, True])
        self.assertEqual(got, reference)

    def test_the_layer_of_one_instance_makes_that_one_terrain(self):
        rep = units(self.f)[1].Representation.Representations[0]
        self.layer([rep])
        got, reference, calls = self.answers()
        self.assertEqual(got, [False, True, False])
        self.assertEqual(got, reference)
        self.assertEqual(calls, 1)                  # only the element that reaches the layer is traversed

    def test_a_layer_on_what_get_layers_does_not_look_at_changes_nothing(self):
        self.layer([self.f.by_type("IfcMappedItem")[0]])        # neither a shape representation nor a geometric item
        got, reference, _calls = self.answers()
        self.assertEqual(got, [False, False, False])
        self.assertEqual(got, reference)

    def test_a_terrain_by_its_name_needs_no_layer(self):
        e = units(self.f)[0]
        e.Name = "Solido topografico"
        with mock.patch.object(ifcopenshell.util.element, "get_layers") as spy:
            self.assertTrue(ifc_terrain.of_entity(e))
        spy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
