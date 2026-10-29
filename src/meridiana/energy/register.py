"""The register of the calculations (R61, docs/compiti/19r-relazione.md): the typical year hour by hour as a CSV
file beside the report, so that every number of the report can be followed down to its hour. The irradiance on
the plane, the cells' temperature and the production of the simulation (simulate.py); with a consumption, the
consumption, the energy self-consumed, fed in and drawn of the hourly balance (economics.py). A header of lines
starting with «#» says what each column is, in which unit and where it comes from.

The file is written as the language of the window reads it in a spreadsheet: in Italian «;» between the fields and
the decimal comma, in English «,» and the point; UTF-8 with its mark, so that a spreadsheet on Windows reads «°» and
«²». No Qt here."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from ..i18n import _, language, number
from .simulate import REFERENCE_YEAR, TIMEZONE


@dataclass(frozen=True)
class Column:
    id: str
    label: str
    unit: str
    decimals: int
    meaning: str


def columns(inverters=()) -> list[Column]:
    """Every column the register may have, in its order; `frame` keeps those it has data for."""
    out = [
        Column("ghi", _("Global horizontal"), "W/m²", 1,
               _("global horizontal irradiance, the mean of the hour, from the weather of the site")),
        Column("poa", _("On the plane"), "W/m²", 1,
               _("global irradiance on the modules' plane before the shadings, the arrays weighted by their power")),
        Column("temp_air", _("Air"), "°C", 2, _("air temperature, from the weather of the site")),
        Column("t_cell", _("Cells"), "°C", 2,
               _("cells' temperature, PVsyst's thermal model (pvlib.temperature.pvsyst_cell), the arrays weighted "
                 "by their power")),
        Column("production", _("Produced"), "kWh", 4,
               _("energy delivered on the AC side in the hour, after the inverters, the AC wiring and the "
                 "unavailability")),
        Column("consumption", _("Consumed"), "kWh", 4, _("energy used on site in the hour")),
        Column("self", _("Self-consumed"), "kWh", 4,
               _("energy produced and used on site in the same hour, the battery's included")),
        Column("export", _("Fed in"), "kWh", 4, _("energy fed into the grid in the hour")),
        Column("import", _("Drawn"), "kWh", 4, _("energy drawn from the grid in the hour")),
    ]
    for inv in inverters:
        label = f"{inv['number']} · {inv['name']}"
        for side in ("dc", "ac"):
            out.append(Column(f"inverter_{inv['number']}_{side}", f"{label} {side.upper()}", "kWh", 4,
                              _("Hourly energy of this physical inverter; AC includes its clipping, wiring and "
                                "unavailability. No unused capacity of another inverter compensates its clipping.")))
    return out


def frame(sim, load=None, econ=None):
    """The register's table: one row an hour of the typical year (local time of REFERENCE_YEAR), the columns of
    `columns()` the data have: the simulation's always, the cells' temperature when the simulation kept its first
    pass, the balance's when there is a consumption."""
    import pandas as pd
    h = sim.hourly
    data = {"ghi": h["ghi"].to_numpy(), "poa": h["poa"].to_numpy(), "temp_air": h["temp_air"].to_numpy()}
    parts = getattr(sim, "parts", None)
    if parts is not None and getattr(parts, "per_array", None):
        data["t_cell"] = np.sum([w * np.asarray(ap.t_cell, dtype=float)
                                 for w, ap in zip(parts.weights, parts.per_array, strict=True)], axis=0)
    data["production"] = h["e_kwh"].to_numpy()
    inverters = getattr(sim, "inverters", ())
    for inv in inverters:
        for side in ("dc", "ac"):
            data[f"inverter_{inv['number']}_{side}"] = np.asarray(inv[f"p_{side}"], dtype=float) / 1000.0
    out = pd.DataFrame(data, index=h.index)
    out.attrs["inverters"] = [{"number": inv["number"], "name": inv["name"]} for inv in inverters]
    hb = getattr(econ, "hourly", None) if econ is not None else None
    if hb is not None and len(hb):
        for k in ("consumption", "self", "export", "import"):
            out[k] = hb[k].reindex(out.index).fillna(0.0).to_numpy()
    elif load is not None:
        out["consumption"] = load.hourly.reindex(out.index).fillna(0.0).to_numpy()
    return out


def header(project_name: str, variant: str, version: str, sources: list[tuple[str, str]], cols: list[Column],
           rows: int = 8760) -> list[str]:
    """The lines before the table, without their «#»: what the file is, the time, the sources, each column."""
    lines = [_("Meridiana {v}: register of the calculations of «{project}», variant «{variant}», {day}").format(
        v=version, project=project_name, variant=variant, day=date.today().strftime("%d/%m/%Y")),
        _("The typical year hour by hour, {n} rows: each the hour that starts at its time, in Italian local time "
          "({tz}, summer time included) of the reference year {year}; «UTC» is its offset.").format(
            n=number(rows, 0, grouping=True), tz=TIMEZONE, year=REFERENCE_YEAR)]
    lines += [f"{label}: {text}" for label, text in sources if text]
    lines.append(_("The models, the losses and their sources are in the report, chapter «Parameters and methods»."))
    lines.append(_("The columns:"))
    lines += [f"  {c.label} ({c.unit}): {c.meaning}" for c in cols]
    return lines


def write_csv(path: Path, table, lines: list[str]) -> None:
    """`table` (from `frame`) with its header `lines` as a CSV file, written beside `path` and put in its place at
    the end: a file stopped half way leaves nothing."""
    italian = language() == "it"
    sep, comma = (";", ",") if italian else (",", ".")
    known = {c.id: c for c in columns(table.attrs.get("inverters", ()))}
    cols = [known[k] for k in table.columns if k in known]
    head = [_("Local time"), "UTC"] + [f"{c.label} ({c.unit})" for c in cols]
    stamps = table.index.strftime("%Y-%m-%d %H:%M")
    offsets = [f"{t[:3]}:{t[3:]}" for t in table.index.strftime("%z")]
    values = []
    for c in cols:
        text = np.char.mod(f"%.{c.decimals}f", table[c.id].to_numpy(dtype=float))
        values.append(np.char.replace(text, ".", comma) if comma != "." else text)
    part = Path(path).with_name(Path(path).name + ".part")
    try:
        with open(part, "w", encoding="utf-8-sig", newline="") as f:
            for line in lines:
                # Free names also appear in metadata: every physical line remains a comment.
                for physical in line.splitlines() or [""]:
                    f.write(f"# {physical}\r\n")
            writer = csv.writer(f, delimiter=sep, lineterminator="\r\n")
            writer.writerow(head)
            for i in range(len(table)):
                writer.writerow([stamps[i], offsets[i], *(v[i] for v in values)])
        os.replace(part, path)
    finally:
        if part.exists():
            part.unlink()
