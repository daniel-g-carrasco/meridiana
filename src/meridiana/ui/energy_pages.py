"""The three energy pages of the window: production, consumption, balance and economics. Each is a form on
the left (what the designer sets, every field with its default) and the results on the right: a row of
headline numbers, the charts, and "How it is computed". The pages never compute: they show what the
window's energy job returned and report the designer's edits as (section, path, value)."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QRadioButton, QScrollArea, QStackedWidget,
                               QTabWidget, QVBoxLayout, QWidget)

from ..energy import consumption as cons
from ..energy.economics import Settings
from ..energy.simulate import Losses, thermal_names
from ..i18n import _, number
from .charts import Chart
from .help_box import help_button, register
from .pedigree import PedigreeView
from . import waiting
from .properties import combo, make_form, spin
from .design import Space
from .theme import mark, mark_problem
from .style import Group


def month_names() -> list[str]:
    return [_("Jan"), _("Feb"), _("Mar"), _("Apr"), _("May"), _("Jun"), _("Jul"), _("Aug"), _("Sep"), _("Oct"),
            _("Nov"), _("Dec")]


def stale_tip() -> str:
    """What the mark of values to update means (the tiles, the title of the phase)."""
    return _("To update: the project changed after this computation; «Compute» (F5) computes it again")


def split_unit(value: str) -> tuple[str, str]:
    """«92.410 kWh» as the number and its unit, for the unit to be written small (study 17, R2); a text without
    a number, or without a unit, stays whole."""
    head, _space, tail = value.rpartition(" ")
    if head and tail and any(ch.isdigit() for ch in head) and not any(ch.isdigit() for ch in tail):
        return head, tail
    return value, ""


class ElidedLabel(QLabel):
    """A tile's label: cut with «…» when the tile is narrow (five to a row in the middle card), whole in its
    tooltip; it never makes the tile wider."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setToolTip(text)

    def setText(self, text: str) -> None:
        super().setText(text)
        self.setToolTip(text)

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(24)
        return hint

    def paintEvent(self, event) -> None:
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        r = self.contentsRect()
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, r.width())
        self.style().drawItemText(p, r, int(self.alignment()), self.palette(), self.isEnabled(), text,
                                  self.foregroundRole())


class Tile(QFrame):
    """A headline number as a card without a border (study 17, R2, Daniel's choice of 23/10/2026): the label, the
    number with its unit beside it, a line of detail (the source), in the catalogue's styles (R121). The `key` tile,
    the number that counts on the page, comes first; no longer in the accent's tint (R104: «lo vorrei un po' meno
    presente il colore di accento»)."""

    def __init__(self, label: str, key: bool = False):
        super().__init__()
        self.setObjectName("tile")
        self.setProperty("key", key)
        self.setFrameShape(QFrame.Shape.NoFrame)
        from .design import Text, set_text
        self.label = set_text(ElidedLabel(label), Text.SECONDARY)       # the label of a result
        self.value = set_text(QLabel("–"), Text.DISPLAY)                # the figure of a result
        self.unit = set_text(QLabel(""), Text.DESCRIPTION)
        self.unit.hide()
        self.detail = set_text(QLabel(""), Text.SECONDARY)
        self.detail.setWordWrap(True)
        box = QVBoxLayout(self)
        box.setContentsMargins(12, 8, 12, 8)
        box.setSpacing(2)
        box.addWidget(self.label)
        number = QHBoxLayout()
        number.setSpacing(4)
        number.addWidget(self.value)
        number.addWidget(self.unit, 0, Qt.AlignmentFlag.AlignBottom)
        number.addStretch(1)
        box.addLayout(number)
        box.addWidget(self.detail)

    def set(self, value: str, detail: str = "") -> None:
        number, unit = split_unit(value)
        self.value.setText(number)
        self.unit.setText(unit)
        self.unit.setVisible(bool(unit))
        self.detail.setText(detail)

    def text(self) -> str:
        """What the tile says, number and unit together (as `set` was given it)."""
        return f"{self.value.text()} {self.unit.text()}".strip()


class Tiles(QWidget):
    """The headline numbers in rows that follow the width: as many to a row as fit, at least one; the first is
    the key one unless `key` says another (none with -1)."""
    TILE = 165                                  # logical pixels a tile wants (five in the middle card of 1600 px)

    def __init__(self, labels: list[str], columns: int = 5, key: int = 0):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(8)
        self.most = columns
        self.columns = 0
        self.tiles = [Tile(label, key=i == key) for i, label in enumerate(labels)]
        for t in self.tiles:
            t.setMinimumWidth(120)
        self._place(columns)

    def _place(self, columns: int) -> None:
        if columns == self.columns:
            return
        self.columns = columns
        for t in self.tiles:
            self.grid.removeWidget(t)
        for i, t in enumerate(self.tiles):
            self.grid.addWidget(t, i // columns, i % columns)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place(max(1, min(self.most, self.width() // self.TILE)))

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(130)
        return hint

    def __getitem__(self, i: int) -> Tile:
        return self.tiles[i]

    def helps(self, ids) -> None:
        """The «?» of each tile, by its help in help.py; the help box follows the pointer over them (task 17d)."""
        for tile, hid in zip(self.tiles, ids, strict=True):        # one help per tile, no tile without
            help_button(tile, hid, hover=True, beside=tile.label)


def year_carpet(hourly, months: list[str]):
    """The year as a carpet (R63): 24 rows of hours, a column for each day; the hour the clock repeats in autumn
    averaged, the one it skips in spring between its neighbours; the days' names and the months' starts for the
    axis."""
    import numpy as np
    import pandas as pd
    idx = hourly.index
    table = pd.DataFrame({"v": hourly.to_numpy(), "d": idx.dayofyear, "h": idx.hour}).pivot_table(
        index="h", columns="d", values="v", aggfunc="mean").reindex(range(24))
    days = list(table.columns)
    dates = pd.Timestamp(year=int(idx[0].year), month=1, day=1) + pd.to_timedelta(np.asarray(days) - 1, unit="D")
    cols = [f"{d.day} {months[d.month - 1]}" for d in dates]
    ticks = [(j, months[d.month - 1]) for j, d in enumerate(dates) if d.day == 1]
    # the hour the clock skips in spring, between the two beside it (it came out as nought)
    table = table.interpolate(axis=0, limit_direction="both")
    return table.fillna(0.0).to_numpy(), cols, ticks


def scrolled(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(widget)
    area.setMinimumWidth(280)
    area.setMinimumHeight(160)
    return area


class FittedBox(QVBoxLayout):
    """The results of a page, as tall as the room in the middle card: a wrapped line (the weather's strip) made the
    scroll area size them for their preferred height (QScrollArea asks the layout for its height for width), and
    the charts' 480 px pushed the strip under the card's edge. They scroll only below their minimum."""

    def hasHeightForWidth(self) -> bool:
        return False


def chart_card(tabs: QTabWidget) -> QFrame:
    """The charts of a page in a card of their own, their tabs as pills inside it (D2 and the drafts of the
    phases, 24/10/2026)."""
    card = QFrame()
    card.setObjectName("chart-card")
    box = QVBoxLayout(card)
    box.setContentsMargins(8, 6, 8, 8)
    box.addWidget(tabs)
    return card


class Page(QWidget):
    edited = Signal(str, str, object)        # section ("energy", "consumption", "economics"), path, value
    computeRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # the drafts of the phases (docs/studio/19-grafica/fasi.py, Daniel 24/10/2026: «bellissimi»): what is
        # typed stands in the right column, as the model's properties (`side`, given to the window's inspector);
        # the page in the middle holds the results, the tiles and the charts (`centre`)
        self.form = QWidget()
        self.form_box = QVBoxLayout(self.form)
        self.form_box.setContentsMargins(Space.L, Space.XXS, Space.L, Space.L)     # the 10 below on the scale
        self.results = QWidget()
        self.results_box = FittedBox(self.results)
        # on the scale (Daniel, 25/10/2026): 16 all round, 12 between the parts (they were 14 and 10)
        self.results_box.setContentsMargins(Space.XL, Space.XL, Space.XL, Space.XL)
        self.results_box.setSpacing(Space.L)
        self.side = scrolled(self.form)
        self.side.setMinimumWidth(0)
        self.centre = scrolled(self.results)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self.centre)
        self.setMinimumWidth(320)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.loading = False                 # filling the form from the project: no edits sent
        self.stale = False                   # the values are those of a year computed before the last change
        # the arc in the top right corner of the results while the year is computed, past the threshold (study
        # 16, F3): where the designer looks, besides the words in the status bar
        self.spinner = waiting.Spinner(self.centre, 24,
                                       tip=_("Computing: the values shown are the last ones until the new ones come"))
        waiting.pin(self.spinner, self.centre)
        self.computing = waiting.Delayed(self.spinner, self)

    def set_computing(self, on: bool) -> None:
        """The year is being computed (on) or is back (off): the arc, only if it takes longer than the threshold."""
        if on:
            self.computing.begin()
        else:
            self.computing.end()

    def set_stale(self, on: bool) -> None:
        """The headline numbers of the last year in the theme's muted grey while the project has changed after it was
        computed, still there to read (Daniel, 23/10/2026: grey, not struck through); the phase's title carries the
        mark (the window). The charts keep their colours: the numbers say it."""
        self.stale = on
        tip = stale_tip() if on else ""
        for tile in getattr(getattr(self, "tiles", None), "tiles", []):
            waiting.set_stale(tile.value, on)
            tile.setToolTip(tip)

    def send(self, section: str, path: str, value) -> None:
        if not self.loading:
            self.edited.emit(section, path, value)

    def compute_button(self) -> QPushButton:
        """«Compute», the one button full of accent on the page (study 17, C2: one per page)."""
        b = QPushButton(_("Compute"))
        b.setProperty("primary", True)
        b.clicked.connect(self.computeRequested.emit)
        return b


# production

class EnergyPage(Page):
    fetchRequested = Signal()
    inverterRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        f = self.form_box
        # the weather of the site, a strip under the charts (the drafts of the phases): what it is, its two
        # choices of shading and the button that fetches it again
        self.meteo_strip = QFrame()
        self.meteo_strip.setObjectName("strip")
        strip = QVBoxLayout(self.meteo_strip)
        strip.setContentsMargins(12, 6, 8, 6)
        strip.setSpacing(4)
        mf = QHBoxLayout()
        mf.setSpacing(12)
        self.meteo_label = QLabel(_("Not fetched yet."))
        self.meteo_label.setWordWrap(True)
        fetch = QPushButton(_("Fetch the typical year and the horizon from PVGIS"))
        fetch.clicked.connect(self.fetchRequested.emit)
        self.use_horizon = QCheckBox(_("Shading of the far horizon"))
        self.use_horizon.toggled.connect(lambda v: self.send("energy", "losses.use_horizon", v))
        self.use_near = QCheckBox(_("Shading of the obstacles of the scene"))
        self.use_near.setToolTip(_("Exclusions with a height, parapets and the other buildings cast their shadows "
                                   "on the modules"))
        self.use_near.toggled.connect(lambda v: self.send("energy", "losses.use_near", v))
        strip.addWidget(self.meteo_label)
        mf.addWidget(fetch)                          # first: the corner on the right is Meridio's
        mf.addWidget(self.use_horizon)
        mf.addWidget(self.use_near)
        mf.addStretch(1)
        strip.addLayout(mf)

        arrays = Group(_("Arrays (the modules laid, by orientation)"))
        af = QVBoxLayout(arrays)
        from .rows import RowList
        self.arrays = RowList(_("No module laid yet."))      # rows to read, not a table in the card (R79)
        af.addWidget(self.arrays)
        self.thermal_box = QWidget()
        self.thermal_form = make_form(self.thermal_box)
        af.addWidget(QLabel(_("Cooling of the modules' back (thermal model):")))
        af.addWidget(self.thermal_box)
        f.addWidget(arrays)

        inv = Group(_("Inverter"))
        inf = make_form(inv)
        self.inv_label = QLabel()
        self.inv_label.setWordWrap(True)
        choose = QPushButton(_("Choose from the catalogue…"))
        choose.clicked.connect(self.inverterRequested.emit)
        auto = QPushButton(_("Size it by itself"))
        auto.clicked.connect(lambda: self.send("energy", "inverter", None))
        # one under the other, as in the Plant's panel: side by side they made the form wider than its card
        row = QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(choose)
        row.addWidget(auto)
        holder = QWidget()
        holder.setLayout(row)
        self.inv_count = spin(1, 500, 1, "", 0, 1)
        self.inv_count.valueChanged.connect(lambda v: self.send("energy", "inverter_count", int(v)))
        self.ratio = spin(0.5, 2.0, 1.1, "", 2, 0.05)
        self.ratio.valueChanged.connect(lambda v: self.send("energy", "dc_ac_ratio", v))
        inf.addRow(self.inv_label)
        inf.addRow(holder)
        inf.addRow(_("How many"), self.inv_count)
        inf.addRow(_("DC/AC ratio when sized by itself"), self.ratio)
        f.addWidget(inv)

        strings = Group(_("Strings (CEI 64-8/7)"))
        sf_ = make_form(strings)
        self.t_min = spin(-40, 20, -10, " °C", 1, 1)
        self.t_min.valueChanged.connect(lambda v: self.send("energy", "t_min", v))
        self.n_series = spin(0, 60, 0, "", 0, 1)
        self.n_series.setSpecialValueText(_("suggested"))
        self.n_series.valueChanged.connect(self._layout_changed)
        self.per_mppt = QLineEdit()
        self.per_mppt.setPlaceholderText(_("e.g. 2;1 (strings on input 1 and 2)"))
        self.per_mppt.editingFinished.connect(self._layout_changed)
        self.strings_label = QLabel(_("Compute to see the strings."))
        self.strings_label.setWordWrap(True)
        self.strings_label.setTextFormat(Qt.TextFormat.RichText)
        sf_.addRow(_("Lowest temperature of the site"), self.t_min)
        sf_.addRow(_("Modules in series"), self.n_series)
        sf_.addRow(_("Strings on each input"), self.per_mppt)
        sf_.addRow(self.strings_label)
        f.addWidget(strings)

        loss = Group(_("Losses"))
        lf = make_form(loss)
        self.loss = {}
        d = Losses()
        self.transposition = combo((("perez", "Perez 1990"), ("haydavies", "Hay e Davies"), ("isotropic", _("isotropic"))),
                                   d.transposition)
        self.transposition.currentIndexChanged.connect(
            lambda _i: self.send("energy", "losses.transposition", self.transposition.currentData()))
        lf.addRow(_("Transposition model"), self.transposition)
        for key, label, lo, hi, dec, unit in (
                ("albedo", _("Ground reflectance (albedo)"), 0.0, 1.0, 2, ""),
                ("soiling", _("Soiling"), 0.0, 20.0, 1, " %"), ("quality", _("Module quality"), -5.0, 5.0, 1, " %"),
                ("mismatch", _("Mismatch"), 0.0, 10.0, 1, " %"), ("dc_wiring", _("DC wiring at STC"), 0.0, 10.0, 1, " %"),
                ("ac_wiring", _("AC wiring at nominal power"), 0.0, 10.0, 1, " %"),
                ("unavailability", _("Unavailability"), 0.0, 20.0, 1, " %"), ("iam_b0", _("ASHRAE b0 (reflection)"), 0.0, 0.2, 3, "")):
            s = spin(lo, hi, getattr(d, key), unit, dec, 0.1 if dec <= 1 else 0.01)
            s.valueChanged.connect(lambda v, k=key: self.send("energy", f"losses.{k}", v))
            lf.addRow(label, s)
            self.loss[key] = s
        self.lid_auto = QCheckBox(_("LID from the module's datasheet"))
        self.lid = spin(0.0, 10.0, 1.0, " %", 1, 0.1)
        self.lid_auto.toggled.connect(lambda v: (self.lid.setEnabled(not v),
                                                 self.send("energy", "losses.lid", None if v else self.lid.value())))
        self.lid.valueChanged.connect(lambda v: self.send("energy", "losses.lid", v) if not self.lid_auto.isChecked() else None)
        lf.addRow(self.lid_auto)
        lf.addRow(_("Light-induced degradation"), self.lid)
        f.addWidget(loss)
        f.addWidget(self.compute_button())
        f.addWidget(self.status)
        f.addStretch(1)

        r = self.results_box
        self.tiles = Tiles([_("Energy a year"), _("Specific yield"), _("Performance ratio"), _("Power"),
                            _("PVGIS, second opinion")])
        self.tiles.helps(("production.energy", "production.specific_yield", "production.pr", "production.power",
                          "production.pvgis"))
        r.addWidget(self.tiles)
        tabs = QTabWidget()
        self.monthly = Chart(_("Production month by month"))
        self.losses_chart = register(Chart(_("From the sun to the meter: each step")), "production.losses")
        self.day = Chart(_("Average production by hour and month"))
        self.pedigree = PedigreeView()
        tabs.addTab(self.monthly, _("Months"))
        tabs.addTab(self.losses_chart, _("Losses"))
        tabs.addTab(self.day, _("Typical day"))
        tabs.addTab(self.pedigree, _("How it is computed"))
        r.addWidget(chart_card(tabs), 1)
        r.addWidget(self.meteo_strip)
        self.monthly.message(_("Lay the modules of a sub-field, then compute."))

    def show_project(self, project, arrays: list) -> None:
        self.loading = True
        try:
            e = project.energy or {}
            losses = Losses.from_dict(e.get("losses"))
            self.use_horizon.setChecked(losses.use_horizon)
            self.use_near.setChecked(losses.use_near)
            self.transposition.setCurrentIndex(max(0, self.transposition.findData(losses.transposition)))
            for k, s in self.loss.items():
                s.setValue(float(getattr(losses, k)))
            self.lid_auto.setChecked(losses.lid is None)
            self.lid.setEnabled(losses.lid is not None)
            if losses.lid is not None:
                self.lid.setValue(float(losses.lid))
            self.inv_count.setValue(int(e.get("inverter_count") or 1))
            self.t_min.setValue(float(e.get("t_min") if e.get("t_min") is not None else -10.0))
            layout = e.get("strings") or {}
            self.n_series.setValue(int(layout.get("n_series") or 0))
            self.per_mppt.setText(";".join(str(x) for x in layout.get("per_mppt") or []))
            self.ratio.setValue(float(e.get("dc_ac_ratio") or 1.1))
            rec = e.get("inverter")
            self.inv_label.setText(_("{maker} {model}, {kw} kW AC").format(
                maker=rec.get("manufacturer", ""), model=rec.get("model", ""),
                kw=number(float(rec.get("ac_power_nominal_w") or 0) / 1000.0, 1)) if rec else
                _("Not chosen: sized by itself at the DC/AC ratio below."))
            self.arrays.set_rows([
                (a.name, _("{n} modules · {kwp} kWp · tilt {tilt}° · azimuth {az}°").format(
                    n=a.modules, kwp=number(a.p_stc / 1000.0, 2), tilt=number(a.tilt, 1), az=number(a.azimuth, 1)))
                for a in arrays])
            while self.thermal_form.rowCount():
                self.thermal_form.removeRow(0)
            seen = set()
            for a in arrays:
                sfid = a.key.split(".")[0]
                if sfid in seen:
                    continue
                seen.add(sfid)
                c = combo(thermal_names().items(), a.thermal)
                c.currentIndexChanged.connect(lambda _i, w=c, s=sfid: self.send("energy", f"thermal.{s}", w.currentData()))
                self.thermal_form.addRow(a.name.split(" ")[0] if len(a.name) > 18 else a.name, c)
        finally:
            self.loading = False

    def _layout_changed(self, *_a) -> None:
        n = int(self.n_series.value())
        try:
            per = [int(x) for x in self.per_mppt.text().replace(",", ";").split(";") if x.strip()]
            self.per_mppt.setToolTip("")
            mark_problem(self.per_mppt, False)
        except ValueError:
            per = []
            self.per_mppt.setToolTip(_("Whole numbers separated by ; are expected, one per input: 2; 2; 1"))
            mark_problem(self.per_mppt, True)          # said, not dropped in silence, in the theme's danger
        self.send("energy", "strings", {"n_series": n, "per_mppt": per} if n and per else None)

    def show_strings(self, info: dict, sim) -> None:
        if info.get("error") or "plan" not in info:
            self.strings_label.setText(info.get("error", ""))
            if sim is not None:
                self.pedigree.show_records([sim.record])
            return
        plan = info["plan"]
        head = (_("Suggested: {n} modules in series, strings on the inputs {per} ({used} of {total} modules on each "
                  "inverter).") if getattr(plan, "suggested", False) else
                _("{n} modules in series, strings on the inputs {per} ({used} of {total} modules on each inverter)."))
        rows = []
        marks = {"ok": "✔", "warn": "⚠", "fail": "✘", "info": "ℹ"}
        for c in plan.checks:
            rows.append(f"<tr><td>{mark(marks.get(c.level, '✔'))}</td><td>{c.label}</td><td>{c.detail}</td></tr>")
        span = _("Range of modules in series: {lo} to {hi}. Coldest morning {t} °C, hottest cell {c} °C.").format(
            lo=plan.n_series_min, hi=plan.n_series_max, t=number(info["t_min"], 1), c=number(info["t_cell_max"], 0))
        self.strings_label.setText(f"<p>{head.format(n=plan.n_series, per=';'.join(map(str, plan.strings_per_mppt)), used=plan.modules, total=info['modules'])}</p>"
                                   f"<p>{span}</p><table>{''.join(rows)}</table>")
        if sim is not None:
            self.pedigree.show_records([sim.record, plan.record])

    def show_meteo(self, text: str) -> None:
        self.meteo_label.setText(text)

    def show_results(self, sim, pvgis, error: str = "") -> None:
        if error or sim is None:
            self.status.setText(error)
            self.monthly.message(error or _("Nothing to compute yet."))
            return
        self.status.setText("\n".join(sim.notes))
        t = self.tiles
        t[0].set(f"{number(sim.energy_kwh, 0, grouping=True)} kWh", _("typical year"))
        t[1].set(f"{number(sim.specific_yield, 0, grouping=True)} kWh/kWp")
        t[2].set(f"{number(100 * sim.pr, 1)} %", "IEC 61724-1")
        t[3].set(f"{number(sim.p_stc_kw, 2)} kWp", _("{kw} kW AC, DC/AC {r}").format(
            kw=number(sim.p_ac_kw, 1), r=number(sim.p_stc_kw / sim.p_ac_kw, 2) if sim.p_ac_kw else "–"))
        months = month_names()
        series = [(_("Meridiana"), [float(v) for v in sim.monthly.e_ac.to_numpy()])]
        if pvgis is not None:
            diff = 100.0 * (sim.energy_kwh / pvgis.yearly_kwh - 1.0) if pvgis.yearly_kwh else 0.0
            t[4].set(f"{number(pvgis.yearly_kwh, 0, grouping=True)} kWh",
                     _("Meridiana {d}%. PVGIS: crystSi2025 technology, average of the years 2005-2023 (SARAH3); "
                       "Meridiana: typical year").format(
                         d=number(diff, 1, sign=True)))
            series.append((_("PVGIS, PVcalc"), [float(v) for v in pvgis.monthly_kwh]))
        else:
            t[4].set("–", _("not available without the network"))
        self.monthly.bars(months, series, "kWh")
        steps = [c for c in sim.chain if c.change is not None]
        self.losses_chart.changes([c.label for c in steps], [float(c.change) for c in steps], "%")
        h = sim.hourly
        matrix = np.zeros((12, 24))
        for m in range(12):
            sel = h[h.index.month == m + 1]
            matrix[m] = sel.p_ac.groupby(sel.index.hour).mean().reindex(range(24), fill_value=0.0).to_numpy() / 1000.0
        self.day.heatmap(matrix, months, [f"{k}" for k in range(24)], "kW")
        self.pedigree.show_records([sim.record])


# consumption

class ConsumptionPage(Page):
    importRequested = Signal(str, str)        # path, unit

    def __init__(self, parent=None):
        super().__init__(parent)
        f = self.form_box
        pod = Group(_("Supply point (POD)"))
        pf = make_form(pod)
        self.pod = QLineEdit()
        self.pod.setPlaceholderText("IT001E12345678")
        self.pod_check = QLabel("")
        self.pod.editingFinished.connect(self._pod)
        self.supply = combo((("auto", _("Automatic")), *self.supply_names().items()), "auto")
        self.supply.currentIndexChanged.connect(lambda _i: self.send("consumption", "supply", self.supply.currentData()))
        self.power = spin(0, 10000, 0.0, " kW", 1, 0.5)
        self.power.setSpecialValueText(_("automatic"))
        self.power.valueChanged.connect(lambda v: self.send("consumption", "contract_kw", v))
        pf.addRow(_("POD code"), self.pod)
        pf.addRow(self.pod_check)
        pf.addRow(_("Supply"), self.supply)
        pf.addRow(_("Contracted power"), self.power)
        f.addWidget(pod)

        data = Group(_("Consumption"))
        df = QVBoxLayout(data)
        self.profile = combo((("auto", _("Automatic")), *cons.profile_names().items()), "auto")
        self.profile.currentIndexChanged.connect(lambda _i: self.send("consumption", "profile", self.profile.currentData()))
        prof = make_form()
        prof.addRow(_("Typical profile"), self.profile)
        df.addLayout(prof)
        self.guess_note = QLabel("")
        self.guess_note.setWordWrap(True)
        df.addWidget(self.guess_note)
        self.mode = QButtonGroup(self)
        self.pages = QStackedWidget()
        modes = ((_("Yearly total"), "annual"), (_("Yearly, by band"), "bands"), (_("Month by month and band (bills)"), "bills"),
                 (_("Measured curve (CSV)"), "measured"))
        for k, (label, key) in enumerate(modes):
            b = QRadioButton(label)
            b.setProperty("key", key)
            self.mode.addButton(b, k)
            df.addWidget(b)
        self.mode.idClicked.connect(self._mode)
        # yearly
        w = QWidget()
        wf = make_form(w)
        self.annual = spin(0, 1e9, 0, " kWh", 0, 100)
        self.annual.setSpecialValueText(_("automatic"))
        self.annual.valueChanged.connect(lambda v: self.send("consumption", "annual_kwh", v))
        wf.addRow(_("Yearly consumption"), self.annual)
        self.pages.addWidget(w)
        # by band
        w = QWidget()
        wf = make_form(w)
        self.band_spins = {}
        for b in ("F1", "F2", "F3"):
            s = spin(0, 1e9, 0, " kWh", 0, 100)
            s.valueChanged.connect(lambda _v: self.send("consumption", "bands_kwh",
                                                        {k: x.value() for k, x in self.band_spins.items()}))
            wf.addRow(b, s)
            self.band_spins[b] = s
        self.pages.addWidget(w)
        # bills
        # the bills month by month in F1, F2, F3: number fields in a grid with the totals, not a table (R79)
        from .rows import FieldGrid
        bills_page = QWidget()
        bl = QVBoxLayout(bills_page)
        bl.setContentsMargins(0, 0, 0, 0)
        self.bills_note = QLabel(_("Started from the estimate in hand: write over it what the bills say."))
        self.bills_note.setWordWrap(True)
        from .design import Text, set_text
        set_text(self.bills_note, Text.SECONDARY)
        bl.addWidget(self.bills_note)
        self.bills = FieldGrid(month_names(), ["F1", "F2", "F3"], "kWh")
        self.bills.changed.connect(self._bills)
        bl.addWidget(self.bills)
        self.pages.addWidget(bills_page)
        self.estimate: list = []                    # the load in hand month by month and band, for the bills
        # measured
        w = QWidget()
        wl = QVBoxLayout(w)
        self.measured_label = QLabel(_("No curve imported."))
        self.measured_label.setWordWrap(True)
        self.unit = combo((("kWh", _("energy per interval (kWh)")), ("kW", _("average power (kW)"))), "kWh")
        imp = QPushButton(_("Import a CSV…"))
        imp.clicked.connect(self._import)
        wl.addWidget(self.measured_label)
        wl.addWidget(self.unit)
        wl.addWidget(imp)
        self.pages.addWidget(w)
        df.addWidget(self.pages)
        f.addWidget(data)
        f.addWidget(self.compute_button())
        f.addWidget(self.status)
        f.addStretch(1)

        r = self.results_box
        self.tiles = Tiles([_("Consumption a year"), "F1", "F2", "F3", _("Highest hour"), _("Base load"),
                            _("Load factor"), _("Between 8 and 18"), _("Weekends and holidays")])
        self.tiles.helps(("consumption.year",) + ("consumption.bands",) * 3 + ("consumption.shape",) * 5)
        r.addWidget(self.tiles)
        tabs = QTabWidget()
        self.monthly = Chart(_("Consumption month by month, by band"))
        self.day = Chart(_("Average consumption by hour and month"))
        self.week = Chart(_("Average week, hour by hour"))
        self.duration = Chart(_("Load duration curve: the hours of the year from the highest load"))
        self.year_map = Chart(_("The year hour by hour: each column a day, each row an hour"))     # R63
        self.pedigree = PedigreeView()
        tabs.addTab(self.monthly, _("Months"))
        tabs.addTab(self.day, _("Typical day"))
        tabs.addTab(self.year_map, _("Year"))
        tabs.addTab(self.week, _("Week"))
        tabs.addTab(self.duration, _("Duration"))
        tabs.addTab(self.pedigree, _("How it is computed"))
        r.addWidget(chart_card(tabs), 1)

    @staticmethod
    def supply_names() -> dict:
        return {"domestic": _("Domestic"), "other_lv": _("Other uses, low voltage"), "mv": _("Medium voltage")}

    def _pod(self) -> None:
        text = self.pod.text().strip().upper().replace(" ", "")
        self.pod_check.setText("" if not text or cons.valid_pod(text) else
                               _("A POD is IT, three digits, E and eight digits: check it on the bill."))
        self.send("consumption", "pod", text)

    def _mode(self, k: int) -> None:
        self.pages.setCurrentIndex(k)
        key = self.mode.button(k).property("key")
        # the source used is the best one filled: switching clears the better ones
        if self.loading:
            return
        if key in ("annual", "bands", "bills"):
            self.send("consumption", "measured", [])
        if key in ("annual", "bands"):
            self.send("consumption", "monthly_bands_kwh", [])
        if key == "bills" and not any(sum(r.values()) for r in self.bills.values()) and len(self.estimate) == 12:
            # no bills yet: the grid starts from the estimate, and the choice stays (it went back to the annual
            # total, the data having nothing for it)
            rows = [{k: round(v) for k, v in r.items()} for r in self.estimate]
            self.bills.set_values(rows)
            self.bills_note.show()
            self.send("consumption", "monthly_bands_kwh", rows)
        if key == "annual":
            self.send("consumption", "bands_kwh", {})

    def _bills(self, rows: list) -> None:
        if self.loading:
            return
        self.bills_note.hide()                      # the designer's figures now
        self.send("consumption", "monthly_bands_kwh", rows)

    def _import(self) -> None:
        name, _f = QFileDialog.getOpenFileName(self, _("Import a load curve"), "", _("CSV files (*.csv *.txt)"))
        if name:
            self.importRequested.emit(name, self.unit.currentData())

    def show_project(self, project, ctx=None) -> None:
        self.loading = True
        try:
            c = cons.Consumption.from_dict(project.consumption)
            g = cons.guess(ctx or cons.Context())
            self.pod.setText(c.pod)
            self.supply.setItemText(0, _("Automatic: {name}").format(name=self.supply_names()[g.supply]))
            self.supply.setCurrentIndex(max(0, self.supply.findData(c.supply)))
            self.power.setSpecialValueText(_("automatic: {kw} kW").format(kw=number(g.contract_kw, 1)))
            self.power.setValue(float(c.contract_kw or 0))
            self.profile.setItemText(0, _("Automatic: {name}").format(name=cons.profile_names()[g.profile]))
            self.profile.setCurrentIndex(max(0, self.profile.findData(c.profile)))
            self.annual.setSpecialValueText(_("automatic: {kwh} kWh").format(kwh=number(g.annual_kwh, 0, grouping=True)))
            self.annual.setValue(float(c.annual_kwh or 0))
            for spin_box in (self.power, self.annual):     # the automatic value is longer than the numbers
                spin_box.setMinimumWidth(spin_box.fontMetrics().horizontalAdvance(spin_box.specialValueText()) + 48)
            auto = c.profile == "auto" or not c.has_data()
            self.guess_note.setVisible(auto)
            self.guess_note.setText(_("What is automatic is guessed from the project: {why}. Enter the bills or the "
                                      "curve of the POD for a real result.").format(why=g.why) if auto else "")
            for b, s in self.band_spins.items():
                s.setValue(float((c.bands_kwh or {}).get(b, 0) or 0))
            self.bills.set_values(c.monthly_bands_kwh if len(c.monthly_bands_kwh) == 12 else [])
            k = 3 if c.measured else 2 if c.monthly_bands_kwh else 1 if any((c.bands_kwh or {}).values()) else 0
            self.mode.button(k).setChecked(True)
            self.pages.setCurrentIndex(k)
            self.measured_label.setText(_("{n} values imported.").format(n=len(c.measured)) if c.measured else
                                        _("No curve imported."))
        finally:
            self.loading = False

    def show_results(self, load, error: str = "") -> None:
        if error or load is None:
            self.status.setText(error)
            return
        self.status.setText("")
        self.estimate = load.monthly_by_band()     # where the bills' grid starts when it is empty
        by = load.by_band()
        total = load.annual_kwh or 1.0
        t = self.tiles
        t[0].set(f"{number(load.annual_kwh, 0, grouping=True)} kWh", load.basis)
        for i, b in enumerate(("F1", "F2", "F3")):
            t[i + 1].set(f"{number(100 * by[b] / total, 0)} %", f"{number(by[b], 0, grouping=True)} kWh")
        t[4].set(f"{number(float(load.hourly.max()), 2)} kWh", _("in one hour"))
        fig = load.figures()
        t[5].set(f"{number(fig['base_kw'], 2)} kW", _("never below it in 95% of the hours"))
        t[6].set(f"{number(100 * fig['load_factor'], 0)} %", _("mean load over the highest"))
        t[7].set(f"{number(100 * fig['day_share'], 0)} %", _("of the consumption, when a system produces most"))
        t[8].set(f"{number(100 * fig['off_share'], 0)} %", _("of the consumption"))
        from ..energy import bands
        b = bands.band_of(load.hourly.index)
        months = month_names()
        series = []
        for band in ("F1", "F2", "F3"):
            s = load.hourly[b == band]
            series.append((band, [float(v) for v in s.groupby(s.index.month).sum().reindex(range(1, 13), fill_value=0)]))
        self.monthly.bars(months, series, "kWh", stacked=True)
        h = load.hourly
        matrix = np.zeros((12, 24))
        for m in range(12):
            sel = h[h.index.month == m + 1]
            matrix[m] = sel.groupby(sel.index.hour).mean().reindex(range(24), fill_value=0.0).to_numpy()
        self.day.heatmap(matrix, months, [f"{k}" for k in range(24)], "kWh/h", 2)
        carpet, cols, ticks = year_carpet(h, months)
        self.year_map.heatmap(carpet, [f"{k}:00" for k in range(24)], cols, "kWh/h", 2, ticks=ticks,
                              row_ticks=[(k, f"{k}") for k in range(0, 24, 3)])
        days = [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]
        week = load.week()
        self.week.line(list(range(168)), [(_("average load"), [float(v) for v in week])], "kW", "", 2,
                       ticks=[(24 * d + 12, days[d]) for d in range(7)],
                       names=[f"{days[h // 24]} {h % 24}:00" for h in range(168)])
        curve = load.duration()
        step = 24                                  # a point a day is enough to read the curve
        self.duration.line(list(range(0, len(curve), step)), [(_("load"), [float(v) for v in curve[::step]])], "kW",
                           _("hours of the year"), 2)
        self.pedigree.show_records([load.record])


# balance and economics

class EconomicsPage(Page):
    batteryRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        f = self.form_box
        d = Settings()
        self.fields = {}

        def group(title, rows):
            g = Group(title)
            gf = make_form(g)
            for key, label, lo, hi, dec, unit, step in rows:
                s = spin(lo, hi, getattr(d, key), unit, dec, step)
                s.valueChanged.connect(lambda v, k=key: self.send("economics", k, v))
                gf.addRow(label, s)
                self.fields[key] = s
            f.addWidget(g)
            return gf

        bought = group(_("Energy bought (every variable cost, taxes included)"), (
            ("buy_f1", "F1", 0, 2, 3, " €/kWh", 0.01), ("buy_f2", "F2", 0, 2, 3, " €/kWh", 0.01),
            ("buy_f3", "F3", 0, 2, 3, " €/kWh", 0.01)))
        register(bought.parentWidget(), "economics.prices")      # F1 on a price: what the defaults are (17d)
        fed = group(_("Energy fed in"), (("sell", _("Value (dedicated withdrawal)"), 0, 1, 3, " €/kWh", 0.005),))
        self.limit = spin(-1, 100000, -1, " kW", 1, 1)
        self.limit.setSpecialValueText(_("no limit"))
        self.limit.valueChanged.connect(lambda v: self.send("economics", "export_limit_kw", v))
        fed.addRow(_("Export limit (0: zero export)"), self.limit)
        cer = group(_("Renewable energy community"), (
            ("shared_pct", _("Share of the energy fed in that is shared"), 0, 100, 0, " %", 5),
            ("pz", _("Zonal price expected"), 0, 1000, 0, " €/MWh", 5),
            ("trase", _("TRASE of the year (ARERA)"), 0, 0.1, 4, " €/kWh", 0.0005),
            ("grant_pct", _("Capital grant"), 0, 40, 0, " %", 5)))
        self.community = QCheckBox(_("The system is in a community (CER)"))
        self.community.toggled.connect(lambda v: self.send("economics", "community", v))
        cer.insertRow(0, self.community)
        self.zone = combo((("", _("from the site's address")), ("north", _("North (+10 €/MWh)")),
                           ("centre", _("Centre (+4 €/MWh)")), ("other", _("South and islands"))), "")
        self.zone.currentIndexChanged.connect(lambda _i: self.send("economics", "zone", self.zone.currentData()))
        cer.addRow(_("Zone for the PV correction"), self.zone)
        store = Group(_("Storage"))
        stf = make_form(store)
        self.battery_label = QLabel(_("No battery."))
        self.battery_label.setWordWrap(True)
        pick = QPushButton(_("Choose a battery from the catalogue…"))
        pick.clicked.connect(self.batteryRequested.emit)
        none = QPushButton(_("No battery"))
        none.clicked.connect(lambda: self.send("economics", "battery", None))
        # one under the other: side by side they made the form wider than its card and cut its right edge
        row = QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(pick)
        row.addWidget(none)
        holder = QWidget()
        holder.setLayout(row)
        self.battery_units = spin(1, 50, 1, "", 0, 1)
        self.battery_units.valueChanged.connect(lambda v: self.send("economics", "battery_units", int(v)))
        self.battery_cost = spin(0, 5000, 650, " €/kWh", 0, 10)
        self.battery_cost.valueChanged.connect(lambda v: self.send("economics", "battery_cost_per_kwh", v))
        stf.addRow(self.battery_label)
        stf.addRow(holder)
        stf.addRow(_("How many"), self.battery_units)
        stf.addRow(_("Installed cost per usable kWh"), self.battery_cost)
        f.addWidget(store)
        group(_("Investment and running costs"), (
            ("capex_per_kwp", _("Cost per kWp, turnkey"), 0, 10000, 0, " €/kWp", 50),
            ("capex_total", _("Or the total of the offer"), 0, 1e9, 0, " €", 100),
            ("opex_per_kwp", _("Running costs"), 0, 500, 0, " €/kWp/a", 1),
            ("inverter_year", _("Inverter replaced in year"), 0, 40, 0, "", 1),
            ("inverter_per_kw", _("Its cost"), 0, 2000, 0, " €/kW", 10)))
        group(_("Financial parameters"), (
            ("years", _("Years"), 1, 40, 0, "", 1), ("discount", _("Discount rate"), 0, 20, 1, " %", 0.5),
            ("escalation", _("Energy price growth"), -10, 20, 1, " %/a", 0.5),
            ("opex_escalation", _("Running cost growth"), -10, 20, 1, " %/a", 0.5),
            ("degradation", _("Module degradation (-1: datasheet)"), -1, 5, 2, " %/a", 0.05),
            ("deduction_pct", _("Tax deduction over 10 years"), 0, 110, 0, " %", 1)))
        note = QLabel(_("Prices and costs start from indicative values, marked as such in \"How it is computed\": "
                        "replace them with the bill and the offer."))
        note.setWordWrap(True)
        from .design import Text, set_text
        set_text(note, Text.SECONDARY)
        f.addWidget(note)
        f.addWidget(self.compute_button())
        f.addWidget(self.status)
        f.addStretch(1)

        r = self.results_box
        self.tiles = Tiles([_("Self-consumption"), _("Self-sufficiency"), _("Saving, first year"),
                            _("Sale and incentives, first year"), _("Investment"), _("Net present value"),
                            _("Internal rate of return"), _("Payback"), _("Levelised cost"), _("Bill, first year")], 5)
        self.tiles.helps(("economics.self_consumption", "economics.self_sufficiency", "economics.first_year",
                          "economics.first_year", "economics.return", "economics.npv", "economics.return",
                          "economics.return", "economics.return", "economics.first_year"))
        r.addWidget(self.tiles)
        tabs = QTabWidget()
        bal = QWidget()
        bl = QVBoxLayout(bal)
        self.prod_split = Chart(_("Production: self-consumed and fed in"))
        self.cons_split = Chart(_("Consumption: covered by the system and by the grid"))
        bl.addWidget(self.prod_split)
        bl.addWidget(self.cons_split)
        self.bill = Chart(_("Energy part of the bill, month by month: without the system and with it"))
        self.cash = Chart(_("Cumulative cash flow"))
        self.flows = Chart(_("Cash flow year by year"))
        size = QWidget()
        sl = QVBoxLayout(size)
        self.size_share = Chart(_("Self-consumption and self-sufficiency, by the size of the system"))
        self.size_npv = Chart(_("Net present value, by the size of the system"))
        self.size_note = QLabel("")
        self.size_note.setWordWrap(True)
        sl.addWidget(self.size_share)
        sl.addWidget(self.size_npv)
        sl.addWidget(self.size_note)
        storage = QWidget()
        stl = QVBoxLayout(storage)
        self.store_share = Chart(_("Self-sufficiency, by the capacity of the battery"))
        self.store_npv = Chart(_("Net present value, by the capacity of the battery"))
        self.store_note = QLabel("")
        self.store_note.setWordWrap(True)
        stl.addWidget(self.store_share)
        stl.addWidget(self.store_npv)
        stl.addWidget(self.store_note)
        self.pedigree = PedigreeView()
        # what is used on the spot, hour by hour through the year (R63): when the production meets the load
        self.self_map = Chart(_("Used on the spot, hour by hour: each column a day, each row an hour"))
        tabs.addTab(bal, _("Balance"))
        tabs.addTab(self.self_map, _("Year"))
        tabs.addTab(self.bill, _("Bill"))
        tabs.addTab(self.cash, _("Cash flow"))
        tabs.addTab(self.flows, _("Year by year"))
        tabs.addTab(size, _("Size"))
        tabs.addTab(storage, _("Storage"))
        tabs.addTab(self.pedigree, _("How it is computed"))
        r.addWidget(chart_card(tabs), 1)

    def show_project(self, project) -> None:
        self.loading = True
        try:
            s = Settings.from_dict(project.economics)
            for k, w in self.fields.items():
                w.setValue(float(getattr(s, k)))
            self.community.setChecked(bool(s.community))
            b = s.battery or {}
            self.battery_label.setText(_("{maker} {model}: {kwh} kWh usable").format(
                maker=b.get("manufacturer", ""), model=b.get("model", ""),
                kwh=number(float(b.get("usable_energy_kwh") or b.get("nominal_energy_kwh") or 0), 1)) if b else
                _("No battery."))
            self.battery_units.setValue(int(s.battery_units or 1))
            self.limit.setValue(float(s.export_limit_kw))
            self.battery_cost.setValue(float(s.battery_cost_per_kwh))
            self.zone.setCurrentIndex(max(0, self.zone.findData(s.zone)))
        finally:
            self.loading = False

    def show_sizing(self, sizing, storage, p_stc_kw: float, battery_kwh: float) -> None:
        """The what-if charts: the system larger or smaller, the battery larger or smaller."""
        if sizing is None or storage is None:
            for chart in (self.size_share, self.size_npv, self.store_share, self.store_npv):
                chart.message(_("Compute the production and the consumption first."))
            return
        kwp = [round(float(x), 1) for x in sizing.kwp]
        here = (p_stc_kw, _("as designed"))
        self.size_share.line(kwp, [(_("self-consumption"), [100 * float(v) for v in sizing.self_ratio]),
                                   (_("self-sufficiency"), [100 * float(v) for v in sizing.self_sufficiency])],
                             "%", "kWp", 0, area=False, mark=here, markers=True)
        self.size_npv.line(kwp, [(_("net present value"), [float(v) for v in sizing.npv])], "€", "kWp", 0,
                           mark=here, markers=True)
        best = sizing.loc[sizing.npv.idxmax()]
        self.size_note.setText(_("The production grows with the power, in the same proportions; the investment too. "
                                 "The highest net present value of these sizes is at {kwp} kWp ({eur} €).").format(
            kwp=number(float(best.kwp), 1), eur=number(float(best.npv), 0, grouping=True)))
        frame, generic = storage
        kwh = [round(float(x), 1) for x in frame.kwh]
        mark = (battery_kwh, _("as designed")) if battery_kwh > 0 else None
        self.store_share.line(kwh, [(_("self-sufficiency"), [100 * float(v) for v in frame.self_sufficiency])], "%",
                              "kWh", 0, mark=mark, markers=True)
        self.store_npv.line(kwh, [(_("net present value"), [float(v) for v in frame.npv])], "€", "kWh", 0,
                            mark=mark, markers=True)
        best = frame.loc[frame.npv.idxmax()]
        self.store_note.setText(_("Each capacity is {generic}. The highest net present value is at {kwh} kWh "
                                  "({eur} €).").format(generic=generic, kwh=number(float(best.kwh), 1),
                                                       eur=number(float(best.npv), 0, grouping=True)))

    def show_results(self, econ, error: str = "") -> None:
        if error or econ is None:
            self.status.setText(error)
            self.prod_split.message(error or _("Compute the production and the consumption first."))
            return
        self.status.setText("")
        k = econ.kpi
        t = self.tiles
        t[0].set(f"{number(100 * k['self_ratio'], 0)} %", _("of the production, {kwh} kWh").format(
            kwh=number(k["self"], 0, grouping=True)))
        t[1].set(f"{number(100 * k['self_sufficiency'], 0)} %", _("of the consumption"))
        t[2].set(f"{number(k['saving_1'], 0, grouping=True)} €")
        detail = []
        if k["incentive_1"]:
            detail.append(_("of which incentives {eur} €").format(eur=number(k["incentive_1"], 0, grouping=True)))
        if k.get("curtailed"):
            detail.append(_("{kwh} kWh curtailed by the export limit").format(kwh=number(k["curtailed"], 0, grouping=True)))
        t[3].set(f"{number(k['sale_1'] + k['incentive_1'], 0, grouping=True)} €", "; ".join(detail))
        t[4].set(f"{number(k['capex'], 0, grouping=True)} €")
        t[5].set(f"{number(k['npv'], 0, grouping=True)} €")
        t[6].set(f"{number(100 * k['irr'], 1)} %" if k["irr"] is not None else "–")
        t[7].set(_("{y} years").format(y=number(k["payback"], 1)) if k["payback"] is not None else _("not within the years"),
                 _("discounted {y}").format(y=number(k["payback_discounted"], 1)) if k["payback_discounted"] is not None else "")
        t[8].set(f"{number(k['lcoe'], 3)} €/kWh")
        if getattr(econ, "hourly", None) is not None and "self" in econ.hourly:
            carpet, cols, ticks = year_carpet(econ.hourly["self"], month_names())
            self.self_map.heatmap(carpet, [f"{h}:00" for h in range(24)], cols, "kWh/h", 2, ticks=ticks,
                                  row_ticks=[(h, f"{h}") for h in range(0, 24, 3)])
        t[9].set(f"{number(k['bill_after'], 0, grouping=True)} €", _("energy part, was {eur} €").format(
            eur=number(k["bill_before"], 0, grouping=True)))
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
        self.prod_split.bars(months, prod, "kWh", stacked=True)
        self.cons_split.bars(months, cons_series, "kWh", stacked=True)
        self.bill.bars(months, [(_("without the system"), [float(v) for v in m["bill_before"]]),
                                (_("with the system"), [float(v) for v in m["bill_after"]])], "€")
        years = [0] + list(econ.years.index)
        self.cash.line(years, [(_("Cumulative"), [-k["capex"]] + [float(v) for v in econ.years.cumulative])], "€",
                       _("year"))
        y = econ.years
        self.flows.bars([str(i) for i in y.index], [(_("Net cash flow"), [float(v) for v in y.flow])], "€")
        self.pedigree.show_records([econ.record])
