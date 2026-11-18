"""The plan as a DXF (R513): written, audited by ezdxf and read back. The modules are where the layout lays them (to the
millimetre), each a block with its data, the strings run through their modules in their order, the buildings' outlines
are the project's; the coordinates local, UTM or of the file the buildings came from, the unit in the header; the parts
asked and nothing else; a stop half way writes nothing."""

import math
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone, mixed

from meridiana import dxf_export, geo, jobs
from meridiana.energy import plant as plants


def need_ezdxf():
    if not dxf_export.available():
        raise unittest.SkipTest("ezdxf is not installed")


def laid(project):
    results, _keys, _laid = jobs.layout_of(project)
    return results, plants.build(project, results, check=False)


def read(path):
    import ezdxf
    return ezdxf.readfile(str(path))


def module_refs(doc) -> list:
    return [e for e in doc.modelspace().query("INSERT") if e.dxf.layer == "FV-MODULI"]


def outline(ref) -> list[tuple[float, float]]:
    """The corners of a module's block reference, in the file's coordinates."""
    poly = next(e for e in ref.virtual_entities() if e.dxftype() == "LWPOLYLINE")
    return [(float(v.x), float(v.y)) for v in poly.vertices_in_wcs()]


class Written(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        need_ezdxf()
        cls.folder = tempfile.TemporaryDirectory()
        cls.project = mixed()
        cls.results, cls.plant = laid(cls.project)
        cls.path = Path(cls.folder.name) / "pianta.dxf"
        cls.summary = dxf_export.export(cls.project, cls.results, cls.path, plant=cls.plant)
        cls.doc = read(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def laid_modules(self):
        return {(sf.name, m.key): m for sf in self.project.subfields
                for m in (self.results.get(sf.id).modules if self.results.get(sf.id) else [])}

    def test_the_file_is_clean_and_says_its_unit(self):
        self.assertEqual(dxf_export.audit(self.path), [])
        self.assertEqual(self.doc.dxfversion, "AC1024")                 # R2010
        self.assertEqual(self.doc.header["$INSUNITS"], 6)              # metres
        self.assertEqual(self.doc.header["$MEASUREMENT"], 1)
        self.assertFalse(self.path.with_name(self.path.name + ".part").exists())

    def test_the_layers_are_named_with_their_colour_line_and_description(self):
        for name, colour, ltype, weight, _what in dxf_export.LAYERS:
            layer = self.doc.layers.get(name)
            self.assertEqual((layer.color, layer.dxf.linetype.upper(), layer.dxf.lineweight),
                             (colour, ltype.upper(), weight), name)
            self.assertTrue(layer.description)
        self.assertEqual(self.doc.styles.get("MERIDIANA").dxf.font, dxf_export.FONT)

    def test_every_module_laid_is_a_block_on_its_place_with_its_data(self):
        expected = self.laid_modules()
        refs = module_refs(self.doc)
        self.assertEqual(len(refs), len(expected))
        self.assertEqual(self.summary["modules"], len(expected))
        labels = {(sf, key): s.label for s in self.plant.strings for sf, key, _c in s.modules}
        names = {sf.name: sf.id for sf in self.project.subfields}
        for ref in refs:
            att = {a.dxf.tag: a.dxf.text for a in ref.attribs}
            m = expected[(att["SOTTOCAMPO"], att["CHIAVE"])]
            for corner in outline(ref):
                self.assertLess(min(math.dist(corner, q) for q in m.corners), 1e-3)
            self.assertEqual(att["STRINGA"], labels.get((names[att["SOTTOCAMPO"]], m.key), ""))
            self.assertTrue(att["MODELLO"] and att["POTENZA_W"])
            self.assertTrue(all(a.is_invisible for a in ref.attribs))

    def test_the_buildings_outlines_are_the_projects(self):
        outlines = [e for e in self.doc.modelspace().query("LWPOLYLINE") if e.dxf.layer == "FV-EDIFICI"]
        self.assertEqual(len(outlines), len(self.project.buildings))
        for b, e in zip(self.project.buildings, outlines, strict=True):
            self.assertTrue(e.closed)
            got = [tuple(v[:2]) for v in e.get_points("xy")]
            self.assertEqual(len(got), len(b.footprint))
            for q, g in zip(b.footprint, got, strict=True):
                self.assertLess(math.dist(q, g), 1e-3)

    def test_each_string_runs_through_its_modules_in_order_and_is_a_group(self):
        strings = [s for s in self.plant.strings if s.modules]
        self.assertTrue(strings)
        groups = dict(self.doc.groups)
        self.assertEqual(self.summary["strings"], len(strings))
        names = [e for e in self.doc.modelspace().query("TEXT") if e.dxf.layer == "FV-STRINGHE-NOMI"]
        self.assertEqual(sorted(e.dxf.text for e in names), sorted(s.label for s in strings))
        for s in strings:
            group = groups["STRINGA_" + s.label.replace(".", "-")]
            points = [tuple(map(float, v[:2])) for e in group if e.dxftype() == "LWPOLYLINE"
                      for v in e.get_points("xy")]
            centres = [c for _sf, _key, c in s.modules]
            at = 0
            for c in centres:                   # the middles of the modules, one after the other along the line
                while at < len(points) and math.dist(points[at], c) > 1e-6:
                    at += 1
                self.assertLess(at, len(points), f"{s.label}: {c} not on its line in order")
            colours = {e.dxf.true_color for e in group if e.dxf.hasattr("true_color")}
            self.assertEqual(len(colours), 1, s.label)

    def test_ridges_pitches_obstacles_and_dimensions(self):
        counts = self.summary["layers"]
        for layer in ("FV-FALDE", "FV-COLMI", "FV-PARAPETTI", "FV-OSTACOLI", "FV-QUOTE", "FV-TESTI",
                      "FV-SOTTOCAMPI", "FV-INVERTER", "FV-CARTIGLIO"):
            self.assertGreater(counts.get(layer, 0), 0, layer)
        texts = [e.dxf.text for e in self.doc.modelspace().query("TEXT")]
        self.assertTrue(any("2,20" in t or "2.20" in t for t in texts))            # the plant on the roof, 2,2 m
        dims = [e for e in self.doc.modelspace().query("DIMENSION") if e.dxf.layer == "FV-QUOTE"]
        self.assertTrue(any(abs(d.get_measurement() - 40.0) < 1e-6 for d in dims))
        self.assertTrue(any(self.project.name in t for t in texts))                 # the title block


class Frames(unittest.TestCase):
    def setUp(self):
        need_ezdxf()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.project = capannone()
        self.results, self.plant = laid(self.project)

    def centres(self, path) -> list[tuple[float, float]]:
        return sorted((float(e.dxf.insert.x), float(e.dxf.insert.y)) for e in module_refs(read(path)))

    def expected(self, frame) -> list[tuple[float, float]]:
        return sorted(frame(*m.centre) for r in self.results.values() for m in r.modules)

    def close(self, got, expected, tolerance):
        self.assertEqual(len(got), len(expected))
        for g, e in zip(got, expected, strict=True):
            self.assertLess(math.dist(g, e), tolerance)

    def test_utm_is_the_sites_zone_turned_by_the_convergence(self):
        path = Path(self.folder.name) / "utm.dxf"
        out = dxf_export.export(self.project, self.results, path, plant=self.plant, frame="utm", parts=("modules",))
        zone, east, north, gamma, _k = geo.to_utm(self.project.site.lat, self.project.site.lon)
        self.assertEqual(zone, 32)
        g = math.radians(gamma)

        def utm(x, y):
            return east + x * math.cos(g) - y * math.sin(g), north + x * math.sin(g) + y * math.cos(g)
        self.close(self.centres(path), self.expected(utm), 1e-3)
        self.assertIn("EPSG:32632", out["label"])
        self.assertEqual(dxf_export.audit(path), [])

    def test_the_frame_of_the_ifc_model_the_buildings_came_from(self):
        b = self.project.buildings[0]
        self.project.resources["ifc_reference"] = {"file": "architetto.ifc", "theta": 30.0, "origin": [1000.0, 2000.0],
                                                   "shift": [0.0, 0.0],
                                                   "anchor": {"building": b.id, "footprint": [list(q) for q in b.footprint]}}
        choices = {c["key"]: c for c in dxf_export.frame_choices(self.project)}
        self.assertTrue(choices["imported"]["enabled"])
        path = Path(self.folder.name) / "ifc.dxf"
        dxf_export.export(self.project, self.results, path, plant=self.plant, frame="imported", parts=("modules",))
        a = math.radians(30.0)
        self.close(self.centres(path), self.expected(
            lambda x, y: (1000.0 + x * math.cos(a) - y * math.sin(a), 2000.0 + x * math.sin(a) + y * math.cos(a))), 1e-3)
        b.footprint = [[0, 0], [41, 0], [41, 20], [0, 20]]       # reshaped since: that frame no longer holds
        choices = {c["key"]: c for c in dxf_export.frame_choices(self.project)}
        self.assertFalse(choices["imported"]["enabled"])
        self.assertTrue(choices["imported"]["why"])
        with self.assertRaises(ValueError):
            dxf_export.export(self.project, self.results, path, frame="imported")

    def test_a_drawing_in_millimetres_follows_its_building_when_moved(self):
        b = self.project.buildings[0]
        self.project.resources["drawing_reference"] = {"file": "pianta.dxf", "unit": "mm", "origin": [58000.0, -36000.0],
                                                       "turn": -68.72,
                                                       "anchor": {"building": b.id,
                                                                  "footprint": [list(q) for q in b.footprint]}}
        before = Path(self.folder.name) / "before.dxf"
        dxf_export.export(self.project, self.results, before, plant=self.plant, frame="imported")
        doc = read(before)
        self.assertEqual(doc.header["$INSUNITS"], 4)
        self.assertEqual(dxf_export.audit(before), [])
        t = math.radians(-68.72)
        self.close(self.centres(before), self.expected(
            lambda x, y: (58000.0 + 1000 * (x * math.cos(t) - y * math.sin(t)),
                          -36000.0 + 1000 * (x * math.sin(t) + y * math.cos(t)))), 1.0)
        self.assertAlmostEqual(doc.dimstyles.get("MERIDIANA").dxf.dimlfac, 0.001)    # the dimensions read metres
        # the building and its modules moved by 5 m East and turned by 10 degrees on the plan: they stay put in the
        # drawing, as the IFC export keeps them in the model's frame
        turn, (dx, dy) = math.radians(10.0), (5.0, 0.0)

        def moved(q):
            return [dx + q[0] * math.cos(turn) - q[1] * math.sin(turn), dy + q[0] * math.sin(turn) + q[1] * math.cos(turn)]
        b.footprint = [moved(q) for q in b.footprint]
        for sf in self.project.subfields:
            sf.ring = [moved(q) for q in sf.ring]
            sf.params["azimuth"] = sf.params.get("azimuth", 0.0) - 10.0
        results, pl = laid(self.project)
        after = Path(self.folder.name) / "after.dxf"
        dxf_export.export(self.project, results, after, plant=pl, frame="imported", parts=("buildings",))
        first = [e for e in read(before).modelspace().query("LWPOLYLINE") if e.dxf.layer == "FV-EDIFICI"][0]
        second = [e for e in read(after).modelspace().query("LWPOLYLINE") if e.dxf.layer == "FV-EDIFICI"][0]
        for p, q in zip(first.get_points("xy"), second.get_points("xy"), strict=True):
            self.assertLess(math.dist(p[:2], q[:2]), 1.0)                    # a millimetre

    def test_the_parts_asked_and_nothing_else(self):
        path = Path(self.folder.name) / "moduli.dxf"
        out = dxf_export.export(self.project, self.results, path, plant=self.plant, parts=("modules",))
        self.assertEqual(set(out["layers"]), {"FV-MODULI", "FV-SOTTOCAMPI", "FV-TESTI"})
        with self.assertRaises(ValueError):
            dxf_export.export(self.project, self.results, path, parts=("modules", "cables"))

    def test_a_stop_half_way_writes_nothing(self):
        path = Path(self.folder.name) / "fermato.dxf"
        path.write_text("old", encoding="utf-8")

        def stop(fraction, _what):
            if fraction > 0.5:
                raise dxf_export.Interrupted()
        with self.assertRaises(dxf_export.Interrupted):
            dxf_export.export(self.project, self.results, path, plant=self.plant, progress=stop)
        self.assertEqual(path.read_text(encoding="utf-8"), "old")
        self.assertEqual([p.name for p in Path(self.folder.name).iterdir()], ["fermato.dxf"])

    def test_the_optimizers_one_block_for_each_group(self):
        from meridiana import catalog
        from meridiana.energy import optimizers
        se = next(r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None) if r["model"] == "SE50K")
        self.project.energy["inverters"] = [{"record": se, "count": 1, "name": ""}]
        self.project.energy["strings"] = {"auto": True}
        results, pl = laid(self.project)
        self.assertTrue(pl.strings)
        path = Path(self.folder.name) / "ottimizzatori.dxf"
        dxf_export.export(self.project, results, path, plant=pl)
        refs = [e for e in read(path).modelspace().query("INSERT") if e.dxf.layer == "FV-OTTIMIZZATORI"]
        per = pl.units[0].choice.per
        expected = sum(len(optimizers.module_groups(s.modules, per, s.optimizer_group_sizes or None)) for s in pl.strings)
        self.assertEqual(len(refs), expected)
        self.assertTrue(all(e.dxf.name == "FV_OTTIMIZZATORE" for e in refs))
        self.assertEqual(dxf_export.audit(path), [])


if __name__ == "__main__":
    unittest.main()
