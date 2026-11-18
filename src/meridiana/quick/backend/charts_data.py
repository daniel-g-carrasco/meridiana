"""Result pages as plain data, independent of the Widgets and plotting libraries.

Numbers remain unrounded until presentation. Calendar holes and unavailable values
become JSON null, never a fictitious zero. Pedigree records retain every formula,
input, source and reference. The numerical transformations mirror energy_pages;
the differential tests run that implementation as the independent reference.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import math

import numpy as np

from ...energy.register import year_carpet
from ...energy.pedigree import kind_names, limits
from ...energy.storage import check_storage, operating_battery
from ...i18n import _, number, ngettext


LONG = 100


def calculation_basis(basis):
    """The immutable year context, with the exact wording used by the Widgets."""
    if basis is None:
        return {}
    inverters = ngettext('{n} inverter', '{n} inverters', basis.inverter_count).format(n=basis.inverter_count)
    modules = _('{n} of {total} modules connected').format(n=basis.connected_modules, total=basis.laid_modules)
    storage = ngettext('{n} battery', '{n} batteries', basis.battery_count).format(n=basis.battery_count)
    if basis.battery_count:
        storage += _(', {capacity} kWh usable · {energy} kWh supplied to loads').format(
            capacity=number(basis.battery_kwh, 1), energy=number(basis.supplied_kwh, 1, grouping=True))
    text = _('Calculated plant: {inverters} · {modules} · {storage}').format(
        inverters=inverters, modules=modules, storage=storage)
    detail = '\n'.join([*basis.inverters, basis.battery_name] if basis.battery_name else basis.inverters)
    return dict(text=text, tip=text + ('\n' + detail if detail else ''))


def _plain(value):
    """A QVariant/strict-JSON value, preserving unavailable numbers as null."""
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_plain(item) for item in value]
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def pedigree(records):
    """The records as plain values, each with its steps laid out as the report lays them out (report_typst/steps.py,
    R460): the formula numbered, the values on the decimal comma, «With the values», the result."""
    from ...report_typst.steps import for_window
    records = _plain(records)
    for record, view in zip(records, for_window(records), strict=True):
        record["view"] = view
    return records


@dataclass
class ChartData:
    kind: str = "message"
    title: str = ""
    categories: list[str] = field(default_factory=list)
    series: list = field(default_factory=list)
    unit: str = ""
    stacked: bool = False
    decimals: int = 0
    xs: list = field(default_factory=list)
    rows: list[str] = field(default_factory=list)
    cols: list[str] = field(default_factory=list)
    matrix: list = field(default_factory=list)
    xlabel: str = ""
    ticks: list | None = None
    row_ticks: list | None = None
    names: list[str] | None = None
    area: bool = True
    mark_zero: bool = True
    mark: tuple | None = None
    markers: bool = False
    source: str = ""
    message: str = ""
    action: str = ""

    def table(self) -> dict:
        """The original raw table with units separated and additive totals only.

        Monthly energy, money and yearly cash flows can be summed. Percentages,
        loss-chain steps, typical-hour means, cumulative cash and sizing curves
        cannot: these have no totals. Empty states have no fabricated table row.
        """
        headers, rows, units, totals = [], [], [], []
        if self.kind == "bars":
            headers = [""] + [name for name, _values in self.series]
            rows = [
                [category] + [values[i] for _name, values in self.series] for i, category in enumerate(self.categories)
            ]
            units = [""] + [self.unit] * len(self.series)
            if self.unit in ("kWh", "Wh", "MWh", "€") and rows:
                totals = [None] + [
                    None if any(value is None or not math.isfinite(value) for value in values) else sum(values)
                    for _name, values in self.series
                ]
        elif self.kind == "changes":
            headers, units = [_("Step"), self.unit], ["", self.unit]
            values = self.series[0][1] if self.series else []
            rows = [[label, value] for label, value in zip(self.categories, values, strict=True)]
        elif self.kind == "heatmap":
            headers, units = [""] + list(self.cols), [""] + [self.unit] * len(self.cols)
            rows = [[label] + list(self.matrix[i]) for i, label in enumerate(self.rows)]
        elif self.kind == "line":
            headers = [self.xlabel or ""] + [name for name, _values in self.series]
            units = [""] + [self.unit] * len(self.series)
            rows = [
                [self.names[i] if self.names is not None else str(x)] + [values[i] for _name, values in self.series]
                for i, x in enumerate(self.xs)
            ]
        return _plain({"headers": headers, "rows": rows, "units": units, "totals": totals})

    def to_dict(self) -> dict:
        return {**_plain(asdict(self)), "table": self.table(), "zoomable": self.kind == "line" and len(self.xs) > LONG}


def bars(categories, series, unit, stacked=False, decimals=0, *, title="", source="") -> ChartData:
    return ChartData("bars", title, list(categories), _plain(series), unit, stacked, decimals, source=source)


def changes(labels, values, unit="%", *, title="", source="") -> ChartData:
    return ChartData("changes", title, list(labels), [(unit, list(values))], unit, decimals=1, source=source)


def heatmap(matrix, rows, cols, unit, decimals=1, ticks=None, row_ticks=None, *, title="", source="") -> ChartData:
    return ChartData(
        "heatmap",
        title,
        unit=unit,
        decimals=decimals,
        matrix=_plain(matrix),
        rows=list(rows),
        cols=list(cols),
        ticks=ticks,
        row_ticks=row_ticks,
        source=source,
    )


def line(
    xs,
    series,
    unit,
    xlabel="",
    decimals=0,
    area=True,
    mark_zero=True,
    mark=None,
    markers=False,
    ticks=None,
    names=None,
    *,
    title="",
    source="",
) -> ChartData:
    return ChartData(
        "line",
        title,
        series=_plain(series),
        unit=unit,
        xs=list(xs),
        xlabel=xlabel,
        decimals=decimals,
        area=area,
        mark_zero=mark_zero,
        mark=mark,
        markers=markers,
        ticks=ticks,
        names=names,
        source=source,
    )


def month_names() -> list[str]:
    return [
        _("Jan"),
        _("Feb"),
        _("Mar"),
        _("Apr"),
        _("May"),
        _("Jun"),
        _("Jul"),
        _("Aug"),
        _("Sep"),
        _("Oct"),
        _("Nov"),
        _("Dec"),
    ]


def _spec(kind):
    """Labels and grouping, translated when the page is requested."""
    if kind == "production":
        return (
            _("Production"),
            [_("Energy a year"), _("Specific yield"), _("Performance ratio"), _("Power"), _("PVGIS, second opinion")],
            [
                (_("Months"), [("monthly", _("Production month by month"))]),
                (_("Losses"), [("losses_chart", _("From the sun to the meter: each step"))]),
                (_("Typical day"), [("day", _("Average production by hour and month"))]),
            ],
        )
    if kind == "consumption":
        return (
            _("Consumption"),
            [
                _("Consumption a year"),
                "F1",
                "F2",
                "F3",
                _("Highest hour"),
                _("Base load"),
                _("Load factor"),
                _("Between 8 and 18"),
                _("Weekends and holidays"),
            ],
            [
                (_("Months"), [("monthly", _("Consumption month by month, by band"))]),
                (_("Typical day"), [("day", _("Average consumption by hour and month"))]),
                (_("Year"), [("year_map", _("The year hour by hour: each column a day, each row an hour"))]),
                (_("Week"), [("week", _("Average week, hour by hour"))]),
                (_("Duration"), [("duration", _("Load duration curve: the hours of the year from the highest load"))]),
            ],
        )
    return (
        _("Economics"),
        [
            _("Self-consumption"),
            _("Self-sufficiency"),
            _("Saving, first year"),
            _("Sale and incentives, first year"),
            _("Investment"),
            _("Net present value"),
            _("Internal rate of return"),
            _("Payback"),
            _("Levelised cost"),
            _("Bill, first year"),
        ],
        [
            (
                _("Balance"),
                [
                    ("prod_split", _("Production: self-consumed and fed in")),
                    ("cons_split", _("Consumption: covered by the system and by the grid")),
                ],
            ),
            (_("Year"), [("self_map", _("Used on the spot, hour by hour: each column a day, each row an hour"))]),
            (_("Bill"), [("bill", _("Energy part of the bill, month by month: without the system and with it"))]),
            (_("Cash flow"), [("cash", _("Cumulative cash flow"))]),
            (_("Year by year"), [("flows", _("Cash flow year by year"))]),
            (
                _("Size"),
                [
                    ("size_share", _("Self-consumption and self-sufficiency, by the size of the system")),
                    ("size_npv", _("Net present value, by the size of the system")),
                ],
            ),
            (
                _("Storage"),
                [
                    ("store_share", _("Self-sufficiency, by the capacity of the battery")),
                    ("store_npv", _("Net present value, by the capacity of the battery")),
                ],
            ),
        ],
    )


def _tiles(kind):
    return [{"label": label, "value": "", "detail": "", "more": ""} for label in _spec(kind)[1]]


def _tile(tiles, index, value, detail="", more=""):
    tiles[index].update(value=value, detail=detail, more=more)


def _page(kind, tiles, charts, records=(), status="", empty=False, message="", notes=None):
    title, _labels, groups = _spec(kind)
    helps = {
        'production': ['production.energy', 'production.specific_yield', 'production.pr', 'production.power', 'production.pvgis'],
        'consumption': ['consumption.year'] + ['consumption.bands']*3 + ['consumption.shape']*5,
        'economics': ['economics.self_consumption', 'economics.self_sufficiency', 'economics.first_year',
                      'economics.first_year', 'economics.return', 'economics.npv', 'economics.return',
                      'economics.return', 'economics.return', 'economics.first_year'],
    }
    tiles = [{**tile, 'help': helps[kind][i]} for i, tile in enumerate(tiles)]
    tabs = []
    for tab_title, members in groups:
        content = []
        for key, chart_title in members:
            chart = charts.get(
                key,
                ChartData(message=message or _("Compute the production and the consumption first."), action="compute"),
            )
            chart.title = chart_title
            content.append({"id": key, **chart.to_dict()})
        tabs.append({"title": tab_title, "charts": content, "note": (notes or {}).get(members[0][0], "")})
    records = pedigree(records)
    tabs.append({"title": _("How it is computed"), "charts": [], "records": records})
    return {
        "kind": kind,
        "title": title,
        "tiles": tiles,
        "tabs": tabs,
        "records": records,
        "status": status,
        "empty": empty,
        "action": "compute" if empty else "",
        "source_kinds": kind_names(),
        "limits": limits() if records else [],
        "limits_title": _("What the model does not include"),
        "limits_intro": _(
            "The steps above are the whole of the calculation. What it leaves out, and what it only estimates, is "
            "listed here so that the report does not promise it."
        ),
    }


def _sizing(charts, sizing, storage, p_stc_kw, battery_kwh):
    if sizing is None or storage is None:
        return {}
    kwp = [round(float(x), 1) for x in sizing.kwp]
    here = (p_stc_kw, _("as designed"))
    charts["size_share"] = line(
        kwp,
        [
            (_("self-consumption"), [100 * float(v) for v in sizing.self_ratio]),
            (_("self-sufficiency"), [100 * float(v) for v in sizing.self_sufficiency]),
        ],
        "%",
        "kWp",
        0,
        area=False,
        mark=here,
        markers=True,
    )
    charts["size_npv"] = line(
        kwp, [(_("net present value"), [float(v) for v in sizing.npv])], "€", "kWp", 0, mark=here, markers=True
    )
    best = sizing.loc[sizing.npv.idxmax()]
    size_note = _(
        "The production grows with the power, in the same proportions; the investment too. "
        "The highest net present value of these sizes is at {kwp} kWp ({eur} €)."
    ).format(kwp=number(float(best.kwp), 1), eur=number(float(best.npv), 0, grouping=True))
    frame, generic = storage
    kwh = [round(float(x), 1) for x in frame.kwh]
    mark = (battery_kwh, _("as designed")) if battery_kwh > 0 else None
    charts["store_share"] = line(
        kwh,
        [(_("self-sufficiency"), [100 * float(v) for v in frame.self_sufficiency])],
        "%",
        "kWh",
        0,
        mark=mark,
        markers=True,
    )
    charts["store_npv"] = line(
        kwh, [(_("net present value"), [float(v) for v in frame.npv])], "€", "kWh", 0, mark=mark, markers=True
    )
    best = frame.loc[frame.npv.idxmax()]
    store_note = _("Each capacity is {generic}. The highest net present value is at {kwh} kWh ({eur} €).").format(
        generic=generic, kwh=number(float(best.kwh), 1), eur=number(float(best.npv), 0, grouping=True)
    )
    return {"size_share": size_note, "store_share": store_note}


def storage(settings) -> dict:
    """Read-only storage summary; editable catalogue fields belong to Properties."""
    battery = settings.get("battery") or {}
    coupling = "dc" if settings.get("storage_coupling") == "dc" else "ac"
    inverter = settings.get("storage_inverter") or {} if coupling == "dc" else {}
    units = settings.get("battery_units", 1)
    result = check_storage(battery, inverter, coupling, units)
    states = {
        "compatible": _("Model pairing documented"),
        "incompatible": _("Incompatible configuration"),
        "unknown": _("Compatibility unknown"),
    }
    messages = [states[result.status], *result.messages, *result.sources]
    valid = bool(battery)
    try:
        operating_battery({**settings, "storage_coupling": coupling, "storage_inverter": inverter})
    except ValueError as exc:
        messages.append(str(exc))
        valid = False
    name = f"{battery.get('manufacturer', '')} {battery.get('model', '')}".strip() or _("No battery")
    explanation = _(
        "Hourly balance uses AC production and an equivalent AC round-trip efficiency once. "
        "DC coupling does not recover clipped PV energy. Unknown compatibility is not approval."
    )
    records = [
        {
            "title": _("Storage"),
            "status": result.status,
            "messages": list(result.messages),
            "sources": list(result.sources),
            "explanation": explanation,
        }
    ]
    return {
        "title": _("Storage"),
        "tiles": [{"label": _("Storage"), "value": name, "detail": explanation, "more": ""}],
        "tabs": [],
        "records": records,
        "status": "\n".join(messages),
        "empty": not bool(battery),
        "action": "choose_battery" if not battery else "",
        "valid": valid,
    }


def production(sim, pvgis=None, error="") -> dict:
    tiles, charts, records = _tiles("production"), {}, []
    if error or sim is None:
        return _page(
            "production", tiles, charts, status=error, empty=True, message=error or _("Nothing to compute yet.")
        )
    status = "\n".join(sim.notes)
    t = tiles
    _tile(t, 0, f"{number(sim.energy_kwh, 0, grouping=True)} kWh", _("typical year"))
    _tile(t, 1, f"{number(sim.specific_yield, 0, grouping=True)} kWh/kWp")
    _tile(t, 2, f"{number(100 * sim.pr, 1)} %", "IEC 61724-1")
    _tile(
        t,
        3,
        f"{number(sim.p_stc_kw, 2)} kWp",
        _("{kw} kW AC, DC/AC {r}").format(
            kw=number(sim.p_ac_kw, 1), r=number(sim.p_stc_kw / sim.p_ac_kw, 2) if sim.p_ac_kw else "–"
        ),
    )
    months = month_names()
    series = [(_("Meridiana"), [float(v) for v in sim.monthly.e_ac.to_numpy()])]
    if pvgis is not None:
        diff = 100.0 * (sim.energy_kwh / pvgis.yearly_kwh - 1.0) if pvgis.yearly_kwh else 0.0
        _tile(
            t,
            4,
            f"{number(pvgis.yearly_kwh, 0, grouping=True)} kWh",
            _("Meridiana {d}% against PVGIS").format(d=number(diff, 1, sign=True)),
            _(
                "Meridiana {d}%. PVGIS: crystSi2025 technology, average of the years 2005-2023 (SARAH3); Meridiana: typical year"
            ).format(d=number(diff, 1, sign=True)),
        )
        series.append((_("PVGIS, PVcalc"), [float(v) for v in pvgis.monthly_kwh]))
    else:
        _tile(t, 4, "–", _("not available without the network"))
    charts["monthly"] = bars(months, series, "kWh")
    steps = [c for c in sim.chain if c.change is not None]
    charts["losses_chart"] = changes([c.label for c in steps], [float(c.change) for c in steps], "%")
    h = sim.hourly
    matrix = np.zeros((12, 24))
    for m in range(12):
        sel = h[h.index.month == m + 1]
        matrix[m] = sel.p_ac.groupby(sel.index.hour).mean().reindex(range(24), fill_value=0.0).to_numpy() / 1000.0
    charts["day"] = heatmap(matrix, months, [f"{k}" for k in range(24)], "kW")
    records = [sim.record]
    return _page("production", tiles, charts, records, status)


def consumption(load, error="") -> dict:
    tiles, charts, records = _tiles("consumption"), {}, []
    if error or load is None:
        return _page(
            "consumption",
            tiles,
            charts,
            status=error,
            empty=True,
            message=error or _("Compute the production and the consumption first."),
        )
    status = ""
    by = load.by_band()
    total = load.annual_kwh or 1.0
    t = tiles
    _tile(t, 0, f"{number(load.annual_kwh, 0, grouping=True)} kWh", load.basis)
    for i, b in enumerate(("F1", "F2", "F3")):
        _tile(t, i + 1, f"{number(100 * by[b] / total, 0)} %", f"{number(by[b], 0, grouping=True)} kWh")
    _tile(t, 4, f"{number(float(load.hourly.max()), 2)} kW", _("mean power of the busiest hour"))      # R447
    fig = load.figures()
    _tile(t, 5, f"{number(fig['base_kw'], 2)} kW", _("never below it in 95% of the hours"))
    _tile(t, 6, f"{number(100 * fig['load_factor'], 0)} %", _("mean load over the highest"))
    _tile(t, 7, f"{number(100 * fig['day_share'], 0)} %", _("of the consumption, when a system produces most"))
    _tile(t, 8, f"{number(100 * fig['off_share'], 0)} %", _("of the consumption"))
    from ...energy import bands

    b = bands.band_of(load.hourly.index)
    months = month_names()
    series = []
    for band in ("F1", "F2", "F3"):
        s = load.hourly[b == band]
        series.append((band, [float(v) for v in s.groupby(s.index.month).sum().reindex(range(1, 13), fill_value=0)]))
    charts["monthly"] = bars(months, series, "kWh", stacked=True)
    h = load.hourly
    matrix = np.zeros((12, 24))
    for m in range(12):
        sel = h[h.index.month == m + 1]
        matrix[m] = sel.groupby(sel.index.hour).mean().reindex(range(24), fill_value=0.0).to_numpy()
    charts["day"] = heatmap(matrix, months, [f"{k}" for k in range(24)], "kWh/h", 2)
    carpet, cols, ticks = year_carpet(h, months)
    charts["year_map"] = heatmap(
        carpet,
        [f"{k}:00" for k in range(24)],
        cols,
        "kWh/h",
        2,
        ticks=ticks,
        row_ticks=[(k, f"{k}") for k in range(0, 24, 3)],
    )
    days = [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]
    week = load.week()
    charts["week"] = line(
        list(range(168)),
        [(_("average load"), [float(v) for v in week])],
        "kW",
        "",
        2,
        ticks=[(24 * d + 12, days[d]) for d in range(7)],
        names=[f"{days[h // 24]} {h % 24}:00" for h in range(168)],
    )
    curve = load.duration()
    step = 24
    charts["duration"] = line(
        list(range(0, len(curve), step)),
        [(_("load"), [float(v) for v in curve[::step]])],
        "kW",
        _("hours of the year"),
        2,
    )
    records = [load.record]
    return _page("consumption", tiles, charts, records, status)


def economics(econ, error="", sizing=None, storage=None, p_stc_kw=0, battery_kwh=0) -> dict:
    tiles, charts, records = _tiles("economics"), {}, []
    if error or econ is None:
        return _page(
            "economics",
            tiles,
            charts,
            status=error,
            empty=True,
            message=error or _("Compute the production and the consumption first."),
        )
    status = ""
    k = econ.kpi
    t = tiles
    _tile(
        t,
        0,
        f"{number(100 * k['self_ratio'], 0)} %",
        _("of the production, {kwh} kWh").format(kwh=number(k["self"], 0, grouping=True)),
    )
    _tile(t, 1, f"{number(100 * k['self_sufficiency'], 0)} %", _("of the consumption"))
    _tile(t, 2, f"{number(k['saving_1'], 0, grouping=True)} €")
    detail = []
    if k["incentive_1"]:
        detail.append(_("of which incentives {eur} €").format(eur=number(k["incentive_1"], 0, grouping=True)))
    if k.get("curtailed"):
        detail.append(_("{kwh} kWh curtailed by the export limit").format(kwh=number(k["curtailed"], 0, grouping=True)))
    _tile(t, 3, f"{number(k['sale_1'] + k['incentive_1'], 0, grouping=True)} €", "; ".join(detail))
    _tile(t, 4, f"{number(k['capex'], 0, grouping=True)} €")
    _tile(t, 5, f"{number(k['npv'], 0, grouping=True)} €")
    _tile(t, 6, f"{number(100 * k['irr'], 1)} %" if k["irr"] is not None else "–")
    _tile(
        t,
        7,
        _("{y} years").format(y=number(k["payback"], 1)) if k["payback"] is not None else _("not within the years"),
        _("discounted {y}").format(y=number(k["payback_discounted"], 1)) if k["payback_discounted"] is not None else "",
    )
    _tile(t, 8, f"{number(k['lcoe'], 3)} €/kWh" if np.isfinite(k["lcoe"]) else _("No production"))
    if getattr(econ, "hourly", None) is not None and "self" in econ.hourly:
        carpet, cols, ticks = year_carpet(econ.hourly["self"], month_names())
        charts["self_map"] = heatmap(
            carpet,
            [f"{h}:00" for h in range(24)],
            cols,
            "kWh/h",
            2,
            ticks=ticks,
            row_ticks=[(h, f"{h}") for h in range(0, 24, 3)],
        )
    _tile(
        t,
        9,
        f"{number(k['bill_after'], 0, grouping=True)} €",
        _("energy part, was {eur} €").format(eur=number(k["bill_before"], 0, grouping=True)),
    )
    months = month_names()
    m = econ.monthly
    battery = bool(k.get("battery"))
    prod = [(_("Self-consumed"), [float(v) for v in m["direct"]])]
    cons_series = [(_("From the system"), [float(v) for v in m["direct"]])]
    if battery:
        prod.append((_("Into the battery"), [float(v) for v in m["stored"]]))
        cons_series.append((_("From the battery"), [float(v) for v in m["given"]]))
    prod.append((_("Fed in"), [float(v) for v in m["export"]]))
    cons_series.append((_("From the grid"), [float(v) for v in m["import"]]))
    charts["prod_split"] = bars(months, prod, "kWh", stacked=True)
    charts["cons_split"] = bars(months, cons_series, "kWh", stacked=True)
    charts["bill"] = bars(
        months,
        [
            (_("without the system"), [float(v) for v in m["bill_before"]]),
            (_("with the system"), [float(v) for v in m["bill_after"]]),
        ],
        "€",
    )
    years = [0] + list(econ.years.index)
    charts["cash"] = line(
        years, [(_("Cumulative"), [-k["capex"]] + [float(v) for v in econ.years.cumulative])], "€", _("year")
    )
    y = econ.years
    charts["flows"] = bars([str(i) for i in y.index], [(_("Net cash flow"), [float(v) for v in y.flow])], "€")
    records = [econ.record]
    notes = _sizing(charts, sizing, storage, p_stc_kw, battery_kwh)
    return _page("economics", tiles, charts, records, status, notes=notes)
