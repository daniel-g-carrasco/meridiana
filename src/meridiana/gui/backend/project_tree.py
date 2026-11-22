"""Project tree presentation and commands over the shared, undoable Session.

No widget is created here. The shell connects the three navigation signals to its
properties, views and checks panels. Layouts are supplied by the session's jobs.

R575 (proposal of the IFC layers, 6.5): the sub-fields and the exclusions under their building, the parts of a
building under it, groups that close and are remembered for each project (in the user's settings, FoldMemory), the
sub-fields and kWp of each building, names in their natural order. The rows of a closed group are not made at all:
a project of 2 000 sub-fields gives the rows of its buildings.

R604: the bodies of one imported model are ONE node of the tree (`imported.models`, the only place that groups them):
its bodies worth a row inside it, the others in one row «Other bodies»; the node chosen is the whole import (all its
bodies selected together, moved, framed and deleted as one). The planes the import made are shown by their short name
(`imported.namer`). The tree carries no marks of the checks (R604): the Checks panel has them.
"""
from __future__ import annotations

import re

from PySide6.QtCore import QObject, Property, Signal, Slot

from meridiana.core.model import clipboard, imported, model
from meridiana.core.layout import manual
from meridiana.core.geometry import squaring
from meridiana.app.interface import layout_commands
from meridiana.i18n import _, ngettext, number
from meridiana.app.interface.fields import field_label
from meridiana.app.session import ProjectSession


FOLDS_KEPT = 100                # the projects whose groups the settings remember, the last ones opened


def natural_key(text: str) -> list:
    """«Lastra 2» before «Lastra 10»: the runs of digits compared as numbers, the rest without case."""
    return [(0, int(t), "") if t.isdigit() else (1, 0, t.casefold())
            for t in re.split(r"(\d+)", text or "", flags=re.ASCII) if t]


def _main_of(b, by_id) -> str:
    """The building a body is a part of (Building.part_of, R440), when that one is a building on its own."""
    main = by_id.get(b.part_of) if b.part_of and b.part_of != b.id else None
    return main.id if main is not None and main.part_of not in by_id else ""


def footprints_bounds(project, ids) -> list | None:
    """The bounds of the footprints of the buildings `ids` as the plan frames them (plan.targetBounds): [min x, -max y,
    width, height]; None when none of them is left."""
    wanted = set(ids)
    points = [q for b in project.buildings if b.id in wanted for q in b.footprint]
    if not points:
        return None
    xs, ys = [float(q[0]) for q in points], [float(q[1]) for q in points]
    return [min(xs), -max(ys), max(xs) - min(xs), max(ys) - min(ys)]


class FoldMemory:
    """Which groups of the tree the designer opened or closed, for each project (its bim_id): in the user's settings
    (Config.tree_folds) when they are given, else for this session only. Not in the project, not undone (proposal of
    the IFC layers, 6.3). Only the groups that differ from how they start are kept."""

    def __init__(self, cfg=None, path=None):
        self.cfg, self.path = cfg, path
        self._own: dict = {}

    def _table(self) -> dict:
        return self.cfg.tree_folds if self.cfg is not None else self._own

    def get(self, project_key: str) -> set:
        return set(self._table().get(project_key) or [])

    def put(self, project_key: str, toggled: set) -> None:
        table = self._table()
        table.pop(project_key, None)
        if toggled:
            table[project_key] = sorted(toggled)
        while len(table) > FOLDS_KEPT:
            table.pop(next(iter(table)))
        if self.cfg is not None and self.path is not None:
            from meridiana.app.platform import config, log
            try:
                config.save(self.cfg, self.path)
            except OSError as error:
                log.complain("project tree groups", error)


class ProjectTreeBackend(QObject):
    changed = Signal()
    rowsAboutToChange = Signal()
    selectionChanged = Signal()
    propertiesRequested = Signal(str, str)
    frameRequested = Signal(str, str)
    errorOccurred = Signal(str)

    def __init__(self, session: ProjectSession, parent=None, folds: FoldMemory | None = None):
        super().__init__(parent)
        self.session = session
        self.folds = folds if folds is not None else FoldMemory()
        self._toggled: tuple[str, set] = ("", set())     # (project's bim_id, its groups not as they start)
        self._rows = []
        self._models: dict = {}                         # key -> imported.Model, as at the last refresh
        self._model_of: dict = {}                       # id of a top body of a model -> its Model
        self.session.subscribe(self._session_changed)
        self.refresh()

    @Slot()
    def close(self):
        if self._session_changed in self.session.listeners:
            self.session.listeners.remove(self._session_changed)

    def _session_changed(self, topics):
        if topics == {"selection"}:
            if not self._reveal_selection():
                self.selectionChanged.emit()
        elif any(t.startswith(("project:", "layout:")) or t in {"file", "restored"}
                 for t in topics):
            self.refresh()

    # the groups: which are open, the designer's choice kept for each project

    def _toggled_now(self) -> set:
        key = self.session.project.bim_id
        if self._toggled[0] != key:
            self._toggled = (key, self.folds.get(key))
        return self._toggled[1]

    def is_open(self, fold: str) -> bool:
        """The groups of the tree start open, the buildings and their exclusions closed."""
        return fold.startswith("group:") != (fold in self._toggled_now())

    @Slot(str)
    def toggle(self, fold):
        self.setOpen(fold, not self.is_open(fold))

    @Slot(str, bool)
    def setOpen(self, fold, wanted):
        self._open_all({fold: bool(wanted)})

    def _open_all(self, wanted: dict) -> bool:
        toggled = self._toggled_now()
        changed = False
        for fold, state in wanted.items():
            if fold and self.is_open(fold) != state:
                toggled ^= {fold}
                changed = True
        if changed:
            self.folds.put(self.session.project.bim_id, toggled)
            self.refresh()
        return changed

    def _ancestors(self, kind: str, oid: str) -> list[str]:
        """The groups an object of the tree sits in, from the outside in."""
        p = self.session.project
        by_id = {b.id: b for b in p.buildings}
        if kind == "row":
            kind, oid = "subfield", oid.partition("/")[0]

        def first_level(bid):
            """The groups of a body listed under «Buildings»: its imported model, the model's other bodies (R604)."""
            m = self._model_of.get(bid)
            if m is None:
                return ["group:building"]
            return ["group:building", f"model:{m.key}"] + ([f"others:{m.key}"] if bid in m.others else [])

        def of_building(bid):
            if bid not in by_id:
                return ["group:free"]
            main = _main_of(by_id[bid], by_id)
            return first_level(main or bid) + ([f"building:{main}"] if main else []) + [f"building:{bid}"]
        if kind == "building" and oid in by_id:
            main = _main_of(by_id[oid], by_id)
            return first_level(main or oid) + ([f"building:{main}"] if main else [])
        if kind == "subfield":
            sf = next((x for x in p.subfields if x.id == oid), None)
            return of_building(sf.building) if sf is not None else []
        if kind == "exclusion":
            e = next((x for x in p.exclusions if x.id == oid), None)
            if e is None:
                return []
            host = e.building if e.building in by_id else ""
            return (of_building(host) if host else ["group:free"]) + [f"exclusions:{host}"]
        if kind == "prop":
            return ["group:prop"]
        return []

    @Slot(str, str, result=bool)
    def reveal(self, kind, oid):
        """The groups holding the object opened (a selection made on the plan or in the 3D view): whether one was."""
        return self._open_all({fold: True for fold in self._ancestors(kind, oid)})

    def _reveal_selection(self) -> bool:
        if self._whole_model() is not None:
            # the node chosen is the whole import: its row in view, the node itself not unfolded (R604)
            return self._open_all({"group:building": True})
        kind, oid = self.session.selection
        wanted = {fold: True for fold in self._ancestors(kind, oid)}
        for other in self.session.selected_many():
            wanted.update({fold: True for fold in self._ancestors(kind, other)})
        return self._open_all(wanted)

    def _whole_model(self):
        """The imported model whose bodies are exactly what is selected, None for any other selection."""
        if self.session.selection[0] != "building" or not self._models:
            return None
        many = self.session.selected_many()
        if len(many) < 2:
            return None
        body = self.session.project.building(many[-1])
        m = self._models.get(body.group) if body is not None else None
        return m if m is not None and set(many) == set(m.bodies) else None

    @Slot()
    def refresh(self):
        p, session = self.session.project, self.session
        rows = []

        def add(kind, oid, label, icon="", count=-1, tail="", tip="", state="", depth=0, fold="", children=0,
                pick=True, join=True, tint="", value=""):
            # join: whether Ctrl and Shift add the row to the others chosen (the site and a model are chosen alone);
            # tint: the kind whose colour the icon takes (Theme.colors.kind); value (R665): what a building or a
            # sub-field measures, alone (the tail is it after the name): never cut, the name gives way to it
            rows.append(dict(kind=kind, oid=oid, label=label, icon=icon, count=count, value=value,
                             tail=" · " + value if value else tail, tip=tip, state=state, group=kind == "group",
                             depth=depth, fold=fold, open=bool(fold) and self.is_open(fold), children=children,
                             pick=pick, join=pick and join, tint=tint or kind))

        add("site", "", p.name, "site", tip=_("Site: {name}").format(name=p.name), join=False)
        models = imported.models(p)
        self._models = {m.key: m for m in models}
        self._model_of = {bid: m for m in models for bid in m.shown + m.others}
        names_now = []                          # one namer for this refresh, made when a sub-field row needs it

        def namer():
            if not names_now:
                names_now.append(imported.namer(p))
            return names_now[0]

        by_id = {b.id: b for b in p.buildings}
        parts, tops = {}, []
        for b in p.buildings:
            main = _main_of(b, by_id)
            if main:
                parts.setdefault(main, []).append(b)
            else:
                tops.append(b)
        fields_of, kept_out = {}, {}
        for sf in p.subfields:
            fields_of.setdefault(sf.building if sf.building in by_id else None, []).append(sf)
        for e in p.exclusions:
            kept_out.setdefault(e.building if e.building in by_id else None, []).append(e)
        powers = {}

        def laid(sf):
            """(modules, kWp) of a sub-field's layout in hand."""
            result = session.results.get(sf.id)
            n = getattr(result, "count", 0) if sf.filled and not isinstance(result, Exception) else 0
            if not n:
                return 0, 0.0
            if sf.module not in powers:
                powers[sf.module] = p.module_of(sf).power_kw
            return n, n * powers[sf.module]

        def summary(b):
            """The sub-fields, modules and kWp of a building and of all it holds."""
            fields, modules, kw = 0, 0, 0.0
            for part in parts.get(b.id, []):
                f, m, k = summary(part)
                fields, modules, kw = fields + f, modules + m, kw + k
            for sf in fields_of.get(b.id, []):
                n, k = laid(sf)
                fields, modules, kw = fields + 1, modules + n, kw + k
            return fields, modules, kw

        def in_words(fields, kw):
            words = (ngettext("{n} sub-field", "{n} sub-fields", fields).format(n=fields) if fields
                     else _("no sub-fields"))
            if kw > 0:
                words += " · " + _("{kwp} kWp").format(kwp=number(kw, 1))
            return " · " + words

        names, numbers = model.exclusion_names(profile_id=p.regulatory_profile), p.exclusion_numbers()

        def kwp(kw):
            return _("{kwp} kWp").format(kwp=number(kw, 1))

        def subfield_row(sf, depth, short):
            state, result = session.layout_state(sf), session.results.get(sf.id)
            # R665 (Daniel 16/11/2026: «per i sottocampi mettiamoci anche la potenza»): its modules and their kWp
            value = ""
            if state == "ok":
                _n, kw = laid(sf)
                value = number(result.count, 0) + (" · " + kwp(kw) if kw > 0 else "")
            tail = " · …" if state == "stale" else ""
            tip = (_("To lay out again: it changed after its layout") if state == "stale" else
                   _("The layout failed: {why}").format(why=result) if state == "error" else "")
            source = namer().source(sf)             # R604: the file and the elements a plane of the import came from
            add("subfield", sf.id, namer().subfield(sf, short), "subfield", tail=tail, value=value,
                tip="\n".join(x for x in (tip, source) if x), state=state, depth=depth)

        def subfield_rows(those, depth, short):
            labelled = sorted(((namer().subfield(sf, short), sf) for sf in those), key=lambda ls: natural_key(ls[0]))
            for _label, sf in labelled:
                subfield_row(sf, depth, short)

        def exclusions_row(host, those, depth):
            fold = f"exclusions:{host or ''}"
            add("fold", fold, _("Exclusions"), count=len(those), depth=depth, fold=fold, children=len(those),
                pick=False)
            if self.is_open(fold):
                labelled = sorted(((f"{names.get(e.kind, e.kind)} {numbers[e.id]}", e) for e in those),
                                  key=lambda le: natural_key(le[0]))
                for label, e in labelled:
                    add("exclusion", e.id, label, "exclusion", tip=e.id, depth=depth + 1)

        def building_row(b, depth, about):
            fields, _modules, kw = about
            mine_parts = parts.get(b.id, [])
            mine_fields = fields_of.get(b.id, [])
            mine_out = kept_out.get(b.id, [])
            children = len(mine_parts) + len(mine_fields) + (1 if mine_out else 0)
            fold = f"building:{b.id}" if children else ""
            opened = bool(fold) and self.is_open(fold)
            # R665 (Daniel 16/11/2026: «si può eliminare l'indicazione 1-subfields, no subfields? e mantenere solo la
            # potenza?»): its kWp alone, nothing without modules
            add("building", b.id, b.name, "building", value=kwp(kw) if kw > 0 else "", depth=depth, fold=fold,
                children=children)
            if opened:
                for part in sorted(mine_parts, key=lambda x: natural_key(x.name)):
                    building_row(part, depth + 1, summary(part))
                subfield_rows(mine_fields, depth + 1, True)
                if mine_out:
                    exclusions_row(b.id, mine_out, depth + 1)

        def bodies_rows(ids, depth):
            for b in sorted((by_id[i] for i in ids), key=lambda x: natural_key(x.name)):
                building_row(b, depth, abouts[b.id])

        def model_row(m):
            """R604: one imported model, one row: its bodies inside it, the small ones gathered in «Other bodies»."""
            mine = m.shown + m.others
            fields = sum(abouts[i][0] for i in mine)
            modules = sum(abouts[i][1] for i in mine)
            kw = sum(abouts[i][2] for i in mine)
            fold = f"model:{m.key}"
            tip = _("Imported model: {bodies}, {modules}").format(
                bodies=ngettext("{n} body", "{n} bodies", len(m.bodies)).format(n=len(m.bodies)),
                modules=ngettext("{n} module", "{n} modules", modules).format(n=number(modules, 0)))
            if m.file:
                tip += "\n" + m.file                # the whole path at the bottom of the tip, never in the label
            add("model", m.key, m.name, "import_ifc", tail=in_words(fields, kw), tip=tip, depth=1, fold=fold,
                children=len(m.shown) + (1 if m.others else 0), join=False, tint="building")
            if not self.is_open(fold):
                return
            bodies_rows(m.shown, 2)
            if m.others:
                others = f"others:{m.key}"
                add("fold", others, _("Other bodies"), count=len(m.others), depth=2, fold=others,
                    children=len(m.others), pick=False)
                if self.is_open(others):
                    bodies_rows(m.others, 3)

        abouts = {b.id: summary(b) for b in tops}
        alone = [("building", b.name, b) for b in tops if b.id not in self._model_of]
        entries = sorted(alone + [("model", m.name, m) for m in models], key=lambda e: natural_key(e[1]))
        total = sum(a[2] for a in abouts.values())
        fold = "group:building"
        add("group", "building", _("Buildings"), count=len(entries), fold=fold if entries else "",
            children=len(entries), tail=" · " + _("{kwp} kWp").format(kwp=number(total, 1)) if total > 0 else "",
            pick=False)
        if entries and self.is_open(fold):
            for kind, _name, thing in entries:
                if kind == "model":
                    model_row(thing)
                else:
                    building_row(thing, 1, abouts[thing.id])
        free_fields = fields_of.get(None, [])
        free_out = kept_out.get(None, [])
        if free_fields or free_out:
            fold = "group:free"
            add("group", "free", _("On the ground"), count=len(free_fields) + len(free_out), fold=fold,
                children=len(free_fields) + (1 if free_out else 0), pick=False)
            if self.is_open(fold):
                subfield_rows(free_fields, 1, False)
                if free_out:
                    exclusions_row(None, free_out, 1)
        if p.props:
            fold = "group:prop"
            add("group", "prop", _("3D objects"), count=len(p.props), fold=fold, children=len(p.props), pick=False)
            if self.is_open(fold):
                labelled = sorted(((p.prop_label(x), x) for x in p.props), key=lambda lx: natural_key(lx[0]))
                for label, prop in labelled:
                    add("prop", prop.id, label, "object_3d", tip=prop.id, depth=1)
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
                    empty=_("Nothing in the project yet"),
                    relayout=_("Lay again automatically"),
                    relayoutQuestion=_("The rows by hand give way to the automatic layout, and the modules taken "
                                       "out by hand come back. Undo brings them back. Go on?"))

    @Property(str, notify=selectionChanged)
    def selectionKind(self):
        if self._whole_model() is not None:
            return "model"                  # R604: the keyboard goes on from the model's row
        return "subfield" if self.session.selection[0] == "row" else self.session.selection[0]

    @Property(str, notify=selectionChanged)
    def selectionId(self):
        whole = self._whole_model()
        if whole is not None:
            return whole.key
        return self.session.selection[1].partition("/")[0] if self.session.selection[0] == "row" else self.session.selection[1]

    @Property("QVariantList", notify=selectionChanged)
    def selectedRows(self):
        """The rows lit, as «kind/id»: more than one when several were chosen with Ctrl or Shift (R439); a model's
        row with its bodies' when they are all chosen (R604)."""
        kind, oid = self.session.selection
        if kind == "row":
            kind, oid = "subfield", oid.partition("/")[0]
        many = self.session.selected_many()
        lit = [f"{kind}/{x}" for x in many] or ([f"{kind}/{oid}"] if kind != "site" else [])
        whole = self._whole_model()
        return [f"model/{whole.key}"] + lit if whole is not None else lit

    @Slot(str, "QVariantList")
    def selectMany(self, kind, oids):
        known = [oid for oid in oids if self._object(kind, oid) is not None]
        if kind == "model":
            if known:
                self.select(kind, known[-1])            # a model is chosen alone (R604)
        elif known:
            self.session.select_many(kind, known)

    @Property("QVariantList", notify=changed)
    def variants(self):
        return [dict(id=v["id"], name=v["name"], active=v["id"] == self.session.project.variant)
                for v in self.session.project.variants]

    def _object(self, kind, oid):
        if kind == "model":
            return next((m for m in imported.models(self.session.project) if m.key == oid), None)
        field = dict(building="buildings", subfield="subfields", exclusion="exclusions", prop="props").get(kind)
        return next((x for x in getattr(self.session.project, field, []) if x.id == oid), None) if field else None

    def _main_body(self, m) -> str:
        """The body a model's selection follows: the one the import anchored the model on, else its first shown."""
        ref = (self.session.project.resources or {}).get("ifc_reference")
        anchor = ((ref or {}).get("anchor") or {}).get("building") if isinstance(ref, dict) else None
        return anchor if anchor in m.bodies else m.shown[0]

    def model_bounds(self, key) -> list | None:
        """The bounds of all the bodies of a model as the plan frames them, None when it is not there."""
        m = self._object("model", key)
        return footprints_bounds(self.session.project, m.bodies) if m is not None else None

    @Slot(str, str)
    def select(self, kind, oid):
        if kind == "model":
            m = self._object(kind, oid)
            if m is not None:
                main = self._main_body(m)
                self.session.select_many("building", [i for i in m.bodies if i != main] + [main])
            return
        if kind == "site" or self._object(kind, oid) is not None:
            self.session.select(kind, oid)

    @Slot(str, str, str, result=bool)
    def rename(self, kind, oid, name):
        thing, name = self._object(kind, oid), name.strip()
        if kind not in ("building", "subfield", "model") or thing is None or not name or name == thing.name:
            return False
        if kind == "model":                 # format 33: the name of the import, saved in the project (R604)
            self.session.edit(_("Rename the imported model"), imported.renamed(oid, name))
            return True
        self.session.edit(_("Change {what}").format(what=field_label("name", kind)), lambda p: setattr(thing, "name", name))
        return True

    @Slot(str, str, result="QVariantList")
    def actions(self, kind, oid):
        if kind != "site" and self._object(kind, oid) is None:
            return []
        if kind == "model":                 # renamed as a building is (R604; its name in the project since format 33)
            return [dict(id=key, text=text, separator=not key) for key, text in (
                ("properties", _("Properties")), ("frame", _("Frame it")), ("", ""), ("rename", _("Rename…")),
                ("", ""), ("delete", _("Delete")))]
        if kind == self.session.selection[0] and oid in self.session.selected_many():
            return [dict(id=key, text=text, separator=not key) for key, text in (
                ("properties", _("Properties")), ("", ""), ("delete", _("Delete")))]
        out = [("properties", _("Properties")), ("frame", _("Frame it"))]
        sf = self._object(kind, oid) if kind == "subfield" else None
        # R564: the same entries as the bar's, the plan's and the 3D view's (layout_commands.entries)
        layout = {e["action"]: e for e in layout_commands.entries(sf)}
        out += [(e["action"], e["text"]) for e in layout.values()]
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
        return [dict(id=key, text=text, separator=not key, enabled=layout.get(key, {}).get("enabled", bool(key)),
                     note=layout.get(key, {}).get("note", "")) for key, text in out]

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
        if kind == "model" and action == "delete":
            # the whole import with what stands on its bodies, one undo step (R604); its reference stays
            session.edit(_("Delete an imported model"),
                         lambda p: [clipboard.drop(p, "building", bid) for bid in thing.bodies])
            self.select("site", "")
        elif action == "properties":
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
        elif action == "fill" and not layout_commands.fill_state(thing)[0]:
            self.errorOccurred.emit(layout_commands.fill_state(thing)[2])
        elif action in ("fill", "empty"):
            # R564: one change and one name for each, as the plan's, the 3D view's, the panel's and the bar's
            session.edit(layout_commands.text(action), manual.fill(p, oid, action == "fill"))
        elif action == "relayout":
            session.edit(layout_commands.text(action), manual.relayout(p, oid))
        elif action == "explode":
            session.edit(layout_commands.text(action), manual.explode(p, oid, None, session.results.get(oid)))
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
