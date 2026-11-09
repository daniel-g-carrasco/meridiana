"""R522: inverters and strings proposed for the modules in no string only (Daniel 07/11/2026): the designer's strings
and inverters stay byte for byte, the free modules go on free inputs of the inverters there are or on inverters added,
and which of the two is said with its DC/AC ratio, of the whole plant and of each inverter."""

import copy
import json
import types
import unittest

import _setup  # noqa: F401

from meridiana.energy import plant, sizing, stringing
from calcoli.test_sizing import groups, inverter, project


def by_hand(gs, sfid, sizes, unit=1, mppt=1):
    """The designer's strings on sub-field `sfid`: consecutive modules in strings of `sizes`, on (unit, mppt)."""
    g = next(g for g in gs if g.sfid == sfid)
    keys = [f"{g.sfid}/{pm.key}" for pm in g.placed]
    out, at = [], 0
    for k, n in enumerate(sizes):
        out.append({"inverter": unit, "mppt": mppt + k if isinstance(mppt, int) and mppt < 0 else mppt,
                    "modules": keys[at:at + n]})
        at += n
    return out


def made(entries, runs):
    p = project(copy.deepcopy(entries))
    p.energy["strings"]["runs"] = copy.deepcopy(runs)
    return p


def dump(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


class FreeModules(unittest.TestCase):
    def test_free_inputs_of_the_inverter_there_is_when_the_ratio_stays_in_the_band(self):
        gs = groups([24, 20])                       # s2 on another face (azimuth 90°): a field of its own
        entries = [{"record": inverter("20K", 20), "count": 1, "name": ""}]
        runs = by_hand(gs, "s1", [12, 12])
        p = made(entries, runs)
        before = dump(p.energy)
        result = sizing.choose_free(p, gs, [inverter("10K", 10), inverter("20K", 20)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.mode, sizing.FREE_INPUTS)
        self.assertEqual(result.added, [])
        self.assertEqual(dump(p.energy), before)              # the project is not touched by the search
        self.assertEqual(dump(result.runs[:2]), dump(runs))   # the designer's strings first, as they were
        self.assertEqual(sum(len(r["modules"]) for r in result.new_runs), 20)
        self.assertFalse({k for r in result.new_runs for k in r["modules"]} & {k for r in runs for k in r["modules"]})
        self.assertTrue(all(r["mppt"] != 1 for r in result.new_runs))   # the other face on another input
        self.assertAlmostEqual(result.ratio, 44 * 450 / 20000, places=6)
        self.assertIn("no inverter is added", result.why)
        self.assertIn("The 2 strings there are stay as they are", result.why)
        self.assertFalse(result.plant.left)

    def test_inverters_added_when_the_free_inputs_would_go_above_the_band(self):
        gs = groups([24, 20])
        entries = [{"record": inverter("10K", 10), "count": 1, "name": "Mine"}]
        runs = by_hand(gs, "s1", [12, 12])
        p = made(entries, runs)
        result = sizing.choose_free(p, gs, [inverter("8K", 8), inverter("10K", 10), inverter("20K", 20)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.mode, sizing.FREE_NEW)
        self.assertEqual(dump(result.entries[:1]), dump(entries))        # the inverter there is, as it was
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.added], [("8K", 1)])
        self.assertTrue(all(r["inverter"] == 2 for r in result.new_runs))  # numbered after the ones there are
        self.assertEqual(dump(result.runs[:2]), dump(runs))
        self.assertIn("above the band", result.why)
        ratios = plant.unit_ratios(result.plant)
        self.assertAlmostEqual(ratios[1], 24 * 450 / 10000, places=6)
        self.assertAlmostEqual(ratios[2], 20 * 450 / 8000, places=6)
        self.assertAlmostEqual(result.ratio, 44 * 450 / 18000, places=6)
        # the free inputs above the band are an alternative, said as such
        self.assertTrue(any(a.mode == sizing.FREE_INPUTS and a.standing == sizing.ABOVE_BAND for a in result.alternatives))

    def test_inverters_added_when_no_free_input_takes_them(self):
        gs = groups([24, 20])
        one = inverter("10K1", 10, mppt_count=1, strings_per_mppt=[2], dc_current_max_per_mppt_a=[30],
                       dc_isc_max_per_mppt_a=[40])
        entries = [{"record": one, "count": 1, "name": ""}]
        runs = by_hand(gs, "s1", [12, 12])
        result = sizing.choose_free(made(entries, runs), gs, [inverter("8K", 8)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.mode, sizing.FREE_NEW)
        self.assertIn("do not take them", result.why)

    def test_free_inputs_for_some_and_an_inverter_added_for_the_rest(self):
        gs = groups([24, 20, 20])                   # three faces; the inverter there is has one free input
        two = inverter("20K2", 20, mppt_count=2, dc_current_max_per_mppt_a=[60] * 2, dc_isc_max_per_mppt_a=[100] * 2)
        entries = [{"record": two, "count": 1, "name": ""}]
        runs = by_hand(gs, "s1", [12, 12])
        result = sizing.choose_free(made(entries, runs), gs, [inverter("8K", 8), two], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.mode, sizing.FREE_BOTH)
        self.assertEqual(dump(result.runs[:2]), dump(runs))
        on_one = [r for r in result.new_runs if r["inverter"] == 1]
        self.assertEqual({r["mppt"] for r in on_one}, {2})
        self.assertEqual([(e["record"]["model"], e["count"]) for e in result.added], [("8K", 1)])
        ratios = plant.unit_ratios(result.plant)
        self.assertAlmostEqual(ratios[1], 44 * 450 / 20000, places=6)
        self.assertAlmostEqual(ratios[2], 20 * 450 / 8000, places=6)
        self.assertIn("20 of the 40 modules in no string go on free inputs", result.why)
        self.assertTrue(any(a.mode == sizing.FREE_NEW for a in result.alternatives))   # all on new ones, listed

    def test_an_error_already_in_the_designer_s_part_does_not_refuse_the_free_modules(self):
        # Rho, 07/11/2026: a string by hand 57,9 A on 40 A refused every proposal for the free modules
        gs = groups([24, 20])
        tight = inverter("20K", 20, dc_isc_max_per_mppt_a=[25] * 4)
        entries = [{"record": tight, "count": 1, "name": ""}]
        runs = by_hand(gs, "s1", [12, 12])                       # two strings on input 1: over its 25 A
        p = made(entries, runs)
        self.assertTrue(sizing._failing_units(plant.build(p, groups=gs)))
        result = sizing.choose_free(p, gs, [inverter("8K", 8)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(dump(result.runs[:2]), dump(runs))
        self.assertFalse(result.plant.left)
        # the error stays said by the checks, the new strings are valid
        new = [s for s in result.plant.strings if s.run < 0 or s.run >= 2]
        self.assertTrue(new and all(plant.acceptable(s) for s in new))

    def test_nothing_free_says_so(self):
        gs = groups([24])
        runs = by_hand(gs, "s1", [12, 12])
        result = sizing.choose_free(made([{"record": inverter("10K", 10), "count": 1, "name": ""}], runs), gs,
                                    [inverter("10K", 10)], 1.1)
        self.assertFalse(result.ok)
        self.assertIn("no modules in no string", result.reason)

    def test_no_inverter_there_sizes_the_free_modules_alone(self):
        gs = groups([24, 20])
        result = sizing.choose_free(made([], []), gs, [inverter("20K", 20), inverter("10K", 10)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.mode, sizing.FREE_NEW)
        self.assertFalse(result.plant.left)

    def test_a_sub_field_sent_to_an_inverter_gets_no_new_one(self):
        gs = groups([24, 20])
        gs[1].target = (1, 0)
        entries = [{"record": inverter("10K", 10), "count": 1, "name": ""}]
        runs = by_hand(gs, "s1", [12, 12])
        result = sizing.choose_free(made(entries, runs), gs, [inverter("8K", 8)], 1.1)
        # the free inputs above the band are the only way: taken, and said
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.mode, sizing.FREE_INPUTS)
        self.assertEqual(result.standing, sizing.ABOVE_BAND)
        self.assertTrue(any("Above the band" in n for n in result.notes))


class FreeModulesTimeLimit(unittest.TestCase):
    """R522, Daniel 07/11/2026 sera: «un limite di tempo ragionevole» (Rho: 11 minutes and no proposal). The search
    ends within FREE_SECONDS with the best proposal found; «Stop» (`enough`) the same at once; cancel throws it away."""

    def slow(self, pause):
        # every string search of a candidate costs `pause` seconds, as a big roof does: on a clock of the test, the
        # search's own (stringing.time and sizing.time), so nothing waits
        real = plant.build
        builds, clock = [], [1000.0]

        def build(*args, **kw):
            builds.append(1)
            clock[0] += pause
            return real(*args, **kw)
        fake = types.SimpleNamespace(monotonic=lambda: clock[0])
        for module in (stringing, sizing):
            self.addCleanup(setattr, module, "time", module.time)
            module.time = fake
        self.addCleanup(setattr, plant, "build", real)
        plant.build = build
        self.clock = clock
        return builds

    def records(self):
        return [inverter(f"{kw}K", kw) for kw in (5, 6, 8, 10, 12, 15, 17, 20, 25, 30)]

    def test_a_limit_of_reasonable_seconds_is_written_in_one_place(self):
        self.assertTrue(10 <= sizing.FREE_SECONDS <= 30)

    def test_the_search_ends_at_its_time_limit(self):
        builds = self.slow(0.25)
        gs = groups([24, 20, 16])
        start = self.clock[0]
        result = sizing.choose_free(made([], []), gs, self.records(), 1.1, seconds=1.0)
        self.assertLessEqual(self.clock[0] - start, 1.0 + 3 * 0.25)   # a candidate or two past the limit, not minutes
        self.assertLessEqual(len(builds), 7)
        if result.ok:
            self.assertFalse(result.plant.left)
        else:
            self.assertIn("time limit", result.reason)

    def test_stop_keeps_the_best_proposal_found_until_then(self):
        builds = self.slow(0.0)     # the plant there is, then the first candidate (valid): stopped before the second
        gs = groups([24, 20])
        result = sizing.choose_free(made([], []), gs, self.records(), 1.1, enough=lambda: len(builds) >= 3)
        self.assertTrue(result.ok, result.reason)
        self.assertFalse(result.plant.left)
        self.assertTrue(any("Search stopped" in n for n in result.notes), result.notes)

    def test_cancel_still_throws_everything_away(self):
        result = sizing.choose_free(made([], []), groups([24, 20]), self.records(), 1.1, cancelled=lambda: True)
        self.assertFalse(result.ok)

    def test_modules_no_inverter_strings_stay_free_and_the_rest_is_proposed(self):
        # Rho, 07/11/2026 sera: a few free modules on a face no inverter strings (too few for its MPPT window) kept every
        # proposal away for 11 minutes; now the best proposal strings the others, and says how many stay free
        gs = groups([24, 20, 3])
        self.assertFalse(sizing.choose(made([], []), gs, self.records(), 1.1).ok)    # the whole plant: still none
        result = sizing.choose_free(made([], []), gs, self.records(), 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.left, 3)
        self.assertEqual(sum(len(r["modules"]) for r in result.new_runs), 44)
        self.assertTrue(all(plant.acceptable(s) for s in result.plant.strings))
        self.assertIn("3 modules stay in no string", result.notes[0])


class FreeModulesAsADesigner(unittest.TestCase):
    """R522 r22-impianto (Daniel 07/11/2026): the free inputs of the inverters there are filled first, up to the ratio
    asked; for the rest inverters of the right size, each inside the band; the window says the ratio of each one."""

    def records(self):
        return [inverter(f"{kw}K", kw) for kw in (5, 6, 8, 10, 12, 15, 17, 20, 25, 30)]

    def test_the_inverter_there_is_filled_first_and_the_rest_gets_the_right_size(self):
        # Rho in small: an inverter of the designer with every input free (his strings taken away), 84 free modules
        gs = groups([48, 36])
        entries = [{"record": inverter("20K", 20), "count": 1, "name": ""}]
        result = sizing.choose_free(made(entries, []), gs, self.records(), 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.mode, sizing.FREE_BOTH)
        self.assertEqual(result.left, 0)
        self.assertEqual(sum(e["count"] for e in result.added), 1)
        low, high = sizing.band(1.1)
        ratios = plant.unit_ratios(result.plant)
        self.assertEqual(sorted(ratios), [1, 2])
        for k, r in ratios.items():
            self.assertTrue(low <= r <= high, (k, r))       # the inverter there is and the one added, both in the band
        self.assertTrue(low <= result.ratio <= high)
        self.assertTrue(all(plant.acceptable(s) for s in result.plant.strings))
        self.assertIn("1: ", result.why)                      # the ratio of each inverter, in the words

    def test_no_proposal_inside_the_band_says_so(self):
        result = sizing.choose_free(made([], []), groups([20]), [inverter("50K", 50)], 1.1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.standing, sizing.UNDER_ONE)
        self.assertIn("Outside the band", result.why)
        self.assertIn("no combination of this brand", result.why)

    def test_an_inverter_there_is_left_empty_is_not_the_proposal(self):
        # the old search took new inverters for every module and left the designer's own inverter with no string
        gs = groups([48, 36])
        entries = [{"record": inverter("20K", 20), "count": 1, "name": ""}]
        result = sizing.choose_free(made(entries, []), gs, self.records(), 1.1)
        self.assertGreater(plant.unit_ratios(result.plant)[1], 0.9)



class SmallFaceGoesOnOverTheNextOne(unittest.TestCase):
    """R522 r24-scelte (Daniel 08/11/2026): a face too small for a string of whole rows does not go along a path of
    its own on an input of its own: the string goes on over the face next to it when R433 allows it (same building;
    without optimizers only with compatible exposures), else its modules stay in no string and the window says why."""

    def case(self, building="b1", azimuth=0.0, across=False):
        from unittest import mock

        from meridiana.energy import faces
        from calcoli.test_sizing import grid
        gs = groups([54, 5])                        # rows of 12: 4 whole and one of 6; the small face: 5 modules
        small = grid(5, azimuth)
        for pm in small:                            # beside the last row of the big face
            pm.centre = (pm.centre[0], pm.centre[1] + 15.0)
            pm.corners = [(x, y + 15.0) for x, y in pm.corners]
        gs[1].placed = small
        p = made([], [])
        p.energy["strings"]["strategy"] = "rows"
        if across:
            p.energy["strings"][plant.ACROSS] = True
        face_of = {"s1": faces.Face("b1", 0, "Capannone, falda 1"),
                   "s2": faces.Face(building, 1 if building == "b1" else 0, "Tettoia, falda 2")}
        with mock.patch.object(faces, "faces_of", lambda project: face_of):
            result = sizing.choose_free(p, gs, [inverter("20K", 20), inverter("25K", 25)], 1.1)
        self.assertTrue(result.ok, result.reason)
        return result

    def strings_of_s2(self, result):
        return [r for r in result.new_runs if any(k.startswith("s2/") for k in r["modules"])]

    def test_the_string_goes_on_over_the_face_next_to_it(self):
        result = self.case()
        mixed = self.strings_of_s2(result)
        self.assertEqual(len(mixed), 1, result.new_runs)
        keys = mixed[0]["modules"]
        self.assertEqual(sum(k.startswith("s2/") for k in keys), 5)     # the whole small face, once
        self.assertTrue(any(k.startswith("s1/") for k in keys))         # and on over the big one
        self.assertFalse(any(k[0] == "s2" for k in result.plant.left))
        self.assertTrue(all(plant.acceptable(s) for s in result.plant.strings))
        self.assertIn("runs over Capannone, falda 1 and Tettoia, falda 2", result.why)
        self.assertIn("Length of the new strings", result.why)

    def test_between_two_buildings_it_stays_in_no_string_and_says_why(self):
        result = self.case(building="b2")
        self.assertEqual(self.strings_of_s2(result), [])
        self.assertEqual(sum(1 for k in result.plant.left if k[0] == "s2"), 5)
        self.assertIn("another building", result.why)
        self.assertIn("only by hand (R433)", result.why)

    def test_without_optimizers_other_exposures_stop_it_unless_the_designer_asked(self):
        result = self.case(azimuth=90.0)
        self.assertEqual(self.strings_of_s2(result), [])
        self.assertIn("compatible exposures", result.why)
        asked = self.case(azimuth=90.0, across=True)
        self.assertEqual(len(self.strings_of_s2(asked)), 1)

    def test_no_face_goes_along_a_path_of_its_own_on_an_input_of_its_own(self):
        result = self.case(building="b2")
        for r in result.new_runs:
            self.assertEqual(len({k.split("/")[0] for k in r["modules"]}), 1)
            self.assertFalse(all(k.startswith("s2/") for k in r["modules"]))


if __name__ == "__main__":
    unittest.main()
