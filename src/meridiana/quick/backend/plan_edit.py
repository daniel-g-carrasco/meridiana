"""Plan selection and edits, independent of Qt (R295, R299, R300, R344).

Coordinates are metres East/North. Pointer movement is optional: QML can render
the same gesture locally and send only its final command. Every project change
is a session edit; failures return an error event and preserve the project.
"""
from __future__ import annotations

import copy
import math
import random

import numpy as np
import shapely
from shapely.geometry import Point, Polygon

from ... import canopies, clipboard, layout, manual, model, move, props, roof_vertices, roofs, sides, squaring, sweep
from ...energy import plant
from ...i18n import ngettext, number
from .plan_locale import _
from .plan_tools import ridge_building
from .models3d import ASSET_FOR_KIND as ASSET_DEFAULT


# What the plan's clicks, hover, sweeps, Tab and transforms can take in each phase: the one rule (Daniel, 05/11/2026).
# Impianto: what the modules are made of; Modellazione: the model. The other phases do not show the plan.
SELECTABLE = {"plant": frozenset({"subfield", "row", "module"}),
              "modelling": frozenset({"building", "pitch", "exclusion", "prop"})}
EVERY_KIND = frozenset({"building", "pitch", "exclusion", "prop", "subfield", "row", "module"})
PICK_ORDER = ("prop", "exclusion", "module", "subfield", "pitch", "building")   # the Widgets' priority
VERTEX_PX = 13.0            # R427: near a corner of what is selected the corner wins, in logical pixels


def nearest_vertex(ring, point, reach):
    """The place in `ring` of the corner nearest to `point` within `reach`, or -1: with two corners in reach the
    nearer one, not the one drawn last."""
    best, distance = -1, math.inf
    for i, corner in enumerate(ring):
        d = math.dist(corner[:2], point)
        if d <= reach and d < distance:
            best, distance = i, d
    return best


class PlanEditor:
    def __init__(self, session):
        self.session = session
        self.results = {}
        self.phase = "modelling"
        self.tool = "select"
        self.swept = []
        self.swept_things = []
        self.string_optimizers = {}         # inverter's number -> modules on each optimizer (R424)
        self.string_partial = {}            # inverter's number -> the modules with an optimizer, on some only (R456)
        self.gesture = None
        self.pointer = (0.0, 0.0)
        self.preview = {}
        self.hint = ""
        self.last_error = ""
        self.strings_mode = False
        self.chosen_string = -1
        self.draft = None
        self.draft_target = None
        self.snaps_on = True
        self.pick_reach = 0.0  # The event adapter sets six logical pixels in world metres.
        self.notice = ""       # what the last command has to say, in place of the hint until the next gesture
        self.clip = None       # what Ctrl+C or Ctrl+X took (R432)
        self.side = None       # a side being dragged parallel to itself (R473, R445 phase B): see start_side
        self._quad_indexes = {}
        self._wiring_scene = None
        self._hint()

    @property
    def project(self):
        return self.session.project

    @property
    def selection(self):
        return self.session.selection

    @property
    def selected_module(self):
        return self.session.selected_module

    def set_results(self, results):
        self.results = {k: v for k, v in results.items() if not isinstance(v, Exception)}
        self._quad_indexes.clear()

    def selectable(self):
        """What the plan can take in this phase. An object chosen elsewhere (the tree, a check's mark) stays lit but
        has no grips and does not move."""
        return SELECTABLE.get(self.phase, EVERY_KIND)

    def select(self, kind, oid, key=""):
        if kind == "module":
            kind = "subfield"
        self.session.select(kind or "site", oid, (oid, key) if key else ("", ""))
        self.gesture = None
        self.preview = {}
        self._hint()

    def set_phase(self, phase):
        self.phase = "modelling" if phase == "model" else phase
        self.gesture = None
        self.preview = {}
        self.swept = []
        self.swept_things = []
        self.draft = self.draft_target = None
        self.notice = ""
        kind = self.selection[0]
        if kind != "site" and kind not in self.selectable():
            self.select("site", "")
        self._hint()

    def set_tool(self, tool):
        self.tool = tool
        self.notice = ""
        self.gesture = None
        self.side = None
        self.preview = {}
        if tool not in ("string", "draw_string"):
            self.draft = self.draft_target = None
        elif self.draft is None:
            self.start_draft()
        if tool == "square":
            self.tool = "select"
            return self.apply_command({"type": "square"})
        if tool == "rotate":
            self._gesture()
        self._hint()
        return []

    def set_strings_mode(self, on):
        self.strings_mode = bool(on)

    def choose_string(self, index):
        self.chosen_string = index if 0 <= index < len(self.runs()) else -1

    def move_vertex(self, index, point):
        return self.apply_command({"type": "vertex", "index": index, "point": point})

    def start_grip(self, grip, point):
        """Take a transform grip at its world point; the next click commits it."""
        if grip not in ("move", "rotate"):
            raise ValueError("Unknown transform grip")
        if not self._movable():
            return []
        self.set_tool("move")
        self.pointer = tuple(map(float, point))
        g = self._gesture()
        if g is None:
            return []
        g.grip = True
        if grip == "move":
            g.base = self.pointer
        else:
            g.to_rotate(self.pointer, .001)
        self.tool = g.mode
        self.move(self.pointer)
        self._hint()
        return []

    def set_side_length(self, index, value):
        return self.apply_command({"type": "side", "index": index, "value": value})

    # a side dragged parallel to itself (R473; R445 phase B for a sub-field that is its modules)

    def side_at(self, point, reach):
        """The side of what is selected under `point` (within `reach` metres), -1 when there is none or a corner is
        nearer (the corner wins, R427), or the thing cannot be reshaped here."""
        kind, oid = self.selection
        if (self.tool != "select" or kind not in ("building", "subfield", "exclusion") or not oid
                or kind not in self.selectable() or self.session.selected_many()):
            return -1
        ring = self._side_ring()
        if not ring or nearest_vertex(ring, point, reach * VERTEX_PX / 6.0) >= 0:
            return -1
        found = sides.nearest(ring, point, reach)
        return -1 if found is None else found

    def _side_ring(self):
        kind, oid = self.selection
        obj = self._object(self.project, kind, oid)
        if obj is None:
            return []
        return [list(map(float, q)) for q in (obj.footprint if kind == "building" else obj.ring)]

    def start_side(self, index, point):
        """Take side `index` of what is selected at `point`: the pointer then moves it along its normal, the
        neighbours lengthen or shorten; a sub-field that is its modules shows the modules that would come (green)
        and go (red). A measure can be typed; Enter applies it, Esc leaves everything as it was."""
        ring = self._side_ring()
        if not ring or not 0 <= index < len(ring):
            return []
        kind, oid = self.selection
        sf = self.session.subfield(oid) if kind == "subfield" else None
        self.side = {"index": int(index), "kind": kind, "oid": oid, "ring": ring, "typed": "", "distance": 0.0,
                     "flush": bool(sf is not None and sf.flush and sf.manual), "last": None}
        self.notice = self.last_error = ""
        self.tool = "side"
        self.gesture = None
        self.pointer = tuple(map(float, point))
        self._side_preview()
        self._hint()
        return []

    def _side_preview(self):
        g = self.side
        if g is None:
            return
        distance = g["distance"]
        if g["typed"]:
            value = move.parse(g["typed"])
            if value is not None:
                distance = value
        else:
            distance = sides.offset(g["ring"], g["index"], self.pointer)
        g["distance"] = distance
        preview = {"type": "side", "tool": "side", "kind": g["kind"], "oid": g["oid"], "index": g["index"],
                   "distance": distance, "rings": [], "add": [], "remove": [], "refused": ""}
        try:
            if g["flush"]:
                sf = self.session.subfield(g["oid"])
                found = manual.preview_shift(self.project, sf, g["index"], distance, self.results.get(g["oid"]))
                preview.update(rings=[found["ring"]], add=found["add"], remove=found["remove"],
                               added=found["added"], removed=found["removed"])
            else:
                preview["rings"] = [sides.shift(g["ring"], g["index"], distance)]
        except ValueError as error:
            preview["refused"] = str(error)
            preview["rings"] = [g["last"]] if g["last"] else []
        else:
            g["last"] = preview["rings"][0] if preview["rings"] else None
        lines = [_("side {n}: {d} m").format(n=g["index"] + 1, d=number(distance))]
        if g["typed"]:
            lines[0] = _("side {n}: {d}_").format(n=g["index"] + 1, d=g["typed"])
        if g["flush"] and not preview["refused"]:
            lines.append(_("+{a} −{r} modules").format(a=preview.get("added", 0), r=preview.get("removed", 0))
                         .replace("−", "-"))
        if preview["refused"]:
            lines.append(preview["refused"])
        ring = g["ring"]
        a, b = ring[g["index"]], ring[(g["index"] + 1) % len(ring)]
        nx, ny = sides.outward(ring, g["index"])
        mid = ((a[0] + b[0]) / 2 + nx * distance, (a[1] + b[1]) / 2 + ny * distance)
        preview["card"] = {"anchor": list(mid), "lines": lines}
        self.preview = preview

    def end_side(self, point=None):
        """Let the side go where it is (or where the measure typed says): one undoable change; nothing when it did
        not move."""
        g = self.side
        if g is None:
            return []
        if point is not None and not g["typed"]:
            self.pointer = tuple(map(float, point))
        self._side_preview()
        distance, refused = self.preview.get("distance", 0.0), self.preview.get("refused")
        self.side, self.preview, self.tool = None, {}, "select"
        if refused:
            self.last_error = refused
            self._hint()
            return [{"type": "error", "message": refused}]
        if abs(distance) < 1e-4:
            self._hint()
            return []
        return self.apply_command({"type": "side_shift", "kind": g["kind"], "oid": g["oid"], "index": g["index"],
                                   "distance": distance})

    def cancel_side(self):
        self.side, self.preview, self.tool = None, {}, "select"
        self._hint()
        return []

    def row_handle(self):
        """Select's row endpoint, in metres East/North, computed by the core."""
        kind, oid = self.selection
        if kind != "row" or self.tool != "select":
            return {}
        sfid, _sep, rid = oid.partition("/")
        sf = self.session.subfield(sfid)
        if sf is None:
            return {}
        result = self.results.get(sfid)
        if result is None and not sf.manual:
            return {}  # Await the worker; a visual property must not run a layout.
        rows = manual.rows_now(self.project, sf, result)
        row = next((row for row in rows if row.id == rid), None)
        if row is None:
            return {}
        size = manual.frame(self.project, sf, rows)[1]
        x, y = manual.end_point(row, size)
        return {"oid": oid, "x": x, "y": y,
                "hint": _("Drag the end of the row: it takes or gives back places, one module at a time.")}

    def resize_row(self, oid, point):
        return self.apply_command({"type": "row_resize", "oid": oid, "point": point})

    def double_click(self, point, modifiers=None):
        if self.draft is not None:
            self.click(point, modifiers)
            return self.finish_draft()
        kind, sfid, key = self.pick(point)
        if kind == "module":
            return self.apply_command({"type": "module_turn", "sfid": sfid, "key": key})
        return []

    def drag(self, point, modifiers=None):
        """A held left button collecting modules; hover alone never adds one."""
        return self.click(point, modifiers) if self.draft is not None else self.move(point, modifiers)

    def _hint(self):
        if self.phase not in ("modelling", "plant"):
            self.hint = ""
        elif self.notice:
            self.hint = self.notice
        elif self.tool == "paste":
            self.hint = self.preview.get("refused") or self.preview.get("where") or _("Click: paste here · Esc: cancel")
            if not self.preview.get("refused") and self.preview.get("where"):
                self.hint = _("Click: paste {where} · Esc: cancel").format(where=self.preview["where"])
        elif self.draft is not None:
            self.hint = _("Click: module · Enter: finish string · Backspace: last module · Esc: cancel")
        elif self.side is not None:
            self.hint = (_("Drag: move the side, parallel · type a measure in metres · Enter: apply · Esc: cancel")
                         if not self.side["flush"] else
                         _("Drag: whole rows and columns come (green) or go (red), the modules laid stay · type a "
                           "measure · Enter: apply · Esc: cancel"))
        elif self.tool == "erase_inverter_strings":
            self.hint = _("Click: inverter and strings to erase · Esc: leave")
        elif self.tool == "erase_inverter":
            self.hint = _("Click: inverter to erase · Esc: leave")
        elif self.tool == "erase_string":
            self.hint = _("Click: string to erase · Esc: leave")
        elif self.gesture is not None and self.gesture.grip and not self.gesture.typing:
            self.hint = _("Click: apply · Enter/Space: move or rotate · C: copy · Esc: cancel")
        elif self.tool == "rotate" or self.gesture is not None and self.gesture.mode == "rotate":
            self.hint = _("Click: angle · Enter: apply · Ctrl: 5° · Shift: 90° · C: copy · Esc: cancel")
        elif self.tool == "move":
            self.hint = (_("Click: destination · Enter: apply · Tab: direction · Ctrl: copy · Esc: cancel")
                         if self.gesture is not None and self.gesture.base is not None else
                         _("Click: base point · R: rotate · arrows: move · Esc: leave"))
        elif self.swept or self.swept_things:
            self.hint = _("Click: start again · Shift: add · Ctrl: add or take away · Del: delete selection · "
                          "Esc: clear")
        elif self.phase == "plant":
            self.hint = _("Click: select · second click: row · Shift: add · Ctrl: add or take away · Tab: what lies "
                          "under it · Esc: parent · Del: delete")
        else:
            self.hint = _("Click: select · Tab: what lies under it · Esc: parent · Del: delete")

    def rings(self):
        p = self.project
        out = {(k, x.id): (x.footprint if k == "building" else x.footprint() if k == "prop" else x.ring)
               for k, things in (("building", p.buildings), ("subfield", p.subfields),
                                  ("exclusion", p.exclusions), ("prop", p.props)) for x in things}
        for b in p.buildings:
            out.update({("pitch", f"{b.id}:{i}"): pitch.ring for i, pitch in enumerate(b.pitches())})
        return out

    def pick(self, point):
        """The topmost thing the phase can take at `point`; ("site", "", "") when there is none."""
        return next(self._hits(point), ("site", "", ""))

    def pick_stack(self, point):
        """Everything the phase can take at `point`, the topmost first: what Tab walks through."""
        return list(self._hits(point))

    def _hits(self, point, kinds=None):
        kinds = self.selectable() if kinds is None else kinds
        here = Point(*point)
        rings = self.rings()
        for kind in PICK_ORDER:
            if kind not in kinds:
                continue
            if kind == "module":
                yield from self._module_hits(point, here)
                continue
            found = [(oid, ring) for (k, oid), ring in rings.items() if k == kind and len(ring) >= 3]
            if kind == "building":              # R352: a plant room on a roof before the building under it
                found.sort(key=lambda item: Polygon(item[1]).area)
            for oid, ring in found:
                if Polygon(ring).covers(here):
                    if kind != "pitch" or self._sloped(oid):
                        yield kind, oid, ""

    def _sloped(self, oid):
        """A level pitch is its building: no pitch to choose apart from it, and the scene draws none."""
        bid, _sep, place = oid.partition(":")
        return self.project.building(bid).pitches()[int(place)].tilt > 0

    def _module_hits(self, point, here, only=None):
        """The module under the point, one per sub-field; none under it, the nearest in reach."""
        inside = False
        for sfid, r in self.results.items():
            sf = self.session.subfield(sfid)
            if sf is None or only not in (None, sfid):
                continue
            index = self._quad_index(sfid, r)
            near = np.flatnonzero(np.all((index.low <= point) & (index.high >= point), axis=1))
            removed = set(sf.removed)
            for at in near[shapely.covers(index.shapes[near], here)]:
                m = r.modules[int(at)]
                if m.key not in removed:
                    inside = True
                    yield "module", sfid, m.key
                    break
        if inside or self.pick_reach <= 0:
            return
        closest, distance = None, math.inf
        reach = self.pick_reach
        for sfid, result in self.results.items():
            sf = self.session.subfield(sfid)
            if sf is None or only not in (None, sfid):
                continue
            index = self._quad_index(sfid, result)
            near = np.flatnonzero(np.all((index.low-reach <= point) & (index.high+reach >= point), axis=1))
            if sf.removed:
                removed = set(sf.removed)
                near = np.asarray([at for at in near if result.modules[int(at)].key not in removed], dtype=int)
            if len(near):
                distances = shapely.distance(index.shapes[near], here)
                at = int(np.argmin(distances))
                value = float(distances[at])
                if value <= reach and value < distance:
                    distance = value
                    closest = ("module", sfid, result.modules[int(near[at])].key)
        if closest is not None:
            yield closest

    def anchor(self):
        """The object the clicks stay on (R427 c): (kind, id, outline), or None. A row or a module anchors its
        sub-field; what the phase cannot take anchors nothing."""
        kind, oid = self.selection
        if self.selected_module[0]:
            kind, oid = "subfield", self.selected_module[0]
        elif kind == "row":
            kind, oid = "subfield", oid.partition("/")[0]
        if not oid or kind not in self.selectable() or self.session.selected_many():
            return None
        ring = self.rings().get((kind, oid))
        return (kind, oid, ring) if ring is not None and len(ring) >= 3 else None

    def _anchored(self, point):
        """What a click at `point` means while something is selected: it stays on it, on its own modules for a
        sub-field, until the click falls outside it (a hair round the outline counts as on it)."""
        found = self.anchor()
        if found is None:
            return None
        kind, oid, ring = found
        here = Point(*point)
        if kind == "subfield":
            hit = next(self._module_hits(point, here, only=oid), None)
            if hit is not None:
                return hit
        return (kind, oid, "") if Polygon(ring).distance(here) <= max(self.pick_reach, 0.0) else None

    def cycle(self, point, step=1):
        """Tab: the next thing under the pointer, as AutoCAD's selection cycling."""
        stack = self.pick_stack(point)
        if not stack:
            self._hint()
            return []
        here = ("module", *self.selected_module) if self.selected_module[0] else (*self.selection, "")
        at = stack.index(here) + step if here in stack else (0 if step > 0 else -1)
        kind, oid, key = stack[at % len(stack)]
        self.swept, self.swept_things = [], []
        self.select(kind, oid, key)
        names = {"prop": _("3D object"), "exclusion": _("Exclusion"), "module": _("Module"), "subfield": _("Sub-field"),
                 "pitch": _("Pitch"), "building": _("Building")}
        self.hint = _("{what}, {n} of {total} under the pointer · Tab: the next · Esc: parent").format(
            what=names[kind], n=at % len(stack) + 1, total=len(stack))
        return []

    def _quad_index(self, sfid, result):
        if sfid not in self._quad_indexes:
            self._quad_indexes[sfid] = sweep.QuadIndex([m.corners for m in result.modules])
        return self._quad_indexes[sfid]

    def _rid(self, sfid, key):
        return manual.row_of(self.results.get(sfid), key)

    def click(self, point, modifiers=None):
        mods = set(modifiers or ())
        self.pointer = tuple(map(float, point))
        self.notice = self.last_error = ""
        if self.tool == "paste":
            return self.apply_command({"type": "paste", "point": self.pointer})
        hit = self.pick(point)
        kind, oid, key = hit
        if self.draft is not None:
            if kind == "module":
                ref = (oid, key)
                owner = self.owner(oid, key)
                if ref not in self.draft and (owner < 0 or owner == self.draft_target[2] or "shift" in mods):
                    self.draft.append(ref)
                elif owner >= 0 and owner != self.draft_target[2] and "shift" not in mods:
                    self.hint = _("This module is in string {name}: hold Shift and click it to move it into this one.").format(
                        name=plant.run_label(self.runs(), owner))
                self.preview = {"type": "string", "modules": list(self.draft)}
            return []
        if self.tool.startswith("erase_"):
            return self.apply_command({"type": self.tool, "sfid": oid, "key": key}) if kind == "module" else []
        if self.tool in ("move", "rotate"):
            if not self._movable():
                if kind == "module":
                    if self.phase == "plant" and self.tool != "rotate":
                        rid = self._rid(oid, key)
                        if "shift" in mods:
                            self.select("subfield", oid, key)
                        else:
                            self.select("row", f"{oid}/{rid}") if rid else self.select("subfield", oid)
                    else:
                        self.select("subfield", oid)
                elif kind == "pitch" and self.phase != "plant":
                    self.select("building", oid.partition(":")[0])
                elif kind in self._allowed():
                    self.select(kind, oid)
                return []
            g = self._gesture()
            if g.mode == "move" and g.base is None and not g.typing:
                g.base = self.pointer
                self._hint()
                return []
            return self._commit_gesture(mods)
        if self.tool != "select":
            return []
        if self.strings_mode and self.phase == "plant":
            self.chosen_string = self.owner(oid, key) if kind == "module" else -1
            return []
        # R529, the rule of the selection (docs/quick/regole.md, Daniel 07/11/2026 sera): a plain click starts the
        # selection again, Shift+click adds, Ctrl+click adds or takes away (toggles); the windows the same
        # (select_area), Ctrl there takes away
        if self.phase == "plant" and self.swept and not mods & {"ctrl", "shift"}:
            self.swept = []
        elif self.phase == "plant" and mods & {"ctrl", "shift"} and kind == "module":
            ref = (oid, key)
            mine = tuple(self.selected_module)
            base = self.swept or ([mine] if mine[0] and mine != ref else [])
            self.swept = ([x for x in base if x != ref] if ref in base and "ctrl" in mods else
                          base if ref in base else base + [ref])
            self.session.select(*self.selection)
            self._hint()
            return []
        self.swept_things = []
        anchored = None if mods else self._anchored(point)
        if anchored is not None:
            kind, oid, key = anchored
        elif kind == "pitch":
            kind, oid = "building", oid.partition(":")[0]   # a click on a roof takes the building, Tab its pitch
        # R529: the row comes with a second click on the module that is selected; a click on another module of its row
        # takes that module, as the hover shows (before, any module of the same row gave the row)
        rid = self._rid(oid, key) if kind == "module" else ""
        if rid and tuple(self.selected_module) == (oid, key):
            self.select("row", f"{oid}/{rid}")
        elif kind == "module":
            self.select("subfield", oid, key)
        else:
            self.select(kind, oid)
        if kind == "site":
            self._say_other_phase(point)
        return []

    def _say_other_phase(self, point):
        """A click on what the phase cannot take selects nothing, and says where it is changed."""
        if self.phase == "plant" and next(self._hits(point, frozenset({"prop", "exclusion", "building"})), None):
            self.notice = _("Buildings, pitches and objects are changed in Modelling.")
        elif self.phase == "modelling" and next(self._hits(point, frozenset({"subfield", "module"})), None):
            self.notice = _("Sub-fields and modules are changed in Plant.")
        self._hint()

    def selection_back(self):
        kind, oid = self.selection
        if self.selected_module[0]:
            target = ("subfield", self.selected_module[0])
        elif kind == "row":
            target = ("subfield", oid.partition("/")[0])
        elif kind == "pitch":
            target = ("building", oid.partition(":")[0])
        elif kind in ("subfield", "exclusion", "prop"):
            obj = self._object(self.project, kind, oid)
            target = ("building", obj.building) if obj and obj.building else ("site", "")
        else:
            target = ("site", "")
        if target[0] not in self.selectable():
            target = ("site", "")
        self.select(*target)

    def select_area(self, ring, kind="window", modifiers=None):
        """A screen-directed window/crossing or lasso, already mapped to East/North."""
        if kind not in ("window", "crossing"):
            raise ValueError("Unknown selection area kind")
        # R529: a plain window starts the selection again, Shift adds to it, Ctrl takes away from it
        mods = set(modifiers or ())
        remove, add = "ctrl" in mods, "shift" in mods
        if self.phase == "plant":
            taken = []
            for sfid, result in self.results.items():
                chosen = self._quad_index(sfid, result).chosen(ring, kind)
                sf = self.session.subfield(sfid)
                taken += [(sfid, m.key) for m, on in zip(result.modules, chosen, strict=True)
                          if on and sf is not None and m.key not in sf.removed]
            gone, had = set(taken), set(self.swept)
            self.swept = ([t for t in self.swept if t not in gone] if remove else
                          self.swept + [t for t in taken if t not in had] if add else list(dict.fromkeys(taken)))
            self.session.select(*self.selection)
        else:
            rings = {k: v for k, v in self.rings().items() if k[0] in ("building", "exclusion", "prop")}
            taken = [k for k, on in zip(rings, sweep.chosen_rings(list(rings.values()), ring, kind), strict=True) if on]
            old = self.swept_things
            taken = ([t for t in old if t not in taken] if remove else
                     old + [t for t in taken if t not in old] if add else taken)
            self.swept_things = taken
            if len(taken) == 1:
                self.select(*taken[0])
            elif taken:
                self.select("site", "")
        self._hint()
        return []

    def _allowed(self):
        return self.selectable()

    def _target(self):
        if self.phase == "plant" and self.selected_module[0]:
            return "module", "/".join(self.selected_module)
        return self.selection

    def _movable(self):
        kind, oid = self._target()
        if self.session.selected_many():
            return False                                    # R439: chosen in the tree to change them together
        if kind == "pitch" and move.outline(self.project, kind, oid) is None:
            return False                                    # only a pitch drawn by hand moves by itself
        return bool(oid) and kind in self._allowed()

    def _gesture(self):
        if not self._movable():
            return None
        kind, oid = self._target()
        if self.gesture is None:
            if kind == "module":
                sfid, _sep, key = oid.partition("/")
                m = next((m for m in getattr(self.results.get(sfid), "modules", []) if m.key == key), None)
                middle = m.centre if m else self.pointer
            else:
                middle = move.centre(self.project, kind, oid)
            if middle is None:
                return None
            self.gesture = move.Gesture(kind, oid, tuple(middle))
            if self.tool == "rotate":
                self.gesture.to_rotate(self.pointer, .001)
        return self.gesture

    def move(self, point, modifiers=None):
        self.pointer = tuple(map(float, point))
        if self.side is not None:
            if not self.side["typed"]:
                self._side_preview()
            return []
        if self.tool == "paste":
            self.last_error = ""        # the refusal of a click stays until the pointer goes somewhere else
            self._paste_preview()
            return []
        g = self._gesture() if self.tool in ("move", "rotate") else None
        if g is not None:
            what = self._transform(set(modifiers or ()))
            self.preview = {"type": "transform", "kind": g.kind, "oid": g.oid, **what}
            if g.kind == "module":
                sfid, _sep, key = g.oid.partition("/")
                rings = [m.corners for m in getattr(self.results.get(sfid), "modules", []) if m.key == key]
            else:
                rings = move.moving(self.project, g.kind, g.oid)
            transform = (move.turn(what["cx"], what["cy"], what["degrees"]) if what["mode"] == "rotate"
                         else move.shift(what["dx"], what["dy"]))
            self.preview["rings"] = [move.moved(ring, transform) for ring in rings]
            active = what['mode'] == 'rotate' or g.base is not None or bool(g.typing)
            if not active:
                self.preview['rings'] = []
            if what['mode'] == 'rotate':
                angle = what['degrees']
                lines = [_('rotation {angle}°').format(angle=number(angle, 0 if abs(angle-round(angle)) < 1e-9 else 1))]
                self.preview.update(pivot=[what['cx'], what['cy']], start=list(g.start) if g.start is not None else None,
                                    pointer=list(self.pointer))
            elif active:
                lines = [_('{length} m').format(length=number(math.hypot(what['dx'], what['dy']))),
                         _('E {dx} m, N {dy} m').format(dx=number(what['dx']), dy=number(what['dy']))]
                self.preview['base'] = list(g.base) if g.base is not None else None
            else:
                lines = []
            if g.typing:
                lines.insert(0, g.label())
            if what['copy'] and active:
                lines.append(_('a copy'))
            self.preview['card'] = dict(anchor=list(self.pointer), lines=lines)
        return []

    def _transform(self, mods):
        g = self.gesture
        if g.mode == "rotate":
            about = g.about or g.middle
            return {"mode": "rotate", "cx": about[0], "cy": about[1],
                    "degrees": g.angle(self.pointer, move.angle_step(mods) if self.snaps_on else 0), "copy": g.copy}
        dx, dy = g.offset(self.pointer)
        return {"mode": "move", "dx": dx, "dy": dy, "copy": g.copy or "ctrl" in mods}

    def _commit_gesture(self, mods):
        g = self.gesture
        if g is None:
            return []
        command = {"type": "transform", "kind": g.kind, "oid": g.oid, **self._transform(mods)}
        self.gesture = None
        self.preview = {}
        return self.apply_command(command)

    def key(self, key, text="", modifiers=None):
        mods = set(modifiers or ())
        self.notice = self.last_error = ""
        if self.side is not None:
            g = self.side
            if key == "Escape":
                return self.cancel_side()
            if key in ("Enter", "Return"):
                return self.end_side()
            if key == "Backspace":
                g["typed"] = g["typed"][:-1]
            elif text and not mods & {"ctrl", "alt"} and (text.isdigit() or text in ".,-"):
                g["typed"] += text
            else:
                return []
            self._side_preview()
            self._hint()
            return []
        if key == "Escape":
            if self.draft is not None:
                self.draft = self.draft_target = None
                self.preview = {}
                self.tool = "select"
            elif self.gesture is not None and self.gesture.typing:
                self.gesture.clear()
                self.move(self.pointer, mods)
            elif self.tool != "select":
                self.set_tool("select")
            elif self.swept or self.swept_things:
                self.swept, self.swept_things = [], []
            else:
                self.selection_back()
            self._hint()
            return []
        if self.draft is not None:
            if key == "Backspace" and self.draft:
                self.draft.pop()
                self.preview = {"type": "string", "modules": list(self.draft)}
            elif key in ("Enter", "Return"):
                return self.finish_draft()
            return []
        if key in ("Delete", "Del"):
            return self.apply_command({"type": "delete"})
        if self.tool == "select" and key in ("Tab", "Backtab"):
            return self.cycle(self.pointer, -1 if key == "Backtab" or "shift" in mods else 1)
        if "ctrl" in mods and self.tool in ("select", "paste") and key in ("C", "X", "V"):
            return self.apply_command({"type": {"C": "copy", "X": "cut", "V": "paste_start"}[key]})
        if self.tool == "paste" and key in ("Enter", "Return"):
            return self.apply_command({"type": "paste", "point": self.pointer})
        if self.tool not in ("move", "rotate"):
            return []
        if key.lower() in ("left", "right", "up", "down") and self._movable():
            dx, dy = move.nudge(key.lower(), mods)
            kind, oid = self._target()
            return self.apply_command({"type": "transform", "kind": kind, "oid": oid,
                                       "mode": "move", "dx": dx, "dy": dy, "nudge": True})
        g = self._gesture()
        if key.upper() == "R" and not mods & {"ctrl", "alt"}:
            if g is not None:
                if g.mode == "move":
                    g.to_rotate(self.pointer, .001)
                else:
                    g.to_move()
                self.tool = g.mode
            else:
                self.tool = "move" if self.tool == "rotate" else "rotate"
        elif g is not None:
            if key.upper() == "C" and not mods & {"ctrl", "alt"}:
                g.copy = not g.copy
            elif key in ("Tab", "Backtab"):
                g.tab()
            elif key == "Backspace":
                g.backspace()
            elif g.grip and (key == "Space" or key in ("Enter", "Return") and not g.typing):
                g.cycle(self.pointer, .001)
                self.tool = g.mode
            elif key in ("Enter", "Return") and (g.mode == "rotate" or g.typing or g.base is not None):
                return self._commit_gesture(mods)
            elif text and not mods & {"ctrl", "alt"}:
                g.type(text)
        self._hint()
        if self.gesture is not None:
            self.move(self.pointer, mods)
        return []

    @staticmethod
    def _object(p, kind, oid):
        things = {"building": p.buildings, "subfield": p.subfields, "exclusion": p.exclusions, "prop": p.props}
        return next((x for x in things.get(kind, []) if x.id == oid), None)

    def _edit(self, label, change, merge=None):
        self.session.edit(label, change, merge)

    def _prop_series(self, c):
        """R375 «Along a line»: a copy of the kind every `step` metres from the first click to the last, the first on
        the start, turned along the line when `align`; one step of undo, the last one selected."""
        o = c.get("options") or {}
        (ax, ay), (bx, by) = (float(v) for v in c["points"][0]), (float(v) for v in c["points"][-1])
        step = max(0.2, float(o.get("step") or 5.0))
        run = math.hypot(bx - ax, by - ay)
        count = int(run / step + 1e-9) + 1
        bearing = math.degrees(math.atan2(by - ay, bx - ax)) % 360. if o.get("align", True) else 0.0
        made = []

        def change(p):
            for i in range(count):
                t = i * step / run if run > 1e-9 else 0.0
                at = [ax + (bx - ax) * t, ay + (by - ay) * t]
                pid = p.new_id("o")
                made.append(pid)
                p.props.append(model.Prop(id=pid, kind=c["kind"], at=at, rotation=bearing, asset=o.get("asset") or None,
                                          building=p.prop_host(at)))
        self._edit(_("Place a row of 3D objects"), change)
        return made

    def _prop_group(self, c):
        """R375 «Small family»: five to seven of the kind round the click, within `radius`, each turned and sized a
        little differently (`variation`, a share); people and vehicles mix their kinds and models (models3d.mix_for).
        The same click with the same `seed` gives the same family."""
        from .models3d import mix_for
        o = c.get("options") or {}
        cx, cy = (float(v) for v in c["point"])
        radius = max(0.5, float(o.get("radius") or 6.0))
        variation = min(1.0, max(0.0, float(o.get("variation") or 20.0) / 100.0))
        rng = random.Random(f"{round(cx, 3)}|{round(cy, 3)}|{int(o.get('seed') or 0)}")
        mix = mix_for(c["kind"])
        family = props.family(c["kind"])
        count = 5 + rng.randrange(3)
        plan = []
        for i in range(count):
            angle = i * math.tau / count + rng.random() * .35
            away = radius * (.35 + rng.random() * .55)
            kind, assets = rng.choice(mix)
            asset = rng.choice(assets) if assets else None
            turn = rng.uniform(-180.0, 180.0) * (variation if family == "car" else 1.0)
            size = 1.0 + rng.uniform(-1.0, 1.0) * variation * (0.5 if family == "person" else 1.0)
            plan.append((kind, asset, [cx + math.cos(angle) * away, cy + math.sin(angle) * away], turn % 360., size))
        made = []

        def change(p):
            for kind, asset, at, turn, size in plan:
                pid = p.new_id("o")
                made.append(pid)
                height = props.measures(kind)["height"] * size
                p.props.append(model.Prop(id=pid, kind=kind, at=at, rotation=turn, height=round(height, 2),
                                          asset=None if asset == ASSET_DEFAULT.get(kind) else asset,
                                          building=p.prop_host(at)))
        self._edit(_("Place a small family of 3D objects"), change)
        return made

    def apply_command(self, command):
        self.last_error = ""
        try:
            result = self._apply(command)
        except (ValueError, IndexError, KeyError) as error:
            self.last_error = str(error)
            self.hint = _("Not changed: {why}").format(why=error)
            return [{"type": "error", "message": self.hint}]
        self._hint()
        return result or []

    def _apply(self, c):
        typ = c["type"]
        if typ == "tool":
            return self.set_tool(c["tool"])
        if typ == "transform":
            return self._apply_transform(c)
        if typ == "delete":
            return self._delete()
        if typ in ("copy", "cut"):
            return self._take(typ == "cut")
        if typ == "paste_start":
            return self._start_paste()
        if typ == "paste":
            return self._paste(c["point"])
        if typ == "split_pitches":
            return self._split(c.get("oid", self.selection[1]))
        if typ == "leave_group":
            self._edit(_("Leave the group"), move.leave_group(self.project, c.get("oid", self.selection[1])))
            return [{"type": "changed", "command": typ}]
        if typ.startswith("erase_"):
            return self._erase(typ, c["sfid"], c["key"])
        if typ == "add_vertices":
            return self._add_vertices(c)
        if typ in ("vertex", "vertices", "side", "square", "side_shift"):
            if typ == "side_shift" and c.get("kind", self.selection[0]) == "subfield":
                sf = self.session.subfield(c.get("oid", self.selection[1]))
                if sf is not None and sf.flush and sf.manual:
                    change = manual.shift_side(self.project, sf.id, int(c["index"]), float(c["distance"]),
                                               self.results.get(sf.id))
                    self._edit(_("Move a side of the sub-field"), change)
                    return [{"type": "changed", "command": typ}]
            return self._outline_edit(c)
        if typ == "fire_bands":
            made = []
            self._edit(_("Add the fire-brigade bands"), lambda p: made.extend(p.fire_bands(c.get("building"))))
            self.notice = (_("{n} free bands of 1 m added as obstacles (DCPREV 14030 3.3.5.1): the modules on them are "
                             "set aside, red; take the band away to lay there.").format(n=len(made)) if made else
                           _("The bands are there already."))
            return [{"type": "changed", "command": typ}]
        if typ in ("polygon", "pitch"):
            return self._polygon(c.get("tool", "pitch"), c["ring"], c.get("spec", {}))
        if typ == "whole":
            here = Point(*c["point"])
            for b in self.project.buildings:
                for pitch in b.pitches():
                    if Polygon(pitch.ring).covers(here):
                        return self._polygon(c["tool"], pitch.ring, c.get("spec", {}))
            raise ValueError(_("Double-click a roof to take a pitch whole; on the ground, draw the area."))
        if typ in ("prop", "prop_line"):
            points = c.get("points")
            at = list(c["point"] if points is None else points[0])
            pid = self.project.new_id("o")
            self._edit(_("Draw a linear 3D object") if points else _("Add a 3D object"),
                       lambda p: p.props.append(model.Prop(id=pid, kind=c["kind"], at=at, path=points,
                                                          asset=c.get("asset") or None, building=p.prop_host(at))))
            self.select("prop", pid)
        elif typ == "prop_series":
            made = self._prop_series(c)
            self.select("prop", made[-1])
        elif typ == "prop_group":
            made = self._prop_group(c)
            self.select("prop", made[-1])
        elif typ == "canopy":
            spec = c["spec"] if isinstance(c["spec"], canopies.Spec) else canopies.Spec(**c["spec"])
            made = []
            self._edit(_("Parking canopy"), lambda p: made.append(canopies.add(p, spec, c["point"])))
            self.select("building", made[0])
        elif typ == "row":
            sf = self._subfield_at(c["start"])
            if sf is None:
                raise ValueError(_("A row is drawn in a sub-field: start it inside one."))
            change = manual.draw(self.project, sf.id, c["start"], c["end"], self.results.get(sf.id),
                                 east_west=c.get("tool") == "east_west")
            self._edit(_("Draw a row"), change)
        elif typ == "ridge":
            points = c["points"]
            b = ridge_building(self.project.buildings, points)
            if b is None:
                raise ValueError(_("A ridge belongs to a building: draw it inside one."))
            covering = b.roof.covering or roofs.DEFAULT_COVERING
            tilt = b.roof.tilt if b.roof.type in model.PITCHED and b.roof.tilt > 0 else roofs.proposed_tilt(covering)
            height = c.get("height")
            found = roofs.from_ridge(b.footprint, points, b.height, tilt, height)
            free = roofs.off_axis_pitches(b.footprint, points, b.height, height, tilt) if found.off_axis else None

            def ridge(p):
                building = p.building(b.id)
                r = building.roof
                if free is not None:                # R410: where it was drawn, not on the axis
                    r.type, r.edges, r.ridge_height, r.covering = "free", [], None, covering
                    r.free_pitches, r.joined, r.welds, r.detached = free, True, [], []
                    roof_vertices.settled(building, range(len(free)))
                    return
                r.type, r.edges, r.ridge_height, r.tilt, r.covering = found.kind, found.edges, height, tilt, covering
                r.free_pitches, r.welds, r.detached = [], [], []
            self._edit(_("Draw a ridge"), ridge)
            self.select("building", b.id)
        elif typ in ("row_resize", "row_append", "row_explode", "row_turn"):
            sfid, _sep, rid = c["oid"].partition("/")
            args = (self.project, sfid, rid)
            result = self.results.get(sfid)
            if typ == "row_resize":
                change = manual.resize(*args, c["point"], result)
            else:
                fn = {"row_append": manual.append, "row_explode": manual.explode, "row_turn": manual.turn}[typ]
                change = fn(*args, result)
            self._edit(_("Change a row"), change)
        elif typ == "module_turn":
            sfid, key = c["sfid"], c["key"]
            rid = self._rid(sfid, key)
            row = next((r for r in getattr(self.results.get(sfid), "rows", []) if r.id == rid), None)
            if row is None:
                return []
            if row.count != 1:
                self.select("row", f"{sfid}/{rid}")
                return []
            self._edit(_("Turn a module"), manual.turn(self.project, sfid, rid, self.results.get(sfid)))
        else:
            raise ValueError("Unknown plan command: " + typ)
        return [{"type": "changed", "command": typ}]

    def _subfield_at(self, point):
        return next((sf for sf in sorted(self.project.subfields, key=lambda s: s.id != self.selection[1])
                     if Polygon(sf.ring).buffer(1e-6).covers(Point(*point))), None)

    def _polygon(self, tool, ring, spec):
        ring = move.drawn_ring(ring)
        shape = Polygon(ring)
        if not shape.is_valid or shape.area < .5:
            raise ValueError(_("Too small to keep: draw it again."))
        b, pitch = move.host(self.project, ring)
        if tool == "building":
            oid = self.project.new_id("b")
            n = len(self.project.buildings) + 1
            if b is not None and Polygon(b.footprint).buffer(1e-6).covers(shape):
                # R352: drawn on a roof, a plant room standing on it: its base the roof there, 3 m high
                base = round(max(model.roof_z(b, ring)), 3)
                rooms = 1 + len(self.project.standing_on(b.id))
                self._edit(_("Draw a plant room"), lambda p: p.buildings.append(model.Building(
                    id=oid, name=_("Plant room {n}").format(n=rooms), footprint=ring, height=round(base + 3.0, 3),
                    base=base, on=b.id)))
            else:
                self._edit(_("Draw a building"), lambda p: p.buildings.append(model.Building(
                    id=oid, name=_("Building {n}").format(n=n), footprint=ring, height=6.0)))
        elif tool == "subfield":
            oid = self.project.new_id("s")
            n = len(self.project.subfields) + 1
            as_modules = spec.get("fill", "modules") != "area"

            def draw(p):
                # R523: with the project's defaults (module, mounting, gaps, pitch...), the fire bands if they ask
                sf = p.new_subfield(oid, _("Sub-field {n}").format(n=n), ring, b.id if b else None, pitch)
                p.add_subfield(sf)
                if as_modules:                  # R445: the sub-field is its modules, from the first click
                    manual.make_flush(p, sf)
            self._edit(_("Draw a sub-field"), draw)
        elif tool == "exclusion":
            oid = self.project.new_id("e")
            self._edit(_("Draw an exclusion"), lambda p: p.exclusions.append(model.ExclusionItem(
                id=oid, ring=ring, kind="skylight", building=b.id if b else None)))
        elif tool == "pitch":
            if b is None:
                raise ValueError(_("A pitch belongs to a building: draw it inside one."))
            eave = spec.get("eave") if spec.get("eave") is not None else b.height
            tilt = spec.get("tilt") if spec.get("tilt") is not None else roofs.proposed_tilt(b.roof.covering or roofs.DEFAULT_COVERING)
            fp = roofs.free_spec(ring, bool(spec.get("swapped")), eave, tilt, spec.get("ridge"))
            fp["ring"] = ring

            def add(p):
                roof = p.building(b.id).roof
                if roof.type != "free":
                    roof.type = "free"
                    roof.free_pitches, roof.welds, roof.detached = [], [], []
                roof.free_pitches.append(fp)
            self._edit(_("Draw a pitch"), add)
            tool, oid = "building", b.id
        else:
            raise ValueError("Unknown outline tool: " + tool)
        self.select(tool, oid)
        return [{"type": "changed", "command": "polygon", "kind": tool, "oid": oid}]

    def _split(self, oid):
        """«Split on the ridge» (R426): one undo, the largest part stays selected with the id it had."""
        change = move.split_on_pitches(self.project, oid)
        made = []
        self._edit(_("Split on the ridge"), lambda p: made.extend(change(p)))
        self.select("subfield", made[0])
        self.notice = _("Split in {n} sub-fields, each on its pitch: they move together.").format(n=len(made))
        return [{"type": "changed", "command": "split_pitches"}]

    def _apply_transform(self, c):
        kind, oid = c.get("kind", self._target()[0]), c.get("oid", self._target()[1])
        if self.phase == "plant" and kind not in self._allowed():
            raise ValueError(_("Move: click a module to turn its sub-field."))
        if self.phase == "modelling" and kind not in self._allowed():
            raise ValueError(_("Sub-fields and modules are changed in Plant."))
        mode = c.get("mode", "move")
        duplicate = c.get("copy", False)
        dx, dy = float(c.get("dx", 0)), float(c.get("dy", 0))
        degrees = float(c.get("degrees", 0))
        if not all(math.isfinite(v) for v in (dx, dy, degrees)):
            raise ValueError("Non-finite transform")
        if not duplicate and (abs(degrees) < 1e-9 if mode == "rotate" else math.hypot(dx, dy) < 1e-9):
            return []
        if kind in ("module", "row"):
            sfid, _sep, key = oid.partition("/")
            if duplicate or mode == "rotate":
                raise ValueError(_("a row turns with its sub-field; a module on its own turns with a double click"))
            fn = manual.move_module if kind == "module" else manual.translate
            change = fn(self.project, sfid, key, dx, dy, self.results.get(sfid))
        elif duplicate:
            change = (move.copy(self.project, kind, oid, about=(c["cx"], c["cy"]), degrees=degrees)
                      if mode == "rotate" else move.copy(self.project, kind, oid, dx, dy))
        else:
            change = (move.rotate(self.project, kind, oid, c["cx"], c["cy"], degrees)
                      if mode == "rotate" else move.translate(self.project, kind, oid, dx, dy))
        made = []
        before = getattr(self.session.subfield(oid), "pitch", None) if kind == "subfield" else None
        self._edit(_("Copy") if duplicate else _("Rotate") if mode == "rotate" else _("Move"),
                   lambda p: made.append(change(p)), ("nudge", kind, oid) if c.get("nudge") else None)
        if duplicate and made:
            self.select(kind, made[0])
        if kind == "subfield":
            self.notice = self._settled_note(made[0] if duplicate and made else oid, before)
        return [{"type": "changed", "command": "transform"}]

    def _settled_note(self, oid, before):
        """What a move of a sub-field did to its pitch, in the status bar: where it lies now, and astride what."""
        sf = self.session.subfield(oid)
        if sf is None:
            return ""
        lying = self._astride_note(oid)
        if lying:
            return lying
        b = self.project.building(sf.building)
        if b is None or sf.pitch == before:
            return ""
        index = b.pitch_index(sf.pitch)
        return _("Now on pitch {n}: its modules are laid on that plane.").format(n=(index or 0) + 1)

    _drop = staticmethod(clipboard.drop)

    # copy, cut, paste (R432), in the phase's rule

    def clip_target(self):
        """What Ctrl+C and Ctrl+X take: the whole object selected, in what the phase can take; or None."""
        kind, oid = self.selection
        if self.selected_module[0] or self.session.selected_many() or kind not in ("subfield", "building", "exclusion", "prop"):
            return None
        return (kind, oid) if kind in self.selectable() else None

    def can_paste(self):
        return self.clip is not None and self.clip.kind in self.selectable()

    def _take(self, cut):
        target = self.clip_target()
        if target is None:
            raise ValueError(_("Select a whole sub-field, building, exclusion or 3D object first (Esc goes up to it)."))
        clip = clipboard.take(self.project, *target)
        if cut:
            self._edit(_("Cut"), clipboard.cut(clip))
            undo = self.session.undo
            clip.cut_step = undo.steps[undo.index - 1] if undo.index else None
            self.select("site", "")
        self.clip = clip
        self.notice = _("Cut: Ctrl+V pastes it under the pointer.") if cut else _("Copied: Ctrl+V pastes it under the pointer.")
        return [{"type": "changed", "command": "cut"}] if cut else []

    def _start_paste(self):
        if self.clip is None:
            raise ValueError(_("Nothing to paste: Ctrl+C or Ctrl+X something first."))
        if not self.can_paste():
            raise ValueError(_("Sub-fields are pasted in Plant.") if self.clip.kind == "subfield" else
                             _("Buildings, exclusions and 3D objects are pasted in Modelling."))
        self.set_tool("paste")
        self._paste_preview()
        return []

    def _paste_preview(self):
        clip = self.clip
        self.preview = {"type": "paste", "rings": clipboard.rings(clip, self.pointer),
                        "refused": clipboard.refused(self.project, clip, self.pointer),
                        "where": clipboard.where(self.project, clip, self.pointer)}
        self._hint()

    def _paste(self, point):
        clip = self.clip
        if not self.can_paste():
            raise ValueError(_("Nothing to paste: Ctrl+C or Ctrl+X something first."))
        where = clipboard.where(self.project, clip, point)
        change = clipboard.paste(self.project, clip, point)     # refused with the reason: the tool stays in hand
        made = []
        self._edit(_("Paste"), lambda p: made.extend(change(p)))
        undo = self.session.undo
        if clip.cut_step is not None and undo.index >= 2 and undo.steps[undo.index - 2] is clip.cut_step:
            undo.join_last()
        clip.cut_step = None
        self.tool = "select"
        self.preview = {}
        self.select(clip.kind, made[0])
        self.notice = self._pasted_note(clip, made, where)
        return [{"type": "changed", "command": "paste"}]

    def _pasted_note(self, clip, made, where):
        if clip.kind == "exclusion" or clip.kind == "prop" or not clip.subfields:
            return _("Pasted.")
        filled = any(s.filled for s in clip.subfields)
        if clip.kind == "building":
            return _("Pasted with what stands on it; its modules are in no string.") if filled else _("Pasted.")
        said = _("Pasted {where}; its modules are laid again, in no string.") if filled else _("Pasted {where}.")
        note = said.format(where=where)
        lying = self._astride_note(made[0])
        return f"{note} {lying}" if lying else note

    def _astride_note(self, sfid):
        sf = self.session.subfield(sfid)
        lying = move.straddle(self.project, sf) if sf is not None else None
        if lying is None:
            return ""
        return _("{area} m² stand on another pitch and are computed on the plane of pitch {n}: "
                 "«Split on the ridge» makes one sub-field per pitch.").format(area=number(lying.other_area, 1),
                                                                                n=lying.index + 1)

    def _delete(self):
        if self.draft is not None:
            return []
        # R531, R532: modules selected are taken out first, also with Inverter open (before, Del deleted the string
        # chosen, or nothing when none was)
        if self.strings_mode and self.phase == "plant" and not self.swept:
            return self._delete_string(self.chosen_string)
        if self.tool != "select":
            return []
        if self.swept:
            by = {}
            for sfid, key in self.swept:
                by.setdefault(sfid, []).append(key)
            changes = [manual.delete_modules(self.project, sfid, keys, self.results.get(sfid)) for sfid, keys in by.items()]
            self._edit(_("Take modules out"), lambda p: [change(p) for change in changes])
            n = len(self.swept)
            self.swept = []
            self.select(*self.selection)
            self.notice = (_("One module taken out of the layout · Ctrl+Z puts it back") if n == 1 else
                           _("{n} modules taken out of the layout · Ctrl+Z puts them back").format(n=n))
            self._hint()
        elif self.session.selected_many():
            kind, things = self.selection[0], self.session.selected_many()
            self._edit(_("Delete objects"), lambda p: [self._drop(p, kind, oid) for oid in things])
            self.select("site", "")
        elif self.swept_things:
            things = list(self.swept_things)
            self._edit(_("Delete objects"), lambda p: [self._drop(p, k, oid) for k, oid in things])
            self.swept_things = []
            self.select("site", "")
        elif self.selected_module[0]:
            sfid, key = self.selected_module
            self._edit(_("Take a module out"), manual.delete_module(self.project, sfid, key, self.results.get(sfid)))
            self.select("subfield", sfid)
            self.notice = _("One module taken out of the layout · Ctrl+Z puts it back")
            self._hint()
        elif self.selection[0] == "row":
            sfid, _sep, rid = self.selection[1].partition("/")
            self._edit(_("Take the row away"), manual.remove(self.project, sfid, rid, self.results.get(sfid)))
            self.select("subfield", sfid)
        elif self.selection[0] in ("building", "subfield", "exclusion", "prop"):
            kind, oid = self.selection
            self._edit(_("Delete"), lambda p: self._drop(p, kind, oid))
            self.select("site", "")
        return [{"type": "changed", "command": "delete"}]

    def _outline_edit(self, c):
        kind, oid = c.get("kind", self.selection[0]), c.get("oid", self.selection[1])
        obj = self._object(self.project, kind, oid)
        if kind == "pitch":
            found = move._free_pitch(self.project, oid)
            ring = found[1]["ring"] if found else None
            attr = "ring"
        elif obj is not None:
            attr = "footprint" if kind == "building" else "path" if kind == "prop" else "ring"
            ring = getattr(obj, attr, None)
        else:
            ring = None
        if ring is None:
            raise ValueError(_("there is no such object to move"))
        new = copy.deepcopy(ring)
        if c["type"] == "side":
            new = sides.stretch(new, int(c["index"]), float(c["value"]))
        elif c["type"] == "side_shift":
            new = sides.shift(new, int(c["index"]), float(c["distance"]))
        elif c["type"] == "square":
            new, why = squaring.square(new)
            if why:
                return []
        elif c["type"] == "vertices":           # R356: more corners moved together
            dx, dy = (float(v) for v in c["delta"])
            for i in {int(i) for i in c["indices"]}:
                new[i] = [round(float(new[i][0]) + dx, 4), round(float(new[i][1]) + dy, 4)] + list(new[i][2:])
        else:
            new[int(c["index"])] = [round(float(v), 4) for v in c["point"]]
        if attr != "path" and (not Polygon(new).is_valid or Polygon(new).area < .5):
            raise ValueError(_("the outline would cross itself or vanish"))
        if kind == "subfield" and obj.flush and obj.manual:
            # R418: a sub-field that is its modules keeps them on their grid, as when a side is dragged (R445 B)
            self._edit(_("Change outline"), manual.reshape_to(self.project, oid, new, self.results.get(oid)))
            return [{"type": "changed", "command": c["type"]}]
        kept_azimuth = self._kept_azimuth(obj, new) if kind == "subfield" else None

        def put(p):
            if kind == "pitch":
                move._free_pitch(p, oid)[1]["ring"] = new
            else:
                setattr(self._object(p, kind, oid), attr, new)
            if kept_azimuth is not None:
                self._object(p, kind, oid).params["azimuth"] = kept_azimuth
        self._edit(_("Change outline"), put)
        return [{"type": "changed", "command": c["type"]}]

    def _add_vertices(self, c):
        """Vertices added on a side of a building, a sub-field or an exclusion (R356): one where the menu was opened
        (`point`) or those that divide the side in `parts`; one undo step."""
        kind, oid = c.get("kind", self.selection[0]), c.get("oid", self.selection[1])
        obj = self._object(self.project, kind, oid) if kind in ("building", "subfield", "exclusion") else None
        if obj is None:
            raise ValueError(_("vertices are added on a side of a building, a sub-field or an exclusion"))
        side = int(c["index"])
        attr = "footprint" if kind == "building" else "ring"
        new, count = sides.insert(getattr(obj, attr), side, parts=c.get("parts"), at=c.get("point"))

        def put(p):
            target = self._object(p, kind, oid)
            if kind == "building":
                target.vertices_added(side, new, count)
            else:
                target.ring = new
        self._edit(ngettext("Add a vertex", "Add {n} vertices", count).format(n=count), put)
        self.notice = ngettext("{n} vertex added on side {side}: drag it to change the outline.",
                               "{n} vertices added on side {side}: drag them to change the outline.",
                               count).format(n=count, side=side + 1)
        return [{"type": "changed", "command": c["type"]}]

    def _kept_azimuth(self, sf, ring):
        """The azimuth an area laid automatically keeps when its outline changes (R418): with the automatic azimuth
        the rows follow the outline's smallest rectangle, so a vertex dragged could turn them all; then the azimuth
        they have now is written, and the rows stay on their side. None when nothing would turn."""
        if sf.manual or sf.params.get("azimuth") is not None:
            return None
        params, surface = self.project.fill_params(sf), self.project.surface_of(sf)
        now = layout.row_azimuth(Polygon(sf.ring).buffer(0), surface, params)
        after = layout.row_azimuth(Polygon(ring).buffer(0), surface, params)
        return round(now, 2) if abs((after - now + 180.0) % 360.0 - 180.0) > 0.01 else None

    def runs(self):
        return copy.deepcopy((self.project.energy.get("strings") or {}).get("runs") or [])

    def wiring_scene(self, mpp, **options):
        from .plan_wiring import WiringScene
        if self._wiring_scene is None:
            self._wiring_scene = WiringScene()
        return self._wiring_scene.build(self, mpp, **options)

    def owner(self, sfid, key):
        ref = f"{sfid}/{key}"
        return next((i for i, r in enumerate(self.runs()) if ref in r.get("modules", [])), -1)

    def start_draft(self, unit=1, mppt=1, modules=None, index=-1):
        self.draft_target = (unit, mppt, index)
        self.draft = list(modules or [])
        self.tool = "string"
        self.preview = {"type": "string", "modules": list(self.draft)}
        self._hint()

    def _put_runs(self, label, runs):
        self._edit(label, lambda p: p.energy.__setitem__("strings", plant.touched(p.energy.get("strings"), runs)))

    def finish_draft(self):
        if self.draft is None:
            return []
        keys = [f"{sfid}/{key}" for sfid, key in self.draft]
        unit, mppt, index = self.draft_target
        runs = self.runs()
        self.draft = self.draft_target = None
        self.preview = {}
        if 0 <= index < len(runs):
            runs, _robbed = plant.set_run(runs, index, keys)
            chosen = index
        elif keys:
            runs, chosen = plant.new_run(runs, unit, mppt, keys)
        else:
            self.tool = "select"
            self._hint()
            return []
        kept = [i for i, r in enumerate(runs) if r.get("modules")]
        self.chosen_string = kept.index(chosen) if chosen in kept else -1
        self._put_runs(_("Draw a string"), runs)
        self.tool = "select"
        self._hint()
        return [{"type": "changed", "command": "string"}]

    def _delete_string(self, index):
        runs = self.runs()
        if 0 <= index < len(runs):
            self._put_runs(_("Delete a string"), plant.delete_run(runs, index))
            self.chosen_string = -1
            return [{"type": "changed", "command": "erase_string"}]
        return []

    def _erase(self, tool, sfid, key):
        runs = self.runs()
        index = self.owner(sfid, key)
        if index < 0:
            raise ValueError(_("This module is in no string: there is nothing to delete here."))
        if tool == "erase_string":
            return self._delete_string(index)
        unit = runs[index].get("inverter", 0)
        if not unit:
            raise ValueError(_("The string of this module is on no inverter: «Delete a string» takes it away."))
        strings = tool == "erase_inverter_strings"
        entries, after = plant.remove_unit(self.project.energy, runs, unit, strings)
        if entries is None and not strings:
            raise ValueError(_("This is the inverter Meridiana sizes by itself: there is none in the list to delete."))

        def put(p):
            if entries is not None:
                p.energy.pop("inverter", None)
                p.energy.pop("inverter_count", None)
                if entries:
                    p.energy["inverters"] = entries
                else:
                    p.energy.pop("inverters", None)
            p.energy["strings"] = plant.touched(p.energy.get("strings"), after)
        self._edit(_("Delete inverter {n}").format(n=unit), put)
        self.chosen_string = -1
        return [{"type": "changed", "command": tool}]
