"""Checks presentation and reversible fixes, with no Widgets dependency (R125-130, R335)."""
from __future__ import annotations

import base64
import copy
from dataclasses import asdict

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from meridiana import checks, manual, model, move, rules, symbol_shapes
from meridiana.energy import faces, plant, system
from meridiana.i18n import _
from meridiana.session import set_path


def object_names(project):
    names = {("site", ""): _("Site: {name}").format(name=project.name)}
    for kind, objects in (("building", project.buildings), ("subfield", project.subfields)):
        names.update({(kind, obj.id): obj.name for obj in objects})
    kinds, numbers = model.exclusion_names(), project.exclusion_numbers()
    names.update({("exclusion", obj.id): f"{kinds.get(obj.kind, obj.kind)} {numbers[obj.id]}"
                  for obj in project.exclusions})
    return names


def gather_session(project, results, energy, plant_state=None):
    """The same inputs as MainWindow._show_checks, including the live string checks."""
    arrays = system.arrays_of(project, {k: v for k, v in results.items() if not isinstance(v, Exception)})
    inverter = system.combined(system.inverters_of(project, sum(a.p_stc for a in arrays))) if arrays else None
    items = checks.gather(project, results, energy, inverter, bool(system.inverter_entries(project.energy)))
    if plant_state is None:
        sim = (energy or {}).get("sim")
        t_cell = max(a["t_cell_max"] for a in sim.arrays) if sim is not None else None
        p_dc = sim.hourly.p_dc.to_numpy() if sim is not None else None
        plant_state = plant.build(project, {k: v for k, v in results.items() if not isinstance(v, Exception)},
                                  t_cell_max_year=t_cell, p_dc_hourly=p_dc, exposure=faces.year_of(sim))
    items += checks.plant_items(plant_state)
    items.sort(key=lambda item: checks.LEVELS.index(item.level))
    return items, checks.defaults_in_use(energy), rules.notes_text(rules.facts(project, results, energy, inverter))


class _Signals(QObject):
    finished = Signal(int, object, str)


class _Gather(QRunnable):
    def __init__(self, serial, project, results, energy, state):
        super().__init__()
        self.serial, self.arguments = serial, (project, results, energy, state)
        self.signals = _Signals()

    def run(self):
        try:
            result, error = gather_session(*self.arguments), ""
        except Exception as exc:
            result, error = None, str(exc)
        self.signals.finished.emit(self.serial, result, error)


class ChecksBackend(QObject):
    changed = Signal()
    viewChanged = Signal(str)
    focusRequested = Signal("QVariantList")
    computeRequested = Signal()
    commandRequested = Signal(str)
    askRequested = Signal(object)
    errorOccurred = Signal(str)
    scrollRequested = Signal(int)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.items, self.extras, self.names = [], [], {}
        self._view, self._phase, self._phase_only = "level", "model", False
        self._levels, self._opened, self._closed = set(), set(), {}
        self._subset, self._related = None, tuple(session.selection)
        self._current, self._rows = -1, []
        self._columns = dict(sources=[], fix=False, place=False)
        self._message, self._notes, self._error = "", "", ""
        self._preview, self._preview_step, self._waiting = {}, None, None
        self._serial, self._jobs, self._disposed = 0, {}, False
        self._plant_state = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._gather)
        self.session.subscribe(self._session_changed)
        self.session.undo.listeners.append(self._undo_moved)
        self.refresh()

    @Property("QVariantList", notify=changed)
    def rows(self):
        return self._rows

    @Property('QVariantMap', notify=changed)
    def columns(self):
        return self._columns

    @Property("QVariantMap", notify=changed)
    def counts(self):
        return checks.counts(self.items)

    @Property("QVariantList", notify=changed)
    def marks(self):
        return [{"kind": key[0], "id": key[1], "level": mark.level, "count": len(mark.items),
                 "items": list(mark.items), "tip": checks.mark_text(self.items, mark)}
                for key, mark in checks.tree_marks(self.items).items()]

    @Property("QVariantList", notify=changed)
    def views(self):
        return [{"key": key, "text": text} for key, text in zip(checks.BY,
                (_("By level"), _("By object"), _("By area"), _("Ready for delivery")), strict=True)]

    @Property("QVariantMap", constant=True)
    def labels(self):
        return {"phase": _("This phase"), "object": _("This object"), "fix": _("Fix…"),
                "viewsTip": _("How the checks are grouped: by level, by object, by area, or what to look at before delivering"),
                "phaseTip": _("Only the checks acted on in the phase shown, and those of every phase"),
                "objectTip": _("Only the checks of the object selected in the views or in the tree"),
                "copyNotesTip": _("Copy the notes for the report") + "\n" + _("The paragraphs of the rules that apply, with their sources, to paste into the technical report"),
                "show": _("Show where it is"), "copy": _("Copy the text"),
                "copyNotes": _("Copy the notes for the report"), "ask": _("Ask {name}").format(name="Meridio"),
                "levels": checks.level_names()}

    @Property(str, notify=changed)
    def emptyMessage(self):
        return _("No checks match this filter.") if self.items else _("Nothing computed yet.")

    @Property("QVariantMap", constant=True)
    def symbols(self):
        out = {}
        for level in checks.LEVELS:
            name = symbol_shapes.LEVEL[level]
            out[level] = {"dark" if dark else "light": "data:image/svg+xml;base64," +
                          base64.b64encode(symbol_shapes.svg(name, dark)).decode("ascii") for dark in (False, True)}
            out[level]["tone"] = symbol_shapes.colour(name, False)
            out[level]["toneDark"] = symbol_shapes.colour(name, True)
        return out

    @Property(str, notify=changed)
    def view(self):
        return self._view

    @Property("QVariantList", notify=changed)
    def levels(self):
        return [lv for lv in checks.LEVELS if lv in self._levels]

    @Property(bool, notify=changed)
    def phaseOnly(self):
        return self._phase_only

    @Property(bool, notify=changed)
    def objectOnly(self):
        return self._subset is not None

    @Property(str, notify=changed)
    def summary(self):
        if self._message:
            return self._message
        words = [_('Only this phase.')] if self._phase_only else []
        if self._subset is not None:
            mark = checks.tree_marks(self.items, checks.LEVELS).get(self._subset)
            words.append(_("Only the checks of {name}: {n}.").format(
                name=self.names.get(self._subset, self._subset[1]), n=len(mark.items) if mark else 0))
        return " ".join(words)

    @Property("QVariantMap", notify=changed)
    def preview(self):
        return self._preview

    @Property(int, notify=changed)
    def currentIndex(self):
        return self._current

    @Property(bool, notify=changed)
    def busy(self):
        return self._timer.isActive() or bool(self._jobs)

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Property(str, notify=changed)
    def title(self):
        n = self.counts["fail"] + self.counts["warn"]
        return f'{_("Checks")} ({n})' if n else _("Checks")

    def _session_changed(self, topics):
        if "selection" in topics:
            self.showRelated(*self.session.selection)
        if topics & {"file", "checks", "energy"} or any(topic.startswith("layout:") for topic in topics):
            self._plant_state = None
            self.refresh()

    @Slot()
    def refresh(self):
        if not self._disposed:
            self._serial += 1  # invalidate a result before the next job starts
            self._timer.start(0)
            self.changed.emit()

    def set_plant_state(self, state):
        """Optionally use the shell's live plant, including its year conditions."""
        self._plant_state = state
        self.refresh()

    def _gather(self):
        job = _Gather(self._serial, copy.deepcopy(self.session.project), dict(self.session.results),
                      dict(self.session.energy), self._plant_state)
        self._jobs[self._serial] = job
        job.signals.finished.connect(self._gathered)
        QThreadPool.globalInstance().start(job)

    @Slot(int, object, str)
    def _gathered(self, serial, result, error):
        self._jobs.pop(serial, None)
        if self._disposed:
            return
        if serial == self._serial:
            self._error = error
            if error:
                self.errorOccurred.emit(error)
            else:
                items, extras, self._notes = result
                self.show_items(items, extras, object_names(self.session.project))
        self.changed.emit()

    def show_items(self, items, extras=(), names=None):
        """Inject completed core results; also useful for differential UI tests."""
        self.items, self.extras = list(items), list(extras)
        self.names = object_names(self.session.project) if names is None else dict(names)
        self._rebuild()

    @staticmethod
    def _memory(item):
        return tuple(item.target), item.text

    def _item(self, index):
        values = self.items + self.extras
        return values[index] if 0 <= index < len(values) else None

    @staticmethod
    def place_of(item):
        target = tuple(item.target)
        if len(target) >= 2 and target[0] in checks.OBJECTS:
            return "object"
        if len(target) >= 2 and target[0] == "phase":
            return "phase"
        return "site" if target[:1] == ("site",) else ""

    def eye_tip(self, item):
        place = self.place_of(item)
        if place == 'object':
            return _("Show where it is: the object framed in the plan and in the 3D view, the rest dimmed")
        if place == 'phase':
            from meridiana import phases
            title = next((phase.title for phase in phases.phases() if phase.id == item.target[1]), item.target[1])
            return _("Go to the {phase} phase, where it is decided").format(phase=title)
        return _("Show the site in the views")

    def _rebuild(self, same_is_quiet=False):
        source = self.items + self.extras if self._view == "delivery" else self.items
        mark = checks.tree_marks(self.items, checks.LEVELS).get(self._subset)
        subset = set(mark.items) if mark else set()
        about = set(checks.about(self.items, *self._related)) if len(self._related) == 2 else set()
        out, visible, included = [], [], []
        for group in checks.grouped(source, self._view, self.names):
            indices = [n for n in group.items if (not self._levels or source[n].level in self._levels)
                       and (not self._phase_only or checks.shown_in_phase(source[n], self._phase))
                       and (self._subset is None or n in subset)]
            if not indices:
                continue
            included.extend(source[n] for n in indices)
            key = "|".join(group.key)
            opened = not self._closed.get(key, group.closed)
            out.append({"header": True, "key": key, "text": group.name, "level": group.level,
                        "count": len(group.items), "counts": checks.counts([source[n] for n in group.items]),
                        "expanded": opened, "itemIndex": -1, "kind": group.kind})
            if opened:
                for position, n in enumerate(indices):
                    item = source[n]
                    out.append({**asdict(item), "header": False, "itemIndex": n, "key": key,
                                "expanded": self._memory(item) in self._opened,
                                "related": n in about, "place": self.place_of(item), "eyeTip": self.eye_tip(item), "hasFix": bool(item.fix),
                                "first": position == 0, "last": position == len(indices) - 1})
                    visible.append(n)
        current = self._current
        if self._current not in visible:
            self._current = visible[0] if visible else -1
        columns = dict(sources=list({item.source for item in included if item.source}),
                       fix=any(item.fix for item in included),
                       place=any(self.place_of(item) for item in included))
        if same_is_quiet and out == self._rows and columns == self._columns and current == self._current:
            return          # r24-fasi (studio 41, S6): a change of phase that shows the same rows asks nothing of QML
        self._rows = out
        self._columns = columns
        self.changed.emit()

    @Slot(str)
    def setView(self, value):
        if value not in checks.BY:
            raise ValueError(value)
        if value != self._view:
            self._view = value
            self._rebuild()
            self.viewChanged.emit(value)

    @Slot(str)
    def setPhase(self, value):
        self._phase = value
        self._rebuild(same_is_quiet=True)    # the phase is read by the rows alone

    @Slot(bool)
    def setPhaseOnly(self, value):
        self._phase_only, self._message = value, ""
        self._rebuild()

    @Slot(str)
    def toggleLevel(self, level):
        if level in checks.LEVELS:
            (self._levels.remove if level in self._levels else self._levels.add)(level)
            self._closed["level|" + level] = False
            self._message = ""
            self._rebuild()

    @Slot("QVariantList")
    def setLevels(self, levels):
        self._levels = set(levels) & set(checks.LEVELS)
        self._message = ""
        self._rebuild()

    @Slot(bool)
    def setObjectOnly(self, value):
        if value and (not self._related or self._related[0] not in (*checks.OBJECTS, "site")):
            self._message = _("Select an object in the views or in the tree first.")
            self.changed.emit()
            return
        self.showSubset(list(self._related) if value else [])

    @Slot("QVariantList")
    def showSubset(self, key):
        self._subset = tuple(key) if key else None
        self._message = ""
        self._rebuild()
        self.takeFirst()

    @Slot(str, str)
    def showRelated(self, kind, oid):
        self._related = (kind, oid)
        if self._subset is not None and self._subset[0] != "group":
            self._subset = self._related
        self._rebuild()
        related = [r["itemIndex"] for r in self._rows if not r["header"] and r["related"]]
        if related and self._current not in related:
            self.selectRow(related[0])

    @Slot(str)
    def toggleGroup(self, key):
        group = next((r for r in self._rows if r["header"] and r["key"] == key), None)
        if group:
            self._closed[key] = group["expanded"]
            self._rebuild()

    @Slot(int)
    def selectRow(self, index):
        if self._current != index and any(not r["header"] and r["itemIndex"] == index for r in self._rows):
            self._current = index
            self.changed.emit()
            self.scrollRequested.emit(index)

    @Slot()
    def takeFirst(self):
        row = next((r for r in self._rows if not r["header"]), None)
        if row is None and self._rows:
            self._closed[self._rows[0]["key"]] = False
            self._rebuild()
            row = next((r for r in self._rows if not r["header"]), None)
        if row:
            self.selectRow(row["itemIndex"])

    @Slot(str)
    def goTo(self, level):
        if level not in checks.LEVELS:
            return
        changed_view = self._view != "level"
        self._view = "level"
        if self._levels and level not in self._levels:
            self._levels.clear()
        self._closed["level|" + level] = False
        self._rebuild()
        if changed_view:
            self.viewChanged.emit("level")
        row = next((r for r in self._rows if not r["header"] and r["level"] == level), None)
        if row:
            self.selectRow(row["itemIndex"])

    @Slot(int)
    def toggleDetail(self, index):
        item = self._item(index)
        if item and item.detail:
            key = self._memory(item)
            (self._opened.remove if key in self._opened else self._opened.add)(key)
            self._current = index
            self._rebuild()

    @Slot(int)
    def showPlace(self, index):
        item = self._item(index)
        if item and self.place_of(item):
            self._current = index
            self.focusRequested.emit(list(item.target))
            self.changed.emit()

    @Slot(int)
    def ask(self, index):
        item = self._item(index)
        if item:
            self.askRequested.emit(item)

    @Slot(int)
    def copyText(self, index):
        item = self._item(index)
        if item:
            QGuiApplication.clipboard().setText(item.text + ("\n" + item.detail if item.detail else ""))

    @Slot()
    def copyNotes(self):
        if self._notes.strip():
            QGuiApplication.clipboard().setText(self._notes)
            self._message = _("The notes for the report are in the clipboard: paste them into the document.")
            self.changed.emit()

    @Slot(int)
    def requestFix(self, index):
        item = self._item(index)
        if item is None or not item.fix:
            self._message = (_("This check has no fix: its detail says what to do.") if item else
                             _("No check under the keyboard: go to one with the arrows first."))
            self.changed.emit()
            return
        self.answerPreview(True)
        self._current = index
        applied = item.fix[0] not in ("compute", "command")
        if applied:
            undo = self.session.undo
            old = undo.steps[undo.index - 1] if undo.can_undo() else None
            try:
                self._apply_fix(item)
            except (ValueError, KeyError, StopIteration, AttributeError) as error:
                self._error = str(error)
                self.errorOccurred.emit(self._error)
                self.changed.emit()
                return
            step = undo.steps[undo.index - 1] if undo.can_undo() else None
            if step is old:
                self._message = _("The fix «{fix}» changed nothing.").format(fix=item.fix_label)
                self.changed.emit()
                return
            self._preview_step = step
            self.focusRequested.emit(list(item.target))
        else:
            self._waiting = item
        self._preview = {"applied": applied,
                         "text": (_("Preview of the fix «{fix}»: the views show the result. Keep it?") if applied
                                  else _("The fix «{fix}»: apply it?")).format(fix=item.fix_label),
                         "keep": _("Keep") if applied else _("Apply"),
                         "drop": _("Take back") if applied else _("Cancel")}
        self.changed.emit()

    def _apply_fix(self, item):
        fix = item.fix
        if fix[0] == "energy":
            self.session.edit(item.fix_label, lambda p: set_path(p.energy, fix[1], copy.deepcopy(fix[2])))
        elif fix[0] == "edit":
            def change(p):
                objects = {"building": p.buildings, "subfield": p.subfields, "exclusion": p.exclusions}
                target = next(obj for obj in objects[fix[1]] if obj.id == fix[2])
                for path, value in fix[3].items():
                    head, _, tail = path.partition(".")
                    if not tail:
                        setattr(target, head, copy.deepcopy(value))
                    elif isinstance(getattr(target, head), dict):
                        set_path(getattr(target, head), tail, copy.deepcopy(value))
                    else:
                        setattr(getattr(target, head), tail, copy.deepcopy(value))
            self.session.edit(item.fix_label, change)
        elif fix[:2] == ("action", "relayout"):
            self.session.edit(item.fix_label, manual.relayout(self.session.project, fix[3]))
        elif fix[:2] == ("action", "split_pitches"):
            self.session.edit(item.fix_label, move.split_on_pitches(self.session.project, fix[3]))
        elif fix[:2] == ("action", "fill"):
            def fill(p):
                sf = next(s for s in p.subfields if s.id == fix[3])
                sf.filled = True
                if not sf.manual:
                    sf.removed = []
            self.session.edit(item.fix_label, fill)
        else:
            raise ValueError(f"Unsupported fix: {fix}")

    @Slot(bool)
    def answerPreview(self, keep):
        step, waiting = self._preview_step, self._waiting
        self._preview_step, self._waiting, self._preview = None, None, {}
        undo = self.session.undo
        if step is not None and not keep and undo.can_undo() and not undo.can_redo() and undo.steps[undo.index - 1] is step:
            undo.take_back()
            self._message = _("Fix taken back: the project is as it was.")
        elif step is not None:
            self._message = _("Fix kept: Ctrl+Z undoes it like any change.")
        if waiting is not None and keep:
            if waiting.fix[0] == "compute":
                self.computeRequested.emit()
            else:
                self.commandRequested.emit(waiting.fix[1])
        self.changed.emit()

    def _undo_moved(self):
        undo, step = self.session.undo, self._preview_step
        if step is not None and (not undo.can_undo() or undo.can_redo() or undo.steps[undo.index - 1] is not step):
            self._preview_step, self._preview = None, {}
            self.changed.emit()

    @Slot()
    def close(self):
        if self._disposed:
            return
        self._disposed = True
        self._timer.stop()
        self.session.listeners.remove(self._session_changed)
        self.session.undo.listeners.remove(self._undo_moved)


def install_checks(engine, backend, theme=None):
    from meridiana.quick.backend.controls import install_controls
    tokens = install_controls(engine, theme)
    engine.rootContext().setContextProperty("checksBackend", backend)
    engine._meridiana_checks = backend
    return tokens
