"""Pure string graphics shared with the Widgets router, R57/R117/R134/R184/R186/R496.

Objects have scene coordinates (East, minus North). Labels and dots expose
East/North centres and pixel offsets, for text that does not scale with the map.
The renderer owns font measurement and overlap rejection of string name chips.

The scene is built once for a given state and kept (R496): while the pointer moves only the elastic band from the
last module of the draft to the pointer changes, and it is returned apart (`band`), so the plan does not rebuild
the strings' layers at every move. A jump between modules that are not next to each other is a thin dashed arc over
the modules it passes, with an arrowhead where it lands (R496).

The scene comes with the plan's layers already split (`layers`) and the large ones already joined into the native
paths the plan draws (`paths`, R598): what the window did with them at every overlay (the objects' points made Qt
points, the colours put in Qt's order, then joined by the plan's batch) is made once with the scene, and only a few
strings go to the QML.
"""
from __future__ import annotations

import copy
import math
import time
import zlib
from collections import defaultdict

from meridiana.core.compute import resources
from meridiana.core.geometry import string_paths
from meridiana.app.interface import theme_colors
from meridiana.app.interface.view_colours import WIDTHS
from meridiana.app.view import plan_levels
from meridiana.core.energy import faces, optimizers, plant

JUMP_ARC_STEPS = 14        # points of the arc of a direct jump
DRAFT = ("draftWires", "draftFills", "draftDots", "draftLabels", "draftColour")    # what the hand is drawing
# the large layers, drawn as joined paths (a few strings to the QML). `wireMarks` (R706) is what follows the scale
# among the strings' lines: the arrowheads, the jumps that take a lane; the rest stays as it is at every scale.
JOINED = ("wires", "wireFills", "unwired", "wireMarks")
PATHS_EACH = 1000           # outlines in a native path: large SVG paths hit Qt's path and vertex limits


def qt_colour(value):
    """A "#rrggbbaa" colour in Qt's order, as the plan hands its objects to the QML; any other value as it is."""
    return theme_colors.qt_hex(value) if isinstance(value, str) and len(value) == 9 and value.startswith("#") else value


ZONE = 32.0                 # metres: the side of the squares the plan's large layers are cut into (R706)


def joined(items, fill="#192d5a", stroke="#c6cbd6", colour=lambda c: c) -> list[dict]:
    """Outlines (dicts with `points`, and `fill`, `stroke`, `width`, `dashed`, `closed` when not the defaults) as
    native SVG paths, one for each style in each square of ZONE metres (an outline goes with the square its middle
    is in) and PATHS_EACH outlines: what the plan's ModuleBatch draws. `bounds` (west, north, east, south, in the
    scene's metres) is what a path covers: the plan draws and builds only the paths that touch its view (R706: a
    plant drawn in a few paths cost the view, at every step, all its modules, on screen or not). `colour` puts a
    colour as the QML wants it (qt_colour for the objects of the scene). A point is a pair or has x() and y()."""
    groups = {}
    for item in items:
        points = [(float(p.x()), float(p.y())) if hasattr(p, "x") else (float(p[0]), float(p[1])) for p in item["points"]]
        if not points:
            continue
        path = "M" + " L".join(f"{x:.8g},{y:.8g}" for x, y in points)
        if item.get("closed", True):
            path += " Z"
        xs, ys = [x for x, _y in points], [y for _x, y in points]
        box = (min(xs), min(ys), max(xs), max(ys))
        key = (colour(item.get("fill", fill)), colour(item.get("stroke", stroke)),
               item.get("width", WIDTHS["module_line"]), item.get("dashed", False),
               math.floor((box[0] + box[2]) / 2 / ZONE), math.floor((box[1] + box[3]) / 2 / ZONE))
        group = groups.get(key)
        if group is None:
            groups[key] = [[path], list(box)]
        else:
            group[0].append(path)
            was = group[1]
            was[0], was[1], was[2], was[3] = min(was[0], box[0]), min(was[1], box[1]), max(was[2], box[2]), max(was[3], box[3])
    return [dict(fill=f, stroke=s, width=w, dashed=d, bounds=list(box), path=" ".join(paths[start:start + PATHS_EACH]))
            for (f, s, w, d, _cx, _cy), (paths, box) in groups.items() for start in range(0, len(paths), PATHS_EACH)]


DOT_LENGTH = 0.003          # metres: a stroke this short with round ends is a dot as wide as its pen
DOT_CELL = ZONE             # metres: the dots of a path are written from the corner of their square


def dot_paths(dots, colour=lambda c: c) -> list[dict]:
    """The strings' dots as native paths (R706), one for each colour in each square of DOT_CELL metres, written from
    the square's corner (`x`, `y`, where the plan puts the path): the plan draws them with the modules, in one layer.
    They were an item each, made again whenever the view settled near the modules: 2000 modules were 6000 items and
    a third of a second of the window. The squares keep the numbers small: Qt's curves work in single precision,
    and three millimetres written at three hundred metres from the origin are no stroke at all for them."""
    groups = defaultdict(list)
    for dot in dots:
        x, y = float(dot["x"]), -float(dot["y"])
        cx, cy = math.floor(x / DOT_CELL), math.floor(y / DOT_CELL)
        # to a tenth of a millimetre: a path's numbers, not a text of the interface
        px, py = round(x - cx * DOT_CELL, 4), round(y - cy * DOT_CELL, 4)
        groups[(colour(dot["colour"]), cx, cy)].append("M" + repr(px) + "," + repr(py) + " h" + repr(DOT_LENGTH))
    return [dict(fill="transparent", stroke=stroke, dashed=False, x=cx * DOT_CELL, y=cy * DOT_CELL, path=" ".join(paths),
                 bounds=[cx * DOT_CELL, cy * DOT_CELL, (cx + 1) * DOT_CELL + DOT_LENGTH, (cy + 1) * DOT_CELL])
            for (stroke, cx, cy), paths in groups.items()]


def layers_of(scene: dict) -> dict:
    """The plan's layers of a wiring scene (R496): the finished strings (lines, fills, dots, names, optimizers), the
    modules in no string (red) and the draft, what the hand is drawing; each is made again on the plan only when it
    changed."""
    objects, dots, labels = scene["objects"], scene["dots"], scene["labels"]
    return {
        "wires": [o for o in objects if not o.get("draft") and not o.get("mark")
                  and o["kind"] not in ("string_fill", "unwired")],
        "wireMarks": [o for o in objects if o.get("mark") and not o.get("draft")],
        "wireFills": [o for o in objects if not o.get("draft") and o["kind"] == "string_fill"],
        "unwired": [o for o in objects if o["kind"] == "unwired"],
        "dots": [d for d in dots if not d.get("draft")],
        # the finished strings' dots at every scale (R706): the plan keeps them drawn and shows those of its level
        # of detail (R707): one on each module, or each string's first alone
        "spots": [d for d in scene.get("spots", dots) if not d.get("draft")],
        "heads": [d for d in scene.get("heads", ()) if not d.get("draft")],
        "stringLabels": [p for p in labels if not p.get("draft")],
        "optimizerPaths": scene["optimizers"],
        "level": (scene["level"], float(scene["size"] or 1.0)),
        "draftWires": [o for o in objects if o.get("draft") and o["kind"] != "string_fill"],
        "draftFills": [o for o in objects if o.get("draft") and o["kind"] == "string_fill"],
        "draftDots": [d for d in dots if d.get("draft")],
        "draftLabels": [p for p in labels if p.get("draft")],
        "draftColour": scene["draftColour"],
    }


def number_indices(points, mpp):
    """The exact Widgets thinning rule, including the first and last module."""
    gaps = sorted(math.dist(a, b) for a, b in zip(points, points[1:], strict=False))
    spacing = gaps[len(gaps) // 2] / mpp if gaps else 99.0
    step = 1 if spacing >= 20 else 5 if spacing * 5 >= 24 else 10
    return [n for n in range(1, len(points) + 1) if n in (1, len(points)) or n % step == 0]


def signature_of(editor) -> tuple:
    """The layouts a scene is made on, by value: each sub-field's layout key and the modules taken out of it."""
    keys = editor.session.layout_keys
    return tuple((sfid, keys.get(sfid), tuple(sf.removed))
                 for sfid in editor.results for sf in [editor.session.subfield(sfid)] if sf is not None)


def options_of(editor, mpp: float, states) -> dict | None:
    """What the plan's scene of the strings is made with besides the project and its layouts, for the layout's job to
    make it in its process (R598): None when it follows the hand (a string being drawn, an eraser over the plan)."""
    if editor.draft or editor.draft_target or editor.tool.startswith("erase_") or not (math.isfinite(mpp) and mpp > 0):
        return None
    partial = getattr(editor, "string_partial", None) or {}
    return {"mpp": float(mpp), "states": dict(states or {}), "tool": editor.tool, "chosen": editor.chosen_string,
            "optimizers": dict(editor.string_optimizers or {}), "partial": {k: list(v) for k, v in partial.items()}}


def coming(session) -> bool:
    """Whether a layout is on its way that brings the plan's scene of the strings made with it (R598): the layouts in
    hand are not those of the project as it is, and the plan asked the layout's job for its scene
    (session.wiring_options) in a window that answers the gesture first (session.later, R547)."""
    return (getattr(session, "later", None) is not None and getattr(session, "wiring_options", None) is not None
            and session.layout_keys != session.expected_layout_keys())


STATES = 5                  # where the strings' states are in WiringScene.build's key: they change the names alone
LEVEL, STEP = 6, 7          # where the level of detail and the step of the scale are: they change the marks, and
                            # whether the dots and the optimizers show, nothing else (R706)


def steady_of(key) -> tuple:
    """What two keys of WiringScene.build have in common when they differ in the scale alone (level and step)."""
    return key[:LEVEL] + key[STEP + 1:]


def only_states(was, key) -> bool:
    """Whether two keys of WiringScene.build differ in the strings' states alone."""
    return (was is not None and key is not None and len(was) == len(key) and was[STATES] != key[STATES]
            and was[:STATES] + was[STATES + 1:] == key[:STATES] + key[STATES + 1:])


def status_colour(state: str) -> str:
    """The traffic light of a string's name (R496) for its state."""
    return theme_colors.STATUS[{"ok": "good", "check": "warning", "fail": "critical"}.get(state, "warning")]


def restated(scene: dict, states: dict) -> dict:
    """The scene with its strings' names in `states` (run -> "ok", "check", "fail"): what a build with them makes,
    since the states change the names alone (R598)."""
    states = states or {}

    def named(label):
        if label.get("kind") != "name" or label.get("draft"):
            return label
        state = states.get(label["run"], "check")
        return dict(label, state=state, statusColour=status_colour(state))
    labels = [named(label) for label in scene["labels"]]
    return dict(scene, labels=labels, names=[named(label) for label in scene.get("names") or ()],
                layers=dict(scene["layers"], stringLabels=[p for p in labels if not p.get("draft")]))


class Strings:
    """What a WiringScene reads of the plan's editor, made of a project, its layouts and the plan's options
    (options_of): the scene of the strings made in the layout's process."""
    draft = None
    draft_target = None
    pointer = (0.0, 0.0)

    def __init__(self, project, results: dict, keys: dict, options: dict):
        self.project = project
        self.results = {sid: r for sid, r in results.items() if not isinstance(r, Exception)}
        self.layout_keys = keys
        self.session = self             # editor.session.subfield and .layout_keys, as the plan's editor has them
        self.tool, self.chosen_string = options["tool"], options["chosen"]
        self.string_optimizers, self.string_partial = options["optimizers"], options["partial"]

    def subfield(self, sfid):
        return next((s for s in self.project.subfields if s.id == sfid), None)

    def runs(self):
        return copy.deepcopy((self.project.energy.get("strings") or {}).get("runs") or [])


def made_with(project, results: dict, keys: dict, options: dict, scene=None) -> dict:
    """The plan's scene of the strings made where the layout is (its process, R598), for the plan to take instead of
    making it on the window's thread (WiringScene.build): the layers it draws, without the objects (the tests make
    them on the window when they read them), with the inputs it answers for (`key`, `signature`). `scene`: the
    WiringScene that makes it, kept by who asks again and again (the plan's thread of the scales, R706): another
    step of the scale then makes the marks alone."""
    view = Strings(project, results, keys, options)
    scene = scene or WiringScene()
    made = scene.build(view, options["mpp"], states=options["states"], wiring_on=True)
    made.pop("band")
    layers = dict(made["layers"], **{name: None for name in JOINED})
    return {"key": scene._key, "signature": signature_of(view),
            "scene": dict(made, objects=None, stable=None, layers=layers)}


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
    return plan_levels.wiring_level(pixels)     # the thresholds are the plan's, in one place (R707)


def scene_bytes(scene: dict) -> int:
    """About what a scene holds in memory: the characters of its joined paths and some four hundred bytes for each
    thing of its layers (an estimate: study 56 measured 5 MB at 2000 modules and 25-28 MB at 10 000)."""
    things = sum(len(layer) for layer in scene["layers"].values() if isinstance(layer, list))
    things += len(scene.get("objects") or ())
    letters = sum(len(path["path"]) for paths in scene.get("paths", {}).values() for path in paths)
    return 4096 + 400 * things + 2 * letters


class WiringScene:
    def __init__(self, limit=None):
        # R706 (study 56): the scenes of the scales the view has been at, by key, within the budget's share for
        # the plan. There was one scene: every step of the scale made it again (110-130 ms at 2000 modules, 500-600
        # at 10 000), the steps a zoom in and back had just crossed too. Emptied when the layouts or the strings
        # change; `trim` gives back what the budget no longer allows.
        self._kept = resources.Cache(limit or (lambda: resources.cache_limit("plan")), scene_bytes)
        self._kept_runs = None
        # R706: the last scene made of each set of things (steady_of: everything but the step of the scale). Another
        # step takes from it what does not follow the scale (fills, lines, dots, names: the modules' share of the
        # work) and makes the marks alone. Few: one for each level of detail the view has been at.
        self._steadies = {}
        self.signature = None
        self.router = None
        self.index = {}
        self.refs = []
        self._optimizer_key = None
        self._optimizer_paths = []
        self._key = None
        self._scene = None
        self._routing_key, self._routed = None, ([], [])
        self._joined = {}           # layer name -> (its objects, their joined paths), kept while the layer is the same
        self.builds = 0
        self.marked = 0             # of which the marks alone, the rest taken from the scene of another step (R706)
        self._laned = []
        self.waited = 0             # builds not made while a layout brings the scene (R598)
        self._coming = None         # (photo, layout keys, coming): coming() of the session as it was last asked

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
        self._quads, self.router = quads, None         # the router made when a scene is built here (_router)
        self.size = string_paths.shorter_sides(quads)[2]
        self.signature = signature
        self._key = None
        self._kept.clear()
        self._kept.pinned = set()
        self._steadies = {}

    def _router(self):
        if self.router is None:
            self.router = string_paths.Router(self._quads)
        return self.router

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
            strings = [list(o) for o in orders]
            self._routed = self.router.legs_together(strings, 6.0 * mpp)
            self._laned = self.router.follows_gap(strings)
        return self._routed

    def band(self, editor):
        """The elastic band from the last module of the draft to the pointer, scene coordinates: [x0, y0, x1, y1]."""
        draft = editor.draft or []
        at = self.index.get(tuple(draft[-1])) if draft else None
        if at is None:
            return []
        x, y = map(float, self._router().centres[at])
        px, py = editor.pointer
        return [x, -y, float(px), -float(py)]

    def build(self, editor, mpp, *, tints=None, states=None, wiring_on=True, full=False, wait=False):
        """The scene for the editor's state at `mpp` metres a pixel, kept while nothing it is made of changes. One
        the layout's job made with the same inputs (`editor.session.wiring_offer`, made_with) is taken as it is: it
        has the layers the plan draws, not the objects; `full`: the objects too, made here when missing (what the
        tests read). Other states of the strings change their names alone (R598). `wait`: while a layout is on its
        way that brings the scene made with it (coming), the scene of before is kept instead of made here (R598: the
        plan shows what it has, the modules of the gesture already drawn); never while the hand draws (options_of)."""
        key = self._key_of(editor, mpp, tints, states, wiring_on)
        if key != self._key:
            # a scale already seen: its scene as it was made (never while the hand draws: that scene follows it)
            keeps = options_of(editor, mpp, states) is not None and tints is None
            kept = self._kept.get(key) if keeps else None
            if kept is not None and not (full and kept["objects"] is None):
                self._scene, self._key = kept, key
                self._kept.pinned = {key}
                return dict(self._scene, band=self.band(editor))
            offered = self._offered(editor, key)
            if offered is None and self._restate(key, states):
                return dict(self._scene, band=self.band(editor))
            # R706: likewise while the scene of a new scale is being made off the window (editor.scene_coming)
            if (offered is None and wait and not full and self._scene is not None
                    and options_of(editor, mpp, states) is not None
                    and (getattr(editor, "scene_coming", False) or self._waits(editor.session))):
                self.waited += 1
                return dict(self._scene, band=self.band(editor))
            self._scene, cost = offered, 0.1
            if self._scene is None:
                started = time.perf_counter()
                # another step of the scale of a scene made here: the marks alone (never while the hand draws)
                steady = self._steadies.get(steady_of(key)) if keeps else None
                self._scene = self._build(editor, mpp, tints=tints, states=states, wiring_on=wiring_on, steady=steady)
                cost = time.perf_counter() - started
                self.builds += 1
                self.marked += steady is not None
                if keeps:
                    if len(self._steadies) >= 4:
                        self._steadies.pop(next(iter(self._steadies)))
                    self._steadies[steady_of(key)] = self._scene
            self._key = key
            if keeps:
                self._kept.pinned = {key}              # the scene in hand leaves last
                self._kept.put(key, self._scene, cost)
        if full and self._scene["objects"] is None:
            self._scene = self._build(editor, mpp, tints=tints, states=states, wiring_on=wiring_on)
            self.builds += 1
        return dict(self._scene, band=self.band(editor))

    def _key_of(self, editor, mpp, tints, states, wiring_on):
        """What a scene is made of, by value: the strings, the hand's state, the level and the step of the scale."""
        if not math.isfinite(mpp) or mpp <= 0:
            raise ValueError("Metres per pixel must be positive")
        self._prepare(editor)
        runs = self._runs_key(editor)
        if runs != self._kept_runs:                     # other strings: the scenes kept are of no use any more
            self._kept_runs = runs
            self._kept.clear()
            self._kept.pinned = set()
            self._steadies = {}
        pixels = self.size / mpp
        erase = editor.tool.startswith("erase_")
        partial = getattr(editor, "string_partial", None) or {}
        return (runs, editor.chosen_string, tuple(map(tuple, editor.draft or ())), editor.draft_target,
                bool(wiring_on), tuple(sorted((states or {}).items())), level_of(pixels),
                round(math.log(mpp) / math.log(1.5)),            # arrows and lanes follow the scale in steps
                repr(sorted((getattr(editor, "string_optimizers", None) or {}).items())),
                repr(sorted((k, sorted(v)) for k, v in partial.items())),
                (editor.tool, editor.pick(editor.pointer)[:3]) if erase else editor.tool == "string",
                tints is not None and tuple(tints))

    def keeps(self, editor, mpp, states, wiring_on=True) -> bool:
        """Whether the scene of this scale is in hand or kept: nothing to make, here or in a job (R706)."""
        key = self._key_of(editor, mpp, None, states, wiring_on)
        return key == self._key or key in self._kept

    def trim(self) -> None:
        """Today's budget applied to the scenes kept: called now and then, and the memory a machine short of it
        asks back is given back (the budget drops to a quarter then, resources.Budget)."""
        self._kept.trim()

    def kept_bytes(self) -> int:
        return self._kept.bytes()

    def _waits(self, session) -> bool:
        """coming(session), asked again only when the photo or the layouts in hand are others (a pointer's move while
        a layout is on its way asks it at each step)."""
        photo, keys = getattr(session, "_photo", None), session.layout_keys
        if self._coming is None or self._coming[0] is not photo or self._coming[1] is not keys:
            self._coming = (photo, keys, coming(session))
        return self._coming[2]

    def _restate(self, key, states) -> bool:
        """Only the states of the strings changed (the plant came, R598): the names take them, the scene stays; before,
        the scene was made again (98-182 ms on Rho). False when anything else changed."""
        if self._scene is None or not only_states(self._key, key):
            return False
        self._scene, self._key = restated(self._scene, states), key
        return True

    def _offered(self, editor, key):
        """The scene the layout's job made for these very inputs (R598), taken once; None when there is none."""
        session = editor.session
        offer = getattr(session, "wiring_offer", None)
        if (not offer or offer["key"] != key and not only_states(offer["key"], key)
                or offer["signature"] != signature_of(editor)):
            return None
        session.wiring_offer = None
        self._joined = {}
        # made with the states of before (the plant came meanwhile): its names take those of now
        return dict(offer["scene"]) if offer["key"] == key else restated(offer["scene"], dict(key[STATES]))

    def _build(self, editor, mpp, *, tints=None, states=None, wiring_on=True, steady=None):
        """The scene. `steady`: the scene of another step of the scale made of the same things (steady_of, never
        with a draft): what does not follow the scale is taken from it as it is, the very lists, and only the marks
        are made, which do (the arrowheads, the jumps that take a lane, the numbers of the string chosen)."""
        router = self._router()
        full = steady is None
        objects, marks, labels, numbers, dots = [], [], [], [], []
        highlights = []
        runs = editor.runs()
        orders = [[self.index.get(tuple(ref.split("/", 1)), -1) for ref in r.get("modules", [])] for r in runs]
        tints = tints or theme_colors.string_tints(theme_colors.PRESETS["indigo"])
        if full:
            seeds = [zlib.crc32(r["modules"][0].encode()) if r.get("modules") else i for i, r in enumerate(runs)]
            colours = [tints[c] for c in string_paths.colours([[j for j in o if j >= 0] for o in orders], router,
                                                              len(tints), seeds)]
        else:
            colours = steady["colours"]
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
        laned = {i for i, follows in zip(plain, self._laned, strict=True) if follows}
        size = router.size
        pixels = size / mpp
        level = level_of(pixels)

        def item(kind, points, colour, *, fill="transparent", width=1.0, closed=False, mark=False, **extra):
            """`mark`: it follows the scale (R706), made at every step; the rest only for a scene made whole."""
            if mark:
                marks.append(dict(kind=kind, oid="", points=[[float(x), -float(y)] for x, y in points],
                                  stroke=colour, fill=fill, width=width, closed=closed, mark=True, **extra))
            elif full:
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
                 "#0a0c10c8", fill=light, closed=True, mark=True, run=run, draft=draft)

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

        def draw(order, colour, legs, width, alpha, run, chosen, lane=0, draft=False, spots=True, follows=False):
            """`follows`: the string's jumps may take a lane, which follows the scale: they are marks."""
            # The string being drawn looks like a finished one; only the module just added is outlined (R467).
            outline = colour if chosen and not draft else "transparent"
            if full:
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
                    item("string_halo", arc, "#0a0c10b0", width=thin + 2, mark=follows, run=run, draft=draft)
                    item("string_jump", arc, light, width=thin, dashed=True, mark=follows, lane=lane, run=run,
                         draft=draft)
                    # the arrival is marked for every string: a jump is what confuses the eye (R496)
                    if math.dist(points[0], points[-1]) / mpp >= 24 and level != "far":
                        arrowhead(arc[-2], arc[-1], light, run, draft, at_end=True)
                elif full:
                    item("string_halo", points, "#0a0c10c8", width=width + 3, run=run, draft=draft)
                    item("string_line", points, light, width=width, dashed=False, lane=lane, run=run, draft=draft)
            if not (full or chosen):
                return None
            pts = [tuple(map(float, router.centres[j])) for j in order]
            close = level == "near"
            if chosen and close:
                arrows(legs, light, run, draft)
            if spots and full:              # at every scale: `dots` is these near the modules, nothing further
                dots.extend(dict(x=x, y=y, colour=colour, diameter=8, run=run, draft=draft) for x, y in pts)
            if chosen:
                for n in number_indices(pts, mpp):
                    x, y = pts[n - 1]
                    dx, dy = heading(pts, n - 1)
                    numbers.append(dict(x=x, y=y, text=str(n), number=n, colour=colour, kind="number",
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
            drawn = draw(order, colour, legs, 4.5 if chosen else 2.5, 190 if chosen else 140, i, chosen, lane,
                         spots=i not in with_units, follows=i in laned)
            if not full:
                continue
            pts, _heading = drawn
            x, y = pts[0]
            dx, dy = heading(pts, 0)
            state = (states or {}).get(i, "check")
            labels.append(dict(x=x, y=y, text=plant.run_label(runs, i), kind="name", colour=colour,
                               run=i, inverter=int(runs[i].get("inverter") or 0), state=state,
                               statusColour=status_colour(state),
                               offsetX=0, offsetY=-28, dirX=dx, dirY=dy))
        drawn_units = dict(with_units)
        drawn_units.update({i: groups for i, groups in some.items() if groups})
        units_of.update({i: string_paths.optimizer_units(router.quads, groups) for i, groups in some.items() if groups})
        units = steady["units"] if not full else [] if not drawn_units else self._optimizer_batches(
            (self.signature, repr(sorted((i, g) for i, g in drawn_units.items())), tuple(colours)),
            [(colours[i], units_of[i], drawn_units[i]) for i in drawn_units])
        optimizer_paths = [] if far else units
        # R433: where a string goes on over another face, a diamond between the two modules: where they are is found
        # with the scene made whole (`turns`), their size follows the scale
        if full:
            turns = []
            face_of = faces.faces_of(editor.project)
            for i in shown:
                refs = [tuple(ref.split("/", 1)) for ref in runs[i].get("modules", [])]
                for (a, at), (b, bt) in zip(zip(refs, orders[i], strict=False),
                                             zip(refs[1:], orders[i][1:], strict=False), strict=False):
                    fa, fb = face_of.get(a[0]), face_of.get(b[0])
                    if fa is None or fb is None or faces.same_face(fa, fb) or at < 0 or bt < 0:
                        continue
                    (ax, ay), (bx, by) = (tuple(map(float, router.centres[at])), tuple(map(float, router.centres[bt])))
                    turns.append(((ax + bx) / 2, (ay + by) / 2, i))
        else:
            turns = steady["turns"]
        r = max(6.0 * mpp, 0.12 * size)
        for mx, my, i in turns:
            item("string_arrow", [(mx, my + r), (mx + r, my), (mx, my - r), (mx - r, my)], "#0a0c10c8",
                 fill=colours[i], closed=True, mark=True, run=i, draft=False, face_change=True)
        assigned = {ref for r in runs for ref in r.get("modules", [])} if full else ()
        if full:
            assigned.update("/".join(ref) for ref in editor.draft or [])    # being wired now: not red (R467)
        if wiring_on and full:
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
        if not full:
            # the lists of the other step as they are: the plan sees the same layers and draws nothing of them again
            names = steady["names"]
            kept = steady["layers"]
            which = {"all": "spots", "heads": "heads"}.get(plan_levels.dots_shown(pixels))
            scene = dict(steady, objects=steady["stable"] + marks, labels=names + numbers, highlights=highlights,
                         level=level, dots=steady[which] if which else [], optimizers=optimizer_paths)
            scene["layers"] = dict(kept, wireMarks=marks, level=(level, float(size)),
                                   dots=kept[which] if which else [], optimizerPaths=optimizer_paths,
                                   stringLabels=names + numbers if numbers or len(kept["stringLabels"]) != len(names)
                                   else kept["stringLabels"])
            scene["paths"] = dict(steady["paths"], wireMarks=joined(marks, colour=qt_colour))
            return scene
        # R707: a dot on each module from MODULE px, from STRING px the first of each string alone (and the draft's,
        # which the hand is laying), none further
        first, heads = set(), []
        for dot in dots:
            if dot.get("draft") or dot["run"] not in first:
                first.add(dot["run"])
                heads.append(dot)
        which = plan_levels.dots_shown(pixels)
        scene = dict(objects=objects + marks, stable=objects, labels=labels + numbers, names=labels, spots=dots,
                     heads=heads, dots=dots if which == "all" else heads if which == "heads" else [],
                     highlights=highlights, optimizers=optimizer_paths, units=units, turns=turns,
                     colours=colours, draftColour=draft_colour, size=float(size), level=level,
                     coordinates="scene-objects/east-north-labels")
        scene["layers"] = layers = layers_of(scene)
        for name in ("spots", "heads"):                 # one list: the plan sees it is the same without reading it
            if which == {"spots": "all", "heads": "heads"}[name] and len(layers["dots"]) == len(layers[name]):
                layers["dots"] = layers[name]
        scene["paths"] = {}
        for name in JOINED:         # a layer as it was (a module added to the draft) keeps its paths
            was = self._joined.get(name)
            if was is None or was[0] != layers[name]:
                self._joined[name] = was = (layers[name], joined(layers[name], colour=qt_colour))
            layers[name] = was[0]
            scene["paths"][name] = was[1]
        return scene
