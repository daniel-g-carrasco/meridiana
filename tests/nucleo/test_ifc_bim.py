"""BIM identity is a persisted object identity, not the name or the coordinates of an export."""
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone_rho, exported
from meridiana import model, move


class BIM(unittest.TestCase):
    def setUp(self):
        import ifcopenshell
        self.ios = ifcopenshell
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.p = capannone_rho()
        self.p.subfields[0].filled = True

    def write(self, name):
        path, _summary, _results = exported(self.p, self.folder, name)
        return self.ios.open(str(path))

    def test_all_ifc_root_guids_survive_repeat_export_and_rename(self):
        a = self.write('a.ifc')
        self.p.name = 'Renamed project'
        self.p.buildings[0].name = 'Renamed building'
        self.p.subfields[0].name = 'Renamed array'
        b = self.write('b.ifc')
        self.assertEqual({r.GlobalId for r in a.by_type('IfcRoot')}, {r.GlobalId for r in b.by_type('IfcRoot')})
        ids = [r.GlobalId for r in b.by_type('IfcRoot')]
        self.assertEqual(len(ids), len(set(ids)))

    def test_module_ids_survive_move_and_serialization_and_belong_to_the_plant(self):
        import ifcopenshell.util.element
        a = self.write('a.ifc')
        first = {m.Name.rsplit(' ',1)[-1]: m.GlobalId for m in a.by_type('IfcSolarDevice')}
        move.translate(self.p,'building',self.p.buildings[0].id,3,5)(self.p)
        self.p = model.Project.from_json(self.p.to_json())
        b = self.write('b.ifc')
        second = {m.Name.rsplit(' ',1)[-1]: m.GlobalId for m in b.by_type('IfcSolarDevice')}
        self.assertEqual(first, second)
        system = b.by_type('IfcSystem')[0]
        members = {x.GlobalId for r in b.by_type('IfcRelAssignsToGroup') if r.RelatingGroup == system
                   for x in r.RelatedObjects}
        self.assertEqual(members,set(second.values()))
        pset = ifcopenshell.util.element.get_pset(b.by_type('IfcSolarDevice')[0],'Meridiana_Modulo')
        self.assertEqual(pset['IdProgettoBIM'],self.p.bim_id)
        self.assertEqual(pset['IdVariante'],self.p.variant)
        self.assertEqual(pset['IdModuloCatalogo'],self.p.subfields[0].module)

    def test_unfilled_support_is_a_virtual_surface_with_stable_identity_and_real_geometry(self):
        import numpy as np
        import ifcopenshell.geom
        import ifcopenshell.util.element
        from meridiana import ifc_export, ifc_import, ifc_read
        sf = self.p.subfields[0]
        sf.filled = False
        sf.support = model.SupportPlane(z0=18, x0=20, y0=10, tilt=23, azimuth=37)
        a = self.write('plane.ifc')
        self.assertEqual(len(a.by_type('IfcSolarDevice')), 0)
        annotation = a.by_type('IfcAnnotation')[0]
        self.assertEqual(annotation.ObjectType, 'MERIDIANA_PLACEMENT_SURFACE')
        props = ifcopenshell.util.element.get_pset(annotation, 'Meridiana_Supporto')
        self.assertEqual(props['IdSottocampo'], sf.id)
        self.assertEqual(props['IdProgettoBIM'], self.p.bim_id)
        self.assertTrue(props['Attivo'])
        settings = ifcopenshell.geom.settings()
        settings.set('use-world-coords', True)
        shape = ifcopenshell.geom.create_shape(settings, annotation)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        for x, y, z in verts:
            self.assertAlmostEqual(z, self.p.surface_of(sf).z(x, y), places=6)
        self.assertEqual(ifc_export.validate(self.folder/'plane.ifc'), [])
        found = ifc_read.read(self.folder/'plane.ifc')
        self.assertEqual(len(found['supports']), 1)
        back = model.Project(site=self.p.site)
        plan = ifc_import.plan(found, back, 'file', name='plane.ifc')
        self.assertEqual(len(plan.supports), 1)
        self.assertEqual(back.subfields, [])
        ifc_import.apply(back, plan)
        received = back.subfields[0]
        self.assertFalse(received.filled)
        self.assertEqual(received.building, back.buildings[0].id)
        self.assertIsNotNone(received.pitch)
        for x, y in sf.ring:
            self.assertAlmostEqual(back.surface_of(received).z(x, y), self.p.surface_of(sf).z(x, y), places=3)
        sf.name = 'Renamed support'
        move.translate(self.p, 'subfield', sf.id, 2, 3)(self.p)
        b = self.write('plane-moved.ifc')
        self.assertEqual(annotation.GlobalId, b.by_type('IfcAnnotation')[0].GlobalId)


if __name__ == '__main__':
    unittest.main()
