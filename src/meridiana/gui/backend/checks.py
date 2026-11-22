"""Checks presentation and reversible fixes, with no Widgets dependency (R125-130, R335). The checks themselves are
the window's one job of the checks (app/checks_job.py, R598): this panel shows what it answers."""
from __future__ import annotations

import base64
import copy
from dataclasses import asdict

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QGuiApplication

from meridiana.app import checks_job
from meridiana.core.rules import checks
from meridiana.core.layout import manual
from meridiana.core.model import move
from meridiana.app.interface import layout_commands, symbol_shapes
from meridiana.i18n import _
from meridiana.app.session import set_path

NONE = "none"           # R664: the levels' filter with every level hidden (an empty one is no filter)


def object_names(project):
    """The headers of the view «by object»: the names shown (R605: a sub-field the import made by its short name)."""
    return checks.object_names(project)


class ChecksBackend(QObject):
    changed = Signal()
    # the rows and their columns on their own signal: the job's answer tells the list in a piece of the window's turns
    # and the rest (counts, title, the marks of the views) in the next one (R598: each under 5 ms)
    rowsChanged = Signal()
    currentChanged = Signal()
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
        self._disposed = False
        # Full publications can also move the current row. Selecting a row alone
        # must not rebuild counts, symbols and every grouping control in QML.
        self.changed.connect(self.currentChanged.emit)
        # the window's one job of the checks (the bridge's); a panel on its own makes its own, on a center of its own
        self._own = None
        self.feed = checks_job.Feed.of(session)
        if self.feed is None:
            from .work import WorkBackend
            self._own = WorkBackend(session, parent=self)
            self.feed = checks_job.Feed(session, self._own.center)
        self.session.subscribe(self._session_changed)
        self.session.undo.listeners.append(self._undo_moved)
        self.feed.join("checks.panel.items", self._came, self._failed)

    @Property("QVariantList", notify=rowsChanged)
    def rows(self):
        return self._rows

    @Property('QVariantMap', notify=rowsChanged)
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
                # R664: what a click on a count does
                "showLevel": _("Show «{level}»"), "hideLevel": _("Hide «{level}»"),
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
            mark = self._subset_mark()
            words.append(_("Only the checks of {name}: {n}.").format(
                name=self.names.get(self._subset, self._subset[1]), n=len(mark.items) if mark else 0))
        return " ".join(words)

    @Property("QVariantMap", notify=changed)
    def preview(self):
        return self._preview

    @Property(int, notify=currentChanged)
    def currentIndex(self):
        return self._current

    @Property(bool, notify=changed)
    def busy(self):
        """Whether the checks are on their way (for whoever waits for them: the tests). The panel draws no wait of its
        own: the job is in the one bar of the jobs (R598)."""
        return self.feed.busy()

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Property(str, notify=changed)
    def title(self):
        n = self.counts["fail"] + self.counts["warn"]
        return f'{_("Checks")} ({n})' if n else _("Checks")

    def _session_changed(self, topics):
        """The selection's related rows; the checks themselves are asked by their job (checks_job.Feed)."""
        if "selection" in topics:
            self.feed.center.timed("checks.related", self.showRelated, *self.session.selection)

    @Slot()
    def refresh(self):
        if not self._disposed:
            self.feed.ask()

    def set_plant_state(self, state):
        """Optionally use the shell's live plant, including its year conditions."""
        self.feed.plant_state = state
        self.refresh()

    def _came(self, answer):
        """The job's answer, a piece of the window's turns: the rows made again only when the checks changed."""
        if self._disposed:
            return
        error, self._error = self._error, ""
        if (answer["items"], answer["extras"], answer["names"]) == (self.items, self.extras, self.names):
            self._notes = answer["notes"]
            if error:
                self.changed.emit()
            return
        self._notes = answer["notes"]
        self.items, self.extras, self.names = list(answer["items"]), list(answer["extras"]), dict(answer["names"])
        self._rebuild(spread=True)

    def _failed(self, sentence):
        if not self._disposed:
            self._error = sentence
            self.errorOccurred.emit(sentence)
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
        if any(len(m) >= 2 and m[0] in checks.OBJECTS for m in item.members):
            return "objects"            # R605: one row for several objects, its eye selects them all
        if len(target) >= 2 and target[0] == "phase":
            return "phase"
        return "site" if target[:1] == ("site",) else ""

    def eye_tip(self, item, titles=None):
        """`titles`: the phases' titles by id, when the caller made them once for many rows (_rebuild)."""
        place = self.place_of(item)
        if place == 'object':
            return _("Show where it is: the object framed in the plan and in the 3D view, the rest dimmed")
        if place == 'objects':
            return _("Show where they are: the objects selected together in the plan and in the 3D view")
        if place == 'phase':
            titles = titles if titles is not None else self._phase_titles()
            title = titles.get(item.target[1], item.target[1])
            return _("Go to the {phase} phase, where it is decided").format(phase=title)
        return _("Show the site in the views")

    @staticmethod
    def _phase_titles():
        from meridiana.app.interface import phases
        return {phase.id: phase.title for phase in phases.phases()}

    def _rebuild(self, same_is_quiet=False, spread=False):
        source = self.items + self.extras if self._view == "delivery" else self.items
        titles = self._phase_titles()               # once, not for each row (R598: the rows of an answer in 5 ms)
        mark = self._subset_mark()
        subset = set(mark.items) if mark else set()
        about = set(checks.about(self.items, *self._related)) if len(self._related) == 2 else set()
        out, visible, included = [], [], []
        for group in checks.grouped(source, self._view, self.names, profile_id=self.session.project.regulatory_profile):
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
                                "related": n in about, "place": self.place_of(item), "eyeTip": self.eye_tip(item, titles), "hasFix": bool(item.fix),
                                # R605: the row for several objects says its command («Fill all») on its button
                                "fixText": item.fix_label if item.members and item.fix else "",
                                "first": position == 0, "last": position == len(indices) - 1})
                    visible.append(n)
        current = self._current
        if self._current not in visible:
            self._current = visible[0] if visible else -1
        columns = dict(sources=list({item.source for item in included if item.source}),
                       fix=any(item.fix for item in included),
                       place=any(self.place_of(item) for item in included))
        same = out == self._rows and columns == self._columns
        if same_is_quiet and same and current == self._current:
            return          # r24-fasi (studio 41, S6): a change of phase that shows the same rows asks nothing of QML
        self._rows = out
        self._columns = columns
        if spread:          # the job's answer: the list, then the rest, each a piece of the window's turns
            center = self.feed.center
            if not same:
                center.piece("checks.panel.rows", self.rowsChanged.emit)
            center.piece("checks.panel.state", self.changed.emit)
            return
        if not same:
            self.rowsChanged.emit()
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

    @Property("QVariantList", notify=changed)
    def shownLevels(self):
        """R664: the levels the list shows, each count's button lit for them: all of them when no filter is on."""
        return [lv for lv in checks.LEVELS if not self._levels or lv in self._levels]

    @Slot(str)
    def toggleLevel(self, level):
        """R664 (Daniel 16/11/2026: «è poco evidente quando sono attivi e quando disattivi»): a count's button shows
        or hides its level, as the other toggles do: lit, the level is in the list. All of them shown is no filter;
        none of them shown is kept apart (NONE), so that it is not read as all."""
        if level in checks.LEVELS:
            shown = set(self.shownLevels)
            (shown.remove if level in shown else shown.add)(level)
            self._levels = set() if shown == set(checks.LEVELS) else (shown or {NONE})
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

    def _subset_mark(self):
        """The mark of the subset shown: an object's, a group's, or ("many", name, kind, id, kind, id...) those of
        several objects together (R575: a group of the Project tree, a building closed with what it holds)."""
        marks = checks.tree_marks(self.items, checks.LEVELS)
        if self._subset and self._subset[0] == "many":
            pairs = list(zip(self._subset[2::2], self._subset[3::2], strict=False))
        elif self._subset and len(self._subset) == 2 and self._subset[0] in checks.OBJECTS:
            pairs = [self._subset]
        else:
            return marks.get(self._subset)
        # R605: an object's checks include the row that stands for it among others (checks.about)
        indices = sorted({i for pair in pairs if pair in marks for i in marks[pair].items}
                         | {i for pair in pairs for i in checks.about(self.items, *pair)})
        if not indices:
            return None
        return checks.Mark(checks.worst(self.items[i].level for i in indices), len(indices), indices)

    @Slot("QVariantList")
    def showSubset(self, key):
        self._subset = tuple(key) if key else None
        self._message = ""
        self._rebuild()
        self.takeFirst()
        # R663: the check shown again, also when it was already the current one (a second click on the same mark
        # after Esc): the list brings it in view and shows it selected
        if self._subset is not None and self._current >= 0:
            self.scrollRequested.emit(self._current)

    @Slot(str, str)
    def showRelated(self, kind, oid):
        self._related = (kind, oid)
        subset = self._subset
        if self._subset is not None and self._subset[0] not in ("group", "many"):
            self._subset = self._related
        self._rebuild(same_is_quiet=self._subset == subset)     # the same rows related: nothing asked of QML
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
            self.currentChanged.emit()
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
        place = self.place_of(item) if item else ""
        if place == "objects":
            self._current = index
            self._show_members(item)
            self.changed.emit()
        elif place:
            self._current = index
            self.focusRequested.emit(list(item.target))
            self.changed.emit()

    def _show_members(self, item):
        """The eye of a row that stands for several objects (R605): the last one framed as one object's eye does, and
        all of them selected together when they are of one kind (session.select_many)."""
        members = [tuple(m[:2]) for m in item.members if len(m) >= 2 and m[0] in checks.OBJECTS]
        self.focusRequested.emit(list(members[-1]))
        kinds = {kind for kind, _oid in members}
        if len(kinds) == 1:
            self.session.select_many(members[0][0], [oid for _kind, oid in members])

    @Slot(int)
    def ask(self, index):
        item = self._item(index)
        if item:
            self.askRequested.emit(item)

    @Slot(int)
    def copyText(self, index):
        item = self._item(index)
        if item:
            parts = list(dict.fromkeys(part for part in (item.text, item.detail) if part))
            if item.source and not any(item.source in part for part in parts):
                parts.append(item.source)
            QGuiApplication.clipboard().setText("\n".join(parts))

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
        if item.fix[:2] == ("action", "fill_all"):
            # a command as the bar's, not a fix to preview: done at once, Ctrl+Z takes it back (R605)
            try:
                self._apply_fix(item)
            except (ValueError, KeyError) as error:
                self._error = str(error)
                self.errorOccurred.emit(self._error)
            self.changed.emit()
            return
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
            self.session.edit(item.fix_label, manual.fill(self.session.project, fix[3]))     # R564: «Fill», once
        elif fix[:2] == ("action", "fill_all"):
            # R605: the bar's «Fill» on every sub-field of the row, one change; the layouts follow the edit as after
            # any change (the jobs' common mechanism, with its bar), the full ones are left alone
            self.session.edit(item.fix_label, layout_commands.fill_all(self.session.project, fix[3:]))
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
        self.feed.leave(self._came)
        if self._own is not None:           # the panel's own job and center: ended with it
            self.feed.close()
            self._own.close()
        self.session.listeners.remove(self._session_changed)
        self.session.undo.listeners.remove(self._undo_moved)


def install_checks(engine, backend, theme=None):
    from meridiana.gui.backend.controls import install_controls
    tokens = install_controls(engine, theme)
    engine.rootContext().setContextProperty("checksBackend", backend)
    engine._meridiana_checks = backend
    return tokens
