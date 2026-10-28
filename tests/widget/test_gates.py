"""A checkbox gates the fields it owns without discarding their values (R194)."""

import unittest

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state


class Gates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()

    def test_the_community_fields_are_writable_only_with_their_checkbox(self):
        from meridiana import model
        from meridiana.ui.energy_pages import EconomicsPage
        page = EconomicsPage()
        self.addCleanup(page.deleteLater)
        project = model.Project(economics={"community": False, "shared_pct": 75, "pz": 123})
        page.show_project(project)
        fields = [page.fields[key] for key in ("shared_pct", "pz", "trase", "grant_pct")] + [page.zone]
        self.assertTrue(all(not field.isEnabled() for field in fields))
        self.assertTrue(all("community" in field.toolTip().lower() for field in fields))
        page.fields["shared_pct"].setValue(80)
        page.community.setChecked(True)
        self.assertTrue(all(field.isEnabled() for field in fields))
        page.community.setChecked(False)
        self.assertEqual(page.fields["shared_pct"].value(), 80)
        self.assertEqual(page.fields["pz"].value(), 123)
        self.assertFalse(page.community.isChecked())

    def test_the_same_gate_applies_to_lid_and_azimuth(self):
        from meridiana.ui.energy_pages import EnergyPage
        from meridiana.ui.properties import Properties
        energy = EnergyPage()
        self.addCleanup(energy.deleteLater)
        energy.lid_auto.setChecked(True)
        self.assertFalse(energy.lid.isEnabled())
        self.assertIn("datasheet", energy.lid.toolTip())
        energy.lid_auto.setChecked(False)
        self.assertTrue(energy.lid.isEnabled())
        project = capannone()
        props = Properties()
        self.addCleanup(props.deleteLater)
        props.show_subfield(project, project.subfields[0], project.fill(project.subfields[0]))
        azimuth = next(field for field in props.widget().findChildren(type(energy.lid))
                       if field.minimum() == -180 and field.maximum() == 180)
        self.assertFalse(azimuth.isEnabled())
        self.assertIn("Automatic", azimuth.toolTip())


if __name__ == "__main__":
    unittest.main()
