"""How a result was computed, step by step: the formula in LaTeX (drawn by matplotlib's mathtext, so no
TeX installation is needed), the explanation, the values that went in with where each comes from, the
result and the reference. The same HTML goes into the report."""

from __future__ import annotations

import functools
import html
import io

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QApplication, QTextBrowser

from ..energy.pedigree import Record
from ..i18n import _
from .charts import CHROME, mode
from .design import strong
from .theme import marked


def kind_names() -> dict:
    return {"input": _("designer"), "default": _("default"), "data": _("data"), "norm": _("standard"),
            "model": _("model"), "computed": _("computed")}


@functools.lru_cache(maxsize=1024)
def formula_png(tex: str, color: str, dpi: float, size: float = 13.0) -> bytes:
    """The formula drawn in the ink of the theme on a transparent ground (matplotlib saves on white). Kept by
    its text, ink and size: the same formulas come back at every result, and drawing one costs some 40 ms
    (177 of them froze the window for 1.5-2 s at each computation, measured on 22/10/2026)."""
    import matplotlib
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image

    from .theme import matplotlib_fonts
    matplotlib_fonts()
    buf = io.BytesIO()
    with matplotlib.rc_context({"savefig.transparent": True}):
        math_to_image(f"${tex}$", buf, prop=FontProperties(size=size), dpi=dpi, format="png", color=color)
    return buf.getvalue()


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


def limits_html() -> str:
    """The section «What the model does not include», for the page and the report."""
    items = "".join(f"<li>{html.escape(t)}</li>" for t in limits())
    intro = _("The steps above are the whole of the calculation. What it leaves out, and what it only estimates, is "
              "listed here so that the report does not promise it.")
    return f"<h2>{html.escape(_('What the model does not include'))}</h2><p>{html.escape(intro)}</p><ul>{items}</ul>"


def records_html(records: list[Record], add_image, *, paper: bool = False) -> str:
    """The records as HTML, with the section on what the model does not include at the end; add_image(name,
    tex, size) registers a formula image and returns its URL."""
    from .document_style import css
    c = CHROME["light" if paper else mode()]
    kinds = kind_names()
    # The report supplies its paper CSS; screen values must never override it.
    parts = [] if paper else ["<style>" + css(ink=c['ink'], muted=c['muted'], rule=c['grid'],
                                             head=c['surface']) + "</style>"]
    n = 0
    for rec in records:
        parts.append(f"<h2>{html.escape(rec.title)}</h2>")
        for step in rec.steps:
            n += 1
            parts.append(f"<h3>{html.escape(step.title)}</h3>")
            if step.explanation:
                parts.append(f"<p>{html.escape(step.explanation)}</p>")
            if step.formula:
                parts.append(f"<p class='formula'><img src='{add_image(f'f{n}', step.formula, 14.0)}'></p>")
            rows = []
            for k, q in enumerate(step.inputs):
                symbol = f"<img src='{add_image(f's{n}_{k}', q.symbol, 11.0)}'>" if q.symbol else ""
                src = q.source
                where = ""
                if src is not None:
                    where = f"<span class='kind'>{html.escape(kinds.get(src.kind, src.kind))}</span>"
                    if src.label:
                        where += f": {html.escape(src.label)}"
                    if src.ref:
                        where += f" <span class='muted'>({html.escape(src.ref)})</span>"
                rows.append(f"<tr><td>{symbol}</td><td>{marked(html.escape(q.label))}</td><td align='right'>"
                            f"{marked(html.escape(q.text()))}</td><td>{where}</td></tr>")
            if step.result is not None:
                q = step.result
                symbol = f"<img src='{add_image(f'r{n}', q.symbol, 11.0)}'>" if q.symbol else ""
                rows.append(f"<tr class='result'><td>{symbol}</td><td>{strong(marked(html.escape(q.label)))}</td>"
                            f"<td align='right'>{strong(marked(html.escape(q.text())))}</td><td></td></tr>")
            if rows:
                heading = "".join(f"<th align='left'>{html.escape(label)}</th>" for label in
                                  (_("Symbol"), _("Quantity"), _("Value and unit"), _("Source")))
                parts.append("<table class='grid' width='100%' cellspacing='0' cellpadding='5'><thead><tr>"
                             + heading + "</tr></thead>" + "".join(rows) + "</table>")
            if step.reference:
                parts.append(f"<p class='muted'>{html.escape(_('Reference'))}: {html.escape(step.reference)}</p>")
    if records:
        parts.append(limits_html())
    return "".join(parts)


class PedigreeView(QTextBrowser):
    """The page drawn when it is on screen: a result that comes back while it is hidden is only noted, and
    two results in a row (the production, then its strings) are drawn once."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.records: list[Record] = []
        self.pending = False

    def show_records(self, records: list[Record]) -> None:
        self.records = records
        self.pending = True
        if self.isVisible():
            self._draw()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.pending:
            self._draw()

    def _draw(self) -> None:
        self.pending = False
        records = self.records
        doc = self.document()
        c = CHROME[mode()]
        app = QApplication.instance()
        dpr = self.devicePixelRatioF() if app is not None else 1.0

        def add_image(name: str, tex: str, size: float) -> str:
            url = QUrl(f"formula://{name}")
            try:
                data = formula_png(tex, c["ink"], 100 * dpr, size)
            except ValueError:
                return ""                         # a formula mathtext cannot draw: the text stays readable
            image = QImage.fromData(data, "PNG")
            image.setDevicePixelRatio(dpr)
            doc.addResource(QTextDocument.ResourceType.ImageResource, url, image)
            return url.toString()

        self.setHtml(records_html(records, add_image) if records else
                     f"<p>{html.escape(_('Nothing computed yet.'))}</p>")
