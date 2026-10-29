"""The chapters of the report (R61, docs/compiti/19r-relazione.md): each a function of the report's context that
returns its HTML (the numbered heading is the composer's, ui/report.py), from the data of the variant; the charts
and the plans drawn for paper by matplotlib (light, 200 dpi), the tables as a document has them (R79 is for the
cards of the interface, not for paper).

The data (`Context.data`) are what the window hands over (MainWindow._report_data): the year ("sim"), the
consumption ("load"), the economics ("econ"), PVGIS ("pvgis"), the plant with its strings ("plant"), the layouts
of the sub-fields ("results"), the checks ("checks"), the notes of the rules ("rules_notes"), the sizing and the
storage, the weather's text ("meteo_text"). A chapter is called only when its data are there (reports.plan)."""

from __future__ import annotations

import functools
import html
import io
import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ..i18n import _, ngettext, number
from .charts import SERIES
from .pedigree import formula_png, records_html
from .report_style import CHROME, INK, MARK_COLOURS, PLAN, STRING_HUES
from .theme import matplotlib_fonts

MARKS = {"ok": "✔", "warn": "⚠", "fail": "✘", "info": "ℹ"}
SYMBOL_OF = {"✔": "check", "⚠": "warning", "✘": "stop", "ℹ": "info"}     # a mark's symbol (ui/symbols.py)
SYMBOL_PX, SYMBOL_RATIO = 12, 6.0       # a symbol in a line of the report (9,5 pt), drawn at 6 times for the print
_IMAGE: list = [None]                   # the report being written: its image(name, make, ratio) (report._compose)


class Html(str):
    """Text already in HTML: written as it is in a table's cell."""


@dataclass
class Context:
    project: object
    data: dict
    image: Callable                  # image(name, make, ratio=1.0) -> the URL of the image `make()` draws
    settings: dict

    def get(self, key: str):
        return self.data.get(key)


def mark(symbol: str) -> str:
    """A result's mark as the window's symbol (R138: it was the character in its colour): a picture of the report
    while one is written, the window's own in a label; the character in its colour for any other."""
    name = SYMBOL_OF.get(symbol)
    if name is not None and _IMAGE[0] is not None:
        url = _IMAGE[0](f"symbol-{name}", functools.partial(_symbol_png, name), SYMBOL_RATIO)
        return f"<img src='{url}' width='{SYMBOL_PX}' height='{SYMBOL_PX}' style='vertical-align: middle'>"
    if name is not None:
        from . import symbols
        return symbols.html(name)
    from .theme import mark as in_font
    return f"<span style='color: {MARK_COLOURS.get(symbol, INK)}'>{in_font(symbol)}</span>"


@functools.lru_cache(maxsize=8)
def _symbol_png(name: str) -> bytes:
    """The symbol on the report's white, SYMBOL_RATIO times its size, as PNG."""
    from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
    from PySide6.QtGui import QImage, QPainter

    from . import symbols
    side = round(SYMBOL_PX * SYMBOL_RATIO)
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    symbols.renderer(name, False).render(p, QRectF(0, 0, side, side))
    p.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def esc(value) -> str:
    return value if isinstance(value, Html) else html.escape(str(value))


def kwh(v) -> str:
    return number(float(v), 0, grouping=True)


def table(rows, head=None, right=(), widths=None) -> str:
    """A table of the document: a header row on a light ground, the numbers (`right`, column indexes) aligned
    right."""
    out = ["<table class='grid' width='100%' cellspacing='0' cellpadding='4'>"]
    if head:
        cells = []
        for i, h in enumerate(head):
            w = f" width='{widths[i]}'" if widths and widths[i] else ""
            cells.append(f"<th align='{'right' if i in right else 'left'}'{w}>{esc(h)}</th>")
        out.append("<thead><tr>" + "".join(cells) + "</tr></thead>")
    for row in rows:
        out.append("<tr>" + "".join(f"<td align='{'right' if i in right else 'left'}'>{esc(c)}</td>"
                                    for i, c in enumerate(row)) + "</tr>")
    out.append("</table>")
    return "".join(out)


def facts(rows) -> str:
    """Label and value, two columns, the value in bold: the headline numbers."""
    body = "".join(f"<tr><td class='label' width='48%'>{esc(a)}</td><td><b>{esc(b)}</b></td></tr>" for a, b in rows)
    return f"<table class='facts' width='100%' cellspacing='0' cellpadding='3'>{body}</table>"


def para(text: str, cls: str = "") -> str:
    return f"<p{f' class={chr(39)}{cls}{chr(39)}' if cls else ''}>{html.escape(text)}</p>"


def months() -> list[str]:
    return [_("Jan"), _("Feb"), _("Mar"), _("Apr"), _("May"), _("Jun"), _("Jul"), _("Aug"), _("Sep"), _("Oct"),
            _("Nov"), _("Dec")]


# drawing for paper

def figure_png(draw, width_in: float = 7.0, height_in: float = 2.8) -> bytes:
    """A chart drawn for paper: light colours, 200 dpi."""
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    c = CHROME["light"]
    matplotlib_fonts()                                  # the program's fonts, at matplotlib's first use
    fig = Figure(figsize=(width_in, height_in), dpi=200, layout="constrained")
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(c["axis"])
    ax.tick_params(colors=c["muted"], labelsize=7, length=0)
    ax.grid(True, axis="y", color=c["grid"], linewidth=0.6)
    ax.set_axisbelow(True)
    draw(ax, c, SERIES["light"])
    buf = io.BytesIO()
    with matplotlib.rc_context({"savefig.facecolor": "white"}):
        fig.savefig(buf, format="png")
    return buf.getvalue()


def _nice(length: float) -> float:
    """A round length for the scale bar, about `length`: 1, 2 or 5 times a power of ten."""
    if length <= 0:
        return 1.0
    p = 10 ** math.floor(math.log10(length))
    return max(s * p for s in (1, 2, 5) if s * p <= length) if length >= p else p


def plan_extent(project) -> tuple[float, float, float, float] | None:
    """The plan's box: (x0, x1, y0, y1) of the buildings, the sub-fields and the exclusions."""
    pts = [p for b in project.buildings for p in b.footprint] + [p for sf in project.subfields for p in sf.ring] + \
        [p for e in project.exclusions for p in e.ring]
    if not pts:
        return None
    xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def plan_png(project, results: dict, plant=None, width_in: float = 7.0, height_in: float | None = None) -> bytes:
    """The plan of the project for paper: buildings, sub-fields with their names, exclusions, the modules laid;
    with `plant`, every string in a hue of its own with its path and its label. North up, a scale bar under its
    bottom left corner; as tall as the plan wants at that width (`height_in` None), within a page's room."""
    box = plan_extent(project)
    if box is None:
        return b""
    span_x, span_y = max(box[1] - box[0], 1.0), max(box[3] - box[2], 1.0)
    if height_in is None:
        height_in = min(5.6, max(2.4, width_in * (span_y * 1.2 + 0.1 * span_x) / (span_x * 1.12)))
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.collections import PolyCollection
    from matplotlib.figure import Figure
    from matplotlib.patches import Polygon
    matplotlib_fonts()                                  # the program's fonts, at matplotlib's first use
    fig = Figure(figsize=(width_in, height_in), dpi=200)
    FigureCanvasAgg(fig)
    ax = fig.add_axes((0.01, 0.01, 0.98, 0.98))
    ax.set_aspect("equal")
    ax.axis("off")
    xs, ys = [], []

    def ring(points, **kw):
        pts = [(float(x), float(y)) for x, y in points]
        if len(pts) >= 3:
            ax.add_patch(Polygon(pts, closed=True, **kw))
            xs.extend(p[0] for p in pts)
            ys.extend(p[1] for p in pts)

    for b in project.buildings:
        ring(b.footprint, facecolor=PLAN["building"], edgecolor=PLAN["building_edge"], linewidth=0.7, zorder=1)
    for e in project.exclusions:
        ring(e.ring, facecolor=PLAN["exclusion"], edgecolor=PLAN["exclusion_edge"], linewidth=0.5, zorder=2)
    colour_of: dict = {}
    if plant is not None:
        for n, s in enumerate(sorted(plant.strings, key=lambda x: (x.inverter, x.mppt, x.index))):
            for sf, key, _c in s.modules:
                colour_of[(sf, key)] = STRING_HUES[n % len(STRING_HUES)]
    polys, faces = [], []
    for sf in project.subfields:
        r = results.get(sf.id)
        for pm in (getattr(r, "modules", None) or []):
            polys.append([(float(x), float(y)) for x, y in pm.corners])
            faces.append(colour_of.get((sf.id, pm.key), PLAN["module"] if plant is None else "#c9c5bd"))
    if polys:
        ax.add_collection(PolyCollection(polys, facecolors=faces, edgecolors=PLAN["module_edge"], linewidths=0.15,
                                         zorder=3))
    for sf in project.subfields:
        ring(sf.ring, facecolor="none", edgecolor=PLAN["subfield"], linewidth=0.8, linestyle=(0, (4, 2)), zorder=4)
    if not xs:
        return b""
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = max(x1 - x0, y1 - y0, 1.0)
    pad = 0.04 * span
    ax.set_xlim(x0 - pad, x1 + 2.5 * pad)
    ax.set_ylim(y0 - 2.6 * pad, y1 + pad)
    label = {"fontsize": 6.5, "color": PLAN["label"], "zorder": 6, "ha": "center", "va": "center",
             "bbox": {"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "none", "alpha": 0.85}}
    if plant is not None:
        for n, s in enumerate(sorted(plant.strings, key=lambda x: (x.inverter, x.mppt, x.index))):
            pts = [c for _sf, _k, c in s.modules if c]
            if not pts:
                continue
            hue = STRING_HUES[n % len(STRING_HUES)]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=hue, linewidth=0.6, zorder=5, alpha=0.9)
            ax.text(pts[0][0], pts[0][1], s.label, **{**label, "fontsize": 5.5, "color": hue})
    else:
        for sf in project.subfields:
            if len(sf.ring) >= 3:
                cx = sum(float(p[0]) for p in sf.ring) / len(sf.ring)
                cy = sum(float(p[1]) for p in sf.ring) / len(sf.ring)
                ax.text(cx, cy, sf.name, **label)
    # the scale bar at the bottom left, the north at the top right
    bar = _nice((x1 - x0) / 5 if x1 > x0 else span / 5)
    bx, by = x0, y0 - 1.5 * pad
    ax.plot([bx, bx + bar], [by, by], color=PLAN["label"], linewidth=1.2, solid_capstyle="butt", zorder=6)
    for x in (bx, bx + bar):
        ax.plot([x, x], [by - 0.3 * pad, by + 0.3 * pad], color=PLAN["label"], linewidth=0.8, zorder=6)
    ax.text(bx + bar + 0.4 * pad, by, f"{number(bar, 0)} m", fontsize=6.5, color=PLAN["label"], va="center",
            zorder=6)
    nx, ny = x1 + 1.5 * pad, y1 - 1.2 * pad
    ax.annotate("", xy=(nx, ny), xytext=(nx, ny - 2.2 * pad),
                arrowprops={"arrowstyle": "-|>", "color": PLAN["label"], "linewidth": 0.8}, zorder=6)
    ax.text(nx, ny + 0.6 * pad, "N", fontsize=7, color=PLAN["label"], ha="center", va="center", zorder=6)
    buf = io.BytesIO()
    with matplotlib.rc_context({"savefig.facecolor": "white"}):
        fig.savefig(buf, format="png")
    return buf.getvalue()


# what the chapters share

def _modules(project, results: dict) -> list[tuple[str, int, float]]:
    """The modules laid by model: (name, how many, kWp)."""
    from ..energy.simulate import ModuleSpec
    out: dict = {}
    for sf in project.subfields:
        r = results.get(sf.id)
        n = len(getattr(r, "modules", None) or []) if sf.filled else 0
        if not n:
            continue
        spec = ModuleSpec.from_record(project.modules.get(sf.module) or {"power_kw": project.module_of(sf).power_kw})
        name = f"{spec.manufacturer} {spec.model}".strip()
        count, kwp = out.get(name, (0, 0.0))
        out[name] = (count + n, kwp + n * spec.pmax / 1000)
    return [(k, n, p) for k, (n, p) in out.items()]


def _inverters(plant) -> list[tuple[str, int, float]]:
    """The inverters by model: (name, how many, AC kW)."""
    out: dict = {}
    for u in getattr(plant, "units", []) or []:
        count, ac = out.get(u.name, (0, 0.0))
        out[u.name] = (count + 1, ac + (u.spec.pac or 0) / 1000)
    return [(k, n, p) for k, (n, p) in out.items()]


def _headline(ctx: Context) -> list[tuple[str, str]]:
    sim, econ, plant = ctx.get("sim"), ctx.get("econ"), ctx.get("plant")
    rows = [(_("Power at STC"), f"{number(sim.p_stc_kw, 2)} kWp")]
    mods = _modules(ctx.project, ctx.get("results") or {})
    if mods:
        rows.append((_("Modules"), "; ".join(f"{n} × {name}" for name, n, _p in mods)))
    invs = _inverters(plant)
    if invs:
        rows.append((_("Inverters"), "; ".join(f"{n} × {name}" for name, n, _p in invs)))
    rows.append((_("AC power"), f"{number(sim.p_ac_kw, 1)} kW"))
    if plant is not None and plant.units:
        from ..energy import plant as plants
        ratio, _cut = plants.dcac(plant)
        if ratio:
            rows.append((_("Ratio DC/AC"), number(ratio, 2)))
    rows += [(_("Energy a year (typical year)"), f"{kwh(sim.energy_kwh)} kWh"),
             (_("Specific yield"), f"{kwh(sim.specific_yield)} kWh/kWp"),
             (_("Performance ratio"), f"{number(100 * sim.pr, 1)} %")]
    if econ is not None:
        k = econ.kpi
        rows += [(_("Self-consumption"), f"{number(100 * k['self_ratio'], 0)} %"),
                 (_("Self-sufficiency"), f"{number(100 * k['self_sufficiency'], 0)} %"),
                 (_("Saving, first year"), f"{kwh(k['saving_1'])} €"),
                 (_("Payback"), _("{y} years").format(y=number(k["payback"], 1)) if k["payback"] is not None else "–")]
    return rows


def _plan(ctx: Context, strings: bool = False) -> str:
    results = ctx.get("results") or {}
    plant = ctx.get("plant") if strings else None
    if not any(getattr(r, "modules", None) for r in results.values()):
        return ""
    name = "plan_strings" if strings else "plan"
    url = ctx.image(name, lambda: plan_png(ctx.project, results, plant))
    caption = (_("The strings on the modules: each in a hue of its own, from its label along its modules.") if strings
               else _("Plan of the modules laid: buildings, sub-fields (dashed), exclusions; north up."))
    return f"<p align='center'><img src='{url}' width='620'></p>{para(caption, 'caption')}"


def _views(ctx: Context) -> str:
    """The 3D pictures of the layout side by side, each with its caption (ui/report_3d.py); "" where they cannot be
    made: nothing laid, or Qt Quick 3D without its renderer here."""
    results = ctx.get("results") or {}
    if not any(getattr(r, "modules", None) for r in results.values()):
        return ""
    from . import report_3d
    if not report_3d.available():
        return ""
    cells = []
    for vid, (_bearing, _elevation, caption) in report_3d.views().items():
        url = ctx.image(f"view_{vid}", lambda vid=vid: report_3d.picture(ctx.project, results, vid))
        cells.append(f"<td align='center' width='50%'><img src='{url}' width='300'><br>"
                     f"<span class='caption'>{html.escape(caption)}</span></td>")
    return ("<table width='100%' cellspacing='0' cellpadding='3' style='margin-top: 4pt; margin-bottom: 6pt'><tr>"
            + "".join(cells) + "</tr></table>")


def _monthly_chart(ctx: Context) -> str:
    from matplotlib.ticker import FuncFormatter
    sim, pv = ctx.get("sim"), ctx.get("pvgis")
    mine = sim.monthly.e_ac.to_numpy()
    names = months()

    def draw(ax, c, col):
        x = np.arange(12)
        w = 0.4 if pv is not None else 0.6
        ax.bar(x - (w / 2 if pv is not None else 0), mine, w, color=col[0], label="Meridiana")
        if pv is not None:
            ax.bar(x + w / 2, pv.monthly_kwh, w, color=col[1], label="PVGIS")
            leg = ax.legend(frameon=False, fontsize=7, loc="upper left", ncols=2)
            for t in leg.get_texts():
                t.set_color(c["ink2"])
        ax.set_xticks(x, names)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: number(v, 0, grouping=True)))
        ax.set_ylabel("kWh", fontsize=7, color=c["ink2"])
    return f"<p align='center'><img src='{ctx.image('monthly', lambda: figure_png(draw))}' width='620'></p>"


# the chapters of «Complete»

def summary(ctx: Context) -> list[str]:
    sim = ctx.get("sim")
    n_sf = sum(1 for sf in ctx.project.subfields if sf.filled and getattr((ctx.get("results") or {}).get(sf.id),
                                                                          "modules", None))
    text = ngettext("A system of {kwp} kWp on {n} sub-field: in the typical year it produces {e} kWh, {y} kWh for "
                    "each kWp.", "A system of {kwp} kWp on {n} sub-fields: in the typical year it produces {e} kWh, "
                    "{y} kWh for each kWp.", max(1, n_sf)).format(
        kwp=number(sim.p_stc_kw, 1), n=max(1, n_sf), e=kwh(sim.energy_kwh), y=kwh(sim.specific_yield))
    return [para(text), facts(_headline(ctx)), _views(ctx), _plan(ctx)]


def site(ctx: Context) -> list[str]:
    s = ctx.project.site
    rows = [(_("Latitude"), f"{number(s.lat, 5)}°"), (_("Longitude"), f"{number(s.lon, 5)}°")]
    if ctx.settings.get("address", True) and s.address:
        rows.insert(0, (_("Address"), s.address))
    sim = ctx.get("sim")
    if ctx.get("meteo_text"):
        rows.append((_("Weather"), ctx.get("meteo_text")))
    pv = ctx.get("pvgis")
    if pv is not None:
        rows.append((_("Second opinion"), pv.source.label))
    parts = [facts(rows)]
    if sim is not None:
        m = sim.monthly
        names = months()
        body = [(names[i], kwh(m.ghi.iloc[i]), kwh(m.dhi.iloc[i]), kwh(m.poa.iloc[i]), number(m.temp_air.iloc[i], 1))
                for i in range(min(12, len(m)))]
        body.append((_("Year"), kwh(m.ghi.sum()), kwh(m.dhi.sum()), kwh(m.poa.sum()), number(m.temp_air.mean(), 1)))
        parts.append(f"<h3>{html.escape(_('Irradiation and temperature month by month'))}</h3>")
        parts.append(table(body, [_("Month"), _("Horizontal, kWh/m²"), _("Diffuse, kWh/m²"),
                                  _("On the plane, kWh/m²"), _("Air, °C")], right=(1, 2, 3, 4)))
        parts.append(para(_("On the plane: the irradiation on the modules' plane, the arrays together, weighted by "
                            "their power."), "caption"))
    return parts


def layout(ctx: Context) -> list[str]:
    from .properties import mounting_names
    results = ctx.get("results") or {}
    p = ctx.project
    mounts = mounting_names()
    buildings = {b.id: b.name for b in p.buildings}
    rows, rules = [], []
    for sf in p.subfields:
        r = results.get(sf.id)
        mods = getattr(r, "modules", None) if sf.filled else None
        if not mods:
            continue
        params = sf.layout_params()
        kw = len(mods) * p.module_of(sf).power_kw
        where = buildings.get(sf.building, "") if sf.building else _("ground")
        rows.append((sf.name, where, number(r.area, 0), str(len(mods)), number(kw, 2),
                     mounts.get(params.mounting, params.mounting), f"{number(r.azimuth, 0)}°", f"{number(r.tilt, 0)}°",
                     number(r.pitch, 2) if r.pitch else "–"))
        if r.pitch:
            rules.append(_("{name}: rows {pitch} m apart, {gap} m free behind each, the sun above {angle}° clears "
                           "them (limit angle, CEI 82-25/3, Fig. 1).").format(
                name=sf.name, pitch=number(r.pitch, 2), gap=number(r.clearance, 2), angle=number(r.limit_angle, 1)))
    parts = [table(rows, [_("Sub-field"), _("On"), _("Area, m²"), _("Modules"), "kWp", _("Mounting"), _("Azimuth"),
                          _("Tilt"), _("Pitch, m")], right=(2, 3, 4, 6, 7, 8))]
    parts.append(para(_("Azimuth from the south, positive towards the west (CEI 82-25); area as drawn, in plan."),
                      "caption"))
    if rules:
        parts.append(f"<h3>{html.escape(_('Distances between the rows'))}</h3>")
        parts += [para(t) for t in rules]
    if p.exclusions:
        from collections import Counter
        from .. import model
        kinds = Counter(e.kind for e in p.exclusions)
        names = model.exclusion_kind_names() if hasattr(model, "exclusion_kind_names") else {}
        parts.append(f"<h3>{html.escape(_('Exclusions'))}</h3>")
        parts.append(para("; ".join(f"{names.get(k, k)}: {n}" for k, n in sorted(kinds.items()))))
    parts.append(_plan(ctx))
    return parts


def plant(ctx: Context) -> list[str]:
    from ..energy import plant as plants
    pl = ctx.get("plant")
    parts = []
    invs = _inverters(pl)
    if invs:
        ratio, cut = plants.dcac(pl)
        rows = [(name, str(n), number(ac, 1)) for name, n, ac in invs]
        parts.append(table(rows, [_("Inverter"), _("How many"), _("AC kW")], right=(1, 2)))
        if ratio:
            text = _("DC/AC ratio {r}").format(r=number(ratio, 2))
            if cut is not None:
                text += "; " + _("energy cut by the inverters {c} % of the year's").format(c=number(100 * cut, 1))
            parts.append(para(text + "."))
    if pl.strings:
        parts.append(_plan(ctx, strings=True))
        parts += plant_parts(ctx.project, pl)
    return parts


def production(ctx: Context) -> list[str]:
    sim, pv = ctx.get("sim"), ctx.get("pvgis")
    rows = [(_("Energy a year (typical year)"), f"{kwh(sim.energy_kwh)} kWh"),
            (_("Specific yield"), f"{kwh(sim.specific_yield)} kWh/kWp"),
            (_("Performance ratio"), f"{number(100 * sim.pr, 1)} %")]
    if pv is not None:
        rows.append((_("PVGIS, second opinion"), f"{kwh(pv.yearly_kwh)} kWh ({pv.source.label})"))
    parts = [facts(rows)]
    inverters = getattr(sim, "inverters", ())
    if inverters:
        parts.append(f"<h3>{html.escape(_('Production by inverter'))}</h3>")
        parts.append(para(_("Each inverter is calculated separately, including its power limit. AC energy includes "
                            "wiring losses and unavailability; the hourly register keeps the individual results.")))
        parts.append(table([(f"{inv['number']} · {inv['name']}", number(inv["p_ac_kw"], 2),
                             kwh(inv["dc_kwh"]), kwh(inv["clipping_kwh"]), kwh(inv["ac_kwh"]))
                            for inv in inverters],
                           [_("Inverter"), _("AC rating, kW"), _("DC energy, kWh"),
                            _("Clipping, kWh"), _("AC energy, kWh")], right=(1, 2, 3, 4)))
    m = sim.monthly
    names = months()
    body = []
    for i in range(min(12, len(m))):
        row = [names[i], kwh(m.poa.iloc[i]), kwh(m.e_ac.iloc[i]), kwh(m.e_ac.iloc[i] / sim.p_stc_kw if sim.p_stc_kw else 0),
               f"{number(100 * m.pr.iloc[i], 1)} %"]
        if pv is not None:
            row.append(kwh(pv.monthly_kwh[i]))
        body.append(row)
    total = [_("Year"), kwh(m.poa.sum()), kwh(sim.energy_kwh), kwh(sim.specific_yield), f"{number(100 * sim.pr, 1)} %"]
    if pv is not None:
        total.append(kwh(pv.yearly_kwh))
    body.append(total)
    head = [_("Month"), _("On the plane, kWh/m²"), _("Energy, kWh"), "kWh/kWp", "PR"] + (["PVGIS, kWh"] if pv else [])
    parts.append(f"<h3>{html.escape(_('Month by month'))}</h3>")
    parts.append(table(body, head, right=tuple(range(1, len(head)))))
    parts.append(_monthly_chart(ctx))
    steps = [s for s in sim.chain if s.change is not None]
    if steps:
        def chain(ax, c, col):
            y = np.arange(len(steps))[::-1]
            vals = [s.change for s in steps]
            ax.barh(y, vals, 0.6, color=[col[0] if v >= 0 else col[7] for v in vals])
            ax.axvline(0, color=c["axis"], linewidth=0.8)
            ax.set_yticks(y, [s.label for s in steps])
            ax.tick_params(axis="y", labelsize=6.5, colors=c["ink2"])
            ax.grid(True, axis="x", color=c["grid"], linewidth=0.6)
            ax.grid(False, axis="y")
            for yy, v in zip(y, vals, strict=True):
                ax.text(v + (0.15 if v >= 0 else -0.15), yy, f"{number(v, 1)}%", va="center",
                        ha="left" if v >= 0 else "right", fontsize=6, color=c["ink2"])
        parts.append(f"<h3>{html.escape(_('From the sun to the grid'))}</h3>")
        parts.append(para(_("Each step against the one before: the irradiation on the plane against the horizontal, "
                            "then the losses down to the energy delivered.")))
        parts.append(f"<p align='center'><img src='{ctx.image('chain', lambda: figure_png(chain, 7.0, 3.6))}' "
                     "width='620'></p>")
    shaded = [a for a in sim.arrays if (a.get("row_shading") or 0) + (a.get("obstacle_shading") or 0) > 0.0005]
    if shaded:
        parts.append(f"<h3>{html.escape(_('Shading'))}</h3>")
        parts.append(table([(a["name"], f"{number(100 * (a.get('row_shading') or 0), 1)} %",
                             f"{number(100 * (a.get('obstacle_shading') or 0), 1)} %",
                             f"{number(100 * (a.get('rows_electrical') or 0), 1)} %") for a in sim.arrays],
                           [_("Array"), _("Rows, linear"), _("Obstacles, linear"), _("Rows, electrical")],
                           right=(1, 2, 3)))
    return parts


def consumption(ctx: Context) -> list[str]:
    from matplotlib.ticker import FuncFormatter
    load, econ = ctx.get("load"), ctx.get("econ")
    by = load.by_band()
    rows = [(_("Consumption a year"), f"{kwh(load.annual_kwh)} kWh ({load.basis})")]
    rows += [(b, f"{kwh(by[b])} kWh") for b in ("F1", "F2", "F3")]
    if econ is not None:
        k = econ.kpi
        rows += [(_("Self-consumption"), f"{number(100 * k['self_ratio'], 0)} % ({kwh(k['self'])} kWh)"),
                 (_("Self-sufficiency"), f"{number(100 * k['self_sufficiency'], 0)} %"),
                 (_("Energy fed in"), f"{kwh(k['export'])} kWh")]
    parts = [facts(rows)]
    if econ is not None and len(getattr(econ, "monthly", [])) == 12:
        mo = econ.monthly
        names = months()
        body = [(names[i], kwh(mo["production"].iloc[i]), kwh(mo["consumption"].iloc[i]), kwh(mo["self"].iloc[i]),
                 kwh(mo["export"].iloc[i]), kwh(mo["import"].iloc[i])) for i in range(12)]
        body.append((_("Year"), kwh(mo["production"].sum()), kwh(mo["consumption"].sum()), kwh(mo["self"].sum()),
                     kwh(mo["export"].sum()), kwh(mo["import"].sum())))
        parts.append(f"<h3>{html.escape(_('Month by month'))}</h3>")
        parts.append(table(body, [_("Month"), _("Produced"), _("Consumed"), _("Self-consumed"), _("Fed in"),
                                  _("Drawn")], right=(1, 2, 3, 4, 5)))
        parts.append(para(_("kWh; self-consumed: the energy produced and used on site, at the same hour."), "caption"))

        def bars(ax, c, col):
            x = np.arange(12)
            ax.bar(x - 0.2, mo["production"].to_numpy(), 0.4, color=col[0], label=_("Produced"))
            ax.bar(x + 0.2, mo["consumption"].to_numpy(), 0.4, color=col[2], label=_("Consumed"))
            ax.plot(x, mo["self"].to_numpy(), color=c["ink"], linewidth=1.2, marker="o", markersize=2.5,
                    label=_("Self-consumed"))
            leg = ax.legend(frameon=False, fontsize=7, loc="upper left", ncols=3)
            for t in leg.get_texts():
                t.set_color(c["ink2"])
            ax.set_xticks(x, names)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: number(v, 0, grouping=True)))
            ax.set_ylabel("kWh", fontsize=7, color=c["ink2"])
        parts.append(f"<p align='center'><img src='{ctx.image('balance', lambda: figure_png(bars))}' width='620'></p>")
    hourly = getattr(econ, "hourly", None) if econ is not None else None
    if hourly is not None and "self" in getattr(hourly, "columns", []):
        from .energy_pages import year_carpet
        grid, _cols, ticks = year_carpet(hourly["self"], months())

        def carpet(ax, c, col):
            ax.grid(False)
            ax.spines["bottom"].set_visible(False)
            im = ax.imshow(grid, aspect="auto", origin="lower", cmap="Blues", interpolation="nearest")
            ax.set_yticks([0, 6, 12, 18, 23], ["0", "6", "12", "18", "23"])
            ax.set_xticks([t for t, _n in ticks], [n for _t, n in ticks])
            ax.set_ylabel(_("hour"), fontsize=7, color=c["ink2"])
            bar = ax.figure.colorbar(im, ax=ax, fraction=0.03, pad=0.01)
            bar.ax.tick_params(labelsize=6, colors=c["muted"], length=0)
            bar.outline.set_visible(False)
            bar.set_label("kW", fontsize=7, color=c["ink2"])
        parts.append(f"<h3>{html.escape(_('Self-consumption hour by hour'))}</h3>")
        parts.append(f"<p align='center'><img src='{ctx.image('carpet', lambda: figure_png(carpet, 7.0, 2.6))}' "
                     "width='620'></p>")
        parts.append(para(_("A column for each day of the year, the hours from the bottom up: the darker, the more "
                            "of the consumption the system covers at that hour."), "caption"))
    return parts


def economics(ctx: Context) -> list[str]:
    from matplotlib.ticker import FuncFormatter
    econ = ctx.get("econ")
    k = econ.kpi
    rows = [(_("Saving, first year"), f"{kwh(k['saving_1'])} €"),
            (_("Sale and incentives, first year"), f"{kwh(k['sale_1'] + k['incentive_1'])} €"),
            (_("Investment"), f"{kwh(k['capex'])} €"), (_("Net present value"), f"{kwh(k['npv'])} €"),
            (_("Internal rate of return"), f"{number(100 * k['irr'], 1)} %" if k["irr"] is not None else "–"),
            (_("Payback"), _("{y} years").format(y=number(k["payback"], 1)) if k["payback"] is not None else "–"),
            (_("Levelised cost"), f"{number(k['lcoe'], 3)} €/kWh" if math.isfinite(k['lcoe']) else _("No production"))]
    parts = [facts(rows)]
    years = list(econ.years.index)
    cum = [-k["capex"]] + [float(v) for v in econ.years.cumulative]

    def cash(ax, c, col):
        ax.plot([0] + years, cum, color=col[0], linewidth=1.6)
        ax.fill_between([0] + years, cum, 0, color=col[0], alpha=0.10, linewidth=0)
        ax.axhline(0, color=c["axis"], linewidth=0.8)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: number(v, 0, grouping=True)))
        ax.set_ylabel("€", fontsize=7, color=c["ink2"])
        ax.set_xlabel(_("year"), fontsize=7, color=c["ink2"])
    parts.append(f"<h3>{html.escape(_('Cumulative cash flow'))}</h3>")
    parts.append(f"<p align='center'><img src='{ctx.image('cash', lambda: figure_png(cash))}' width='620'></p>")
    sizing, storage, sim = ctx.get("sizing"), ctx.get("storage"), ctx.get("sim")
    if sizing is not None and sim is not None:
        parts.append(f"<h3>{html.escape(_('Size of the system and of the storage'))}</h3>")
        parts.append(para(_("The same system smaller and larger, the production and the investment in the same "
                            "proportions; then a generic battery of growing capacity. What changes is what the "
                            "system covers of the consumption and what it is worth.")))
        body = []
        for _i, row in sizing.iterrows():
            here = " ◀" if abs(float(row.kwp) - sim.p_stc_kw) < 1e-6 else ""
            body.append((number(float(row.kwp), 1) + here, f"{number(100 * float(row.self_ratio), 0)} %",
                         f"{number(100 * float(row.self_sufficiency), 0)} %", f"{kwh(float(row.npv))} €"))
        parts.append(table(body, ["kWp", _("Self-consumption"), _("Self-sufficiency"), _("Net present value")],
                           right=(0, 1, 2, 3)))
        if storage is not None:
            frame, generic = storage
            parts.append(para(_("Each capacity is {generic}.").format(generic=generic)))
            parts.append(table([(number(float(r.kwh), 1), f"{number(100 * float(r.self_sufficiency), 0)} %",
                                 f"{kwh(float(r.npv))} €") for _i, r in frame.iterrows()],
                               ["kWh", _("Self-sufficiency"), _("Net present value")], right=(0, 1, 2)))
    return parts


def checks(ctx: Context) -> list[str]:
    from ..checks import area_names
    parts = []
    items = ctx.get("checks") or []
    if items:
        areas = area_names()
        parts.append(table([(Html(mark(MARKS[it.level])), areas.get(it.area, it.area), it.text,
                             Html(f"<span class='muted'>{html.escape(it.source)}</span>")) for it in items],
                           ["", _("Area"), _("Check"), _("Source")], widths=("4%", "16%", "52%", "28%")))
    notes = ctx.get("rules_notes") or []
    if notes:
        parts.append(f"<h3>{html.escape(_('Notes for the technical report'))}</h3>")
        for title, chosen in notes:
            parts.append(f"<h4>{html.escape(title)}</h4>")
            for r, paragraphs in chosen:
                parts += [para(text) for text in paragraphs]
                parts.append(para(f"{r.id} · {r.source()}", "muted"))
    return parts


def methods(ctx: Context) -> list[str]:
    sim, load, econ, pl = ctx.get("sim"), ctx.get("load"), ctx.get("econ"), ctx.get("plant")
    first_plan = next((s.plan for s in getattr(pl, "strings", []) if s.plan is not None), None)
    records = [r for r in (getattr(sim, "record", None), getattr(first_plan, "record", None),
                           getattr(load, "record", None), getattr(econ, "record", None)) if r is not None]
    parts = []
    if records:
        parts.append(records_html(records, lambda name, tex, size: ctx.image(
            "f_" + name, lambda: formula_png(tex, INK, 220, size), 2.2), paper=True))
        defaults = []
        for r in records:
            for st in r.steps:
                for q in st.inputs:
                    if q.source is not None and q.source.kind == "default":
                        defaults.append((st.title, q.label, q.text()))
        if defaults:
            parts.append(f"<h3>{html.escape(_('Values still at their default'))}</h3>")
            parts.append(para(_("Meridiana chose these values because none was given: check them before the final "
                                "design.")))
            parts.append(table(list(dict.fromkeys(defaults)), [_("Step"), _("Value"), _("As used")]))
    return parts


def annexes(ctx: Context) -> list[str]:
    from ..energy.simulate import ModuleSpec
    p = ctx.project
    parts = []
    seen = set()
    for sf in p.subfields:
        if not sf.filled or sf.module in seen:
            continue
        seen.add(sf.module)
        m = ModuleSpec.from_record(p.modules.get(sf.module) or {"power_kw": p.module_of(sf).power_kw})
        parts.append(f"<h3>{html.escape(_('Module: {name}').format(name=f'{m.manufacturer} {m.model}'.strip()))}</h3>")
        rows = [(_("Technology"), m.technology or "–"), (_("Power at STC"), f"{number(m.pmax, 0)} W"),
                ("Vmpp / Impp", f"{number(m.vmp, 2)} V / {number(m.imp, 2)} A"),
                ("Voc / Isc", f"{number(m.voc, 2)} V / {number(m.isc, 2)} A"),
                (_("Temperature coefficients"), f"Pmax {number(m.gamma_pmax, 2)} %/°C, Voc {number(m.beta_voc, 2)} "
                                                f"%/°C, Isc {number(m.alpha_isc, 3)} %/°C"),
                (_("Size"), f"{number(1000 * m.length, 0)} × {number(1000 * m.width, 0)} mm"),
                (_("Cells"), str(m.cells) if m.cells else "–")]
        if m.max_system_voltage:
            rows.append((_("Maximum system voltage"), f"{number(m.max_system_voltage, 0)} V"))
        if m.source is not None:
            rows.append((_("Source"), m.source.label))
        parts.append(facts(rows))
    pl = ctx.get("plant")
    done = set()
    for u in getattr(pl, "units", []) or []:
        if u.name in done:
            continue
        done.add(u.name)
        s = u.spec
        parts.append(f"<h3>{html.escape(_('Inverter: {name}').format(name=u.name))}</h3>")
        rows = [(_("AC power"), f"{number(s.pac / 1000, 1)} kW" if s.pac else "–"),
                (_("European efficiency"), f"{number(100 * s.eta, 1)} %" if s.eta else "–"),
                (_("Maximum DC voltage"), f"{number(s.vdc_max, 0)} V" if s.vdc_max else "–"),
                (_("MPPT window"), f"{number(s.vmppt_min, 0)}-{number(s.vmppt_max, 0)} V"
                 if s.vmppt_min and s.vmppt_max else "–"),
                (_("MPPT inputs"), str(s.mppt_count) if s.mppt_count else "–")]
        if s.imax_per_mppt:
            rows.append((_("Maximum current per input"), " / ".join(f"{number(i, 1)} A" for i in s.imax_per_mppt)))
        if s.source is not None:
            rows.append((_("Source"), s.source.label))
        parts.append(facts(rows))
    shown = set()
    for u in getattr(pl, "units", []) or []:
        ch = u.choice if u.optimized else None
        if ch is None or ch.optimizer.name in shown:
            continue
        shown.add(ch.optimizer.name)
        o = ch.optimizer
        parts.append(f"<h3>{html.escape(_('Power optimizer: {name}').format(name=o.name))}</h3>")
        rows = [(_("Rated input DC power"), f"{number(o.rated_w, 0)} W"),
                (_("Absolute maximum input voltage"), f"{number(o.voc_max, 0)} V"),
                (_("Maximum module Isc"), f"{number(o.isc_max, 1)} A"),
                (_("Maximum output current"), f"{number(o.i_out_max, 1)} A"),
                (_("Weighted efficiency"), f"{number(100 * o.eta, 1)} %"),
                (_("Modules on each"), str(ch.per))]
        if o.i_in_max:
            rows.insert(3, (_("Maximum continuous input current"), f"{number(o.i_in_max, 1)} A"))
        rows.append((_("Source"), o.datasheet))
        parts.append(facts(rows))
    return parts


# the chapters of «Compact»

def overview(ctx: Context) -> list[str]:
    return [facts(_headline(ctx)), _views(ctx), _plan(ctx)]


def monthly(ctx: Context) -> list[str]:
    sim = ctx.get("sim")
    m = sim.monthly
    names = months()
    body = [(names[i], kwh(m.e_ac.iloc[i]), kwh(m.e_ac.iloc[i] / sim.p_stc_kw if sim.p_stc_kw else 0))
            for i in range(min(12, len(m)))]
    body.append((_("Year"), kwh(sim.energy_kwh), kwh(sim.specific_yield)))
    return [table(body, [_("Month"), _("Energy, kWh"), "kWh/kWp"], right=(1, 2), widths=("40%", "30%", "30%")),
            _monthly_chart(ctx)]


def fields(ctx: Context) -> list[str]:
    from ..energy.simulate import ModuleSpec
    from .properties import mounting_names
    results = ctx.get("results") or {}
    p = ctx.project
    mounts = mounting_names()
    rows = []
    for sf in p.subfields:
        r = results.get(sf.id)
        mods = getattr(r, "modules", None) if sf.filled else None
        if not mods:
            continue
        spec = ModuleSpec.from_record(p.modules.get(sf.module) or {"power_kw": p.module_of(sf).power_kw})
        params = sf.layout_params()
        rows.append((sf.name, f"{spec.manufacturer} {spec.model}".strip(), str(len(mods)),
                     number(len(mods) * spec.pmax / 1000, 2), mounts.get(params.mounting, params.mounting),
                     f"{number(r.azimuth, 0)}°", f"{number(r.tilt, 0)}°"))
    return [table(rows, [_("Sub-field"), _("Module"), _("Modules"), "kWp", _("Mounting"), _("Azimuth"), _("Tilt")],
                  right=(2, 3, 5, 6)),
            para(_("Azimuth from the south, positive towards the west (CEI 82-25)."), "caption")]


def electrical(ctx: Context) -> list[str]:
    from ..energy import plant as plants
    pl = ctx.get("plant")
    states = plants.state_names()
    names = {sf.id: sf.name for sf in ctx.project.subfields}
    parts = []
    for u in pl.units:
        mine = sorted((s for s in pl.strings if s.inverter == u.number), key=lambda x: (x.mppt, x.index))
        parts.append(f"<h3>{html.escape(plants.unit_label(u))}: {html.escape(u.name)}</h3>")
        if u.optimized:
            parts.append(para(optimizer_text(u)))
        if not mine:
            parts.append(para(_("No string on it."), "muted"))
            continue
        parts.append(table([(s.label, str(s.mppt), str(len(s.modules)),
                             ", ".join(dict.fromkeys(names.get(sf, sf) for sf, _k, _c in s.modules)),
                             Html(f"{mark(MARKS[{'ok': 'ok', 'check': 'warn', 'fail': 'fail'}[s.state]])} "
                                  f"{html.escape(states[s.state])}")) for s in mine],
                           [_("String"), _("Input"), _("Modules"), _("Sub-field"), _("State")], right=(1, 2)))
    ratio, cut = plants.dcac(pl)
    if ratio:
        text = _("DC/AC ratio {r}").format(r=number(ratio, 2))
        if cut is not None:
            text += "; " + _("energy cut by the inverters {c} % of the year's").format(c=number(100 * cut, 1))
        parts.append(para(text + "."))
    if pl.strings:
        parts.append(_plan(ctx, strings=True))
    return parts


def parameters(ctx: Context) -> list[str]:
    s = ctx.project.site
    rows = [(_("Latitude"), f"{number(s.lat, 5)}°"), (_("Longitude"), f"{number(s.lon, 5)}°")]
    if ctx.settings.get("address", True) and s.address:
        rows.insert(0, (_("Address"), s.address))
    if ctx.get("meteo_text"):
        rows.append((_("Weather"), ctx.get("meteo_text")))
    parts = [facts(rows)]
    sim = ctx.get("sim")
    steps = [st for st in sim.chain if st.change is not None]
    if steps:
        parts.append(f"<h3>{html.escape(_('Losses and gains applied'))}</h3>")
        parts.append(table([(st.label, f"{number(st.change, 1)} %") for st in steps], [_("Step"), _("Change")],
                           right=(1,), widths=("75%", "25%")))
    return parts


BUILDERS: dict = {"summary": summary, "site": site, "layout": layout, "plant": plant, "production": production,
                  "consumption": consumption, "economics": economics, "checks": checks, "methods": methods,
                  "annexes": annexes, "overview": overview, "monthly": monthly, "fields": fields,
                  "electrical": electrical, "parameters": parameters}


# the strings of the plant, as the report has had them since task 16d (step 8)

def _keys_text(keys: list[str]) -> str:
    """The modules of a string in a line: their keys, a run along one row written by its ends («0:0-7, 1:7-0»)."""
    out, i = [], 0
    while i < len(keys):
        row, _sep, slot = keys[i].rpartition(":")
        j, step = i, 0
        while slot.isdigit() and j + 1 < len(keys):
            row2, _sep2, slot2 = keys[j + 1].rpartition(":")
            last = keys[j].rpartition(":")[2]
            if row2 != row or not slot2.isdigit() or abs(int(slot2) - int(last)) != 1 or \
                    (step and int(slot2) - int(last) != step):
                break
            step = int(slot2) - int(last)
            j += 1
        out.append(keys[i] if j == i else f"{keys[i]}-{keys[j].rpartition(':')[2]}")
        i = j + 1
    return ", ".join(out)


def optimizer_text(u) -> str:
    """The power optimizers of an inverter at a fixed string voltage in a sentence, with SolarEdge's table they are
    checked by (task 22)."""
    ch = u.choice
    if ch is None:
        return _("Power optimizers: none of SolarEdge's in the catalogue takes the module.")
    text = ngettext("Power optimizers {name}, {n} module on each", "Power optimizers {name}, {n} modules on each",
                    ch.per).format(name=ch.optimizer.name, n=ch.per)
    if ch.suggested:
        text += " " + _("(proposed by Meridiana)")
    text += "; " + _("strings at the inverter's fixed voltage, {v} V").format(v=number(u.fixed.v_string, 0))
    if ch.rules is not None:
        text += "; " + _("checked by SolarEdge's table, {column} ({source})").format(column=ch.rules.column,
                                                                                   source=ch.rules.source)
    else:
        text += ". " + ch.why
    return text + "."


def _optimized_parts(plant, u) -> list[str]:
    """An inverter with power optimizers in the report: its optimizers, each input (Synergy unit) with its strings,
    their modules, optimizers and power, the checks of each kind of string with their sources, the inverter's own."""
    from ..energy import optimizers
    from ..energy import plant as plant_model
    from .plant_page import input_name
    states = plant_model.state_names()
    parts = [para(optimizer_text(u))]
    rows = []
    plans = []
    for k in range(1, u.inputs + 1):
        slot = plant.inputs.get((u.number, k))
        mine = [plant.strings[i] for i in (slot.strings if slot is not None else [])]
        mods = ", ".join(sorted({str(len(s.modules)) for s in mine}, key=int)) or "–"
        opts = ", ".join(sorted({str(s.plan.optimizers) for s in mine if isinstance(s.plan, optimizers.OptimizedPlan)},
                                key=int)) or "–"
        power = number(sum(s.plan.power_w for s in mine if s.plan is not None) / 1000.0, 2) if mine else "–"
        worst = max((s.state for s in mine), key=("ok", "check", "fail").index) if mine else ""
        state = (Html(f"{mark(MARKS[{'ok': 'ok', 'check': 'warn', 'fail': 'fail'}[worst]])} "
                      f"{html.escape(states[worst])}") if mine else "–")
        rows.append((input_name(u, k), str(len(mine)) if mine else _("free"), mods, opts, power, state))
        for s in mine:
            if s.plan is not None and (len(s.modules), round(s.plan.power_w)) not in [(n, w) for n, w, _p in plans]:
                plans.append((len(s.modules), round(s.plan.power_w), s.plan))
    parts.append(table(rows, [_("Input"), _("Strings"), _("Modules"), _("Optimizers"), "kWp", _("State")],
                       right=(1, 2, 3, 4)))
    for n, _w, p in plans:
        parts.append(para(_("A string of {n} modules, {o} optimizers, {p} kWp").format(
            n=n, o=p.optimizers, p=number(p.power_w / 1000.0, 2)), "muted"))
        parts.append(table([(Html(mark(MARKS.get(c.level, "✔"))), c.label,
                             f"{c.detail} ({c.source})" if c.source else c.detail) for c in p.checks],
                           widths=("4%", "40%", "56%")))
    for c in plant.checks.get(u.number, []):
        source = f" ({html.escape(c.source)})" if c.source else ""
        parts.append(f"<p>{mark(MARKS.get(c.level, '✔'))} {html.escape(c.label)}: {html.escape(c.detail)}{source}</p>")
    return parts


def plant_parts(project, plant) -> list[str]:
    """The strings of the plant: for each inverter its inputs with the strings, the modules in series and the
    state; the checks of each input with their clauses (CEI 64-8/7) and the conditions they were made at; then
    every string with its sub-field and its modules, by inverter and input."""
    from ..energy import plant as plant_model
    states = plant_model.state_names()
    names = {sf.id: sf.name for sf in project.subfields}
    used = sum(1 for slot in plant.inputs.values() if slot.used)
    only_optimizers = all(u.optimized for u in plant.units)
    title = _("Strings of power optimizers (SolarEdge)") if only_optimizers else _("Strings (CEI 64-8/7)")
    parts = [f"<h3>{html.escape(title)}</h3>"]
    head = _("{n} strings on {m} inputs of {u} inverters, named inverter.input.string; {how}.").format(
        n=len(plant.strings), m=used, u=len(plant.units),
        how=(_("proposed by Meridiana: {strategy}").format(
            strategy=plant_model.strategy_names().get(plant.strategy, "").lower()) if plant.auto else
             _("the designer's: drawn on the plan, or proposed by Meridiana when asked and kept")))
    if plant.left:
        head += " " + _("{m} modules are in no string.").format(m=len(plant.left))
    when = (_("Checked at the hottest cell of the typical year, {t} °C, and at {c} °C.").format(
        t=number(plant.t_cell_max, 0), c=number(plant.t_cell_cold, 0)) if plant.year else
        _("Checked at PVsyst's design conditions until the production is computed: {hot} and {warm} °C of cell, "
          "Uoc at {cold} °C.").format(hot=number(plant.t_cell_max, 0), warm=number(plant.t_cell_cold, 0),
                                      cold=number(plant.t_min, 0)))
    if only_optimizers:
        when = _("The strings checked by SolarEdge's tables, the modules' Voc at {t} °C.").format(
            t=number(plant.t_min, 0))
    parts.append(f"<p>{html.escape(head)} {html.escape(when)}</p>")
    for u in plant.units:
        parts.append(f"<h4>{html.escape(plant_model.unit_label(u))}: {html.escape(u.name)}</h4>")
        if u.optimized:
            parts += _optimized_parts(plant, u)
            continue
        rows = []
        for k in range(1, u.inputs + 1):
            slot = plant.inputs.get((u.number, k))
            mine = [plant.strings[i] for i in (slot.strings if slot is not None else [])]
            series = ", ".join(sorted({str(len(s.modules)) for s in mine})) or "–"
            worst = max((s.state for s in mine), key=("ok", "check", "fail").index) if mine else ""
            state = (Html(f"{mark(MARKS[{'ok': 'ok', 'check': 'warn', 'fail': 'fail'}[worst]])} "
                          f"{html.escape(states[worst])}") if mine else "–")
            rows.append((str(k), str(len(mine)) if mine else _("free"), series, state))
        parts.append(table(rows, [_("Input"), _("Strings"), _("Modules in series"), _("State")], right=(0, 1, 2)))
        for k in range(1, u.inputs + 1):
            slot = plant.inputs.get((u.number, k))
            plans = list({id(p): p for p in [plant.strings[i].plan for i in (slot.strings if slot else [])]
                          if p}.values())
            for p in plans:
                parts.append(para(_("Input {k}, {n} modules in series").format(k=k, n=p.n_series), "muted"))
                parts.append(table([(Html(mark(MARKS.get(c.level, "✔"))), c.label, c.detail) for c in p.checks],
                                   widths=("4%", "48%", "48%")))
        for c in plant.checks.get(u.number, []):
            parts.append(f"<p>{mark(MARKS.get(c.level, '✔'))} {html.escape(c.label)}: {html.escape(c.detail)}</p>")
    parts.append(f"<h4>{html.escape(_('The strings on the modules'))}</h4>")
    rows = []
    for s in sorted(plant.strings, key=lambda x: (x.inverter, x.mppt, x.index)):
        sfs = list(dict.fromkeys(sf for sf, _k, _c in s.modules))
        where = ", ".join(names.get(sf, sf) for sf in sfs) or "–"
        rows.append((s.label, where, str(len(s.modules)),
                     Html(f"<span class='muted'>{html.escape(_keys_text([k for _sf, k, _c in s.modules]))}</span>")))
    parts.append(table(rows, [_("String"), _("Sub-field"), _("Modules"), _("Which (row:place)")], right=(2,)))
    return parts
