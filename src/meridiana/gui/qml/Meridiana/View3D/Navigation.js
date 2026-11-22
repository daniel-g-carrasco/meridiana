.pragma library

// Port of meridiana.navigation.Navigator. The backend serializes Style, so the
// fourteen style tables remain in the core. Only event state lives here.
var CLICK_PX = 4;
function same(a, b) {
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; ++i) if (b.indexOf(a[i]) < 0) return false;
    return true;
}
function contains(gestures, buttons, mods) {
    for (var i = 0; i < gestures.length; ++i)
        if (same(gestures[i][0], buttons) && same(gestures[i][1], mods)) return true;
    return false;
}
function create(style) {
    var nav = {style: style, mods: []}; reset(nav); return nav;
}
function reset(nav) {
    nav.held = []; nav.start = null; nav.last = null; nav.gesture = "";
    nav.moved = false; nav.swallow = ""; nav.before = ""; nav.spent = false;
}
function setStyle(nav, style) { nav.style = style; reset(nav); }
function match(nav, buttons, mods) {
    var kinds = ["orbit", "pan", "zoom"];
    for (var i = 0; i < kinds.length; ++i)
        if (contains(nav.style[kinds[i]] || [], buttons, mods)) return kinds[i];
    if (same(mods, ["space"]) && (same(buttons, []) || same(buttons, ["left"]))) return "pan";
    if (same(mods, ["shift"]) && same(buttons, ["left"])) return "orbit";
    return "";
}
function drags(nav, buttons, mods) { return match(nav, buttons, mods) !== ""; }
function chorded(nav, button) {
    var gestures = nav.style.pan.concat(nav.style.orbit, nav.style.zoom);
    for (var i = 0; i < gestures.length; ++i)
        if (gestures[i][0].length > 1 && gestures[i][0].indexOf(button) >= 0) return true;
    return false;
}
function previewsOrbit(nav, mods) {
    if (nav.held.length || nav.gesture) return false;
    for (var i = 0; i < nav.style.orbit.length; ++i) {
        var g = nav.style.orbit[i];
        if (g[0].length && g[1].length && same(g[1], mods)) return true;
    }
    return false;
}
function action(kind, phase, x, y, mods, dx, dy) {
    return {kind: kind, phase: phase, x: x, y: y, dx: dx || 0, dy: dy || 0, mods: mods.slice()};
}
function switchGesture(nav, x, y) {
    var out = [], kind = (nav.moved || !nav.held.length) && !nav.spent ? match(nav, nav.held, nav.mods) : "";
    if (kind !== nav.gesture) {
        if (nav.gesture) out.push(action(nav.gesture, "end", x, y, nav.mods));
        nav.gesture = kind;
        if (kind) out.push(action(kind, "begin", x, y, nav.mods));
    }
    return out;
}
function press(nav, button, mods, x, y) {
    nav.mods = mods.slice();
    if (!nav.held.length) { nav.start = [x, y]; nav.moved = false; }
    else nav.before = nav.gesture;
    if (nav.held.indexOf(button) < 0) nav.held.push(button);
    nav.last = [x, y];
    return nav.gesture ? switchGesture(nav, x, y) : [];
}
function move(nav, x, y, mods) {
    if (mods !== undefined && mods !== null) nav.mods = mods.slice();
    var out = [];
    if (!nav.last) nav.last = [x, y];
    if (nav.held.length && !nav.moved && nav.start)
        if (Math.abs(x - nav.start[0]) + Math.abs(y - nav.start[1]) > CLICK_PX) nav.moved = true;
    if (!nav.held.length && !match(nav, [], nav.mods) && !nav.gesture) { nav.last = [x, y]; return out; }
    if (nav.moved || !nav.held.length) out = switchGesture(nav, x, y);
    if (nav.gesture) out.push(action(nav.gesture, "move", x, y, nav.mods, x - nav.last[0], y - nav.last[1]));
    nav.last = [x, y]; return out;
}
function click(nav, button, x, y) {
    var kind = "";
    if (button === "left" && contains(nav.style.select, ["left"], nav.mods)) kind = "select";
    else if (button === "middle") kind = nav.style.middle_click;
    else if (button === "right") kind = nav.style.right_click;
    return kind ? [action(kind, "once", x, y, nav.mods)] : [];
}
function release(nav, button, mods, x, y) {
    nav.mods = mods.slice();
    var out = [], was = nav.held.slice(), index = nav.held.indexOf(button);
    if (index >= 0) nav.held.splice(index, 1);
    if (nav.gesture) {
        if (!nav.held.length) { out.push(action(nav.gesture, "end", x, y, nav.mods)); nav.gesture = ""; }
        else {
            var next = match(nav, nav.held, nav.mods);
            if (next !== "" && next !== nav.before) {
                out.push(action(nav.gesture, "end", x, y, nav.mods)); nav.gesture = ""; nav.spent = true;
            } else out = switchGesture(nav, x, y);
        }
    } else if (button === nav.swallow) nav.swallow = "";
    else if (!nav.moved && same(was, [button])) out = click(nav, button, x, y);
    if (!nav.held.length) { nav.start = null; nav.moved = false; nav.spent = false; nav.before = ""; }
    return out;
}
function doubleClick(nav, button, mods, x, y) {
    if (button === "middle" && nav.style.middle_double) {
        nav.swallow = button; return [action(nav.style.middle_double, "once", x, y, mods)];
    }
    return [];
}
function wheel(nav, steps, mods, x, y) { return [action("wheel", "once", x, y, mods, 0, steps)]; }
function wheelAction(angle, pixel, phased, synthesized, ctrl, touchpad) {
    var steps = angle[1] ? angle[1] / 120 : pixel[1] / 60;
    if (ctrl) return ["zoom", 0, steps];
    var hasPixels = pixel[0] !== 0 || pixel[1] !== 0;
    if (touchpad || phased || synthesized || angle[0] || (hasPixels && !angle[0] && !angle[1])) {
        var delta = phased || hasPixels ? pixel : angle;
        return ["pan", delta[0], delta[1]];
    }
    return ["wheel", 0, steps];
}
