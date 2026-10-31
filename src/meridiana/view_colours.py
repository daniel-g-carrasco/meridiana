"""The colours of the plan and the 3D view: their own, the same in the light and the dark theme. The theme is for
the interface (windows, panels, fields, buttons, bars) and the buttons over the views; the drawing keeps the
colours it had before phase 2, made to be read (Daniel, 23/10/2026: «per tema intendevo sull'interfaccia e al
massimo in bottoni che ci sono in modellazione»; the 3D «sembra sempre notte» and the orange lines «a malapena si
vedono»). No Qt here.

- Over the orthophoto (PHOTO): the photo always darkened by a veil (VEIL, adjustable), the outlines light and
  saturated with a dark halo under them, a line of two tones that reads on a light roof and on a dark one.
- Without imagery the same dark ground and the same outlines as over the photo (Daniel, 23/10/2026: the dark
  grey of before as the default, so the drawing does not flip when the photo is taken away). PAPER, a light
  ground with dark outlines, stays for a preference to come.
- The line being drawn in the orange of before (9cc8314), with its halo: Daniel's screenshot of 23/10/2026, a
  line hardly seen on a light roof, is the case it is made for.
- The selection in a saturated tint of its own, apart from the warnings' amber, the errors' red and the blue of
  the sub-fields, with its outline marked; what is under the pointer in a lighter tint of it (FreeCAD colours
  them so, study 15, 3.3). The same in the plan and in 3D.
- The 3D view: the day sky, the ground, the walls and the roofs of before (mesh.py)."""

from __future__ import annotations

from . import theme_colors

VEIL = 0.40                     # how much the orthophoto is darkened by default (0 none, 1 black)
VEILS = (0.0, 0.2, 0.4, 0.6, 0.8)

SELECT = "#ff38c8"              # the selection of what has no kind of its own (a measure, a point)
HOVER = "#ff8adb"               # what a click would select: the same, lighter

# the exclusions' outline in their kind's pink, not the errors' red (R67)
# each kind of object its colour (R67; Daniel, 24/10/2026): the selection and what is under the pointer take it,
# in the plan, in 3D and in the project's tree (KIND_UI, on the panels' light and dark floors). Violet the buildings
# and a lighter violet their pitches, the blue of the sub-fields and of what is laid in them, a pink the exclusions:
# none is a status colour (the traffic light's green, yellow, red stay for the checks) nor the modules' navy
KIND = {"building": "#b48cff", "pitch": "#d2b4ff", "subfield": "#4fb4ff", "row": "#4fb4ff", "module": "#4fb4ff",
        "modules": "#4fb4ff", "exclusion": "#ff5fa2", "prop": "#36c9c0"}       # R269: a teal the 3D objects
KIND_HOVER = {"building": "#d6c2ff", "pitch": "#e6d6ff", "subfield": "#9bd4ff", "row": "#9bd4ff",
              "module": "#9bd4ff", "modules": "#9bd4ff", "exclusion": "#ff9fc6", "prop": "#8be3dd"}
KIND_UI = {"building": ("#7a4fd1", "#c4a6ff"), "pitch": ("#9b6be0", "#d2b4ff"),
           "subfield": ("#1d6fd6", "#6db6ff"), "exclusion": ("#c2306f", "#ff7fb6"), "prop": ("#0f7f78", "#5fd8cf")}


def kind_colour(kind: str, hover: bool = False) -> str:
    """The plan's and the 3D view's colour of a kind of object, for the selection or for what is under the pointer."""
    return (KIND_HOVER if hover else KIND).get(kind, HOVER if hover else SELECT)


def kind_ink(kind: str, dark: bool) -> str:
    """A kind's colour on the panels (the tree's icons): readable on their light or dark floor."""
    pair = KIND_UI.get(kind)
    return pair[1 if dark else 0] if pair else ""

# over the veiled orthophoto: the colours before phase 2 (commit 9cc8314), the outlines a little lighter and more
# saturated, each over a dark halo
PHOTO = {"bg": "#2b2f33", "bld_stroke": "#fff4dc", "bld_fill": "#f2efe628", "pitch": "#ffa552",
         "sub_stroke": "#56b8ff", "sub_fill": "#5ab0ff23", "exclusion": "#ff5fa2", "module": "#192d5a",
         "module_line": "#c6cbd6", "guide": "#7fd4ff", "halo": "#0b0d10e0", "sel": SELECT, "hover": HOVER,
         "draw": "#ffb000", "label_bg": "#14161ac8", "label_fg": "#f2efe6", "prop": "#5fd8cf"}

# without imagery: a light ground, the same outlines made dark enough for it, over a light halo
PAPER = {"bg": "#f3f1ec", "bld_stroke": "#3a352d", "bld_fill": "#3a352d10", "pitch": "#c25a12",
         "sub_stroke": "#1d6fd6", "sub_fill": "#1d6fd614", "exclusion": "#c2306f", "module": "#1f3352",
         "module_line": "#c6cbd6", "guide": "#2e6fb0", "halo": "#ffffffe0", "sel": "#c814b4", "hover": "#cc4cc0",
         "draw": "#b85c00", "label_bg": "#1e1c19e6", "label_fg": "#f8f7f4", "prop": "#0f7f78"}

WORLD = {"ocean": "#263943", "land": ("#52665b", "#5c6858", "#4e6261"), "border": "#a0aa98",
         "graticule": "#78909c35", "label": "#f2efe6", "label_halo": "#14161ae0"}

# the 3D view: the day sky (a gradient around 9cc8314's #cfe0ec), the ground without imagery, the colours of
# mesh.py; the selection tints what it is and outlines it, what is under the pointer is outlined lighter
D3 = {"sky_top": "#a9c9e3", "sky_bottom": "#e4edf3", "ground": "#9fae93", "select": SELECT, "hover": HOVER,
      "pivot": "#7dff6a", "pivot_halo": "#0b0d10",
      # the gizmo of Move and Rotate (task 16b): East red, North green, up and the turn about it blue, as every
      # program has them (study 16, B3), the handle under the pointer in yellow, over a dark halo
      "gizmo_x": "#ff5a52", "gizmo_y": "#5ad66e", "gizmo_z": "#5b8cff", "gizmo_hot": "#ffd84a",
      "gizmo_halo": "#0b0d10"}

# the 3D pictures of the report (ui/report_3d.py): the same scene on paper, light and neutral, the modules in the
# plan's navy so that they stand out, the edges of the buildings drawn as thin lines, as an axonometric drawing has
D3_PAPER = {"background": "#ffffff", "ground": "#ffffff", "wall": "#ebe8e2", "roof_flat": "#d8d5cf",
            "roof": "#d9b9a8", "module": "#2f4f7f", "obstacle": "#bfc1c6", "tree": "#b5c7a8", "edge": "#7d786f"}

# the pivot's cross-hair in 3D (task 16g, study 16 G): a lime green that nothing else on the plan or in 3D has, over a
# dark halo (flat bands under the tubes) drawn this opaque. The cross-hair belongs to the drawing, so it keeps the
# same colours in both themes (R16).
PIVOT_HALO_OPACITY = 0.7
GIZMO_HALO_OPACITY = 0.75

# R35 (Daniel, 23/10/2026: «diamo un buono spessore a tutto»): the widths of the plan's strokes in logical pixels
# (the pens are cosmetic, the same at every zoom), from the 1-2 px of before to about 2-2.5, the selection and
# what is under the pointer thicker still; "halo" is what the halo adds around each stroke. The screenshots of
# 23/10/2026 (meridiana-prove/ux-2026-10-23) are the starting point.
WIDTHS = {"building": 2.5, "pitch": 1.8, "exclusion": 2.2, "subfield": 2.5, "module_line": 0.8, "guide": 1.3,
          "select": 2.6, "select_module": 2.2, "hover": 2.2, "draw": 2.6, "measure": 2.6, "halo": 3.0,
          "select_halo": 2.0}
# R67 (24/10/2026, «troppo pesanti»): the selection 2.6 px over a halo of 2 more (it was 3.4 over 3), its veil
# inside lighter
# the ribbons that outline the selection and what is under the pointer in 3D, pixels (ui/view3d.py)
RIBBONS = {"select": 4.0, "hover": 3.0}


def plan(imagery: bool) -> dict:
    """The plan's colours: the dark ground and its outlines, with imagery under it or not."""
    del imagery                 # the light PAPER is not chosen by it yet: a preference may, one day
    return dict(PHOTO)


def veil(strength: float) -> str:
    """The veil over the orthophoto as "#rrggbbaa": black, `strength` opaque."""
    a = round(255 * min(1.0, max(0.0, strength)))
    return f"#000000{a:02x}"


def veiled(colour: str, strength: float) -> str:
    """A colour of the photo as it shows under the veil."""
    return theme_colors.mix(colour[:7], "#000000", min(1.0, max(0.0, strength)))


def tinted(colour, t: float, towards: str = SELECT) -> tuple[float, float, float]:
    """A colour of the 3D scene (0-1 floats, mesh.py) taken towards `towards` (the selection's tint) by `t`, in
    sRGB."""
    hot = [int(towards[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(float(c + (h - c) * t) for c, h in zip(colour, hot, strict=True))
