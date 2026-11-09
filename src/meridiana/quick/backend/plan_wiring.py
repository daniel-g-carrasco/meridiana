"""Pure string graphics shared with the Widgets router, R57/R117/R134/R184/R186/R496.

Objects have scene coordinates (East, minus North). Labels and dots expose
East/North centres and pixel offsets, for text that does not scale with the map.
The renderer owns font measurement and overlap rejection of string name chips.

The scene is built once for a given state and kept (R496): while the pointer moves only the elastic band from the
last module of the draft to the pointer changes, and it is returned apart (`band`), so the plan does not rebuild
the strings' layers at every move. A jump between modules that are not next to each other is a thin dashed arc over
the modules it passes, with an arrowhead where it lands (R496).
"""
from __future__ import annotations

import math
import zlib

from ... import string_paths, theme_colors
from ...energy import faces, optimizers, plant

JUMP_ARC_STEPS = 14        # points of the arc of a direct jump


def number_indices(points, mpp):
    """The exact Widgets thinning rule, including the first and last module."""
    gaps = sorted(math.dist(a, b) for a, b in zip(points, points[1:], strict=False))
    spacing = gaps[len(gaps) // 2] / mpp if gaps else 99.0
    step = 1 if spacing >= 20 else 5 if spacing * 5 >= 24 else 10
    return [n for n in range(1, len(points) + 1) if n in (1, len(points)) or n % step == 0]


def jump_arc(a, b, size):
    """The arc of a direct jump from `a` to `b`: it bulges to the left of its direction by a quarter of its length,
    at most two module sizes, so it rises over the modules it passes instead of running through their rows."""
    length = math.dist(a, b)
    if length < 1e-9:
        return [tuple(a), tuple(b)]
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    bulge = min(length * .25, 2.0 * size)
    cx, cy = (a[0] + b[0]) / 2 - uy * bulge * 2, (a[1] + b[1]) / 2 + ux * bulge * 2    # control point of the Bezier
    out = []
    for k in range(JUMP_ARC_STEPS + 1):
        t = k / JUMP_ARC_STEPS
        out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t * t * b[0],
                    (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t * t * b[1]))
    return out


def level_of(pixels):
    """How much the strings can say at this scale: `near` names, numbers and dots; `mid` names and lines; `far` a
    coloured disc for each string and one notice for each inverter (R496, the plan zoomed out)."""
    return "near" if pixels >= 14 else "mid" if pixels >= 6 else "far"


class WiringScene:
    def __init__(self):
        self.signature = None
        self.router = None
        self.index = {}
        self.refs = []
        self._optimizer_key = None
        self._optimizer_paths = []
        self._key = None
        self._scene = None
        self._routing_key, self._routed = None, ([], [])
        self.builds = 0

    def _optimizer_groups(self, run, order, per):
        try:
            return optimizers.module_groups(order, per, run.get("optimizer_group_sizes") or None)
        except ValueError:      # a partition of before: the plain one, the checks say what is wrong
            return optimizers.module_groups(order, per)

    def _optimizer_batches(self, key, drawn):
        """The symbols and the cables as native paths by colour, joined once while nothing changes (R424): `drawn` is
        [(colour, units, groups)]; no item for each module, whatever their number."""
        if key == self._optimizer_key:
            return self._optimizer_paths
        squares, cables = {}, {}
        centres = self.router.centres
        for colour, units, groups in drawn:
            for (x, y, ux, uy, side), group in zip(units, groups, strict=True):
                ax, ay, bx, by = ux * side / 2, uy * side / 2, -uy * side / 2, ux * side / 2
                corners = ((x - ax - bx, y - ay - by), (x + ax - bx, y + ay - by), (x + ax + bx, y + ay + by), (x - ax + bx, y - ay + by))
                squares.setdefault(colour, []).append('M' + ' L'.join(f'{cx:.6g},{-cy:.6g}' for cx, cy in corners) + ' Z')
                cables.setdefault(colour, []).extend(
                    f'M{x:.6g},{-y:.6g} L{float(centres[at][0]):.6g},{-float(centres[at][1]):.6g}' for at in group)
        out = []
        for colour, paths in cables.items():
            out += [dict(fill='transparent', stroke=colour, width=1.0, dashed=False, path=' '.join(paths[at:at + 1000]))
                    for at in range(0, len(paths), 1000)]
        for colour, paths in squares.items():
            out += [dict(fill=colour, stroke='#0a0c10', width=1.0, dashed=False, path=' '.join(paths[at:at + 1000]))
                    for at in range(0, len(paths), 1000)]
        self._optimizer_key, self._optimizer_paths = key, out
        return out

    def _prepare(self, editor):
        signature = tuple((sfid, id(r), tuple(sf.removed) if sf else ())
                          for sfid, r in editor.results.items() for sf in [editor.session.subfield(sfid)])
        if signature == self.signature:
            return
        self.refs, quads = [], []
        for sfid, r in editor.results.items():
            sf = editor.session.subfield(sfid)
            if sf is None:
                continue
            for m in r.modules:
                if m.key not in sf.removed:
                    self.refs.append((sfid, m.key))
                    quads.append(m.corners)
        self.index = {ref: i for i, ref in enumerate(self.refs)}
        self.router = string_paths.Router(quads)
        self.signature = signature
        self._key = None

    @staticmethod
    def _runs_key(editor):
        raw = (editor.project.energy.get("strings") or {}).get("runs") or []
        return tuple((r.get("inverter"), r.get("mppt"), tuple(r.get("modules") or ()),
                      tuple(r.get("optimizer_group_sizes") or ())) for r in raw) + (
            plant.partial_keys(editor.project.energy),)

    def _routing(self, orders, step, mpp):
        """The finished strings' legs and lanes, kept while the strings and the scale step stay (R496): a module added to
        the draft does not route the fifty strings of the plant again."""
        key = (self.signature, orders, step)
        if key != self._routing_key:
            self._routing_key = key
            self._routed = self.router.legs_together([list(o) for o in orders], 6.0 * mpp)
        return self._routed

    def band(self, editor):
        """The elastic band from the last module of the draft to the pointer, scene coordinates: [x0, y0, x1, y1]."""
        draft = editor.draft or []
        at = self.index.get(tuple(draft[-1])) if draft else None
        if at is None or self.router is None:
            return []
        x, y = map(float, self.router.centres[at])
        px, py = editor.pointer
        return [x, -y, float(px), -float(py)]

    def build(self, editor, mpp, *, tints=None, states=None, wiring_on=True):
        if not math.isfinite(mpp) or mpp <= 0:
            raise ValueError("Metres per pixel must be positive")
        self._prepare(editor)
        pixels = self.router.size / mpp
        erase = editor.tool.startswith("erase_")
        key = (self._runs_key(editor), editor.chosen_string, tuple(map(tuple, editor.draft or ())), editor.draft_target,
               bool(wiring_on), tuple(sorted((states or {}).items())), level_of(pixels),
               round(math.log(mpp) / math.log(1.5)),            # arrows and lanes follow the scale in steps
               id(getattr(editor, "string_optimizers", None)),
               (editor.tool, editor.pick(editor.pointer)[:3]) if erase else editor.tool == "string",
               tints is not None and tuple(tints))
        if key != self._key:
            self._scene = self._build(editor, mpp, tints=tints, states=states, wiring_on=wiring_on)
            self._key = key
            self.builds += 1
        return dict(self._scene, band=self.band(editor))

    def _build(self, editor, mpp, *, tints=None, states=None, wiring_on=True):
        router = self.router
        objects, labels, dots = [], [], []
        highlights = []
        runs = editor.runs()
        orders = [[self.index.get(tuple(ref.split("/", 1)), -1) for ref in r.get("modules", [])] for r in runs]
        tints = tints or theme_colors.string_tints(theme_colors.PRESETS["indigo"])
        seeds = [zlib.crc32(r["modules"][0].encode()) if r.get("modules") else i for i, r in enumerate(runs)]
        colours = [tints[c] for c in string_paths.colours([[j for j in o if j >= 0] for o in orders], router, len(tints), seeds)]
        redraw = editor.draft_target[2] if editor.draft_target else -1
        shown = [i for i, o in enumerate(orders) if o and min(o) >= 0 and i != redraw] if wiring_on else []
        fitted = getattr(editor, "string_optimizers", {}) or {}
        # R456: an inverter with optimizers on some modules only: its strings drawn as plain ones, an optimizer on each
        # module that has one
        partial = getattr(editor, "string_partial", {}) or {}
        with_units = {i: self._optimizer_groups(runs[i], orders[i], fitted[runs[i].get("inverter")])
                      for i in shown if runs[i].get("inverter") in fitted and runs[i].get("inverter") not in partial}
        some = {}
        for i in shown:
            named = partial.get(runs[i].get("inverter"))
            if named:
                named = set(named)
                some[i] = [[at] for at, ref in zip(orders[i], runs[i].get("modules", []), strict=False) if ref in named]
        plain = [i for i in shown if i not in with_units]
        routed, lanes = self._routing(tuple(tuple(orders[i]) for i in plain), round(math.log(mpp) / math.log(1.5)), mpp)
        size = router.size
        pixels = size / mpp
        level = level_of(pixels)

        def item(kind, points, colour, *, fill="transparent", width=1.0, closed=False, **extra):
            objects.append(dict(kind=kind, oid="", points=[[float(x), -float(y)] for x, y in points],
                                stroke=colour, fill=fill, width=width, closed=closed, **extra))

        def heading(pts, k):
            """The string's direction at its k-th module, East/North and unit: what places its labels (R467)."""
            a, b = pts[max(k - 1, 0)], pts[min(k + 1, len(pts) - 1)]
            length = math.dist(a, b)
            return ((b[0] - a[0]) / length, (b[1] - a[1]) / length) if length > 1e-12 else (1.0, 0.0)

        def arrowhead(a, b, light, run, draft, *, at_end=False):
            """A small arrowhead on the segment a-b pointing to b: in its middle, or on its end for a jump (R496)."""
            half, wing = 5.0 * mpp, 4.0 * mpp
            length = math.dist(a, b)
            if length < 1e-12:
                return
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            if at_end:
                mx, my = b[0] - ux * half * 1.2, b[1] - uy * half * 1.2
            else:
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            item("string_arrow", [(mx + ux * half, my + uy * half),
                                  (mx - ux * half - uy * wing, my - uy * half + ux * wing),
                                  (mx - ux * half + uy * wing, my - uy * half - ux * wing)],
                 "#0a0c10c8", fill=light, closed=True, run=run, draft=draft)

        def arrows(legs, light, run, draft):
            """One small arrowhead in the middle of each plain leg, pointing to the next module (R467)."""
            for points, jump in legs:
                if jump:
                    continue
                segments = list(zip(points, points[1:], strict=False))
                if not segments:
                    continue
                a, b = max(segments, key=lambda s: math.dist(*s))
                if math.dist(a, b) / mpp >= 24:
                    arrowhead(a, b, light, run, draft)

        def jump_points(points):
            """A direct jump becomes an arc; a bridge through a gap keeps its right angles."""
            return jump_arc(points[0], points[-1], size) if len(points) == 2 else list(points)

        def draw(order, colour, legs, width, alpha, run, chosen, lane=0, draft=False, spots=True):
            # The string being drawn looks like a finished one; only the module just added is outlined (R467).
            outline = colour if chosen and not draft else "transparent"
            for at in order:
                item("string_fill", router.quads[at], outline,
                     fill=colour + f"{alpha:02x}", closed=True, run=run, draft=draft)
            light = "#" + "".join(f"{round(.45 * int(colour[i:i+2], 16) + .55 * 255):02x}" for i in (1, 3, 5))
            if draft and order:
                item("string_current", router.quads[order[-1]], light, width=2.5, closed=True, run=run, draft=draft)
            thin = max(1.2, width * .55)
            for points, jump in legs:
                if jump:
                    arc = jump_points(points)
                    item("string_halo", arc, "#0a0c10b0", width=thin + 2, run=run, draft=draft)
                    item("string_jump", arc, light, width=thin, dashed=True, lane=lane, run=run, draft=draft)
                    # the arrival is marked for every string: a jump is what confuses the eye (R496)
                    if math.dist(points[0], points[-1]) / mpp >= 24 and level != "far":
                        arrowhead(arc[-2], arc[-1], light, run, draft, at_end=True)
                else:
                    item("string_halo", points, "#0a0c10c8", width=width + 3, run=run, draft=draft)
                    item("string_line", points, light, width=width, dashed=False, lane=lane, run=run, draft=draft)
            pts = [tuple(map(float, router.centres[j])) for j in order]
            close = level == "near"
            if chosen and close:
                arrows(legs, light, run, draft)
            if spots and close:
                dots.extend(dict(x=x, y=y, colour=colour, diameter=8, run=run, draft=draft) for x, y in pts)
            if chosen:
                for n in number_indices(pts, mpp):
                    x, y = pts[n - 1]
                    dx, dy = heading(pts, n - 1)
                    labels.append(dict(x=x, y=y, text=str(n), number=n, colour=colour, kind="number",
                                       run=run, draft=draft, offsetX=0, offsetY=0, dirX=dx, dirY=dy))
            return pts, heading

        # With power optimizers the string runs from unit to unit, thin cables from the unit to its modules (R424).
        units_of = {i: string_paths.optimizer_units(router.quads, groups) for i, groups in with_units.items()}

        def unit_legs(units):
            """The string from unit to unit, one plain leg: with optimizers the units sit between the modules and the
            next row is the ordinary way (R424); a jump arc would read as a detour. Kept as one list."""
            points = [(float(u[0]), float(u[1])) for u in units]
            return [(points, False)] if len(points) > 1 else []

        paths = iter(zip(plain, routed, lanes, strict=True))
        plan = []
        for i in shown:
            if i in with_units:
                plan.append((i, unit_legs(units_of[i]), 0))
            else:
                plan.append(next(paths))
        far = level == "far"       # zoomed out: the string's line alone
        for i, legs, lane in plan:
            order, colour = orders[i], colours[i]
            chosen = i == editor.chosen_string
            pts, heading = draw(order, colour, legs, 4.5 if chosen else 2.5, 190 if chosen else 140, i, chosen, lane,
                                spots=i not in with_units)
            x, y = pts[0]
            dx, dy = heading(pts, 0)
            state = (states or {}).get(i, "check")
            labels.append(dict(x=x, y=y, text=plant.run_label(runs, i), kind="name", colour=colour,
                               run=i, inverter=int(runs[i].get("inverter") or 0), state=state,
                               statusColour=theme_colors.STATUS[
                                   {"ok": "good", "check": "warning", "fail": "critical"}.get(state, "warning")],
                               offsetX=0, offsetY=-28, dirX=dx, dirY=dy))
        drawn_units = dict(with_units)
        drawn_units.update({i: groups for i, groups in some.items() if groups})
        units_of.update({i: string_paths.optimizer_units(router.quads, groups) for i, groups in some.items() if groups})
        optimizer_paths = [] if far or not drawn_units else self._optimizer_batches(
            (self.signature, repr(sorted((i, g) for i, g in drawn_units.items())), tuple(colours)),
            [(colours[i], units_of[i], drawn_units[i]) for i in drawn_units])
        # R433: where a string goes on over another face, a diamond between the two modules
        face_of = faces.faces_of(editor.project)
        for i in shown:
            refs = [tuple(ref.split("/", 1)) for ref in runs[i].get("modules", [])]
            for (a, at), (b, bt) in zip(zip(refs, orders[i], strict=False), zip(refs[1:], orders[i][1:], strict=False),
                                         strict=False):
                fa, fb = face_of.get(a[0]), face_of.get(b[0])
                if fa is None or fb is None or faces.same_face(fa, fb) or at < 0 or bt < 0:
                    continue
                (ax, ay), (bx, by) = (tuple(map(float, router.centres[at])), tuple(map(float, router.centres[bt])))
                mx, my, r = (ax + bx) / 2, (ay + by) / 2, max(6.0 * mpp, 0.12 * size)
                item("string_arrow", [(mx, my + r), (mx + r, my), (mx, my - r), (mx - r, my)], "#0a0c10c8",
                     fill=colours[i], closed=True, run=i, draft=False, face_change=True)
        assigned = {ref for r in runs for ref in r.get("modules", [])}
        assigned.update("/".join(ref) for ref in editor.draft or [])    # being wired now: not red (R467)
        if wiring_on:
            for ref, at in self.index.items():
                if "/".join(ref) not in assigned:
                    item("unwired", router.quads[at], theme_colors.STATUS["critical"], width=2, closed=True)
        draft = [self.index[tuple(ref)] for ref in editor.draft or [] if tuple(ref) in self.index]
        draft_colour = ""
        if draft:
            n = len(runs)
            palette = tints[n % len(tints):] + tints[:n % len(tints)]
            draft_colour = colours[redraw] if 0 <= redraw < len(colours) else next((c for c in palette if c not in colours), palette[0])
            draw(draft, draft_colour, router.legs(draft), 3.5, 140, -1, True, draft=True)
        if editor.tool.startswith("erase_"):
            kind, sfid, key = editor.pick(editor.pointer)
            owner = editor.owner(sfid, key) if kind == "module" else -1
            if owner >= 0:
                unit = runs[owner].get("inverter", 0)
                targets = [owner] if editor.tool == "erase_string" else [i for i, r in enumerate(runs) if unit and r.get("inverter", 0) == unit]
                for i in targets:
                    highlights += [tuple(ref.split("/", 1)) for ref in runs[i].get("modules", [])]
        return dict(objects=objects, labels=labels, dots=dots, highlights=highlights, optimizers=optimizer_paths,
                    colours=colours, draftColour=draft_colour, size=float(size), level=level,
                    coordinates="scene-objects/east-north-labels")
