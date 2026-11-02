"""The Plant phase (task 16d; study 16, D; design document 2.3, C10; R114-R119): the plan in the strings' mode on the
left (the window's own PlanView, lent while the phase is open, the strings always shown, a click on a module chooses
its string), a strip in the phase's bar with what the strings are and their legend; the inverters, their inputs and
the strings are all in the inspector of the right panel (one arrangement: the right panel changes with the phase,
never two columns, and nothing over the plan: R119), the checks of the strings in the Checks panel below. In
Production the group «Inverter» becomes a reference to this phase.

The page never computes: it shows energy/plant.Plant and reports the designer's edits as signals."""

from __future__ import annotations

import html

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPalette, QPen
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QVBoxLayout,
                               QWidget)
from PySide6.QtWidgets import QStyle, QStyleOptionViewItem

from .. import shortcuts, theme_colors
from ..energy import optimizers
from ..energy import plant as plant_model
from ..energy.plant import input_name  # noqa: F401  (the window imports it from here)
from ..energy import system
from ..i18n import _, ngettext, number
from .cards import default_tokens
from .properties import combo, make_form, spin
from . import icons, marks
from .help_box import help_button
from .theme import mark, symbol_font
from .design import Button, Icon, Line, Radius, Size, Space, Text, Type, font, free_text, set_text, strong
from .style import Group
from .sections import SectionDelegate

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


def active_overview(plant, limit: int = 6) -> str:
    """The inverters at work over those chosen (R245), with the rule of the year (energy/pipeline.py): an installed
    inverter (not one sized by itself) with a string of modules on one of its inputs; then a line for each unit, the
    first `limit` of them. «Active» is what the production counts: an inverter chosen without strings is idle."""
    units = [u for u in plant.units if u.entry >= 0 and u.spec.pac > 0]
    if not units:
        return _("No inverter selected.")
    lines, active, power = [], 0, 0.0
    for u in units:
        runs = [s for s in plant.strings if s.inverter == u.number and s.modules and 1 <= s.mppt <= u.inputs]
        if runs:
            active += 1
            power += u.spec.pac
            inputs = len({s.mppt for s in runs})
            what = (ngettext("{n} string", "{n} strings", len(runs)).format(n=len(runs)) + " " +
                    ngettext("on {n} input", "on {n} inputs", inputs).format(n=inputs))
        else:
            what = _("no strings")
        lines.append(f"{plant_model.unit_label(u)} · {u.name}: {what}")
    head = ngettext("{active} of {total} inverter with strings", "{active} of {total} inverters with strings",
                    len(units)).format(active=active, total=len(units))
    head += f" · {number(power / 1000.0, 1)} kW AC"
    more = len(lines) - limit
    shown = lines[:limit] + ([_("and {n} more").format(n=more)] if more > 0 else [])
    return "\n".join([head, *shown])


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
        # R277: no wider than 50 characters: the Plant's bar has the Panels' tools too, and the strip asking for
        # its long words whole (533 px with a string being drawn) went into the bar's overflow menu at 1400 px
        self.strip.setMaximumWidth(50 * self.inv_label.fontMetrics().averageCharWidth())
        strip.addWidget(self.texts, 1)
        # R298 (study 23, C3): the string chosen, compressed, in place of the summary while one is chosen
        self.chosen_strip = ChosenStrip()
        self.chosen_strip.hide()
        strip.addWidget(self.chosen_strip, 1)
        # where the legend was (R181: «la legenda che non serve a nulla»): the string being drawn, nothing otherwise
        self.draft_card = DraftCard()
        strip.addWidget(self.draft_card, 1)
        box.addWidget(self.strip)
        self.chosen_index = -1
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
        self._arrange()

    def show_chosen(self, plant, index: int, states: dict | None = None) -> None:
        """The string chosen, compressed, in the strip (R298, study 23, C3) while one is chosen; -1 brings the
        summary back. Three states of the strip, one at a time: the summary, the string chosen, the string drawn."""
        states = states or {"ok": theme_colors.STATUS["good"], "check": theme_colors.STATUS["warning"],
                            "fail": theme_colors.STATUS["critical"]}
        self.chosen_index = index if self.chosen_strip.show_string(plant, index, states) else -1
        self._arrange()

    def state(self) -> str:
        """Which of the three the strip shows: "draft", "chosen" or "summary"."""
        if self.draft_card.isVisibleTo(self):
            return "draft"
        return "chosen" if self.chosen_index >= 0 else "summary"

    def _arrange(self) -> None:
        state = self.state()
        self.chosen_strip.setVisible(state == "chosen")
        self.texts.setVisible(state == "summary")

    def show_string(self, text: str) -> None:
        """The string chosen with its voltages in place of the plant's summary (R57; since R298 the compressed card,
        `show_chosen`, takes its place: kept for the words of the line); "" brings the summary back."""
        self.string_text = text
        shown = text or getattr(self, "plant_summary", "")
        self.strings_label.setText(shown)
        self.strings_label.setToolTip(shown)


def plant_totals(plant) -> str:
    """The inverters of the plant in a line, at the head of the Inverter group (study 23, I-A): how many, their AC
    power, the modules' power, the DC/AC ratio. No judgement on the ratio before the year is computed (R308)."""
    if plant is None:
        return _("The inverters are being checked…")
    units = [u for u in plant.units if u.entry >= 0 and u.spec.pac > 0]
    if not units:
        return _("No inverter chosen: Meridiana sizes one by itself for the checks.")
    ac = sum(u.spec.pac for u in units)
    parts = [ngettext("{n} inverter", "{n} inverters", len(units)).format(n=len(units)),
             _("{kw} kW AC").format(kw=number(ac / 1000.0, 1)),
             _("{kwp} kWp").format(kwp=number(plant.p_stc_w / 1000.0, 1))]
    if ac > 0 and plant.p_stc_w > 0:
        parts.append(_("DC/AC {r}").format(r=number(plant.p_stc_w / ac, 2)))
    return " · ".join(parts)


def unit_lines(plant, unit) -> tuple[str, str, str]:
    """What the card of an inverter says under its name (study 23, A2): the model with its power and inputs; its
    strings, inputs, modules, power and DC/AC; the first reason of its inputs to look at ("" when none)."""
    spec = unit.spec
    model = f"{spec.manufacturer} {spec.model}".strip()
    fixed = unit.fixed
    if fixed is not None:
        what = _("{model} · {kw} kW · strings at {v} V, with power optimizers").format(
            model=model, kw=number(spec.pac / 1000.0, 1), v=number(fixed.v_string, 0))
    else:
        what = _("{model} · {kw} kW · {n} MPPT").format(model=model, kw=number(spec.pac / 1000.0, 1),
                                                        n=int(spec.mppt_count or 1))
    runs = [s for s in plant.strings if s.inverter == unit.number and s.modules]
    if not runs:
        return what, _("no strings"), ""
    inputs = len({s.mppt for s in runs})
    modules = sum(len(s.modules) for s in runs)
    power = sum(slot.power_w for (n, _k), slot in plant.inputs.items() if n == unit.number)
    line = (ngettext("{n} string", "{n} strings", len(runs)).format(n=len(runs)) + " " +
            ngettext("on {n} input", "on {n} inputs", inputs).format(n=inputs) + " · " +
            ngettext("{n} module", "{n} modules", modules).format(n=modules) + " · " +
            _("{kwp} kWp").format(kwp=number(power / 1000.0, 1)))
    if spec.pac > 0 and power > 0:
        line += " · " + _("DC/AC {r}").format(r=number(power / spec.pac, 2))
    reasons = []
    for (n, k), slot in sorted(plant.inputs.items()):
        if n == unit.number and slot.strings and slot.level != "ok" and slot.why:
            reasons.append(f"{input_name(unit, k)}: {slot.why}")
    return what, line, reasons[0] if reasons else ""


def string_figures(s) -> tuple[list, list]:
    """The string chosen as bars and rows (study 23, F and C2): the bars (key, label, text, low, high, state) with
    the fractions of the limit they fill, the rows of the checks (state, text) with their clause. Nothing computed:
    everything from the plan of the string's input."""
    p = s.plan
    bars, rows = [], []
    levels = {"ok": "ok", "info": "ok", "warn": "check", "fail": "fail"}
    if p is not None and not isinstance(p, optimizers.OptimizedPlan):
        if p.uoc_max and p.v_limit:
            frac = p.uoc_max / p.v_limit
            bars.append(("uoc", "Uoc", _("{u} / {lim} V").format(u=number(p.uoc_max, 0), lim=number(p.v_limit, 0)),
                         0.0, min(frac, 1.0), "ok" if frac <= 1.0 else "fail"))
        lo_v, hi_v = p.window
        if p.vmp_hot and hi_v:
            inside = (not lo_v or p.vmp_hot >= lo_v) and p.vmp_cold <= hi_v
            bars.append(("umpp", "Umpp", _("{hot}-{cold} V").format(hot=number(p.vmp_hot, 0),
                                                                    cold=number(p.vmp_cold, 0)),
                         min(p.vmp_hot / hi_v, 1.0), min(p.vmp_cold / hi_v, 1.0), "ok" if inside else "fail"))
        current = next((c for c in p.checks if c.key.startswith("isc") and c.detail and not c.key.startswith("isc_")),
                       None)
        if current is not None:
            import re
            figures = [float(f.replace(",", ".")) for f in re.findall(r"\d+(?:[.,]\d+)?", current.detail)][:2]
            if len(figures) == 2 and figures[1] > 0:
                bars.append(("isc", "I", _("{a} / {b} A").format(a=number(figures[0], 1), b=number(figures[1], 1)),
                             0.0, min(figures[0] / figures[1], 1.0), levels.get(current.level, "check")))
    for c in (p.checks if p is not None else []):
        rows.append((levels.get(c.level, "check"), f"{c.label}: {c.detail}" if c.detail else c.label))
    if not rows and s.why:
        rows.append(("check", s.why))
    return bars, rows


def worst_row(rows: list) -> tuple:
    """The row that matters most: the first failure, else the first to check, else the first."""
    for wanted in ("fail", "check"):
        for row in rows:
            if row[0] == wanted:
                return row
    return rows[0] if rows else ("", "")


class MarginBar(QWidget):
    """A figure against its limit as a bar (study 23, E and F): the label at the left, a track as long as the
    limit, the span filled in the state's colour, the figures at the right. Nothing is invented: the colours are
    the states' (the theme's), the track the field's."""

    LABEL = 40
    TEXT = 92

    def __init__(self, label: str, parent=None, compact: bool = False):
        super().__init__(parent)
        self.label, self.text, self.low, self.high, self.state = label, "", 0.0, 0.0, ""
        self.colours: dict = {}
        self.compact = compact
        self.setFont(font(Type.CAPTION if compact else Type.SMALL))
        self.setFixedHeight(self.fontMetrics().lineSpacing() + (2 if compact else Space.XS))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set(self, text: str, low: float, high: float, state: str, colours: dict) -> None:
        self.text, self.low, self.high, self.state, self.colours = text, low, high, state, colours
        self.setToolTip(f"{self.label} {text}")
        self.update()

    def paintEvent(self, event) -> None:
        from PySide6.QtGui import QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fm = self.fontMetrics()
        h = self.height()
        text_w = fm.horizontalAdvance(self.text) + Space.S
        muted = self.palette().color(QPalette.ColorRole.PlaceholderText)
        p.setPen(muted)
        p.drawText(QRectF(0, 0, self.LABEL, h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.label)
        p.setPen(self.palette().color(QPalette.ColorRole.Text))
        p.drawText(QRectF(self.width() - text_w, 0, text_w, h),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.text)
        track = QRectF(self.LABEL, (h - 6) / 2, max(0.0, self.width() - self.LABEL - text_w - Space.S), 6)
        if track.width() <= 0:
            return
        ground = QPainterPath()
        ground.addRoundedRect(track, 3, 3)
        line = self.palette().color(QPalette.ColorRole.Mid)
        line.setAlphaF(0.35)
        p.fillPath(ground, line)
        colour = QColor(self.colours.get(self.state, "")) if self.colours.get(self.state) else \
            self.palette().color(QPalette.ColorRole.Highlight)
        span = QRectF(track.left() + track.width() * self.low, track.top(),
                      max(3.0, track.width() * (self.high - self.low)), track.height())
        fill = QPainterPath()
        fill.addRoundedRect(span, 3, 3)
        p.fillPath(fill, colour)


class Disc(QWidget):
    """The number of an inverter in a round disc (R297, A2 with the disc of before): the handle of its card. It is
    dragged to change the order (Alt+Up and Alt+Down do the same from the keyboard); under the pointer the number
    gives way to the dots of a grip. Two figures fit: the font is the caption's."""

    SIZE = Size.CONTROL
    MIME = "application/x-meridiana-inverter"

    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.number = number
        self.current = False
        self.hot = False
        self.press = None
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setFont(font(Type.CAPTION, Type.SEMIBOLD))
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(_("Drag to change the order of the inverters (Alt+Up and Alt+Down too). The number is the "
                          "inverter's place: the strings are named after it."))

    def set_current(self, on: bool) -> None:
        if on != self.current:
            self.current = on
            self.update()

    def enterEvent(self, event) -> None:
        self.hot = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hot = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.press = event.position().toPoint()
        event.ignore()                                  # the card chooses its inverter

    def mouseMoveEvent(self, event) -> None:
        from PySide6.QtCore import QMimeData
        from PySide6.QtGui import QDrag
        from PySide6.QtWidgets import QApplication
        if self.press is None or (event.position().toPoint() - self.press).manhattanLength() < \
                QApplication.startDragDistance():
            return
        self.press = None
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self.MIME, str(self.number).encode())
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(QPoint(self.SIZE // 2, self.SIZE // 2))
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event) -> None:
        self.press = None
        event.ignore()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        fill = pal.color(QPalette.ColorRole.Highlight if self.current else QPalette.ColorRole.Mid)
        if not self.current:
            fill.setAlphaF(0.45)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        r = QRectF(1, 1, self.SIZE - 2, self.SIZE - 2)
        p.drawEllipse(r)
        ink = pal.color(QPalette.ColorRole.HighlightedText if self.current else QPalette.ColorRole.Text)
        if self.hot:                                    # the grip: two columns of three dots
            p.setBrush(ink)
            cx, cy = self.SIZE / 2, self.SIZE / 2
            for dx in (-3, 3):
                for dy in (-5, 0, 5):
                    p.drawEllipse(QRectF(cx + dx - 1.2, cy + dy - 1.2, 2.4, 2.4))
            return
        p.setPen(ink)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, str(self.number))


class InverterCard(QFrame):
    """One inverter of the plant (R297, study 23, A2): its disc with the number as the handle, its name (F2 or a
    double click to rename, the menu too), the model with its power and inputs, its strings with their modules and
    power, the first reason of its inputs to look at; the menu «⋯» at the right. The card of the inverter the
    Strings show is outlined. The optimizers of a SolarEdge inverter on their row (task 22)."""

    activated = Signal(int)                     # its number: the Strings show it
    renamed = Signal(int, str)
    moved = Signal(int, int)                    # number, by how many places (-1 up, +1 down)
    menuAsked = Signal(int, QPoint)             # number, where (global)

    def __init__(self, unit, parent=None):
        super().__init__(parent)
        self.setObjectName("tile")
        self.number = unit.number
        self.entry = unit.entry
        self.unit_name = unit.name
        self.current = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        box = QHBoxLayout(self)
        box.setContentsMargins(Space.M, Space.M, Space.S, Space.M)
        box.setSpacing(Space.M)
        self.disc = Disc(unit.number)
        box.addWidget(self.disc, 0, Qt.AlignmentFlag.AlignTop)
        column = QVBoxLayout()
        column.setSpacing(Space.XXS)
        self.name = QLabel(strong(html.escape(unit.name, quote=False)))
        self.name.setTextFormat(Qt.TextFormat.RichText)
        self.name.setWordWrap(True)
        self.name.setToolTip(_("The inverter's name: F2 or a double click to change it"))
        self.editor = QLineEdit()
        self.editor.setPlaceholderText(_("Name of the inverter"))
        self.editor.editingFinished.connect(self._done)
        self.editor.installEventFilter(self)
        self.editor.hide()
        column.addWidget(self.name)
        column.addWidget(self.editor)
        self.what = QLabel("")
        self.strings = QLabel("")
        self.note = QLabel("")
        for label in (self.what, self.strings, self.note):
            label.setWordWrap(True)
            set_text(label, Text.SECONDARY)
            column.addWidget(label)
        self.note.hide()
        box.addLayout(column, 1)
        self.more = QToolButton()
        self.more.setText("⋯")
        self.more.setFont(symbol_font(self.more.font()))
        self.more.setAutoRaise(True)
        self.more.setToolTip(_("Rename, move, datasheet, string, empty, take out"))
        self.more.clicked.connect(lambda: self.menuAsked.emit(
            self.number, self.more.mapToGlobal(QPoint(0, self.more.height()))))
        box.addWidget(self.more, 0, Qt.AlignmentFlag.AlignTop)
        self.column = column

    def set_current(self, on: bool) -> None:
        self.current = on
        self.disc.set_current(on)
        self.update()

    def set_lines(self, what: str, strings: str, note: str) -> None:
        self.what.setText(what)
        self.strings.setText(strings)
        self.note.setText(note)
        self.note.setVisible(bool(note))
        self.setToolTip("\n".join(x for x in (self.unit_name, what, strings, note) if x))
        self.setAccessibleName(_("Inverter {n}, {name}: {what}; {strings}").format(
            n=self.number, name=self.unit_name, what=what, strings=strings))

    def rename(self) -> None:
        """The name as a field in its place (F2, a double click, the menu)."""
        self.editor.setText(self.unit_name)
        self.name.hide()
        self.editor.show()
        self.editor.setFocus()
        self.editor.selectAll()

    def _done(self) -> None:
        if self.editor.isHidden():
            return
        text = self.editor.text().strip()
        self.editor.hide()
        self.name.show()
        self.setFocus()
        if text and text != self.unit_name:
            self.renamed.emit(self.number, text)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.editor and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.editor.setText(self.unit_name)         # given up: nothing changes
            self._done()
            return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self.activated.emit(self.number)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.rename()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.menuAsked.emit(self.number, event.globalPos())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F2:
            self.rename()
        elif event.key() == Qt.Key.Key_Up and event.modifiers() & Qt.KeyboardModifier.AltModifier:
            self.moved.emit(self.number, -1)
        elif event.key() == Qt.Key.Key_Down and event.modifiers() & Qt.KeyboardModifier.AltModifier:
            self.moved.emit(self.number, 1)
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.current:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(self.palette().color(QPalette.ColorRole.Highlight), Line.HAIR))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), Radius.CARD, Radius.CARD)


class InverterList(QWidget):
    """The inverters of the plant one by one (R297, study 23, I-A): a card for each, in the order of their numbers,
    the one the Strings show outlined. The cards are dragged by their disc to change the order, which renumbers
    the strings (the window says so in the status bar); the menu «⋯» of each: Rename, Move up, Move down, Datasheet,
    String this inverter, Empty its strings, Take out of the plant. Made again only when the inverters change (a
    name being typed keeps its field while the strings come back)."""

    activated = Signal(int)
    renamed = Signal(int, str)
    moved = Signal(int, int)                    # number, its new place (from 0)
    datasheetAsked = Signal(int)
    stringAsked = Signal(int)
    emptied = Signal(int)
    removed = Signal(int)                       # number: taken out of the plant, its strings on no inverter
    optimizerAsked = Signal(int)                # entry (task 22)
    optimizerCleared = Signal(int)
    perChosen = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(Space.S)
        self.cards: dict = {}                   # number -> its card
        self.keys: list = []
        self.working = 0
        self.optimizer_labels: dict = {}        # entry -> the label of its optimizers (task 22)
        self.optimizer_entries: list = []       # the entries as the window gives them, for the optimizers' rows

    def show_units(self, plant, entries: list, working: int) -> None:
        """The cards of `plant`'s inverters (none while the plant is computed: the cards of before stay), the one
        `working` outlined."""
        self.working = working
        if plant is None:
            return
        units = [u for u in plant.units if u.entry >= 0 and u.spec.pac > 0]
        keys = [(u.number, u.entry, u.name, u.optimized) for u in units]
        if keys != self.keys:
            while self.box.count():
                item = self.box.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()
            self.cards, self.optimizer_labels = {}, {}
            self.keys = keys
            for u in units:
                card = InverterCard(u)
                card.activated.connect(self.activated)
                card.renamed.connect(self.renamed)
                card.moved.connect(self._nudge)
                card.menuAsked.connect(self._menu)
                if u.optimized and 0 <= u.entry < len(entries):
                    card.column.addLayout(self._optimizer_row(u.entry, entries[u.entry]))
                self.box.addWidget(card)
                self.cards[u.number] = card
        for u in units:
            card = self.cards[u.number]
            card.set_current(u.number == working)
            card.set_lines(*unit_lines(plant, u))
        self._optimizers(plant)

    def set_current(self, working: int) -> None:
        self.working = working
        for n, card in self.cards.items():
            card.set_current(n == working)

    def order(self) -> list[int]:
        return sorted(self.cards)

    def _nudge(self, number: int, delta: int) -> None:
        order = self.order()
        if number not in order:
            return
        at = order.index(number) + delta
        if 0 <= at < len(order):
            self.moved.emit(number, at)

    def position_at(self, y: int) -> int:
        """The place (from 0) a card dropped at `y` takes: before the first card whose middle is under `y`."""
        for at, n in enumerate(self.order()):
            card = self.cards[n]
            if y < card.geometry().center().y():
                return at
        return len(self.cards)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(Disc.MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(Disc.MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(Disc.MIME):
            return
        number = int(bytes(event.mimeData().data(Disc.MIME)).decode() or 0)
        order = self.order()
        if number not in order:
            return
        at = self.position_at(int(event.position().y()))
        if at > order.index(number):
            at -= 1                                 # taken out before it is put back
        event.acceptProposedAction()
        if at != order.index(number):
            self.moved.emit(number, at)

    def _menu(self, number: int, where: QPoint) -> None:
        from PySide6.QtWidgets import QMenu
        card = self.cards.get(number)
        if card is None:
            return
        order = self.order()
        at = order.index(number)
        menu = QMenu(self)
        a = menu.addAction(_("Rename"), card.rename)
        a.setShortcut("F2")
        up = menu.addAction(_("Move up"), lambda: self._nudge(number, -1))
        up.setShortcut("Alt+Up")
        up.setEnabled(at > 0)
        down = menu.addAction(_("Move down"), lambda: self._nudge(number, 1))
        down.setShortcut("Alt+Down")
        down.setEnabled(at < len(order) - 1)
        menu.addSeparator()
        menu.addAction(_("Datasheet…"), lambda: self.datasheetAsked.emit(number))
        menu.addAction(_("String this inverter…"), lambda: self.stringAsked.emit(number))
        menu.addAction(_("Empty its strings"), lambda: self.emptied.emit(number))
        menu.addSeparator()
        menu.addAction(_("Take out of the plant"), lambda: self.removed.emit(number))
        self.menu = menu                            # kept, for the tests
        menu.popup(where)

    def _optimizer_row(self, i: int, e: dict) -> QVBoxLayout:
        """The power optimizers of an inverter at a fixed string voltage (task 22): which, how many modules on each,
        «Optimizers…» to choose them in the catalogue, ✕ to go back to the ones Meridiana proposes."""
        box = QVBoxLayout()
        box.setSpacing(Space.XXS)
        label = QLabel("")
        label.setWordWrap(True)
        set_text(label, Text.SECONDARY)
        box.addWidget(label)
        self.optimizer_labels[i] = label
        line = QHBoxLayout()
        line.setSpacing(Space.XS)
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
            per.setToolTip(_("Maximum modules on each optimizer. Its model determines series or parallel wiring; "
                              "edit individual groups from the string menu."))
            per.activated.connect(lambda _x, k=i, w=per: self.perChosen.emit(k, int(w.currentData())))
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


class StringRow(QWidget):
    """One string in the card of its input (view B): its colour as on the plan, its name, its modules; chosen with a
    click (as on the plan), drawn again with a double click, its menu with the right button."""

    clicked = Signal(int)
    doubleClicked = Signal(int)
    menuAsked = Signal(int, QPoint)

    def __init__(self, index: int, label: str, modules: int, colour: str, tip: str, parent=None):
        super().__init__(parent)
        self.index = index
        self.selected = False
        self.hot = False
        self.setFixedHeight(Size.CHIP)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tip)
        box = QHBoxLayout(self)
        box.setContentsMargins(Space.S, 0, Space.S, 0)
        box.setSpacing(Space.S)
        dot = QLabel()
        dot.setPixmap(swatch(colour).pixmap(Icon.CONTROL, Icon.CONTROL))
        dot.setFixedSize(Icon.CONTROL, Icon.CONTROL)
        box.addWidget(dot)
        self.name = QLabel(label)
        set_text(self.name, Text.BODY)
        self.name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        box.addWidget(self.name, 1)
        self.count = QLabel(str(modules))
        set_text(self.count, Text.SECONDARY)
        self.count.setToolTip(ngettext("{n} module", "{n} modules", modules).format(n=modules))
        box.addWidget(self.count)

    def set_selected(self, on: bool) -> None:
        if on != self.selected:
            self.selected = on
            self.update()

    def enterEvent(self, event) -> None:
        self.hot = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hot = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        elif event.button() == Qt.MouseButton.RightButton:
            self.menuAsked.emit(self.index, event.globalPosition().toPoint())
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(self.index)
        event.accept()

    def paintEvent(self, event) -> None:
        if not (self.selected or self.hot):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        colour = self.palette().color(QPalette.ColorRole.Highlight)
        colour.setAlphaF(0.28 if self.selected else 0.12)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(colour)
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), Radius.INNER, Radius.INNER)


class InputCard(QFrame):
    """One input (MPPT) of the inverter shown, as a card in the grid (R298, study 23, B): its name and the mark of
    the worst of its states on the first row, its strings under it, «+» to draw a string on it when it takes more.
    Outlined while a string is drawn on it."""

    def __init__(self, unit, k: int, parent=None):
        super().__init__(parent)
        self.setObjectName("tile")
        self.key = (unit.number, k)
        self.active = False
        box = QVBoxLayout(self)
        box.setContentsMargins(Space.S, Space.S, Space.S, Space.S)
        box.setSpacing(Space.XXS)
        head = QHBoxLayout()
        head.setContentsMargins(Space.S, 0, 0, 0)
        head.setSpacing(Space.XS)
        self.title = QLabel(strong(html.escape(input_name(unit, k), quote=False)))
        self.title.setTextFormat(Qt.TextFormat.RichText)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # two cards in 220 px
        head.addWidget(self.title, 1)
        self.mark = QLabel()
        self.mark.setFixedSize(Icon.CONTROL, Icon.CONTROL)
        head.addWidget(self.mark)
        self.add = QToolButton()
        self.add.setObjectName("add-string")
        self.add.setIcon(icons.icon("plus"))
        self.add.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        self.add.setAutoRaise(True)
        head.addWidget(self.add)
        box.addLayout(head)
        self.rows_box = QVBoxLayout()
        self.rows_box.setSpacing(0)
        box.addLayout(self.rows_box)
        self.free = QLabel(_("free"))
        set_text(self.free, Text.SECONDARY)
        self.free.setContentsMargins(Space.S, 0, 0, 0)
        box.addWidget(self.free)
        box.addStretch(1)

    def set_state(self, level: str, tip: str, free: bool, room: bool) -> None:
        self.mark.setPixmap(marks.icon(level).pixmap(Icon.CONTROL, Icon.CONTROL))
        self.mark.setToolTip(tip)
        self.setToolTip(tip)
        self.free.setVisible(free)
        self.add.setVisible(room)

    def set_active(self, on: bool) -> None:
        if on != self.active:
            self.active = on
            self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(self.palette().color(QPalette.ColorRole.Highlight), Line.HAIR))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), Radius.CARD, Radius.CARD)


class InputsGrid(QWidget):
    """The inputs of the inverter shown as cards in two columns (R298, Daniel's choice of 02/11/2026: study 23, B):
    the ten MPPT of a large inverter are seen whole, as the terminals on the inverter; where it is free is seen at
    once; the string chosen is found. The figures are in the string chosen (ChosenString) and in the tooltips.
    The same signals and ways as the list of before (StringList), so that the window goes on as it was: `chosen`,
    `newString`, `redraw`, `menuAsked`, `unitChanged`; `show_plant`, `choose`, `show_draft`, `set_unit`."""

    chosen = Signal(int)                        # index into Plant.strings, -1 none
    newString = Signal(int, int)                # unit, input
    redraw = Signal(int)
    menuAsked = Signal(int, QPoint)
    unitChanged = Signal(int)

    COLUMNS = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inputs-grid")
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(Space.S)
        self.plant = None
        self.colours: list = []
        self.states: dict = {}
        self.working_unit = 0
        self.draft_input = (0, 0)
        self.loading = False
        self.selected = -1
        self.input_heads: dict = {}             # (unit, input) -> its card
        self.adders: dict = {}                  # (unit, input) -> its «+»
        self.rows: dict = {}                    # index into Plant.strings -> its row

    def set_unit(self, unit: int) -> None:
        if unit != self.working_unit:
            self.show_plant(self.plant, self.colours, self.states, unit=unit)

    def show_plant(self, plant, colours: list, states: dict, chosen: int = -1, *, unit: int | None = None) -> None:
        previous = self.working_unit
        self.plant, self.colours, self.states = plant, colours, states
        if plant is not None:
            wanted = unit if unit is not None else self.working_unit
            if 0 <= chosen < len(plant.strings):
                wanted = plant.strings[chosen].inverter
            units = {u.number for u in plant.units}
            self.working_unit = wanted if wanted in units else plant.units[0].number if plant.units else 0
        self.loading = True
        try:
            while self.grid.count():
                item = self.grid.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()
            self.input_heads, self.adders, self.rows = {}, {}, {}
            self.selected = -1
            if plant is None:
                return
            names = plant_model.state_names()
            words = {"ok": _("correct"), "warn": _("to be checked"), "fail": _("out of limit")}
            u = plant.unit(self.working_unit)
            cards = []
            if u is not None:
                for k in range(1, u.inputs + 1):
                    slot = plant.inputs.get((u.number, k))
                    mine = list(slot.strings) if slot is not None else []
                    card = InputCard(u, k)
                    takes = (optimized_takes(u, slot) if u.optimized else
                             _("takes {n} strings of {lo} to {hi} modules").format(n=slot.allowed, lo=slot.series[0],
                                                                                  hi=slot.series[1])
                             if slot is not None and slot.series[1] else _("its window is not known"))
                    level = slot.level if slot is not None and mine else "info"
                    reasons = [words.get(level, "") if mine else _("empty"), takes]
                    reasons += ([slot.why] if slot is not None and slot.why else [])
                    reasons += [plant.strings[i].why for i in mine if plant.strings[i].why]
                    room = slot is None or not slot.allowed or len(mine) < slot.allowed
                    card.set_state(level, "\n".join(dict.fromkeys(r for r in reasons if r)), not mine, room)
                    card.add.setToolTip(_("Activate input {k} of inverter {n}: draw a string, or another equal string "
                                          "in parallel, by clicking its modules on the plan in order ({takes})").format(
                        k=k, n=u.number, takes=takes))
                    card.add.clicked.connect(lambda _c=False, n=u.number, m=k: self.newString.emit(n, m))
                    for i in mine:
                        self._row(card, plant.strings[i], i, names)
                    self.input_heads[(u.number, k)] = card
                    self.adders[(u.number, k)] = card.add
                    cards.append(card)
            lost = [i for i, s in enumerate(plant.strings)
                    if (s.inverter == self.working_unit or s.inverter not in {x.number for x in plant.units})
                    and not plant.inputs.get((s.inverter, s.mppt))]
            if lost:
                card = InputCard(u if u is not None else plant.units[0], 0) if plant.units else None
                if card is not None:
                    card.title.setText(strong(html.escape(_("Without an input"), quote=False)))
                    card.set_state("fail", _("Strings whose inverter is gone: give them another from their menu, "
                                             "or Undo"), False, False)
                    for i in lost:
                        self._row(card, plant.strings[i], i, names)
                    cards.append(card)
            for at, card in enumerate(cards):
                self.grid.addWidget(card, at // self.COLUMNS, at % self.COLUMNS)
            for column in range(self.COLUMNS):
                self.grid.setColumnStretch(column, 1)
            self.show_draft(*self.draft_input)
            if chosen in self.rows:
                self._select(chosen)
        finally:
            self.loading = False
            if previous != self.working_unit:
                self.unitChanged.emit(self.working_unit)

    def _row(self, card: InputCard, s, i: int, names: dict) -> None:
        tip = f"{s.label}: {plant_model.voltages(s)}" + (f"\n{s.why}" if s.why else "")
        tip += "\n" + names.get(s.state, "")
        row = StringRow(i, s.label, len(s.modules), self.colours[i] if i < len(self.colours) else "#888888", tip)
        row.clicked.connect(self._clicked)
        row.doubleClicked.connect(self.redraw)
        row.menuAsked.connect(self._menu)
        card.rows_box.addWidget(row)
        self.rows[i] = row

    def _select(self, index: int) -> None:
        self.selected = index
        for i, row in self.rows.items():
            row.set_selected(i == index)

    def _clicked(self, index: int) -> None:
        self._select(index)
        if not self.loading:
            self.chosen.emit(index)

    def _menu(self, index: int, where: QPoint) -> None:
        self._select(index)
        self.menuAsked.emit(index, where)

    def current(self) -> int:
        return self.selected

    def choose(self, index: int) -> None:
        """String `index` selected (-1: none), without a signal: the plan chose it."""
        if self.plant is not None and 0 <= index < len(self.plant.strings):
            unit = self.plant.strings[index].inverter
            if unit != self.working_unit:
                self.show_plant(self.plant, self.colours, self.states, chosen=index, unit=unit)
        self._select(index if index in self.rows else -1)

    def show_draft(self, unit: int = 0, mppt: int = 0) -> None:
        """The input being drawn on outlined, until the draft is closed or given up."""
        if unit and not self.loading and unit != self.working_unit:
            self.set_unit(unit)
        self.draft_input = (int(unit), int(mppt))
        for key, card in self.input_heads.items():
            card.set_active(key == self.draft_input and unit > 0)


class MiniDiagram(QWidget):
    """The inverter shown as a single-line diagram in miniature (R298, study 23, C, the other view of the menu):
    one row per input, each string a bar as long as its modules, in its colour on the plan, its name on it; the
    mark of the input's worst state at the row's end. A click on a bar chooses the string, a double click draws it
    again, the right button opens its menu; a click on a free input's dotted box draws a string on it. The same
    ways as the grid, so that the two views are swapped under the same inspector."""

    chosen = Signal(int)
    newString = Signal(int, int)
    redraw = Signal(int)
    menuAsked = Signal(int, QPoint)
    unitChanged = Signal(int)

    LABEL = 56
    ROW = Size.CHIP + Space.XS
    BAR = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mini-diagram")
        self.setMouseTracking(True)
        self.setFont(font(Type.CAPTION))
        self.plant = None
        self.colours: list = []
        self.states: dict = {}
        self.working_unit = 0
        self.draft_input = (0, 0)
        self.loading = False
        self.selected = -1
        self.rows: dict = {}                    # index -> its bar's rect (QRectF)
        self.input_heads: dict = {}             # (unit, k) -> the row's rect
        self.adders: dict = {}                  # (unit, k) -> the free box's rect
        self.levels: dict = {}                  # (unit, k) -> the worst state
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_unit(self, unit: int) -> None:
        if unit != self.working_unit:
            self.show_plant(self.plant, self.colours, self.states, unit=unit)

    def show_plant(self, plant, colours: list, states: dict, chosen: int = -1, *, unit: int | None = None) -> None:
        previous = self.working_unit
        self.plant, self.colours, self.states = plant, colours, states
        if plant is not None:
            wanted = unit if unit is not None else self.working_unit
            if 0 <= chosen < len(plant.strings):
                wanted = plant.strings[chosen].inverter
            units = {u.number for u in plant.units}
            self.working_unit = wanted if wanted in units else plant.units[0].number if plant.units else 0
        self.selected = chosen if plant is not None and 0 <= chosen < len(plant.strings) else -1
        u = plant.unit(self.working_unit) if plant is not None else None
        self.setFixedHeight(max(Size.CONTROL, (u.inputs if u is not None else 0) * self.ROW))
        self._layout()
        if previous != self.working_unit:
            self.unitChanged.emit(self.working_unit)

    def _layout(self) -> None:
        """Where each bar and box is, for the drawing and the clicks."""
        self.rows, self.input_heads, self.adders, self.levels = {}, {}, {}, {}
        plant = self.plant
        u = plant.unit(self.working_unit) if plant is not None else None
        if u is None:
            self.update()
            return
        longest = max((len(s.modules) for s in plant.strings), default=1) or 1
        room = max(40.0, self.width() - self.LABEL - Icon.CONTROL - 2 * Space.S)
        for k in range(1, u.inputs + 1):
            y = (k - 1) * self.ROW
            slot = plant.inputs.get((u.number, k))
            mine = list(slot.strings) if slot is not None else []
            self.input_heads[(u.number, k)] = QRectF(0, y, self.width(), self.ROW)
            self.levels[(u.number, k)] = slot.level if slot is not None and mine else "info"
            x = float(self.LABEL)
            for i in mine:
                w = max(24.0, room * len(plant.strings[i].modules) / longest * 0.5)
                self.rows[i] = QRectF(x, y + (self.ROW - self.BAR) / 2, w, self.BAR)
                x += w + Space.XS
            if slot is None or not slot.allowed or len(mine) < slot.allowed:
                self.adders[(u.number, k)] = QRectF(x, y + (self.ROW - self.BAR) / 2, 24, self.BAR)
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        plant = self.plant
        u = plant.unit(self.working_unit) if plant is not None else None
        if u is None:
            return
        pal = self.palette()
        muted = pal.color(QPalette.ColorRole.PlaceholderText)
        for (n, k), rect in self.input_heads.items():
            p.setPen(muted)
            p.drawText(QRectF(Space.XS, rect.top(), self.LABEL - Space.XS, rect.height()),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, input_name(u, k))
            # the bus of the input: a line under the bars, the diagram's wire
            p.setPen(QPen(muted, Line.HAIR))
            p.drawLine(QPointF(self.LABEL, rect.bottom() - 2), QPointF(self.width() - Icon.CONTROL - Space.S,
                                                                        rect.bottom() - 2))
            level = self.levels.get((n, k), "info")
            marks.icon(level).paint(p, QRectF(self.width() - Icon.CONTROL - Space.XS, rect.top() + (rect.height() -
                                                                                                Icon.CONTROL) / 2,
                                              Icon.CONTROL, Icon.CONTROL).toRect())
            if (n, k) == self.draft_input:
                p.setPen(QPen(pal.color(QPalette.ColorRole.Highlight), Line.HAIR))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), Radius.INNER, Radius.INNER)
        for i, rect in self.rows.items():
            colour = QColor(self.colours[i] if i < len(self.colours) else "#888888")
            p.setPen(QPen(pal.color(QPalette.ColorRole.Text), 1.5) if i == self.selected else Qt.PenStyle.NoPen)
            p.setBrush(colour)
            p.drawRoundedRect(rect, Radius.MARK, Radius.MARK)
            ink = QColor("#000000") if colour.lightnessF() > 0.6 else QColor("#ffffff")
            p.setPen(ink)
            label = plant.strings[i].label
            if p.fontMetrics().horizontalAdvance(label) + 4 <= rect.width():
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        for rect in self.adders.values():
            p.setPen(QPen(muted, Line.HAIR, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, Radius.MARK, Radius.MARK)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "+")

    def _hit(self, pos) -> tuple[str, object]:
        for i, rect in self.rows.items():
            if rect.contains(pos):
                return "string", i
        for key, rect in self.adders.items():
            if rect.contains(pos):
                return "free", key
        return "", None

    def mousePressEvent(self, event) -> None:
        what, which = self._hit(event.position())
        if what == "string":
            self.selected = which
            self.update()
            if event.button() == Qt.MouseButton.RightButton:
                self.menuAsked.emit(which, event.globalPosition().toPoint())
            elif not self.loading:
                self.chosen.emit(which)
        elif what == "free" and event.button() == Qt.MouseButton.LeftButton:
            self.newString.emit(*which)
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        what, which = self._hit(event.position())
        if what == "string":
            self.redraw.emit(which)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        what, which = self._hit(event.position())
        if what == "string" and self.plant is not None:
            s = self.plant.strings[which]
            self.setToolTip(f"{s.label}: {plant_model.voltages(s)}" + (f"\n{s.why}" if s.why else ""))
        elif what == "free":
            self.setToolTip(_("Draw a string on this input"))
        else:
            self.setToolTip("")
        self.setCursor(Qt.CursorShape.PointingHandCursor if what else Qt.CursorShape.ArrowCursor)

    def current(self) -> int:
        return self.selected

    def choose(self, index: int) -> None:
        if self.plant is not None and 0 <= index < len(self.plant.strings):
            unit = self.plant.strings[index].inverter
            if unit != self.working_unit:
                self.show_plant(self.plant, self.colours, self.states, chosen=index, unit=unit)
        self.selected = index if index in self.rows else -1
        self.update()

    def show_draft(self, unit: int = 0, mppt: int = 0) -> None:
        if unit and not self.loading and unit != self.working_unit:
            self.set_unit(unit)
        self.draft_input = (int(unit), int(mppt))
        self.update()


class StringsView(QStackedWidget):
    """The Strings of the inverter shown, in the view chosen from the menu beside the «?» (R298): the inputs as
    cards (B) or the single-line diagram in miniature (C). One face to the window: the signals and ways of the
    view in front, the other view brought up to date when it comes in front."""

    VIEWS = ("cards", "diagram")
    chosen = Signal(int)
    newString = Signal(int, int)
    redraw = Signal(int)
    menuAsked = Signal(int, QPoint)
    unitChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.views = {"cards": InputsGrid(), "diagram": MiniDiagram()}
        for view in self.views.values():
            self.addWidget(view)
            view.chosen.connect(self.chosen)
            view.newString.connect(self.newString)
            view.redraw.connect(self.redraw)
            view.menuAsked.connect(self.menuAsked)
            view.unitChanged.connect(self.unitChanged)
        self.view = "cards"
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def front(self):
        return self.views[self.view]

    def set_view(self, view: str) -> None:
        if view not in self.views or view == self.view:
            return
        back = self.front()
        self.view = view
        self.setCurrentWidget(self.front())
        self.front().show_plant(back.plant, back.colours, back.states, back.current(), unit=back.working_unit)
        self.front().show_draft(*back.draft_input)

    def __getattr__(self, name: str):
        # the view in front answers for the stack: plant, colours, states, working_unit, rows, input_heads,
        # adders, draft_input, loading, show_plant, set_unit, choose, current, show_draft
        if name in ("views", "view"):
            raise AttributeError(name)
        return getattr(self.front(), name)

    def sizeHint(self) -> QSize:
        return self.front().sizeHint()


def view_names() -> dict:
    return {"cards": _("Inputs as cards"), "diagram": _("Single-line diagram in miniature")}


class _Beside(QObject):
    """Keeps a button on the title's row of a group, at the left of its «?»."""

    def __init__(self, host: QWidget, button: QWidget):
        super().__init__(host)
        self.host, self.button = host, button
        host.installEventFilter(self)
        self.place()

    def place(self) -> None:
        from .help_box import BUTTON
        head = self.host.fontMetrics().height() + 8
        self.button.move(self.host.width() - BUTTON - 6 - Space.XS - self.button.width(),
                         max(0, (head - self.button.height()) // 2))
        self.button.raise_()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.host and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.place()
        return False


class ChosenString(Group):
    """The string chosen, as a group at the top of the column (R298, study 23, C4; Daniel's choice of 02/11/2026):
    its name, inverter and input on the first line, its modules and power on the second; the three figures as bars
    against their limits (Uoc, Umpp, the input's current); the checks as rows with their mark and clause, parted by
    thin lines; the string's commands, Redraw, Move to…, Delete. Shown only while a string is chosen."""

    redrawAsked = Signal(int)
    moveAsked = Signal(int, QPoint)             # the string's menu, with where it can go
    deleteAsked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(_("String chosen"), parent)
        help_button(self, "plant.string")
        self.index = -1
        box = QVBoxLayout(self)
        box.setSpacing(Space.S)
        self.identity = QLabel("")
        self.identity.setTextFormat(Qt.TextFormat.RichText)
        self.identity.setWordWrap(True)
        box.addWidget(self.identity)
        self.detail = QLabel("")
        self.detail.setWordWrap(True)
        set_text(self.detail, Text.SECONDARY)
        box.addWidget(self.detail)
        self.bars = {key: MarginBar(label) for key, label in (("uoc", "Uoc"), ("umpp", "Umpp"), ("isc", "I"))}
        for bar in self.bars.values():
            box.addWidget(bar)
        self.rows_box = QVBoxLayout()
        self.rows_box.setSpacing(Space.XS)
        box.addLayout(self.rows_box)
        self.row_widgets: list = []
        self.source = QLabel("")
        self.source.setWordWrap(True)
        set_text(self.source, Text.CAPTION)
        box.addWidget(self.source)
        buttons = QHBoxLayout()
        buttons.setSpacing(Space.S)
        self.redraw = QPushButton(_("Redraw"))
        self.redraw.setToolTip(_("Draw this string again on the plan, from its modules"))
        self.redraw.clicked.connect(lambda: self.redrawAsked.emit(self.index))
        self.move = QPushButton(_("Move to…"))
        self.move.setToolTip(_("The string's menu: the inputs it can go to, and the rest"))
        self.move.clicked.connect(lambda: self.moveAsked.emit(
            self.index, self.move.mapToGlobal(QPoint(0, self.move.height()))))
        self.delete = QPushButton(_("Delete"))
        self.delete.setToolTip(_("This string deleted: its modules stay laid, in no string (Ctrl+Z brings it back)"))
        self.delete.clicked.connect(lambda: self.deleteAsked.emit(self.index))
        for b in (self.redraw, self.move, self.delete):
            # three on a row: they share the width and never widen the panel (the words are in the tooltips too)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            buttons.addWidget(b, 1)
        box.addLayout(buttons)
        self.states: dict = {}

    def show(self, plant, index: int, states: dict) -> None:       # noqa: A003  the group's own way of showing
        s = plant.strings[index] if plant is not None and 0 <= index < len(plant.strings) else None
        self.index = index if s is not None else -1
        self.states = states
        self.setVisible(s is not None)
        if s is None:
            return

        def esc(text: str) -> str:
            return html.escape(text, quote=False)
        unit = plant.unit(s.inverter)
        where = (f"{plant_model.unit_label(unit)} {unit.name} · {input_name(unit, s.mppt)}" if unit is not None
                 else _("Without an input"))
        light = f"<span style='color: {states.get(s.state, '')};'>{mark(MARKS.get(s.state, ''))}</span>"
        self.identity.setText(f"{strong(esc(s.label))} · {esc(where)} {light}")
        power = sum(m[2] for m in s.modules if len(m) > 2 and isinstance(m[2], (int, float))) if s.modules else 0.0
        detail = ngettext("{n} module in series", "{n} modules in series", len(s.modules)).format(n=len(s.modules))
        if power:
            detail += " · " + _("{kwp} kWp").format(kwp=number(power / 1000.0, 1))
        detail += " · " + plant_model.state_names().get(s.state, "")
        self.detail.setText(detail)
        bars, rows = string_figures(s)
        found = {key: (text, low, high, state) for key, _label, text, low, high, state in bars}
        for key, bar in self.bars.items():
            bar.setVisible(key in found)
            if key in found:
                bar.set(*found[key], states)
        while self.row_widgets:
            self.row_widgets.pop().deleteLater()
        levels = {"ok": "ok", "check": "check", "fail": "fail"}
        if not rows:
            rows = [("", _("No check yet: the strings are being laid."))]
        for at, (level, text) in enumerate(rows):
            if at:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setObjectName("bar-line")
                line.setFixedHeight(Line.HAIR)
                self.rows_box.addWidget(line)
                self.row_widgets.append(line)
            row = QLabel()
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setWordWrap(True)
            set_text(row, Text.SECONDARY)
            sign = (f"<span style='color: {states.get(levels[level], '')};'>{mark(MARKS[levels[level]])}</span> "
                    if level in levels else "")
            row.setText(sign + esc(text))
            self.rows_box.addWidget(row)
            self.row_widgets.append(row)
        step = s.plan.record.find("vmp") if s.plan is not None and s.plan.record is not None else None
        cell = next((q for q in (step.inputs if step is not None else []) if q.symbol == r"T_{c,max}"), None)
        source = cell.source.label if cell is not None and cell.source is not None else ""
        self.source.setText(source)
        self.source.setVisible(bool(source))


class ChosenStrip(QWidget):
    """The string chosen, compressed in the right zone of the Plant's bar (R298, study 23, C3): 60 px, its name and
    path on the first line, its modules and the worst of its remarks on the second, the three bars with their
    figures at the right; in the low bar (icons alone) one line with the figures and no bars. Shown only while a
    string is chosen; the plant's summary otherwise, the string being drawn meanwhile (PlantPage)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chosen-strip")
        self.text = ""
        box = QHBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(Space.L)
        lines = QVBoxLayout()
        lines.setSpacing(0)
        self.title = QLabel()
        self.title.setFont(font(Type.SMALL, Type.SEMIBOLD))
        self.remark = QLabel()
        self.remark.setFont(font(Type.SMALL))
        self.remark.setTextFormat(Qt.TextFormat.RichText)
        for label in (self.title, self.remark):
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            lines.addWidget(label)
        box.addLayout(lines, 1)
        bars = QVBoxLayout()
        bars.setSpacing(0)
        self.bars = {key: MarginBar(label, compact=True) for key, label in (("uoc", "Uoc"), ("umpp", "Umpp"),
                                                                            ("isc", "I"))}
        for bar in self.bars.values():
            bar.setMinimumWidth(150)
            bars.addWidget(bar)
        self.bars_box = QWidget()
        self.bars_box.setLayout(bars)
        bars.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self.bars_box)
        self.figures = ""
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def show_string(self, plant, index: int, states: dict) -> bool:
        """The string `index` of `plant`; whether there is one to show."""
        s = plant.strings[index] if plant is not None and 0 <= index < len(plant.strings) else None
        if s is None:
            self.text = ""
            return False
        unit = plant.unit(s.inverter)
        where = (f"{s.label} · {plant_model.unit_label(unit)} {unit.name} · {input_name(unit, s.mppt)}"
                 if unit is not None else f"{s.label} · {_('Without an input')}")
        self.title.setText(where)
        bars, rows = string_figures(s)
        found = {key: (text, low, high, state) for key, _label, text, low, high, state in bars}
        for key, bar in self.bars.items():
            bar.setVisible(key in found)
            if key in found:
                bar.set(*found[key], states)
        level, remark = worst_row(rows)
        modules = ngettext("{n} module", "{n} modules", len(s.modules)).format(n=len(s.modules))
        sign = (f"<span style='color: {states.get(level, '')};'>{mark(MARKS[level])}</span> "
                if level in MARKS else "")
        self.remark.setText(f"{html.escape(modules, quote=False)} · {sign}{html.escape(remark, quote=False)}"
                            if remark else html.escape(modules, quote=False))
        self.figures = " · ".join(f"{label} {text}" for _key, label, text, _lo, _hi, _st in bars)
        self.text = "\n".join((where, f"{modules} · {remark}" if remark else modules, self.figures))
        self.setToolTip(self.text)
        self._fit()
        return True

    def _fit(self) -> None:
        """Two lines with the bars in the tall bar; one line with the figures in the low one."""
        low = self.height() and self.height() < 3 * self.bars["uoc"].height() + Space.XS
        self.bars_box.setVisible(not low and bool(self.figures))
        if low and self.figures:
            self.remark.setText(html.escape(self.figures, quote=False))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()


class DatasheetSheet(QDialog):
    """The datasheet of an inverter from the catalogue (R297, study 23): a little window that stays open while the
    work goes on, with the record's fields the checks use, in the catalogue's words, and the address of the
    maker's datasheet when the record has it."""

    def __init__(self, unit, record: dict, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QDialogButtonBox, QTextBrowser
        from .catalog_dialog import field_names, origin_names
        self.setWindowTitle(_("Datasheet of inverter {n}").format(n=unit.number))
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setModal(False)
        self.resize(420, 480)
        box = QVBoxLayout(self)
        head = QLabel(strong(html.escape(f"{record.get('manufacturer', '')} {record.get('model', '')}".strip(),
                                         quote=False)))
        head.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(head)
        sub = QLabel(_("{label} · {name} · from the catalogue").format(label=plant_model.unit_label(unit),
                                                                       name=unit.name))
        set_text(sub, Text.SECONDARY)
        box.addWidget(sub)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        lines = []
        for key, label in field_names().items():
            v = record.get(key)
            if v in (None, "", []):
                continue
            if key == "datasheet_url":
                lines.append(f"<tr><td>{html.escape(label)}</td><td><a href='{html.escape(str(v))}'>"
                             f"{html.escape(str(v))}</a></td></tr>")
                continue
            if key == "source":
                v = origin_names().get(v, v)
            if isinstance(v, bool):
                v = _("yes") if v else _("no")
            elif isinstance(v, float):
                v = number(v, 3 if abs(v) < 10 else 1)
            lines.append(f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(v))}</td></tr>")
        self.view.setHtml(f"<table cellspacing='0' cellpadding='3'>{''.join(lines)}</table>")
        box.addWidget(self.view, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        box.addWidget(buttons)


class StringingPopup(QDialog):
    """«String automatically…» (R308, study 23, M3; Daniel's choice of 02/11/2026): a little window hung at the
    edge of the right panel, not modal (the plan can still be clicked to change the modules), with the options
    inside: on what (the whole plant, the modules selected on the plan, one inverter), replace the strings there
    are or add for the modules in no string only, the path of the strings, the modules in series, the DC/AC ratio
    wanted as a free field with the sentence that says what it does. No judgement on the ratio: the energy cut is
    checked once the year is computed, as today."""

    asked = Signal(dict)                        # scope, unit, replace, strategy, n_series, dc_ac

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QDialogButtonBox
        self.setWindowTitle(_("String automatically"))
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setModal(False)
        box = QVBoxLayout(self)
        box.setSpacing(Space.M)
        self.lead = QLabel(_("Meridiana lays strings on the inputs of the inverters, valid for their voltage window "
                             "and their currents. The modules can also be chosen on the plan while this window is "
                             "open."))
        self.lead.setWordWrap(True)
        set_text(self.lead, Text.DESCRIPTION)
        box.addWidget(self.lead)
        form = make_form()
        self.scope = QComboBox()
        self.scope.setToolTip(_("The modules Meridiana works on"))
        form.addRow(_("On what"), self.scope)
        self.existing = QComboBox()
        self.existing.addItem(_("replace the strings there are"), True)
        self.existing.addItem(_("add strings for the modules in no string only"), False)
        self.existing.setToolTip(_("Replace: the strings on those modules go, after a question. Add: yours stay as "
                                   "they are"))
        form.addRow(_("Strings there are"), self.existing)
        self.strategy = combo(plant_model.strategy_names().items(), "serpentine")
        self.strategy.setToolTip(_("How the strings run along the modules"))
        form.addRow(_("Path of the strings"), self.strategy)
        self.n_series = QSpinBox()
        self.n_series.setRange(0, 80)
        self.n_series.setKeyboardTracking(False)
        self.n_series.setSpecialValueText(_("suggested"))
        self.n_series.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.n_series.setToolTip(_("The modules in series of each string; «suggested»: Meridiana chooses from the "
                                   "voltage window"))
        form.addRow(_("Modules in series"), self.n_series)
        self.ratio = spin(0.5, 2.0, 1.1, "", 2, 0.05)
        self.ratio.setToolTip(_("The modules' power over the inverter's AC power"))
        form.addRow(_("DC/AC ratio wanted"), self.ratio)
        self.ratio_note = QLabel(_("The modules' power (kWp) over the inverters' AC power. «Choose automatically» "
                                   "picks the size closest to it; the energy the inverters cut shows once the "
                                   "production is computed. Your choice: no judgement here."))
        self.ratio_note.setWordWrap(True)
        set_text(self.ratio_note, Text.SECONDARY)
        form.addRow(self.ratio_note)
        box.addLayout(form)
        buttons = QDialogButtonBox()
        self.go = buttons.addButton(_("String"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.go.setDefault(True)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._go)
        buttons.rejected.connect(self.close)
        box.addWidget(buttons)
        from .style import pad_fields
        pad_fields(self)
        self.setMinimumWidth(360)

    def prepare(self, plant, swept: int, unit: int, strings: dict, ratio: float) -> None:
        """The choices of now: the units of `plant`, `swept` modules selected on the plan, `unit` the one asked
        for (0: the whole plant), `strings` energy["strings"] for the path and the series, `ratio` the DC/AC."""
        self.scope.clear()
        self.scope.addItem(_("the whole plant"), ("all", 0))
        self.scope.addItem(ngettext("{n} module selected on the plan", "{n} modules selected on the plan",
                                    swept).format(n=swept), ("swept", 0))
        self.scope.model().item(1).setEnabled(swept > 0)
        for u in (plant.units if plant is not None else []):
            if u.entry >= 0:
                self.scope.addItem(_("{label} · {name}").format(label=plant_model.unit_label(u), name=u.name),
                                   ("unit", u.number))
        wanted = ("unit", unit) if unit else ("swept", 0) if swept else ("all", 0)
        at = next((i for i in range(self.scope.count()) if tuple(self.scope.itemData(i)) == wanted), 0)
        self.scope.setCurrentIndex(at)
        self.strategy.setCurrentIndex(max(0, self.strategy.findData(strings.get("strategy") or "serpentine")))
        self.n_series.setValue(int(strings.get("n_series") or 0))
        self.ratio.setValue(float(ratio or 1.1))

    def options(self) -> dict:
        scope, unit = tuple(self.scope.currentData() or ("all", 0))
        return {"scope": scope, "unit": int(unit), "replace": bool(self.existing.currentData()),
                "strategy": self.strategy.currentData(), "n_series": int(self.n_series.value()) or None,
                "dc_ac": float(self.ratio.value())}

    def _go(self) -> None:
        self.asked.emit(self.options())
        self.close()

    def hang_at(self, panel: QWidget) -> None:
        """At the left edge of `panel`, its top aligned with the panel's (M3: hung at the edge, over the plan)."""
        if panel is None or not panel.isVisible():
            return
        corner = panel.mapToGlobal(QPoint(0, 0))
        self.adjustSize()
        self.move(corner.x() - self.width() - Space.M, corner.y() + Space.M)


class PlantInspector(QScrollArea):
    """The Inverter section of the Plant's right panel (design C10; R119; study 23): at the top the string chosen,
    only while one is (R298); the inverters one by one with their menus (R297); the Strings of the inverter shown,
    as cards or as a diagram (R298), with the commands at their head; the conditions of the checks; the sub-field
    selected, for the proposal. The page never computes: it shows energy/plant.Plant and reports the designer's
    edits as signals."""

    removed = Signal(int)                       # unit number: taken out of the plant
    renamed = Signal(int, str)                  # unit number, its name (R297)
    moved = Signal(int, int)                    # unit number, its new place from 0 (R297: the strings renumbered)
    datasheetAsked = Signal(int)                # unit number
    stringAsked = Signal(int)                   # unit number: «String this inverter…»
    emptied = Signal(int)                       # unit number: its strings deleted
    edited = Signal(str, object)                # path in energy, value
    assigned = Signal(str, int, int)            # sub-field, inverter (0: automatic), input (0: automatic)
    stringChosen = Signal(int)                  # index into Plant.strings, -1 none
    stringDeleteAsked = Signal(int)
    optimizerAsked = Signal(int)                # entry: choose its power optimizers in the catalogue (task 22)
    optimizerCleared = Signal(int)              # entry: back to the optimizers Meridiana proposes
    perChosen = Signal(int, int)                # entry, modules on each optimizer (1 or 2)
    viewChanged = Signal(str)                   # "cards" or "diagram", to remember (R298)

    def __init__(self, actions: dict, parent=None, view: str = "cards"):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.loading = False
        self.states = {"ok": theme_colors.STATUS["good"], "check": theme_colors.STATUS["warning"],
                       "fail": theme_colors.STATUS["critical"]}
        self.colours: list = []                     # each string's colour, as on the plan (the window's)
        page = QWidget()
        box = QVBoxLayout(page)
        box.setSpacing(Space.M)
        # the string chosen at the top (R298, C4), hidden without one
        self.string_group = ChosenString()
        self.string_group.redrawAsked.connect(lambda i: self.list.redraw.emit(i))
        self.string_group.moveAsked.connect(lambda i, where: self.list.menuAsked.emit(i, where))
        self.string_group.deleteAsked.connect(self.stringDeleteAsked)
        box.addWidget(self.string_group)
        self.string_group.hide()

        # the inverters (R297): the totals, the cards, the commands, the DC/AC ratio on its scale
        inv = self.inverters_group = Group(_("Inverter"))
        help_button(inv, "plant.inverters")
        inv_box = QVBoxLayout(inv)
        inv_box.setSpacing(Space.S)
        self.totals = QLabel("")
        self.totals.setWordWrap(True)
        set_text(self.totals, Text.DESCRIPTION)
        inv_box.addWidget(self.totals)
        self.units = InverterList()
        self.units.activated.connect(self._unit_activated)
        self.units.renamed.connect(self.renamed)
        self.units.moved.connect(self.moved)
        self.units.datasheetAsked.connect(self.datasheetAsked)
        self.units.stringAsked.connect(self.stringAsked)
        self.units.emptied.connect(self.emptied)
        self.units.removed.connect(self.removed)
        self.units.optimizerAsked.connect(self.optimizerAsked)
        self.units.optimizerCleared.connect(self.optimizerCleared)
        self.units.perChosen.connect(lambda k, per: self.perChosen.emit(k, per) if not self.loading else None)
        inv_box.addWidget(self.units)
        self.inverter_buttons = {}
        for cid in ("inverter_catalog", "inverter_auto"):        # one under the other: the panel may be narrow
            b = QPushButton(shortcuts.plain(actions[cid].text()))
            b.setToolTip(actions[cid].toolTip())
            b.clicked.connect(actions[cid].trigger)
            inv_box.addWidget(b)
            self.inverter_buttons[cid] = b
        form = make_form()
        self.ratio = spin(0.5, 2.0, 1.1, "", 2, 0.05)
        self.ratio.setToolTip(_("The modules' power over the inverters' AC power: «Choose automatically» picks the "
                                "size closest to it. The energy cut shows on the scale once the year is computed"))
        self.ratio.valueChanged.connect(lambda v: self._send("dc_ac_ratio", v))
        form.addRow(_("DC/AC ratio wanted"), self.ratio)
        self.clip_scale = ClipScale()                       # the ratio on its scale of the energy cut (R62)
        form.addRow(self.clip_scale)
        inv_box.addLayout(form)
        box.addWidget(inv)

        # the strings (R115, R298): the view chosen from the menu beside the «?», the commands at the head
        self.strings_group = Group(_("Strings"))
        help_button(self.strings_group, "plant.strings")
        self.view_button = QToolButton(self.strings_group)
        self.view_button.setObjectName("view-menu")
        self.view_button.setAutoRaise(True)
        self.view_button.setIcon(icons.icon("subfield"))
        self.view_button.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        self.view_button.setFixedSize(Button.SMALL[0], Button.SMALL[0])
        self.view_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.view_button.setToolTip(_("How the strings are shown: the inputs as cards, or a single-line diagram"))
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QActionGroup
        self.view_menu = QMenu(self.view_button)
        self.view_actions: dict = {}
        group = QActionGroup(self.view_menu)
        for key, name in view_names().items():
            a = self.view_menu.addAction(name)
            a.setCheckable(True)
            a.triggered.connect(lambda _c=False, k=key: self.set_view(k, tell=True))
            group.addAction(a)
            self.view_actions[key] = a
        self.view_button.setMenu(self.view_menu)
        self.strings_group._view_beside = _Beside(self.strings_group, self.view_button)
        sbox = QVBoxLayout(self.strings_group)
        sbox.setSpacing(Space.S)
        self.state = QLabel("")
        self.state.setWordWrap(True)
        set_text(self.state, Text.DESCRIPTION)
        sbox.addWidget(self.state)
        head = QHBoxLayout()
        head.setSpacing(Space.S)
        self.working_inverter = QComboBox()
        self.working_inverter.setAccessibleName(_("Inverter shown"))
        self.working_inverter.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.working_inverter.setMinimumContentsLength(8)        # a narrow panel: the name is in the cards too
        self.working_inverter.setToolTip(_("The inverter whose inputs and strings are shown (a click on its card "
                                           "does the same)"))
        self.working_inverter.currentIndexChanged.connect(self._working_changed)
        head.addWidget(self.working_inverter, 1)
        self.working_summary = QLabel("")
        set_text(self.working_summary, Text.SECONDARY)
        self.working_summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.working_summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(self.working_summary, 1)
        sbox.addLayout(head)
        self.list = StringsView()
        self.list.chosen.connect(lambda i: self.stringChosen.emit(i) if not self.loading else None)
        self.list.unitChanged.connect(self._working_shown)
        sbox.addWidget(self.list)
        self.string_buttons = {}
        for cid in ("strings_auto", "strings_manual", "strings_clear"):    # one under the other: a narrow panel
            if cid not in actions:
                continue
            b = QPushButton(shortcuts.plain(actions[cid].text()))
            b.setToolTip(actions[cid].toolTip())
            b.clicked.connect(actions[cid].trigger)
            sbox.addWidget(b)
            self.string_buttons[cid] = b
        box.addWidget(self.strings_group)

        # the conditions of the checks (study 23: what is left of «Proposal and checks»)
        rules = self.conditions_group = Group(_("Conditions of the checks"))
        help_button(rules, "plant.conditions")
        sf = make_form(rules)
        self.t_min = spin(-40, 20, -10, " °C", 1, 1)
        self.t_min.valueChanged.connect(lambda v: self._send("t_min", v))
        sf.addRow(_("Lowest temperature of the site"), self.t_min)
        sf.labelForField(self.t_min).setWordWrap(True)      # a narrow panel: the words wrap, the field stays
        self.conditions = QLabel("")
        self.conditions.setWordWrap(True)
        set_text(self.conditions, Text.SECONDARY)
        sf.addRow(self.conditions)
        box.addWidget(rules)

        self.subfield_group = Group(_("Sub-field selected"))
        help_button(self.subfield_group, "plant.subfield")
        sub = make_form(self.subfield_group)
        self.subfield_name = QLabel("")
        sub.addRow(self.subfield_name)
        self.sub_inverter = QComboBox()
        self.sub_input = QComboBox()
        self.sub_inverter.activated.connect(self._assign)
        self.sub_input.activated.connect(self._assign)
        for w in (self.sub_inverter, self.sub_input):
            w.setToolTip(_("Where «String automatically» sends the strings of this sub-field; the strings of now do "
                           "not change"))
        sub.addRow(_("Inverter of the proposal"), self.sub_inverter)
        sub.addRow(_("Input of the proposal"), self.sub_input)
        self.subfield = ""
        box.addWidget(self.subfield_group)
        self.subfield_group.hide()
        box.addStretch(1)
        self.setWidget(page)
        self.side = None                            # the Plant's page of three sections (PlantSide)
        self.plant = None
        self.set_view(view)

    def sizeHint(self) -> QSize:
        """Modest: the right panel is a stack of the phases' inspectors and takes the widest hint of them, so this
        one must not widen it in the other phases (the plan and the 3D view would lose the room)."""
        return QSize(240, 320)

    def minimumSizeHint(self) -> QSize:
        return QSize(180, 120)

    @property
    def view(self) -> str:
        return self.list.view

    def set_view(self, view: str, tell: bool = False) -> None:
        """The Strings as `view` ("cards" or "diagram"); `tell` says it to the window, which remembers it."""
        if view not in StringsView.VIEWS:
            view = "cards"
        self.list.set_view(view)
        self.view_actions[view].setChecked(True)
        self.view_button.setIcon(icons.icon("subfield" if view == "cards" else "row"))
        if tell:
            self.viewChanged.emit(view)

    def _send(self, path: str, value) -> None:
        if not self.loading:
            self.edited.emit(path, value)

    def _assign(self, _i=0) -> None:
        if self.loading or not self.subfield:
            return
        inv = int(self.sub_inverter.currentData() or 0)
        mppt = int(self.sub_input.currentData() or 0) if inv else 0
        self.assigned.emit(self.subfield, inv, mppt)

    def _unit_activated(self, unit: int) -> None:
        """A click on the card of an inverter: the Strings show it."""
        if unit != self.list.working_unit:
            blocked = self.working_inverter.blockSignals(True)
            try:
                self.working_inverter.setCurrentIndex(self.working_inverter.findData(unit))
            finally:
                self.working_inverter.blockSignals(blocked)
            if self.list.current() >= 0:
                self.stringChosen.emit(-1)
            self.list.set_unit(unit)
        self.units.set_current(unit)

    def _working_changed(self, _index: int) -> None:
        """The inverter shown changes the view only; the commands keep their scope."""
        if self.loading:
            return
        if self.list.current() >= 0:
            self.stringChosen.emit(-1)
        self.list.set_unit(int(self.working_inverter.currentData() or 0))

    def _working_shown(self, unit: int) -> None:
        """A string selected on the plan brings its inverter into view: the combo, the cards, the summary."""
        blocked = self.working_inverter.blockSignals(True)
        try:
            self.working_inverter.setCurrentIndex(self.working_inverter.findData(unit))
        finally:
            self.working_inverter.blockSignals(blocked)
        self.units.set_current(unit)
        plant = self.list.plant
        found = plant.unit(unit) if plant is not None else None
        if found is None:
            self.working_summary.setText("")
            return
        count = sum(1 for s in plant.strings if s.inverter == unit)
        power = sum(slot.power_w for (n, _k), slot in plant.inputs.items() if n == unit)
        text = ngettext("{n} string", "{n} strings", count).format(n=count)
        if power:
            text += " · " + _("{kwp} kWp").format(kwp=number(power / 1000.0, 1))
        self.working_summary.setText(text)
        tip = _("{name}: {kw} kW AC").format(name=found.name, kw=number(found.spec.pac / 1000, 1))
        if found.spec.imax_total is not None:
            tip += "\n" + _("Shared inverter DC current limit: {a} A").format(a=number(found.spec.imax_total, 1))
        self.working_summary.setToolTip(tip)

    def _working_units(self, plant) -> None:
        """Keep a physical unit's number across recalculations, including the pending calculation."""
        if plant is None:
            self.working_inverter.setEnabled(False)
            return
        unit = self.list.working_unit
        self.working_inverter.clear()
        for u in plant.units:
            self.working_inverter.addItem(f"{plant_model.unit_label(u)} · {u.name}", u.number)
        self.working_inverter.setCurrentIndex(max(0, self.working_inverter.findData(unit)))
        self.working_inverter.setEnabled(bool(plant.units))

    def show_string(self, plant, index: int) -> None:
        """The string chosen at the top of the column, with its bars and checks (hidden when none is chosen)."""
        self.string_group.show(plant, index, self.states)

    def show_plant(self, project, plant, selection: tuple = ("", ""), chosen: int = -1) -> None:
        """The inverters of `project`, the strings of `plant` (None while it is computed), the string chosen, the
        sub-field selected."""
        self.plant = plant
        self.show_string(plant, chosen)
        self.loading = True
        try:
            e = project.energy or {}
            entries = system.inverter_entries(e)
            self.totals.setText(plant_totals(plant))
            self.totals.setToolTip(system.describe(e))
            self._working_units(plant)
            self.ratio.setValue(float(e.get("dc_ac_ratio") or 1.1))
            if plant is not None:
                self.clip_scale.set(*plant_model.dcac(plant))
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
            self.units.show_units(plant, entries, self.list.working_unit)
            self._working_shown(self.list.working_unit)
            if plant is not None and "strings_clear" in self.string_buttons:
                self.string_buttons["strings_clear"].setEnabled(bool(plant.strings))
            self._subfield(project, plant, selection)
        finally:
            self.loading = False
        if self.side is not None:                   # R277: the sub-field's card and the storage beside
            self.side.follow(project, selection, chosen)

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


def storage_summary(economics: dict | None) -> str:
    """The storage of the project in a line (the Storage section of the Plant, R277): the battery, how many, the
    coupling; «No battery» without one."""
    e = economics or {}
    battery = e.get("battery") or {}
    name = f"{battery.get('manufacturer', '')} {battery.get('model', '')}".strip()
    if not name:
        return _("No battery")
    units = int(e.get("battery_units") or 1)
    coupling = {"ac": _("AC: independent storage converter"), "dc": _("DC: hybrid inverter")}.get(
        e.get("storage_coupling") or "", "")
    text = f"{units} × {name}" if units > 1 else name
    return f"{text}\n{coupling}" if coupling else text


class PlantSection(Group):
    """One of the three sections of the Plant's right panel (R277): a group that folds as every other (R287), and
    tells the page when it opens, so that one only is open and takes the panel's height."""

    def __init__(self, sid: str, title: str, page: "PlantSide"):
        super().__init__(title)
        self.sid = sid
        self.page = page

    def set_expanded(self, expanded: bool, ms: int = -1) -> None:
        from .design import Motion
        super().set_expanded(expanded, Motion.NORMAL if ms < 0 else ms)
        if self.collapsible and expanded:
            self.page._opened(self.sid)
        elif self.collapsible:
            self.page._restretch()                  # R296: a section closed keeps no height, the space goes below


class PlantSide(QWidget):
    """The right panel of the Plant phase (R277, decision 2c of study 22): one page with three sections in the order
    of the work, Panels, Inverter, Storage. Panels shows the card of the selected sub-field (the model's Properties,
    lent while the phase is open: the layout's fields where the modules are laid), Inverter the inverters and
    their strings (PlantInspector), Storage the battery with «Configure». One section is open at a time and takes
    the height left; the command used opens its own (a tool of the Panels, «Catalogue», «Configure», a string).
    The section open says what a click on a module of the plan is about: its row and its sub-field with Panels,
    as in the Modelling; its string with Inverter and Storage (the window, `_plant_clicks`)."""

    SECTIONS = ("panels", "inverter", "storage")
    sectionOpened = Signal(str)

    def __init__(self, inverters: PlantInspector, actions: dict, project=None, parent=None):
        super().__init__(parent)
        self.setObjectName("plant-side")
        self.project = project                          # the window's project now (a callable), for the storage
        self.inverters = inverters
        self.properties = None                          # the Properties lent (lend), None when at home
        self.selection: tuple = ("", "")
        self.chosen = -1
        self.current = ""
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(Space.S)
        self.box = box
        self.sections: dict[str, PlantSection] = {}
        for sid, title in (("panels", _("Panels")), ("inverter", _("Inverter")), ("storage", _("Storage"))):
            section = PlantSection(sid, title, self)
            inner = QVBoxLayout(section)
            inner.setContentsMargins(0, 0, 0, 0)
            self.sections[sid] = section
            box.addWidget(section)
        box.addStretch(0)                               # the empty space of the panel when every section is closed
        # Panels: the sub-field's card, or what to do when none is selected
        panels = self.sections["panels"].layout()
        self.panels_hint = QLabel(_("Select a sub-field on the plan to see its layout here, or draw one with "
                                    "«Sub-field»."))
        self.panels_hint.setWordWrap(True)
        self.panels_hint.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        free_text(self.panels_hint, Text.SECONDARY)             # the section's layout has no margins (R296)
        panels.addWidget(self.panels_hint)
        self.props_holder = QWidget()
        holder = QVBoxLayout(self.props_holder)
        holder.setContentsMargins(0, 0, 0, 0)
        panels.addWidget(self.props_holder, 1)
        self.props_holder.hide()
        # Inverter: the inverters and their strings, as before
        self.sections["inverter"].layout().addWidget(inverters, 1)
        # Storage: the battery in a line and the command that configures it
        storage = self.sections["storage"].layout()
        self.storage_text = QLabel(_("No battery"))
        self.storage_text.setWordWrap(True)
        free_text(self.storage_text)
        storage.addWidget(self.storage_text)
        if "battery_catalog" in actions:
            configure = QPushButton(shortcuts.plain(actions["battery_catalog"].text()))
            configure.setToolTip(actions["battery_catalog"].toolTip())
            configure.clicked.connect(actions["battery_catalog"].trigger)
            row = QHBoxLayout()                         # off the frame as the text above it (R296)
            row.setContentsMargins(Space.M, 0, Space.M, 0)
            row.addWidget(configure)
            row.addStretch(1)
            storage.addLayout(row)
        storage.addStretch(1)
        # the command used opens its section: the groups of the Plant's bar say which (phases.py)
        from .. import phases
        where = {"modules": "panels", "inverter": "inverter", "storage": "storage", "strings": "inverter"}
        self.command_section: dict[str, str] = {}
        for group in phases.by_id("plant").groups:
            if group.id == "edit":                  # R295: Select, Move, Rotate leave open what is open
                continue
            for tool in group.every():
                self.command_section[tool.command] = where.get(group.id, "inverter")
        for cid, sid in self.command_section.items():
            if cid in actions:
                actions[cid].triggered.connect(lambda _c=False, k=sid: self.open(k))
        self.open("panels", ms=0)
        inverters.side = self

    def open(self, sid: str, ms: int = -1) -> None:
        """Section `sid` open, the others closed; it takes the height left. The storage's line read again: after
        «Configure», whose dialog has just closed, it says the battery chosen."""
        if sid in self.sections:
            self.sections[sid].set_expanded(True, ms)
        if sid == "storage" and self.project is not None:
            self.show_storage(self.project())

    def show_storage(self, project) -> None:
        text = storage_summary(getattr(project, "economics", None))
        self.storage_text.setText(text)
        self.storage_text.setToolTip(text)

    def _opened(self, sid: str) -> None:
        changed = sid != self.current
        self.current = sid
        for other, section in self.sections.items():
            if other != sid and section.expanded:
                section.set_expanded(False)
        self._restretch()
        if changed:
            self.sectionOpened.emit(sid)

    def _restretch(self) -> None:
        """The height goes to the section that is open, to none when every one is closed: a closed section is as
        tall as its header and the space under it stays empty, out of every frame (R296)."""
        for section in self.sections.values():
            self.box.setStretch(self.box.indexOf(section), 1 if section.expanded else 0)
        self.box.setStretch(self.box.count() - 1, 0 if any(s.expanded for s in self.sections.values()) else 1)

    # the Properties, lent while the Plant is open (as the plan is to the Plant page)

    def lend(self, properties) -> None:
        if self.properties is properties:
            return
        self.properties = properties
        self.props_holder.layout().addWidget(properties)
        properties.show()
        self._show_card()

    def give_back(self):
        """The Properties taken back by the inspector: returned to the caller, None when not lent."""
        properties, self.properties = self.properties, None
        if properties is not None:
            self.props_holder.layout().removeWidget(properties)
        self._show_card()
        return properties

    def _show_card(self) -> None:
        card = self.properties is not None and self.selection[0] in ("subfield", "row")
        self.props_holder.setVisible(card)
        self.panels_hint.setVisible(not card)

    def follow(self, project, selection: tuple, chosen: int) -> None:
        """What the window shows changed: the sub-field's card in Panels, the storage's line. A sub-field selected
        anew opens Panels, a string chosen anew opens Inverter (never at each refresh of the same selection)."""
        selection = tuple(selection or ("", ""))
        if selection != self.selection and selection[0] in ("subfield", "row"):
            self.open("panels")
        if chosen >= 0 and chosen != self.chosen:
            self.open("inverter")
        self.chosen = chosen
        self.selection = selection
        self._show_card()
        self.show_storage(project)


class StringSectionDelegate(SectionDelegate):
    """The active input uses the same inset rounded surface as a selected string, below the header's air."""

    def paint(self, painter, option, index) -> None:
        from .sections import ACTIVE_ROLE, row_pill
        if index.data(ACTIVE_ROLE):
            low = QStyleOptionViewItem(option)
            low.rect.adjust(0, self.air, 0, 0)
            low.state |= QStyle.StateFlag.State_Selected
            row_pill(painter, low)
        super().paint(painter, option, index)


class StringList(QTreeWidget):
    """The strings of the plant in the right panel (R115, Daniel 25/10/2026: «se seleziono una stringa non mi porta alla
    stringa, se premo Canc non me la cancella, il + non fa nulla»): a section for each input of each inverter, its
    name and how many strings it has, «+» at its right to draw a new string on it; only the working inverter's
    inputs are shown, including unused ones. Under each input its strings, each with
    its colour on the plan, its name, its modules and its state as a mark and a word; an input without strings says
    so. A string chosen here is chosen on the plan and brought into view (the window); Del deletes it (the window's
    key), a double click draws it again, the right button opens its menu. As tall as its rows: it scrolls with the
    panel (design system, «Elenco a righe»)."""

    chosen = Signal(int)                        # index into Plant.strings, -1 none
    newString = Signal(int, int)                # unit, input
    redraw = Signal(int)                        # index: drawn again on the plan
    menuAsked = Signal(int, QPoint)             # index, where (global)
    unitChanged = Signal(int)                  # physical inverter shown, also when chosen on the plan

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("strings-list")
        self.setProperty("row-pills", True)
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
            self.setItemDelegateForColumn(column, StringSectionDelegate(self, pills=True))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemSelectionChanged.connect(self._selected)
        self.itemDoubleClicked.connect(self._double)
        self.loading = False
        self.adders: dict = {}                  # (unit, input) -> its «+»
        self.input_heads: dict = {}             # (unit, input) -> its section, highlighted while drawing there
        self.input_info: dict = {}              # (unit, input) -> limits, power and state, always visible
        self.rows: dict = {}                    # index into Plant.strings -> its row
        self.draft_input = (0, 0)
        self.working_unit = 0
        self.plant = None
        self.colours: list = []
        self.states: dict = {}

    def sizeHint(self) -> QSize:
        return QSize(200, self.height())

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange) and hasattr(self, "rows"):
            self._fit()

    def show_draft(self, unit: int = 0, mppt: int = 0) -> None:
        """Highlight the input being drawn on, and only until the draft is closed or given up."""
        from .sections import ACTIVE_ROLE
        if unit and not self.loading and unit != self.working_unit:
            self.set_unit(unit)
        self.draft_input = (int(unit), int(mppt))
        for key, head in self.input_heads.items():
            active = key == self.draft_input and unit > 0
            for column in range(2):
                head.setData(column, ACTIVE_ROLE, active)
                head.setData(column, Qt.ItemDataRole.BackgroundRole, None)
        self.viewport().update()

    def set_unit(self, unit: int) -> None:
        """Show every input of one physical inverter without changing the plant or the string indices."""
        if unit != self.working_unit:
            self.show_plant(self.plant, self.colours, self.states, unit=unit)

    def show_plant(self, plant, colours: list, states: dict, chosen: int = -1, *, unit: int | None = None) -> None:
        """All inputs of one physical unit, with global string indices, colours and checks. A chosen string
        brings its inverter into view; a recalculation otherwise keeps the current workspace."""
        from . import marks
        from .sections import section
        previous = self.working_unit
        self.plant, self.colours, self.states = plant, colours, states
        if plant is not None:
            wanted = unit if unit is not None else self.working_unit
            if 0 <= chosen < len(plant.strings):
                wanted = plant.strings[chosen].inverter
            units = {u.number for u in plant.units}
            self.working_unit = wanted if wanted in units else plant.units[0].number if plant.units else 0
        self.loading = True
        try:
            self.clear()
            self.adders, self.input_heads, self.input_info, self.rows = {}, {}, {}, {}
            if plant is None:
                return
            names = plant_model.state_names()
            level = {"ok": "ok", "check": "warn", "fail": "fail"}

            def string_row(parent, i):
                s = plant.strings[i]
                n = len(s.modules)
                tail = "  " + ngettext("{n} module", "{n} modules", n).format(n=n) + " · " + names.get(s.state, "")
                row = QTreeWidgetItem(parent, [s.label + tail, ""])
                row.setData(0, Qt.ItemDataRole.UserRole, i)
                row.setIcon(0, swatch(colours[i] if i < len(colours) else "#888888"))
                row.setIcon(1, marks.icon(level.get(s.state, "warn")))
                tip = f"{s.label}: {plant_model.voltages(s)}" + (f"\n{s.why}" if s.why else "")
                row.setToolTip(0, tip)
                row.setToolTip(1, names.get(s.state, ""))
                self.rows[i] = row

            for u in plant.units:
                if u.number != self.working_unit:
                    continue
                for k in range(1, u.inputs + 1):
                    slot = plant.inputs.get((u.number, k))
                    mine = list(slot.strings) if slot is not None else []
                    head = section(self, f"{plant_model.unit_label(u)} · {input_name(u, k)}", "")
                    takes = (optimized_takes(u, slot) if u.optimized else
                             _("takes {n} strings of {lo} to {hi} modules").format(n=slot.allowed, lo=slot.series[0],
                                                                                  hi=slot.series[1])
                             if slot is not None and slot.series[1] else _("its window is not known"))
                    head.setToolTip(0, f"{u.name}: {takes}")
                    self.input_heads[(u.number, k)] = head
                    self._adder(head, u.number, k, takes)
                    if slot is not None:
                        series = (_("{lo}-{hi} in series").format(lo=slot.series[0], hi=slot.series[1])
                                  if slot.series[1] else _("series range not known"))
                        parallel = _("max {n} in parallel").format(n=slot.allowed)
                        connectors = u.spec.inputs_per_mppt
                        physical = connectors[k - 1] if connectors and k <= len(connectors) else None
                        if not u.optimized:
                            parallel += "\n" + (_("{n} physical inputs share this MPPT").format(n=int(physical))
                                                 if physical is not None else _("Physical input count not specified"))
                            rules = u.spec.imax_by_strings
                            if rules and k <= len(rules) and isinstance(rules[k - 1], dict):
                                limits = [_("{n} strings: {a} A").format(n=n, a=number(a, 1))
                                          for n, a in rules[k - 1].items()]
                                if limits:
                                    parallel += "\n" + "; ".join(limits)
                        state = (_("empty") if not mine else
                                 {"ok": _("correct"), "warn": _("to be checked"), "fail": _("out of limit")}[slot.level])
                        count = ngettext("{n} string", "{n} strings", len(mine)).format(n=len(mine))
                        text = _("{series}\n{parallel}\n{power} kWp\n{count} · {state}").format(
                            series=series, parallel=parallel, power=number(slot.power_w / 1000.0, 2), count=count,
                            state=state)
                        info = QTreeWidgetItem(head, [text, ""])
                        info.setFlags(Qt.ItemFlag.ItemIsEnabled)
                        info.setIcon(1, marks.icon(slot.level if mine else "info"))
                        reasons = [slot.why] if slot.why else []
                        reasons += [plant.strings[i].why for i in mine if plant.strings[i].why]
                        info.setToolTip(0, "\n".join([takes] + list(dict.fromkeys(reasons))))
                        self.input_info[(u.number, k)] = info
                    for i in mine:
                        string_row(head, i)
                    if not mine:
                        free = QTreeWidgetItem(head, [_("free: «+» to draw a string on it"), ""])
                        free.setFlags(Qt.ItemFlag.ItemIsEnabled)
                        free.setToolTip(0, takes)
            # Strings whose inverter has gone must remain reachable for correction in every workspace.
            lost = [i for i, s in enumerate(plant.strings)
                    if (s.inverter == self.working_unit or s.inverter not in units)
                    and not plant.inputs.get((s.inverter, s.mppt))]
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
            if previous != self.working_unit:
                self.unitChanged.emit(self.working_unit)

    def _adder(self, head, unit: int, k: int, takes: str) -> None:
        """«+» on the row of an input: a tool button of the design system with Lucide's «plus»."""
        from .sections import AIR
        holder = QWidget()
        box = QHBoxLayout(holder)
        box.setContentsMargins(0, AIR, Space.XS, 0)
        box.setSpacing(0)
        add = QToolButton()
        add.setObjectName("add-string")
        add.setIcon(icons.icon("plus"))
        add.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        add.setAutoRaise(True)
        add.setToolTip(_("Activate input {k} of inverter {n}: draw a string, or another equal string in parallel, "
                         "by clicking its modules on the plan in order ({takes})").format(k=k, n=unit, takes=takes))
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
        if self.plant is not None and 0 <= index < len(self.plant.strings):
            unit = self.plant.strings[index].inverter
            if unit != self.working_unit:
                self.show_plant(self.plant, self.colours, self.states, chosen=index, unit=unit)
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
    def group_of(widget) -> QWidget:
        """The group a field is in: since R287 a Group keeps its fields in a body of its own, so the field's
        parent is the body, and hiding the body alone would leave the group's header on the page."""
        w = widget.parentWidget()
        while w is not None and not isinstance(w, QGroupBox):
            w = w.parentWidget()
        return w if w is not None else widget.parentWidget()
    old = group_of(page.inv_label)
    strings = group_of(page.t_min)
    box = page.form_box
    at = box.indexOf(old)
    ref = InverterReference(go)
    box.insertWidget(at if at >= 0 else 2, ref)
    for w in (old, strings):
        w.hide()
    return ref


class LazyReference:
    """`install_reference` for a page that is made later (ui/lazy_page.LazyPage): the reference is put in when the
    page is made, and what it was told before (`show_energy`) is told to it then; any other attribute asks for it."""

    def __init__(self, page, go):
        self._real = None
        self._energy = None
        self._told = False
        self._page = page

        def made(real) -> None:
            self._real = install_reference(real, go)
            if self._told:
                self._real.show_energy(self._energy)
        page.when_built(made)

    def show_energy(self, energy: dict | None) -> None:
        if self._real is not None:
            self._real.show_energy(energy)
        else:
            self._energy, self._told = energy, True

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if self._real is None:
            self._page.real()                       # made now: the hook has put the reference in
        return getattr(self._real, name)


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

