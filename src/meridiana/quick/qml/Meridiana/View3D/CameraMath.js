.pragma library

// Numerical port of meridiana.camera. All camera operations return a new state.
// Qt coordinates: x east, y up, z south; quaternions: [w, x, y, z].
var ANIMATION_MS = 240;
var DEGREES_PER_PIXEL = 0.35;
var ZOOM_STEP = 0.8;
var MIN_DISTANCE = 0.5;
var ELEVATION_LIMIT = 89.0;
var CLIP = 20000.0;
var VIEWS = {top: [0, -90], south: [0, 0], north: [180, 0], east: [270, 0],
             west: [90, 0], home: [30, -35]};

function add(a, b) { return a.map(function(v, i) { return v + b[i]; }); }
function sub(a, b) { return a.map(function(v, i) { return v - b[i]; }); }
function scale(a, s) { return a.map(function(v) { return v * s; }); }
function dot(a, b) { var s = 0; for (var i = 0; i < a.length; ++i) s += a[i] * b[i]; return s; }
function norm(a) { return Math.sqrt(dot(a, a)); }
function unit(a) { var n = norm(a); return n > 1e-12 ? scale(a, 1 / n) : a.slice(); }
function clamp(v, lo, hi) { return Math.min(Math.max(v, lo), hi); }
function radians(deg) { return deg * Math.PI / 180; }
function degrees(rad) { return rad * 180 / Math.PI; }
function qmul(a, b) {
    return [a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],
            a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],
            a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],
            a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]];
}
function axisAngle(axis, deg) {
    var a = scale(unit(axis), Math.sin(radians(deg) / 2));
    return [Math.cos(radians(deg) / 2), a[0], a[1], a[2]];
}
function rotate(q, v) {
    return qmul(qmul(q, [0, v[0], v[1], v[2]]), [q[0], -q[1], -q[2], -q[3]]).slice(1);
}
function slerp(a, b, t) {
    a = unit(a); b = unit(b);
    var d = dot(a, b);
    if (d < 0) { b = scale(b, -1); d = -d; }
    if (d > 0.9995) return unit(add(a, scale(sub(b, a), t)));
    var theta = Math.acos(d);
    return scale(add(scale(a, Math.sin((1 - t) * theta)), scale(b, Math.sin(t * theta))), 1 / Math.sin(theta));
}
function ease(t) { return 1 - Math.pow(1 - clamp(t, 0, 1), 3); }
function look(bearing, elevation) {
    return qmul(axisAngle([0, 1, 0], -bearing), axisAngle([1, 0, 0], elevation));
}
function create() { return {position: [0, 50, 80], rotation: look(30, -35), target: [0, 0, 0], fov: 60, ortho: false}; }
function copy(s) {
    return {position: s.position.slice(), rotation: s.rotation.slice(), target: s.target.slice(), fov: s.fov, ortho: s.ortho};
}
function forward(s) { return rotate(s.rotation, [0, 0, -1]); }
function right(s) { return rotate(s.rotation, [1, 0, 0]); }
function up(s) { return rotate(s.rotation, [0, 1, 0]); }
function bearing(s) {
    var f = forward(s);
    if (Math.hypot(f[0], f[2]) < 1e-6) f = f[1] < 0 ? up(s) : scale(up(s), -1);
    return (degrees(Math.atan2(f[0], -f[2])) + 360) % 360;
}
function elevation(s) { return degrees(Math.asin(clamp(forward(s)[1], -1, 1))); }
function halfHeight(s) {
    return Math.max(MIN_DISTANCE, dot(sub(s.target, s.position), forward(s))) * Math.tan(radians(s.fov) / 2);
}
function ray(s, px, py, w, h) {
    var x = 2 * px / w - 1, y = 1 - 2 * py / h;
    if (s.ortho) {
        var half = halfHeight(s);
        return [add(add(s.position, scale(right(s), x * half * w / h)), scale(up(s), y * half)), forward(s)];
    }
    var t = Math.tan(radians(s.fov) / 2);
    return [s.position.slice(), unit(rotate(s.rotation, [x * t * w / h, y * t, -1]))];
}
function project(s, point, w, h) {
    var v = sub(point, s.position), z = dot(v, forward(s)), x, y;
    if (s.ortho) {
        if (Math.abs(z) > CLIP) return null;
        var half = halfHeight(s);
        x = dot(v, right(s)) / (half * w / h); y = dot(v, up(s)) / half;
    } else {
        if (z <= 1e-9) return null;
        var t = Math.tan(radians(s.fov) / 2);
        x = dot(v, right(s)) / (z * t * w / h); y = dot(v, up(s)) / (z * t);
    }
    return [(x + 1) * w / 2, (1 - y) * h / 2];
}
function ground(s, px, py, w, h) {
    var r = ray(s, px, py, w, h), o = r[0], d = r[1];
    if (Math.abs(d[1]) < 1e-9) return null;
    var distance = -o[1] / d[1];
    return distance > 0 ? add(o, scale(d, distance)) : null;
}
function pivot(s, px, py, w, h, hit) {
    return hit !== null && hit !== undefined ? hit.slice() : (ground(s, px, py, w, h) || s.target.slice());
}
function keepInView(s, point, w, h) {
    var seen = project(s, point, w, h);
    if (seen && seen[0] >= 0 && seen[0] <= w && seen[1] >= 0 && seen[1] <= h) return point.slice();
    var f = forward(s), depth = dot(sub(point, s.position), f);
    if (!(depth >= MIN_DISTANCE && depth <= CLIP)) depth = Math.max(MIN_DISTANCE, dot(sub(s.target, s.position), f));
    return add(s.position, scale(f, depth));
}
function pixelSize(s, point, h) {
    if (s.ortho) return 2 * halfHeight(s) / Math.max(h, 1);
    var depth = Math.max(MIN_DISTANCE, dot(sub(point, s.position), forward(s)));
    return 2 * depth * Math.tan(radians(s.fov) / 2) / Math.max(h, 1);
}
function turn(s, q, p) {
    var result = copy(s);
    result.position = add(p, rotate(q, sub(s.position, p)));
    result.target = add(p, rotate(q, sub(s.target, p)));
    result.rotation = unit(qmul(q, s.rotation));
    return result;
}
function orbit(s, dx, dy, p, mode) {
    if (mode === "arcball") {
        var axis = unit(add(scale(up(s), dx), scale(right(s), dy)));
        return norm(axis) > 0 ? turn(s, axisAngle(axis, -Math.hypot(dx, dy) * DEGREES_PER_PIXEL), p) : copy(s);
    }
    var result = turn(s, axisAngle([0, 1, 0], -dx * DEGREES_PER_PIXEL), p);
    var elev = elevation(result), next = clamp(elev - dy * DEGREES_PER_PIXEL, -ELEVATION_LIMIT, ELEVATION_LIMIT);
    var r = right(result); r[1] = 0;
    return norm(r) > 1e-9 ? turn(result, axisAngle(r, next - elev), p) : result;
}
function pan(s, dx, dy, w, h, depthPoint) {
    var p = depthPoint === null || depthPoint === undefined ? s.target : depthPoint;
    var depth = Math.max(MIN_DISTANCE, dot(sub(p, s.position), forward(s)));
    var size = 2 * (s.ortho ? halfHeight(s) : Math.tan(radians(s.fov) / 2) * depth) / h;
    var delta = add(scale(right(s), -dx * size), scale(up(s), dy * size)), result = copy(s);
    result.position = add(s.position, delta); result.target = add(s.target, delta);
    return result;
}
function zoom(s, steps, point) {
    var f = Math.pow(ZOOM_STEP, steps), distance = norm(sub(s.position, point));
    if (distance * f < MIN_DISTANCE) f = MIN_DISTANCE / Math.max(distance, 1e-9);
    var result = copy(s);
    result.position = add(point, scale(sub(s.position, point), f));
    result.target = add(point, scale(sub(s.target, point), f));
    return result;
}
function zoomPoint(s, px, py, w, h, hit) {
    if (hit !== null && hit !== undefined) return hit.slice();
    var g = ground(s, px, py, w, h), r = ray(s, px, py, w, h), o = r[0], d = r[1], f = forward(s);
    var depth = dot(sub(s.target, o), f);
    var plane = add(o, scale(d, depth / Math.max(dot(d, f), 1e-6)));
    return g && norm(sub(g, o)) < 20 * Math.max(norm(sub(s.target, o)), 1) ? g : plane;
}
function recentre(s, point) {
    var result = copy(s);
    result.position = sub(point, scale(forward(s), norm(sub(point, s.position))));
    result.target = point.slice(); return result;
}
function fit(s, centre, radius, aspect) {
    var result = copy(s), v = radians(s.fov), hfov = 2 * Math.atan(Math.tan(v / 2) * aspect);
    var distance = radius / Math.sin(Math.min(v, hfov) / 2);
    result.position = sub(centre, scale(forward(s), distance)); result.target = centre.slice();
    return result;
}
function orient(s, bearing, elevation) {
    var result = copy(s); result.rotation = look(bearing, elevation);
    result.position = sub(s.target, scale(forward(result), norm(sub(s.position, s.target))));
    return result;
}
function view(s, name, centre, radius, aspect) {
    var result = copy(s); result.rotation = look(VIEWS[name][0], VIEWS[name][1]);
    return fit(result, centre, radius, aspect);
}
function between(a, b, t) {
    var e = ease(t), result = copy(a);
    result.position = add(a.position, scale(sub(b.position, a.position), e));
    result.target = add(a.target, scale(sub(b.target, a.target), e));
    result.rotation = slerp(a.rotation, b.rotation, e); result.ortho = t >= 1 ? b.ortho : a.ortho;
    return result;
}
