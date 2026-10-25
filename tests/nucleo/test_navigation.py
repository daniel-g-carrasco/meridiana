"""The navigation styles (study 15, table 2.2) and the one state machine for the plan and the 3D view: for each
style, which gesture pans, orbits and zooms, what a click and a double click do."""

import unittest

import _setup  # noqa: F401

from meridiana import navigation as nav


def drag(n: nav.Navigator, buttons: str, mods: str = "") -> list[str]:
    """Press the buttons in order, move 20 px, release them: what the moves did. (Letting one button of a chord
    go first goes back to what the other does, as in FreeCAD: no move happens there here.)"""
    m = set(mods.split())
    out = []
    for b in buttons.split():
        out += n.press(b, m, 100, 100)
    for step in range(1, 5):
        out += n.move(100 + 5 * step, 100, m)
    for b in reversed(buttons.split()):
        out += n.release(b, m, 120, 100)
    kinds = {a.kind for a in out if a.phase == "move"}
    assert len(kinds) <= 1, out
    return kinds.pop() if kinds else ""


def click(n: nav.Navigator, button: str, mods: str = "") -> list[str]:
    m = set(mods.split())
    out = n.press(button, m, 50, 50) + n.move(51, 51, m) + n.release(button, m, 51, 51)
    return [a.kind for a in out]


# style: (gesture, mods) -> what the drag does; from table 2.2 of study 15 and 12a, 2.6
TABLE = {
    "autocad": [("middle", "", "pan"), ("left right", "", "pan"), ("middle", "shift", "orbit"),
                ("middle right", "", "orbit"), ("right", "", "orbit"), ("middle", "ctrl", "zoom")],
    "cad": [("middle", "", "pan"), ("right", "ctrl", "pan"), ("middle left", "", "orbit"), ("middle right", "", "orbit"),
            ("right", "shift", "orbit"), ("right", "ctrl shift", "zoom")],
    "revit": [("middle", "", "pan"), ("left right", "", "pan"), ("middle", "shift", "orbit"),
              ("middle right", "", "orbit"), ("middle", "ctrl", "zoom"), ("right", "ctrl shift", "zoom")],
    "blender": [("middle", "shift", "pan"), ("left right", "", "pan"), ("middle", "", "orbit"),
                ("middle", "ctrl", "zoom")],
    "solidworks": [("middle", "ctrl", "pan"), ("middle", "", "orbit"), ("middle", "shift", "zoom")],
    "nx": [("middle", "shift", "pan"), ("middle right", "", "pan"), ("middle", "", "orbit"), ("middle left", "", "zoom")],
    "openinventor": [("middle", "", "pan"), ("left", "ctrl shift", "pan"), ("left", "", "orbit"),
                     ("left middle", "", "zoom"), ("middle", "ctrl", "zoom")],
    "opencascade": [("middle", "", "pan"), ("middle", "ctrl", "pan"), ("right", "ctrl", "orbit"),
                    ("middle right", "", "orbit"), ("left", "ctrl", "zoom")],
    "openscad": [("right", "", "pan"), ("left", "", "orbit"), ("middle", "", "zoom"), ("right", "shift", "zoom")],
    "tinkercad": [("middle", "", "pan"), ("right", "", "orbit")],
    "touchpad": [("left", "shift", "orbit")],
    "gesture": [("right", "", "pan"), ("left", "", "orbit"), ("left", "alt", "orbit")],
    "maya": [("middle", "alt", "pan"), ("left", "alt", "orbit"), ("right", "alt", "zoom")],
    "sketchup": [("middle", "shift", "pan"), ("middle left", "", "pan"), ("middle", "", "orbit")],
}


class Styles(unittest.TestCase):
    def test_every_style_of_the_table_moves_the_view_as_it_should(self):
        self.assertEqual(set(TABLE), set(nav.STYLES))
        for key, rows in TABLE.items():
            for buttons, mods, kind in rows:
                with self.subTest(style=key, gesture=buttons, mods=mods):
                    n = nav.Navigator()
                    n.set_style(key)
                    self.assertEqual(drag(n, buttons, mods), kind)

    def test_a_gesture_of_another_style_does_nothing(self):
        n = nav.Navigator()
        n.set_style("cad")
        self.assertEqual(drag(n, "middle", "shift"), "")        # Revit's orbit is nothing in CAD
        n.set_style("revit")
        self.assertEqual(drag(n, "middle left"), "")

    def test_autocad_is_revit_with_the_double_middle_click_that_fits(self):
        n = nav.Navigator()
        self.assertEqual(n.style.name, "AutoCAD")               # the provisional default
        self.assertEqual([a.kind for a in n.double("middle", set(), 5, 5)], ["fit"])
        n.set_style("revit")
        self.assertEqual(n.double("middle", set(), 5, 5), [])   # FreeCAD's Revit has no fit there
        n.set_style("unknown")
        self.assertEqual(n.style.name, "AutoCAD")

    def test_a_real_double_click_is_one_click_and_a_double_not_two_clicks(self):
        n = nav.Navigator()                                 # what Qt sends: press, release, press, double, release
        kinds = [a.kind for a in n.press("middle", set(), 5, 5) + n.release("middle", set(), 5, 5)
                 + n.press("middle", set(), 5, 5) + n.double("middle", set(), 5, 5)
                 + n.release("middle", set(), 5, 5)]
        self.assertEqual(kinds, ["recentre", "fit"])        # the last recentre stopped the fit
        self.assertEqual([a.kind for a in n.press("middle", set(), 9, 9) + n.release("middle", set(), 9, 9)],
                         ["recentre"])                      # the next click is a click again
        n.set_style("revit")                                # no double there: both clicks count
        kinds = [a.kind for a in n.press("middle", set(), 5, 5) + n.release("middle", set(), 5, 5)
                 + n.press("middle", set(), 5, 5) + n.double("middle", set(), 5, 5)
                 + n.release("middle", set(), 5, 5)]
        self.assertEqual(kinds, ["recentre", "recentre"])

    def test_the_drag_begins_moves_and_ends(self):
        n = nav.Navigator()
        out = n.press("middle", set(), 0, 0) + n.move(10, 0) + n.move(15, 5) + n.release("middle", set(), 15, 5)
        self.assertEqual([(a.kind, a.phase) for a in out], [("pan", "begin"), ("pan", "move"), ("pan", "move"),
                                                            ("pan", "end")])
        self.assertEqual([(a.dx, a.dy) for a in out if a.phase == "move"], [(10, 0), (5, 5)])

    def test_shift_pressed_while_panning_turns_it_into_an_orbit(self):
        n = nav.Navigator()                                     # AutoCAD
        out = n.press("middle", set(), 0, 0) + n.move(10, 0) + n.move(20, 0, {"shift"}) + n.release("middle", {"shift"}, 20, 0)
        self.assertEqual([(a.kind, a.phase) for a in out], [("pan", "begin"), ("pan", "move"), ("pan", "end"),
                                                            ("orbit", "begin"), ("orbit", "move"), ("orbit", "end")])

    def test_letting_the_left_go_first_ends_a_pan_with_both_buttons_without_an_orbit(self):
        n = nav.Navigator()                                     # AutoCAD: left + right pans, right alone orbits
        out = n.press("left", set(), 0, 0) + n.press("right", set(), 0, 0) + n.move(10, 0) + n.move(20, 0)
        out += n.release("left", set(), 20, 0) + n.move(30, 0) + n.move(40, 0) + n.release("right", set(), 40, 0)
        self.assertEqual([(a.kind, a.phase) for a in out],
                         [("pan", "begin"), ("pan", "move"), ("pan", "move"), ("pan", "end")])
        self.assertEqual(click(n, "right"), ["menu"])           # the next gesture is free again

    def test_letting_a_button_go_goes_back_to_the_gesture_before_the_chord(self):
        n = nav.Navigator()
        n.set_style("cad")                                      # middle pans; adding the left one orbits
        out = n.press("middle", set(), 0, 0) + n.move(10, 0) + n.press("left", set(), 10, 0) + n.move(20, 0)
        out += n.release("left", set(), 20, 0) + n.move(30, 0) + n.release("middle", set(), 30, 0)
        self.assertEqual([(a.kind, a.phase) for a in out],
                         [("pan", "begin"), ("pan", "move"), ("pan", "end"), ("orbit", "begin"), ("orbit", "move"),
                          ("orbit", "end"), ("pan", "begin"), ("pan", "move"), ("pan", "end")])

    def test_which_styles_make_a_gesture_of_the_left_button_with_another(self):
        n = nav.Navigator()
        self.assertTrue(n.chorded("left"))                      # AutoCAD: left + right pans
        n.set_style("solidworks")
        self.assertFalse(n.chorded("left"))
        n.set_style("cad")
        self.assertTrue(n.chorded("left") and n.chorded("middle"))


class Clicks(unittest.TestCase):
    def test_a_short_press_is_a_click_not_a_drag(self):
        n = nav.Navigator()
        self.assertEqual(click(n, "left"), ["select"])
        self.assertEqual(click(n, "middle"), ["recentre"])      # FreeCAD's lookAtPoint
        self.assertEqual(click(n, "right"), ["menu"])           # the right button dragged orbits, held still a menu
        self.assertEqual([a.mods for a in n.press("left", {"ctrl"}, 0, 0) + n.release("left", {"ctrl"}, 0, 0)],
                         [frozenset({"ctrl"})])                 # Ctrl adds to the selection

    def test_styles_without_a_middle_click(self):
        n = nav.Navigator()
        for key in ("opencascade", "openscad", "tinkercad", "sketchup"):
            n.set_style(key)
            self.assertEqual(click(n, "middle"), [], key)

    def test_openinventor_selects_with_ctrl_or_shift(self):
        n = nav.Navigator()
        n.set_style("openinventor")
        self.assertEqual(click(n, "left"), [])
        self.assertEqual(click(n, "left", "shift"), ["select"])

    def test_the_wheel_zooms_towards_the_cursor_in_every_style(self):
        for key in nav.STYLES:
            n = nav.Navigator()
            n.set_style(key)
            (a,) = n.wheel(1.0, set(), 30, 40)
            self.assertEqual((a.kind, a.x, a.y, a.dy), ("wheel", 30, 40, 1.0))


class Touchpad(unittest.TestCase):
    def test_shift_and_moving_pans_without_a_button(self):
        n = nav.Navigator()
        n.set_style("touchpad")
        out = n.move(0, 0, {"shift"}) + n.move(5, 0, {"shift"}) + n.move(5, 0, set())
        self.assertEqual([(a.kind, a.phase) for a in out], [("pan", "begin"), ("pan", "move"), ("pan", "move"),
                                                            ("pan", "end")])
        n.set_style("autocad")
        self.assertEqual(n.move(0, 0, {"shift"}) + n.move(5, 0, {"shift"}), [])


class OrbitKeys(unittest.TestCase):
    """The key that makes the next press an orbit, read from the style's table: with it held the 3D view shows where
    the orbit would turn (study 16, G2). A gesture of keys alone orbits at once and has nothing to wait for."""

    SHIFT, CTRL, ALT = frozenset({"shift"}), frozenset({"ctrl"}), frozenset({"alt"})

    def test_which_styles_have_a_key_for_the_orbit(self):
        keys = {k: nav.orbit_keys(s) for k, s in nav.STYLES.items()}
        self.assertEqual(keys["autocad"], (self.SHIFT,))                      # Shift + middle
        self.assertEqual(keys["cad"], (self.SHIFT,))                          # Shift + right (Ctrl + right pans)
        self.assertEqual(keys["revit"], (self.SHIFT,))
        self.assertEqual(keys["opencascade"], (self.CTRL,))                   # Ctrl + right
        self.assertEqual(keys["touchpad"], (self.SHIFT,))                     # Shift + left; Alt alone orbits at once
        self.assertEqual(keys["gesture"], (self.ALT,))
        self.assertEqual(keys["maya"], (self.ALT,))
        for key in ("blender", "solidworks", "nx", "openinventor", "openscad", "tinkercad", "sketchup"):
            self.assertEqual(keys[key], (), key)                              # a button alone orbits: no key to hold

    def test_the_keys_in_words_for_the_preferences(self):
        self.assertEqual(nav.orbit_key_text("autocad"), "Shift")
        self.assertEqual(nav.orbit_key_text("opencascade"), "Ctrl")
        self.assertEqual(nav.orbit_key_text("blender"), "")
        self.assertEqual(nav.orbit_key_text("unknown"), "Shift")              # the default style, as everywhere

    def test_only_exactly_the_key_of_the_style_previews_the_orbit(self):
        n = nav.Navigator()
        self.assertTrue(n.previews_orbit({"shift"}))                          # AutoCAD, the default
        self.assertFalse(n.previews_orbit(set()))
        self.assertFalse(n.previews_orbit({"ctrl"}))
        self.assertFalse(n.previews_orbit({"shift", "ctrl"}))                 # that is the zoom
        self.assertFalse(n.previews_orbit({"shift", "alt"}))
        n.set_style("cad")
        self.assertTrue(n.previews_orbit({"shift"}))
        n.set_style("opencascade")
        self.assertTrue(n.previews_orbit({"ctrl"}))
        self.assertFalse(n.previews_orbit({"shift"}))
        n.set_style("blender")
        self.assertFalse(n.previews_orbit({"shift"}))                         # Shift + middle pans there

    def test_not_while_a_button_is_held_or_a_drag_goes_on(self):
        n = nav.Navigator()
        n.press("middle", {"shift"}, 100, 100)
        self.assertFalse(n.previews_orbit({"shift"}))                         # the press is on
        n.move(120, 100, {"shift"})
        n.release("middle", {"shift"}, 120, 100)
        self.assertTrue(n.previews_orbit({"shift"}))                          # and over: the key is still down
        n.set_style("touchpad")
        n.move(0, 0, {"shift"})                                               # Shift and moving pans there
        self.assertFalse(n.previews_orbit({"shift"}))

    def test_a_click_with_the_key_held_is_not_an_orbit_but_leaves_the_preview_possible(self):
        n = nav.Navigator()
        out = n.press("middle", {"shift"}, 50, 50) + n.move(51, 51, {"shift"}) + n.release("middle", {"shift"}, 51, 51)
        self.assertEqual([a.kind for a in out], ["recentre"])
        self.assertTrue(n.previews_orbit({"shift"}))


class Explained(unittest.TestCase):
    """Each style in words for the preferences, from the same tables the views use (Daniel, 23/10/2026)."""

    ROWS = ["Pan", "Orbit (3D only)", "Zoom", "Recentre on the point", "Fit the view", "Select", "Menu"]

    def test_every_style_has_its_table_and_a_line_on_whom_it_suits(self):
        for key in nav.STYLES:
            with self.subTest(key):
                rows = nav.table(key)
                self.assertEqual([what for what, _how in rows], self.ROWS)
                self.assertTrue(all(how.strip() for _what, how in rows))
                self.assertTrue(nav.audience(key).strip())

    def test_the_table_is_made_from_the_gestures_of_the_style(self):
        for key, style in nav.STYLES.items():
            with self.subTest(key):
                rows = dict(nav.table(key))
                for kind, row in (("pan", "Pan"), ("orbit", "Orbit (3D only)"), ("zoom", "Zoom")):
                    for gesture in getattr(style, kind):
                        self.assertIn(nav.gesture_text(gesture), rows[row])

    def test_the_table_changes_with_the_style(self):
        autocad, blender, inventor = (dict(nav.table(k)) for k in ("autocad", "blender", "openinventor"))
        self.assertNotEqual(autocad, blender)
        self.assertEqual(autocad["Pan"], "middle, left + right")
        self.assertEqual(blender["Orbit (3D only)"], "middle")
        self.assertIn("double click of the middle button", autocad["Fit the view"])
        self.assertNotIn("double click", blender["Fit the view"])
        self.assertEqual(inventor["Select"], "a click with Ctrl + left or Shift + left")
        self.assertIn("AutoCAD", nav.audience("autocad"))
        # a style this version does not know (a newer one's, a file edited by hand) is AutoCAD's hands, the default
        # until Daniel says otherwise
        self.assertEqual(dict(nav.table("future-style")), autocad)
        self.assertEqual(nav.orbit_key_text("future-style"), nav.orbit_key_text("autocad"))
        moving = nav.Navigator()
        moving.set_style("future-style")
        self.assertIs(moving.style, nav.STYLES["autocad"])
        self.assertIs(nav.Navigator().style, nav.STYLES["autocad"])


if __name__ == "__main__":
    unittest.main()
