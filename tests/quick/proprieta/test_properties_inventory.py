"""R389: runtime inventory against the original Properties controls.

The child owns QApplication: the Quick suite may already own QGuiApplication.
The oracle reads actual bound Widgets, including their ranges and option models;
it never parses Python source or rebuilds a second copy of the Quick schema.
"""
from collections import Counter, defaultdict
import copy
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
        from meridiana.quick.backend.properties import PropertiesBackend
        from meridiana.session import ProjectSession
        from meridiana.ui.properties import Properties
        from shiboken6 import delete
        self.project = capannone()
        self.session = ProjectSession(self.project)
        self.backend = PropertiesBackend(self.session)
        self.widget = Properties()
        self.addCleanup(delete, self.widget)
        self.addCleanup(self.backend.close)

    def visible(self, widget):
        from PySide6.QtCore import Qt
        page = self.widget.widget()
        while widget is not None and widget is not page:
            if widget.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide) and widget.isHidden():
                return False
            widget = widget.parentWidget()
        return True

    def label(self, widget):
        from PySide6.QtWidgets import QCheckBox, QFormLayout
        if isinstance(widget, QCheckBox):
            return widget.accessibleName() or widget.text()
        # The Widgets date shares a single Day row: the month is its second spin.
        if widget is getattr(self.widget, "sun_month", None):
            return "Month"
        for form in self.widget.widget().findChildren(QFormLayout):
            candidate = widget
            while candidate is not None and candidate is not self.widget.widget():
                label = form.labelForField(candidate)
                if label is not None:
                    return label.text()
                candidate = candidate.parentWidget()
        self.fail(f"No label for {widget!r}")

    def widget_fields(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox, QWidget
        editable = (QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox)
        fields, seen = [], set()
        for widget, _value, _setter in self.widget._binds:
            if id(widget) in seen or not isinstance(widget, editable) or not self.visible(widget):
                continue
            seen.add(id(widget))
            field = dict(label=self.label(widget), enabled=widget.isEnabled())
            if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                field.update(kind="number", value=widget.value(), minimum=widget.minimum(),
                    maximum=widget.maximum(), step=widget.singleStep(),
                    decimals=widget.decimals() if isinstance(widget, QDoubleSpinBox) else 0,
                    unit=getattr(widget, "unit", widget.suffix().strip()), special=widget.specialValueText())
            elif isinstance(widget, QComboBox):
                field.update(kind="choice", value=widget.currentData(), options=[
                    dict(value=widget.itemData(i), label=widget.itemText(i),
                         enabled=bool(widget.model().flags(widget.model().index(i, 0)) & Qt.ItemFlag.ItemIsEnabled))
                    for i in range(widget.count())])
            elif isinstance(widget, QCheckBox):
                field.update(kind="check", value=widget.isChecked())
            else:
                field.update(kind="text", value=widget.text())
            fields.append(field)
        # Catch editable controls omitted from _binds, without counting a spin's
        # internal line edit or the search line inside the activities combo.
        all_controls = []
        for widget in self.widget.widget().findChildren(QWidget):
            if not isinstance(widget, editable) or not self.visible(widget):
                continue
            if isinstance(widget, QLineEdit) and isinstance(widget.parentWidget(), (QDoubleSpinBox, QSpinBox, QComboBox)):
                continue
            all_controls.append(widget)
        self.assertEqual(set(map(id, all_controls)), seen, "Unbound editable Widgets control")
        return fields

    def compare(self, kind, obj=None):
        from PySide6.QtWidgets import QPushButton
        if kind == "site":
            self.session.select("", "")
            self.widget.show_site(self.project, not (self.project.buildings or self.project.subfields))
        else:
            self.session.select(kind, obj.id)
            if kind == "subfield":
                self.widget.show_subfield(self.project, obj, None)
            else:
                getattr(self.widget, "show_" + kind)(obj)
        self.backend.refresh()
        actual = [field.data for section in self.backend.sections for field in section["fields"]
                  if field.data["id"] not in QUICK_ONLY
                  if field.data["kind"] in ("text", "number", "choice", "check") and field.data["visible"]]
        expected = self.widget_fields()
        type(self).configurations[kind] += 1
        type(self).field_count += len(expected)
        self.assertEqual(Counter((f["label"], f["kind"]) for f in actual),
                         Counter((f["label"], f["kind"]) for f in expected), "Editable field inventory")
        grouped = defaultdict(list)
        for field in actual:
            grouped[field["label"], field["kind"]].append(field)
        for old in expected:
            new = grouped[old["label"], old["kind"]].pop(0)
            with self.subTest(field=new["id"]):
                self.assertEqual(new["enabled"], old["enabled"])
                if old["kind"] == "number":
                    for key in ("minimum", "maximum", "decimals", "unit", "step", "special"):
                        self.assertEqual(new[key], old[key], key)
                    self.assertAlmostEqual(new["value"], old["value"], delta=.5 * 10 ** -old["decimals"] + 1e-9)
                else:
                    self.assertEqual(new["value"], old["value"])
                    self.assertIs(type(new["value"]), type(old["value"]))
                if old["kind"] == "choice":
                    self.assertEqual(new["options"], old["options"])
                    self.assertEqual([type(o["value"]) for o in new["options"]],
                                     [type(o["value"]) for o in old["options"]])
        actual_actions = [field.data for section in self.backend.sections for field in section["fields"]
                          if field.data["kind"] == "action" and field.data["visible"]
                          and field.data["id"] not in QUICK_ONLY]
        old_buttons = [button for button in self.widget.widget().findChildren(QPushButton)
                       if self.visible(button) and button.text() and button.text() != "?"]
        self.assertEqual(Counter((field["label"], field["enabled"]) for field in actual_actions),
                         Counter((button.text(), button.isEnabled()) for button in old_buttons), "Action inventory")

    def test_site_reserved_network_and_rules(self):
        from meridiana import model
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
        from meridiana import model
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
        from meridiana import model
        from meridiana.fields import mounting_names, pitch_mode_names
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
        from PySide6.QtWidgets import QPushButton
        sf = self.project.subfields[0]
        for manual in (False, True):
            for filled in (False, True):
                with self.subTest(manual=manual, filled=filled):
                    sf.manual, sf.filled = manual, filled
                    self.compare("subfield", sf)
                    captions = {button.text() for button in self.widget.widget().findChildren(QPushButton)}
                    quick = {f.data["label"] for section in self.backend.sections for f in section["fields"]
                             if f.data["kind"] == "action"}
                    expected = "Lay again automatically" if manual and filled else "Lay again" if filled else "Lay the modules"
                    self.assertIn(expected, captions)
                    self.assertIn(expected, quick)
                    self.assertEqual("Take them out" in captions, filled)
                    self.assertEqual("Take them out" in quick, filled)

    def test_all_exclusions_implicit_and_explicit_height(self):
        from meridiana import model
        for kind in model.exclusion_names():
            for height in (None, 2.35):
                with self.subTest(kind=kind, height=height):
                    obj = model.ExclusionItem("inventory-exclusion", [[1, 1], [3, 1], [3, 3], [1, 3]],
                                              kind=kind, height=height, clearance=.45)
                    self.project.exclusions = [obj]
                    self.compare("exclusion", obj)

    def test_every_prop_kind_default_and_explicit_dimensions(self):
        from meridiana import model, props
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
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--inventory"],
                                capture_output=True, text=True, encoding="utf-8", timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(InventorySubprocessTest)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InventoryCases)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
