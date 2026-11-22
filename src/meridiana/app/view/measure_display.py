"""What the measuring tool draws in one view (study 46): plain dicts, lists, numbers, strings and bools, ready for a
QVariant. Every point is [East, North, height]; the view takes it to the screen (the plan from above, the 3D view
through its camera). No Qt.

The shape (`build`):
- view, mode, state, hint, polar (bool), snap ("all" or the one the menu asked);
- current: the measurement in hand ({marks, segments, total}) with `elastic`, the span to the pointer; None at rest;
- done: the measurements of the session, each {id, mode, selected, closed, marks, segments, total};
- pointer: the mark under the pointer {at, kind, exact}; guides: [{a, b, kind, label}]; edge: the reference edge lit
  {a, b}; constraint, typed, request: small pills {text, at}; source: the dotted line of the height mode {a, b}.
- a segment is {a, b, style ("span" or "height"), pill}; a pill is {text, below, approx, at}.
"""

from __future__ import annotations

import math

from meridiana.app.view import measure_text as words
from meridiana.core.geometry import measure as geo


def _list(p) -> list:
    return [float(c) for c in p]


def _mid(a, b) -> list:
    return [(float(a[i]) + float(b[i])) / 2 for i in range(3)]


def _mark(p) -> dict:
    # the top of a height that took its height from elsewhere: the snap's mark is on its source (_source)
    kind = "free" if getattr(p, "source", None) is not None else p.kind
    return {"at": _list(p.point), "kind": str(kind), "exact": bool(p.exact)}


def _source(p) -> dict | None:
    """The height mode's reference: the dotted line from the point the top took its height from to the top, with the
    snap's mark on that point. None when the top is the point itself (a typed height, the pointer on the vertical)."""
    if getattr(p, "source", None) is None:
        return None
    return {"a": _list(p.source), "b": _list(p.point), "kind": str(p.kind)}


def _segment(a, b, mode: str, view: str, elastic: bool = False) -> dict:
    s = geo.span(a.point, b.point)
    approx = not (a.exact and b.exact)
    if mode == "height":
        pill, style = words.height_pill(s, b.point[2], approx), "height"
    else:
        pill, style = words.span_pill(s, view, approx, elastic), "span"
    pill["at"] = _mid(a.point, b.point)
    return {"a": _list(a.point), "b": _list(b.point), "style": style, "pill": pill}


def _measurement(points, mode: str, view: str, closed: bool = False, elastic=None) -> dict:
    """Marks, segments and total of a measurement; `elastic` the pointer's point after the last one placed."""
    pairs = list(zip(points, points[1:], strict=False)) + ([(points[-1], points[0])] if closed else [])
    out = {"marks": [_mark(p) for p in points], "segments": [_segment(a, b, mode, view) for a, b in pairs],
           "total": None, "closed": bool(closed), "elastic": None,
           "sources": [s for s in (_source(p) for p in points) if s]}
    path = list(points)
    if elastic is not None and points and math.dist(elastic.point, points[-1].point) > 1e-9:
        out["elastic"] = _segment(points[-1], elastic, mode, view, elastic=True)
        path.append(elastic)
    count = len(path) - 1 + (1 if closed else 0)
    if mode == "distance" and count >= 2:
        true, plan = geo.totals([p.point for p in path], closed)
        area = geo.plan_area([p.point for p in path]) if closed else None
        approx = not all(p.exact for p in path)
        out["total"] = words.total_pill(view, true, plan, count, area, approx)
        out["total"]["at"] = _list(path[0].point if closed else path[-1].point)
    # R609: what the view writes along a span, its number alone (the rest goes to the hint bar, measure_tool.numbers).
    # R618 (Daniel 14/11/2026: «non mi piace il fatto che il totale sia insieme alla riga dell'ultima misura»): the
    # total is no longer after the last span's number; the view draws it in a pill at the path's end ("total")
    for s in out["segments"] + ([out["elastic"]] if out["elastic"] else []):
        s["pill"]["label"] = s["pill"]["text"]
    return out


def about(tool) -> str:
    """R609: the hint bar's numbers of the span to the pointer (and of the path's total), the drawing writing only
    the span's number: in the view the pointer is in (the 3D view's probe carries its ray)."""
    points, target = tool.points, tool.target
    if not points or target is None or math.dist(target.point, points[-1].point) <= 1e-9:
        return ""
    view = "3d" if tool.probe is not None and tool.probe.ray is not None else "plan"
    m = _measurement(points, tool.mode, view, elastic=target)
    return words.details(m["elastic"]["pill"], m["total"]) if m["elastic"] else ""


def _small(text: str, at) -> dict | None:
    return {"text": text, "at": _list(at)} if text and at is not None else None


def done(tool, view: str) -> list:
    """The measurements of the session as the view draws them (the "done" of `build`)."""
    out = []
    for m in tool.measures:
        item = _measurement(list(m.points), m.mode, view, m.closed)
        item.update({"id": m.id, "mode": m.mode, "selected": m.id in tool.selected})
        out.append(item)
    return out


def build(tool, view: str, with_done: bool = True) -> dict:
    """`with_done` False leaves "done" empty: a view that follows the pointer asks for the measurements made only when
    they change (gui/backend/measure.py), not at every step."""
    target, last = tool.target, (tool.points[-1] if tool.points else None)
    current = None
    if tool.points:
        current = _measurement(tool.points, tool.mode, view, elastic=target)
    made = done(tool, view) if with_done else []
    at = target.point if target is not None else (last.point if last else None)
    guides = []
    if view == "plan" and tool.probe is not None and last is not None:
        guides = [g for g in (_guide(x, at[2]) for x in tool.probe.guides) if g]
    kind = "held" if tool.held is not None else tool.constraint
    label = words.constraint_label(kind, tool.pitch) if last is not None else ""
    if label and target is not None:
        guides.append({"a": _list(last.point), "b": _list(target.point), "kind": "constraint", "label": label})
    edge = None
    if tool.constraint in ("perpendicular", "parallel") and tool.edge:
        edge = {"a": _list(tool.edge[0]), "b": _list(tool.edge[1])}
    elif tool.snap_request == "perpendicular" and tool.probe is not None and tool.probe.edge:
        edge = {"a": _list(tool.probe.edge[0]), "b": _list(tool.probe.edge[1])}
    source = _source(target) if tool.mode == "height" and last is not None and target is not None else None
    # the pointer's mark is where the snap is: on the source of a height, else on the point
    pointer = None
    if target is not None:
        pointer = ({"at": source["a"], "kind": source["kind"], "exact": bool(target.exact)} if source
                   else _mark(target))
    return {"view": view, "mode": tool.mode, "state": tool.state, "hint": tool.hint, "polar": bool(tool.polar),
            "snap": tool.snap_request or "all", "current": current, "done": made,
            "pointer": pointer, "guides": guides, "edge": edge,
            "constraint": _small(label, at), "source": source, "follow": _follow(tool, last),
            "typed": _small(words.typed_text(tool.mode, tool.typed) if tool.typed else "", at),
            "request": _small(words.snap_label(tool.snap_request) if tool.snap_request else "", at)}


def _follow(tool, last) -> dict | None:
    """The line the span to the pointer keeps to while the 3D view's pointer moves (the view looks for no point then
    and draws the span on the screen): the foot's vertical in the height mode, the axis or the direction held in the
    distance mode; two points of it. None when the span is free."""
    if last is None:
        return None
    p = last.point
    if tool.mode == "height":
        direction = (0.0, 0.0, 1.0)
    elif tool.held is not None:
        direction = tool.held
    elif tool.constraint in geo.AXES:
        direction = geo.AXES[tool.constraint]
    else:
        return None
    return {"a": _list(p), "b": [p[i] + direction[i] for i in range(3)]}


def _guide(g, z: float) -> dict | None:
    """A guide of the view (snapping.Guide or a dict) with three coordinates."""
    if isinstance(g, dict):
        a, b, kind, label = g.get("a"), g.get("b"), g.get("kind", ""), g.get("label", "")
    else:
        a, b, kind, label = getattr(g, "a", None), getattr(g, "b", None), getattr(g, "kind", ""), getattr(g, "label", "")
    if a is None or b is None:
        return None
    return {"a": _list(geo.point3(a, z)), "b": _list(geo.point3(b, z)), "kind": str(kind or ""), "label": str(label or "")}
