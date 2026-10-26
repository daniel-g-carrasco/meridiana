"""The Plant phase (task 16d; study 16, D; design document 2.3, C10; R114-R119): the plan in the strings' mode on the
left (the window's own PlanView, lent while the phase is open, the strings always shown, a click on a module chooses
its string), a strip in the phase's bar with what the strings are and their legend; the inverters, their inputs and
the strings are all in the inspector of the right panel (one arrangement: the right panel changes with the phase,
never two columns, and nothing over the plan: R119), the checks of the strings in the Checks panel below. In
Production the group «Inverter» becomes a reference to this phase.

The page never computes: it shows energy/plant.Plant and reports the designer's edits as signals."""

from __future__ import annotations

import html

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPalette, QPen
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QSpinBox, QToolButton, QTreeWidget, QTreeWidgetItem,
                               QTreeWidgetItemIterator, QVBoxLayout, QWidget)

from .. import shortcuts, theme_colors
from ..energy import optimizers
from ..energy import plant as plant_model
from ..energy import system
from ..i18n import _, ngettext, number
from .cards import default_tokens
from .properties import combo, make_form, spin
from . import icons
from .theme import mark, symbol_font
from .design import Icon, Radius, Size, Space, Type, font, strong
from .style import Group

MARKS = {"ok": "✔", "check": "⚠", "fail": "✘"}


def summary(plant) -> str:
    """The strings in a line: how many, on how many inputs, the modules left out."""
    if plant is None:
        return ""
    used = sum(1 for slot in plant.inputs.values() if slot.used) or len({(s.inverter, s.mppt) for s in plant.strings})
    parts = [ngettext("{n} string on {m} inputs", "{n} strings on {m} inputs", len(plant.strings)).format(
        n=len(plant.strings), m=used)]
    if plant.left:
        parts.append(ngettext("{n} module in no string", "{n} modules in no string", len(plant.left)).format(
            n=len(plant.left)))
    return " · ".join(parts)


class DraftCard(QFrame):
    """While a string is drawn, in the corner of the strip where the legend was (R181, Daniel 26/10/2026: «la pillola
    che compare è troppo invasiva, andrebbe portata in un angolo tipo dove c'è la legenda che non serve a nulla e
    riorganizzata per essere consona ed esteticamente gradevole per questa sezione»): the colour the string will have
    as a dot, as the plan's labels have it (R167); the string, its inverter with its make and model and its input on
    the first line; its modules against what the input takes, with the state's symbol, on the second; the keys, muted,
    on the right. Hidden while no string is drawn: nothing over the plan."""

    DOT = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("draft-card")
        self.text = ""                                      # everything it says, for the tests and a reader
        self.symbol_name = ""                               # the state's symbol: check, warning, stop or none
        self.colour = QColor()
        box = QHBoxLayout(self)
        box.setContentsMargins(Space.S + self.DOT + Space.S, Space.XS, Space.S, Space.XS)
        box.setSpacing(Space.L)
        lines = QVBoxLayout()
        lines.setSpacing(0)
        self.title = QLabel()
        self.title.setFont(font(Type.SMALL, Type.SEMIBOLD))
        self.count = QLabel()
        self.count.setFont(font(Type.SMALL))
        self.count.setTextFormat(Qt.TextFormat.RichText)
        for label in (self.title, self.count):
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            lines.addWidget(label)
        box.addLayout(lines, 1)
        self.keys = QLabel()
        self.keys.setFont(font(Type.CAPTION))
        self.keys.setStyleSheet("color: palette(placeholder-text);")
        self.keys.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(self.keys)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(2 * QFontMetrics(self.title.font()).lineSpacing() + 2 * Space.XS)
        self.hide()

    def show_draft(self, title: str = "", count: str = "", state: str = "", colour: str = "", keys: str = "") -> None:
        """The string being drawn (`state`: ok, short, many or "" for no judgement); nothing hides the card."""
        if not title:
            self.text, self.symbol_name = "", ""
            self.hide()
            return
        from . import symbols
        self.symbol_name = {"ok": "check", "short": "warning", "many": "stop"}.get(state, "")
        self.colour = QColor(colour) if colour else QColor()
        self.title.setText(title)
        sign = symbols.html(self.symbol_name) + "&nbsp;" if self.symbol_name else ""
        self.count.setText(sign + html.escape(count))
        self.keys.setText(keys)
        self.text = "\n".join((title, count, keys.replace("\n", " · ")))
        self.setToolTip(self.text)
        self.show()
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.colour.isValid():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(self.palette().color(QPalette.ColorRole.Text), 1))
        p.setBrush(self.colour)
        r = QRectF(Space.S, (self.height() - self.DOT) / 2, self.DOT, self.DOT)
        p.drawEllipse(r)


class ClipScale(QWidget):
    """The DC/AC ratio on its scale (R62): a band from 0 to 6 % of the year's energy cut by the inverter, green under
    1 %, yellow to 3 %, red beyond, a mark where the plant is, the ratio and the share written above it."""

    ZONES = ((1.0, "good"), (3.0, "warning"), (6.0, "critical"))
    END = 6.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ratio, self.loss = 0.0, None
        t = default_tokens()
        self.colours = {"text": t["text"], "muted": t["muted"], "good": "#1baf7a", "warning": "#eda100",
                        "critical": theme_colors.STATUS["critical"]}
        self.setFixedHeight(self.fontMetrics().lineSpacing() + 18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set(self, ratio: float, loss: float | None) -> None:
        self.ratio, self.loss = ratio, loss
        if loss is None:
            self.setToolTip(_("The energy the inverter cuts shows once the production is computed"))
        else:
            self.setToolTip(_("Energy cut beyond the inverter's nominal power: green under 1 %, yellow to 3 %, red "
                              "beyond (the same thresholds as the checks)"))
        self.update()

    def set_colours(self, t: dict, states: dict) -> None:
        self.colours = {"text": t["text"], "muted": t["muted"], "good": states.get("ok", "#1baf7a"),
                        "warning": states.get("check", "#eda100"),
                        "critical": states.get("fail", theme_colors.STATUS["critical"])}
        self.update()

    def paintEvent(self, event) -> None:
        from PySide6.QtCore import QPointF, QRectF
        from PySide6.QtGui import QColor, QPainter, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fm = self.fontMetrics()
        head = (_("DC/AC {r} · energy cut {pct} %").format(r=number(self.ratio, 2), pct=number(self.loss, 1))
                if self.loss is not None else _("DC/AC {r} · energy cut: after the computation").format(
                    r=number(self.ratio, 2)))
        p.setPen(QColor(self.colours["text"]))
        p.drawText(QRectF(0, 0, self.width(), fm.lineSpacing()),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, head)
        y = fm.lineSpacing() + 6
        track_w = self.width() - 2.0
        start = 0.0
        for end, key in self.ZONES:
            c = QColor(self.colours[key])
            c.setAlphaF(0.75 if self.loss is not None else 0.3)
            seg = QRectF(1 + track_w * start / self.END, y, track_w * (end - start) / self.END, 6)
            path = QPainterPath()
            path.addRoundedRect(seg, 3, 3)
            p.fillPath(path, c)
            start = end
        if self.loss is not None:
            x = 1 + track_w * min(self.loss, self.END) / self.END
            mark = QPainterPath(QPointF(x, y - 1))
            mark.lineTo(x - 5, y - 7)
            mark.lineTo(x + 5, y - 7)
            mark.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.colours["text"]))
            p.drawPath(mark)
            p.drawRoundedRect(QRectF(x - 1.5, y - 1, 3, 8), 1, 1)


class PlantPage(QWidget):
    """Phase 2: the strip (the inverters, the strings or the one chosen, the legend) and the place of the plan."""

    def __init__(self, actions: dict, parent=None):
        super().__init__(parent)
        self.actions = actions
        box = QVBoxLayout(self)
        box.setContentsMargins(Space.S, Space.S, Space.S, Space.S)     # the plan off the card's line (R77)
        box.setSpacing(Space.S)
        self.page_box = box
        # the strip of the strings: in the bar of the phase, at the right of its tools (R70), or on top of the page
        # when the bar is on the left side (`place_strip`)
        self.strip = QWidget()
        self.strip.setObjectName("plant-strip")
        strip = QHBoxLayout(self.strip)
        strip.setContentsMargins(0, 0, 0, 0)
        strip.setSpacing(Space.L)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        # one line each, whatever they say: a strip that grows would move the plan under the pointer at each string
        self.inv_label = QLabel("")                         # the inverters in a line (system.describe)
        self.strings_label = QLabel("")                     # the strings in a line (summary)
        for label in (self.inv_label, self.strings_label):
            label.setFont(font(Type.SMALL))                 # as the words of the bar (R70)
        self.strings_label.setStyleSheet("color: palette(placeholder-text);")
        for label in (self.inv_label, self.strings_label):
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            texts.addWidget(label)
        # the words before the legend: a string being drawn says its modules here, never cut to a few letters
        self.texts = QWidget()
        self.texts.setLayout(texts)
        texts.setContentsMargins(0, 0, 0, 0)
        self.texts.setMinimumWidth(44 * self.inv_label.fontMetrics().averageCharWidth())
        strip.addWidget(self.texts, 1)
        # where the legend was (R181: «la legenda che non serve a nulla»): the string being drawn, nothing otherwise
        self.draft_card = DraftCard()
        strip.addWidget(self.draft_card, 1)
        box.addWidget(self.strip)
        self.host = QWidget()                               # where the plan stands while the phase is open
        self.host_box = QVBoxLayout(self.host)
        self.host_box.setContentsMargins(0, 0, 0, 0)
        self.empty = QLabel(_("The plan comes here when the phase is open."))
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.host_box.addWidget(self.empty)
        box.addWidget(self.host, 1)
        self.plan = None

    def lend(self, plan) -> None:
        """The window's plan, shown here while the phase is open: nothing over it (R119)."""
        self.plan = plan
        self.empty.hide()
        self.host_box.addWidget(plan)
        plan.show()

    def returned(self) -> None:
        self.plan = None
        self.empty.show()

    def place_strip(self, holder: QWidget | None) -> None:
        """The strip in `holder` (a place in the bar of the phase), or on top of the page when None."""
        if holder is not None:
            holder.layout().addWidget(self.strip)
        else:
            self.page_box.insertWidget(0, self.strip)
        self.strip.show()

    def show_inverter(self, text: str) -> None:
        self.inverter_text = text
        shown = getattr(self, "draft_text", "") or text
        self.inv_label.setText(shown)
        self.inv_label.setToolTip(shown)

    def show_draft(self, text: str) -> None:
        self.draft_text = text
        shown = text or getattr(self, "inverter_text", "")
        self.inv_label.setText(shown)
        self.inv_label.setToolTip(shown)

    def show_plant(self, plant) -> None:
        self.plant_summary = summary(plant)
        if not getattr(self, "string_text", ""):
            self.strings_label.setText(self.plant_summary)
            self.strings_label.setToolTip(self.plant_summary)

    def show_draft_card(self, *args) -> None:
        """The string being drawn in the card, which takes the strip while it shows (the summary's two lines said
        the same, and the card was squeezed to a few letters); no arguments: the summary back (R181)."""
        self.draft_card.show_draft(*args)
        self.texts.setVisible(not self.draft_card.isVisibleTo(self))

    def show_string(self, text: str) -> None:
        """The string chosen with its voltages in place of the plant's summary; "" brings the summary back (R57)."""
        self.string_text = text
        shown = text or getattr(self, "plant_summary", "")
        self.strings_label.setText(shown)
        self.strings_label.setToolTip(shown)


class PlantInspector(QScrollArea):
    """The right panel in the Plant phase (design C10; R119: the whole management of the inverters is here): the
    inverters with their count and optimizers, added from the catalogue or sized; the strings by inverter and input
    (StringList: chosen, drawn, deleted) with Meridiana's proposal and its completion when asked; the rules of the
    proposal and the conditions of the checks; the string chosen with its checks; the inverter and the input of the
    sub-field selected, for the proposal."""

    countChanged = Signal(int, int)             # entry of energy["inverters"], how many
    removed = Signal(int)                       # entry
    edited = Signal(str, object)                # path in energy, value
    assigned = Signal(str, int, int)            # sub-field, inverter (0: automatic), input (0: automatic)
    stringChosen = Signal(int)                  # index into Plant.strings, -1 none
    optimizerAsked = Signal(int)                # entry: choose its power optimizers in the catalogue (task 22)
    optimizerCleared = Signal(int)              # entry: back to the optimizers Meridiana proposes
    perChosen = Signal(int, int)                # entry, modules on each optimizer (1 or 2)

    def __init__(self, actions: dict, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.loading = False
        self.states = {"ok": theme_colors.STATUS["good"], "check": theme_colors.STATUS["warning"],
                       "fail": theme_colors.STATUS["critical"]}
        self.colours: list = []                     # each string's colour, as on the plan (the window's)
        page = QWidget()
        box = QVBoxLayout(page)
        box.setSpacing(8)
        inv = Group(_("Inverters"))
        inv_box = QVBoxLayout(inv)
        self.describe = QLabel("")
        self.describe.setWordWrap(True)
        inv_box.addWidget(self.describe)
        self.entries_box = QVBoxLayout()
        self.entries_box.setSpacing(4)
        inv_box.addLayout(self.entries_box)
        self.entry_rows: list = []                  # (record, count spin) per entry
        self.entry_keys: list = []                  # what each row was made of (record, optimizer, modules on each)
        self.optimizer_labels: dict = {}            # entry -> the label of its optimizers (task 22)
        for cid in ("inverter_catalog", "inverter_auto"):        # one under the other: the panel may be narrow
            b = QPushButton(shortcuts.plain(actions[cid].text()))
            b.setToolTip(actions[cid].toolTip())
            b.clicked.connect(actions[cid].trigger)
            inv_box.addWidget(b)
        form = make_form()
        self.ratio = spin(0.5, 2.0, 1.1, "", 2, 0.05)
        self.ratio.valueChanged.connect(lambda v: self._send("dc_ac_ratio", v))
        form.addRow(_("DC/AC ratio when sized by itself"), self.ratio)
        self.clip_scale = ClipScale()                       # the ratio on its scale of the energy cut (R62)
        form.addRow(self.clip_scale)
        inv_box.addLayout(form)
        box.addWidget(inv)

        # the strings (R115): the list by inverter and input, and what Meridiana does only when asked
        self.strings_group = Group(_("Strings"))
        sbox = QVBoxLayout(self.strings_group)
        sbox.setSpacing(Space.S)
        self.state = QLabel("")
        self.state.setWordWrap(True)
        sbox.addWidget(self.state)
        self.list = StringList()
        self.list.chosen.connect(lambda i: self.stringChosen.emit(i) if not self.loading else None)
        sbox.addWidget(self.list)
        self.string_buttons = {}
        for cid in ("strings_auto", "strings_complete", "strings_clear"):      # one under the other: a narrow panel
            b = QPushButton(shortcuts.plain(actions[cid].text()))
            b.setToolTip(actions[cid].toolTip())
            if actions[cid].menu() is not None:
                b.setMenu(actions[cid].menu())                  # «Propose»: the strategies, as in the bar
            else:
                b.clicked.connect(actions[cid].trigger)
            sbox.addWidget(b)
            self.string_buttons[cid] = b
        box.addWidget(self.strings_group)

        # the rules of the next proposal and the conditions of the checks
        rules = Group(_("Proposal and checks"))
        sf = make_form(rules)
        self.strategy = combo(plant_model.strategy_names().items(), "serpentine")
        self.strategy.setToolTip(_("How «Propose the strings» runs along the modules: kept for the next proposal, the "
                                   "strings of now do not change"))
        self.strategy.activated.connect(lambda _i: self._send("strings.strategy", self.strategy.currentData()))
        sf.addRow(_("Strategy of the proposal"), self.strategy)
        self.n_series = QSpinBox()
        self.n_series.setRange(0, 80)
        self.n_series.setKeyboardTracking(False)
        self.n_series.setSpecialValueText(_("suggested"))
        self.n_series.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.n_series.setToolTip(_("The modules in series of the next proposal; «suggested»: Meridiana chooses"))
        self.n_series.valueChanged.connect(lambda v: self._send("strings.n_series", int(v) or None))
        sf.addRow(_("Modules in series of the proposal"), self.n_series)
        self.t_min = spin(-40, 20, -10, " °C", 1, 1)
        self.t_min.valueChanged.connect(lambda v: self._send("t_min", v))
        sf.addRow(_("Lowest temperature of the site"), self.t_min)
        self.conditions = QLabel("")
        self.conditions.setWordWrap(True)
        self.conditions.setStyleSheet("color: palette(placeholder-text);")
        sf.addRow(self.conditions)
        box.addWidget(rules)

        # the string chosen: its checks, live (task 16d, step 7), with where the temperatures come from
        self.string_group = Group(_("String chosen"))
        sg = QVBoxLayout(self.string_group)
        self.string_checks = QLabel("")
        self.string_checks.setTextFormat(Qt.TextFormat.RichText)
        self.string_checks.setWordWrap(True)
        sg.addWidget(self.string_checks)
        box.addWidget(self.string_group)
        self.string_group.hide()

        self.subfield_group = Group(_("Sub-field selected"))
        sub = make_form(self.subfield_group)
        self.subfield_name = QLabel("")
        sub.addRow(self.subfield_name)
        self.sub_inverter = QComboBox()
        self.sub_input = QComboBox()
        self.sub_inverter.activated.connect(self._assign)
        self.sub_input.activated.connect(self._assign)
        for w in (self.sub_inverter, self.sub_input):
            w.setToolTip(_("Where «Propose the strings» sends the strings of this sub-field; the strings of now do "
                           "not change"))
        sub.addRow(_("Inverter of the proposal"), self.sub_inverter)
        sub.addRow(_("Input of the proposal"), self.sub_input)
        self.subfield = ""
        box.addWidget(self.subfield_group)
        self.subfield_group.hide()
        box.addStretch(1)
        self.setWidget(page)

    def sizeHint(self) -> QSize:
        """Modest: the right panel is a stack of the phases' inspectors and takes the widest hint of them, so this
        one must not widen it in the other phases (the plan and the 3D view would lose the room)."""
        return QSize(240, 320)

    def minimumSizeHint(self) -> QSize:
        return QSize(180, 120)

    def _send(self, path: str, value) -> None:
        if not self.loading:
            self.edited.emit(path, value)

    def _assign(self, _i=0) -> None:
        if self.loading or not self.subfield:
            return
        inv = int(self.sub_inverter.currentData() or 0)
        mppt = int(self.sub_input.currentData() or 0) if inv else 0
        self.assigned.emit(self.subfield, inv, mppt)

    def show_string(self, plant, index: int) -> None:
        """The checks of string `index` of `plant` (hidden when none is chosen): each with its mark, its clause,
        and the conditions they were made at with their source (the pedigree of the plan)."""
        s = plant.strings[index] if plant is not None and 0 <= index < len(plant.strings) else None
        self.string_group.setVisible(s is not None)
        if s is None:
            return
        import html

        def esc(text: str) -> str:
            return html.escape(text, quote=False)
        names = plant_model.state_names()
        light = f"<span style='color: {self.states.get(s.state, '')};'>{mark(MARKS.get(s.state, ''))}</span>"
        rows = [f"{strong(s.label)} · {len(s.modules)} {_('modules')} · {light} {names.get(s.state, '')}"]
        levels = {"ok": "ok", "info": "ok", "warn": "check", "fail": "fail"}
        for c in (s.plan.checks if s.plan is not None else []):
            k = levels.get(c.level, "check")
            rows.append(f"<span style='color: {self.states.get(k, '')};'>{mark(MARKS[k])}</span> "
                        f"{esc(c.label)}: {esc(c.detail)}")
        if s.plan is None and s.why:
            rows.append(esc(s.why))
        step = s.plan.record.find("vmp") if s.plan is not None and s.plan.record is not None else None
        cell = next((q for q in (step.inputs if step is not None else []) if q.symbol == r"T_{c,max}"), None)
        if cell is not None and cell.source is not None:
            rows.append(f"<span style='color: palette(placeholder-text);'>{esc(cell.source.label)}</span>")
        self.string_checks.setText("<br>".join(rows))

    def show_plant(self, project, plant, selection: tuple = ("", ""), chosen: int = -1) -> None:
        """The inverters of `project`, the strings of `plant` (None while it is computed), the string chosen, the
        sub-field selected."""
        self.show_string(plant, chosen)
        self.loading = True
        try:
            e = project.energy or {}
            self.describe.setText(system.describe(e))
            self._entries(system.inverter_entries(e))
            self._optimizers(plant)
            self.ratio.setValue(float(e.get("dc_ac_ratio") or 1.1))
            if plant is not None:
                self.clip_scale.set(*plant_model.dcac(plant))
            s = e.get("strings") if (e.get("strings") or {}).__class__ is dict else {}
            s = s or {}
            self.strategy.setCurrentIndex(max(0, self.strategy.findData(s.get("strategy") or "serpentine")))
            self.n_series.setValue(int(s.get("n_series") or 0))
            self.t_min.setValue(float(e.get("t_min") if e.get("t_min") is not None else plant_model.DESIGN_COLD))
            self.state.setText(summary(plant) if plant is not None else _("The strings are being laid…"))
            if plant is not None:
                text = (
                    _("Checked at the hottest cell of the typical year, {t} °C, and at {c} °C.").format(
                        t=number(plant.t_cell_max, 0), c=number(plant.t_cell_cold, 0)) if plant.year else
                    _("Checked at PVsyst's design conditions until the production is computed: {hot} and {warm} °C "
                      "of cell, Uoc at {cold} °C.").format(hot=number(plant.t_cell_max, 0),
                                                         warm=number(plant.t_cell_cold, 0),
                                                         cold=number(plant.t_min, 0)))
                if plant.optimized:
                    only = _("The strings checked by SolarEdge's tables, the modules' Voc at {t} °C.").format(
                        t=number(plant.t_min, 0))
                    text = only if all(u.optimized for u in plant.units) else f"{text} {only}"
                self.conditions.setText(text)
            self.list.show_plant(plant, self.colours, self.states, chosen)
            if plant is not None:
                self.string_buttons["strings_complete"].setEnabled(bool(plant.left))
                self.string_buttons["strings_clear"].setEnabled(bool(plant.strings))
            self._subfield(project, plant, selection)
        finally:
            self.loading = False

    def _entries(self, entries: list) -> None:
        """One row per inverter of the list: its name, how many, take it out. Made again only when the list changes
        (a field with the focus keeps it while the strings come back)."""
        keys = [(e["record"], e.get("optimizer"), e.get("per_optimizer")) for e in entries]
        same = len(entries) == len(self.entry_rows) and keys == self.entry_keys
        if same:
            for e, (_rec, count) in zip(entries, self.entry_rows, strict=True):
                if count.value() != e["count"]:
                    count.setValue(e["count"])
            return
        while self.entries_box.count():
            item = self.entries_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.entry_rows = []
        self.entry_keys = keys
        self.optimizer_labels = {}
        for i, e in enumerate(entries):
            row = QFrame()
            row.setObjectName("tile")
            # the draft of the Plant (24/10/2026): the model in bold and what it is under it, how many and out
            # on its right
            outer = QVBoxLayout(row)
            outer.setContentsMargins(12, 8, 8, 8)
            outer.setSpacing(4)
            grid = QHBoxLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(8)
            outer.addLayout(grid)
            column = QVBoxLayout()
            column.setSpacing(1)
            rec = e["record"]
            kw = float(rec.get("ac_power_nominal_w") or 0.0) / 1000.0
            name = e["name"] or f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip()
            label = QLabel(_("{name}, {kw} kW, {n} MPPT").format(name=name, kw=number(kw, 1),
                                                                  n=int(rec.get("mppt_count") or 1)))
            label.setVisible(False)                         # the whole sentence, for a reader of the screen
            title = QLabel(strong(name))
            title.setTextFormat(Qt.TextFormat.RichText)
            title.setWordWrap(True)
            fixed = optimizers.fixed_voltage(rec)
            what = QLabel(_("{kw} kW AC · {n} MPPT").format(kw=number(kw, 1), n=int(rec.get("mppt_count") or 1))
                          if fixed is None else
                          _("{kw} kW AC · strings at {v} V, with power optimizers").format(
                              kw=number(kw, 1), v=number(fixed.v_string, 0)))
            what.setStyleSheet("color: palette(placeholder-text);")
            what.setWordWrap(True)
            column.addWidget(title)
            column.addWidget(what)
            column.addWidget(label)
            if fixed is not None:
                outer.addLayout(self._optimizer_row(i, e))
            grid.addLayout(column, 1)
            line = QHBoxLayout()
            line.setSpacing(2)
            grid.addLayout(line)
            count = QSpinBox()
            count.setRange(1, 500)
            count.setKeyboardTracking(False)
            count.setValue(e["count"])
            count.setPrefix("× ")
            count.setToolTip(_("How many of this model"))
            count.valueChanged.connect(lambda v, k=i: self.countChanged.emit(k, int(v)) if not self.loading else None)
            line.addWidget(count)
            from .style import pad_fields
            pad_fields(count)
            out = QToolButton()
            out.setText("✕")
            out.setFont(symbol_font(out.font()))
            out.setAutoRaise(True)
            out.setToolTip(_("Take this inverter out of the plant"))
            out.clicked.connect(lambda _c=False, k=i: self.removed.emit(k))
            line.addWidget(out)
            self.entries_box.addWidget(row)
            self.entry_rows.append((rec, count))

    def _optimizer_row(self, i: int, e: dict) -> QVBoxLayout:
        """The power optimizers of an inverter at a fixed string voltage (task 22): which, how many modules on each,
        «Optimizers…» to choose them in the catalogue, ✕ to go back to the ones Meridiana proposes."""
        box = QVBoxLayout()
        box.setSpacing(2)
        label = QLabel("")
        label.setWordWrap(True)
        box.addWidget(label)
        self.optimizer_labels[i] = label
        line = QHBoxLayout()
        line.setSpacing(4)
        choose = QPushButton(_("Optimizers…"))
        choose.setToolTip(_("Choose the power optimizers of this inverter in the catalogue"))
        choose.clicked.connect(lambda _c=False, k=i: self.optimizerAsked.emit(k))
        line.addWidget(choose)
        rec = e.get("optimizer")
        if rec:
            per = QComboBox()
            per.addItem(_("one module each"), 1)
            if (rec.get("modules_per_unit") or 1) >= 2:
                per.addItem(_("two modules each"), 2)
            per.setCurrentIndex(max(0, per.findData(e.get("per_optimizer") or 1)))
            per.setToolTip(_("Modules on each optimizer: two in series where the optimizer takes them"))
            per.activated.connect(lambda _x, k=i, w=per: self.perChosen.emit(k, int(w.currentData()))
                                  if not self.loading else None)
            per.setEnabled(per.count() > 1)
            line.addWidget(per)
            back = QToolButton()
            back.setText("✕")
            back.setFont(symbol_font(back.font()))
            back.setAutoRaise(True)
            back.setToolTip(_("Back to the optimizers Meridiana proposes for the module"))
            back.clicked.connect(lambda _c=False, k=i: self.optimizerCleared.emit(k))
            line.addWidget(back)
        line.addStretch(1)
        box.addLayout(line)
        return box

    def _optimizers(self, plant) -> None:
        """The optimizers of each inverter in its row: chosen, proposed by Meridiana, or none that fits."""
        for i, label in self.optimizer_labels.items():
            unit = next((u for u in (plant.units if plant is not None else []) if u.entry == i), None)
            ch = unit.choice if unit is not None else None
            if plant is None:
                text = _("Optimizers: being checked…")
            elif ch is None:
                text = _("Optimizers: none of SolarEdge's in the catalogue takes this module; choose one")
            else:
                text = ngettext("Optimizers: {name}, {n} module each", "Optimizers: {name}, {n} modules each",
                                ch.per).format(name=ch.optimizer.name, n=ch.per)
                if ch.suggested:
                    text += " " + _("(proposed by Meridiana)")
                if ch.rules is None:
                    text += ". " + ch.why
            label.setText(text)
            label.setToolTip(text)

    def _subfield(self, project, plant, selection: tuple) -> None:
        kind, oid = selection
        sf = next((x for x in project.subfields if x.id == oid), None) if kind == "subfield" else None
        self.subfield = sf.id if sf is not None else ""
        self.subfield_group.setVisible(sf is not None)
        if sf is None:
            return
        self.subfield_name.setText(strong(sf.name))
        units = plant.units if plant is not None else []
        inv = sf.params.get("inverter") if sf.params.get("inverter").__class__ is int else 0
        mppt = sf.params.get("mppt") if sf.params.get("mppt").__class__ is int else 0
        self.sub_inverter.clear()
        self.sub_inverter.addItem(_("automatic"), 0)
        for u in units:
            self.sub_inverter.addItem(f"{plant_model.unit_label(u)} · {u.name}", u.number)
        self.sub_inverter.setCurrentIndex(max(0, self.sub_inverter.findData(inv)))
        self.sub_input.clear()
        self.sub_input.addItem(_("automatic"), 0)
        unit = plant.unit(inv) if plant is not None else None
        for k in range(1, (unit.inputs if unit is not None else 0) + 1):
            self.sub_input.addItem(_("Input {k}").format(k=k), k)
        self.sub_input.setCurrentIndex(max(0, self.sub_input.findData(mppt)))
        self.sub_input.setEnabled(unit is not None)


class StringList(QTreeWidget):
    """The strings of the plant in the right panel (R115, Daniel 25/10/2026: «se seleziono una stringa non mi porta alla
    stringa, se premo Canc non me la cancella, il + non fa nulla»): a section for each input of each inverter, its
    name and how many strings it has, «+» at its right to draw a new string on it; under it its strings, each with
    its colour on the plan, its name, its modules and its state as a mark and a word; an input without strings says
    so. A string chosen here is chosen on the plan and brought into view (the window); Del deletes it (the window's
    key), a double click draws it again, the right button opens its menu. As tall as its rows: it scrolls with the
    panel (design system, «Elenco a righe»)."""

    chosen = Signal(int)                        # index into Plant.strings, -1 none
    newString = Signal(int, int)                # unit, input
    redraw = Signal(int)                        # index: drawn again on the plan
    menuAsked = Signal(int, QPoint)             # index, where (global)

    def __init__(self, parent=None):
        super().__init__(parent)
        from .sections import SectionDelegate
        self.setObjectName("strings-list")
        self.setHeaderHidden(True)
        self.setIndentation(0)
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.setExpandsOnDoubleClick(False)
        self.setColumnCount(2)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        head = self.header()
        head.setStretchLastSection(False)
        head.setSectionResizeMode(0, head.ResizeMode.Stretch)
        head.setSectionResizeMode(1, head.ResizeMode.Fixed)
        head.resizeSection(1, Size.CONTROL + Space.M)
        for column in (0, 1):
            self.setItemDelegateForColumn(column, SectionDelegate(self, pills=True))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemSelectionChanged.connect(self._selected)
        self.itemDoubleClicked.connect(self._double)
        self.loading = False
        self.adders: dict = {}                  # (unit, input) -> its «+»
        self.input_heads: dict = {}             # (unit, input) -> its section, highlighted while drawing there
        self.rows: dict = {}                    # index into Plant.strings -> its row
        self.draft_input = (0, 0)

    def sizeHint(self) -> QSize:
        return QSize(200, self.height())

    def show_draft(self, unit: int = 0, mppt: int = 0) -> None:
        """Highlight the input being drawn on, and only until the draft is closed or given up."""
        from .sections import ACTIVE_ROLE
        self.draft_input = (int(unit), int(mppt))
        for key, head in self.input_heads.items():
            active = key == self.draft_input and unit > 0
            for column in range(2):
                head.setData(column, ACTIVE_ROLE, active)
                head.setData(column, Qt.ItemDataRole.BackgroundRole,
                             self.palette().brush(self.palette().ColorRole.Highlight) if active else None)
        self.viewport().update()

    def show_plant(self, plant, colours: list, states: dict, chosen: int = -1) -> None:
        """The inputs and the strings of `plant`, the strings in `colours` (the plan's), the traffic light in
        `states`; the row of string `chosen` selected (without a signal)."""
        from . import marks
        from .sections import TAIL_ROLE, section
        self.loading = True
        try:
            self.clear()
            self.adders, self.input_heads, self.rows = {}, {}, {}
            if plant is None:
                return
            names = plant_model.state_names()
            level = {"ok": "ok", "check": "warn", "fail": "fail"}

            def string_row(parent, i):
                s = plant.strings[i]
                n = len(s.modules)
                tail = "  " + ngettext("{n} module", "{n} modules", n).format(n=n) + " · " + names.get(s.state, "")
                row = QTreeWidgetItem(parent, [s.label + tail, ""])
                row.setData(0, TAIL_ROLE, tail)
                row.setData(0, Qt.ItemDataRole.UserRole, i)
                row.setIcon(0, swatch(colours[i] if i < len(colours) else "#888888"))
                row.setIcon(1, marks.icon(level.get(s.state, "warn")))
                tip = f"{s.label}: {plant_model.voltages(s)}" + (f"\n{s.why}" if s.why else "")
                row.setToolTip(0, tip)
                row.setToolTip(1, names.get(s.state, ""))
                self.rows[i] = row

            for u in plant.units:
                for k in range(1, u.inputs + 1):
                    slot = plant.inputs.get((u.number, k))
                    mine = list(slot.strings) if slot is not None else []
                    # the count with its word: «INGRESSO 2  1» read as an input's number
                    head = section(self, f"{plant_model.unit_label(u)} · {input_name(u, k)}",
                                   ngettext("{n} string", "{n} strings", len(mine)).format(n=len(mine)))
                    takes = (optimized_takes(u, slot) if u.optimized else
                             _("takes {n} strings of {lo} to {hi} modules").format(n=slot.allowed, lo=slot.series[0],
                                                                                  hi=slot.series[1])
                             if slot is not None and slot.series[1] else _("its window is not known"))
                    head.setToolTip(0, f"{u.name}: {takes}")
                    self.input_heads[(u.number, k)] = head
                    self._adder(head, u.number, k, takes)
                    for i in mine:
                        string_row(head, i)
                    if not mine:
                        free = QTreeWidgetItem(head, [_("free: «+» to draw a string on it"), ""])
                        free.setFlags(Qt.ItemFlag.ItemIsEnabled)
                        free.setForeground(0, self.palette().color(QPalette.ColorRole.PlaceholderText))
                        free.setToolTip(0, takes)
            lost = [i for i, s in enumerate(plant.strings) if not plant.inputs.get((s.inverter, s.mppt))]
            if lost:
                head = section(self, _("Without an input"), ngettext("{n} string", "{n} strings",
                                                                      len(lost)).format(n=len(lost)))
                for i in lost:
                    string_row(head, i)
            self.expandAll()
            self.show_draft(*self.draft_input)
            if chosen in self.rows:
                self.setCurrentItem(self.rows[chosen])
            self._fit()
        finally:
            self.loading = False

    def _adder(self, head, unit: int, k: int, takes: str) -> None:
        """«+» on the row of an input: a tool button of the design system with Lucide's «plus»."""
        from .sections import AIR
        holder = QWidget()
        box = QHBoxLayout(holder)
        box.setContentsMargins(0, AIR, 0, 0)
        box.setSpacing(0)
        add = QToolButton()
        add.setObjectName("add-string")
        add.setIcon(icons.icon("plus"))
        add.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        add.setAutoRaise(True)
        add.setToolTip(_("A new string on input {k} of inverter {n}: then click its modules on the plan in order "
                         "({takes})").format(k=k, n=unit, takes=takes))
        add.clicked.connect(lambda _c=False, n=unit, m=k: self.newString.emit(n, m))
        box.addWidget(add, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setItemWidget(head, 1, holder)
        self.adders[(unit, k)] = add

    def _fit(self) -> None:
        """As tall as its rows."""
        self.doItemsLayout()
        height = 0
        it = QTreeWidgetItemIterator(self)
        while it.value() is not None:
            height += self.visualItemRect(it.value()).height() or self.sizeHintForRow(0)
            it += 1
        self.setFixedHeight(max(Size.CONTROL, height + 2 * self.frameWidth() + Space.XS))

    def index_of(self, item) -> int:
        value = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        return value if value.__class__ is int else -1

    def current(self) -> int:
        """The string of the row selected, -1 none."""
        items = self.selectedItems()
        return self.index_of(items[0]) if items else -1

    def choose(self, index: int) -> None:
        """String `index` selected (-1: none), without a signal: the plan chose it."""
        self.loading = True
        try:
            if index in self.rows:
                self.setCurrentItem(self.rows[index])
                self.scrollToItem(self.rows[index])
            else:
                self.clearSelection()
        finally:
            self.loading = False

    def _selected(self) -> None:
        if not self.loading:
            self.chosen.emit(self.current())

    def _double(self, item, _column) -> None:
        i = self.index_of(item)
        if i >= 0:
            self.redraw.emit(i)

    def _menu(self, pos) -> None:
        item = self.itemAt(pos)
        i = self.index_of(item)
        if i >= 0:
            if self.current() != i:
                self.setCurrentItem(item)
            self.menuAsked.emit(i, self.viewport().mapToGlobal(pos))


def swatch(colour: str) -> QIcon:
    """A square of a string's colour with rounded corners (the radius of the marks), as the list shows it beside the
    string's name: the colour itself on the light panel would not read as text (pink, yellow)."""
    from PySide6.QtGui import QPainter, QPixmap
    size = Icon.CONTROL
    ratio = 2.0
    pix = QPixmap(int(size * ratio), int(size * ratio))
    pix.setDevicePixelRatio(ratio)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor(0, 0, 0, 60))
    p.setBrush(QColor(colour))
    p.drawRoundedRect(QRectF(2.5, 2.5, size - 5, size - 5), Radius.MARK, Radius.MARK)
    p.end()
    return QIcon(pix)


class InverterReference(QGroupBox):
    """In Production, where the group «Inverter» was (design 2.4): the inverters in a line and the way to the Plant
    phase, where they are chosen («Impianto: 2 x SUN2000-10KTL, cambia…»)."""

    def __init__(self, go, parent=None):
        super().__init__(_("Inverter"), parent)
        box = QVBoxLayout(self)
        self.label = QLabel("")
        self.label.setWordWrap(True)
        box.addWidget(self.label)
        self.button = QPushButton(_("Go to the Plant"))
        self.button.setToolTip(_("The inverters, their inputs and the strings are chosen in the Plant phase"))
        self.button.clicked.connect(go)
        box.addWidget(self.button, 0, Qt.AlignmentFlag.AlignLeft)

    def show_energy(self, energy: dict | None) -> None:
        self.label.setText(_("Plant: {what}").format(what=system.describe(energy)))


def install_reference(page, go) -> InverterReference:
    """The Production page with the reference in place of its groups «Inverter» and «Strings» (they are the Plant's
    now): the page's own widgets are hidden, not taken away, so that the page goes on as it was written."""
    old = page.inv_label.parentWidget()
    strings = page.t_min.parentWidget()
    box = page.form_box
    at = box.indexOf(old)
    ref = InverterReference(go)
    box.insertWidget(at if at >= 0 else 2, ref)
    for w in (old, strings):
        w.hide()
    return ref


def input_name(unit, k: int) -> str:
    """An input as the Plant names it: «Input 2» of an inverter with MPPT, «Synergy unit 2» of a SolarEdge inverter
    with Synergy units, «Strings» of a SolarEdge inverter with one DC bus (task 22)."""
    if not unit.optimized:
        return _("Input {k}").format(k=k)
    return _("Synergy unit {k}").format(k=k) if unit.inputs > 1 else _("Strings")


def optimized_takes(unit, slot) -> str:
    """What an input of an inverter with optimizers takes: the strings' optimizers and power by SolarEdge's table."""
    ch = unit.choice
    if ch is None or ch.rules is None:
        return _("its optimizers are not known")
    r = ch.rules
    on_it = max(1, len(slot.strings)) if slot is not None else 1
    cap = optimizers.connected_limit(r, on_it, 0.0)[0]
    text = _("strings of {lo} to {hi} optimizers").format(lo=r.opt_min, hi=r.opt_max)
    if cap != float("inf"):
        text += ", " + _("up to {p} kW each, {c} kW carried").format(p=number(cap / 1000.0, 2),
                                                                    c=number(r.p_cont / 1000.0, 2))
    if slot is not None and slot.allowed:
        text += ", " + ngettext("{n} input pair", "{n} input pairs", slot.allowed).format(n=slot.allowed)
    return text

