"""Project tree presentation and commands over the shared, undoable Session.

No widget is created here. The shell connects the three navigation signals to its
properties, views and checks panels. Layouts are supplied by the session's jobs.
"""
from __future__ import annotations

import base64

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QFont

from meridiana import checks, clipboard, manual, model, squaring, symbol_shapes
from meridiana.i18n import _, number
from meridiana.fields import field_label
from meridiana.session import ProjectSession


class ProjectTreeBackend(QObject):
    changed = Signal()
    rowsAboutToChange = Signal()
    selectionChanged = Signal()
    propertiesRequested = Signal(str, str)
    frameRequested = Signal(str, str)
    checksRequested = Signal(str, str, str)
    errorOccurred = Signal(str)

    def __init__(self, session: ProjectSession, parent=None):
        super().__init__(parent)
        self.session = session
        self._rows = []
        self._items = []
        self._external_checks = False
        self._mark_widths = {}
        self.session.subscribe(self._session_changed)
        self.refresh()

    @Slot()
    def close(self):
        if self._session_changed in self.session.listeners:
            self.session.listeners.remove(self._session_changed)

    def _session_changed(self, topics):
        if topics == {"selection"}:
            self.selectionChanged.emit()
        elif any(t.startswith(("project:", "layout:")) or t in {"checks", "energy", "file", "restored"}
                 for t in topics):
            self.refresh()

    def set_checks(self, items):
        """Use the same published checks as the checks page, including plant checks."""
        self._external_checks = True
        self._items = list(items)
        self.refresh()

    @Slot(int, QFont, result=int)
    def markWidth(self, count, font):
        # Tree marks have no minimum two-digit reserve. Only the column has it. Kept by count and font: every row
        # asks again at every change of the tree (study 41: 11 ms a time, five times a Del).
        key = (count, font.key())
        width = self._mark_widths.get(key)
        if width is None:
            from meridiana.ui.status_pill import size_hint
            width = self._mark_widths[key] = size_hint(str(count), font, 24).width()
        return width

    @Slot()
    def refresh(self):
        p, session = self.session.project, self.session
        if not self._external_checks:
            self._items = checks.gather(p, session.good_results(), session.energy)
        marks = checks.tree_marks(self._items)
        rows = []

        def add(kind, oid, label, icon="", count=-1, tail="", tip="", state=""):
            mark = marks.get((kind, oid))
            symbol = symbol_shapes.LEVEL.get(mark.level, "info") if mark else "stop" if state == "error" else "info"
            sources = ["data:image/svg+xml;base64," + base64.b64encode(symbol_shapes.svg(symbol, dark)).decode("ascii")
                       for dark in (False, True)]
            error_sources = ["data:image/svg+xml;base64," + base64.b64encode(symbol_shapes.svg("stop", dark)).decode("ascii")
                             for dark in (False, True)] if state == "error" else []
            rows.append(dict(kind=kind, oid=oid, label=label, icon=icon, count=count,
                             tail=tail, tip=tip, state=state, group=kind == "group",
                             markSources=sources, errorSources=error_sources,
                             markLevel=mark.level if mark else "", markCount=mark.count if mark else 0,
                             markTip=(checks.mark_text(self._items, mark, inside=kind in ("site", "group"))
                                      + "\n" + _("A click: these checks in the panel below")) if mark else ""))

        add("site", "", p.name, "site", tip=_("Site: {name}").format(name=p.name))
        add("group", "building", _("Buildings"), count=len(p.buildings))
        for b in p.buildings:
            add("building", b.id, b.name, "building")
        add("group", "subfield", _("Sub-fields"), count=len(p.subfields))
        for sf in p.subfields:
            state, result = session.layout_state(sf), session.results.get(sf.id)
            tail = " · " + number(result.count, 0) if state == "ok" else " · …" if state == "stale" else ""
            tip = (_("To lay out again: it changed after its layout") if state == "stale" else
                   _("The layout failed: {why}").format(why=result) if state == "error" else "")
            add("subfield", sf.id, sf.name, "subfield", tail=tail, tip=tip, state=state)
        add("group", "exclusion", _("Exclusions"), count=len(p.exclusions))
        names, numbers = model.exclusion_names(), p.exclusion_numbers()
        for e in p.exclusions:
            add("exclusion", e.id, f"{names.get(e.kind, e.kind)} {numbers[e.id]}", "exclusion", tip=e.id)
        if p.props:
            add("group", "prop", _("3D objects"), count=len(p.props))
            for prop in p.props:
                add("prop", prop.id, p.prop_label(prop), "object_3d", tip=prop.id)
        self.rowsAboutToChange.emit()
        self._rows = rows
        self.changed.emit()
        self.selectionChanged.emit()

    @Property("QVariantList", notify=changed)
    def rows(self):
        return self._rows

    @Property("QVariantMap", constant=True)
    def labels(self):
        return dict(rename=_("Rename"), name=_("Name:"), cancel=_("Cancel"),
                    apply=_("Apply"), variants=_("Variants"), newVariant=_("New variant"),
                    deleteVariant=_("Delete a variant"), renameVariant=_("Rename the variant"),
                    relayout=_("Lay again automatically"),
                    relayoutQuestion=_("The rows by hand give way to the automatic layout, and the modules taken "
                                       "out by hand come back. Undo brings them back. Go on?"))

    @Property(str, notify=selectionChanged)
    def selectionKind(self):
        return "subfield" if self.session.selection[0] == "row" else self.session.selection[0]

    @Property(str, notify=selectionChanged)
    def selectionId(self):
        return self.session.selection[1].partition("/")[0] if self.session.selection[0] == "row" else self.session.selection[1]

    @Property("QVariantList", notify=selectionChanged)
    def selectedRows(self):
        """The rows lit, as «kind/id»: more than one when several were chosen with Ctrl or Shift (R439)."""
        kind, many = self.selectionKind, self.session.selected_many()
        return [f"{kind}/{oid}" for oid in many] or ([f"{kind}/{self.selectionId}"] if kind != "site" else [])

    @Slot(str, "QVariantList")
    def selectMany(self, kind, oids):
        known = [oid for oid in oids if self._object(kind, oid) is not None]
        if known:
            self.session.select_many(kind, known)

    @Property("QVariantList", notify=changed)
    def variants(self):
        return [dict(id=v["id"], name=v["name"], active=v["id"] == self.session.project.variant)
                for v in self.session.project.variants]

    def _object(self, kind, oid):
        field = dict(building="buildings", subfield="subfields", exclusion="exclusions", prop="props").get(kind)
        return next((x for x in getattr(self.session.project, field, []) if x.id == oid), None) if field else None

    @Slot(str, str)
    def select(self, kind, oid):
        if kind == "site" or self._object(kind, oid) is not None:
            self.session.select(kind, oid)

    @Slot(str, str)
    def activateMark(self, kind, oid):
        row = next((r for r in self._rows if (r["kind"], r["oid"]) == (kind, oid)), None)
        if row and row["markCount"]:
            self.select(kind, oid)
            self.checksRequested.emit(kind, oid, row["label"] + row["tail"])

    @Slot(str, str, str, result=bool)
    def rename(self, kind, oid, name):
        thing, name = self._object(kind, oid), name.strip()
        if kind not in ("building", "subfield") or thing is None or not name or name == thing.name:
            return False
        self.session.edit(_("Change {what}").format(what=field_label("name", kind)), lambda p: setattr(thing, "name", name))
        return True

    @Slot(str, str, result="QVariantList")
    def actions(self, kind, oid):
        if kind != "site" and self._object(kind, oid) is None:
            return []
        if kind == self.session.selection[0] and oid in self.session.selected_many():
            return [dict(id=key, text=text, separator=not key) for key, text in (
                ("properties", _("Properties")), ("", ""), ("delete", _("Delete")))]
        out = [("properties", _("Properties")), ("frame", _("Frame it"))]
        sf = self._object(kind, oid) if kind == "subfield" else None
        if sf is not None:
            out.append(("relayout" if sf.manual else "fill", _("Lay again automatically") if sf.manual else
                        _("Lay again") if sf.filled else _("Lay the modules")))
            if sf.filled:
                out += [("explode", _("Explode the rows")), ("empty", _("Take the modules out"))]
        if kind == "building":
            out.append(("pitches", _("A sub-field on each pitch")))
        if kind != "site":
            out.append(("", ""))
            if kind in ("building", "subfield"):
                out.append(("rename", _("Rename…")))
            out.append(("duplicate", _("Duplicate")))
            if kind != "prop":
                out.append(("square", _("Square the corners")))
            out.extend([("", ""), ("delete", _("Delete"))])
        return [dict(id=key, text=text, separator=not key) for key, text in out]

    @Slot(str, str, str, result=bool)
    def trigger(self, action, kind, oid):
        if not action or action not in {a["id"] for a in self.actions(kind, oid)}:
            return False
        many = self.session.selected_many() if kind == self.session.selection[0] else []
        if oid in many:                     # R439: on what is selected together, not on one of them
            if action == "delete":
                self.session.edit(_("Delete objects"), lambda p: [clipboard.drop(p, kind, x) for x in many])
                self.select("site", "")
            else:
                self.propertiesRequested.emit(kind, oid)
            return True
        self.select(kind, oid)
        try:
            self._trigger(action, kind, oid)
        except (ValueError, KeyError) as error:
            self.errorOccurred.emit(_("Not changed: {why}").format(why=error))
            return False
        return True

    def _trigger(self, action, kind, oid):
        session, p = self.session, self.session.project
        thing = self._object(kind, oid)
        if action == "properties":
            self.propertiesRequested.emit(kind, oid)
        elif action == "frame":
            self.frameRequested.emit(kind, oid)
        elif action == "duplicate":
            made = []
            session.edit(_("Duplicate"), lambda p: made.append(p.duplicate(kind, oid)))
            self.select(kind, made[0])
        elif action == "delete":
            def drop(p):
                field = dict(building="buildings", subfield="subfields", exclusion="exclusions", prop="props")[kind]
                setattr(p, field, [x for x in getattr(p, field) if x.id != oid])
                if kind == "building":
                    for field in ("subfields", "exclusions", "props"):
                        setattr(p, field, [x for x in getattr(p, field) if x.building != oid])
            titles = dict(building=_("Delete a building"), subfield=_("Delete a sub-field"),
                          exclusion=_("Delete an exclusion"), prop=_("Delete a 3D object"))
            session.edit(titles[kind], drop)
            self.select("site", "")
        elif action in ("fill", "empty"):
            def fill(p):
                thing.filled = action == "fill"
                if thing.filled and not thing.manual:
                    thing.removed = []
            session.edit(_("Lay the modules") if action == "fill" else _("Take the modules out"), fill)
        elif action == "relayout":
            session.edit(_("Lay again automatically"), manual.relayout(p, oid))
        elif action == "explode":
            session.edit(_("Explode the rows"), manual.explode(p, oid, None, session.results.get(oid)))
        elif action == "square":
            attr = "footprint" if kind == "building" else "ring"
            ring, why = squaring.square([tuple(q) for q in getattr(thing, attr)])
            if why:
                self.errorOccurred.emit(_("It is square already.") if why == "square_enough" else
                                        _("No corner is near a right angle: nothing to square."))
                return
            session.edit(_("Square the corners"), lambda p: setattr(thing, attr, [[round(x, 4), round(y, 4)] for x, y in ring]))
        elif action == "pitches":
            from shapely.geometry import Polygon
            pitches = [(i, pitch) for i, pitch in enumerate(thing.pitches())
                       if len(pitch.ring) >= 3 and Polygon(pitch.ring).area >= .5]
            for index, pitch in pitches:
                sid = p.new_id("s")
                # R523: with the project's defaults, as the sub-fields drawn on the plan
                sf = p.new_subfield(sid, _("Sub-field {n}").format(n=len(p.subfields) + 1),
                                    [[round(x, 4), round(y, 4)] for x, y in pitch.ring], oid, thing.pitch_ref(index))
                session.edit(_("Draw a sub-field"), lambda p, sf=sf: p.add_subfield(sf))
                self.select("subfield", sid)

    @Slot(str)
    def switchVariant(self, vid):
        variant = next((v for v in self.variants if v["id"] == vid), None)
        if variant and not variant["active"]:
            self.session.edit(_("Work on the variant {name}").format(name=variant["name"]), lambda p: p.switch_variant(vid))

    @Slot(str)
    def newVariant(self, name):
        if name.strip():
            self.session.edit(_("New variant {name}").format(name=name.strip()), lambda p: p.add_variant(name.strip()))

    @Slot(str, str)
    def renameVariant(self, vid, name):
        variant = next((v for v in self.session.project.variants if v["id"] == vid), None)
        if variant and name.strip():
            self.session.edit(_("Rename the variant"), lambda p: variant.update(name=name.strip()))

    @Slot(str)
    def deleteVariant(self, vid):
        variant = next((v for v in self.variants if v["id"] == vid), None)
        if variant and not variant["active"]:
            self.session.edit(_("Delete the variant {name}").format(name=variant["name"]), lambda p: p.remove_variant(vid))

    @Slot()
    def undo(self):
        self.session.undo.undo()

    @Slot()
    def redo(self):
        self.session.undo.redo()
