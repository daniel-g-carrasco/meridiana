"""What an import made, read back from the project (R604, R605): one model for the bodies that came in together, the
bodies worth a row and the others, and the short names of the planes the import created."""
import unittest

from meridiana.core.model import imported, model

FILE = "I:/jobs/a long folder/another/Town hall.ifc"


def square(x: float, side: float) -> list:
    return [[x, 0.0], [x + side, 0.0], [x + side, side], [x, side]]


def body(p: model.Project, name: str, side: float, group: str = "ifc1", **more) -> model.Building:
    b = model.Building(id=p.new_id("b"), name=name, footprint=square(40.0 * len(p.buildings), side), group=group, **more)
    p.buildings.append(b)
    return b


def plane(p: model.Project, building: str | None, elements: str = "#12", file: str = FILE) -> model.SubField:
    sf = model.SubField(id=p.new_id("s"), name=f"{file}: {elements}", ring=square(0.0, 3.0), building=building,
                        support=model.SupportPlane(enabled=True))
    p.subfields.append(sf)
    return sf


def town_hall() -> model.Project:
    """One import of six bodies: the main roof with planes, a large roof without, four small ones; and a building
    drawn by hand."""
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=square(-100.0, 20.0)))
    main = body(p, "Town hall", 30.0)
    body(p, "Town hall 2", 12.0)                # 144 m2, no sub-field: a roof worth laying
    for n in range(3, 7):
        body(p, f"Town hall {n}", 4.0)          # 16 m2 each
    for _n in range(3):
        plane(p, main.id, "#40, #41")           # the same element gives three planes: the same saved name
    p.resources = {"ifc_reference": {"file": FILE, "anchor": {"building": main.id, "footprint": main.footprint}}}
    return p


class Models(unittest.TestCase):
    def test_the_bodies_of_one_import_are_one_model_named_as_they_are(self):
        p = town_hall()
        found = imported.models(p)
        self.assertEqual(len(found), 1)
        m = found[0]
        self.assertEqual((m.key, m.name, m.file), ("ifc1", "Town hall", FILE))
        self.assertEqual(len(m.bodies), 6)
        self.assertEqual([p.building(i).name for i in m.shown], ["Town hall", "Town hall 2"])
        self.assertEqual([p.building(i).name for i in m.others], [f"Town hall {n}" for n in range(3, 7)])
        self.assertIsNone(imported.model_of(p, "b1"))
        self.assertEqual(imported.model_of(p, m.bodies[3]).key, "ifc1")

    def test_a_body_imported_alone_or_left_alone_is_a_building_as_any_other(self):
        p = model.Project(name="Prova")
        body(p, "House", 10.0, group="")
        body(p, "Left", 10.0, group="ifc3")
        self.assertEqual(imported.models(p), [])

    def test_one_small_body_is_not_gathered_and_without_a_main_one_all_are_shown(self):
        p = town_hall()
        p.buildings = p.buildings[:4]           # the shed, the main roof, the large one, one small
        m = imported.models(p)[0]
        self.assertEqual((len(m.shown), m.others), (3, ()))
        q = model.Project(name="Prova")
        for n in range(5):
            body(q, f"Skid {n + 2}", 3.0)
        m = imported.models(q)[0]
        self.assertEqual((len(m.shown), m.others), (5, ()))

    def test_a_part_with_a_sub_field_makes_its_body_worth_a_row(self):
        p = town_hall()
        small = p.buildings[3]
        part = body(p, "Town hall 7", 2.0, part_of=small.id)
        plane(p, part.id).name = "Canopy"                   # a sub-field of the designer's
        m = imported.models(p)[0]
        self.assertIn(small.id, m.shown)
        self.assertNotIn(part.id, m.shown + m.others)       # a part is listed under its body, not in the node
        self.assertIn(part.id, m.bodies)

    def test_the_name_falls_back_to_the_file_then_to_a_plain_one(self):
        p = town_hall()
        p.buildings[2].name = "Tower"           # the bodies no longer share a name: the file's, without folders
        self.assertEqual(imported.models(p)[0].name, "Town hall")
        p.resources["ifc_reference"]["file"] = "C:\\models\\Site A.IFC"
        self.assertEqual(imported.models(p)[0].name, "Site A")
        p.resources = {}
        self.assertEqual(imported.models(p)[0].name, "Imported model")
        for b in p.buildings[1:]:
            b.group = "ifc2"
        self.assertEqual(imported.models(p)[0].name, "Imported model 2")

    def test_bodies_numbered_from_one_have_no_name_of_their_own(self):
        self.assertEqual(imported.shared_name(["Body 1", "Body 2", "Body 3"]), "")
        self.assertEqual(imported.shared_name(["Hall", "Hall 2", "Hall 10"]), "Hall")
        self.assertEqual(imported.shared_name(["Hall", "Annex"]), "")
        self.assertEqual(imported.shared_name([]), "")


class PlaneNames(unittest.TestCase):
    def test_the_planes_of_an_import_are_short_and_different(self):
        p = town_hall()
        names = imported.namer(p)
        full = [names.subfield(sf) for sf in p.subfields]
        self.assertEqual(full, ["Town hall · surface 1", "Town hall · surface 2", "Town hall · surface 3"])
        self.assertEqual(names.subfield(p.subfields[1], short=True), "Surface 2")
        self.assertEqual(len({sf.name for sf in p.subfields}), 1)       # as saved they read the same
        for sf in p.subfields:
            self.assertNotIn("/", names.subfield(sf))
        self.assertEqual(names.source(p.subfields[0]), f"From {FILE}, IFC #40, #41")
        self.assertEqual(imported.subfield_name(p, p.subfields[2]), "Town hall · surface 3")

    def test_a_name_of_the_designer_is_shown_as_it_is(self):
        p = town_hall()
        p.subfields[1].name = "South shed"
        p.subfields.append(model.SubField(id="s9", name="Notes: #3", ring=square(0.0, 2.0)))
        names = imported.namer(p)
        self.assertEqual([names.subfield(sf) for sf in p.subfields],
                         ["Town hall · surface 1", "South shed", "Town hall · surface 3", "Notes: #3"])
        self.assertEqual(names.source(p.subfields[1]), "")      # the plane renamed keeps its place: the others their numbers

    def test_the_number_stays_when_the_import_listed_what_it_made(self):
        p = town_hall()
        p.resources["ifc_reference"]["derived"] = {"exclusions": [], "supports": [sf.id for sf in p.subfields]}
        gone, kept = p.subfields[0], p.subfields[2]
        p.subfields.remove(gone)
        p.subfields[0].name = "South shed"
        self.assertEqual(imported.namer(p).subfield(kept), "Town hall · surface 3")

    def test_a_single_body_and_a_plane_on_the_ground(self):
        p = model.Project(name="Prova")
        house = body(p, "House", 10.0, group="")
        on_roof, loose = plane(p, house.id), plane(p, None, elements="#7")
        names = imported.namer(p)
        self.assertEqual(names.subfield(on_roof), "House · surface 1")
        self.assertEqual(names.subfield(loose), "Town hall · surface 1")

    def test_a_copy_and_a_part_of_a_split_keep_what_the_program_added(self):
        p = town_hall()
        p.subfields[0].name += ", pitch 2"
        p.subfields.append(model.SubField(id="s8", name=f"{FILE}: #40, #41 (copy)", ring=square(0.0, 2.0),
                                          building=p.subfields[0].building))
        names = imported.namer(p)
        self.assertEqual(names.subfield(p.subfields[0]), "Town hall · surface 1, pitch 2")
        self.assertEqual(names.subfield(p.subfields[-1], short=True), "Surface 4 (copy)")
        cut = model.SubField(id="gone", name=f"{FILE}: #9", ring=square(0.0, 2.0))
        self.assertEqual(names.subfield(cut), "Town hall")

    def test_what_the_import_saves_is_read_back(self):
        self.assertEqual(imported.source_of(f"{FILE}: #12"), (FILE, "#12"))
        self.assertEqual(imported.source_of(f"{FILE}: #12, #40"), (FILE, "#12, #40"))
        self.assertEqual(imported.source_of(f"{FILE}: {FILE}"), (FILE, ""))
        for other in ("Sub-field 3", "Roof: south", "notes.txt: #4", ""):
            self.assertEqual(imported.source_of(other), ("", ""))
        self.assertEqual(imported.file_stem(FILE), "Town hall")
        self.assertEqual(imported.file_stem("C:\\a\\b\\Model.v2.ifcZIP"), "Model.v2")


class WhichBodiesAreShown(unittest.TestCase):
    """The rule of 14/11/2026 (study 49, chapter 10): a body holding a sub-field of the designer's, or one on whose
    roof at least ROOF_LEAST modules of the project fit; the planes the import offered and nobody touched do not
    count."""

    def shown(self, p):
        return [p.building(i).name for i in imported.models(p)[0].shown]

    def test_a_plane_the_import_offered_does_not_keep_a_small_body_in_view(self):
        p = town_hall()
        small = p.buildings[3]
        sf = plane(p, small.id)
        self.assertNotIn("Town hall 3", self.shown(p))
        sf.filled = True                                    # laid: the designer's
        self.assertIn("Town hall 3", self.shown(p))
        sf.filled, sf.name = False, "Lantern"               # renamed: the designer's
        self.assertIn("Town hall 3", self.shown(p))

    def test_what_fits_follows_the_module_the_band_and_the_obstacles(self):
        p = town_hall()
        large = p.buildings[2]                              # 12 x 12 m: about 28 modules of 450 W
        fit = imported.fitting(p, p.buildings)
        self.assertEqual(fit[large.id], int(11.0 * 11.0 * imported.FIT_SHARE / (2.278 * 1.134)))      # 28
        self.assertTrue(all(fit[b.id] < imported.ROOF_LEAST for b in p.buildings[3:]))     # 4 x 4 m
        # a module of the project five times larger: it no longer fits seven times
        p.modules["big"] = {**p.modules["generic-450"], "length": 5.0, "width": 2.6}
        p.layout_defaults = {"module": "big"}
        self.assertLess(imported.fitting(p, p.buildings)[large.id], imported.ROOF_LEAST)
        self.assertNotIn("Town hall 2", self.shown(p))
        p.layout_defaults = {}
        # obstacles over most of it
        p.exclusions.append(model.ExclusionItem(id="e1", ring=square(40.0 * 2, 11.0), kind="plant", building=large.id))
        self.assertNotIn("Town hall 2", self.shown(p))

    def test_a_large_strip_narrower_than_a_module_is_not_worth_a_row(self):
        p = town_hall()
        strip = p.buildings[2]
        strip.footprint = [[0.0, 50.0], [120.0, 50.0], [120.0, 51.9], [0.0, 51.9]]     # 228 m2, 1,9 m wide
        self.assertEqual(imported.fitting(p, [strip])[strip.id], 0)
        self.assertNotIn("Town hall 2", self.shown(p))

    def test_the_room_is_kept_until_the_outline_changes(self):
        p = town_hall()
        large = p.buildings[2]
        first = imported.fitting(p, [large])[large.id]
        large.footprint = [[q[0], q[1] * 2] for q in large.footprint]       # 12 x 24 m now
        self.assertGreater(imported.fitting(p, [large])[large.id], first)


if __name__ == "__main__":
    unittest.main()
