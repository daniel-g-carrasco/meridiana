"""The theme's colours computed from one chosen colour (the seed), as study 13 section 12 describes and
docs/studio/13-colori/colori.js computes: the same algorithm, number for number.

Everything is in OKLCH, where the lightness L is the one the eye perceives: the accent, the selection, the
selected module and the assistant keep the seed's hue h (the assistant takes the opposite one) and change only
L and the chroma C, until the contrasts hold. A derived colour may not sit closer than 0.15 in OKLab to a status
colour (warning, critical, good): it is moved away in small steps, darker in the light theme, lighter and less
vivid in the dark one, and the report says so.

The backgrounds ("fondi" in the study) are three: "meridiana" (lime and night, section 7, given by the caller
as the base tokens), "tinted" (greys barely tinted by the seed, "Dal colore") and "grey" (neutral, "Grigi").
Three floors (study 17, A): the window, the panels (the cards the panels are, 1.12:1 from the window in the
light theme) and the view; over them `card` (study 17, C.5: in the dark theme a white veil over the panel),
`field` (the tonal veil of fields and buttons) and `field_line` (a border at 3:1 or more, WCAG 1.4.11).

Colours are "#rrggbb" strings; a translucent one is "#rrggbbaa", the CSS order the study uses: Qt reads eight
digits as "#aarrggbb", so the window converts them with `qt_hex`.

No Qt here: the window's theme (ui/theme.py, still to come) builds its palette and style sheet from these."""

from __future__ import annotations

import copy
import functools
import math
from dataclasses import dataclass

STATUS = {"warning": "#fab219", "critical": "#d03b3b", "good": "#0ca30c"}
NEAR = 0.15                     # the least OKLab distance from a status colour (study 13, 12.3)
BACKGROUNDS = ("meridiana", "tinted", "grey")

# The ready-made colours of section 12.1, besides the system's own. Bronze is the one the program starts with.
PRESETS = {
    "bronze": "#8b5a12", "terracotta": "#a4482b", "olive": "#5f6b1f", "forest": "#2f6b4f", "petrol": "#1f6a7a",
    "blue": "#2a5ea8", "indigo": "#5b4bb0", "plum": "#8a3a6e", "graphite": "#4a4f57",
}
DEFAULT_SEED = PRESETS["bronze"]

# Meridiana's own backgrounds and text (study 13, section 7), the base of the "meridiana" backgrounds.
MERIDIANA_LIGHT = {
    # the floors of the mockups Daniel chose (study 17, 23/10/2026; back to them on 24/10/2026, «riprodurre
    # fedelmente»): the cards stand apart by their line and their shadow, not by a darker window
    "window": "#f2f1ed", "panel": "#f8f7f4", "view": "#ffffff", "line": "#d9d5cc", "line_soft": "#e8e5de",
    "text": "#1e1c19", "text2": "#514c44", "muted": "#6f685d", "header": "#f2f1ed", "card": "#ffffff",
    "tooltip_bg": "#1e1c19", "tooltip_fg": "#f8f7f4",
    "plan": {"bg": "#fbfaf8", "bld_stroke": "#3a352d", "bld_fill": "#3a352d0d", "ink": "#3a352d",
             "label_bg": "#1e1c19e6", "label_fg": "#f8f7f4"}, "d3": {}, "chart": {},
}
MERIDIANA_DARK = {
    # neutral greys with clear steps between the floors (Daniel, 24/10/2026: «in scala di grigi con un maggior
    # contrasto tra i vari colori»): the window under the cards, the cards, the views and the fields between them
    "window": "#151515", "panel": "#252525", "view": "#1c1c1c", "line": "#404040", "line_soft": "#333333",
    "text": "#ededed", "text2": "#c4c4c4", "muted": "#9b9b9b", "header": "#151515", "card": "#252525",
    "tooltip_bg": "#ededed", "tooltip_fg": "#151515",
    "plan": {"bg": "#1c1c1c", "bld_stroke": "#d6d6d6", "bld_fill": "#d6d6d60d", "ink": "#d6d6d6",
             "label_bg": "#0e0e0ee6", "label_fg": "#ededed"}, "d3": {}, "chart": {"surface": "#1c1c1c"},
}
# What does not change with the chosen colour nor with the backgrounds (study 13, 12.2): the modules, the
# selection's halo and the guides on the plan, the sky, the ground, the walls and the pitches in 3D.
FIXED_LIGHT = {
    "plan": {"module": "#1f3352", "halo": "#ffffff", "guide": "#2e6fb0"},
    "d3": {"sky_top": "#dde7f0", "sky_bottom": "#f6f2ea", "ground": "#d6d0bf", "wall": "#f0ebe1", "roof": "#b5643f",
           "roof_flat": "#b8b5b0", "module": "#1f3352", "obstacle": "#8f9299", "tree": "#4f7845"},
}
FIXED_DARK = {
    "plan": {"module": "#1d3152", "halo": "#0b0d10", "guide": "#8ab4f8"},
    "d3": {"sky_top": "#0f141c", "sky_bottom": "#1f2a3a", "ground": "#23272a", "wall": "#d6d0c4", "roof": "#9a5a3e",
           "roof_flat": "#9c9994", "module": "#1d3152", "obstacle": "#7d8088", "tree": "#3e5f37"},
}
# the warning's yellow is 1.8:1 on white: a mark alone on a light background takes a darker ochre (study 13, 3.1)
WARNING_INK = "#b07a00"


def _to_lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _from_lin(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _rgb(hex_: str) -> tuple[float, float, float]:
    h = hex_.lstrip("#")[:6]
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


@functools.lru_cache(maxsize=4096)
def lab(hex_: str) -> tuple[float, float, float]:
    """OKLab of an sRGB colour. Kept by its text: the strings' tints measure the same colours against each other
    thousands of times at the window's start (75 ms, R120)."""
    r, g, b = map(_to_lin, _rgb(hex_))
    l_ = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (0.2104542553 * l_ + 0.793617785 * m - 0.0040720468 * s,
            1.9779984951 * l_ - 2.428592205 * m + 0.4505937099 * s,
            0.0259040371 * l_ + 0.7827717662 * m - 0.808675766 * s)


def lch(hex_: str) -> tuple[float, float, float]:
    """OKLCH of an sRGB colour: lightness 0-1, chroma, hue in degrees."""
    L, a, b = lab(hex_)
    return L, math.hypot(a, b), (math.atan2(b, a) * 180 / math.pi + 360) % 360


def _linear(L: float, C: float, h: float) -> tuple[float, float, float]:
    a, b = C * math.cos(h * math.pi / 180), C * math.sin(h * math.pi / 180)
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3
    return (4.0767416621 * l_ - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l_ + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l_ - 0.7034186147 * m + 1.707614701 * s)


def _in_gamut(v) -> bool:
    return all(-0.0005 <= x <= 1.0005 for x in v)


def hex_of(L: float, C: float, h: float) -> str:
    """The sRGB colour of an OKLCH one; out of gamut, the chroma is cut (keeping L and h) until it fits."""
    c = C
    if not _in_gamut(_linear(L, c, h)):
        lo, hi = 0.0, c
        for _i in range(18):
            mid = (lo + hi) / 2
            if _in_gamut(_linear(L, mid, h)):
                lo = mid
            else:
                hi = mid
        c = lo
    # math.floor(x + 0.5): JavaScript's Math.round, not Python's round half to even
    return "#" + "".join(f"{math.floor(max(0.0, min(1.0, _from_lin(max(0.0, min(1.0, x))))) * 255 + 0.5):02x}"
                         for x in _linear(L, c, h))


def luminance(hex_: str) -> float:
    r, g, b = map(_to_lin, _rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """The WCAG contrast ratio of two colours, 1 to 21."""
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def distance(a: str, b: str) -> float:
    """The OKLab distance of two colours."""
    return math.dist(lab(a), lab(b))


def nearest_status(hex_: str) -> tuple[str, float]:
    """The status colour nearest to `hex_` and its distance."""
    best = ("", 9.0)
    for k, s in STATUS.items():
        d = distance(hex_, s)
        if d < best[1]:
            best = (k, d)
    return best


def protect(hex_: str, darker: bool) -> tuple[str, bool]:
    """The colour moved away from the status colours, darker (light theme) or lighter and less vivid (dark
    theme), in at most 14 steps; and whether it moved."""
    L, C, h = lch(hex_)
    out, n = hex_, 0
    while nearest_status(out)[1] < NEAR and n < 14:
        if darker:
            L, C = L - 0.03, C * 0.94
        else:
            L, C = min(0.97, L + 0.02), C * 0.8
        out = hex_of(L, C, h)
        n += 1
    return out, n > 0


def assistant(seed: str, dark: bool) -> tuple[str, bool]:
    """The assistant's colour: a role of its own (rule 3.6), the hue opposite to the seed's, L 0.42 in the light
    theme and 0.80 in the dark one, C 0.06, kept away from the status colours; and whether it was moved."""
    h = (lch(seed)[2] + 180) % 360
    return protect(hex_of(0.8 if dark else 0.42, 0.06, h), not dark)


@dataclass
class Report:
    """What the preview says about the derived colours: the contrasts, and whether Meridiana moved them."""
    on_accent: float            # text on the accent
    on_view: float              # the accent on the view's background
    on_window: float            # the accent on the window's background
    near: str                   # the status colour the accent was moved away from, or ""
    status_distance: float      # the accent's distance from the nearest status colour
    selection_text: float       # the text on the list selection
    muted: float                # the muted text on the panels
    text2: float                # the secondary text on the panels
    module_sel_distance: float  # the selected module's distance from the nearest status colour
    assistant_near: str         # the status colour the assistant was moved away from, or ""


@dataclass
class Derived:
    tokens: dict                # the base tokens with the derived ones; "plan", "d3" and "chart" are dicts
    report: Report


def _merge(t: dict, more: dict) -> None:
    for k, v in more.items():
        if isinstance(v, dict):
            t.setdefault(k, {}).update(v)
        else:
            t[k] = v


def _backgrounds(t: dict, dark: bool, h: float, k: float) -> None:
    """The "tinted" (k = 1) and "grey" (k = 0) backgrounds, text and lines."""
    def N(L, C):
        return hex_of(L, C * k, h)

    if not dark:
        t.update(window=N(0.957, 0.008), panel=N(0.978, 0.005), view="#ffffff", header=N(0.957, 0.008),
                 card="#ffffff", line=N(0.872, 0.013), line_soft=N(0.926, 0.01), text=N(0.235, 0.012),
                 text2=N(0.43, 0.016), muted=N(0.515, 0.016), tooltip_bg=N(0.235, 0.012),
                 tooltip_fg=N(0.978, 0.005))
        t["plan"].update(bg=N(0.988, 0.003), grid=N(0.935, 0.008), bld_stroke=N(0.32, 0.012),
                         bld_fill=N(0.32, 0.012) + "0d", ink=N(0.32, 0.012), label_bg=t["text"] + "e6",
                         label_fg=t["panel"], pitch=N(0.6, 0.014))
        t["chart"].update(surface="#ffffff", grid=N(0.93, 0.007), axis=N(0.83, 0.01))
    else:
        t.update(window=N(0.196, 0.012), panel=N(0.265, 0.013), view=N(0.226, 0.011), header=N(0.196, 0.012),
                 card=N(0.265, 0.013), line=N(0.372, 0.015), line_soft=N(0.321, 0.013), text=N(0.946, 0.008),
                 text2=N(0.82, 0.012), muted=N(0.69, 0.014), tooltip_bg=N(0.946, 0.008),
                 tooltip_fg=N(0.196, 0.012))
        t["plan"].update(bg=t["view"], grid=N(0.262, 0.012), bld_stroke=N(0.86, 0.01),
                         bld_fill=N(0.86, 0.01) + "0d", ink=N(0.86, 0.01), label_bg=N(0.15, 0.01) + "e6",
                         label_fg=t["text"], halo=N(0.13, 0.01), pitch=N(0.66, 0.014))
        t["chart"].update(surface=t["view"], grid=N(0.275, 0.01), axis=N(0.38, 0.012))


CARD_VEIL = 0.0                 # dark theme: the card is the panel, as in the mockups (the line sets it apart)
FIELD_VEIL = (0.06, 0.22)       # the mockups' --sink: the text at 6 % in the light theme, black at 22 % in the dark
LINE_CONTRAST = 3.0             # a border that identifies a control (WCAG 2.2, 1.4.11)
SELECT_CHROMA = 0.018           # the selection's colour at most (R104): a grey that leans to the accent's hue
# a control under the pointer and pressed (or on): its colour at rest with the text's colour over it, at 8 % and at
# 16 %, in both themes (R160, Daniel 25/10/2026: «caratteristiche di delta colore» the same everywhere); a control
# at rest with no ground of its own takes `hover` and `press` as they are, see-through; one with a ground of its
# own (the `field` of the buttons, the tabs) the same layer over it (`state`)
HOVER, PRESS = 0.08, 0.16


def _surfaces(t: dict, dark: bool) -> None:
    """The surfaces the controls and the cards stand on (study 17, A.5 and C.5): `card` lifted over the panel in
    the dark theme (the view's white in the light one), `field` the tonal veil over the panel, `field_line` a
    grey of the backgrounds' tint at 3:1 or more from the panel and from the field, `accent_hover` the accent
    under the pointer, `danger` the errors' red readable on a field in both themes."""
    if dark:
        t["card"] = mix(t["panel"], "#ffffff", CARD_VEIL)
        t["field"] = mix(t["panel"], "#000000", FIELD_VEIL[1])
    else:
        t["card"] = t["view"]
        t["field"] = mix(t["panel"], t["text"], FIELD_VEIL[0])
    L, C, h = lch(t["line"])
    L = 0.54 if dark else 0.58
    line = hex_of(L, C, h)
    while min(contrast(line, t["panel"]), contrast(line, t["field"])) < LINE_CONTRAST + 0.05 and 0.2 < L < 0.9:
        L += 0.01 if dark else -0.01
        line = hex_of(L, C, h)
    t["field_line"] = line
    # under the pointer: a little lighter in the dark theme, darker in the light one, so the text on it reads better
    t["accent_hover"] = mix(t["accent"], "#ffffff" if dark else t["text"], 0.12)
    # the line of a card: crisp over its shadow in both themes (Daniel, 24/10/2026: «le schede non hanno bordi ma
    # una sbiaditura fatta male di essi»)
    t["card_line"] = t["line"]
    L, C, h = lch(STATUS["critical"])
    L = 0.72 if dark else L
    danger = hex_of(L, C, h)
    while contrast(danger, t["field"]) < 4.5 and 0.2 < L < 0.95:
        L += 0.01 if dark else -0.01
        danger = hex_of(L, C, h)
    t["danger"] = danger
    t["hover"] = t["text"] + f"{round(HOVER * 255):02x}"
    t["press"] = t["text"] + f"{round(PRESS * 255):02x}"


def state(t: dict, rest: str, alpha: float) -> str:
    """The colour of a control with the ground `rest` under the pointer (HOVER) or pressed (PRESS): `rest` with the
    text's colour over it at `alpha`, opaque."""
    return mix(rest, t["text"], alpha)


def derive(seed: str, dark: bool, backgrounds: str = "meridiana", base: dict | None = None) -> Derived:
    """The theme's tokens from the chosen colour `seed`, for the light or the dark theme, with the backgrounds
    "meridiana" (the `base`, Meridiana's own by default), "tinted" or "grey"."""
    if backgrounds not in BACKGROUNDS:
        raise ValueError(f"unknown backgrounds {backgrounds!r}")
    L0, C0, h = lch(seed)
    if base is None:
        # every role: the grey backgrounds first, then what the backgrounds chosen give, then what never changes
        t = {"plan": {}, "d3": {}, "chart": {}}
        _backgrounds(t, dark, h, 0.0)
        if backgrounds == "meridiana":
            _merge(t, MERIDIANA_DARK if dark else MERIDIANA_LIGHT)
        _merge(t, FIXED_DARK if dark else FIXED_LIGHT)
    else:
        t = copy.deepcopy(base)
        for group in ("plan", "d3", "chart"):
            t.setdefault(group, {})
    if backgrounds != "meridiana":
        _backgrounds(t, dark, h, 0.0 if backgrounds == "grey" else 1.0)

    # the accent: white on it in the light theme, on the view's background in the dark one
    L = max(L0, 0.82) if dark else min(L0, 0.6)
    C = min(C0, 0.11) if dark else min(C0, 0.17)
    acc = hex_of(L, C, h)
    if not dark:
        while contrast(acc, "#ffffff") < 4.6 and L > 0.2:
            L -= 0.01
            acc = hex_of(L, C, h)
    else:
        while contrast(acc, t["view"]) < 7 and L < 0.97:
            L += 0.01
            acc = hex_of(L, C, h)
    near = nearest_status(acc)[0]
    acc, moved = protect(acc, not dark)

    fg = t["window"] if dark else "#ffffff"
    # the selection, the chosen tab or pill, the tool on: a grey with a hint of the hue (R104, Daniel 25/10/2026:
    # «lo vorrei un po' meno presente in tutto Meridiana il colore di accento»); it was the accent's pale tint
    sel_bg = (hex_of(0.36, min(SELECT_CHROMA, C0 * 0.5 + 0.004), h) if dark
              else hex_of(0.915, min(SELECT_CHROMA, C0 * 0.5 + 0.004), h))
    mod_sel = acc if dark else protect(hex_of(0.88, min(0.09, C0), h), False)[0]
    asst, asst_moved = assistant(seed, dark)
    t.update(accent=acc, accent_fg=fg, accent_soft=acc + ("24" if dark else "20"), select_bg=sel_bg,
             select_fg=t["text"], assistant=asst)
    t["plan"].update(sub_stroke=acc, sub_fill=acc + ("12" if dark else "14"), sel=acc)
    t["d3"]["module_sel"] = mod_sel
    _surfaces(t, dark)
    report = Report(
        on_accent=contrast(acc, fg), on_view=contrast(acc, t["view"]), on_window=contrast(acc, t["window"]),
        near=near if moved else "", status_distance=nearest_status(acc)[1],
        selection_text=contrast(t["text"], sel_bg), muted=contrast(t["muted"], t["panel"]),
        text2=contrast(t["text2"], t["panel"]), module_sel_distance=nearest_status(mod_sel)[1],
        assistant_near=nearest_status(hex_of(0.8 if dark else 0.42, 0.06, (h + 180) % 360))[0]
        if asst_moved else "")
    return Derived(t, report)


def qt_hex(hex_: str) -> str:
    """A "#rrggbbaa" colour in Qt's order, "#aarrggbb"; "#rrggbb" stays as it is."""
    h = hex_.lstrip("#")
    return "#" + h[6:8] + h[:6] if len(h) == 8 else "#" + h


def mix(a: str, b: str, t: float) -> str:
    """`a` towards `b` by `t` (0 to 1), in sRGB as Qt mixes the colours of a palette."""
    pa, pb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{math.floor((x + (y - x) * t) * 255 + 0.5):02x}" for x, y in zip(pa, pb, strict=True))


def faded_text(t: dict) -> str:
    """The text of what is disabled: the muted text taken towards the window's floor."""
    return mix(t["muted"], t["window"], 0.35)


ROLES = ("Window", "WindowText", "Base", "AlternateBase", "ToolTipBase", "ToolTipText", "PlaceholderText", "Text",
         "Button", "ButtonText", "BrightText", "Light", "Midlight", "Mid", "Dark", "Shadow", "Highlight",
         "HighlightedText", "Link", "LinkVisited", "Accent")
GROUPS = ("Active", "Inactive", "Disabled")


def palette(t: dict, dark: bool) -> dict:
    """Every role of a Qt palette in its three groups, {group: {role: "#rrggbb"}}, from the tokens of `derive`:
    a full palette on Fusion, so that no widget keeps a colour of the system's (study 13, 8)."""
    button = t["panel"] if dark else t.get("card", t["view"])
    active = {
        "Window": t["window"], "WindowText": t["text"], "Base": t["view"], "AlternateBase": t["panel"],
        "ToolTipBase": t["tooltip_bg"], "ToolTipText": t["tooltip_fg"], "PlaceholderText": t["muted"],
        "Text": t["text"], "Button": button, "ButtonText": t["text"],
        "BrightText": "#ffffff" if dark else "#000000",
        "Light": mix(button, "#ffffff", 0.12 if dark else 0.6), "Midlight": mix(button, "#ffffff", 0.06 if dark else 0.3),
        "Mid": t["line"], "Dark": mix(t["line"], "#000000" if dark else t["text"], 0.35),
        "Shadow": "#000000" if dark else mix(t["text"], "#000000", 0.5),
        "Highlight": t["select_bg"], "HighlightedText": t["select_fg"], "Link": t["text"],      # R104: underlined
        "LinkVisited": t["text2"], "Accent": t["accent"],
    }
    faded = faded_text(t)
    disabled = {**active, "WindowText": faded, "Text": faded, "ButtonText": faded, "PlaceholderText": faded,
                "Highlight": t["line"], "HighlightedText": t["muted"], "Link": faded, "Accent": t["line"]}
    return {"Active": active, "Inactive": dict(active), "Disabled": disabled}


def portal_accent(rgb) -> str:
    """The accent of the desktop portal (org.freedesktop.appearance, "accent-color"): three numbers from 0 to 1;
    anything else (out of range: «not set», as the specification says) is no accent, ""."""
    try:
        values = [float(x) for x in rgb]
    except (TypeError, ValueError):
        return ""
    if len(values) != 3 or any(not 0.0 <= x <= 1.0 for x in values):
        return ""
    return "#" + "".join(f"{math.floor(x * 255 + 0.5):02x}" for x in values)


def gdbus_accent(text: str) -> str:
    """The accent in what `gdbus call ... org.freedesktop.portal.Settings.ReadOne org.freedesktop.appearance
    accent-color` prints, «(<(0.784, 0.533, 0.0)>,)»; "" for anything else (an error, no portal, unset)."""
    import re
    if not isinstance(text, str) or "(" not in text:
        return ""
    values = re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)
    return portal_accent(values) if len(values) == 3 else ""


def gdbus_number(text: str) -> int | None:
    """A whole number in what gdbus prints for a portal setting, «(<uint32 1>,)» (reduced-motion: 1 asks for less
    motion); None for anything else."""
    import re
    if not isinstance(text, str):
        return None
    m = re.search(r"<+(?:uint32|int32|uint16|byte)?\s*(\d+)>", text)
    return int(m.group(1)) if m else None


def valid_hex(text: str) -> bool:
    h = text.lstrip("#") if isinstance(text, str) else ""
    return isinstance(text, str) and text.startswith("#") and len(h) == 6 and all(
        c in "0123456789abcdefABCDEF" for c in h)


def seed_for(choice: str, system: str = "") -> str:
    """The chosen colour of the settings ("system", a ready-made one by name, or "#rrggbb") as a colour:
    the system's accent when there is one, bronze otherwise."""
    if choice == "system":
        return system.lower() if valid_hex(system) else DEFAULT_SEED
    if choice in PRESETS:
        return PRESETS[choice]
    return choice.lower() if valid_hex(choice) else DEFAULT_SEED


def retouch_note(report: Report, dark: bool) -> str:
    """What the preview says when the accent was moved away from a status colour, or ""."""
    from .i18n import _
    if not report.near:
        return ""
    what = {"warning": _("the yellow of the warnings"), "critical": _("the red of the errors"),
            "good": _("the green of the checks passed")}[report.near]
    how = _("made it a little lighter") if dark else _("made it a little darker")
    return _("It was close to {what}: Meridiana {how} to keep them apart.").format(what=what, how=how)


# the strings on the plan (task 16d, step 6): a tint for each, as PVsyst's «colours of the electronic components»

TINTS = 8                       # how many tints before they come round again
TINT_HALO = "#0b0d10"           # the dark halo the strings are drawn on (ui/plan.py), the same in both themes
TINT_AVOID = (*STATUS.values(), "#ff38c8")     # the traffic light and the plan's selection (view_colours.SELECT)
TINT_CONTRAST = 3.0             # a line on its halo, as a border that identifies (WCAG 2.2, 1.4.11)
_TINT_CANDIDATES: list = []


def _tint_candidates() -> list:
    """The colours a tint may be: every 15° of hue at five lightnesses and three chromas, those that stand at 3:1
    on the halo and at NEAR or more from the traffic light and the selection. Computed once."""
    if not _TINT_CANDIDATES:
        out: list = []
        for L in (0.5, 0.6, 0.7, 0.8, 0.9):
            for C in (0.08, 0.14, 0.2):
                for k in range(24):
                    c = hex_of(L, C, 15.0 * k)
                    if (c not in out and contrast(c, TINT_HALO) >= TINT_CONTRAST
                            and min(distance(c, a) for a in TINT_AVOID) >= NEAR):
                        out.append(c)
        _TINT_CANDIDATES.extend(out)
    return _TINT_CANDIDATES


_TINTS: dict = {}


def string_tints(seed: str, n: int = TINTS) -> list[str]:
    """`n` tints for the strings, from the chosen colour: the first the seed's hue at a lightness that reads on the
    dark plan, each next one the candidate farthest in OKLab from those already taken, so that two strings side by
    side never look alike. Kept apart from the traffic light (green, yellow, red: the state of a string) and the
    selection, as the derived colours are (NEAR, study 13, 12.3); the same in both themes, as the plan's colours
    (R16)."""
    key = (seed.lower(), n)
    if key in _TINTS:
        return list(_TINTS[key])
    cands = _tint_candidates()
    _L0, _C0, h0 = lch(seed)

    def near_seed(c: str) -> float:
        L, _C, h = lch(c)
        return abs(((h - h0 + 180.0) % 360.0) - 180.0) / 30.0 + abs(L - 0.75) * 4.0
    out = [min(cands, key=near_seed)]
    while len(out) < n:
        out.append(max((c for c in cands if c not in out), key=lambda c: min(distance(c, o) for o in out)))
    if len(_TINTS) > 32:
        _TINTS.clear()
    _TINTS[key] = tuple(out)
    return out
