"""Where every number comes from. A calculation is a list of steps; each step says what it computes, the
formula (LaTeX, in the subset matplotlib's mathtext draws), the values that went in with their source, the
value that came out, and the reference: a standard with edition and clause, a published model, a data
set. The window shows the steps under "How it is computed" and the report prints them: a result that
cannot be shown this way is not given.

The sources are of six kinds, so the designer sees at a glance what to check:
- input: typed by the designer;
- default: chosen by Meridiana when nothing was typed, with the reason;
- data: a data set or a datasheet (PVGIS, a manufacturer, a catalogue), with its date;
- norm: a standard or a law, with edition, clause and page;
- model: a published physical model (Perez 1990, the PVsyst thermal model...);
- computed: the result of an earlier step.
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field

from ..i18n import _, number

KINDS = ("input", "default", "data", "norm", "model", "computed")


@dataclass(frozen=True)
class Source:
    kind: str
    label: str
    ref: str = ""

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"source kind {self.kind!r}")


@dataclass
class Quantity:
    symbol: str                 # LaTeX, without the dollars
    label: str
    value: float | int | str
    unit: str = ""
    source: Source | None = None
    decimals: int = 2

    def text(self) -> str:
        """The value as the window writes it, with its unit."""
        if isinstance(self.value, str):
            return self.value
        # a value that cannot be had (a rate with nothing produced): «–», as the tiles write it; the Quick gets it as
        # None, JSON having no NaN, and broke the Economics page with nought produced (06/11/2026)
        if self.value is None or not math.isfinite(float(self.value)):
            return "–"
        v = number(float(self.value), self.decimals)
        return f"{v} {self.unit}".strip()


@dataclass
class Step:
    key: str
    title: str
    formula: str                # LaTeX, without the dollars; "" when the step is a choice, not a formula
    explanation: str
    inputs: list[Quantity] = field(default_factory=list)
    result: Quantity | None = None
    reference: str = ""
    # the formula again with the numbers of one declared hour, LaTeX lines each ending in «= result» (R479,
    # energy/worked.py); the hour said above them; for the tests, where the calculation keeps each value
    worked: list[str] = field(default_factory=list)
    example: str = ""
    proof: list = field(default_factory=list)


@dataclass
class Record:
    """The steps of one calculation, in order."""
    title: str
    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> Quantity | None:
        self.steps.append(step)
        return step.result

    def find(self, key: str) -> Step | None:
        return next((s for s in self.steps if s.key == key), None)

    def merge(self, other: Record) -> None:
        self.steps.extend(other.steps)


def computed(label: str) -> Source:
    return Source("computed", label)


def kind_names() -> dict:
    return {"input": _("designer"), "default": _("default"), "data": _("data"), "norm": _("standard"),
            "model": _("model"), "computed": _("computed")}


def limits() -> list[str]:
    """What the energy model leaves out or only estimates, as the report and the page must say it (study
    18: B-calcoli section 7, B-pvsyst section 8)."""
    return [
        _("Bifacial modules: the light on the rear face is not computed (the bifaciality factor of the module is "
          "read and not used); a bifacial module counts as its front face."),
        _("Spectral correction: none (PVGIS counts about +1% for crystalline silicon in the Po valley)."),
        _("Degradation over the years and P50/P90: the production is the first year's (LID included); the yearly "
          "degradation acts in the economics only; no probability of exceedance (PVGIS gives the year-to-year "
          "spread of the irradiation)."),
        _("Snow: none. Soiling: one share for the whole year, not month by month."),
        _("MV transformer, MV lines, auxiliaries and the inverters' night consumption: none (1.5-2% on ground-mounted "
          "plants with an MV connection)."),
        _("Cables: shares at STC and at the nominal AC power, not lengths, sections and resistivity; no check of the "
          "voltage drop here."),
        _("Inverters: each connected unit is calculated separately with its nominal power, efficiency and input "
          "constraints. The conversion curve is PVWatts calibrated to the catalogued efficiency, not the full "
          "OND efficiency map; firmware, start-up hysteresis and dynamic MPPT tracking are not simulated."),
        _("Trackers: none, the modules are fixed."),
        _("Weather: the PVGIS typical year only; no Meteonorm, no measured years, no weather file of PVsyst."),
        _("Irradiance-level loss is an estimate based on one-diode parameters fitted to a few datasheet points, "
          "unless parameters are available in the module's PVsyst file."),
        _("Electrical shading reconstructs sampled current-voltage curves of differently illuminated cell groups, "
          "bypass sections, series strings and parallel MPPT inputs. Cell positions and internal connections are "
          "inferred when the manufacturer does not provide them. Bypass voltage drop and shade discretisation "
          "are modelling assumptions; reverse breakdown and hot spots are not simulated. A shaded module affects "
          "the common string current, not only the modules after it. Numerical reference tests are not field measurements."),
        _("Bypass layout comes from the module file when available; otherwise three bypass diodes and the cell "
          "layout inferred from the cell count are assumptions to verify against the manufacturer's diagram."),
        _("Optimizers: supported SolarEdge systems use the actual module groups, input operating window, "
          "current and output-voltage limits hour by hour when these are documented. Conversion efficiency "
          "remains fixed. Two modules on one optimizer share its MPPT. Missing limits are reported; other "
          "optimizer architectures, optional branch cables and proprietary firmware are not inferred."),
    ]
