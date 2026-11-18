"""The plan of the plant in the report (R436): every string in a hue of its own with its name (inverter.input.string) and
its two ends, the optimizers where the inverter has them, and a sheet for each sub-field when on one sheet the modules
would be too small to read on A4. Without Qt: the SVG as text."""

import re
import unittest
from types import SimpleNamespace

import _setup  # noqa: F401
from _fixtures import capannone

from meridiana import jobs, model
from meridiana.energy import plant as plants
from meridiana.report_typst import figures


INVERTER = {"manufacturer": "Acme", "model": "AC-20K", "ac_power_nominal_w": 20000, "efficiency_euro_pct": 97.5,
            "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180, "mppt_voltage_max_v": 1000, "mppt_count": 2,
            "dc_current_max_per_mppt_a": [26, 26], "dc_isc_max_per_mppt_a": [40, 40]}


def laid(project, record=None, count: int = 2):
    """The layouts and the strings Meridiana proposes on them, on `count` inverters `record` (20 kW by default)."""
    project.energy["inverters"] = [{"record": record or INVERTER, "count": count, "name": ""}]
    project.energy["strings"] = {"auto": True}
    results, _keys, _laid = jobs.layout_of(project)
    return results, plants.build(project, results)


def labels(svg: bytes) -> list[str]:
    return re.findall(r'font-weight="700" text-anchor="middle" fill="#[0-9a-f]{6}">([^<]+)</text>', svg.decode())


class PlantPlan(unittest.TestCase):
    def test_every_string_has_its_name_its_hue_and_its_two_ends_on_one_sheet(self):
        p = capannone()
        results, pl = laid(p)
        self.assertGreater(len(pl.strings), 2)
        [sheet] = figures.plant_sheets(p, results, pl)
        self.assertEqual(sorted(labels(sheet.svg)), sorted(s.label for s in pl.strings))
        hues = figures.string_hues(pl, results)
        self.assertEqual(set(hues), {s.label for s in pl.strings})
        self.assertTrue(set(hues.values()) <= set(figures.STRING_HUES))
        self.assertEqual(sheet.svg.decode().count("<circle"), 2 * len(pl.strings))     # first and last module
        self.assertEqual(sheet.optimizers, 0)
        self.assertEqual(sheet.title, "")

    def test_two_roofs_far_apart_get_a_sheet_each_with_their_own_strings(self):
        p = capannone()
        b = model.Building(id=p.new_id("b"), name="Magazzino", footprint=[[400, 300], [440, 300], [440, 320], [400, 320]],
                           height=7.0)
        p.buildings.append(b)
        p.subfields.append(model.SubField(id=p.new_id("s"), name="Nord", ring=[[401, 301], [439, 301], [439, 319],
                                                                             [401, 319]],
                                          building=b.id, params={"tilt": 15.0}, filled=True))
        results, pl = laid(p)
        sheets = figures.plant_sheets(p, results, pl)
        self.assertEqual([s.title for s in sheets], ["Sud", "Nord"])
        mine = [{s.label for s in sheet.strings} for sheet in sheets]
        self.assertFalse(mine[0] & mine[1])
        self.assertEqual(mine[0] | mine[1], {s.label for s in pl.strings})
        for sheet, names in zip(sheets, mine, strict=True):
            self.assertEqual(set(labels(sheet.svg)), names)

    def test_the_optimizers_are_drawn_one_for_each_group_of_modules(self):
        from meridiana import catalog
        from meridiana.energy import optimizers
        p = capannone()
        se = next(r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None) if r["model"] == "SE50K")
        results, pl = laid(p, se, 1)
        self.assertTrue(pl.optimized and pl.strings)
        [sheet] = figures.plant_sheets(p, results, pl)
        per = pl.units[0].choice.per
        expected = sum(len(optimizers.module_groups(s.modules, per, s.optimizer_group_sizes or None))
                       for s in pl.strings)
        self.assertEqual(sheet.optimizers, expected)
        self.assertEqual(sheet.svg.decode().count(f'fill="{figures.OPTIMIZER}"'), expected)
        self.assertLess(expected, sum(len(s.modules) for s in pl.strings))          # S1000: two modules on each

    def test_the_modules_in_no_string_are_grey_and_counted(self):
        p = capannone()
        results, pl = laid(p)
        some = SimpleNamespace(units=pl.units, strings=pl.strings[:1])
        [sheet] = figures.plant_sheets(p, results, some)
        laid_n = len(results[p.subfields[0].id].modules)
        self.assertEqual(sheet.free, laid_n - len(pl.strings[0].modules))

    def test_no_strings_no_sheet(self):
        p = capannone()
        results, _pl = laid(p)
        self.assertEqual(figures.plant_sheets(p, results, SimpleNamespace(units=[], strings=[])), [])
        self.assertEqual(figures.plant_sheets(p, results, None), [])


if __name__ == "__main__":
    unittest.main()
