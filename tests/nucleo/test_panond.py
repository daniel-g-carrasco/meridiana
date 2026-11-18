"""PVsyst's component files: a module and an inverter read with PVsyst's units turned into the catalogue's,
a file without the essential values refused with their names, and the import shown before it is used."""

import unittest

import _setup
from _fixtures import OND, PAN
from _fixtures import written as write

from meridiana.catalog import panond
from meridiana.energy.components import InverterSpec, ModuleSpec


class Module(unittest.TestCase):
    def test_a_module_with_pvsysts_units_turned_into_the_catalogues(self):
        rec, said = panond.module(write(PAN, "AS-54-415.PAN"))
        self.assertEqual((rec["manufacturer"], rec["model"]), ("Acme Solar", "AS-54-415"))
        self.assertEqual(rec["pmax"], 415.0)
        self.assertAlmostEqual(rec["alpha_isc"], 6.12 / 13.9 / 10, places=6)       # mA/K to %/K
        self.assertAlmostEqual(rec["beta_voc"], -101.0 / 37.07 / 10, places=6)     # mV/K to %/K
        self.assertEqual((rec["cells"], rec["cells_in_series"]), (108, 54))
        self.assertEqual((rec["length"], rec["width"]), (1.722, 1.134))
        self.assertAlmostEqual(rec["bifaciality"], 70.0)
        self.assertTrue(any("54" in s for s in said))
        m = ModuleSpec.from_record(rec)
        self.assertIn("AS-54-415.PAN", m.source.label)
        self.assertAlmostEqual(m.power_at_25(1000.0), 415.0, delta=415.0 * 0.02)
        # RShunt and RSerie without Gamma: no one-diode model from the file, the datasheet fit instead
        self.assertNotIn("pvsyst_sdm", rec)
        self.assertEqual(m.sdm()["origin"], "fit")
        rec2, said2 = panond.module(write(PAN.replace("  RSerie=0.155\n", "  RSerie=0.155\n  Gamma=0.90\n"), "AS-54-415.PAN"))
        self.assertEqual(rec2["pvsyst_sdm"], {"R_sh_ref": 300.0, "R_s": 0.155, "gamma_ref": 0.90})
        self.assertTrue(any("gamma 0.9" in s for s in said2))
        m2 = ModuleSpec.from_record(rec2)
        self.assertEqual((m2.sdm()["origin"], m2.sdm()["R_sh_0"]), ("pan", 1200.0))     # PVsyst's default 4 x RShunt

    def test_a_file_without_the_essentials_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            panond.module(write(PAN.replace("  Voc=37.070\n", ""), "broken.PAN"))
        self.assertIn("Voc", str(caught.exception))
        with self.assertRaises(ValueError):
            panond.module(write(OND, "not-a-module.PAN"))


class Inverter(unittest.TestCase):
    def test_an_inverter_in_kilowatts_and_its_inputs(self):
        rec, said = panond.inverter(write(OND, "AP-50K.OND"))
        self.assertEqual(rec["ac_power_nominal_w"], 50000.0)
        self.assertEqual((rec["mppt_voltage_min_v"], rec["mppt_voltage_max_v"], rec["dc_voltage_max_v"]),
                         (200.0, 1000.0, 1100.0))
        self.assertEqual((rec["mppt_count"], rec["phases"]), (4, 3))
        self.assertEqual(rec["dc_current_max_a"], 128.0)
        self.assertNotIn("dc_current_max_per_mppt_a", rec)
        inv = InverterSpec.from_record(rec)
        self.assertAlmostEqual(inv.eta, 0.984)
        self.assertIn("AP-50K.OND", inv.source.label)
        self.assertTrue(any("128" in s for s in said))
        self.assertEqual(inv.imax_total, 128.0)
        self.assertIsNone(inv.imax_per_mppt)

    def test_physical_inputs_do_not_supply_the_missing_tracker_count(self):
        rec, said = panond.inverter(write(OND.replace("NbMPPT=4", "NbInputs=8"), "inputs.OND"))
        self.assertNotIn("mppt_count", rec)
        self.assertEqual(rec["dc_input_pairs"], 8)
        self.assertNotIn("dc_current_max_per_mppt_a", rec)
        self.assertTrue(any("NbMPPT" in s for s in said))



class RealFiles(unittest.TestCase):
    """Two files written by PVsyst for real products (pvlib's test data, BSD 3-Clause, tests/data/pvsyst)."""
    DATA = _setup.DATA / "pvsyst"

    def test_a_manufacturers_module(self):
        rec, _said = panond.module(self.DATA / "ET-M772BH550GL.PAN")
        self.assertEqual((rec["manufacturer"], rec["model"], rec["pmax"]), ("ET SOLAR", "ET-M772BH550GL", 550.0))
        self.assertAlmostEqual(rec["alpha_isc"], 0.052, places=6)                 # 7.28 mA/K on 14 A
        self.assertAlmostEqual(rec["beta_voc"], -128.0 / 49.9 / 10, places=6)
        self.assertEqual((rec["cells"], rec["cells_in_series"]), (144, 72))
        self.assertEqual((rec["bypass_diodes"], rec["twin_half_cells"]), (3, True))      # slTwinHalfCells
        self.assertEqual(rec["iam_profile"]["theta"], [0.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0])
        self.assertEqual(rec["iam_profile"]["iam"][-2:], [0.66, 0.0])
        m = ModuleSpec.from_record(rec)
        self.assertAlmostEqual(float(m.power_at_25(1000.0)), 550.0, delta=550.0 * 0.01)
        from meridiana.energy import nearshade
        self.assertEqual(nearshade.blocks_of(m.cells, m.diodes, m.twin), (3, 2))

    def test_a_manufacturers_inverter_with_its_byte_order_mark(self):
        rec, _said = panond.inverter(self.DATA / "CPS SCH275KTL-DO-US-800-250kW_275kVA_1.OND")
        self.assertEqual(rec["manufacturer"], "ChintPower")                       # the file starts with a BOM
        self.assertEqual((rec["ac_power_nominal_w"], rec["mppt_count"], rec["phases"]), (250000.0, 12, 3))
        self.assertEqual((rec["mppt_voltage_min_v"], rec["mppt_voltage_max_v"]), (500.0, 1500.0))
        self.assertEqual(rec["dc_current_max_a"], 360.0)
        self.assertEqual(rec["dc_input_pairs"], 36)
        self.assertNotIn("dc_current_max_per_mppt_a", rec)


if __name__ == "__main__":
    unittest.main()
