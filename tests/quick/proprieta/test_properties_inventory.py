"""R389: runtime inventory of the Properties' fields, against those of the original Properties controls.

The child owns QApplication: the Quick suite may already own QGuiApplication.
Until 10/11/2026 the oracle read the actual bound Widgets, with their ranges and option models; when they went, the
Quick's fields of that day (equal to them) were recorded: quick/aiuti/riferimenti.py.
"""
from collections import Counter
import copy
import os
import subprocess
import sys
import unittest
from pathlib import Path

# in the Properties of Qt Quick only: the Widgets stand as they are while the rewrite goes on (R417, R418)
QUICK_ONLY = {"asset",                        # R374 (r22-f2): the model drawn for a 3D object, Quick only
              "base", "on", "part_of", "saddles.direction", "saddles.band", "saddles.tilt", "saddles.channel",
              "saddles.depth", "saddles.offset",       # study 37 (r20-solidi): the Widgets stay 2,5D
              "params.alignment", "params.target_kwp",
              "roof.keep_ridge",        # R413: asked for Quick, not in the Widgets
              "defaults_take", "defaults_apply"}     # R523: the defaults of the next sub-fields, Quick only


class InventoryCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import _setup
        from meridiana import i18n
        cls.app = _setup.qt_or_skip()
        i18n.setup("en")
        cls.configurations = Counter()
        cls.field_count = 0

    @classmethod
    def tearDownClass(cls):
        print(f"Runtime inventory: {dict(cls.configurations)}; {cls.field_count} editable field comparisons")

    def setUp(self):
        from _fixtures import capannone
        from meridiana.gui.backend.properties import PropertiesBackend
        from meridiana.app.session import ProjectSession
        self.project = capannone()
        self.session = ProjectSession(self.project)
        self.backend = PropertiesBackend(self.session)
        self.addCleanup(self.backend.close)

    def compare(self, kind, obj=None):
        from quick.aiuti import riferimenti
        self.session.select("", "") if kind == "site" else self.session.select(kind, obj.id)
        self.backend.refresh()
        keys = ("label", "kind", "enabled", "value", "minimum", "maximum", "decimals", "unit", "step", "special",
                "options")
        actual = [{key: field.data[key] for key in keys if key in field.data}
                  for section in self.backend.sections for field in section["fields"]
                  if field.data["id"] not in QUICK_ONLY
                  if field.data["kind"] in ("text", "number", "choice", "check") and field.data["visible"]]
        actions = [(field.data["label"], field.data["enabled"]) for section in self.backend.sections
                   for field in section["fields"] if field.data["kind"] == "action" and field.data["visible"]
                   and field.data["id"] not in QUICK_ONLY]
        type(self).configurations[kind] += 1
        type(self).field_count += len(actual)
        riferimenti.check(self, {"fields": actual, "actions": sorted(actions)})

    def test_site_reserved_network_and_rules(self):
        from meridiana.core.model import model
        self.compare("site")
        self.project.network = model.Network(distributor="E-distribuzione", pod="IT001E12345678",
            voltage_v=20000, phases="3", level="MT", connection="new", available_kw=80.5,
            requested_kw=65.2, practice_code="PR-42")
        self.project.rules = {"public": True, "permit_2027": True, "floor_m2": 455, "risk": True}
        for reserved in (False, True):
            with self.subTest(reserved=reserved):
                self.project.reserved = reserved
                self.project.network_consent = {"tiles": "2026-11-04"}
                self.compare("site")

    def test_every_roof_shape_and_canopy(self):
        from meridiana.core.model import model
        building = self.project.buildings[0]
        for kind in ("flat", "mono", "gable", "hip", "free"):
            for canopy in (False, True):
                with self.subTest(roof=kind, canopy=canopy):
                    building.roof = model.Roof(type=kind, tilt=22.5)
                    building.canopy = model.Canopy(bays=7, pillars="two_rows", columns=5) if canopy else None
                    if kind == "free":
                        building.roof.free_pitches = [dict(ring=copy.deepcopy(building.footprint),
                            eave_side=1, eave=8.3, tilt=22.5),
                            dict(ring=[[x + 50, y] for x, y in building.footprint],
                                 eave_side=2, eave=9.4, tilt=17.3)]
                    self.compare("building", building)

    def test_fire_categories_and_legacy_subject(self):
        building = self.project.buildings[0]
        for activity, category, subject in ((0, "B", True), (49, "A", True), (70, "B", True), (57, "C", True)):
            with self.subTest(activity=activity):
                building.fire.activity, building.fire.category, building.fire.subject = activity, category, subject
                self.compare("building", building)

    def test_all_mountings_pitch_modes_support_and_azimuth(self):
        from meridiana.core.model import model
        from meridiana.app.interface.fields import mounting_names, pitch_mode_names
        sf = self.project.subfields[0]
        for mounting in mounting_names():
            for pitch in pitch_mode_names():
                for support in (False, True):
                    with self.subTest(mounting=mounting, pitch=pitch, support=support):
                        sf.params.update(mounting=mounting, pitch_mode=pitch, azimuth=27.4 if support else None,
                            pitch=4.35, gcr=.43, portrait=not support,
                            window={"day": 17, "month": 11, "start": 9.5, "end": 14.5})
                        sf.support = model.SupportPlane(enabled=support, tilt=4.5, azimuth=12.3, z0=17.2)
                        self.compare("subfield", sf)

    def test_manual_and_filled_layout_actions(self):
        sf = self.project.subfields[0]
        for manual in (False, True):
            for filled in (False, True):
                with self.subTest(manual=manual, filled=filled):
                    sf.manual, sf.filled = manual, filled
                    self.compare("subfield", sf)
                    quick = {f.data["label"] for section in self.backend.sections for f in section["fields"]
                             if f.data["kind"] == "action"}
                    # R564: the words of the bar and of the menus (layout_commands): «Fill», «Empty»
                    expected = "Lay again automatically" if manual and filled else "Fill"
                    self.assertIn(expected, quick)
                    self.assertEqual("Empty" in quick, filled)

    def test_all_exclusions_implicit_and_explicit_height(self):
        from meridiana.core.model import model
        for kind in model.exclusion_names():
            for height in (None, 2.35):
                with self.subTest(kind=kind, height=height):
                    obj = model.ExclusionItem("inventory-exclusion", [[1, 1], [3, 1], [3, 3], [1, 3]],
                                              kind=kind, height=height, clearance=.45)
                    self.project.exclusions = [obj]
                    self.compare("exclusion", obj)

    def test_every_prop_kind_default_and_explicit_dimensions(self):
        from meridiana.core.model import model
        from meridiana.core.geometry import props
        # R374 (r22-f2): the kinds of the catalogue of models (the new vehicles, the fixed objects of the site) are
        # Quick only: the Widgets, frozen, know neither them nor their measures (a wanted difference)
        quick_only = set(props.SITE_KINDS) | {"truck", "pickup", "sports_car", "bicycle"}
        for kind in [k for k in model.prop_names() if k not in quick_only]:
            for explicit in (False, True):
                with self.subTest(kind=kind, explicit=explicit):
                    obj = model.Prop("inventory-prop", kind=kind, rotation=47.5,
                        height=2.5 if explicit else None, width=1.5 if explicit else None,
                        length=4.5 if explicit else None, railing=True)
                    self.project.props = [obj]
                    self.compare("prop", obj)

    def test_choice_read_preserves_boolean_identity_and_rejects_integers(self):
        sf = self.project.subfields[0]
        self.compare("subfield", sf)
        field = self.backend.field("params.portrait").data
        for value in (False, True):
            self.assertIs(self.backend._read(field, value), value)
        for value in (0, 1, "true", "False", None):
            with self.subTest(invalid=value), self.assertRaises(ValueError):
                self.backend._read(field, value)


class InventorySubprocessTest(unittest.TestCase):
    def test_original_widgets_field_inventory(self):
        # the tests' helpers and the sources on the path, as in the tests' own process: the CI installs only the
        # requirements, not the program
        tests = Path(__file__).resolve().parents[2]
        path = os.pathsep.join([str(tests), str(tests.parent / "src")])
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--inventory"],
                                capture_output=True, text=True, encoding="utf-8", timeout=180,
                                env=dict(os.environ, PYTHONPATH=path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(InventorySubprocessTest)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InventoryCases)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
