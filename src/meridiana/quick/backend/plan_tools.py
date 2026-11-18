"""Pure drawing gestures. Commands describe edits; the session adapter applies them.

All coordinates are East/North metres. Snap references and project context are read
only; no gesture modifies a project. Preview dictionaries are suitable for QML.
"""
from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import asdict

from shapely.geometry import Point, Polygon

from ... import manual, roofs, sides
from ...i18n import ngettext, number, pgettext
from ...snapping import EXACT, Guide, Snap, Snapper, ortho
from .plan_locale import _

def ridge_building(buildings, points):
    """The building a ridge drawn through `points` belongs to (R410). Of those under its first point, the one that holds
    the whole ridge, and of those the smallest: a building drawn over or inside a larger one is the one meant. The first
    under the first point alone took the larger one below: the ridge went to another building, which was selected
    (06/11/2026)."""
    if not points:
        return None
    first = Point(points[0])
    under = [b for b in buildings if len(b.footprint) >= 3 and Polygon(b.footprint).buffer(1e-6).covers(first)]
    if not under:
        return None
    whole = [b for b in under if all(Polygon(b.footprint).buffer(1e-6).covers(Point(q)) for q in points)]
    return min(whole or under, key=lambda b: Polygon(b.footprint).area)


DRAWING = {"building", "pitch", "ridge", "subfield", "exclusion", "prop_line", "prop_series"}
ROWS = {"row", "east_west"}
# R375: prop places one object at a click (and stays, with `repeat`), prop_series a row of them between two clicks,
# prop_group a small family round one click
TOOLS = DRAWING | ROWS | {"select", "measure", "prop", "canopy", "prop_group"}
PITCH_FIELDS = ("depth", "tilt", "ridge", "eave")


def parse_length(text):
    """Accept decimal comma and an optional metre suffix, never NaN or infinity."""
    try:
        value = float(text.strip().lower().removesuffix("m").strip().replace(",", "."))
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) else None


def _variant(value):
    """Nested tuples are PyObject wrappers in QVariantMap, not QML coordinate arrays."""
    if isinstance(value, dict):
        return {key: _variant(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_variant(item) for item in value]
    return value


class DrawingMachine:
    def __init__(self, project=None, *, metres_per_pixel=0.02):
        self.project = project
        self.metres_per_pixel = metres_per_pixel
        self.snapper = Snapper()
        self.snaps_on = True
        self.orthogonal = False
        self.rect_mode = False
        self.tool = "select"
        self.options = {}
        self.pointer = None
        self.raw_pointer = None
        self.snap = None
        self.points = []
        self.typed = ""
        self.lock_direction = None
        self.pitch_points = False
        self.pitch_card = {}
        self.ridge_height = None
        self._ridge_cache = None
        self._row_cache = None
        self._row_base = {}
        self._grid_cache = None
        self.results = {}
        self.selected_subfield = ""
        self.error = ""
        self._reset()
        self.set_project(project)

    def set_project(self, project):
        self.project = project
        self._row_cache = None
        self._row_base = {}
        self._grid_cache = None
        segments = []
        if project is not None:
            rings = [b.footprint for b in project.buildings]
            rings += [p.ring for b in project.buildings for p in b.pitches()]
            rings += [s.ring for s in project.subfields] + [e.ring for e in project.exclusions]
            for ring in rings:
                pts = [tuple(p) for p in ring]
                segments.extend(zip(pts, pts[1:] + pts[:1], strict=True))
        self.set_references(segments)

    def set_results(self, results):
        self.results = results
        self._row_cache = None
        self._row_base = {}

    def set_references(self, segments, points=None):
        self.snapper.set_references(segments, points)
        return []

    def _reset(self):
        self.points = []
        self.typed = ""
        self.snap = None
        self.lock_direction = None
        self.snapper.reset()
        self.pitch_card = {"field": "depth", "tilt": None, "ridge": None, "eave": None, "swapped": False}
        self.ridge_height = None
        self.error = ""

    def set_tool(self, tool, **options):
        if tool not in TOOLS:
            raise ValueError(f"Unknown drawing tool: {tool}")
        self.tool = tool
        self.options = deepcopy(options)
        self.pitch_points = False
        self._reset()
        return []

    @property
    def rectangle(self):
        return (not self.pitch_points if self.tool == "pitch" else self.rect_mode) and self.tool != "ridge"

    def set_rectangle(self, enabled):
        if self.tool == "pitch":
            self.pitch_points = not enabled
        else:
            self.rect_mode = bool(enabled)
        return []

    @property
    def state(self):
        if self.typed:
            return "typing"
        if self.tool == "measure" and len(self.points) == 2:
            return "measured"
        if not self.points:
            return "idle"
        if self.rectangle and len(self.points) == 2:
            return "depth"
        return "drawing"

    @property
    def hint(self):
        if self.error:
            return self.error
        if self.tool == "select":
            return _("Click: select · Delete: remove · Esc: container")
        if self.typed:
            action = (_("Enter: apply value") if self.tool in {"pitch", "ridge"}
                      else _("Enter: apply length"))
            return action + _(" · Backspace: delete digit · Esc: clear")
        n = len(self.points)
        if self.tool in {"prop", "canopy", "prop_group"}:
            return _("Click: position · Esc: exit")
        if self.tool == "prop_series":
            return _("Click: row end · Esc: cancel") if n else _("Click: row start · Esc: exit")
        if self.tool == "measure":
            if n == 2:
                return _("Click: new measurement · Esc: clear measurement")
            return (_("Click: second point · Esc: cancel") if n else _("Click: first point · Esc: exit"))
        if self.tool in ROWS:
            return (_("Click: row end · Number+Enter: length · Esc: cancel") if n
                    else _("Click: row start · Esc: exit"))
        if self.tool == "ridge":
            if not n:
                return _("Click: first ridge point inside a building · Esc: exit")
            if n == 1:
                return _("Click: ridge end · Number: height · Esc: cancel")
            return _("Enter: finish ridge · Click: another point · Esc: cancel")
        if self.tool == "pitch" and not self.pitch_points:
            if not n:
                return _("Click: eave start · R: corners · Esc: exit")
            if n == 1:
                return _("Click: eave end · Number: length · Esc: cancel")
            if self.pitch_card["field"] != "depth":
                return _("Number: field value · Up/Down: field · Tab: swap · Esc: cancel")
            return _("Click: depth · Up/Down: field · Tab: swap · Esc: cancel")
        if self.rectangle:
            return (_("Click: first side point · R: polygon · Esc: exit") if not n else
                    _("Click: side end · Number: length · Esc: cancel") if n == 1 else
                    _("Click: depth · Number+Enter: depth · Esc: cancel"))
        if not n:
            return _("Click: first corner · R: rectangle · Esc: exit")
        if n >= (2 if self.tool == "prop_line" else 3):
            return _("Enter: finish · Click: another corner · Backspace: back · Esc: cancel")
        return _("Click: next corner · Number: length · Backspace: back · Esc: cancel")

    def move(self, point, modifiers=frozenset()):
        cursor = tuple(map(float, point))
        if not all(math.isfinite(p) for p in cursor):
            return []
        self.raw_pointer = cursor
        chain = self.points[:1] if self.tool == "measure" else self.points
        free = ("ctrl" in modifiers and "alt" not in modifiers) or not self.snaps_on
        if "shift" not in modifiers:
            self.lock_direction = None
        if self.lock_direction and chain:
            last = chain[-1]
            u = self.lock_direction
            t = sum((cursor[i] - last[i]) * u[i] for i in (0, 1))
            target = (last[0] + t * u[0], last[1] + t * u[1])
            self.snap = Snapper._measure(Snap(target, "direction", [Guide(last, target, "polar", "Shift")]), chain)
        else:
            self.snap = self.snapper.snap(cursor, chain, self.metres_per_pixel, free=free)
            if self.orthogonal and chain and self.tool in DRAWING and self.snap.kind not in EXACT:
                target = ortho(chain, cursor)
                self.snap = Snapper._measure(Snap(target, "direction", [Guide(chain[-1], target, "polar", "F8")]), chain)
            if self.rectangle and len(chain) == 2 and self._depth(self.snap.point) < 1e-6:
                self.snap = self.snapper.snap(cursor, chain, self.metres_per_pixel, free=True)
        self.pointer = self.snap.point
        return []

    def click(self, point, modifiers=frozenset()):
        self.error = ""
        if not all(math.isfinite(float(p)) for p in point):
            return []
        self.move(point, modifiers)
        p = self.pointer
        if p is None or self.tool == "select":
            return []
        if self.tool in {"prop", "canopy", "prop_group"}:
            options = deepcopy(self.options)
            if self.tool == "prop":
                command = {"type": "prop", "kind": options.get("kind", "tree"), "point": p}
                if options.get("asset"):
                    command["asset"] = options["asset"]
            elif self.tool == "prop_group":
                command = {"type": "prop_group", "kind": options.get("kind", "tree"), "point": p, "options": options}
            else:
                command = {"type": "canopy", "point": p, "spec": deepcopy(options.get("spec", {}))}
            if self.tool == "prop" and options.get("repeat"):
                return [command]            # R375 «Choose and place»: a copy at every click, Esc ends
            self.set_tool("select")
            return [command, {"type": "tool", "tool": "select"}]
        if self.tool == "prop_series":
            if self.points and math.dist(p, self.points[0]) > 1e-6:
                self.points.append(p)
                return self.finish()
            self.points = [p]
            return []
        if self.tool == "measure":
            self.points = [p] if len(self.points) != 1 else [self.points[0], p]
            return []
        if self.typed:
            return self._apply_typed()
        if self.tool in ROWS:
            if self.points and math.dist(p, self.points[0]) > 1e-6:
                return self._end_row(p)
            if not self.points:
                self.points = [p]
                self.snapper.reset()
            return []
        if self.tool == "ridge":
            if self.points and math.dist(p, self.points[-1]) <= 6 * self.metres_per_pixel:
                return self.finish()
            if not self.points and self._building_at(p) is None:
                self.error = _("A ridge belongs to a building: click inside one.")
                return []
            self.points.append(p)
            building = self._ridge_building()
            if len(self.points) == 2 and building is not None and len(building.footprint) == 4:
                return self.finish()
            return []
        if self.rectangle and len(self.points) == 2:
            if self._depth(p) > .05:
                return self.finish(self._rectangle(p))
            return []
        if len(self.points) >= 3 and math.dist(p, self.points[0]) <= 10 * self.metres_per_pixel:
            return self.finish()
        if not self.points or math.dist(p, self.points[-1]) > 1e-6:
            self.points.append(p)
        return []

    def double_click(self, point, modifiers=frozenset()):
        if self.tool == "subfield" and len(self.points) <= 2:
            self._reset()
            return [{"type": "whole", "tool": "subfield", "point": tuple(map(float, point)),
                     "spec": {"fill": self.options.get("fill", "modules")}}]
        return self.finish()

    def finish(self, ring=None):
        points = list(self.points if ring is None else ring)
        minimum = 2 if self.tool in {"ridge", "prop_line", "prop_series"} else 3
        if self.tool not in DRAWING or len(points) < minimum:
            return []
        if self.tool == "ridge":
            command = {"type": "ridge", "points": points, "height": self.ridge_height}
        elif self.tool == "prop_line":
            command = {"type": "prop_line", "kind": self.options.get("kind", "hedge"), "points": points}
            if self.options.get("asset"):
                command["asset"] = self.options["asset"]
        elif self.tool == "prop_series":
            command = {"type": "prop_series", "kind": self.options.get("kind", "tree"), "points": points,
                       "options": deepcopy(self.options)}
        else:
            poly = Polygon(points)
            if not poly.is_valid or poly.area < .5:
                self.error = _("The outline crosses itself or is too small to keep.")
                return []
            if self.tool == "pitch":
                command = {"type": "pitch", "ring": points, "spec": {k: self.pitch_card[k]
                           for k in ("swapped", "tilt", "ridge", "eave")}}
            else:
                command = {"type": "polygon", "tool": self.tool, "ring": points}
                if self.tool == "subfield":
                    command["spec"] = {"fill": self.options.get("fill", "modules")}
        leave = self.tool in {"prop_line", "prop_series"}
        self._reset()
        if leave:
            self.set_tool("select")
        return [command] + ([{"type": "tool", "tool": "select"}] if leave else [])

    def _end_row(self, end):
        command = {"type": "row", "tool": self.tool, "start": self.points[0], "end": end}
        self._reset()
        return [command]

    def key(self, key, text="", modifiers=frozenset()):
        self.error = ""
        if key in {"F8", "Orthogonal"}:
            self.orthogonal = not self.orthogonal
            return self.move(self.raw_pointer, modifiers) if self.raw_pointer else []
        if key in {"F3", "Snaps"}:
            self.snaps_on = not self.snaps_on
            return self.move(self.raw_pointer, modifiers) if self.raw_pointer else []
        if key == "Shift" and self.points and self.pointer:
            d = math.dist(self.points[-1], self.pointer)
            if d > 1e-9:
                self.lock_direction = tuple((self.pointer[i] - self.points[-1][i]) / d for i in (0, 1))
            return []
        if key in {"Escape", "Esc"}:
            if self.typed:
                self.typed = ""
            elif self.points or self.ridge_height is not None or self._roof_draft_open():
                self._reset()
                self.pitch_points = False
            elif self.tool != "select":
                self.set_tool("select")
                return [{"type": "tool", "tool": "select"}]
            return []
        if key == "Backspace":
            if self.typed:
                self.typed = self.typed[:-1]
            elif self.points:
                self.points.pop()
            return []
        if key.upper() == "R" and not modifiers and self.tool in DRAWING:
            return self.set_rectangle(not self.rectangle)
        if self.tool == "pitch" and self.points:
            if key in {"Tab", "Backtab"}:
                self.pitch_card["swapped"] = not self.pitch_card["swapped"]
                return []
            if len(self.points) >= 2 and key in {"Up", "Down"}:
                index = PITCH_FIELDS.index(self.pitch_card["field"]) + (1 if key == "Down" else -1)
                self.pitch_card["field"] = PITCH_FIELDS[index % 4]
                self.typed = ""
                return []
        if key in {"Enter", "Return"}:
            if self.typed:
                return self._apply_typed()
            if self.tool == "pitch" and self.rectangle and len(self.points) == 2 and self.pointer:
                return self.finish(self._rectangle(self.pointer)) if self._depth(self.pointer) > .05 else []
            return self.finish()
        if self.points and text and all(c in "0123456789,.;-%" for c in text):
            if self.tool in DRAWING | ROWS:
                self.typed += text
        return []

    def _roof_draft_open(self):
        return self.pitch_points or self.pitch_card["swapped"] or any(
            self.pitch_card[k] is not None for k in ("tilt", "ridge", "eave"))

    def _typed_target(self):
        parts = self.typed.replace(",", ".").split(";")
        length = parse_length(parts[0])
        if len(parts) > 2 or length is None or length <= 0:
            return None
        angle = parse_length(parts[1]) if len(parts) == 2 else None
        if len(parts) == 2 and angle is None:
            return None
        last = self.points[-1]
        target = self.pointer or last
        if angle is not None:
            theta = (math.atan2(last[1] - self.points[-2][1], last[0] - self.points[-2][0]) + math.radians(angle)
                     if len(self.points) >= 2 else math.radians(90 - angle))
            target = (last[0] + math.cos(theta), last[1] + math.sin(theta))
        elif math.dist(target, last) < 1e-9:
            target = ((2 * last[0] - self.points[-2][0], 2 * last[1] - self.points[-2][1])
                      if len(self.points) >= 2 else (last[0] + 1, last[1]))
        distance = math.dist(target, last)
        return (last[0] + (target[0] - last[0]) / distance * length,
                last[1] + (target[1] - last[1]) / distance * length)

    def _apply_typed(self):
        if self.tool == "ridge":
            value = parse_length(self.typed)
            building = self._ridge_building()
            eave = building.height if building else 0
            if value is None or value <= eave + .001:
                self.error = _("The ridge must stand above the eave.")
                return []
            self.ridge_height, self.typed = value, ""
            return self.finish()
        if self.tool == "pitch" and len(self.points) >= 2 and self.pitch_card["field"] != "depth":
            return self._write_pitch()
        target = self._typed_target()
        if target is None:
            self.error = _("Enter a positive length, optionally followed by ;angle.")
            return []
        if self.tool in ROWS:
            return self._end_row(target)
        if self.rectangle and len(self.points) == 2:
            depth = parse_length(self.typed.split(";")[0])
            ring = self._rectangle(self.pointer or self.points[-1], depth)
            self.typed = ""
            return self.finish(ring)
        self.points.append(target)
        self.typed = ""
        return []

    def _write_pitch(self):
        field = self.pitch_card["field"]
        percent = self.typed.endswith("%")
        value = parse_length(self.typed.rstrip("%"))
        if value is None:
            self.error = _("Enter a valid number.")
            return []
        # A submitted numeric field is consumed even when its geometric range is
        # refused. The next value replaces it, as in the Widgets pitch card.
        self.typed = ""
        if field == "tilt":
            value = roofs.slope_from_percent(value) if percent else value
            if not 0 <= value <= 80:
                self.error = _("The slope goes from 0 to 80°.")
                return []
            self.pitch_card["tilt"], self.pitch_card["ridge"] = value, None
        elif field == "ridge":
            values = self.pitch_values()
            building = self._building_at(self.points[0])
            eave = values["eave"] if values else (building.height if building else 0)
            if value <= eave + .001:
                self.error = _("The ridge must stand above the eave.")
                return []
            self.pitch_card["ridge"] = value
        elif field == "eave":
            if not 0 <= value <= 1000:
                self.error = _("The eave height goes from 0 to 1000 m.")
                return []
            self.pitch_card["eave"] = value
        self.typed = ""
        return []

    def _building_at(self, point):
        if self.project is None or point is None:
            return None
        here = Point(point)
        return next((b for b in self.project.buildings if len(b.footprint) >= 3
                     and Polygon(b.footprint).buffer(1e-6).contains(here)), None)

    def _ridge_building(self):
        return ridge_building(self.project.buildings if self.project is not None else [], self.points)

    def _rectangle(self, point, depth=None):
        a, b = self.points[:2]
        length = math.dist(a, b) or 1
        nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
        h = (point[0] - b[0]) * nx + (point[1] - b[1]) * ny
        if depth is not None:
            h = math.copysign(abs(depth), h if abs(h) > 1e-9 else 1)
        return [a, b, (b[0] + nx * h, b[1] + ny * h), (a[0] + nx * h, a[1] + ny * h)]

    def _depth(self, point):
        a, b = self.points[:2]
        return abs((point[0] - a[0]) * (b[1] - a[1]) - (point[1] - a[1]) * (b[0] - a[0])) / (math.dist(a, b) or 1)

    def _preview_ring(self):
        if not self.points:
            return []
        target = self.pointer
        if self.typed and self.tool != "ridge" and (self.tool != "pitch" or self.pitch_card["field"] == "depth"):
            target = self._typed_target() or target
        if self.rectangle and len(self.points) == 2 and target:
            depth = parse_length(self.typed.split(";")[0]) if self.typed and self.pitch_card["field"] == "depth" else None
            return self._rectangle(target, depth)
        return list(self.points) + ([target] if target and math.dist(target, self.points[-1]) > 1e-6 else [])

    def pitch_values(self, ring=None):
        ring = self._preview_ring() if ring is None else ring
        if len(ring) < 3:
            return None
        b = self._building_at(ring[0])
        card = self.pitch_card
        eave = card["eave"] if card["eave"] is not None else (b.height if b else 0)
        tilt = card["tilt"] if card["tilt"] is not None else roofs.proposed_tilt(
            (b.roof.covering if b else "") or roofs.DEFAULT_COVERING)
        try:
            spec = roofs.free_spec(ring, card["swapped"], eave, tilt, card["ridge"])
        except ValueError:
            spec = roofs.free_spec(ring, card["swapped"], eave, tilt)
        return {"depth": roofs.free_depth(ring, spec["eave_side"]), "tilt": spec["tilt"], "eave": eave,
                "eave_side": spec["eave_side"], "ridge": roofs.free_ridge(ring, spec["eave_side"], eave, spec["tilt"]),
                "field": card["field"], "spec": {k: card[k] for k in ("swapped", "tilt", "ridge", "eave")}}

    def ridge_values(self):
        b = self._building_at(self.points[0] if self.points else self.pointer)
        if b is None:
            return None
        key = b.geometry_key()
        if self._ridge_cache is None or self._ridge_cache[0] != key:
            self._ridge_cache = (key, roofs.ridge_run(b.footprint))
        value = self.ridge_height
        if value is None:
            value = b.height + self._ridge_cache[1] * math.tan(math.radians(
                roofs.proposed_tilt(b.roof.covering or roofs.DEFAULT_COVERING)))
        return {"ridge": value, "eave": b.height, "typed": self.ridge_height is not None, "sides": len(b.footprint)}

    def grid_values(self, ring):
        """The modules a sub-field drawn as modules (R445) would be made of inside `ring`, their plan corners: the
        designer sees them lay as he draws. From the core's grid, kept until the ring changes by a centimetre."""
        if self.project is None or self.tool != "subfield" or self.options.get("fill") == "area" or len(ring) < 3:
            return None
        # the defaults the sub-field is drawn with (R523) are in the key: changed, the modules lay again
        key = (tuple((round(x, 2), round(y, 2)) for x, y in ring), repr(sorted(self.project.layout_defaults.items())))
        if self._grid_cache is not None and self._grid_cache[0] == key:
            return self._grid_cache[1]
        out = {"quads": [], "count": 0}
        from ... import manual, move
        ring = move.drawn_ring(ring)            # R551: the ring the drawing keeps (plan_edit._polygon), to 0.1 mm
        shape = Polygon(ring)
        if shape.is_valid and shape.area >= .5:
            b, pitch = move.host(self.project, ring)
            # R523: the sub-field the drawing will make, with the project's defaults: the preview is the layout
            sf = self.project.new_subfield("_draft", "", ring, b.id if b else None, pitch)
            try:
                rows = manual.grid(self.project, sf)
                quads = manual.corners(self.project, sf, rows)
                out = {"quads": quads, "count": len(quads)}
            except ValueError as error:
                out["error"] = str(error)
        self._grid_cache = (key, out)
        return out

    def row_values(self, points):
        """The core's actual modules, cached until the row endpoint or project changes."""
        if self.project is None or len(points) != 2:
            return None
        start, end = points
        key = (self.tool, tuple(start), tuple(end), self.selected_subfield)
        if self._row_cache is not None and self._row_cache[0] == key:
            return self._row_cache[1]
        sf = next((s for s in sorted(self.project.subfields, key=lambda s: s.id != self.selected_subfield)
                   if Polygon(s.ring).buffer(1e-6).covers(Point(start))), None)
        result = {"quads": [], "bad": True, "count": 0}
        if sf is not None and sf.filled and not sf.manual and self.results.get(sf.id) is None:
            # The session's worker owns automatic layouts, never a pointer event.
            result["pending"] = True
            self._row_cache = (key, result)
            return result
        if sf is not None:
            try:
                if sf.id not in self._row_base:
                    self._row_base[sf.id] = manual.rows_now(self.project, sf, self.results.get(sf.id))
                params = manual.east_west_params(self.project, sf) if self.tool == "east_west" else None
                row = manual.line_row(self.project, sf, start, end, self._row_base[sf.id], params=params)
                quads = manual.corners(self.project, sf, [row], params)
                result = {"quads": quads, "count": len(quads), "bad": manual.trouble(self.project, sf, [row], params)}
            except ValueError as error:
                result["error"] = str(error)
        self._row_cache = (key, result)
        return result

    def _card(self, preview):
        anchor = self.pointer
        lines = []
        if self.tool == "pitch" and preview["pitch"]:
            now = preview["pitch"]
            values = {"depth": (_("Depth"), _("{v} m").format(v=number(now["depth"]))),
                      "tilt": (_("Slope"), _("{d}° ({p} %)").format(d=number(now["tilt"], 1),
                               p=number(math.tan(math.radians(now["tilt"])) * 100, 0))),
                      "ridge": (_("Ridge height"), _("{v} m").format(v=number(now["ridge"]))),
                      "eave": (_("Eave height"), _("{v} m").format(v=number(now["eave"])))}
            lines = [pgettext("roof", "Pitch") + (" · " + _("eave and ridge swapped") if self.pitch_card["swapped"] else "")]
            for field, (label, value) in values.items():
                active = field == now["field"]
                shown = self.typed + "_" if active and self.typed else value
                lines.append(("→ " if active else "   ") + label + ": " + shown)
            lines.append(_("↑↓ row · Tab eave ↔ ridge · Enter done"))
        elif self.tool == "ridge" and preview["ridge"]:
            now = preview["ridge"]
            value = self.typed + "_" if self.typed else _("{v} m").format(v=number(now["ridge"]))
            lines = [_("Ridge"), _("Ridge height: {v}").format(v=value) +
                     ("" if now["typed"] or self.typed else " " + _("(proposed)")),
                     _("Eave height: {v} m").format(v=number(now["eave"])), _("type the ridge height · Enter done")]
        elif self.tool in ROWS and len(preview["points"]) == 2:
            anchor = preview["points"][-1]
            lines = [_("{length} m").format(length=number(preview["length"] or 0.0))]
            count = preview["row"]["count"] if preview["row"] else 0
            if not (preview["row"] or {}).get("pending"):
                lines.append(ngettext("{n} module", "{n} modules", count).format(n=count))
            if self.typed:
                lines.insert(0, _("length: {value}_").format(value=self.typed))
        elif self.tool == "measure" and len(self.points) == 2:
            anchor = self.points[-1]
            lines = [_("{length} m").format(length=number(preview["length"] or 0.0))]
        elif self.points and self.tool in DRAWING | {"measure"}:
            if preview.get("modules") and preview["modules"]["count"]:
                lines.append(ngettext("{n} module", "{n} modules", preview["modules"]["count"]).format(
                    n=preview["modules"]["count"]))
            if preview["length"]:
                lines.append(_("{length} m").format(length=number(preview["length"])))
                lines.append(_("direction {bearing}° from North").format(bearing=number(preview["bearing"], 1)))
            if preview["turn"] is not None:
                lines.append(_("turn {turn}°").format(turn=number(abs(preview["turn"]), 1)))
            if self.typed:
                lines.insert(0, _("length: {value}_").format(value=self.typed))
        return {"anchor": anchor, "lines": lines}

    @property
    def preview(self):
        ring = self._preview_ring() if self.tool in DRAWING else []
        points = list(self.points)
        if self.tool == "measure" and len(points) == 1 and self.pointer:
            points.append(self.pointer)
        if self.tool in ROWS and points and self.pointer:
            points.append((self._typed_target() if self.typed else None) or self.pointer)
        measured = Snapper._measure(Snap(points[-1], "free"), points[:1]) if len(points) == 2 else self.snap
        out = {"tool": self.tool, "state": self.state, "points": points, "ring": ring,
                "pointer": self.pointer, "snap": self.snap.kind if self.snap else "", "typed": self.typed,
                "guides": [asdict(g) for g in self.snap.guides] if self.snap else [],
                "length": measured.length if measured else None, "bearing": measured.bearing if measured else None,
                "turn": self.snap.turn if self.snap else None, "area": self.snap.area if self.snap else None,
                "side_lengths": sides.lengths(ring) if len(ring) >= 3 and self.tool != "prop_line" else [],
                "pitch": self.pitch_values(ring) if self.tool == "pitch" else None,
                "ridge": self.ridge_values() if self.tool == "ridge" else None, "hint": self.hint,
                "modules": self.grid_values(ring) if self.tool == "subfield" and len(ring) >= 3 else None,
                "rectangle": self.rectangle, "row": self.row_values(points) if self.tool in ROWS else None}
        out["card"] = self._card(out)
        return _variant(out)
