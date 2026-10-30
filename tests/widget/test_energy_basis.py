"""Both result pages retain the context of the computed year while the live project changes."""
import unittest

import _setup
from meridiana.energy.calculation_basis import CalculationBasis

setUpModule = _setup.keep_global_state


class EnergyBasis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_both_pages_show_computed_subset_before_results_and_keep_it_after_project_edit(self):
        from meridiana import model
        from meridiana.ui.energy_pages import ConsumptionPage, EnergyPage
        basis = CalculationBasis(("Maker INV-20",), 8, 120, 2, "Maker B10", 20, 3.5)
        for kind in (EnergyPage, ConsumptionPage):
            page = kind()
            self.addCleanup(_setup.dispose, page)
            page.show_basis(basis)
            before = page.plant_context.text()
            self.assertIn("1 inverter", before)
            self.assertIn("8 of 120 modules connected", before)
            self.assertIn("2 batteries", before)
            self.assertIn("3.5", before)
            self.assertIn("Maker INV-20", page.plant_context.toolTip())
            project = model.Project()
            project.energy["inverters"] = []
            project.economics["battery_units"] = 9
            if kind is EnergyPage:
                page.show_project(project, [])
            else:
                page.show_project(project)
            page.set_stale(True)
            self.assertEqual(page.plant_context.text(), before)
            self.assertIs(page.calculation_basis, basis)
            self.assertLess(page.results_box.indexOf(page.plant_context), page.results_box.indexOf(page.tiles))
            page.show_basis(None)
            self.assertTrue(page.plant_context.isHidden())
            self.assertEqual(page.plant_context.text(), "")

    def test_plant_context_wraps_inside_a_narrow_results_view_instead_of_being_cut_off(self):
        from meridiana.ui.energy_pages import ConsumptionPage, EnergyPage
        from meridiana.ui.style import pad_fields
        _setup.meridiana_look()
        for kind in (EnergyPage, ConsumptionPage):
            page = kind()
            self.addCleanup(_setup.dispose, page)
            page.show_basis(CalculationBasis(("Maker INV-20",), 8, 120, 2, "Maker B10", 20, 3.5))
            pad_fields(page)
            page.resize(400, 720)
            page.show()
            self.app.processEvents()
            self.assertLessEqual(page.results.width(), page.centre.viewport().width(), kind.__name__)
            self.assertGreaterEqual(page.plant_context.height(),
                                    page.plant_context.heightForWidth(page.plant_context.width()))
