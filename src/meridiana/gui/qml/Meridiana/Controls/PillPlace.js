.pragma library

// Where the pills of lengths go on a view, the parts of the rule the plan's sides (Plan/SidePills.js) and the measures
// (Measure/MeasureLayer.qml) share: the width of a LengthPill, the two places beside a span, the overlap with the pills
// already placed, and the measures' rule (on the middle of the span, to one side when it covers another). Pure: points
// are {x, y} on the screen, boxes {x, y, width, height}.

// A LengthPill's width: the disc (badge > 0, its width) or the margin, the longer of its two lines, then the sign at the
// end (end > 0, its width: the strings' state, as far from the end as the disc from the start) or the margin.
function width(text, below, badge, xxs, xs, s, end) {
    return (badge > 0 ? xxs + badge + xs : s) + Math.max(text, below || 0) + (end > 0 ? xs + end + xxs : s)
}

// Its height: the line of the value with its margins, and the line below (0 without one).
function height(text, below, xxs) {
    return text + 2 * xxs + (below || 0)
}

function overlaps(box, placed) {
    return placed.some(function(o) {
        return box.x < o.x + o.width && box.x + box.width > o.x && box.y < o.y + o.height && box.y + box.height > o.y
    })
}

// The two centres `away` from the middle of a-b, square to it: left of a-b first, then right.
function beside(a, b, away) {
    var dx = b.x - a.x, dy = b.y - a.y, n = Math.hypot(dx, dy), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
    if (n < 1e-9) return [{x: mx, y: my}, {x: mx, y: my}]
    return [{x: mx + dy / n * away, y: my - dx / n * away}, {x: mx - dy / n * away, y: my + dx / n * away}]
}

function boxAt(c, width, height) {
    return {x: c.x - width / 2, y: c.y - height / 2, width: width, height: height}
}

// Whether the segment a-b passes through the box (Liang and Barsky's clipping).
function crosses(box, a, b) {
    var t0 = 0, t1 = 1, dx = b.x - a.x, dy = b.y - a.y
    var p = [-dx, dx, -dy, dy], q = [a.x - box.x, box.x + box.width - a.x, a.y - box.y, box.y + box.height - a.y]
    for (var i = 0; i < 4; ++i) {
        if (Math.abs(p[i]) < 1e-12) {
            if (q[i] < 0) return false
        } else {
            var r = q[i] / p[i]
            if (p[i] < 0) t0 = Math.max(t0, r)
            else t1 = Math.min(t1, r)
            if (t0 > t1) return false
        }
    }
    return true
}

// Whether two spans {a, b} are the same, either way round.
function same(l, m) {
    function at(p, q) { return Math.abs(p.x - q.x) < 1e-6 && Math.abs(p.y - q.y) < 1e-6 }
    return at(l.a, m.a) && at(l.b, m.b) || at(l.a, m.b) && at(l.b, m.a)
}

function crossesAny(box, lines) {
    return lines.some(function(l) { return crosses(box, l.a, l.b) })
}

// The first of `centres` whose box covers none of `taken`, of `marks` and of `lines` ([{a, b}], the other spans);
// else the first that covers no pill and no mark; else the first that covers no mark; else the first.
function firstFree(centres, width, height, taken, marks, lines) {
    var boxes = centres.map(function(c) { return boxAt(c, width, height) })
    var rules = [function(b) { return !overlaps(b, taken) && !overlaps(b, marks) && !crossesAny(b, lines || []) },
                 function(b) { return !overlaps(b, taken) && !overlaps(b, marks) },
                 function(b) { return !overlaps(b, marks) }]
    for (var r = 0; r < rules.length; ++r)
        for (var j = 0; j < boxes.length; ++j)
            if (rules[r](boxes[j])) return boxes[j]
    return boxes[0]
}

// The box moved inside `room` ({x, y, width, height}), `edge` from its sides, as little as it takes.
function inside(box, room, edge) {
    if (!room || room.width <= 0 || room.height <= 0) return box
    var x = Math.max(room.x + edge, Math.min(box.x, room.x + room.width - edge - box.width))
    var y = Math.max(room.y + edge, Math.min(box.y, room.y + room.height - edge - box.height))
    return {x: x, y: y, width: box.width, height: box.height}
}

// A box of `width` x `height` beyond b, past the end of the span a-b along its direction, its nearer side `gap` from b
// (the least way along the direction that clears b): the total at the end of a path (study 46, bozza 1). It goes
// further along the direction only when it covers one of `taken` (or of `lines`, the spans); kept inside `room`
// (`edge` from its sides) when one is given.
function beyond(a, b, width, height, gap, taken, lines, room, edge) {
    var dx = b.x - a.x, dy = b.y - a.y, n = Math.hypot(dx, dy)
    var ux = n > 1e-9 ? dx / n : 1, uy = n > 1e-9 ? dy / n : 0
    var across = Math.abs(ux) > 1e-9 ? (width / 2 + gap) / Math.abs(ux) : Infinity
    var along = Math.abs(uy) > 1e-9 ? (height / 2 + gap) / Math.abs(uy) : Infinity
    var near = Math.min(across, along), far = Math.max(across, along)
    var steps = [near, isFinite(far) ? far : near + height + gap]
    var centres = steps.map(function(t) { return {x: b.x + ux * t, y: b.y + uy * t} })
    return inside(firstFree(centres, width, height, taken || [], [], lines || []), room, edge || 0)
}

// The measures' pills (study 46, §3.5): `items` [{a, b, width, height}] in order. A pill goes on the middle of its span
// when the span is longer than the pill along it (and the marks of its ends), else beside it, square to it (as the
// plan's sides' measures); on the middle too it moves beside the span when it covers one already placed (`placed` too,
// the boxes of before). Beside, it keeps `gap` and half a mark (`mark`) from the line. Never over the mark of a point
// (`marks`, their boxes); clear of the other spans (`lines`, [{a, b}]) where it can. Gives the boxes, in the same order.
function onSpans(items, gap, placed, marks, mark, lines) {
    var out = [], taken = (placed || []).slice(), points = marks || [], half = (mark || 0) / 2
    for (var i = 0; i < items.length; ++i) {
        var it = items[i], dx = it.b.x - it.a.x, dy = it.b.y - it.a.y, n = Math.hypot(dx, dy)
        var ux = n > 1e-9 ? dx / n : 1, uy = n > 1e-9 ? dy / n : 0
        var away = Math.abs(uy) * it.width / 2 + Math.abs(ux) * it.height / 2 + gap + half
        var middle = {x: (it.a.x + it.b.x) / 2, y: (it.a.y + it.b.y) / 2}
        var fits = n >= Math.abs(ux) * it.width + Math.abs(uy) * it.height + 2 * (mark || 0)
        var centres = (fits ? [middle] : []).concat(beside(it.a, it.b, away))
        var others = (lines || []).filter(function(l) { return !same(l, it) })
        var box = firstFree(centres, it.width, it.height, taken, points, others)
        taken.push(box)
        out.push(box)
    }
    return out
}

function readable(degrees) { return ((degrees + 90) % 180 + 180) % 180 - 90 }
function rotatedBox(x, y, w, h, angle) {
    var r = angle * Math.PI / 180, c = Math.abs(Math.cos(r)), s = Math.abs(Math.sin(r))
    var bw = w*c+h*s, bh = w*s+h*c
    return {x: x+w/2-bw/2, y: y+h/2-bh/2, width: bw, height: bh}
}
