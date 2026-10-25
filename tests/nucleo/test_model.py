"""The project in the core (model.py): the variants, the workflow of a sub-field, what a change touches, names and
copies, roofs on any outline, typed settings, pitches, the rows by hand. The file itself, its versions and its
damages are in formati/test_project_files.py."""

import dataclasses
import json
import math
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import _setup
from _fixtures import capannone_rho as sample

from meridiana import model


class Variants(unittest.TestCase):
    def test_a_new_project_has_one_variant(self):
        p = model.Project()
        self.assertEqual([v["name"] for v in p.variants], ["Base"])
        self.assertEqual(p.current_variant()["id"], p.variant)

    def test_a_new_variant_is_a_copy_and_each_keeps_its_own_design(self):
        p = sample()
        p.energy = {"losses": {"soiling": 2.0}}
        base = p.variant
        second = p.add_variant("Tilt 30")
        self.assertEqual(p.variant, second)
        self.assertEqual([v["id"] for v in p.variants], [base, second])
        p.subfields[0].params["tilt"] = 30.0
        p.energy["losses"]["soiling"] = 4.0
        p.switch_variant(base)
        self.assertEqual(p.subfields[0].params["tilt"], 15.0)            # the base came back as it was
        self.assertEqual(p.energy["losses"]["soiling"], 2.0)
        self.assertEqual(p.design_of(second)["subfields"][0]["params"]["tilt"], 30.0)
        self.assertNotIn("design", p.current_variant())
        p.switch_variant(second)
        self.assertEqual(p.subfields[0].params["tilt"], 30.0)
        self.assertEqual(len(p.buildings), 1)                             # the site is shared

    def test_variants_are_saved_and_the_one_in_hand_comes_back(self):
        p = sample()
        base = p.variant
        p.add_variant("Est-ovest")
        p.subfields[0].params["mounting"] = "east_west"
        q = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual(q.variant, p.variant)
        self.assertEqual(q.subfields[0].params["mounting"], "east_west")
        q.switch_variant(base)
        self.assertNotIn("mounting", q.subfields[0].params)

    def test_the_one_in_hand_and_the_last_cannot_be_deleted(self):
        p = sample()
        base = p.variant
        with self.assertRaises(ValueError):
            p.remove_variant(base)
        second = p.add_variant("Altro")
        p.remove_variant(base)
        self.assertEqual([v["id"] for v in p.variants], [second])

    def test_a_file_before_variants_gets_its_base(self):
        data = sample().to_json()
        data["version"] = 3
        data.update(data["variants"][0]["design"])          # before the variants the design was the project's
        del data["variants"], data["variant"]
        q = model.Project.from_json(data)
        self.assertEqual([v["name"] for v in q.variants], ["Base"])
        self.assertEqual(len(q.subfields), 1)

    def test_the_file_holds_every_variant_with_its_design_and_the_project_the_working_copy(self):
        p = sample()
        base = p.variant
        second = p.add_variant("Altro")
        p.subfields[0].params["tilt"] = 30.0
        data = p.to_json()
        for key in model.DESIGN:
            self.assertNotIn(key, data)                     # format 7: one representation, in the variants
        designs = {v["id"]: v["design"] for v in data["variants"]}
        self.assertEqual(sorted(designs), [base, second])
        self.assertEqual(designs[second]["subfields"][0]["params"]["tilt"], 30.0)
        self.assertEqual(designs[base]["subfields"][0]["params"]["tilt"], 15.0)
        self.assertNotIn("design", p.current_variant())     # in memory the one in hand is the working copy
        self.assertNotIn("app_version", data)
        q = model.Project.from_json(json.loads(json.dumps(data)))
        self.assertEqual((q.variant, q.subfields[0].params["tilt"]), (second, 30.0))
        self.assertEqual(q.to_json(), data)

    def test_a_variant_without_a_design_or_unknown_is_said_not_a_crash(self):
        p = sample()
        p.variants.append({"id": "v9", "name": "Vuota", "note": ""})
        p.switch_variant("v9")                              # a file written by hand: an empty design
        self.assertEqual(p.subfields, [])
        with self.assertRaises(KeyError):
            p.switch_variant("v10")
        with self.assertRaises(KeyError):
            p.design_of("v10")


class Workflow(unittest.TestCase):
    def test_a_new_sub_field_is_not_filled_until_asked(self):
        self.assertFalse(sample().subfields[0].filled)

    def test_ids_are_unique_and_short(self):
        p = sample()
        self.assertEqual(p.new_id("s"), "s2")

    def test_a_subject_building_brings_the_fire_rules(self):
        p = sample()
        r = p.fill(p.subfields[0])
        self.assertGreater(r.count, 50)
        self.assertTrue(all(m.tilt == 15.0 for m in r.modules))

    def test_the_sub_field_parameters_reach_the_layout(self):
        params = sample().subfields[0].layout_params()
        self.assertEqual(params.stack, 2)
        self.assertEqual(params.tilt, 15.0)

    def test_the_sites_design_window_sets_the_row_pitch(self):
        p = sample()
        sf = p.subfields[0]
        sf.params["mounting"] = "tilted_anchored"
        short = p.fill(sf).pitch
        p.sun_window = {**p.sun_window, "start": 9.0, "end": 15.0}             # a longer day without shade
        self.assertGreater(p.fill(sf).pitch, short + 0.05)
        sf.params["window"] = {**p.sun_window, "start": 10.0, "end": 14.0}     # the sub-field's own wins
        self.assertAlmostEqual(p.fill(sf).pitch, short)

    def test_modules_out_of_the_obstacles_shadows(self):
        import numpy as np
        from shapely.geometry import Point

        from meridiana import sun
        from meridiana.energy import nearshade, system
        p = model.Project(site=model.Site(lat=45.5, lon=9.2))
        p.buildings.append(model.Building(id="b1", name="Tetto", footprint=[[0, 0], [30, 0], [30, 20], [0, 20]],
                                          height=6.0))
        p.exclusions.append(model.ExclusionItem(id="e1", ring=[[14, 3], [16, 3], [16, 5], [14, 5]], kind="plant",
                                                building="b1", height=2.5))
        sf = model.SubField(id="s1", name="Tetto", ring=[[1, 1], [29, 1], [29, 19], [1, 19]], building="b1",
                            params={"mounting": "tilted_anchored", "tilt": 10.0}, filled=True)
        p.subfields.append(sf)
        free = p.fill(sf)
        sf.params["shade_free"] = True
        kept = p.fill(sf, shade=system.shadow_exclusions)
        self.assertLess(kept.count, free.count)
        self.assertGreater(kept.count, 0.6 * free.count)                     # only the shadow goes, not the roof
        noon = sun.DesignWindow(start=12.0, end=12.0).positions(45.5, 9.2)[0]
        shade = nearshade.plan_shadow(system.obstacles_of(p, sf), noon.bearing, noon.elevation, 6.0)
        self.assertGreater(shade.area, 10.0)                                 # 2.5 m at 21° of sun: some 6 m long
        inside = [pm for pm in kept.modules if shade.contains(Point(np.mean([c[0] for c in pm.corners]),
                                                                   np.mean([c[1] for c in pm.corners])))]
        self.assertEqual(inside, [])
        p.exclusions.clear()                                                 # nothing to avoid: nothing changes
        self.assertEqual(p.fill(sf, shade=system.shadow_exclusions).count, p.fill(model.SubField(**{
            **sf.__dict__, "params": {"mounting": "tilted_anchored", "tilt": 10.0}})).count)

    def test_obstacles_rise_from_their_roof(self):
        p = sample()
        prisms = {o["id"]: o for o in p.obstacle_prisms() if o["kind"] != "parapet"}
        vent, plant = prisms["e1"], prisms["e2"]
        self.assertEqual((vent["z0"], vent["z1"]), (9.5, 9.5 + model.OBSTACLE_HEIGHTS["vent"]))
        self.assertAlmostEqual(plant["z1"], 9.5 + 2.2)
        p.exclusions.append(model.ExclusionItem(id="e9", ring=[[50, 5], [52, 5], [52, 7], [50, 7]], kind="tree"))
        tree = next(o for o in p.obstacle_prisms() if o["id"] == "e9")
        self.assertEqual((tree["z0"], tree["z1"]), (0.0, model.OBSTACLE_HEIGHTS["tree"]))
        p.exclusions.append(model.ExclusionItem(id="e10", ring=[[5, 5], [6, 5], [6, 6]], kind="walkway",
                                                building="b1"))
        self.assertFalse(any(o["id"] == "e10" for o in p.obstacle_prisms()))

    def test_a_parapet_runs_inside_the_outline(self):
        from shapely.geometry import Polygon
        p = sample()
        quads = [o for o in p.obstacle_prisms() if o["kind"] == "parapet"]
        self.assertEqual(len(quads), 4)
        outline = Polygon(p.buildings[0].footprint).buffer(1e-9)
        for o in quads:
            self.assertTrue(outline.contains(Polygon(o["ring"])))
            self.assertEqual((o["z0"], o["z1"]), (9.5, 10.3))
        p.buildings[0].roof = model.Roof(type="gable", tilt=20.0)
        self.assertFalse(any(o["kind"] == "parapet" for o in p.obstacle_prisms()))

    def test_an_obstacle_on_a_pitch_follows_it(self):
        p = sample()
        b = p.buildings[0]
        b.roof = model.Roof(type="mono", eave_side=0, tilt=10.0)    # eave on the South side, rising North
        chimney = model.ExclusionItem(id="e9", ring=[[10, 10], [11, 10], [11, 11], [10, 11]], kind="chimney",
                                      building=b.id)
        p.exclusions.append(chimney)
        o = next(o for o in p.obstacle_prisms() if o["id"] == "e9")
        t = math.tan(math.radians(10.0))
        self.assertAlmostEqual(o["z0"], 9.5 + 10 * t, places=6)
        self.assertAlmostEqual(o["z1"], 9.5 + 11 * t + model.OBSTACLE_HEIGHTS["chimney"], places=6)

    def test_a_gable_roof_gives_the_sub_field_its_pitch(self):
        p = sample()
        b = p.buildings[0]
        b.roof = model.Roof(type="gable", tilt=20.0)
        sf = p.subfields[0]
        sf.pitch = 2                                       # the side of the eave: the North one (format 9)
        s = p.surface_of(sf)
        self.assertEqual((s.tilt, s.azimuth), (20.0, 180.0))
        sf.pitch = 1                                       # a gable end has no pitch: the first one
        self.assertEqual(p.surface_of(sf).azimuth, 0.0)
        self.assertEqual([b.pitch_ref(i) for i in range(2)], [0, 2])
        self.assertEqual((b.pitch_index(2), b.pitch_index(1), b.pitch_index(None)), (1, None, None))


class Touched(unittest.TestCase):
    """What a change touches, as FreeCAD's recompute (study 15, 3.6): a sub-field is laid out again only when
    something its layout reads has changed."""

    def setUp(self):
        self.p = sample()
        self.p.subfields.append(model.SubField(id=self.p.new_id("s"), name="Terra", ring=[[50, 0], [70, 0], [70, 10],
                                                                                         [50, 10]]))
        self.a, self.b = self.p.subfields

    def keys(self) -> tuple[str, str]:
        return self.p.layout_key(self.a), self.p.layout_key(self.b)

    def test_the_key_of_a_layout_changes_with_what_it_reads(self):
        key_a, key_b = self.keys()
        self.a.params["gap"] = 0.05                         # the sub-field itself
        self.assertNotEqual(self.p.layout_key(self.a), key_a)
        self.assertEqual(self.p.layout_key(self.b), key_b)  # another sub-field is not read
        key_a, key_b = self.keys()
        self.p.exclusions[0].clearance = 0.5                # an exclusion of the building a lies on
        self.assertNotEqual(self.p.layout_key(self.a), key_a)
        self.assertEqual(self.p.layout_key(self.b), key_b)  # b is on the ground, out of the shadows' rule
        key_a, key_b = self.keys()
        self.p.sun_window = {**self.p.sun_window, "start": 9.0}     # the design day
        self.assertNotEqual(self.p.layout_key(self.b), key_b)
        key_a, key_b = self.keys()
        self.p.economics = {"price": 1}                     # the economics are not read
        self.assertEqual(self.p.layout_key(self.b), key_b)

    def test_a_name_moves_nothing_and_a_height_only_what_sees_it(self):
        b = self.p.buildings[0]
        key_a, key_b = self.keys()
        b.name, b.fire.category = "Renamed", "C"            # neither is read by the layout
        self.assertEqual(self.keys(), (key_a, key_b))
        b.fire.subject = not b.fire.subject                 # the fire rules: the sub-fields of that building
        self.assertNotEqual(self.p.layout_key(self.a), key_a)
        self.assertEqual(self.p.layout_key(self.b), key_b)
        key_a, key_b = self.keys()
        b.height = 12.0                                     # its own sub-fields see it, the one on the ground not
        self.assertNotEqual(self.p.layout_key(self.a), key_a)
        self.assertEqual(self.p.layout_key(self.b), key_b)
        key_a, key_b = self.keys()
        self.b.params["shade_free"] = True                  # out of the shadows: every building counts
        key_b = self.p.layout_key(self.b)
        b.height = 14.0
        self.assertNotEqual(self.p.layout_key(self.b), key_b)
        key_b = self.p.layout_key(self.b)
        self.p.exclusions[0].height = 3.0                   # and every obstacle
        self.assertNotEqual(self.p.layout_key(self.b), key_b)
        key_b = self.p.layout_key(self.b)
        b.name = "Renamed again"
        self.assertEqual(self.p.layout_key(self.b), key_b)

    def test_the_geometry_key_of_a_building_is_its_shape_alone(self):
        b = self.p.buildings[0]
        key = b.geometry_key()
        b.name, b.fire.subject = "Other", True
        self.assertEqual(b.geometry_key(), key)
        for change in (lambda: setattr(b, "height", 11.0), lambda: setattr(b, "parapet", 0.5),
                       lambda: setattr(b.roof, "tilt", 5.0), lambda: b.footprint.append([20.0, 30.0])):
            change()
            self.assertNotEqual(b.geometry_key(), key)
            key = b.geometry_key()

    def test_the_state_of_a_layout_empty_stale_error_or_ok(self):
        self.assertEqual(self.p.layout_state(self.a, {}, {}), "empty")
        self.a.filled = True
        self.assertEqual(self.p.layout_state(self.a, {}, {}), "stale")
        keys = {self.a.id: self.p.layout_key(self.a)}
        self.assertEqual(self.p.layout_state(self.a, keys, {self.a.id: object()}), "ok")
        self.assertEqual(self.p.layout_state(self.a, keys, {self.a.id: ValueError("no room")}), "error")
        self.a.params["tilt"] = 20.0
        self.assertEqual(self.p.layout_state(self.a, keys, {self.a.id: object()}), "stale")


class Names(unittest.TestCase):
    def test_exclusions_are_numbered_within_their_kind(self):
        p = sample()
        p.exclusions.append(model.ExclusionItem(id="e9", ring=[[5, 5], [6, 5], [6, 6], [5, 6]], kind="vent"))
        self.assertEqual(list(p.exclusion_numbers().values()), [1, 1, 2])     # vent 1, plant 1, vent 2

    def test_a_copy_has_an_id_of_its_own_and_moves_aside(self):
        p = sample()
        sf = p.subfields[0]
        sf.filled, sf.removed = True, ["r1c1"]
        new = p.duplicate("subfield", sf.id)
        copy = next(s for s in p.subfields if s.id == new)
        self.assertNotEqual(new, sf.id)
        self.assertEqual(copy.ring[0], [2.0, 0.0])
        self.assertEqual((copy.filled, copy.removed, copy.params), (False, [], sf.params))
        self.assertIsNot(copy.params, sf.params)
        self.assertIn("(copy)", copy.name)
        b = p.duplicate("building", p.buildings[0].id, (50, 0))
        self.assertEqual(p.building(b).footprint[0], [50.0, 0.0])
        self.assertIsNot(p.building(b).roof, p.buildings[0].roof)
        e = p.duplicate("exclusion", p.exclusions[0].id)
        self.assertEqual(len({x.id for x in p.exclusions}), 3)
        self.assertTrue(e.startswith("e"))
        with self.assertRaises(ValueError):
            p.duplicate("subfield", "nothing")

    def test_a_copied_building_takes_its_hand_drawn_pitches_along(self):
        p = sample()
        b = p.buildings[0]
        b.roof.type = "free"
        b.roof.free_pitches = [{"ring": [[0, 0], [10, 0], [10, 5], [0, 5]], "eave_side": 0, "eave": 6.0, "tilt": 20.0}]
        new = p.building(p.duplicate("building", b.id, (50, 0)))
        self.assertEqual(new.roof.free_pitches[0]["ring"][0], [50.0, 0.0])
        self.assertEqual(b.roof.free_pitches[0]["ring"][0], [0, 0])               # the original stays
        self.assertAlmostEqual(new.pitches()[0].z(55, 3), b.pitches()[0].z(5, 3))

    def test_a_copied_sub_field_shares_nothing_of_its_parameters(self):
        p = sample()
        sf = p.subfields[0]
        sf.params["window"] = {"day": 21, "month": 12}
        new = p.duplicate("subfield", sf.id)
        copy = next(s for s in p.subfields if s.id == new)
        copy.params["window"]["day"] = 1
        self.assertEqual(sf.params["window"]["day"], 21)


def eighth(p: model.Project) -> dict:
    """A project as a file of format 8 held it: the roofs without their sides, ridge height and covering."""
    data = json.loads(json.dumps(p.to_json()))
    data["version"] = 8
    for b in data["buildings"]:
        for key in ("edges", "ridge_height", "covering"):
            b["roof"].pop(key)
    return data


def rectangles_8() -> dict:
    """Gable and hip roofs on rectangles, as format 8 had them, with sub-fields on each pitch: a gable on a
    rectangle turned by 30 degrees, a hip, a square gable with its ridge parallel to side 2."""
    p = model.Project(name="Tetti")
    p.site = model.Site(lat=45.5226, lon=9.03, address="Rho (MI)")
    turned = [[0.0, 0.0], [13.8564, 8.0], [9.3564, 15.7942], [-4.5, 7.7942]]
    p.buildings.append(model.Building(id="b1", name="Casa", footprint=turned, height=6.0,
                                      roof=model.Roof(type="gable", tilt=30.0)))
    p.buildings.append(model.Building(id="b2", name="Villa", footprint=[[30, 0], [50, 0], [50, 10], [30, 10]],
                                      height=7.0, roof=model.Roof(type="hip", tilt=25.0)))
    p.buildings.append(model.Building(id="b3", name="Torre", footprint=[[60, 0], [70, 0], [70, 10], [60, 10]],
                                      height=9.0, roof=model.Roof(type="gable", tilt=20.0, ridge_along=1)))
    subs = [("s1", "b1", 0, [[-4.09, 7.684], [9.247, 15.384], [11.197, 12.007], [-2.14, 4.307]]),
            ("s2", "b1", 1, [[-1.84, 3.787], [11.497, 11.487], [13.447, 8.11], [0.11, 0.41]]),
            ("s3", "b2", 0, [[31, 0.5], [49, 0.5], [45, 4.5], [35, 4.5]]),
            ("s4", "b2", 1, [[31, 9.5], [35, 5.5], [45, 5.5], [49, 9.5]]),
            ("s5", "b2", 2, [[49.5, 1], [49.5, 9], [45.5, 5]]),
            ("s6", "b2", 3, [[30.5, 1], [34.5, 5], [30.5, 9]]),
            ("s7", "b3", 0, [[60.5, 0.5], [64.5, 0.5], [64.5, 9.5], [60.5, 9.5]]),
            ("s8", "b3", 1, [[65.5, 0.5], [69.5, 0.5], [69.5, 9.5], [65.5, 9.5]])]
    for sid, bid, pitch, ring in subs:
        p.subfields.append(model.SubField(id=sid, name=sid, ring=ring, building=bid, pitch=pitch,
                                          params={"mounting": "coplanar", "portrait": bid != "b1"}, filled=True))
    return eighth(p)


class RoofsOnAnyOutline(unittest.TestCase):
    """Format 9 (task 16a): gable and hip roofs on any outline, sides as eaves or gable ends, sub-fields on the
    side of their eave."""

    # what format 8 laid on rectangles_8(), measured with its roofs.py on 24/10/2026: the azimuth of the pitch,
    # the modules and a digest of their keys and corners
    BEFORE = {"s1": (150.0, 6, "49fcff776ead"), "s2": (-30.0, 6, "4140a4e3b6fa"), "s3": (180.0, 8, "ecc7d1d255fe"),
              "s4": (-90.0, 9, "b2cf3c5579c8"), "s5": (0.0, 1, "ea6514a863df"), "s6": (90.0, 1, "e7e4e4b11d81"),
              "s7": (90.0, 6, "c802fa48c48e"), "s8": (-90.0, 6, "3066f632be47")}

    @staticmethod
    def digest(result) -> str:
        import hashlib

        def before_16c(key):                 # «f3:5» was «2:5» before the rows had ids (task 16c)
            row, _sep, rest = key.partition(":")
            return f"{int(row[1:]) - 1}:{rest}"
        keys = sorted(before_16c(m.key) for m in result.modules)
        corners = sorted(tuple(round(c, 6) for pt in m.corners for c in pt) for m in result.modules)
        return hashlib.sha1(json.dumps([keys, corners]).encode()).hexdigest()[:12]

    def load(self, data) -> tuple[model.Project, str | None]:
        d = Path(tempfile.mkdtemp())
        (d / "p.meridiana").write_text(json.dumps(data), encoding="utf-8")
        return model.Project.load(d / "p.meridiana")

    def test_the_house_with_a_gable_roof_lays_its_modules_flat_on_the_southern_pitch(self):
        from _fixtures import casa_a_falde
        p = casa_a_falde()
        b, sf = p.buildings[0], p.subfields[0]
        self.assertEqual([(q.side, q.tilt) for q in b.pitches()], [(0, 30.0), (2, 30.0)])   # eaves on the long sides
        s = p.surface_of(sf)
        self.assertEqual((s.tilt, s.azimuth), (30.0, 0.0))                     # the pitch of side 0 faces South
        r = p.fill(sf)
        self.assertGreater(r.count, 0)
        self.assertTrue(all(m.tilt == 30.0 for m in r.modules))                # coplanar: the slope of the roof
        self.assertTrue(all(0.0 < m.centre[1] < 4.0 for m in r.modules))      # all below the ridge at 4 m

    def test_a_file_on_rectangles_opens_without_notice_and_lays_the_same_modules(self):
        p, notice = self.load(rectangles_8())
        self.assertIsNone(notice)
        # the long sides of the turned rectangle are its eaves; the square's ridge runs parallel to side 2
        self.assertEqual([b.roof.edges for b in p.buildings], [["eave", "gable", "eave", "gable"], ["eave"] * 4,
                                                               ["gable", "eave", "gable", "eave"]])
        for sf in p.subfields:
            with self.subTest(sub_field=sf.id):
                azimuth, count, digest = self.BEFORE[sf.id]
                self.assertAlmostEqual(p.surface_of(sf).azimuth, azimuth, places=3)
                result = p.fill(sf)
                self.assertEqual((result.count, self.digest(result)), (count, digest))
        # the sub-fields now name the side of their eave: s3 was on the first pitch, which faced North
        self.assertEqual({sf.id: sf.pitch for sf in p.subfields},
                         {"s1": 2, "s2": 0, "s3": 2, "s4": 1, "s5": 0, "s6": 3, "s7": 3, "s8": 1})

    def test_a_file_with_an_l_opens_with_a_notice_and_its_sub_fields_on_the_pitches_under_them(self):
        p = model.Project(name="L")
        p.buildings.append(model.Building(id="b1", name="Edificio a L", footprint=[[0, 0], [20, 0], [20, 8], [8, 8],
                                                                                 [8, 18], [0, 18]],
                                          height=6.0, roof=model.Roof(type="gable", tilt=20.0)))
        # format 8 put two pitches on the rectangle 20 x 18: 0 to the North, 1 to the South
        for sid, pitch, ring in (("s1", 0, [[10, 1], [18, 1], [18, 3], [10, 3]]),     # the South of the long arm
                                 ("s2", 1, [[1, 12], [3, 12], [3, 16], [1, 16]]),    # the West of the other arm
                                 ("s3", 1, [[5, 10], [7, 10], [7, 16], [5, 16]]),    # its East
                                 ("s4", None, [[10, 5], [18, 5], [18, 7], [10, 7]])):  # the North of the long arm
            p.subfields.append(model.SubField(id=sid, name=sid, ring=ring, building="b1", pitch=pitch))
        data = eighth(p)
        self.assertEqual(model._old_azimuths(data["buildings"][0]["footprint"], data["buildings"][0]["roof"]),
                         [180.0, 0.0])
        q, notice = self.load(data)
        self.assertIn("Edificio a L", notice)
        self.assertEqual(q.buildings[0].roof.edges, ["eave", "gable", "eave", "eave", "gable", "eave"])
        self.assertEqual({sf.id: sf.pitch for sf in q.subfields}, {"s1": 0, "s2": 5, "s3": 3, "s4": 2})
        self.assertEqual([round(q.surface_of(sf).azimuth) for sf in q.subfields], [0, 90, -90, 180])

    def test_the_sides_of_a_roof_are_its_types_own_until_the_designer_says(self):
        b = model.Building(id="b1", name="L", footprint=[[0, 0], [20, 0], [20, 8], [8, 8], [8, 18], [0, 18]],
                           height=6.0, roof=model.Roof(type="gable", tilt=20.0))
        self.assertEqual(b.sides_kind(), ["eave", "gable", "eave", "eave", "gable", "eave"])
        self.assertEqual(len(b.pitches()), 4)
        b.roof.type = "hip"
        self.assertEqual(b.sides_kind(), ["eave"] * 6)
        self.assertEqual(len(b.pitches()), 6)
        b.roof.edges = ["eave", "gable", "eave", "eave", "eave", "eave"]
        self.assertEqual([pt.side for pt in b.pitches()], [0, 2, 3, 4, 5])
        b.footprint = b.footprint[:4] + b.footprint[5:]               # a corner less: the edges no longer fit
        self.assertEqual(b.sides_kind(), ["eave"] * 5)

    def test_a_roof_that_cannot_be_as_asked_says_why(self):
        b = model.Building(id="b1", name="B", footprint=[[8.866, -3.97], [8.866, 0.0], [0.0, 0.0], [0.0, 12.305],
                                                         [29.879, 12.305], [29.879, 0.0], [12.095, 0.0],
                                                         [12.095, -3.97]],
                           height=6.0, roof=model.Roof(type="gable", tilt=20.0,
                                                       edges=["gable", "eave", "gable", "gable", "eave", "eave",
                                                              "gable", "gable"]))
        self.assertEqual(b.roof_problem(), ("gables", [0, 6]))
        b.footprint = [[0, 0], [10, 10], [10, 0], [0, 10]]              # crossing itself: flat until put right
        b.roof.edges = []
        self.assertEqual(b.roof_problem(), ("outline", []))
        self.assertEqual([pt.tilt for pt in b.pitches()], [0.0])

    def test_the_new_keys_of_a_roof_are_checked(self):
        for key, value, words in (("edges", ["eave", "wall"], "roof.edges[1]"), ("ridge_height", "high", "ridge_height"),
                                  ("ridge_height", 1e9, "ridge_height"), ("covering", "straw", "roof.covering")):
            with self.subTest(key=key, value=value):
                data = json.loads(json.dumps(sample().to_json()))
                data["buildings"][0]["roof"][key] = value
                with self.assertRaises(ValueError) as caught:
                    model.Project.from_json(data)
                self.assertIn(words, str(caught.exception))


class Typed(unittest.TestCase):
    """The settings of the energy side have a schema (settings.py): a key the program does not know is said,
    a value of the wrong type refused with its path."""

    def test_unknown_keys_of_the_settings_are_said_with_their_path(self):
        p = sample()
        p.energy = {"losses": {"soiling": 3.0, "soilng": 4.0}, "dc_ac_ratio": 1.2, "invertor": {}}
        p.economics = {"capex_per_kwp": 1200.0, "capex": 5}
        p.consumption = {"annual_kwh": 1000.0, "yearly_kwh": 2000.0}
        unknown: list = []
        q = model.Project.from_json(json.loads(json.dumps(p.to_json())), unknown=unknown)
        self.assertEqual(sorted(unknown), ["consumption.yearly_kwh", "variants[0].design.economics.capex",
                                           "variants[0].design.energy.invertor",
                                           "variants[0].design.energy.losses.soilng"])
        self.assertEqual(q.energy["losses"]["soiling"], 3.0)      # the dictionaries stay as they are, known keys and all

    def test_a_setting_of_the_wrong_type_is_refused_with_its_path(self):
        for section, data, words in (("energy", {"losses": {"soiling": "two"}}, "energy.losses.soiling"),
                                     ("energy", {"inverters": [{"record": {}, "count": 1.5}]},
                                      "energy.inverters[0].count"),
                                     ("energy", {"strings": {"per_mppt": 3}}, "energy.strings.per_mppt"),
                                     ("economics", {"community": "yes"}, "economics.community"),
                                     ("consumption", {"pod": 12}, "consumption.pod"),
                                     ("economics", {"battery": []}, "economics.battery")):
            with self.subTest(section=section, data=data):
                p = sample()
                setattr(p, section, data)
                with self.assertRaises(ValueError) as caught:
                    model.Project.from_json(json.loads(json.dumps(p.to_json())))
                self.assertIn(words, str(caught.exception))

    def test_a_null_lid_and_a_null_t_min_are_the_defaults(self):
        p = sample()
        p.energy = {"losses": {"lid": None}, "t_min": None}
        model.Project.from_json(json.loads(json.dumps(p.to_json())))


class Pitches(unittest.TestCase):
    def test_the_pitches_are_kept_until_the_geometry_changes(self):
        p = sample()
        b = p.buildings[0]
        first = b.pitches()
        self.assertIs(b.pitches(), first)
        b.name = "Other"
        self.assertIs(b.pitches(), first)
        b.height = 12.0
        again = b.pitches()
        self.assertIsNot(again, first)
        self.assertEqual(again[0].z0, 12.0)
        self.assertNotIn("_pitches", asdict(b))             # never in the file
        self.assertEqual(b, dataclasses.replace(b))         # never compared

    def test_a_free_pitch_drawn_today_has_its_id_checked(self):
        p = sample()
        p.buildings[0].roof = model.Roof(type="free", free_pitches=[
            {"id": "p1", "ring": [[0, 0], [10, 0], [10, 5], [0, 5]], "eave_side": 0, "eave": 6.0, "tilt": 20.0}])
        model.Project.from_json(json.loads(json.dumps(p.to_json())))
        p.buildings[0].roof.free_pitches[0]["id"] = 3
        with self.assertRaises(ValueError) as caught:
            model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertIn("free_pitches[0].id", str(caught.exception))


class Imports(unittest.TestCase):
    def test_the_model_does_not_load_the_energy_side(self):
        """`model` imported on its own, in a fresh interpreter: no pandas, no pvlib, no energy (A 7.12): the
        shadows for a sub-field out of them come from the caller (energy.system.shadow_exclusions)."""
        import subprocess
        import sys
        code = ("import sys; sys.path.insert(0, r'" + str(_setup.ROOT / "src") + "'); import meridiana.model; "
                "print(sorted(m for m in sys.modules if m.startswith('meridiana.energy') or m in ('pandas', 'pvlib')))")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(), "[]")

    def test_a_sub_field_out_of_the_shadows_needs_the_shadow_function(self):
        p = sample()
        sf = p.subfields[0]
        sf.params["shade_free"] = True
        with self.assertRaises(ValueError) as caught:
            p.fill(sf)
        self.assertIn("shadow function", str(caught.exception))
        from meridiana.energy import system
        self.assertGreater(p.fill(sf, shade=system.shadow_exclusions).count, 0)


class RowsByHand(unittest.TestCase):
    """Format 10 (task 16c, step 1): a sub-field keeps its rows by hand, the modules have ids."""

    def by_hand(self) -> tuple[model.Project, model.SubField]:
        p = sample()
        sf = p.subfields[0]
        sf.filled = True
        auto = p.fill(sf)
        sf.rows, sf.manual = [r.as_dict() for r in auto.rows if r.places], True
        return p, sf

    def test_a_sub_field_by_hand_keeps_its_modules_when_the_pitch_changes(self):
        p, sf = self.by_hand()
        before = p.fill(sf)
        self.assertTrue(before.manual)
        sf.params["pitch_mode"], sf.params["pitch"] = "value", 12.0
        after = p.fill(sf)
        self.assertEqual([m.key for m in after.modules], [m.key for m in before.modules])
        self.assertEqual([m.centre for m in after.modules], [m.centre for m in before.modules])
        sf.manual = False                                       # automatic again: the new pitch lays fewer rows
        self.assertLess(p.fill(sf).count, before.count)

    def test_the_rows_are_in_the_key_of_the_layout_and_come_back_from_the_file(self):
        p, sf = self.by_hand()
        key = p.layout_key(sf)
        sf.rows[0]["x"] += 0.1
        self.assertNotEqual(p.layout_key(sf), key)
        q = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual((q.subfields[0].rows, q.subfields[0].manual), (sf.rows, True))
        # by hand the shadows are a check, not a layout: no shadow function is needed
        sf.params["shade_free"] = True
        self.assertGreater(p.fill(sf).count, 0)

    def test_an_old_file_has_no_rows_and_lays_as_before_with_the_ids_of_the_same_modules(self):
        folder = _setup.FORMATS
        nine = json.loads((folder / "progetto-v9.meridiana").read_text(encoding="utf-8"))
        design = nine["variants"][0]["design"]
        design["subfields"][0]["filled"] = True
        design["subfields"][0]["removed"] = ["0:1", "1:3:1"]
        p = model.Project.from_json(json.loads(json.dumps(nine)))
        sf = p.subfields[0]
        self.assertEqual((sf.rows, sf.manual), ([], False))
        self.assertEqual(sf.removed, ["f1:1", "f2:3:1"])
        self.assertEqual(p.energy["strings"]["runs"][0]["modules"], ["s1/f1:0", "s1/f1:1", "s1/f1:2"])
        full = p.fill(model.SubField(**{**asdict(sf), "removed": []}))
        laid = p.fill(sf)
        self.assertEqual(laid.count, full.count - 2)
        # the modules taken out are those that were the second of the first row and the upper one of the fourth of
        # the second row
        gone = {m.key for m in full.modules} - {m.key for m in laid.modules}
        self.assertEqual(gone, {"f1:1", "f2:3:1"})
        self.assertEqual([m.slot for m in full.modules if m.rid == "f1" and m.level == 0][:3], [0, 1, 2])

    def test_keys_that_are_not_a_row_and_a_place_are_left_out_and_said(self):
        folder = _setup.FORMATS
        nine = json.loads((folder / "progetto-v9.meridiana").read_text(encoding="utf-8"))
        nine["variants"][0]["design"]["subfields"][0]["removed"] = ["0:1", "r2c3"]
        nine["variants"][0]["design"]["energy"]["strings"]["runs"][0]["modules"].append("s1/top")
        notes: list = []
        p = model.Project.from_json(nine, notes=notes)
        self.assertEqual(p.subfields[0].removed, ["f1:1"])
        self.assertEqual(len(p.energy["strings"]["runs"][0]["modules"]), 3)
        self.assertEqual(len(notes), 1)
        self.assertIn("2 keys", notes[0])

    def test_the_tenth_format_opens_with_its_rows_by_hand(self):
        folder = _setup.FORMATS
        p, notice = model.Project.load(folder / "progetto-v10.meridiana")
        self.assertIsNone(notice)
        sf = p.subfields[0]
        self.assertTrue(sf.manual)
        self.assertEqual([r["id"] for r in sf.rows], ["f1", "f90", "f91"])
        r = p.fill(sf)
        self.assertTrue(r.manual)
        self.assertNotIn("f1:1", r.keys)                                      # taken out by hand
        self.assertIn("f2:1", r.keys)                                         # exploded, with the key it had
        self.assertTrue(next(m for m in r.modules if m.key == "f2:1").turned)
        self.assertEqual(p.energy["strings"]["runs"][0]["modules"], ["s1/f1:0", "s1/f1:2", "s1/f2:0"])

    def test_rows_that_are_not_rows_are_refused_with_their_path(self):
        p, sf = self.by_hand()
        for bad, where in (({"id": 3}, "rows[0].id"), ({"x": "a"}, "rows[0].x"), ({"places": [1, None]}, "places[1]"),
                           ({"keys": [1]}, "rows[0].keys"), ({"turned": 1}, "rows[0].turned")):
            data = p.to_json()
            data["variants"][0]["design"]["subfields"][0]["rows"][0].update(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError) as caught:
                model.Project.from_json(json.loads(json.dumps(data)))
            self.assertIn(where, str(caught.exception))
        data = p.to_json()
        rows = data["variants"][0]["design"]["subfields"][0]["rows"]
        rows[1]["id"] = rows[0]["id"]
        with self.assertRaises(ValueError) as caught:
            model.Project.from_json(json.loads(json.dumps(data)))
        self.assertIn("used twice", str(caught.exception))

    def test_a_copy_of_a_sub_field_has_no_rows_of_its_own(self):
        p, sf = self.by_hand()
        made = p.duplicate("subfield", sf.id)
        copy = next(s for s in p.subfields if s.id == made)
        self.assertEqual((copy.rows, copy.manual, copy.filled), ([], False, False))


if __name__ == "__main__":
    unittest.main()
