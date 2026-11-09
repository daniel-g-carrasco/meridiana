"""The report's look (R460, the draft A5 of the study of 06/11/2026 with the chart colours of its closing decision): one
set of values read by the Typst template (as `D.style` in data.json) and by the editable exports (odt.py, word.py), so
the PDF, the ODT and the DOCX have the same fonts, greys, rules and vertical scale.

The report has a palette of its own, warm greys without blue: the colour of the author's profile no longer reaches it
(Daniel, 06/11/2026: «cambia il blu scuro nelle relazioni come grigio scuro, dai titoli e da tutto il resto»). The
colours of the results (green, amber, red of the checks) and the hues of the strings stay, as they say something."""

from __future__ import annotations

import copy

ACCENT = "#3b3a37"           # anthracite: numbers of the sections, rules of the cover, the codes of the steps
TALPA = "#6b655c"            # taupe: the main series, the totals
SABBIA = "#dcd6ca"           # sand, near the grey of the tables' heads: the second series (PVGIS, consumption)
TALPA_DARK = "#4a4743"       # the hatching of the losses

STYLE = {
    "font": {"body": "IBM Plex Sans", "weight": 300, "head": "IBM Plex Sans", "head_weight": 600,
             "table": "IBM Plex Sans", "math": "IBM Plex Math", "mono": "IBM Plex Mono", "table_stretch": 75},
    "size": 9.5,
    "table_size": 8.4,
    "table_pad": 3.6,
    "margin_left": 20,
    "justify": True,
    "hyphenate": True,
    "toc_levels": 2,
    "accent": ACCENT,
    "ink": "#1a1a1a",
    "txt2": "#5f5b54",           # secondary text: table heads, captions, labels
    "faint": "#7a766f",          # faint text: sources, the dots of the contents, «LOGO»
    "tint": "#f4f4f1",           # the result's row
    "rule": "#ccc8c0",
    "hf_rule": 0.5,
    "hf_colour": "#bcb8b0",
    "head_fill": "#f0efec",      # the head of the tables
    "grid": "#dcdbd5",           # the rules of the tables
    "colours": {"acc": ACCENT, "sun": "#e8a317", "leaf": "#2e8b57", "slate": ACCENT, "red": "#d9534f",
                "ok": "#2e7d4f", "warn": "#b7791f", "fail": "#c0392b", "info": "#6b675f", "grey": "#a19c93"},
    "chart": {"calc": TALPA, "ref": SABBIA, "loss": TALPA_DARK, "loss_bg": SABBIA, "gain": TALPA, "total": TALPA,
              "zero": SABBIA, "produced": TALPA, "consumed": SABBIA, "self": ACCENT, "self_halo": True,
              "cash": TALPA, "cash_line": ACCENT, "line_width": 1.2, "extra": ACCENT, "grid": "#e6e2da",
              "grid_width": 0.4, "axis": "#bcb8b0", "hatch": 2.4},
    # the vertical scale, points (6 pt is half a line of text): before (a) and after (b)
    "spacing": {"par": 6, "h1a": 24, "h1b": 12, "h2a": 18, "h2b": 6, "h3a": 12, "h3b": 3, "h4a": 9, "h4b": 3,
                "capa": 4, "capb": 12, "eqa": 10, "eqb": 10, "dasha": 6, "dashb": 12, "taba": 6, "tabb": 12,
                "figa": 6, "figb": 12, "lista": 3, "listb": 9},
}

# the colours of the program's drawings as the report has them (the window keeps its own)
PLAN_MODULE = ACCENT
PLAN_SUBFIELD = "#8f8a80"
D3_MODULE = TALPA_DARK
D3_OBSTACLE = "#c2beb6"


def style() -> dict:
    """A copy of the look, for one document."""
    return copy.deepcopy(STYLE)


def points_to_cm(value: float) -> float:
    return round(value * 2.54 / 72, 2)
