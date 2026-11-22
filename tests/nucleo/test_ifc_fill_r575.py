"""R575 D5: the fast reading (ifc_scan) closes the faces as they are. A fan from the first vertex drew triangles outside
an L, filled the holes of faces and profiles, and read an arc of a trimmed circle as the whole circle (the «circle of
ground» kilometres wide of a real model). The areas here are exact values of samples written by hand."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_scan
from meridiana.core.geometry import polyfill

DATA = Path(__file__).resolve().parents[1] / "data" / "ifc"

# IFC2X3 in metres: an L prism as a faceted Brep (concave caps), a 4 x 4 face with a 2 x 2 hole (a surface model) and
# a half disc of radius 1 (a circle trimmed from 0 to 180 degrees, the file's angles in degrees) extruded 1 m
BREP = r"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('t','2026-11-11T00:00:00',(''),(''),'','','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#2=IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);
#3=IFCMEASUREWITHUNIT(IFCPLANEANGLEMEASURE(0.0174532925199433),#2);
#4=IFCDIMENSIONALEXPONENTS(0,0,0,0,0,0,0);
#5=IFCCONVERSIONBASEDUNIT(#4,.PLANEANGLEUNIT.,'DEGREE',#3);
#6=IFCUNITASSIGNMENT((#1,#5));
#7=IFCPROJECT('0000000000000000000001',$,'P',$,$,$,$,$,#6);
#8=IFCCARTESIANPOINT((0.,0.,0.));
#9=IFCAXIS2PLACEMENT3D(#8,$,$);
#10=IFCLOCALPLACEMENT($,#9);
#11=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,$);
#101=IFCCARTESIANPOINT((0.,0.,0.));
#102=IFCCARTESIANPOINT((4.,0.,0.));
#103=IFCCARTESIANPOINT((4.,1.,0.));
#104=IFCCARTESIANPOINT((1.,1.,0.));
#105=IFCCARTESIANPOINT((1.,3.,0.));
#106=IFCCARTESIANPOINT((0.,3.,0.));
#111=IFCCARTESIANPOINT((0.,0.,1.));
#112=IFCCARTESIANPOINT((4.,0.,1.));
#113=IFCCARTESIANPOINT((4.,1.,1.));
#114=IFCCARTESIANPOINT((1.,1.,1.));
#115=IFCCARTESIANPOINT((1.,3.,1.));
#116=IFCCARTESIANPOINT((0.,3.,1.));
#120=IFCPOLYLOOP((#101,#106,#105,#104,#103,#102));
#121=IFCPOLYLOOP((#111,#112,#113,#114,#115,#116));
#122=IFCPOLYLOOP((#101,#102,#112,#111));
#123=IFCPOLYLOOP((#102,#103,#113,#112));
#124=IFCPOLYLOOP((#103,#104,#114,#113));
#125=IFCPOLYLOOP((#104,#105,#115,#114));
#126=IFCPOLYLOOP((#105,#106,#116,#115));
#127=IFCPOLYLOOP((#106,#101,#111,#116));
#130=IFCFACEOUTERBOUND(#120,.T.);
#131=IFCFACEOUTERBOUND(#121,.T.);
#132=IFCFACEOUTERBOUND(#122,.T.);
#133=IFCFACEOUTERBOUND(#123,.T.);
#134=IFCFACEOUTERBOUND(#124,.T.);
#135=IFCFACEOUTERBOUND(#125,.T.);
#136=IFCFACEOUTERBOUND(#126,.T.);
#137=IFCFACEOUTERBOUND(#127,.T.);
#140=IFCFACE((#130));
#141=IFCFACE((#131));
#142=IFCFACE((#132));
#143=IFCFACE((#133));
#144=IFCFACE((#134));
#145=IFCFACE((#135));
#146=IFCFACE((#136));
#147=IFCFACE((#137));
#150=IFCCLOSEDSHELL((#140,#141,#142,#143,#144,#145,#146,#147));
#151=IFCFACETEDBREP(#150);
#152=IFCSHAPEREPRESENTATION(#11,'Body','Brep',(#151));
#153=IFCPRODUCTDEFINITIONSHAPE($,$,(#152));
#154=IFCWALL('0000000000000000000011',$,'L',$,$,#10,#153,$);
#201=IFCCARTESIANPOINT((10.,0.,5.));
#202=IFCCARTESIANPOINT((14.,0.,5.));
#203=IFCCARTESIANPOINT((14.,4.,5.));
#204=IFCCARTESIANPOINT((10.,4.,5.));
#205=IFCCARTESIANPOINT((11.,1.,5.));
#206=IFCCARTESIANPOINT((11.,3.,5.));
#207=IFCCARTESIANPOINT((13.,3.,5.));
#208=IFCCARTESIANPOINT((13.,1.,5.));
#210=IFCPOLYLOOP((#205,#206,#207,#208));
#211=IFCPOLYLOOP((#201,#202,#203,#204));
#212=IFCFACEBOUND(#210,.T.);
#213=IFCFACEOUTERBOUND(#211,.T.);
#214=IFCFACE((#212,#213));
#215=IFCCONNECTEDFACESET((#214));
#216=IFCFACEBASEDSURFACEMODEL((#215));
#217=IFCSHAPEREPRESENTATION(#11,'Body','SurfaceModel',(#216));
#218=IFCPRODUCTDEFINITIONSHAPE($,$,(#217));
#219=IFCSLAB('0000000000000000000012',$,'HOLE',$,$,#10,#218,$,.FLOOR.);
#301=IFCCARTESIANPOINT((0.,0.));
#302=IFCAXIS2PLACEMENT2D(#301,$);
#303=IFCCIRCLE(#302,1.);
#304=IFCTRIMMEDCURVE(#303,(IFCPARAMETERVALUE(0.)),(IFCPARAMETERVALUE(180.)),.T.,.PARAMETER.);
#305=IFCCARTESIANPOINT((-1.,0.));
#306=IFCCARTESIANPOINT((1.,0.));
#307=IFCPOLYLINE((#305,#306));
#308=IFCCOMPOSITECURVESEGMENT(.CONTINUOUS.,.T.,#304);
#309=IFCCOMPOSITECURVESEGMENT(.CONTINUOUS.,.T.,#307);
#310=IFCCOMPOSITECURVE((#308,#309),.F.);
#311=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,#310);
#312=IFCCARTESIANPOINT((20.,0.,0.));
#313=IFCAXIS2PLACEMENT3D(#312,$,$);
#314=IFCDIRECTION((0.,0.,1.));
#315=IFCEXTRUDEDAREASOLID(#311,#313,#314,1.);
#316=IFCSHAPEREPRESENTATION(#11,'Body','SweptSolid',(#315));
#317=IFCPRODUCTDEFINITIONSHAPE($,$,(#316));
#318=IFCSLAB('0000000000000000000013',$,'HALF',$,$,#10,#317,$,.FLOOR.);
ENDSEC;
END-ISO-10303-21;
"""


def areas(path) -> dict:
    s = ifc_scan.scan(path, workers=1)
    out = {}
    for e in s.elements:
        t = s.triangles(e.id) * s.unit_m
        out[e.name] = float(0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum())
    return out, s


class Faces(unittest.TestCase):
    def test_the_samples_of_the_diagnosis_have_their_exact_area(self):
        """Before: 39.0, 36.8, 48.0, 35.2, 11.77 and 214.72 m2."""
        got, _s = areas(DATA / "r575-sintetico.ifc")
        exact = {"RAGGIERA": 30.0, "FORO": 28.8, "ESTRUSA_L": 30.0, "CORNICE": 28.8, "ARCO": 12.97,
                 "PARAPETTO_U": 61.84}
        for name, value in exact.items():
            with self.subTest(name):
                self.assertAlmostEqual(got[name], value, delta=0.01 * value)

    def test_breps_with_concave_faces_holes_and_a_trimmed_arc(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brep.ifc"
            path.write_text(BREP, encoding="ascii", newline="\n")
            got, s = areas(path)
        self.assertAlmostEqual(got["L"], 26.0, places=6)            # caps 2 x 6 m2, walls 14 m2
        self.assertAlmostEqual(got["HOLE"], 12.0, places=6)
        half = 2 * np.pi / 2 + (np.pi + 2.0)
        self.assertAlmostEqual(got["HALF"], half, delta=0.01 * half)
        by_name = {e.name: e for e in s.elements}
        self.assertAlmostEqual(by_name["HALF"].lo[1], 0.0, places=6)    # half a disc, not the whole one
        self.assertAlmostEqual(by_name["HALF"].hi[1], 1.0, delta=0.01)       # the arc in pieces of 10 degrees
        # the triangles stay inside the L: none has its centre in the missing corner
        t = s.triangles(next(e.id for e in s.elements if e.name == "L"))
        c = t.mean(axis=1)
        self.assertFalse(((c[:, 0] > 1.0 + 1e-9) & (c[:, 1] > 1.0 + 1e-9)).any())


class Arcs(unittest.TestCase):
    def test_a_wide_arc_stays_within_a_centimetre(self):
        """A road's curve of 500 m radius: pieces of 10 degrees would leave the arc by 1.9 m."""
        n = ifc_scan._pieces_of_arc(np.radians(30.0), 500.0, 0.01)
        sag = 500.0 * (1 - np.cos(np.radians(30.0) / n / 2))
        self.assertLessEqual(sag, 0.01)
        self.assertEqual(ifc_scan._pieces_of_arc(np.pi, 1.0, 0.01), 18)        # a small one: 10 degrees each


class Fill(unittest.TestCase):
    def test_concave_with_holes_and_upright(self):
        xyz = np.array([(0, 0, 0), (4, 0, 0), (4, 1, 0), (1, 1, 0), (1, 3, 0), (0, 3, 0),
                        (10, 0, 5), (14, 0, 5), (14, 4, 5), (10, 4, 5), (11, 1, 5), (11, 3, 5), (13, 3, 5), (13, 1, 5),
                        (0, 0, 0), (0, 5, 0), (0, 5, 2), (0, 0, 2)], float)
        tris, owner = polyfill.fill(xyz, np.arange(len(xyz)), np.array([0, 6, 10, 14, 18]), np.array([0, 1, 3, 4]))
        p = xyz[tris]
        n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        area = 0.5 * np.linalg.norm(n, axis=1)
        self.assertEqual([round(float(area[owner == k].sum()), 9) for k in range(3)], [6.0, 12.0, 10.0])
        # turned as the outlines: up, up, towards +x
        self.assertTrue((n[owner == 0][:, 2] > 0).all() and (n[owner == 1][:, 2] > 0).all())
        self.assertTrue((n[owner == 2][:, 0] > 0).all())

    def test_a_convex_ring_keeps_its_fan(self):
        xyz = np.array([(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)], float)
        tris, _owner = polyfill.fill(xyz, np.arange(4), np.array([0, 4]), np.array([0, 1]))
        self.assertEqual(tris.tolist(), [[0, 1, 2], [0, 2, 3]])


if __name__ == "__main__":
    unittest.main()
