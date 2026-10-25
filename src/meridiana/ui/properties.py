"""The properties of the selected object, as a form: what the designer sets for a site, a building, a
sub-field, an exclusion. A value is sent when it is confirmed (Enter, leaving the field, a choice in a
list), never at every key: the layout runs once per change, not once per digit."""

from __future__ import annotations

import html
import math

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
                               QWidget)

from .. import layout, model, roofs, rules, sides
from ..i18n import _, ngettext, number, pgettext
from .design import Text, semibold, set_text
from .help_box import HintLabel, help_button, register
from .quantity_field import QuantityField
from .theme import mark
from .style import Group


def mounting_names() -> dict:
    return {
        "coplanar": _("Coplanar on the pitch"),
        "integrated": _("Integrated in the roof (BIPV)"),
        "tilted_anchored": _("Tilted rows, anchored"),
        "tilted_ballasted": _("Tilted rows, ballasted"),
        "east_west": _("East-west pairs"),
        "ground": _("Ground-mounted rows"),
        "canopy": _("Canopy or carport"),
    }


def roof_names() -> dict:
    return {"flat": _("Flat"), "mono": _("Mono-pitch"), "gable": _("Gable"), "hip": _("Hip"),
            "free": _("Pitches drawn by hand")}


def exclusion_names() -> dict:
    return model.exclusion_names()           # in the core since task 16c: the checks name them too


def field_label(path: str, kind: str = "") -> str:
    """What a changed field is called in the Undo menu."""
    if kind == "exclusion" and path == "height":
        return _("height")
    return {
        "name": _("name"), "height": _("eave height"), "roof.type": _("roof"), "roof.tilt": _("slope"),
        "roof.eave_side": _("eave side"), "fire.subject": _("fire control"),
        "fire.roof_fire_resistant": _("fire-resistant slab"), "module": _("module"),
        "params.mounting": _("mounting"), "params.portrait": _("orientation"), "params.stack": _("modules across"),
        "params.tilt": _("tilt"), "params.azimuth": _("azimuth"), "params.gap": _("gap between modules"),
        "params.edge": _("edge margin"), "params.shade_free": _("out of the shadows"), "params.flush_row_gap": _("gap between rows"),
        "params.table_modules": _("modules per table"), "params.table_gap": _("gap between tables"),
        "params.pitch_mode": _("row pitch"), "params.pitch": _("row pitch"), "params.gcr": _("ground cover ratio"),
        "kind": _("kind"), "clearance": _("clearance"), "sun_window": _("sun window"), "parapet": _("parapet"),
        "use_near": _("shading of the obstacles"), "footprint": _("outline"), "ring": _("outline"),
        "roof.edges": _("eaves and gable ends"), "roof.ridge_height": _("ridge height"),
        "roof.covering": _("covering"), "rules": _("connection and obligations"), "reserved": _("reserved"),
    }.get(path, path)


def combo(items, current) -> QComboBox:
    """A list that fits a narrow panel: it shows what fits and the whole text in its pop-up. No tooltip that
    repeats the choice (study 17, E.2: what a field means is in the help box, task 17d)."""
    c = QComboBox()
    c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(8)
    for key, label in items:
        c.addItem(label, key)
        c.setItemData(c.count() - 1, label, Qt.ItemDataRole.ToolTipRole)
    c.setCurrentIndex(max(0, c.findData(current)))
    return c


def make_form(parent=None) -> QFormLayout:
    """Label and field on one line while they fit, the field under its label when the panel is narrow."""
    f = QFormLayout(parent) if parent is not None else QFormLayout()
    f.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    return f


def spin(lo: float, hi: float, value: float, suffix: str = "", decimals: int = 2, step: float = 0.1) -> QDoubleSpinBox:
    """A number field; lengths (" m") and angles (" °") take their units and a calculation (QuantityField)."""
    if suffix in (" m", " °"):
        return QuantityField("length" if suffix == " m" else "angle", suffix.strip(), lo, hi, value, decimals, step)
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    s.setSuffix(suffix)
    s.setKeyboardTracking(False)          # valueChanged only when confirmed
    s.setGroupSeparatorShown(True)        # 1.300 €/kWp, not 1300
    s.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)    # as the mockups of C2
    return s


class LeadBox:
    """A page's box whose first layout added (the page's first form) goes into the group titled as the page; the
    rest into the page as before. Everything else is the box's own."""

    def __init__(self, box: QVBoxLayout, lead: QWidget):
        self.box, self.lead, self.filled = box, lead, False

    def addLayout(self, layout, *args) -> None:
        if not self.filled:
            self.filled = True
            self.lead.layout().addLayout(layout)
            return
        self.box.addLayout(layout, *args)

    def __getattr__(self, name):
        return getattr(self.box, name)


class WrappedCheck(QWidget):
    """A check box whose words wrap in a narrow panel: a QCheckBox never wraps, and one long line set the width
    of the whole right column (the target of 24/10/2026 gives it 380 px). The box keeps its words as its
    accessible name and tooltip's subject; a click on the words ticks it, as on a check box's own text."""

    def __init__(self, box: QCheckBox, parent=None):
        super().__init__(parent)
        self.box = box
        text = box.text()
        box.setText("")
        box.setAccessibleName(text.replace("&", ""))
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(box, 0, Qt.AlignmentFlag.AlignTop)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setBuddy(box)
        self.label.installEventFilter(self)
        row.addWidget(self.label, 1)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.label and event.type() == QEvent.Type.MouseButtonRelease and self.box.isEnabled():
            self.box.toggle()
            return True
        return False


def whole(lo: int, hi: int) -> QSpinBox:
    """A whole-number field. Its value is sent when confirmed, as in spin(): with the keyboard tracked, «12»
    sent 1 and then 12, and a result coming back meanwhile wrote over what was being typed (review, 23/10/2026)."""
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setKeyboardTracking(False)
    s.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return s


def _typing(w: QWidget) -> bool:
    """A field with the keyboard and text not yet confirmed: what the designer is writing."""
    if not w.hasFocus():
        return False
    if isinstance(w, QLineEdit):
        return w.isModified()
    if isinstance(w, (QSpinBox, QDoubleSpinBox)):
        if w.specialValueText() and w.value() == w.minimum():
            return w.text() != w.specialValueText()
        return w.cleanText() != w.textFromValue(w.value())
    return False


def _hold(w: QAbstractSpinBox, value) -> None:
    """A number field being written: the text stays as typed, the value under it becomes the project's. Enter
    or leaving the field sends what was typed when it differs from the project, not from what the field held
    before: after a change from elsewhere, a value typed equal to the old one was taken for no change, and a
    text refused went back to the old value instead of the project's (review of phase 2, 23/10/2026)."""
    edit = w.lineEdit()
    text, cursor = edit.text(), edit.cursorPosition()
    start, length = edit.selectionStart(), len(edit.selectedText())
    blocked = w.blockSignals(True)
    try:
        w.setValue(value)
        edit.setText(text)          # with the editor's signals on: the field knows it has text to confirm
        if start >= 0 and length:
            edit.setSelection(start, length)
        else:
            edit.setCursorPosition(cursor)
    finally:
        w.blockSignals(blocked)


def put(w: QWidget, value, force: bool = False) -> None:
    """Show `value` in a field without a signal (it is not an edit), and leave a field being written alone;
    `force` drops what is being written (after an undo, the text belonged to a project that is gone)."""
    if not force and _typing(w):
        if isinstance(w, (QSpinBox, QDoubleSpinBox)) and w.textFromValue(value) != w.textFromValue(w.value()):
            _hold(w, value)
        return
    blocked = w.blockSignals(True)
    try:
        if isinstance(w, QLineEdit):
            if w.text() != value:
                w.setText(value)
            w.setModified(False)
        elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
            if force or w.textFromValue(value) != w.cleanText():
                w.setValue(value)
        elif isinstance(w, QComboBox):
            i = max(0, w.findData(value))
            if i != w.currentIndex():
                w.setCurrentIndex(i)
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(value))
        elif isinstance(w, QLabel):
            w.setText(value)
            w.setVisible(bool(value))
    finally:
        w.blockSignals(blocked)


class Properties(QScrollArea):
    """A page per kind of object. A new result or an edit of the object shown sets the values of the page in
    place: the page is built again only for another object, or when the fields themselves change (a roof
    type with a slope or without, a pitch from the sun or given). Building it again cost time at every edit,
    and took away the field being written, with what was in it (study 12, I1, I4, P5)."""

    edited = Signal(str, str, dict)        # kind, id, the fields changed
    action = Signal(str, str, str)         # what ("fill", "empty", "fit", "site"), kind, id
    pageShown = Signal(str)                # the help id of the page just built, for the help box (help_box.py)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(260)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)    # holds the keyboard while a page is replaced
        self.kind, self.oid = "", ""
        self._pending_focus: int | None = None
        self.rebuilds = 0                     # pages built, for the tests: values alone do not build one
        self._shape: tuple | None = None      # what decides the fields of the page shown
        self._binds: list = []                # (field, value now) for each field of the page
        self.shown: dict = {}                 # what the page shows: "project", "object", "result", ...
        self._page_kind = ""                  # the kind of object of the page shown
        self._scroll_back = None              # waiting for the new page's height to scroll it back
        self._drop = False                    # drop_typing: the next values replace what is being written
        self.show_none()

    def _same(self, shape: tuple) -> bool:
        """True when the page shown has these fields already: only the values need setting."""
        if shape == self._shape and self.widget() is not None:
            return True
        self._shape = shape
        return False

    def _bind(self, widget: QWidget, value, setter=None):
        """Keep `widget` showing `value()`, the object's value as it is now; `setter` for what is not a value
        of a field (a button enabled or not)."""
        self._binds.append((widget, value, setter or put))
        if isinstance(widget, QuantityField) and setter is None:
            widget.refused.connect(lambda why: self.action.emit("refused:" + why, self.kind, self.oid))
        return widget

    def _text(self, value, send) -> QLineEdit:
        """A text field showing `value()`. Enter or leaving it sends what it holds (`send(text)`) and then shows
        what the project kept: the name without the spaces around it, the old one for an empty field. Still
        marked as being written after Enter, it went on showing an empty field (review, 23/10/2026)."""
        field = self._bind(QLineEdit(), value)

        def confirmed():
            text = field.text()
            field.setModified(False)        # confirmed: what the project answers is shown from here on
            send(text)
            put(field, value())
        field.editingFinished.connect(confirmed)
        return field

    def _refresh(self) -> None:
        force, self._drop = self._drop, False
        for widget, value, setter in self._binds:
            if setter is put:
                put(widget, value(), force)
            else:
                setter(widget, value())

    def drop_typing(self) -> None:
        """The project was put back (undo, redo, another variant): the next values shown replace what a field
        holds unconfirmed, which was written for the project before; Enter would have sent it to the one now
        shown, to the sub-field of another variant with the same id too (review of phase 2, 23/10/2026)."""
        self._drop = True

    def _page(self, title: str, hid: str = ""):
        """A new page in place of the old one. The old one goes later: an edit rebuilds the panel from inside
        the signal of the field being edited, and a field deleted under its own key press (setWidget deletes
        at once) brought the program down. The keyboard stays on the same field of the new page. `hid` is the
        page's help (help.py): what explains its fields that have no help of their own."""
        self.rebuilds += 1
        self._binds = []
        place = self._focus_place()
        if place is None:
            place = self._pending_focus           # a second rebuild before the first one gave it back
        self._pending_focus = place
        current = self.widget()
        if current is not None:
            # the old page says nothing more from here on: a field that loses the keyboard below confirms what
            # it holds, and a value typed halfway ("0," of "0,07") went into the project as 0 (22/10/2026)
            for w in current.findChildren(QWidget):
                w.blockSignals(True)
        if place is not None:
            self.setFocus(Qt.FocusReason.OtherFocusReason)    # not to the next widget of the window meanwhile
        # from one object to another of the same kind the page stays where it was scrolled: back at the top at
        # each click it looked like a panel loaded again from nothing (Daniel, 23/10/2026)
        scrolled = self.verticalScrollBar().value() if self.kind == self._page_kind else 0
        self._page_kind = self.kind
        old = self.takeWidget()
        if old is not None:
            old.hide()
            old.deleteLater()
        page = QWidget()
        box = QVBoxLayout(page)
        if hid:
            # the page's title is the header of a group holding its first fields (C3, the target of 24/10/2026)
            register(page, hid)
            lead = Group(title)
            lead.setObjectName("lead")
            QVBoxLayout(lead).setContentsMargins(8, 4, 8, 8)
            help_button(lead, hid)                     # the «?» of the page, on its title's row
            box.addWidget(lead)
            box = LeadBox(box, lead)
        else:
            box.addWidget(set_text(QLabel(title), Text.STRONG))
        # another subject fades in over the one before (R75); the same subject made again (a value changed) does not
        from .motion import crossfade
        subject = (title, hid)
        if subject != getattr(self, "_subject", None) and self.widget() is not None:
            crossfade(self.viewport(), lambda: self.setWidget(page))
        else:
            self.setWidget(page)
        self._subject = subject
        self.pageShown.emit(hid)
        # the fields' text off their edge, once the page is built (ui/style.pad_fields)
        from PySide6.QtCore import QTimer as _Timer
        from .style import pad_fields
        _Timer.singleShot(0, page, lambda: pad_fields(page))
        bar = self.verticalScrollBar()
        if self._scroll_back is not None:
            bar.rangeChanged.disconnect(self._scroll_back)
            self._scroll_back = None
        if scrolled:
            # when the new page has its height, before it is painted: earlier the bar has no room for the value
            def back(_low, high):
                if high >= scrolled:
                    bar.setValue(scrolled)
                    bar.rangeChanged.disconnect(back)
                    self._scroll_back = None
            self._scroll_back = back
            bar.rangeChanged.connect(back)
        if place is not None:
            QTimer.singleShot(0, lambda: self._refocus(page, place))
        return box

    @staticmethod
    def _fields(page) -> list:
        """The fields of a page that take the keyboard, in their order. A page just built is not shown yet
        (its layout shows the fields a moment later): a field counts unless it, or a box it is in, was
        hidden on purpose."""
        def shown(w):
            while w is not None and w is not page:
                if w.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide) and w.isHidden():
                    return False
                w = w.parentWidget()
            return True
        return [w for w in page.findChildren(QWidget)
                if w.focusPolicy() & Qt.FocusPolicy.TabFocus and w.isEnabled() and shown(w)
                and not isinstance(w.parentWidget(), (QAbstractSpinBox, QComboBox))]   # not their inner editors

    def _focus_place(self) -> int | None:
        """Which field of the page has the keyboard, by its place among the fields."""
        page, w = self.widget(), QApplication.focusWidget()
        if page is None or w is None or not page.isAncestorOf(w):
            return None
        fields = self._fields(page)
        while w is not None and w is not page:
            if w in fields:
                return fields.index(w)
            w = w.parentWidget()
        return None

    def _refocus(self, page, place: int) -> None:
        if self.widget() is not page:
            return
        self._pending_focus = None
        fields = self._fields(page)
        if 0 <= place < len(fields):
            fields[place].setFocus(Qt.FocusReason.OtherFocusReason)

    def show_none(self) -> None:
        self.kind, self.oid = "", ""
        if self._same(("none",)):
            return
        box = self._page(_("Nothing selected"))
        note = QLabel(_("Choose a tool to draw a building, a sub-field or an exclusion, or click an object to see "
                        "its properties."))
        note.setWordWrap(True)
        box.addWidget(note)
        box.addStretch(1)

    def _emit(self, field: str, value) -> None:
        self.edited.emit(self.kind, self.oid, {field: value})

    @staticmethod
    def _note(text: str = "") -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    # site

    def show_site(self, project: model.Project, can_move: bool) -> None:
        self.kind, self.oid = "site", ""
        self.shown = {"project": project, "can_move": can_move}
        if not self._same(("site",)):
            self._build_site()
        self._refresh()

    def _project(self) -> model.Project:
        return self.shown["project"]

    def _build_site(self) -> None:
        box = self._page(_("Site"), "site")
        form = make_form()
        name = self._text(lambda: self._project().name, lambda text: self.edited.emit(
            "project", "", {"name": text.strip() or self._project().name}))
        form.addRow(_("Project"), name)
        form.addRow(_("Latitude"), self._bind(QLabel(), lambda: number(self._project().site.lat, 6)))
        form.addRow(_("Longitude"), self._bind(QLabel(), lambda: number(self._project().site.lon, 6)))
        address = QLabel()
        address.setWordWrap(True)
        form.addRow(_("Address"), address)

        def show_address(label, text):
            label.setText(text)
            form.setRowVisible(label, bool(text))
        self._bind(address, lambda: self._project().site.address, show_address)
        # task 14: Meridio never sends anything of a reserved project to a cloud model
        reserved = self._bind(QCheckBox(_("Reserved: never sent to a cloud model")),
                              lambda: bool(getattr(self._project(), "reserved", False)))
        reserved.setToolTip(_("Meridio answers about this project only with the local model, whatever his "
                              "settings say"))
        reserved.toggled.connect(lambda v: self.edited.emit("project", "", {"reserved": v}))
        form.addRow(reserved)
        box.addLayout(form)
        move = QPushButton(_("Find the site…"))

        def movable(button, can):
            button.setEnabled(can)
            button.setToolTip(_("Search an address or type coordinates.") if can else
                              _("The site can be moved only before anything is drawn: the drawing is measured "
                                "from it."))
        self._bind(move, lambda: self.shown["can_move"], movable)
        move.clicked.connect(lambda: self.action.emit("site", "site", ""))
        box.addWidget(move)

        sun = Group(_("Row pitch from the sun"))
        help_button(sun, "site.sun_window")
        sform = make_form(sun)

        def window():
            return self._project().sun_window
        day = whole(1, 31)
        self._bind(day, lambda: int(window()["day"]))
        month = whole(1, 12)
        self._bind(month, lambda: int(window()["month"]))
        start = self._bind(spin(0, 24, 0, " h", 1, 0.5), lambda: float(window()["start"]))
        end = self._bind(spin(0, 24, 0, " h", 1, 0.5), lambda: float(window()["end"]))
        row = QHBoxLayout()
        row.addWidget(day)
        row.addWidget(QLabel("/"))
        row.addWidget(month)
        holder = QWidget()
        holder.setLayout(row)
        register(holder, "site.sun_window.day")
        sform.addRow(_("Day"), holder)
        sform.addRow(_("From (solar time)"), start)
        sform.addRow(_("To (solar time)"), end)
        sform.addRow(self._note(_("No row shades the next one on that day between those hours. The standards leave "
                                  "this choice to the designer (CEI 82-25/3 6.2 gives only the limit angle).")))

        def send():
            self.edited.emit("project", "", {"sun_window": {**window(), "day": day.value(), "month": month.value(),
                                                           "start": start.value(), "end": end.value()}})
        for wdg in (day, month):
            wdg.editingFinished.connect(send)
        for wdg in (start, end):
            wdg.valueChanged.connect(lambda _v: send())
        box.addWidget(sun)
        box.addWidget(self._rules_group())
        box.addStretch(1)

    def _rules_group(self) -> QGroupBox:
        """What the rules need beyond the drawing: the connection level and the minimum renewable capacity of
        the building (D.Lgs. 199/2021), with what decides it."""
        def rules_now():
            return dict(self._project().rules or {})
        group = Group(_("Connection and obligations"))
        help_button(group, "site.rules")
        form = make_form(group)

        def send(key, value):
            self.edited.emit("project", "", {"rules": {**rules_now(), key: value}})
        level = self._bind(combo(rules.level_names().items(), "auto"), lambda: rules_now().get("connection") or "auto")
        level.currentIndexChanged.connect(lambda _i: send("connection", level.currentData()))
        level.setToolTip(_("The distributor decides; CEI 0-16 Tab. 4 indicates low voltage up to 100 kW, medium voltage "
                           "up to 6 MW for production, high voltage above 10 MW."))
        form.addRow(_("Connection"), level)
        obligation = self._bind(combo(rules.obligation_names().items(), ""), lambda: rules_now().get("obligation") or "")
        obligation.currentIndexChanged.connect(lambda _i: send("obligation", obligation.currentData()))
        form.addRow(_("Minimum renewable capacity"), obligation)
        public = self._bind(QCheckBox(_("Public building (+10%)")), lambda: bool(rules_now().get("public")))
        public.toggled.connect(lambda v: send("public", v))
        form.addRow(public)
        use = self._bind(combo(rules.use_names().items(), "other"), lambda: rules_now().get("use") or "other")
        use.currentIndexChanged.connect(lambda _i: send("use", use.currentData()))
        form.addRow(_("Use of the building"), use)
        permit = self._bind(QCheckBox(_("Permit requested from 01/01/2027")), lambda: bool(rules_now().get("permit_2027")))
        permit.toggled.connect(lambda v: send("permit_2027", v))
        form.addRow(permit)
        # DM 37/2008 art. 5 par. 2: who may design depends on the supply and the premises, not on the PV power
        contracted = self._bind(spin(0, 100000, 0, " kW", 1, 0.5), lambda: float(rules_now().get("contracted_kw") or 0))
        contracted.setSpecialValueText(_("not stated"))
        contracted.setToolTip(_("The contracted power of the supply (the POD), not the power of the PV system: "
                                "DM 37/2008 art. 5 par. 2 asks for a professional's design above 6 kW."))
        contracted.valueChanged.connect(lambda v: send("contracted_kw", float(v)))
        form.addRow(_("Contracted power"), contracted)
        floor = self._bind(spin(0, 1000000, 0, " m²", 0, 10), lambda: float(rules_now().get("floor_m2") or 0))
        floor.setSpecialValueText(_("not stated"))
        floor.setToolTip(_("The floor area of the premises: above 200 m² (production, commerce, services) or 400 m² "
                           "(a dwelling) the design is a professional's (DM 37/2008 art. 5 par. 2)."))
        floor.valueChanged.connect(lambda v: send("floor_m2", float(v)))
        form.addRow(_("Floor area of the premises"), floor)
        premises = self._bind(combo(rules.premises_names().items(), ""), lambda: rules_now().get("premises") or "")
        premises.currentIndexChanged.connect(lambda _i: send("premises", premises.currentData()))
        form.addRow(_("Premises"), premises)
        risk = self._bind(QCheckBox(_("Higher fire risk, medical use or explosion hazard")),
                          lambda: bool(rules_now().get("risk")))
        risk.setToolTip(_("Environments subject to specific CEI rules (for the fire risk, CEI 64-8/7 sect. 751.03): "
                          "the design is always a professional's (DM 37/2008 art. 5 par. 2 d)."))
        risk.toggled.connect(lambda v: send("risk", v))
        form.addRow(WrappedCheck(risk))

        def region_note():
            region = rules.region_of(self._project().site.address)
            return (_("Region from the address: {region}. Lombardy raises k for permits from 01/01/2027.").format(
                region=region) if region else _("The address does not name a region with rules of its own: the "
                                                "national ones apply."))
        form.addRow(self._bind(self._note(), region_note))
        return group

    # building

    def show_building(self, b: model.Building) -> None:
        self.kind, self.oid = "building", b.id
        self.shown = {"object": b}
        if not self._same(("building", b.id, b.roof.type, len(b.footprint))):
            self._build_building(b)
        self._refresh()

    def _object(self):
        return self.shown["object"]

    def _build_building(self, b: model.Building) -> None:
        box = self._page(_("Building"), "building")
        form = make_form()
        name = self._text(lambda: self._object().name,
                          lambda text: self._emit("name", text.strip() or self._object().name))
        form.addRow(_("Name"), name)
        height = self._bind(spin(0.5, 300, b.height, " m"), lambda: self._object().height)
        height.valueChanged.connect(lambda v: self._emit("height", v))
        form.addRow(_("Eave height"), height)
        box.addLayout(form)
        box.addWidget(self._roof_group(b))
        box.addWidget(self._sides_group(len(b.footprint), lambda: self._object().footprint, "footprint"))

        fire = Group(_("Fire brigade"))
        help_button(fire, "building.fire")
        fform = make_form(fire)
        subject = self._bind(QCheckBox(_("Activity subject to control (DPR 151/2011)")),
                             lambda: self._object().fire.subject)
        subject.toggled.connect(lambda v: self._emit("fire.subject", v))
        fform.addRow(WrappedCheck(subject))
        rei = self._bind(QCheckBox(_("Fire-resistant roof slab")), lambda: self._object().fire.roof_fire_resistant)
        rei.toggled.connect(lambda v: self._emit("fire.roof_fire_resistant", v))
        fform.addRow(rei)
        fform.addRow(self._note(_("For an activity subject to control, the sub-fields keep 1 m from the edge, groups "
                                  "of at most 20 m and 2 m corridors (DCPREV 14030/2025, 3.3.5.1).")))
        box.addWidget(fire)
        box.addStretch(1)

    def _roof_group(self, b: model.Building) -> QGroupBox:
        """The roof (task 16a; style C3 of the design, 3.6): its type, what covers it with the slope it proposes,
        the slope, the ridge height that sets the slope when written, and on a gable or hip roof each side as an
        eave or a gable end, also clicked on the plan."""
        group = Group(_("Roof"))
        help_button(group, "building.roof")
        form = make_form(group)
        kind = self._bind(combo(roof_names().items(), b.roof.type), lambda: self._object().roof.type)
        kind.currentIndexChanged.connect(lambda _i: self.edited.emit(
            self.kind, self.oid, self._object().retyped(kind.currentData())))
        form.addRow(_("Type"), kind)
        pitched = b.roof.type in model.PITCHED
        if b.roof.type in ("mono", *model.PITCHED):
            names = roofs.covering_names()
            covering = self._bind(combo([(k, _("{covering} ({p} %)").format(covering=names[k], p=number(pct, 0)))
                                         for k, pct in roofs.COVERINGS.items()], b.roof.covering),
                                  lambda: self._object().roof.covering or roofs.DEFAULT_COVERING)

            def covered(_i):
                c = covering.currentData()
                changes = {"roof.covering": c, "roof.tilt": roofs.proposed_tilt(c)}
                if self._object().roof.ridge_height is not None:
                    changes["roof.ridge_height"] = None            # the slope proposed wins over the ridge
                self.edited.emit(self.kind, self.oid, changes)
            covering.currentIndexChanged.connect(covered)
            form.addRow(_("Covering"), covering)

            def slope(degrees):
                changes = {"roof.tilt": degrees}
                if self._object().roof.ridge_height is not None:
                    changes["roof.ridge_height"] = None            # a slope written wins over the ridge
                self.edited.emit(self.kind, self.oid, changes)
            tilt = self._bind(spin(0, 80, b.slope(), " °", 1, 1), lambda: self._object().slope())
            tilt.valueChanged.connect(slope)
            form.addRow(_("Slope"), tilt)
            percent = self._bind(spin(0, 600, 0, " %", 1, 1),
                                 lambda: math.tan(math.radians(self._object().slope())) * 100)
            percent.valueChanged.connect(lambda v: slope(math.degrees(math.atan(v / 100))))
            form.addRow(_("Slope (percent)"), percent)
            proposed = self._bind(self._note(), lambda: _("Proposed for {covering}: {p} %, from {source}.").format(
                covering=names.get(self._object().roof.covering or roofs.DEFAULT_COVERING, ""),
                p=number(roofs.COVERINGS.get(self._object().roof.covering or roofs.DEFAULT_COVERING, 35.0), 0),
                source=roofs.covering_source(self._object().roof.covering)))
            form.addRow(proposed)
        if pitched:
            ridge = self._bind(spin(0.5, 1000, b.ridge(), " m", 2, 0.1), lambda: self._object().ridge())
            ridge.setToolTip(_("The height of the ridge above the ground: written, it sets the slope (the highest "
                               "point of the roof stands there)"))

            def ridge_written(value):
                if value <= self._object().height + 0.01:
                    self.action.emit("refused:" + _("the ridge must stand above the eave ({h} m)").format(
                        h=number(self._object().height)), self.kind, self.oid)
                    put(ridge, self._object().ridge(), True)
                    return
                self.edited.emit(self.kind, self.oid, {"roof.ridge_height": round(value, 3)})
            ridge.valueChanged.connect(ridge_written)
            form.addRow(_("Ridge height"), ridge)
        if b.roof.type == "mono":
            side = whole(1, len(b.footprint))
            self._bind(side, lambda: self._object().roof.eave_side + 1)
            side.valueChanged.connect(lambda v: self._emit("roof.eave_side", v - 1))
            form.addRow(_("Eave on side"), self._with_pick(side, "eave", _("Click on the plan the side the roof "
                                                                         "goes down to")))
        if pitched:
            kinds = ((("eave", _("Eave")), ("gable", _("Gable end"))))
            for i in range(len(b.footprint)):
                edge = self._bind(combo(kinds, "eave"), lambda i=i: self._object().sides_kind()[i])
                edge.currentIndexChanged.connect(lambda _i, i=i, e=edge: self._emit(
                    "roof.edges", self._object().with_side(i, e.currentData())))
                form.addRow(_("Side {n}").format(n=i + 1), edge)
            pick = QPushButton(_("Pick on the plan"))
            pick.setToolTip(_("Click a side on the plan: an eave becomes a gable end, a gable end an eave"))
            pick.clicked.connect(lambda: self.action.emit("pick_gable", self.kind, self.oid))
            form.addRow(pick)
            problem = self._note()
            problem.setTextFormat(Qt.TextFormat.RichText)
            form.addRow(self._bind(problem, self._roof_note))
        if b.roof.type == "flat":
            parapet = self._bind(spin(0, 5, b.parapet, " m", 2, 0.1), lambda: self._object().parapet)
            parapet.setToolTip(_("Height of the parapet above the roof, all round: it casts shadows on the modules"))
            parapet.valueChanged.connect(lambda v: self._emit("parapet", v))
            form.addRow(_("Parapet"), parapet)
        return group

    def _roof_note(self) -> str:
        """What the roof could not be as asked (model.Building.roof_problem), or nothing."""
        what, sides_ = self._object().roof_problem()
        if what == "gables":
            return mark("⚠") + " " + html.escape(ngettext(
                "Side {sides} cannot be a gable end on this outline: it is an eave.",
                "Sides {sides} cannot be gable ends on this outline: they are eaves.", len(sides_)).format(
                sides=", ".join(str(s + 1) for s in sides_)))
        if what == "outline":
            return mark("⚠") + " " + html.escape(_("The outline crosses itself: the roof stays flat until it is "
                                                   "put right."))
        return ""

    def _with_pick(self, field, purpose: str, tip: str) -> QWidget:
        """A field and, next to it, the button that lets the designer click the side on the plan instead."""
        pick = QPushButton(_("Pick on the plan"))
        pick.setToolTip(tip)
        pick.clicked.connect(lambda: self.action.emit("pick_" + purpose, self.kind, self.oid))
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field, 1)
        row.addWidget(pick)
        holder = QWidget()
        holder.setLayout(row)
        return holder

    def _sides_group(self, n: int, ring, path: str) -> QGroupBox:
        """The length of each side, to change after drawing: the side stretches as in CAD programs, what is
        at its far end moving with it. A double click on a side's measure on the plan does the same. `ring`
        gives the outline as it is now."""
        group = Group(_("Sides"))
        help_button(group, "sides")
        form = make_form(group)
        for i in range(n):
            s = self._bind(spin(0.1, 10000, 1.0, " m", 2, 0.1), lambda i=i: sides.lengths(ring())[i])

            def send(v, i=i):
                try:
                    self._emit(path, sides.stretch(ring(), i, v))
                except ValueError as error:
                    self.action.emit("refused:" + str(error), self.kind, self.oid)
            s.valueChanged.connect(send)
            form.addRow(_("Side {n}").format(n=i + 1), s)
        return group

    # sub-field

    def show_subfield(self, project: model.Project, sf: model.SubField, result: layout.Result | None,
                      state: str = "ok", error: str = "") -> None:
        """`state` is where its layout stands (model.Project.layout_state): a layout to do again or failed
        is said above the figures, as FreeCAD marks the objects to recompute and those in error."""
        self.kind, self.oid = "subfield", sf.id
        self.shown = {"project": project, "object": sf, "result": result, "state": state, "error": error}
        p = sf.layout_params()
        flush = p.mounting in layout.FLUSH
        shape = ("subfield", sf.id, flush, p.mounting == "canopy", None if flush else p.pitch_mode, sf.filled,
                 sf.manual, len(sf.ring), tuple((k, m["manufacturer"], m["model"]) for k, m in project.modules.items()))
        if not self._same(shape):
            self._build_subfield(project, sf)
        self._refresh()

    def _params(self) -> layout.Params:
        return self._object().layout_params()

    def _build_subfield(self, project: model.Project, sf: model.SubField) -> None:
        p = sf.layout_params()
        box = self._page(_("Sub-field"), "subfield")
        form = make_form()
        name = self._text(lambda: self._object().name,
                          lambda text: self._emit("name", text.strip() or self._object().name))
        form.addRow(_("Name"), name)
        mounting = self._bind(combo(mounting_names().items(), p.mounting), lambda: self._params().mounting)
        register(mounting, "subfield.mounting")
        mounting.currentIndexChanged.connect(lambda _i: self._emit("params.mounting", mounting.currentData()))
        form.addRow(_("Mounting"), mounting)
        module = self._bind(combo(((key, f"{m['manufacturer']} {m['model']}") for key, m in project.modules.items()),
                                  sf.module), lambda: self._object().module)
        module.currentIndexChanged.connect(lambda _i: self._emit("module", module.currentData()))
        pick = QPushButton(_("Catalogue…"))
        pick.setToolTip(_("Choose the module among the datasheets and the CEC list"))
        pick.clicked.connect(lambda: self.action.emit("catalog_module", "subfield", self.oid))
        row_m = QHBoxLayout()
        row_m.addWidget(module, 1)
        row_m.addWidget(pick)
        holder_m = QWidget()
        holder_m.setLayout(row_m)
        form.addRow(_("Module"), holder_m)
        orient = self._bind(combo(((True, _("Portrait")), (False, _("Landscape"))), p.portrait),
                            lambda: self._params().portrait)
        orient.currentIndexChanged.connect(lambda _i: self._emit("params.portrait", orient.currentData()))
        form.addRow(_("Orientation"), orient)
        stack = whole(1, 6)
        register(stack, "subfield.stack")
        self._bind(stack, lambda: self._params().stack)
        stack.valueChanged.connect(lambda v: self._emit("params.stack", v))
        form.addRow(_("Modules per table, across"), stack)
        flush = p.mounting in layout.FLUSH
        if not flush or p.mounting == "canopy":
            tilt = self._bind(spin(0, 60, p.tilt, " °", 1, 1), lambda: self._params().tilt)
            tilt.valueChanged.connect(lambda v: self._emit("params.tilt", v))
            form.addRow(_("Module tilt"), tilt)
        auto = self._bind(QCheckBox(_("Automatic")), lambda: self._params().azimuth is None)
        azimuth = spin(-180, 180, 0.0, " °", 1, 1)

        def azimuth_now():
            q, r = self._params(), self.shown["result"]
            return r.azimuth if r is not None and q.azimuth is None else (q.azimuth or 0.0)

        def enabled(w, on):
            w.setEnabled(on)
        self._bind(azimuth, azimuth_now)
        self._bind(azimuth, lambda: self._params().azimuth is not None, enabled)
        auto.toggled.connect(lambda v: self._emit("params.azimuth", None if v else azimuth.value()))
        azimuth.valueChanged.connect(lambda v: self._emit("params.azimuth", v) if not auto.isChecked() else None)
        row = QHBoxLayout()
        row.addWidget(azimuth, 1)
        row.addWidget(auto)
        holder = QWidget()
        holder.setLayout(row)
        form.addRow(_("Azimuth (from South, + West)"), holder)
        box.addLayout(form)

        gaps = Group(_("Gaps and margins"))
        help_button(gaps, "subfield.gaps")
        gform = make_form(gaps)
        for field, label, hi in (("gap", _("Between modules"), 1.0), ("edge", _("From the edge of the area"), 20.0)):
            s = self._bind(spin(0, hi, 0, " m", 2, 0.01 if hi <= 1 else 0.1),
                           lambda f=field: getattr(self._params(), f))
            s.valueChanged.connect(lambda v, f=field: self._emit("params." + f, v))
            if field == "edge":
                register(s, "subfield.edge")
            gform.addRow(label, s)
        if flush:
            s = self._bind(spin(0, 2, 0, " m", 2, 0.01), lambda: self._params().flush_row_gap)
            register(s, "subfield.row_gap")
            s.valueChanged.connect(lambda v: self._emit("params.flush_row_gap", v))
            gform.addRow(_("Between rows"), s)
            gform.addRow(HintLabel("subfield.row_gap"))         # the value does not explain itself (E.7)
        tables = whole(0, 200)
        tables.setSpecialValueText(_("continuous rows"))
        self._bind(tables, lambda: self._params().table_modules)
        tables.valueChanged.connect(lambda v: self._emit("params.table_modules", v))
        gform.addRow(_("Modules per table, along"), tables)
        tgap = self._bind(spin(0, 5, 0, " m", 2, 0.05), lambda: self._params().table_gap)
        tgap.valueChanged.connect(lambda v: self._emit("params.table_gap", v))
        gform.addRow(_("Between tables"), tgap)
        shade_free = self._bind(QCheckBox(_("Out of the obstacles' shadows")), lambda: self._params().shade_free)
        register(shade_free, "subfield.shade_free")       # the long tooltip it had is the help's text now
        shade_free.toggled.connect(lambda v: self._emit("params.shade_free", v))
        gform.addRow(shade_free)
        gform.addRow(HintLabel("subfield.shade_free"))
        box.addWidget(gaps)

        if not flush:
            pitch = Group(_("Row pitch"))
            help_button(pitch, "subfield.pitch")
            pform = make_form(pitch)
            mode = self._bind(combo((("sun", _("From the sun")), ("value", _("Given pitch")),
                                     ("gcr", _("Ground cover ratio"))), p.pitch_mode),
                              lambda: self._params().pitch_mode)
            mode.currentIndexChanged.connect(lambda _i: self._emit("params.pitch_mode", mode.currentData()))
            pform.addRow(pgettext("rows", "Pitch"), mode)
            if p.pitch_mode == "value":
                v = self._bind(spin(0.5, 30, 3.0, " m", 2, 0.05), lambda: self._params().pitch or 3.0)
                v.valueChanged.connect(lambda x: self._emit("params.pitch", x))
                pform.addRow(pgettext("rows", "Pitch"), v)
            elif p.pitch_mode == "gcr":
                v = self._bind(spin(0.1, 1.0, 0.5, "", 2, 0.01), lambda: self._params().gcr)
                v.valueChanged.connect(lambda x: self._emit("params.gcr", x))
                pform.addRow(_("Ratio"), v)
            box.addWidget(pitch)

        box.addWidget(self._sides_group(len(sf.ring), lambda: self._object().ring, "ring"))

        buttons = QHBoxLayout()
        if sf.manual and sf.filled:
            # the rows by hand (task 16c): laid again only by asking, the hand's changes lost (PVsyst's warning)
            fill = QPushButton(_("Lay again automatically"))
            fill.setToolTip(_("The rows by hand give way to the automatic layout; asked first, and Undo brings "
                              "them back"))
            fill.clicked.connect(lambda: self.action.emit("relayout", "subfield", self.oid))
        else:
            fill = QPushButton(_("Lay the modules") if not sf.filled else _("Lay again"))
            fill.clicked.connect(lambda: self.action.emit("fill", "subfield", self.oid))
        fill.setProperty("primary", True)       # the one button full of accent in the Model (study 17, C2)
        buttons.addWidget(fill)
        if sf.filled:
            empty = QPushButton(_("Take them out"))
            empty.setProperty("destructive", True)
            empty.clicked.connect(lambda: self.action.emit("empty", "subfield", self.oid))
            buttons.addWidget(empty)
        box.addLayout(buttons)

        state = self._note()
        state.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(self._bind(state, self._state_note))
        summary = self._bind(self._note(), self._summary)
        summary.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(summary)
        notes = self._note()
        notes.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(self._bind(notes, lambda: "<br>".join(
            mark("⚠") + " " + html.escape(_(n)) for n in (self.shown["result"].notes if self._laid() else []))))
        box.addStretch(1)

    def _state_note(self) -> str:
        state = self.shown.get("state")
        if state == "stale":
            return mark("⟳") + " " + html.escape(
                _("To lay out again: the layout is on its way, the figures below are the previous ones."))
        if state == "error":
            return mark("✘") + " " + html.escape(_("The layout failed: {why}").format(why=self.shown.get("error", "")))
        return ""

    def _laid(self) -> bool:
        return self.shown["result"] is not None and self._object().filled

    def _summary(self) -> str:
        """The modules laid, their power and the geometry of the rows, once the layout is back."""
        if not self._laid():
            return ""
        result, p = self.shown["result"], self._params()
        kw = result.count * self._project().module_of(self._object()).power_kw
        lines = [
            semibold(ngettext("<b>{n} module</b>, Po,cc {kw} kW", "<b>{n} modules</b>, Po,cc {kw} kW",
                              result.count).format(n=result.count, kw=number(kw))),
            _("azimuth {a}°, tilt {t}°").format(a=number(result.azimuth, 1, sign=True), t=number(result.tilt, 1)),
        ]
        if p.mounting not in layout.FLUSH:
            lines.append(_("row pitch {p} m, clear gap {g} m, limit angle {l}°").format(
                p=number(result.pitch), g=number(result.clearance), l=number(result.limit_angle, 1)))
        if result.groups:
            lines.append(ngettext("{n} fire-brigade group", "{n} fire-brigade groups",
                                  len(result.groups)).format(n=len(result.groups)))
        if getattr(result, "manual", False):
            # the state of the rows by hand in the Result of the layout (design 2.2, task 16c)
            rows = sum(1 for r in result.rows if r.places)
            lines.append(mark("ℹ") + " " + html.escape(ngettext(
                "Rows by hand: {n} row, kept as it is; the pitch and the rules are checked, not applied",
                "Rows by hand: {n} rows, kept as they are; the pitch and the rules are checked, not applied",
                rows).format(n=rows)))
        return "<br>".join(lines)

    # exclusion

    def show_exclusion(self, e: model.ExclusionItem) -> None:
        self.kind, self.oid = "exclusion", e.id
        self.shown = {"object": e}
        if not self._same(("exclusion", e.id, e.height is None, len(e.ring))):
            self._build_exclusion(e)
        self._refresh()

    def _build_exclusion(self, e: model.ExclusionItem) -> None:
        box = self._page(_("Exclusion"), "exclusion")
        form = make_form()
        kind = self._bind(combo(exclusion_names().items(), e.kind), lambda: self._object().kind)
        kind.currentIndexChanged.connect(lambda _i: self._emit("kind", kind.currentData()))
        form.addRow(_("Kind"), kind)
        clear = self._bind(spin(0, 10, e.clearance, " m", 2, 0.1), lambda: self._object().clearance)
        clear.valueChanged.connect(lambda v: self._emit("clearance", v))
        form.addRow(_("Extra clearance"), clear)
        height = self._bind(spin(0, 60, e.obstacle_height(), " m", 2, 0.1), lambda: self._object().obstacle_height())
        height.setToolTip(_("How high it rises above the roof (or the ground): it casts shadows on the modules"))
        height.valueChanged.connect(lambda v: self._emit("height", v))
        form.addRow(_("Height"), height)
        box.addLayout(form)
        if e.height is None:
            box.addWidget(self._note(_("Height: the default for this kind, indicative; measure it on the site.")))
        else:
            back = QPushButton(_("Use the default height of this kind"))
            back.clicked.connect(lambda: self._emit("height", None))
            box.addWidget(back)
        box.addWidget(self._note(_("Smoke vents, openings and roof plant get 1 m more by themselves where the "
                                   "fire-brigade rules apply (DCPREV 14030/2025, 3.3.5.1).")))
        box.addWidget(self._sides_group(len(e.ring), lambda: self._object().ring, "ring"))
        box.addStretch(1)
