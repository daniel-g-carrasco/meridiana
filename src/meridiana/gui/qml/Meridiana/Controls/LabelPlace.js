.pragma library
.import "PillPlace.js" as Pill

// Where a measure's written length goes on a view (R609, Daniel 14/11/2026: «semplici scritte allineate con le linee
// di misurazione»), as a dimension of a technical drawing: along the span a-b, turned as it is and never upside down
// (read from left to right, or from the bottom up), centred on its middle and `gap` from the line on the side the
// text's top faces, `pointGap` when the span is shorter than the text (so that it clears the marks of its ends); a
// span seen end on (a height in the plan) has its text level, `pointGap` above the point. The box
// is kept inside `room` ({x, y, width, height}), `edge` from its sides, as little as it takes. Pure: points are {x, y}
// on the screen. Gives {x, y} the centre, `angle` in degrees (Qt's: clockwise, in [-90, 90)) and `box` the upright
// bounds of the turned text.

function along(a, b, width, height, gap, pointGap, room, edge) {
    var dx = b.x - a.x, dy = b.y - a.y, n = Math.hypot(dx, dy)
    var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
    var angle = 0, cx = mx, cy = my - (pointGap + height / 2)
    if (n >= 1e-6) {
        angle = Math.atan2(dy, dx) * 180 / Math.PI
        if (angle >= 90) angle -= 180
        else if (angle < -90) angle += 180
        var r = angle * Math.PI / 180, away = (n < width + 2 * pointGap ? pointGap : gap) + height / 2
        cx = mx + Math.sin(r) * away                       // the text's top faces (sin, -cos)
        cy = my - Math.cos(r) * away
    }
    var r2 = angle * Math.PI / 180, c = Math.abs(Math.cos(r2)), s = Math.abs(Math.sin(r2))
    var bw = width * c + height * s, bh = width * s + height * c
    if (room && room.width > 0 && room.height > 0) {
        var e = edge || 0
        cx = Math.max(room.x + e + bw / 2, Math.min(cx, room.x + room.width - e - bw / 2))
        cy = Math.max(room.y + e + bh / 2, Math.min(cy, room.y + room.height - e - bh / 2))
    }
    return {x: cx, y: cy, angle: angle, box: {x: cx - bw / 2, y: cy - bh / 2, width: bw, height: bh}}
}

// R618 (Daniel 14/11/2026: «c'è una linea corta nella quale la misura si accavalla alla linea di fianco... non mi
// piace il fatto che il totale sia insieme alla riga dell'ultima misura»): the words of all the spans of a view laid
// out together, in the screen's pixels, again at every change of the view. A word goes
//   1. on its span (as along() above, centred) when the span is as long as the text and a `margin` at each end, and it
//      touches nothing: the other spans (their halo), the marks of the points, the words and pills placed before it;
//      on the side the text's top faces, else on the other side;
//   2. else out of the span, on its line past the freer end (a dimension of a drawing with its text outside), when the
//      span is at least `outMin` long and the word touches nothing there;
//   3. else hidden: the host draws a small sign across the middle of the span and shows the number on hover.
// A span seen end on (a height in the plan) has its word level above its point when that touches nothing, else hidden.
// The words on their spans are placed first, then the totals, then the words out of their spans: a span that can carry
// its word keeps it, and a path's total counts more than a number written away from its span. The
// hysteresis: a word changes place only `hysteresis` pixels past the limit (longer to come back, clearer of the rest),
// so that it does not go back and forth at the limit; `previous` holds the places of before by key.
// The total of a path (totals) is a pill at the path's end, upright, in the first of eight directions around the end
// (along the last span first, then turning away from it) where it touches nothing; else hidden as a word.
//
// scene: {lines: [{a, b}] every span drawn, marks: [{x, y}], halo (half the width of a span with its halo), mark (half
// a mark), gap, margin, hysteresis, outMin, room, edge, taken: [] the boxes placed, which grows}. Boxes are turned
// rectangles {cx, cy, hw, hh, c, s, angle} with their upright bounds (x0, y0, x1, y1: the broad look that leaves out
// at once what is far, before the exact one); `bounds(box)` gives the upright bounds as a rect.

function shape(cx, cy, w, h, angle) {
    var r = angle * Math.PI / 180, c = Math.cos(r), s = Math.sin(r)
    var bw = (w * Math.abs(c) + h * Math.abs(s)) / 2, bh = (w * Math.abs(s) + h * Math.abs(c)) / 2
    return {cx: cx, cy: cy, hw: w / 2, hh: h / 2, c: c, s: s, angle: angle,
            x0: cx - bw, y0: cy - bh, x1: cx + bw, y1: cy + bh}
}

function local(o, p) {
    var dx = p.x - o.cx, dy = p.y - o.cy
    return {x: dx * o.c + dy * o.s, y: -dx * o.s + dy * o.c}
}

function bounds(o) {
    return {x: o.x0, y: o.y0, width: o.x1 - o.x0, height: o.y1 - o.y0}
}

function corners(o) {
    return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(function(k) {
        var x = k[0] * o.hw, y = k[1] * o.hh
        return {x: o.cx + x * o.c - y * o.s, y: o.cy + x * o.s + y * o.c}
    })
}

// whether the span a-b, `pad` thick on each side, touches the box
function hitsLine(o, a, b, pad) {
    if (Math.max(a.x, b.x) + pad < o.x0 || Math.min(a.x, b.x) - pad > o.x1
            || Math.max(a.y, b.y) + pad < o.y0 || Math.min(a.y, b.y) - pad > o.y1) return false
    return Pill.crosses({x: -o.hw - pad, y: -o.hh - pad, width: 2 * (o.hw + pad), height: 2 * (o.hh + pad)},
                        local(o, a), local(o, b))
}

function hitsPoint(o, p, r) {
    if (p.x + r < o.x0 || p.x - r > o.x1 || p.y + r < o.y0 || p.y - r > o.y1) return false
    var q = local(o, p)
    return Math.abs(q.x) <= o.hw + r && Math.abs(q.y) <= o.hh + r
}

// two turned boxes closer than `pad` (separating axes)
function hitsBox(o, p, pad) {
    if (o.x1 + pad <= p.x0 || p.x1 + pad <= o.x0 || o.y1 + pad <= p.y0 || p.y1 + pad <= o.y0) return false
    var axes = [[o.c, o.s], [-o.s, o.c], [p.c, p.s], [-p.s, p.c]], co = corners(o), cp = corners(p)
    for (var i = 0; i < 4; ++i) {
        var ax = axes[i][0], ay = axes[i][1], a0 = Infinity, a1 = -Infinity, b0 = Infinity, b1 = -Infinity
        for (var k = 0; k < 4; ++k) {
            var u = co[k].x * ax + co[k].y * ay, v = cp[k].x * ax + cp[k].y * ay
            a0 = Math.min(a0, u); a1 = Math.max(a1, u); b0 = Math.min(b0, v); b1 = Math.max(b1, v)
        }
        if (a1 + pad <= b0 || b1 + pad <= a0) return false
    }
    return true
}

function keepIn(o, room, edge) {
    if (!room || room.width <= 0 || room.height <= 0) return o
    var b = bounds(o), e = edge || 0
    var x = Math.max(room.x + e, Math.min(b.x, room.x + room.width - e - b.width))
    var y = Math.max(room.y + e, Math.min(b.y, room.y + room.height - e - b.height))
    if (x === b.x && y === b.y) return o
    return shape(o.cx + x - b.x, o.cy + y - b.y, 2 * o.hw, 2 * o.hh, o.angle)
}

function same(p, q) { return Math.abs(p.x - q.x) < 0.5 && Math.abs(p.y - q.y) < 0.5 }

// whether the box touches nothing, `pad` clear: the spans but `own` (an index of scene.lines, -1 none), the marks but
// those on `ends` (the place of the box already keeps clear of them), the boxes taken
function clear(o, pad, scene, own, ends) {
    var i, lines = scene.lines, marks = scene.marks, taken = scene.taken
    for (i = 0; i < lines.length; ++i)
        if (i !== own && hitsLine(o, lines[i].a, lines[i].b, scene.halo + pad)) return false
    for (i = 0; i < marks.length; ++i) {
        var m = marks[i]
        if (!hitsPoint(o, m, scene.mark + pad)) continue
        var skip = false
        for (var k = 0; k < ends.length; ++k) if (same(ends[k], m)) { skip = true; break }
        if (!skip) return false
    }
    for (i = 0; i < taken.length; ++i)
        if (hitsBox(o, taken[i], pad)) return false
    return true
}

// how many spans other than `own` end at p
function joined(p, scene, own) {
    var n = 0
    for (var i = 0; i < scene.lines.length; ++i)
        if (i !== own && (same(scene.lines[i].a, p) || same(scene.lines[i].b, p))) ++n
    return n
}


// A span's word as seen now: its line, its angle (never upside down), its middle, the unit square to it (for the sign)
// and its place on the span (`on`, unclamped): `gap` from the line on the side the text's top faces; a span seen end
// on (a height in the plan, from above: shorter than half a pixel) has its word level above its point, clear of the
// mark.
function geometry(a, b, width, height, scene, under) {
    var dx = b.x - a.x, dy = b.y - a.y, n = Math.hypot(dx, dy)
    var ux = n > 1e-6 ? dx / n : 1, uy = n > 1e-6 ? dy / n : 0
    var angle = n > 1e-6 ? Math.atan2(dy, dx) * 180 / Math.PI : 0
    if (angle >= 90) angle -= 180
    else if (angle < -90) angle += 180
    var r = angle * Math.PI / 180, away = scene.gap + height / 2, mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
    var endOn = n < 0.5
    return {a: a, b: b, ux: ux, uy: uy, length: n, angle: endOn ? 0 : angle, endOn: endOn,
            mid: {x: mx, y: my}, nx: -uy, ny: ux,
            on: endOn ? shape(mx, my - (scene.mark + scene.gap + height / 2), width, height, 0)
                      : shape(mx + Math.sin(r) * away, my - Math.cos(r) * away, width, height, angle),
            // the other side of the span, where the text's top faces the line: when the first touches something
            under: endOn || !under ? null
                                   : shape(mx - Math.sin(r) * away, my + Math.cos(r) * away, width, height, angle)}
}

// the word out of its span, on its line past the end `name` ("a" or "b"), `margin` from the end's point
function outside(g, name, width, height, scene) {
    var s = name === "a" ? -1 : 1, p = name === "a" ? g.a : g.b, t = scene.margin + width / 2
    return shape(p.x + s * g.ux * t, p.y + s * g.uy * t, width, height, g.angle)
}

// A word where the layout put it (`mode`, `end`), from the span as seen now: what each word's binding asks at every
// step of the view (cheap, no look at the others), while the layout (words(), below) runs once the view has moved.
// Gives {mode, end, x, y (the centre), angle, box (upright bounds), shape, mid, nx, ny, length}.
function wordAt(a, b, width, height, mode, end, scene) {
    var g = geometry(a, b, width, height, scene, mode === "on" && end === "under")
    var o = keepIn(mode === "out" ? outside(g, end, width, height, scene) : end === "under" && g.under ? g.under : g.on,
                   scene.room, scene.edge)
    return {mode: mode, end: end || "", x: o.cx, y: o.cy, angle: g.angle, box: bounds(o), shape: o, mid: g.mid,
            nx: g.nx, ny: g.ny, length: g.length}
}

// The total's pill turned `turn` (0-7) from the last span's direction around the path's end `end` (`from` the point
// before it), clear of the end's mark: {x, y the top left corner, box, shape}.
var TURNS = [0, 45, -45, 90, -90, 135, -135, 180]
function totalAt(end, from, width, height, turn, scene) {
    var dx = end.x - from.x, dy = end.y - from.y, n = Math.hypot(dx, dy)
    var r = (n > 1e-6 ? Math.atan2(dy, dx) : 0) + TURNS[turn] * Math.PI / 180, vx = Math.cos(r), vy = Math.sin(r)
    var away = scene.mark + (scene.totalGap === undefined ? scene.gap : scene.totalGap)
    var tx = Math.abs(vx) > 1e-6 ? (width / 2 + away) / Math.abs(vx) : Infinity
    var ty = Math.abs(vy) > 1e-6 ? (height / 2 + away) / Math.abs(vy) : Infinity
    var t = Math.min(tx, ty)
    var o = keepIn(shape(end.x + vx * t, end.y + vy * t, width, height, 0), scene.room, scene.edge)
    var b = bounds(o)
    return {x: b.x, y: b.y, box: b, shape: o}
}

// items: [{key, line (its span: an index of scene.lines), width, height}] the words' sizes as laid out. Gives, in the
// same order, {key, mode ("on", "out", "hidden"), end ("a", "b" when out; "" or "under", the side, when on)}; adds the
// boxes placed to scene.taken.
// `between(scene)`, when given, is called after the words on their spans and before those out of them.
function words(items, scene, previous, between) {
    var H = scene.hysteresis, before = previous || {}
    var out = items.map(function(it) {
        var l = scene.lines[it.line]
        return {key: it.key, item: it, g: geometry(l.a, l.b, it.width, it.height, scene, true),
                was: before[it.key] || {}, mode: "hidden", end: ""}
    })
    out.forEach(function(w) {
        var g = w.g, was = w.was.mode === "on", need = w.item.width + 2 * scene.margin
        if (!g.endOn && g.length < need + (was ? 0 : H)) return
        // the side the text's top faces first (the side of before at a tie), then the other ("under")
        var sides = g.under ? (was && w.was.end === "under" ? ["under", ""] : ["", "under"]) : [""]
        for (var k = 0; k < sides.length; ++k) {
            var o = keepIn(sides[k] === "under" ? g.under : g.on, scene.room, scene.edge)
            if (clear(o, was && w.was.end === sides[k] ? 0 : H / 2, scene, w.item.line, [g.a, g.b])) {
                w.mode = "on"; w.end = sides[k]; scene.taken.push(o)
                return
            }
        }
    })
    // what goes before the words out of their spans (the totals: a path's total counts more than a span's number
    // written away from it)
    if (between) between(scene)
    out.forEach(function(w) {
        var g = w.g, was = w.was.mode === "out"
        if (w.item.outside === false || w.mode !== "hidden" || g.endOn || g.length < scene.outMin + (was ? 0 : H)) return
        var ends = [{name: "a", joined: joined(g.a, scene, w.item.line)},
                    {name: "b", joined: joined(g.b, scene, w.item.line)}]
        // the freer end first (fewer spans meeting there); at a tie the end of before, else b (the later point)
        var first = was ? w.was.end : "b"
        ends.sort(function(e, f) {
            if (e.joined !== f.joined) return e.joined - f.joined
            return (e.name === first ? -1 : 0) - (f.name === first ? -1 : 0)
        })
        for (var k = 0; k < 2; ++k) {
            var name = ends[k].name
            var o = keepIn(outside(g, name, w.item.width, w.item.height, scene), scene.room, scene.edge)
            if (clear(o, was && name === w.was.end ? 0 : H / 2, scene, w.item.line, [g.a, g.b])) {
                w.mode = "out"; w.end = name; scene.taken.push(o)
                return
            }
        }
    })
    return out.map(function(w) { return {key: w.key, mode: w.mode, end: w.end} })
}

// items: [{key, end: {x, y} the path's last point, from: {x, y} the point before it, width, height}]. Gives, in the
// same order, {key, mode ("on", "hidden"), turn (the direction taken, 0-7)}; adds the pills placed to scene.taken.
function totals(items, scene, previous) {
    var H = scene.hysteresis, before = previous || {}
    return items.map(function(it) {
        // the directions in their order, the one of before kept while it touches nothing, another taken only when it is
        // clear by the hysteresis (so that the pill comes back along the last span once there is room, without flicker)
        var was = before[it.key] || {}
        for (var k = 0; k < TURNS.length; ++k) {
            var o = totalAt(it.end, it.from, it.width, it.height, k, scene).shape
            if (clear(o, was.mode === "on" && k === was.turn ? 0 : H / 2, scene, -1, [it.end])) {
                scene.taken.push(o)
                return {key: it.key, mode: "on", turn: k}
            }
        }
        return {key: it.key, mode: "hidden", turn: 0}
    })
}

// the places of now by key ({mode, end, turn}), for the views' words and for the next layout's hysteresis
function memory(list, into) {
    var out = into || {}
    list.forEach(function(w) { out[w.key] = {mode: w.mode, end: w.end || "", turn: w.turn || 0} })
    return out
}
