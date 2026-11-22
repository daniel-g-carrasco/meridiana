.pragma library
.import "CameraMath.js" as Cam

// Port of meridiana.gizmo; geometry constants are checked against mesh.py.
// Camera inputs are immutable. Drag objects retain their last valid value.
var PIXELS = 90;
var TOLERANCE = 10;
var VERTEX_TOLERANCE = 12;
var VERTEX_TOLERANCE_SELECT = 7;
var EAST = [1, 0, 0], NORTH = [0, 0, -1], UP = [0, 1, 0];
var AXES = {x: EAST, y: NORTH, z: UP};
var HANDLES = ["x", "y", "z", "xy", "rz"];
var ACTIVE = ["x", "y", "xy", "rz"];
var STEPS = {snap: 0.10, fine: 0.01, free: 0.001};
var ANGLES = {snap: 15, fine: 1, free: 0.1};
var RING_SEGMENTS = 48;
var RING_RADIUS = 0.80;
var SHAFT_START = 0.14;
var PLANE = [0.26, 0.42];

function cross(a, b) {
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
}
function length(cam, centre, h) { return PIXELS * Cam.pixelSize(cam, centre, h); }
function step(kind, mods, snaps) {
    var table = kind === "angle" ? ANGLES : STEPS;
    if (!snaps) return table.free;
    return mods.indexOf("shift") >= 0 ? table.fine : table.snap;
}
function roundEven(value) {
    var lower = Math.floor(value), part = value - lower;
    if (part < 0.5) return lower;
    if (part > 0.5) return lower + 1;
    return lower % 2 === 0 ? lower : lower + 1;
}
function stepped(value, size) {
    return size > 0 ? Number((roundEven(value / size) * size).toFixed(6)) + 0 : value;
}
function toSegment(px, py, a, b) {
    var dx = b[0] - a[0], dy = b[1] - a[1], n2 = dx * dx + dy * dy;
    var t = n2 < 1e-12 ? 0 : Math.max(0, Math.min(1, ((px - a[0])*dx + (py - a[1])*dy) / n2));
    return Math.hypot(px - (a[0] + t*dx), py - (a[1] + t*dy));
}
function inside(px, py, poly) {
    var result = false;
    for (var i = 0; i < poly.length; ++i) {
        var a = poly[i], b = poly[(i + 1) % poly.length];
        if ((a[1] > py) !== (b[1] > py) && px < a[0] + (py - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
            result = !result;
    }
    return result;
}
function ringPoints(centre, size, segments) {
    segments = segments === undefined ? RING_SEGMENTS : segments;
    var points = [], radius = RING_RADIUS * size;
    for (var i = 0; i <= segments; ++i) {
        var angle = i * (2 * Math.PI / segments);
        points.push([centre[0] + Math.cos(angle)*radius, centre[1], centre[2] - Math.sin(angle)*radius]);
    }
    return points;
}
function squarePoints(centre, size) {
    var a = PLANE[0], b = PLANE[1];
    return [[a,a], [b,a], [b,b], [a,b]].map(function(p) {
        return [centre[0] + p[0]*size, centre[1], centre[2] - p[1]*size];
    });
}
function pick(cam, px, py, w, h, centre, size, tolerance) {
    var best = tolerance === undefined ? TOLERANCE : tolerance, found = "", names = ["x", "y"];
    for (var i = 0; i < names.length; ++i) {
        var name = names[i], axis = AXES[name];
        var a = Cam.project(cam, Cam.add(centre, Cam.scale(axis, SHAFT_START * size)), w, h);
        var b = Cam.project(cam, Cam.add(centre, Cam.scale(axis, size)), w, h);
        if (a === null || b === null) continue;
        var d = toSegment(px, py, a, b);
        if (d < best) { best = d; found = name; }
    }
    var ring = ringPoints(centre, size).map(function(p) { return Cam.project(cam, p, w, h); });
    for (var j = 0; j < ring.length - 1; ++j) {
        if (ring[j] === null || ring[j + 1] === null) continue;
        var distance = toSegment(px, py, ring[j], ring[j + 1]);
        if (distance < best) { best = distance; found = "rz"; }
    }
    if (found) return found;
    var square = squarePoints(centre, size).map(function(p) { return Cam.project(cam, p, w, h); });
    if (square.every(function(p) { return p !== null; }) && inside(px, py, square)) return "xy";
    return "";
}
function along(cam, px, py, w, h, origin, axis) {
    var ray = Cam.ray(cam, px, py, w, h), o = ray[0], d = ray[1], n = cross(axis, d);
    if (Cam.norm(n) < 1e-9) return null;
    var n2 = cross(d, n);
    return Cam.dot(Cam.sub(o, origin), n2) / Cam.dot(axis, n2);
}
function onPlane(cam, px, py, w, h, origin, normal) {
    var ray = Cam.ray(cam, px, py, w, h), o = ray[0], d = ray[1], den = Cam.dot(d, normal);
    if (Math.abs(den) < 1e-9) return null;
    var distance = Cam.dot(Cam.sub(origin, o), normal) / den;
    if (distance < 0 && !cam.ortho) return null;
    return Cam.add(o, Cam.scale(d, distance));
}
function angleOn(cam, px, py, w, h, centre, zero) {
    var hit = onPlane(cam, px, py, w, h, centre, UP);
    if (hit === null) return null;
    var v = Cam.sub(hit, centre);
    if (Cam.norm(v) < 1e-9) return null;
    return Math.atan2(Cam.dot(cross(zero, v), UP), Cam.dot(zero, v)) * 180 / Math.PI;
}
function begin(handle, cam, px, py, w, h, centre) {
    var start;
    if (handle === "x" || handle === "y") {
        start = along(cam, px, py, w, h, centre, AXES[handle]);
        if (start === null) return null;
    } else if (handle === "xy" || handle === "rz") {
        var p = onPlane(cam, px, py, w, h, centre, UP);
        if (p === null) return null;
        if (handle === "xy") start = p;
        else {
            var v = Cam.sub(p, centre), n = Cam.norm(v);
            if (n <= 1e-9) return null;
            start = Cam.scale(v, 1 / n);
        }
    } else return null;
    return {handle: handle, centre: centre.slice(), start: start, value: [0, 0, 0]};
}
function update(drag, cam, px, py, w, h, mods, snaps) {
    mods = mods === undefined ? [] : mods;
    snaps = snaps === undefined ? true : snaps;
    var handle = drag.handle;
    if (handle === "x" || handle === "y") {
        var t = along(cam, px, py, w, h, drag.centre, AXES[handle]);
        if (t !== null) {
            var d = stepped(t - drag.start, step("move", mods, snaps));
            drag.value = handle === "x" ? [d, 0, 0] : [0, d, 0];
        }
    } else if (handle === "xy") {
        var p = onPlane(cam, px, py, w, h, drag.centre, UP);
        if (p !== null) {
            var v = Cam.sub(p, drag.start), size = step("move", mods, snaps);
            drag.value = [stepped(Cam.dot(v, EAST), size), stepped(Cam.dot(v, NORTH), size), 0];
        }
    } else if (handle === "rz") {
        var a = angleOn(cam, px, py, w, h, drag.centre, drag.start);
        if (a !== null) drag.value = [0, 0, stepped(a, step("angle", mods, snaps))];
    }
    return drag.value;
}
function offset(drag) { return [drag.value[0], 0, -drag.value[1]]; }
function pickPoints(cam, px, py, w, h, points, tolerance) {
    tolerance = tolerance === undefined ? VERTEX_TOLERANCE : tolerance;
    var near = [];
    for (var i = 0; i < points.length; ++i) {
        var at = Cam.project(cam, points[i], w, h);
        if (at === null) continue;
        var d = Math.hypot(px - at[0], py - at[1]);
        if (d <= tolerance) near.push([d, i]);
    }
    near.sort(function(a, b) { return a[0] - b[0] || a[1] - b[1]; });
    return near.map(function(p) { return p[1]; });
}
function beginHeight(cam, px, py, w, h, origin) {
    var t = along(cam, px, py, w, h, origin, UP);
    return t === null ? null : {origin: origin.slice(), start: t, value: 0};
}
function updateHeight(drag, cam, px, py, w, h, mods, snaps) {
    mods = mods === undefined ? [] : mods;
    snaps = snaps === undefined ? true : snaps;
    var t = along(cam, px, py, w, h, drag.origin, UP);
    if (t !== null) drag.value = stepped(t - drag.start, step("move", mods, snaps));
    return drag.value;
}
function rotation(degrees) {
    var half = degrees * Math.PI / 180 / 2;
    return [Math.cos(half), 0, Math.sin(half), 0];
}
