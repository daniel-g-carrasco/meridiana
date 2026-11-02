"""The chapters of the report (R61, then R314): each a function of the report's context that returns its blocks
(blocks.py; the numbered heading is compose.py's), from the data of the variant. Same chapters, same checks and same
numbers as ever; the look is template.typ's. No Qt here.

The data (`Context.data`) are what the interface hands over (MainWindow._report_data): the year ("sim"), the consumption
("load"), the economics ("econ"), PVGIS ("pvgis"), the plant with its strings ("plant"), the layouts of the sub-fields
("results"), the checks ("checks"), the notes of the rules ("rules_notes"), the sizing and the storage, the weather's
text ("meteo_text"). A chapter is called only when its data are there (reports.plan).

Every number says where it comes from: with the register among the chapters, the code of its line in a column of the
table or at the end of a card; without it, a short line under the table with the source in words."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from dataclasses import dataclass, field

from .. import reports
from ..energy.pedigree import kind_names, limits
from ..fields import mounting_names
from ..i18n import _, ngettext, number
from . import blocks as B
from . import figures
from .blocks import bold, facts, floating, keep, muted, para, section, sub, table, two
from .register import Register

MARKS = {"ok": "ok", "check": "warn", "fail": "fail"}       # a string's state, the mark it has


@dataclass
class Picture:
    """A 3D view the interface can make: its caption, and what draws it (PNG bytes)."""
    caption: str
    make: Callable


@dataclass
class Context:
    project: object
    data: dict
    image: Callable                  # image(name, make) -> the name of the image in the report's folder
    settings: dict
    register: Register
    chosen: tuple = ()               # the ids of the chapters written, in order: a chapter leaves out what another has
    pictures: dict = field(default_factory=dict)     # view id -> Picture
    accent: str = "#1c6e8c"
    chapter: int = 0                 # the number of the chapter being written
    figures: int = 0                 # its figures so far

    def get(self, key: str):
        return self.data.get(key)

    def has_chapter(self, cid: str) -> bool:
        return cid in self.chosen

    def caption(self, text: str) -> list:
        """A figure's caption, its number by chapter («Figure 3.1.») in bold: the text can refer to it."""
        self.figures += 1
        n = f"{self.chapter}.{self.figures}" if self.chapter else str(self.figures)
        head, _sep, tail = _("Figure {n}. {caption}").format(n=n, caption="\0").partition("\0")
        return [bold(head.strip()), f" {text}{tail}"]

    def view(self, vid: str) -> str:
        """The image of a 3D view, "" where it cannot be made."""
        picture = self.pictures.get(vid)
        if picture is None:
            return ""
        return self.image(f"view_{vid}.png", picture.make)

    def tabled(self, rows, head=None, *, right=(), widths=None, mark_row=None, group: str = "", where: str = "") -> list:
        """A table with its source: `where` the key of a step or the source in words; with the register, each row a
        code in a last column, without it a line under the table. Without `group`, the table as it is."""
        if not group:
            return [table(rows, head, right, widths, mark_row)]
        if not self.register.active:
            words = self.register.words(where)
            return [table(rows, head, right, widths, mark_row),
                    para(_("Source: {what}.").format(what=words), "source") if words else None]
        reg = self.register
        names = [B.plain(h) for h in head] if head else []
        codes, prefix = [], ""
        for row in rows:
            if isinstance(row, str):
                prefix = row
                continue
            cells = [B.plain(c) for c in row]
            first = f"{names[0]}: {cells[0]}" if names and 0 in right else cells[0]     # a number names its column
            what = f"{prefix}: {first}" if prefix else first
            value = " · ".join(f"{names[i]}: {c}" if i < len(names) else c for i, c in enumerate(cells) if i > 0 and c)
            codes.append(reg.group(group).add(what, value, reg.words(where)))
        return [table(rows, head, right, widths, mark_row, codes, _("Source"))]

    def carded(self, rows, *, group: str, strong: bool = False, ratio=(5, 6)) -> list:
        """A card of label and value, each row (label, value, source): the source the key of a step or words, None
        where the row needs none; with the register, its code beside the value, else a line under the card."""
        reg = self.register
        if reg.active:
            out = []
            for r in rows:
                where = r[2] if len(r) > 2 else ""
                out.append((r[0], r[1], reg.code(where, group, r[0], r[1]) if where else ""))
            return [facts(out, strong, ratio)]
        words = list(dict.fromkeys(reg.words(r[2]) for r in rows if len(r) > 2 and r[2]))
        return [facts([(r[0], r[1]) for r in rows], strong, ratio),
                para(_("Source: {what}.").format(what="; ".join(words)), "source") if words else None]

    def source_of(self, *keys: str) -> dict | None:
        """A line that names the sources of a block: the codes with the register, the steps' titles without it."""
        reg = self.register
        found = [reg.step(k) for k in keys]
        found = [f for f in found if f is not None]
        if not found:
            return None
        names = [f[0] if reg.active else f[1] for f in found]
        return para(_("Source: {what}.").format(what=", ".join(dict.fromkeys(names))), "source")


def kwh(v) -> str:
    return number(float(v), 0, grouping=True)


def months() -> list[str]:
    return [_("Jan"), _("Feb"), _("Mar"), _("Apr"), _("May"), _("Jun"), _("Jul"), _("Aug"), _("Sep"), _("Oct"),
            _("Nov"), _("Dec")]


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


def _payback(k: dict) -> str:
    return _("{y} years").format(y=number(k["payback"], 1)) if k["payback"] is not None else "–"


def _plant_rows(ctx: Context) -> list[tuple]:
    """What the system is made of, each with its source."""
    sim, plant = ctx.get("sim"), ctx.get("plant")
    rows = [(_("Power at STC"), f"{number(sim.p_stc_kw, 2)} kWp", "module")]
    mods = _modules(ctx.project, ctx.get("results") or {})
    if mods:
        rows.append((_("Modules"), "; ".join(f"{n} × {name}" for name, n, _p in mods), "module"))
    if plant is not None and getattr(plant, "strings", None):
        rows.append((_("Strings"), str(len(plant.strings)), "uocmax"))
    invs = _inverters(plant)
    if invs:
        rows.append((_("Inverters"), "; ".join(f"{n} × {name}" for name, n, _p in invs), "inverter"))
    rows.append((_("AC power"), f"{number(sim.p_ac_kw, 1)} kW", "inverter"))
    if plant is not None and plant.units:
        from ..energy import plant as plants
        ratio, _cut = plants.dcac(plant)
        if ratio:
            rows.append((_("Ratio DC/AC"), number(ratio, 2), "inverter"))
    return rows


def _yield_rows(ctx: Context) -> list[tuple]:
    sim = ctx.get("sim")
    return [(_("Energy a year (typical year)"), f"{kwh(sim.energy_kwh)} kWh", "ac"),
            (_("Specific yield"), f"{kwh(sim.specific_yield)} kWh/kWp", "ac"),
            (_("Performance ratio"), f"{number(100 * sim.pr, 1)} %", "pr")]


def _money_rows(ctx: Context) -> list[tuple]:
    econ = ctx.get("econ")
    if econ is None:
        return []
    k = econ.kpi
    return [(_("Self-consumption"), f"{number(100 * k['self_ratio'], 0)} %", "balance"),
            (_("Self-sufficiency"), f"{number(100 * k['self_sufficiency'], 0)} %", "balance"),
            (_("Saving, first year"), f"{kwh(k['saving_1'])} €", "saving"),
            (_("Payback"), _payback(k), "npv")]


def headline(ctx: Context) -> list[tuple[str, str]]:
    """The headline numbers, each once: what the scheda says and what a test reads."""
    return [(r[0], r[1]) for r in _plant_rows(ctx) + _yield_rows(ctx) + _money_rows(ctx)]


def tiles(ctx: Context, details: bool = True) -> dict:
    """The four numbers at the head of the cover and of the summary."""
    sim, econ = ctx.get("sim"), ctx.get("econ")
    mods = _modules(ctx.project, ctx.get("results") or {})
    invs = _inverters(ctx.get("plant"))
    made = ", ".join(f"{n} × {name}" for name, n, _p in mods + invs) if details else ""
    items = [{"n": number(sim.p_stc_kw, 2), "u": "kWp", "l": _("Power at STC"), "s": made, "c": "acc"},
             {"n": kwh(sim.energy_kwh), "u": "kWh", "l": _("Energy a year (typical year)"),
              "s": f"{kwh(sim.specific_yield)} kWh/kWp" if details else "", "c": "sun"},
             {"n": number(100 * sim.pr, 1), "u": "%", "l": _("Performance ratio"),
              "s": _("from the sun to the grid") if details else "", "c": "sun"}]
    if econ is not None and econ.kpi["payback"] is not None:
        k = econ.kpi
        items.append({"n": number(k["payback"], 1), "u": _("years"), "l": _("Payback"),
                      "s": (_("investment {c} €, saving {s} € in the first year").format(
                          c=kwh(k["capex"]), s=kwh(k["saving_1"])) if details else ""), "c": "leaf"})
    else:
        items.append({"n": kwh(sim.specific_yield), "u": "kWh/kWp", "l": _("Specific yield"),
                      "s": _("for each kWp installed") if details else "", "c": "leaf"})
    return {"k": "tiles", "items": items}


def plan_block(ctx: Context, strings: bool = False) -> dict | None:
    """The plan at the whole width, on its card with its legend under it, floating: the text after it fills the page
    it would have left half empty («ampio, come quello in C»)."""
    results = ctx.get("results") or {}
    if not any(getattr(r, "modules", None) for r in results.values()):
        return None
    plant = ctx.get("plant") if strings else None
    name = "plan_strings.svg" if strings else "plan.svg"
    colours = {"module": ctx.accent}
    image = ctx.image(name, lambda: figures.plan_svg(ctx.project, results, plant, colours=colours))
    caption = (_("The strings on the modules: each in a hue of its own, from its label along its modules.") if strings
               else _("Plan of the modules laid: buildings, sub-fields (dashed), exclusions; north up."))
    n = sum(len(getattr(results.get(sf.id), "modules", None) or []) for sf in ctx.project.subfields)
    chips = [{"t": _("Modules, {n}").format(n=number(n, 0, grouping=True)),
              "fill": ctx.accent if not strings else figures.STRING_HUES[0]},
             {"t": _("Buildings"), "fill": figures.PLAN["building"], "edge": figures.PLAN["building_edge"]},
             {"t": _("Sub-fields"), "fill": "#ffffff", "edge": figures.PLAN["subfield"], "dash": True}]
    if ctx.project.exclusions:
        chips.append({"t": _("Exclusions"), "fill": figures.PLAN["exclusion"], "edge": figures.PLAN["exclusion_edge"]})
    return floating(section(_("The strings on the modules") if strings else _("Plan of the modules"), "acc"),
                    B.figure(image, ctx.caption(caption), max_h=175.0, tint=True, inset=2.5, chips=chips))


def view_block(ctx: Context, vid: str) -> dict | None:
    """A 3D view at the whole width; floating, as the plan."""
    picture = ctx.pictures.get(vid)
    if picture is None:
        return None
    return floating(B.figure(ctx.view(vid), ctx.caption(picture.caption), max_h=118.0))


def monthly_bars(ctx: Context, h: float = 34.0) -> dict:
    """The energy month by month as full bars with their values, Meridiana beside PVGIS when it is there."""
    sim, pv = ctx.get("sim"), ctx.get("pvgis")
    mine = [float(v) for v in sim.monthly.e_ac.to_numpy()]
    top = max(mine) if mine else 0.0
    if top >= 1000:
        texts = [number(v / 1000, 1) for v in mine]
    else:
        texts = [kwh(v) for v in mine]
    series = [{"name": "Meridiana", "color": "sun", "values": mine, "texts": texts if pv is None else None}]
    if pv is not None:
        series.append({"name": "PVGIS", "color": "acc", "values": [float(v) for v in pv.monthly_kwh], "texts": None})
    return {"k": "bars", "labels": months()[:len(mine)], "series": series, "h": h, "thousands": top >= 1000}


def checks_badge(ctx: Context) -> dict | None:
    """How the checks came out, in a pill: green when nothing is left, amber when something is to look at, red when
    something fails."""
    items = ctx.get("checks") or []
    if not items:
        return None
    fails = sum(1 for it in items if it.level == "fail")
    warns = sum(1 for it in items if it.level == "warn")
    oks = sum(1 for it in items if it.level == "ok")
    level = "fail" if fails else "warn" if warns else "ok"
    if fails or warns:
        text = _("{ok} met, {warn} to look at, {fail} not met").format(ok=oks, warn=warns, fail=fails)
    else:
        text = ngettext("{ok} check met", "{ok} checks met", oks).format(ok=oks)
    return {"k": "badge", "level": level, "t": text}


def checks_note(ctx: Context) -> list:
    """Under the pill: what is not met or is to be looked at, in words, and where the rest is."""
    items = ctx.get("checks") or []
    out = []
    open_items = list({(it.level, it.text): it for it in items if it.level in ("fail", "warn")}.values())
    for it in open_items[:3]:
        out.append(para([B.mark(it.level), " ", it.text], "muted"))
    if len(open_items) > 3:
        out.append(para(_("and {n} more.").format(n=len(open_items) - 3), "muted"))
    if ctx.has_chapter("checks"):
        n = ctx.chosen.index("checks") + 1
        out.append(para(_("Every check, with its source: chapter {n}.").format(n=n), "source"))
    return out


def _sheet(ctx: Context) -> list:
    """The page that reads on its own: the four numbers, the energy, how it is made, what it yields, the checks, and a
    3D view with what the page leaves."""
    sim = ctx.get("sim")
    n_sf = sum(1 for sf in ctx.project.subfields if sf.filled and getattr((ctx.get("results") or {}).get(sf.id),
                                                                          "modules", None))
    text = ngettext("A system of {kwp} kWp on {n} sub-field: in the typical year it produces {e} kWh, {y} kWh for "
                    "each kWp.", "A system of {kwp} kWp on {n} sub-fields: in the typical year it produces {e} kWh, "
                    "{y} kWh for each kWp.", max(1, n_sf)).format(
        kwp=number(sim.p_stc_kw, 1), n=max(1, n_sf), e=kwh(sim.energy_kwh), y=kwh(sim.specific_yield))
    made = [(r[0], r[1]) for r in _plant_rows(ctx)]
    energy = [(r[0], r[1]) for r in _yield_rows(ctx)]
    bars = monthly_bars(ctx)
    left = [section(_("Energy month by month"), "sun"), bars]
    if bars.get("thousands"):
        left.append(para(_("In MWh."), "source"))
    left.append(facts(energy, strong=True))
    left.append(ctx.source_of("ac", "pr"))
    right = [section(_("How it is made"), "acc"), facts(made), ctx.source_of("module", "uocmax", "inverter")]
    money = _money_rows(ctx)
    below_left = []
    if money:
        below_left = [section(_("What it yields"), "leaf"), facts([(r[0], r[1]) for r in money]),
                      ctx.source_of("balance", "saving", "npv")]
    below_right = [section(_("Checks"), "slate"), checks_badge(ctx), *checks_note(ctx)] if ctx.get("checks") else []
    parts = [tiles(ctx), para(text), two(left, right)]
    if below_left or below_right:
        parts.append(two(below_left, below_right) if below_left and below_right
                     else keep(*(below_left or below_right)))
    return parts


def _sheet_picture(ctx: Context) -> list:
    """The 3D view that closes the sheet, as large as the page lets it be; the cover has the other one."""
    views = list(ctx.pictures)
    if views:
        vid = views[-1]
        return [{"k": "fill_figure", "image": ctx.view(vid), "caption": ctx.caption(ctx.pictures[vid].caption)},
                {"k": "pagebreak"}]
    return [{"k": "pagebreak"}]


# the chapters of «Complete»

def summary(ctx: Context) -> list:
    parts = _sheet(ctx) + _sheet_picture(ctx)
    if not ctx.has_chapter("layout"):
        parts.append(plan_block(ctx))                 # the layout has the plan: once in the report
    return parts


def site(ctx: Context) -> list:
    s = ctx.project.site
    place = _("Project's data")
    rows = [(_("Latitude"), f"{number(s.lat, 5)}°", place), (_("Longitude"), f"{number(s.lon, 5)}°", place)]
    if ctx.settings.get("address", True) and s.address:
        rows.insert(0, (_("Address"), s.address, place))
    sim = ctx.get("sim")
    if ctx.get("meteo_text"):
        rows.append((_("Weather"), ctx.get("meteo_text"), _("Weather")))
    pv = ctx.get("pvgis")
    if pv is not None:
        rows.append((_("Second opinion"), pv.source.label, pv.source.label))
    parts = ctx.carded(rows, group=_("Site and climate data"), ratio=(2, 7))
    if sim is not None:
        m = sim.monthly
        names = months()
        body = [(names[i], kwh(m.ghi.iloc[i]), kwh(m.dhi.iloc[i]), kwh(m.poa.iloc[i]), number(m.temp_air.iloc[i], 1))
                for i in range(min(12, len(m)))]
        body.append((_("Year"), kwh(m.ghi.sum()), kwh(m.dhi.sum()), kwh(m.poa.sum()), number(m.temp_air.mean(), 1)))
        parts.append(section(_("Irradiation and temperature month by month"), "sun"))
        parts += ctx.tabled(body, [_("Month"), _("Horizontal, kWh/m²"), _("Diffuse, kWh/m²"),
                                   _("On the plane, kWh/m²"), _("Air, °C")], right=(1, 2, 3, 4), mark_row=len(body) - 1,
                            group=_("Irradiation and temperature month by month"), where="poa")
        parts.append(para(_("On the plane: the irradiation on the modules' plane, the arrays together, weighted by "
                            "their power."), "caption"))
    return parts


def layout(ctx: Context) -> list:
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
                     mounts.get(params.mounting, params.mounting), number(r.azimuth, 0), number(r.tilt, 0),
                     number(r.pitch, 2) if r.pitch else "–"))
        if r.pitch:
            rules.append(_("{name}: rows {pitch} m apart, {gap} m free behind each, the sun above {angle}° clears "
                           "them (limit angle, CEI 82-25/3, Fig. 1).").format(
                name=sf.name, pitch=number(r.pitch, 2), gap=number(r.clearance, 2), angle=number(r.limit_angle, 1)))
    parts = ctx.tabled(rows, [_("Sub-field"), _("On"), _("Area, m²"), _("Modules"), "kWp", _("Mounting"),
                              f"{_('Azimuth')}, °", f"{_('Tilt')}, °", _("Pitch, m")], right=(2, 3, 4, 6, 7, 8),
                       widths=("14%", "14%", "8%", "9%", "8%", "13%", "10%", "15%", "9%"),
                       group=_("Roofs and layout"), where=_("the layout of the project"))
    parts.append(para(_("Azimuth from the south, positive towards the west (CEI 82-25); area as drawn, in plan."),
                      "caption"))
    if rules:
        parts.append(section(_("Distances between the rows"), "acc"))
        parts += [para(t) for t in rules]
    if p.exclusions:
        from collections import Counter

        from .. import model
        kinds = Counter(e.kind for e in p.exclusions)
        names = model.exclusion_kind_names() if hasattr(model, "exclusion_kind_names") else {}
        parts.append(section(_("Exclusions"), "slate"))
        parts.append(para("; ".join(f"{names.get(k, k)}: {n}" for k, n in sorted(kinds.items()))))
    parts.append(plan_block(ctx))                     # here, once in the report, at its full size
    views = list(ctx.pictures)
    if views:
        parts.append(view_block(ctx, views[0]))
        if not ctx.has_chapter("summary") and len(views) > 1:
            parts.append(view_block(ctx, views[1]))
    return parts


def _dcac_text(pl) -> str:
    from ..energy import plant as plants
    ratio, cut = plants.dcac(pl)
    if not ratio:
        return ""
    text = _("DC/AC ratio {r}").format(r=number(ratio, 2))
    if cut is not None:
        text += "; " + _("energy cut by the inverters {c} % of the year's").format(c=number(100 * cut, 1))
    return text + "."


def plant(ctx: Context) -> list:
    pl = ctx.get("plant")
    parts = []
    invs = _inverters(pl)
    if invs:
        rows = [(name, str(n), number(ac, 1)) for name, n, ac in invs]
        parts += ctx.tabled(rows, [_("Inverter"), _("How many"), _("AC kW")], right=(1, 2),
                            group=_("Electrical system"), where="inverter")
        text = _dcac_text(pl)
        if text:
            parts.append(para(text))
    if pl.strings:
        parts.append(plan_block(ctx, strings=True))
        parts += plant_parts(ctx.project, pl, ctx)
    return parts


# short names of the steps under the bars (the table beneath has the whole names)
def _chain_short() -> dict:
    return {"ghi": _("horizontal"), "poa": _("on the plane"), "far": _("horizon"), "near": _("rows, obstacles"),
            "iam": _("reflection"), "soiling": _("soiling"), "nominal": _("at STC"),
            "irradiance_level": _("low light"), "temperature": _("temperature"), "quality": _("quality"),
            "lid": "LID", "mismatch": "mismatch", "electrical": _("shade, strings"), "dc_wiring": _("DC cables"),
            "inverter": "inverter", "clipping": "clipping", "ac_wiring": _("AC cables"),
            "unavailability": _("unavailable")}


CHAIN_STEP = {"poa": "poa", "far": "poa", "near": "rows", "iam": "iam", "soiling": "soiling",
              "nominal": "module", "irradiance_level": "module", "temperature": "temperature", "quality": "array",
              "lid": "array", "mismatch": "array", "electrical": "electrical_network", "dc_wiring": "array",
              "inverter": "inverter", "clipping": "inverter", "ac_wiring": "ac", "unavailability": "ac"}
FULL_SCALE = 15.0            # a step of this percentage draws a full bar


def _chain_bars(ctx: Context) -> dict | None:
    """From the sun to the grid, as in sketch V1: the amber bars the energy upstream and downstream, each loss in red and
    each gain in green against the step before."""
    sim = ctx.get("sim")
    chain = sim.chain
    if not chain:
        return None
    short = _chain_short()
    irradiance = [s for s in chain if s.kind == "irradiance"]
    energy = [s for s in chain if s.kind == "energy"]
    top = max((s.value for s in irradiance), default=0.0) or 1.0
    bridge = irradiance[-1].value / top if irradiance else 1.0           # the energy's start is where the sun's ends
    start = next((s.value for s in energy), 0.0) or 1.0
    items = []
    for s in chain:
        if s.change is None or s.key == "poa":
            # the totals, and the irradiation on the plane: a total too, its gain on the horizontal written above it
            unit = "kWh/m²" if s.kind == "irradiance" else "kWh"
            h = s.value / top if s.kind == "irradiance" else s.value / start * bridge
            items.append({"t": "total", "h": h, "text": f"{kwh(s.value)} {unit}", "label": short.get(s.key, s.label),
                          "extra": f"{number(s.change, 1, sign=True)} %" if s.change is not None else ""})
        else:
            kind = "gain" if s.change > 0.05 else "loss" if s.change < -0.05 else "zero"
            items.append({"t": kind, "h": min(abs(s.change) / FULL_SCALE, 1.0),
                          "text": f"{number(s.change, 1, sign=kind != 'zero')} %", "label": short.get(s.key, s.label)})
    if energy:
        last = energy[-1]
        items.append({"t": "total", "h": last.value / start * bridge, "text": f"{kwh(last.value)} kWh",
                      "label": _("delivered")})
    return {"k": "waterfall", "items": items, "h": 46.0}


def production(ctx: Context) -> list:
    sim, pv = ctx.get("sim"), ctx.get("pvgis")
    parts = []
    bars = _chain_bars(ctx)
    steps = [s for s in sim.chain if s.change is not None]
    if bars is not None and steps:
        parts.append(section(_("From the sun to the grid"), "sun"))
        parts.append(para(_("Each step against the one before: the irradiation on the plane against the horizontal, "
                            "then the losses down to the energy delivered.")))
        parts.append(bars)
        parts.append(para(ctx.caption(_("From the sun to the grid: each step as a percentage of the one before.") + " "
                                      + _("A red or green bar at full height is {p} %; the amber ones are the energy, "
                                          "in the unit written on them.").format(p=number(FULL_SCALE, 0))), "caption"))
    rows = [(_("Energy a year (typical year)"), f"{kwh(sim.energy_kwh)} kWh", "ac"),
            (_("Specific yield"), f"{kwh(sim.specific_yield)} kWh/kWp", "ac"),
            (_("Performance ratio"), f"{number(100 * sim.pr, 1)} %", "pr")]
    if pv is not None:
        rows.append((_("PVGIS, second opinion"), f"{kwh(pv.yearly_kwh)} kWh ({pv.source.label})", pv.source.label))
    m = sim.monthly
    names = months()
    body = []
    for i in range(min(12, len(m))):
        row = [names[i], kwh(m.poa.iloc[i]), kwh(m.e_ac.iloc[i]), kwh(m.e_ac.iloc[i] / sim.p_stc_kw if sim.p_stc_kw else 0),
               number(100 * m.pr.iloc[i], 1)]
        if pv is not None:
            row.append(kwh(pv.monthly_kwh[i]))
        body.append(row)
    total = [_("Year"), kwh(m.poa.sum()), kwh(sim.energy_kwh), kwh(sim.specific_yield), number(100 * sim.pr, 1)]
    if pv is not None:
        total.append(kwh(pv.yearly_kwh))
    body.append(total)
    head = [_("Month"), _("On the plane, kWh/m²"), _("Energy, kWh"), "kWh/kWp", "PR, %"] + (["PVGIS, kWh"] if pv else [])
    parts.append(section(_("Month by month"), "sun"))
    parts += ctx.tabled(body, head, right=tuple(range(1, len(head))), mark_row=len(body) - 1,
                        group=_("Energy yield") + ", " + _("Month by month"), where="ac")
    side = [section(_("Energy yield"), "sun")] + ctx.carded(rows, group=_("Energy yield"), strong=True)
    chart = [monthly_bars(ctx, 30.0)]
    if chart[0].get("thousands"):
        chart.append(para(_("In MWh."), "source"))
    chart.append(para(ctx.caption(_("Energy delivered month by month, Meridiana beside PVGIS.") if pv is not None
                                  else _("Energy delivered month by month.")), "caption"))
    parts.append(two(side, chart, (5, 6)))
    if steps:
        parts.append(sub(_("Losses and gains applied")))
        parts += ctx.tabled([(s.label, number(s.change, 1)) for s in steps], [_("Step"), f"{_('Change')}, %"],
                            right=(1,), widths=("80%", "20%"), group=_("From the sun to the grid"),
                            where=CHAIN_STEP.get("ac", "ac"))
    inverters = getattr(sim, "inverters", ())
    if inverters:
        parts.append(section(_("Production by inverter"), "acc"))
        parts.append(para(_("Each inverter is calculated separately, including its power limit. AC energy includes "
                            "wiring losses and unavailability; the hourly register keeps the individual results.")))
        parts += ctx.tabled([(f"{inv['number']} · {inv['name']}", number(inv["p_ac_kw"], 2),
                              kwh(inv["dc_kwh"]), kwh(inv["clipping_kwh"]), kwh(inv["ac_kwh"]))
                             for inv in inverters],
                            [_("Inverter"), _("AC rating, kW"), _("DC energy, kWh"),
                             _("Clipping, kWh"), _("AC energy, kWh")], right=(1, 2, 3, 4),
                            widths=("36%", "15%", "17%", "15%", "17%"), group=_("Production by inverter"), where="inverter")
    shaded = [a for a in sim.arrays if (a.get("row_shading") or 0) + (a.get("obstacle_shading") or 0) > 0.0005]
    if shaded:
        parts.append(section(_("Shading"), "sun"))
        parts += ctx.tabled([(a["name"], number(100 * (a.get('row_shading') or 0), 1),
                              number(100 * (a.get('obstacle_shading') or 0), 1),
                              number(100 * (a.get('rows_electrical') or 0), 1)) for a in sim.arrays],
                            [_("Array"), f"{_('Rows, linear')}, %", f"{_('Obstacles, linear')}, %",
                             f"{_('Rows, electrical')}, %"], right=(1, 2, 3), group=_("Shading"), where="rows")
    return parts


def consumption(ctx: Context) -> list:
    load, econ = ctx.get("load"), ctx.get("econ")
    by = load.by_band()
    rows = [(_("Consumption a year"), f"{kwh(load.annual_kwh)} kWh ({load.basis})", "load")]
    rows += [(b, f"{kwh(by[b])} kWh", "load") for b in ("F1", "F2", "F3")]
    if econ is not None:
        k = econ.kpi
        rows += [(_("Self-consumption"), f"{number(100 * k['self_ratio'], 0)} % ({kwh(k['self'])} kWh)", "balance"),
                 (_("Self-sufficiency"), f"{number(100 * k['self_sufficiency'], 0)} %", "balance"),
                 (_("Energy fed in"), f"{kwh(k['export'])} kWh", "balance")]
    parts = ctx.carded(rows, group=_("Consumption and balance"), ratio=(1, 1))
    if econ is not None and len(getattr(econ, "monthly", [])) == 12:
        mo = econ.monthly
        names = months()
        body = [(names[i], kwh(mo["production"].iloc[i]), kwh(mo["consumption"].iloc[i]), kwh(mo["self"].iloc[i]),
                 kwh(mo["export"].iloc[i]), kwh(mo["import"].iloc[i])) for i in range(12)]
        body.append((_("Year"), kwh(mo["production"].sum()), kwh(mo["consumption"].sum()), kwh(mo["self"].sum()),
                     kwh(mo["export"].sum()), kwh(mo["import"].sum())))
        parts.append(section(_("Month by month"), "leaf"))
        parts += ctx.tabled(body, [_("Month"), f"{_('Produced')}, kWh", f"{_('Consumed')}, kWh",
                                   f"{_('Self-consumed')}, kWh", f"{_('Fed in')}, kWh", f"{_('Drawn')}, kWh"],
                            right=(1, 2, 3, 4, 5), mark_row=12, group=_("Consumption and balance") + ", " + _("Month by month"),
                            where="balance")
        parts.append(para(_("Self-consumed: the energy produced and used on site, at the same hour."), "caption"))
        top = max(float(mo["production"].max()), float(mo["consumption"].max()), 1e-9)
        parts.append(keep({"k": "balance", "labels": names, "h": 34.0,
                           "first": [float(v) / top for v in mo["production"]],
                           "second": [float(v) / top for v in mo["consumption"]],
                           "line": [float(v) / top for v in mo["self"]],
                           "names": [_("Produced"), _("Consumed"), _("Self-consumed")]},
                          para(ctx.caption(_("Production and consumption month by month, with the energy "
                                             "self-consumed.")), "caption")))
    hourly = getattr(econ, "hourly", None) if econ is not None else None
    if hourly is not None and "self" in getattr(hourly, "columns", []):
        from ..energy.register import year_carpet
        grid, _cols, ticks = year_carpet(hourly["self"], months())
        days = max(1, grid.shape[1])
        image = ctx.image("carpet.png", lambda: figures.carpet_png(grid, ctx.accent))
        parts.append(keep(section(_("Self-consumption hour by hour"), "leaf"),
                          {"k": "carpet", "image": image, "h": 34.0, "unit": "kW",
                           "top": f"{number(float(grid.max()), 0)} kW",
                           "months": [{"at": t / days, "t": n} for t, n in ticks],
                           "hours": [{"at": h / 24, "t": str(h)} for h in (0, 6, 12, 18, 23)]},
                          para(ctx.caption(_("A column for each day of the year, the hours from the bottom up: the "
                                             "darker, the more of the consumption the system covers at that hour.")),
                               "caption")))
    return parts


def _cash_chart(econ) -> dict:
    k = econ.kpi
    years = [0] + [int(y) for y in econ.years.index]
    cum = [-float(k["capex"])] + [float(v) for v in econ.years.cumulative]
    low, high = min(0.0, *cum), max(0.0, *cum)
    span = (high - low) or 1.0
    last = years[-1] or 1

    def y(v: float) -> float:
        return (v - low) / span
    points = [(x / last, y(v)) for x, v in zip(years, cum, strict=True)]
    labels = sorted({round(low, 2), 0.0, round(high, 2)})
    return {"k": "cash", "h": 36.0, "zero": y(0.0), "points": points,
            "y": [{"at": y(v), "t": f"{kwh(v)} €"} for v in labels],
            "x": [{"at": x / last, "t": str(x)} for x in years if x % 5 == 0 or x == last]}


def economics(ctx: Context) -> list:
    econ = ctx.get("econ")
    k = econ.kpi
    rows = [(_("Saving, first year"), f"{kwh(k['saving_1'])} €", "saving"),
            (_("Sale and incentives, first year"), f"{kwh(k['sale_1'] + k['incentive_1'])} €", "sale"),
            (_("Investment"), f"{kwh(k['capex'])} €", "npv"), (_("Net present value"), f"{kwh(k['npv'])} €", "npv"),
            (_("Internal rate of return"), f"{number(100 * k['irr'], 1)} %" if k["irr"] is not None else "–", "irr"),
            (_("Payback"), _payback(k), "npv"),
            (_("Levelised cost"), f"{number(k['lcoe'], 3)} €/kWh" if math.isfinite(k['lcoe']) else _("No production"),
             "lcoe")]
    left = ctx.carded(rows, group=_("Economics"), strong=True)
    right = [section(_("Cumulative cash flow"), "leaf"), _cash_chart(econ),
             para(ctx.caption(_("Cumulative cash flow over the years: the investment at year 0, the payback where the "
                                "line crosses zero.")), "caption")]
    parts = [two(left, right, (4, 5))]
    sizing, storage, sim = ctx.get("sizing"), ctx.get("storage"), ctx.get("sim")
    if sizing is not None and sim is not None:
        parts.append(section(_("Size of the system and of the storage"), "leaf"))
        parts.append(para(_("The same system smaller and larger, the production and the investment in the same "
                            "proportions; then a generic battery of growing capacity. What changes is what the "
                            "system covers of the consumption and what it is worth.")))
        body, here = [], None
        for _i, row in sizing.iterrows():
            if abs(float(row.kwp) - sim.p_stc_kw) < 1e-6:
                here = len(body)
            body.append((number(float(row.kwp), 1), number(100 * float(row.self_ratio), 0),
                         number(100 * float(row.self_sufficiency), 0), kwh(float(row.npv))))
        first = ctx.tabled(body, ["kWp", f"{_('Self-consumption')}, %", f"{_('Self-sufficiency')}, %",
                                  f"{_('Net present value')}, €"], right=(0, 1, 2, 3), mark_row=here,
                           group=_("Size of the system and of the storage"), where="npv")
        first.append(para(_("The highlighted row is this project."), "caption"))
        if storage is not None:
            frame, generic = storage
            second = [para(_("Each capacity is {generic}.").format(generic=generic), "muted")]
            second += ctx.tabled([(number(float(r.kwh), 1), number(100 * float(r.self_sufficiency), 0),
                                   kwh(float(r.npv))) for _i, r in frame.iterrows()],
                                 [f"{_('Storage')}, kWh", f"{_('Self-sufficiency')}, %",
                                  f"{_('Net present value')}, €"], right=(0, 1, 2),
                                 group=_("Size of the system and of the storage"), where="npv")
            parts.append(two(first, second))
        else:
            parts += first
    return parts


def checks(ctx: Context) -> list:
    from ..checks import area_names
    parts = [checks_badge(ctx)]
    items = ctx.get("checks") or []
    if items:
        # by area, each area a group row: the area's name was repeated on every row (R291)
        areas = area_names()
        order = list(areas) + sorted({it.area for it in items} - set(areas))
        rows: list = []
        for area in order:
            mine = [it for it in items if it.area == area]
            if mine:
                rows.append(areas.get(area, area))
                rows += [(B.mark(it.level), it.text, muted(it.source)) for it in mine]
        parts.append(table(rows, ["", _("Check"), _("Source")], widths=("4%", "64%", "32%")))
    notes = ctx.get("rules_notes") or []
    if notes:
        parts.append(section(_("Notes for the technical report"), "slate"))
        for title, chosen in notes:
            parts.append(sub(title))
            for r, paragraphs in chosen:
                parts += [para(text) for text in paragraphs]
                parts.append(para(f"{r.id} · {r.source()}", "muted"))
    return parts


def _formula_name(tex: str, size: float) -> str:
    return "f_" + hashlib.sha1(f"{size}|{tex}".encode()).hexdigest()[:14] + ".svg"


def _records_blocks(ctx: Context, records: list) -> list:
    """The records as the methods chapter writes them: each step with its code in the register, its formula, the values
    that went in with their sources, the result and the reference; what the model leaves out at the end."""
    kinds = kind_names()
    out = []

    def picture(tex: str, size: float) -> str:
        name = _formula_name(tex, size)
        return ctx.image(name, lambda: figures.formula_svg(tex, size))

    for rec in records:
        out.append(section(rec.title, "slate"))
        for step in rec.steps:
            code = ctx.register.step(step.key) if ctx.register.active else None
            title = [bold(code[0]), "  ", step.title] if code else step.title
            out.append(sub(title))
            if step.explanation:
                out.append(para(step.explanation))
            if step.formula:
                out.append({"k": "formula", "image": picture(step.formula, 12.0)})
            rows = []
            for q in step.inputs:
                src = q.source
                where: list = []
                if src is not None:
                    where.append(bold(kinds.get(src.kind, src.kind)))
                    if src.label:
                        where.append(f": {src.label}")
                    if src.ref:
                        where.append(muted(f" ({src.ref})"))
                rows.append((B.formula(picture(q.symbol, 10.0)) if q.symbol else "", q.label, q.text(), where))
            result = None
            if step.result is not None:
                q = step.result
                result = len(rows)
                rows.append((B.formula(picture(q.symbol, 10.0)) if q.symbol else "", q.label, q.text(), ""))
            if rows:
                out.append(table(rows, [_("Symbol"), _("Quantity"), _("Value and unit"), _("Source")], right=(2,),
                                 widths=("13%", "37%", "18%", "32%"), mark_row=result))
            if step.reference:
                out.append(para(f"{_('Reference')}: {step.reference}", "muted"))
    if records:
        out.append(section(_("What the model does not include"), "slate"))
        out.append(para(_("The steps above are the whole of the calculation. What it leaves out, and what it only "
                          "estimates, is listed here so that the report does not promise it.")))
        out.append({"k": "list", "items": limits()})
    return out


def records_of(data: dict) -> list:
    """The records of the calculations, in the order the chapter of the methods has them."""
    sim, load, econ, pl = data.get("sim"), data.get("load"), data.get("econ"), data.get("plant")
    first_plan = next((s.plan for s in getattr(pl, "strings", []) if s.plan is not None), None)
    return [r for r in (getattr(sim, "record", None), getattr(first_plan, "record", None),
                        getattr(load, "record", None), getattr(econ, "record", None)) if r is not None]


def methods(ctx: Context) -> list:
    records = records_of(ctx.data)
    parts = []
    if records:
        parts += _records_blocks(ctx, records)
        defaults = []
        for r in records:
            for st in r.steps:
                for q in st.inputs:
                    if q.source is not None and q.source.kind == "default":
                        defaults.append((st.title, q.label, q.text()))
        if defaults:
            parts.append(section(_("Values still at their default"), "sun"))
            parts.append(para(_("Meridiana chose these values because none was given: check them before the final "
                                "design.")))
            parts.append(table(list(dict.fromkeys(defaults)), [_("Step"), _("Value"), _("As used")]))
    return parts


def annexes(ctx: Context) -> list:
    from ..energy.simulate import ModuleSpec
    p = ctx.project
    cards: list = []
    seen = set()
    for sf in p.subfields:
        if not sf.filled or sf.module in seen:
            continue
        seen.add(sf.module)
        m = ModuleSpec.from_record(p.modules.get(sf.module) or {"power_kw": p.module_of(sf).power_kw})
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
        cards.append([sub(_("Module: {name}").format(name=f"{m.manufacturer} {m.model}".strip())), facts(rows)])
    pl = ctx.get("plant")
    done = set()
    for u in getattr(pl, "units", []) or []:
        if u.name in done:
            continue
        done.add(u.name)
        s = u.spec
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
        cards.append([sub(_("Inverter: {name}").format(name=u.name)), facts(rows)])
    shown = set()
    for u in getattr(pl, "units", []) or []:
        ch = u.choice if u.optimized else None
        if ch is None or ch.optimizer.name in shown:
            continue
        shown.add(ch.optimizer.name)
        o = ch.optimizer
        rows = [(_("Rated input DC power"), f"{number(o.rated_w, 0)} W"),
                (_("Absolute maximum input voltage"), f"{number(o.voc_max, 0)} V"),
                (_("Maximum module Isc"), f"{number(o.isc_max, 1)} A"),
                (_("Maximum output current"), f"{number(o.i_out_max, 1)} A"),
                (_("Weighted efficiency"), f"{number(100 * o.eta, 1)} %"),
                (_("Modules on each"), str(ch.per))]
        if o.i_in_max:
            rows.insert(3, (_("Maximum continuous input current"), f"{number(o.i_in_max, 1)} A"))
        rows.append((_("Source"), o.datasheet))
        cards.append([sub(_("Power optimizer: {name}").format(name=o.name)), facts(rows)])
    parts = []
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2]
        parts.append(two(pair[0], pair[1]) if len(pair) == 2 else keep(*pair[0]))
    return parts


def register_chapter(ctx: Context) -> list:
    """The register as a chapter of its own: each group, with what each code stands for. Written last, when the other
    chapters have given their rows."""
    parts = [para(_("Every number of the report is here: its code is in the Source column of the tables and on the "
                    "cards. The values hour by hour are in the CSV file of the register.")),]
    for g in ctx.register.groups:
        parts.append(sub([bold(g.code), "  ", g.title]))
        parts.append(table([(code, what, value, where) for code, what, value, where in g.rows],
                           [_("Code"), _("What"), _("Value"), _("Where from")], widths=("10%", "26%", "38%", "26%")))
    return parts


# the chapters of «Compact»

def overview(ctx: Context) -> list:
    """The sheet of the summary, closed by a 3D view; the other view and the plan at the whole width after it."""
    parts = _sheet(ctx) + _sheet_picture(ctx)
    views = list(ctx.pictures)
    if len(views) > 1:
        parts.append(view_block(ctx, views[0]))
    parts.append(plan_block(ctx))
    return parts


def monthly(ctx: Context) -> list:
    sim = ctx.get("sim")
    m = sim.monthly
    names = months()
    body = [(names[i], kwh(m.e_ac.iloc[i]), kwh(m.e_ac.iloc[i] / sim.p_stc_kw if sim.p_stc_kw else 0))
            for i in range(min(12, len(m)))]
    body.append((_("Year"), kwh(sim.energy_kwh), kwh(sim.specific_yield)))
    left = ctx.tabled(body, [_("Month"), _("Energy, kWh"), "kWh/kWp"], right=(1, 2), widths=("40%", "30%", "30%"),
                      mark_row=len(body) - 1, group=_("Estimated monthly energy"), where="ac")
    chart = monthly_bars(ctx, 42.0)
    right = [chart]
    if chart.get("thousands"):
        right.append(para(_("In MWh."), "source"))
    right.append(para(ctx.caption(_("Energy delivered month by month, Meridiana beside PVGIS.")
                                  if ctx.get("pvgis") is not None else _("Energy delivered month by month.")), "caption"))
    return [two(left, right)]


def fields(ctx: Context) -> list:
    from ..energy.simulate import ModuleSpec
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
                     number(r.azimuth, 0), number(r.tilt, 0)))
    parts = ctx.tabled(rows, [_("Sub-field"), _("Module"), _("Modules"), "kWp", _("Mounting"), f"{_('Azimuth')}, °",
                              f"{_('Tilt')}, °"], right=(2, 3, 5, 6),
                       widths=("16%", "28%", "9%", "9%", "18%", "10%", "10%"),
                       group=_("Modules by sub-field"), where=_("the layout of the project"))
    parts.append(para(_("Azimuth from the south, positive towards the west (CEI 82-25)."), "caption"))
    return parts


def electrical(ctx: Context) -> list:
    from ..energy import plant as plants
    pl = ctx.get("plant")
    states = plants.state_names()
    names = {sf.id: sf.name for sf in ctx.project.subfields}
    parts = []
    for u in pl.units:
        mine = sorted((s for s in pl.strings if s.inverter == u.number), key=lambda x: (x.mppt, x.index))
        parts.append(sub(f"{plants.unit_label(u)}: {u.name}"))
        if u.optimized:
            parts.append(para(optimizer_text(u)))
        if not mine:
            parts.append(para(_("No string on it."), "muted"))
            continue
        parts += ctx.tabled([(s.label, str(s.mppt), str(len(s.modules)),
                              ", ".join(dict.fromkeys(names.get(sf, sf) for sf, _k, _c in s.modules)),
                              [B.mark(MARKS[s.state]), " ", states[s.state]]) for s in mine],
                            [_("String"), _("Input"), _("Modules"), _("Sub-field"), _("State")], right=(1, 2),
                            group=_("Electrical design"), where="uocmax")
    text = _dcac_text(pl)
    if text:
        parts.append(para(text))
    if pl.strings:
        parts.append(plan_block(ctx, strings=True))
    return parts


def parameters(ctx: Context) -> list:
    s = ctx.project.site
    place = _("Project's data")
    rows = [(_("Latitude"), f"{number(s.lat, 5)}°", place), (_("Longitude"), f"{number(s.lon, 5)}°", place)]
    if ctx.settings.get("address", True) and s.address:
        rows.insert(0, (_("Address"), s.address, place))
    if ctx.get("meteo_text"):
        rows.append((_("Weather"), ctx.get("meteo_text"), _("Weather")))
    parts = ctx.carded(rows, group=_("Simulation parameters"), ratio=(2, 7))
    sim = ctx.get("sim")
    steps = [st for st in sim.chain if st.change is not None]
    if steps:
        parts.append(section(_("Losses and gains applied"), "sun"))
        parts += ctx.tabled([(st.label, number(st.change, 1)) for st in steps], [_("Step"), f"{_('Change')}, %"],
                            right=(1,), widths=("75%", "25%"), group=_("Losses and gains applied"), where="ac")
    return parts


BUILDERS: dict = {"summary": summary, "site": site, "layout": layout, "plant": plant, "production": production,
                  "consumption": consumption, "economics": economics, "checks": checks, "methods": methods,
                  "annexes": annexes, "register": register_chapter, "overview": overview, "monthly": monthly,
                  "fields": fields, "electrical": electrical, "parameters": parameters}


# the strings of the plant, as the report has had them since task 16d (step 8)

def keys_text(keys: list[str]) -> str:
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


def _tabled(ctx, rows, head=None, **kw) -> list:
    """A table with its source when the report's context is there (`plant_parts` also works without one)."""
    if ctx is not None:
        return ctx.tabled(rows, head, **kw)
    kw.pop("group", None)
    kw.pop("where", None)
    return [table(rows, head, kw.get("right", ()), kw.get("widths"), kw.get("mark_row"))]


def _optimized_parts(plant_state, u, ctx=None) -> list:
    """An inverter with power optimizers in the report: its optimizers, each input (Synergy unit) with its strings,
    their modules, optimizers and power, the checks of each kind of string with their sources, the inverter's own."""
    from ..energy import optimizers
    from ..energy import plant as plant_model
    states = plant_model.state_names()
    parts = [para(optimizer_text(u))]
    rows = []
    plans = []
    for k in range(1, u.inputs + 1):
        slot = plant_state.inputs.get((u.number, k))
        mine = [plant_state.strings[i] for i in (slot.strings if slot is not None else [])]
        mods = ", ".join(sorted({str(len(s.modules)) for s in mine}, key=int)) or "–"
        opts = ", ".join(sorted({str(s.plan.optimizers) for s in mine if isinstance(s.plan, optimizers.OptimizedPlan)},
                                key=int)) or "–"
        power = number(sum(s.plan.power_w for s in mine if s.plan is not None) / 1000.0, 2) if mine else "–"
        worst = max((s.state for s in mine), key=("ok", "check", "fail").index) if mine else ""
        state = [B.mark(MARKS[worst]), " ", states[worst]] if mine else "–"
        rows.append((plant_model.input_name(u, k), str(len(mine)) if mine else _("free"), mods, opts, power, state))
        for s in mine:
            if s.plan is not None and (len(s.modules), round(s.plan.power_w)) not in [(n, w) for n, w, _p in plans]:
                plans.append((len(s.modules), round(s.plan.power_w), s.plan))
    parts += _tabled(ctx, rows, [_("Input"), _("Strings"), _("Modules"), _("Optimizers"), "kWp", _("State")],
                     right=(1, 2, 3, 4), group=_("Strings of power optimizers (SolarEdge)"),
                     where=_("SolarEdge's tables"))
    for n, _w, p in plans:
        parts.append(para(_("A string of {n} modules, {o} optimizers, {p} kWp").format(
            n=n, o=p.optimizers, p=number(p.power_w / 1000.0, 2)), "muted"))
        parts.append(table([(B.mark(c.level if c.level in ("ok", "warn", "fail", "info") else "ok"), c.label,
                             f"{c.detail} ({c.source})" if c.source else c.detail) for c in p.checks],
                           widths=("4%", "40%", "56%")))
    for c in plant_state.checks.get(u.number, []):
        source = f" ({c.source})" if c.source else ""
        parts.append(para([B.mark(c.level if c.level in ("ok", "warn", "fail", "info") else "ok"),
                           " ", f"{c.label}: {c.detail}{source}"]))
    return parts


def _level(c) -> str:
    return c.level if c.level in ("ok", "warn", "fail", "info") else "ok"


def _string_plans(plant_state, units) -> list[tuple[int, list, list[str]]]:
    """The kinds of string checked on `units`, each once: (modules in series, the rows of its checks, the inputs
    «inverter.input» it is on). Two plans are one kind when their checks say the same, the input's own number
    taken off the labels that name it («input 1: ...», stringing.py)."""
    kinds: dict = {}
    for u in units:
        prefixes = {f"{_('input {k}').format(k=k)}: ": "" for k in range(1, u.inputs + 1)}
        for k in range(1, u.inputs + 1):
            slot = plant_state.inputs.get((u.number, k))
            for p in {id(p): p for p in [plant_state.strings[i].plan for i in (slot.strings if slot else [])] if p}.values():
                rows = []
                for c in p.checks:
                    label = c.label
                    for prefix in prefixes:
                        if label.startswith(prefix):
                            label = label[len(prefix):]
                            label = label[:1].upper() + label[1:]
                    rows.append((B.mark(_level(c)), label, c.detail))
                key = (p.n_series, tuple((c.level, r[1], r[2]) for c, r in zip(p.checks, rows, strict=True)))
                kinds.setdefault(key, (p.n_series, rows, []))[2].append(f"{u.number}.{k}")
    return list(kinds.values())


def plant_parts(project, plant_state, ctx=None) -> list:
    """The strings of the plant: for each inverter its inputs with the strings, the modules in series and the
    state; the checks of each input with their clauses (CEI 64-8/7) and the conditions they were made at; then
    every string with its sub-field and its modules, by inverter and input."""
    from ..energy import plant as plant_model
    states = plant_model.state_names()
    names = {sf.id: sf.name for sf in project.subfields}
    used = sum(1 for slot in plant_state.inputs.values() if slot.used)
    only_optimizers = all(u.optimized for u in plant_state.units)
    title = _("Strings of power optimizers (SolarEdge)") if only_optimizers else _("Strings (CEI 64-8/7)")
    parts = [section(title, "acc")]
    head = _("{n} strings on {m} inputs of {u} inverters, named inverter.input.string; {how}.").format(
        n=len(plant_state.strings), m=used, u=len(plant_state.units),
        how=(_("proposed by Meridiana: {strategy}").format(
            strategy=plant_model.strategy_names().get(plant_state.strategy, "").lower()) if plant_state.auto else
             _("the designer's: drawn on the plan, or proposed by Meridiana when asked and kept")))
    if plant_state.left:
        head += " " + _("{m} modules are in no string.").format(m=len(plant_state.left))
    when = (_("Checked at the hottest cell of the typical year, {t} °C, and at {c} °C.").format(
        t=number(plant_state.t_cell_max, 0), c=number(plant_state.t_cell_cold, 0)) if plant_state.year else
        _("Checked at PVsyst's design conditions until the production is computed: {hot} and {warm} °C of cell, "
          "Uoc at {cold} °C.").format(hot=number(plant_state.t_cell_max, 0), warm=number(plant_state.t_cell_cold, 0),
                                      cold=number(plant_state.t_min, 0)))
    if only_optimizers:
        when = _("The strings checked by SolarEdge's tables, the modules' Voc at {t} °C.").format(
            t=number(plant_state.t_min, 0))
    parts.append(para(f"{head} {when}"))
    plain = [u for u in plant_state.units if not u.optimized]
    if plain:
        # one table for every input of every inverter, then the checks once for each kind of string: the same 25
        # modules in series were checked, and written, four times for two inverters of two inputs (R291)
        rows = []
        for u in plain:
            for k in range(1, u.inputs + 1):
                slot = plant_state.inputs.get((u.number, k))
                mine = [plant_state.strings[i] for i in (slot.strings if slot is not None else [])]
                series = ", ".join(sorted({str(len(s.modules)) for s in mine})) or "–"
                worst = max((s.state for s in mine), key=("ok", "check", "fail").index) if mine else ""
                state = [B.mark(MARKS[worst]), " ", states[worst]] if mine else "–"
                rows.append((f"{plant_model.unit_label(u)}: {u.name}" if k == 1 else "", str(k),
                             str(len(mine)) if mine else _("free"), series, state))
        parts += _tabled(ctx, rows, [_("Inverter"), _("Input"), _("Strings"), _("Modules in series"), _("State")],
                         right=(1, 2, 3), widths=("36%", "12%", "12%", "20%", "20%"),
                         group=_("Strings (CEI 64-8/7)"), where="uocmax")
        parts.append(sub(_("Checks of the strings")))
        for n_series, checks_rows, where in _string_plans(plant_state, plain):
            parts.append(para(_("Strings of {n} modules in series, on the inputs {where}.").format(
                n=n_series, where=", ".join(where)), "muted"))
            parts.append(table(checks_rows, widths=("4%", "48%", "48%")))
        own = [(B.mark(_level(c)), f"{c.label}: {c.detail}") for u in plain for c in plant_state.checks.get(u.number, [])]
        if own:
            parts.append(sub(_("Checks of the inverters")))
            parts.append(table(own, widths=("4%", "96%")))
    for u in plant_state.units:
        if u.optimized:
            parts.append(sub(f"{plant_model.unit_label(u)}: {u.name}"))
            parts += _optimized_parts(plant_state, u, ctx)
    parts.append(sub(_("The strings on the modules")))
    rows = []
    for s in sorted(plant_state.strings, key=lambda x: (x.inverter, x.mppt, x.index)):
        sfs = list(dict.fromkeys(sf for sf, _k, _c in s.modules))
        where = ", ".join(names.get(sf, sf) for sf in sfs) or "–"
        rows.append((s.label, where, str(len(s.modules)), muted(keys_text([k for _sf, k, _c in s.modules]))))
    parts += _tabled(ctx, rows, [_("String"), _("Sub-field"), _("Modules"), _("Which (row:place)")], right=(2,),
                     group=_("The strings on the modules"), where=_("the stringing of the project"))
    return parts


def in_report(chapter: reports.Chapter, n: int, breaks: bool = False) -> dict:
    """The heading of a chapter."""
    return {"k": "chapter", "title": f"{n}. {chapter.title}", "id": chapter.id, "break": breaks}
