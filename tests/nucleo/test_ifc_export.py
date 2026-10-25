"""IFC4 out (study 15, 5.2; R91): the project written as a valid georeferenced model, the site to the millionth of a
second and on UTM, every module laid where the layout put it with its sub-field, tilt, azimuth, power and string, the
strings as groups; a stop half way writes nothing. And what it stands on: the UTM projection of geo.py. They need
ifcopenshell (an optional dependency) and say so when it is not there."""

import math
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import RHO, exported, mixed

from meridiana import geo


def need_ifcopenshell():
    import importlib.util
    if importlib.util.find_spec("ifcopenshell") is None:
        raise unittest.SkipTest("ifcopenshell is not installed")


class Utm(unittest.TestCase):
    def test_the_central_meridian_at_45_degrees_is_500_km_east_and_the_meridian_arc_north(self):
        zone, east, north, gamma, k = geo.to_utm(45.0, 9.0)
        self.assertEqual(zone, 32)
        self.assertAlmostEqual(east, 500000.0, places=3)
        self.assertAlmostEqual(north, 4982950.400, places=2)      # 0,9996 x the meridian arc to 45 degrees
        self.assertAlmostEqual(gamma, 0.0, places=9)
        self.assertAlmostEqual(k, 0.9996, places=9)

    def test_there_and_back_within_a_micrometre_and_the_convergence_of_rho(self):
        for lat, lon in ((45.5226, 9.03), (37.5, 15.08), (-33.9, 151.2), (46.5, 13.4)):
            zone, east, north, gamma, _k = geo.to_utm(lat, lon)
            back = geo.from_utm(zone, east, north, lat < 0)
            self.assertAlmostEqual(back[0], lat, places=10)
            self.assertAlmostEqual(back[1], lon, places=10)
        self.assertAlmostEqual(geo.to_utm(45.5226, 9.03)[3], 0.0214, places=4)    # study 15, 5.2

    def test_the_true_north_is_turned_by_the_convergence_counter_clockwise_from_the_grid(self):
        zone, e1, n1, gamma, _k = geo.to_utm(45.5226, 10.5)
        _z, e2, n2, _g, _k = geo.to_utm(45.5236, 10.5, zone)
        self.assertAlmostEqual(math.degrees(math.atan2(-(e2 - e1), n2 - n1)), gamma, places=3)

    def test_the_utm_systems_that_are_wgs84_within_a_metre_and_the_others(self):
        self.assertEqual(geo.utm_of_crs("EPSG:32632"), (32, False))
        self.assertEqual(geo.utm_of_crs("EPSG:32760"), (60, True))
        self.assertEqual(geo.utm_of_crs("EPSG:6707"), (32, False))      # RDN2008 / UTM 32N (N-E)
        self.assertEqual(geo.utm_of_crs("EPSG:7792"), (33, False))
        self.assertEqual(geo.utm_of_crs("EPSG:25833"), (33, False))
        self.assertIsNone(geo.utm_of_crs("EPSG:3003"))                   # Monte Mario / Gauss-Boaga: another datum
        self.assertIsNone(geo.utm_of_crs("EPSG:28992"))
        self.assertIsNone(geo.utm_of_crs(""))


class Export(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()
        cls.folder = Path(tempfile.mkdtemp())
        cls.project = mixed()
        cls.path, cls.summary, cls.results = exported(cls.project, cls.folder)

    def test_the_file_is_valid_ifc4_with_every_module_laid(self):
        from meridiana import ifc_export
        self.assertEqual(ifc_export.validate(self.path), [])
        laid = sum(r.count for r in self.results.values())
        self.assertEqual(self.summary["modules"], laid)
        import ifcopenshell
        f = ifcopenshell.open(str(self.path))
        self.assertEqual(f.schema, "IFC4")
        self.assertEqual(len(f.by_type("IfcSolarDevice")), laid)
        self.assertEqual(len(f.by_type("IfcSolarDeviceType")), 1)              # one module, one orientation
        self.assertEqual(len(f.by_type("IfcBuildingStorey")), 5)              # one for each building, one for the ground
        self.assertEqual(len(f.by_type("IfcSlab")), 8)                        # one for each pitch

    def test_the_site_has_its_place_to_the_millionth_of_a_second_and_a_map_conversion_on_utm(self):
        import ifcopenshell
        f = ifcopenshell.open(str(self.path))
        site = f.by_type("IfcSite")[0]
        for value, expected in ((site.RefLatitude, RHO["lat"]), (site.RefLongitude, RHO["lon"])):
            d, m, sec, us = value
            self.assertAlmostEqual(d + m / 60 + sec / 3600 + us / 3.6e9, expected, places=9)
        m = f.by_type("IfcMapConversion")[0]
        zone, east, north, gamma, _k = geo.to_utm(RHO["lat"], RHO["lon"])
        self.assertEqual(m.TargetCRS.Name, "EPSG:32632")
        self.assertAlmostEqual(m.Eastings, east, places=3)
        self.assertAlmostEqual(m.Northings, north, places=3)
        self.assertAlmostEqual(math.degrees(math.atan2(m.XAxisOrdinate, m.XAxisAbscissa)), gamma, places=9)

    def test_each_module_says_its_sub_field_tilt_azimuth_power_and_string_and_the_strings_are_groups(self):
        import ifcopenshell
        import ifcopenshell.util.element
        f = ifcopenshell.open(str(self.path))
        module = f.by_type("IfcSolarDevice")[0]
        pset = ifcopenshell.util.element.get_pset(module, "Meridiana_Modulo")
        self.assertEqual(pset["IdSottocampo"], "s1")
        self.assertAlmostEqual(pset["Inclinazione"], 15.0)
        self.assertAlmostEqual(pset["AzimutCEI"], 0.0)
        self.assertAlmostEqual(pset["AzimutDaNord"], 180.0)
        self.assertAlmostEqual(pset["PotenzaNominale"], 450.0)
        self.assertRegex(pset["Stringa"], r"^\d+\.\d+\.\d+$")
        groups = [g.Name for g in f.by_type("IfcGroup")]
        self.assertIn("Sottocampo Sud", groups)
        self.assertTrue(any(name.startswith("Stringa ") for name in groups))

    def test_a_module_lies_where_the_layout_put_it_facing_its_azimuth(self):
        import ifcopenshell
        import ifcopenshell.geom
        f = ifcopenshell.open(str(self.path))
        pm = self.results["s1"].modules[0]
        module = next(m for m in f.by_type("IfcSolarDevice") if m.Name.endswith(" " + pm.key) and "Sud" in m.Name)
        s = ifcopenshell.geom.settings()
        s.set("use-world-coords", True)
        verts = ifcopenshell.geom.create_shape(s, module).geometry.verts
        centre = [sum(verts[i::3]) / (len(verts) // 3) for i in range(3)]
        self.assertAlmostEqual(centre[0], pm.centre[0], places=3)
        self.assertAlmostEqual(centre[1], pm.centre[1], places=3)
        self.assertAlmostEqual(centre[2], pm.z, places=3)

    def test_a_stop_half_way_writes_nothing_and_keeps_the_old_file(self):
        from meridiana import ifc_export
        target = self.folder / "fermato.ifc"
        target.write_text("old", encoding="utf-8")

        def stop(fraction, _what):
            if fraction > 0.3:
                raise ifc_export.Interrupted()
        with self.assertRaises(ifc_export.Interrupted):
            ifc_export.export(self.project, self.results, target, progress=stop)
        self.assertEqual(target.read_text(encoding="utf-8"), "old")
        self.assertFalse((self.folder / "fermato.ifc.part").exists())

    def test_without_a_map_conversion_on_request(self):
        path, summary, _r = exported(self.project, self.folder, "senza_mappa.ifc", map_conversion=False)
        self.assertIsNone(summary["map"])
        import ifcopenshell
        f = ifcopenshell.open(str(path))
        self.assertEqual(f.by_type("IfcMapConversion"), ())
        self.assertEqual(f.by_type("IfcSite")[0].RefLatitude[:2], (45, 31))


if __name__ == "__main__":
    unittest.main()
