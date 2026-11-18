"""Revit-like IFC geometry: metric/imperial units, nested placement, mapped/tessellated/BRep roofs."""
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import _setup  # noqa: F401
from _fixtures import RHO
from meridiana import ifc_export, ifc_import, ifc_read, model


def fixture(path, kind='tessellation', unit='m', mapped=False):
    import ifcopenshell.api
    p=model.Project(site=model.Site(**RHO))
    w=ifc_export.Writer(p,{})
    w.setup()
    scale={'m':1.0,'mm':0.001,'foot':0.3048}[unit]
    length=next(u for u in w.project.UnitsInContext.Units if u.UnitType=='LENGTHUNIT')
    if unit=='mm':
        length.Prefix='MILLI'
    elif unit=='foot':
        foot=ifcopenshell.api.run('unit.add_conversion_based_unit',w.f,name='foot')
        w.project.UnitsInContext.Units=[foot if u==length else u for u in w.project.UnitsInContext.Units]
    # Georeferencing eastings/northings remain metres even when geometry uses another project unit.
    for crs in w.f.by_type('IfcProjectedCRS'):
        crs.MapUnit=w.f.createIfcSIUnit(None,'LENGTHUNIT',None,'METRE')
    level=w.element('IfcBuildingStorey','Level')
    w.api.run('aggregate.assign_object',w.f,products=[level],relating_object=w.building)
    w.place(level,(0,0,1/scale),relative=w.building.ObjectPlacement)
    roof=w.element('IfcRoof','Revit-like arbitrary roof',predefined='FREEFORM')
    w.place(roof,(10/scale,20/scale,4/scale),xdir=(math.cos(math.pi/6),math.sin(math.pi/6),0),
            relative=level.ObjectPlacement)
    xy=[(0,0),(20,0),(20,12),(0,12)]
    top=np.array([(x,y,8-0.2*x-0.3*y) for x,y in xy])/scale
    if kind=='tessellation':
        points=w.f.createIfcCartesianPointList3D(top.tolist())
        shape=w.f.createIfcTriangulatedFaceSet(points,None,False,[(1,2,3),(1,3,4)],None)
        repkind='Tessellation'
    else:
        vertices=np.vstack([top,top-np.array([0,0,0.3/scale])])
        faces=[]
        for indices in [(0,1,2,3),(7,6,5,4)]+[(i,i+4,(i+1)%4+4,(i+1)%4) for i in range(4)]:
            loop=w.f.createIfcPolyLoop([w.point3(*vertices[i]) for i in indices])
            faces.append(w.f.createIfcFace([w.f.createIfcFaceOuterBound(loop,True)]))
        shape=w.f.createIfcFacetedBrep(w.f.createIfcClosedShell(faces))
        repkind='Brep'
    rep=w.f.createIfcShapeRepresentation(w.ctx_body,'Body',repkind,[shape])
    if mapped:
        origin=w.axes((2/scale,3/scale,0),(0,0,1),(1,0,0))
        repmap=w.f.createIfcRepresentationMap(origin,rep)
        target=w.f.createIfcCartesianTransformationOperator3D(None,None,w.point3(-1/scale,2/scale,0),1.2,None)
        rep=w.f.createIfcShapeRepresentation(w.ctx_body,'Body','MappedRepresentation',
                                             [w.f.createIfcMappedItem(repmap,target)])
    roof.Representation=w.f.createIfcProductDefinitionShape(None,None,[rep])
    w.contain([roof],level)
    w.relationships()
    w.f.write(str(path))
    return w.f,scale


class ComplexRoofs(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'revit-like.ifc'

    def test_direct_geometry_matches_native_kernel_for_mapped_nested_and_scaled_shapes(self):
        import ifcopenshell.geom
        settings=ifcopenshell.geom.settings()
        settings.set('use-world-coords',True)
        for kind in ('tessellation','brep'):
            for unit in ('m','mm','foot'):
                for mapped in (False,True):
                    with self.subTest(kind=kind,unit=unit,mapped=mapped):
                        ifc,scale=fixture(self.path,kind,unit,mapped)
                        roof=ifc.by_type('IfcRoof')[0]
                        direct=np.vstack(ifc_read.direct_faces(roof,{},scale))
                        native_shape=ifcopenshell.geom.create_shape(settings,roof)
                        native=np.array(native_shape.geometry.verts).reshape(-1,3)
                        np.testing.assert_allclose(direct.min(axis=0),native.min(axis=0),atol=1e-6)
                        np.testing.assert_allclose(direct.max(axis=0),native.max(axis=0),atol=1e-6)

    def test_arbitrary_roof_gets_an_exact_independent_placement_surface(self):
        for kind in ('tessellation','brep'):
            for unit in ('m','mm','foot'):
                for mapped in (False,True):
                    self.check_surface(kind,unit,mapped)

    def check_surface(self,kind,unit,mapped):
        with self.subTest(kind=kind,unit=unit,mapped=mapped):
            fixture(self.path,kind,unit,mapped)
            found=ifc_read.read(self.path)
            p=model.Project(site=model.Site(**RHO))
            plan=ifc_import.plan(found,p,'file',name='revit-like.ifc')
            self.assertTrue(plan.supports)
            self.assertEqual(p.subfields,[])  # no mutation before the import is confirmed
            ifc_import.apply(p,plan)
            sf=p.subfields[0]
            self.assertFalse(sf.filled)
            self.assertTrue(sf.support.enabled)
            self.assertEqual(sf.building,p.buildings[0].id)
            # z is local to the received building's ground (the nested storey stands at world z=1).
            for u,v in ((2,3),(12,7),(18,10)):
                a,b=(1.2*u+1.4,1.2*v+5.6) if mapped else (u,v)
                x=10+a*math.cos(math.pi/6)-b*math.sin(math.pi/6)
                y=20+a*math.sin(math.pi/6)+b*math.cos(math.pi/6)
                z=4+(1.2 if mapped else 1)*(8-0.2*u-0.3*v)
                self.assertAlmostEqual(p.surface_of(sf).z(x,y),z,places=3)
            self.assertIn('revit-like.ifc',' '.join(plan.taken))
            again=model.Project.from_json(p.to_json())
            self.assertEqual(again.subfields[0].support,sf.support)


    def test_true_north_rotates_the_normal_and_the_plane_together(self):
        fixture(self.path)
        found=ifc_read.read(self.path)
        found['map']=None
        found['true_north']=37.0
        p=model.Project(site=model.Site(**RHO))
        frame=ifc_import.Frame(found,ifc_import.place_of(found),'file',p.site)
        plan=ifc_import.plan(found,p,'file',name='turned.ifc')
        ifc_import.apply(p,plan)
        surface=p.surface_of(p.subfields[0])
        for raw in found['buildings'][0]['pitches']:
            for x,y in raw['ring']:
                expected=ifc_read.plane_z(raw,x,y)-found['buildings'][0]['ground']
                self.assertAlmostEqual(surface.z(*frame.point(x,y)),expected,places=3)


if __name__=='__main__':
    unittest.main()
