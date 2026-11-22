"""The plan's levels of detail (R707, study 55): what the plan draws depends on how large a module is on screen, and
the thresholds are here and nowhere else. `p` is the module's shorter side on screen, in logical pixels; `S` the
site's larger side.

    Module    p from 40      the single module: its dot, the numbers of the chosen string
    String    p 14 to 40     the strings: their lines, a name each, the dot of each string's first module
    Field     p 5 to 14      the fields in the strings' colours, no lines; the modules' outlines fade out
    Building  p 1.2 to 5     buildings and fields, one fill for each row; the strings' colours fade out
    Site      p under 1.2    the buildings' shapes alone, while the site is at least 64 px; the checks' marks
                             one by one fade out from p 2 and are summed up on the site's drop
    Map       S under 64     the site's mark alone: it comes in while the drawing goes out, S from 80 to 48 px,
                             and from 5 km a pixel it is the drop without its name

What comes and goes between two thresholds fades with the scale, not with time: its opacity follows p."""
from __future__ import annotations

MODULE = 40.0               # px: from here a dot on every module
STRING = 14.0               # px: from here the strings' lines and their names
FIELD = 5.0                 # px: from here a fill for each module and the strings' colours whole
BUILDING = 1.2              # px: from here the fields
SITE = 64.0                 # px of the site: under it the site's mark alone
SITE_IN = 80.0              # px of the site: the mark comes in from here, while the drawing goes out
SITE_ALONE = 48.0           # px of the site: from here down the mark alone, the drawing not drawn
SITE_NAMELESS = 5000.0      # m a pixel: from here the mark without its name
MARKS = 2.0                 # px: the checks' marks one by one fade out from here down to BUILDING (Daniel 21/11/2026:
#                             the warning's triangle stayed over the site's drop at every zoom out); from far the worst
#                             of them and their number sit on the site's drop

OUTLINE_GONE = 6.0          # px: the modules' outlines fade from STRING down to here
COLOUR_GONE = 2.5           # px: the strings' colours fade from FIELD down to here
EASE = 0.9                  # what comes at a threshold fades in over its last tenth
VERTEX_SIDE = 16.0          # px: the corners of what is selected show while its shorter side is this long on screen
MEASURE_SIDE = 80.0         # px: the measures of its sides while its longer side is this long

# the names the QML reads (PlanController.levels)
AS_QML = dict(module=MODULE, string=STRING, field=FIELD, building=BUILDING, site=SITE,
              siteIn=SITE_IN, siteAlone=SITE_ALONE, siteNameless=SITE_NAMELESS, marks=MARKS,
              outlineGone=OUTLINE_GONE, colourGone=COLOUR_GONE, ease=EASE,
              vertexSide=VERTEX_SIDE, measureSide=MEASURE_SIDE)


def wiring_level(pixels: float) -> str:
    """How much the strings say at this scale (plan_wiring): `near` lines, names and dots; `mid` the coloured
    fields and the names; `far` a mark for each string or inverter."""
    return "near" if pixels >= STRING else "mid" if pixels >= FIELD else "far"


def dots_shown(pixels: float) -> str:
    """Which dots of the finished strings show: `all` (one on each module), `heads` (each string's first), `none`."""
    return "all" if pixels >= MODULE else "heads" if pixels >= STRING else "none"


def site_shown(span: float) -> float:
    """How much of the site's mark shows when the site's larger side is `span` px on screen: 0 from SITE_IN up,
    1 from SITE_ALONE down; the drawing shows the rest."""
    return max(0.0, min(1.0, (SITE_IN - span) / (SITE_IN - SITE_ALONE)))
