import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M

// Meridio (R619, Daniel 14/11/2026): flat slabs on one plane, without the grey disc. The geometry, the poses and the
// eyes' outlines are app/assistant/figure.py (given once by `assistantFigure`, the eyes asked again only when their
// cut changes); here the springs, the inertia and the matrices that put each slab on the screen.
// The order of drawing is the rule Daniel insisted on: the sticker's white, then every side of every slab, then the
// faces red, yellow, blue, then the eyes. A side never over another solid's face.
// The frames run only while something moves (FrameAnimation stopped once the springs settle), never with the reduced
// motion of the system, never when the window is not active.
Item {
    id: root
    // Resolve coverage after all overlapping slabs have been drawn. CurveRenderer's
    // alpha fringes accumulate at coincident edges; MSAA alone cannot undo that.
    // GeometryRenderer uses sample coverage instead. A 2x device-pixel texture also
    // keeps shallow diagonals smooth at fractional display scales (R698).
    layer.enabled: true
    layer.samples: 8
    layer.smooth: true
    layer.textureSize: Qt.size(Math.ceil(width * Screen.devicePixelRatio * 2),
                               Math.ceil(height * Screen.devicePixelRatio * 2))
    property bool animated: true
    property bool awake: true                   // the conversation open: never drowsy meanwhile
    property bool thinking: false
    property bool dragging: false
    property bool greets: false                 // waves when the window opens (the floating character only)
    property string state: thinking ? "thinking" : "idle"
    property string expression: "rest"          // what he shows (figure.EXPRESSIONS)
    property int gazeX: 0                       // where the eyes are asked to look, -1, 0, 1
    property int gazeY: 0
    readonly property var figure: Figure.data
    readonly property bool moving: animated && !Theme.reducedMotion && visible && Window.window !== null
        && Window.window.active
    readonly property bool small: width <= (figure ? figure.small : Theme.size.FIGURE)
    property bool live: false                   // the frames run (FrameAnimation), until everything has settled
    // what is drawn, published at every frame
    property var mats: []                       // for every part (figure.ORDER) its face's affine matrix, 6 numbers
    property point depth: Qt.point(0, 0)        // where the back plane is, from the front, on the screen
    property var shifts: []                     // the same in each part's plane (its matrix undone): Qt.point x 5
    property var eyeMats: [[1, 0, 0, 0, 1, 0], [1, 0, 0, 0, 1, 0]]
    property var eyeShapes: []                  // [{outline, arch, archLine}] x 2, from figure.eyes
    // the state of the springs (plain objects, not bindings: a frame writes them all)
    property var pose: ({})
    property var speed: ({})
    property var lag: ({})
    property var body: ({x: 0, y: 0, vx: 0, vy: 0, ax: 0, ay: 0, at: null, yaw: 0, pitch: 0, vyaw: 0, vpitch: 0, lastYawV: 0})
    property var eyeCache: ({})
    property string eyeKey: ""
    // the time
    property real lastUse: Date.now()
    property real heardAt: 0
    property string reaction: ""
    property real reactionUntil: 0
    property string face: ""
    property real faceUntil: 0
    property real nextFace: Date.now() + randomBetween(60000, 120000)
    property real nextBlink: Date.now() + randomBetween(4000, 8000)
    property real blinkUntil: 0
    property real nextGlance: Date.now() + randomBetween(7000, 16000)
    property point glance: Qt.point(0, 0)
    property real glanceUntil: 0
    property point lookedAt: Qt.point(0, 0)
    property bool following: false
    property real pointSince: 0
    property real pointMoved: 0
    property real since: Date.now()             // when the expression began (its own small movements)
    property bool greeted: false
    property bool ready: false                  // started (Component.onCompleted): before, nothing is computed
    implicitWidth: M.ControlMetrics.figure
    implicitHeight: M.ControlMetrics.figure

    function randomBetween(low, high) { return low + Math.random() * (high-low) }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)) }
    // the inputs of the program
    function touch() { lastUse = Date.now(); choose() }
    function hear() { heardAt = Date.now(); touch() }
    function react(name, seconds) {
        if (!ready || !figure.poses[name]) return
        reaction = name
        reactionUntil = Date.now() + 1000 * (seconds || figure.reactions[name] || 1.4)
        touch()
    }
    function lookAt(x, y) {
        const dead = figure ? figure.followDead : 0.3
        const point = Qt.point(Math.abs(x) < dead ? 0 : x > 0 ? 1 : -1, Math.abs(y) < dead ? 0 : y > 0 ? 1 : -1)
        if (!following || point.x !== lookedAt.x || point.y !== lookedAt.y) { lookedAt = point; pointSince = Date.now() }
        following = true; pointMoved = Date.now(); lastUse = Date.now()
    }
    onAwakeChanged: touch()
    onStateChanged: touch()
    onDraggingChanged: if (dragging) react("surprised")
    onWidthChanged: publish()
    onXChanged: wake()
    onYChanged: wake()
    onMovingChanged: {
        if (!moving) { gazeX = 0; gazeY = 0; following = false; face = ""; blinkUntil = 0; live = false; choose(); snap() }
        else { body.at = null; greet(); wake() }
    }
    onExpressionChanged: { since = Date.now(); wake() }
    onGazeXChanged: wake()
    onGazeYChanged: wake()
    onGreetsChanged: greet()
    Component.onCompleted: start()
    // he waves once, the first time the window shows him moving
    function greet() { if (greets && moving && !greeted && ready) { greeted = true; react("wave") } }

    function start() {
        if (!figure) return
        const keys = figure.poseKeys
        const p = {}, v = {}
        for (let i = 0; i < keys.length; i++) { p[keys[i]] = 0; v[keys[i]] = 0 }
        pose = p; speed = v
        const l = {}
        for (const name of ["hat", "face", "flap0", "flap1", "flap2"]) l[name] = {x: 0, vx: 0, y: 0, vy: 0, t: 0, vt: 0}
        lag = l
        ready = true
        choose(); snap(); greet()
    }
    // what he shows: a reaction while it holds, else the state, else what the time says
    function choose() {
        if (!ready) return
        const now = Date.now()
        let name = "rest"
        const idle = awake || state !== "idle" ? 0 : (now - lastUse) / 1000
        if (reaction && now < reactionUntil) name = reaction
        else if (state === "thinking") name = "think"
        else if (state === "answering") name = "speak"
        else if (now - heardAt < 1000 * figure.listen) name = "listen"
        else if (idle >= figure.asleep) name = "asleep"
        else if (idle >= figure.drowsy) name = "drowsy"
        else if (face && now < faceUntil) name = face
        if (!(reaction && now < reactionUntil)) reaction = ""
        if (name !== expression) { expression = name; if (!moving) snap() }
    }
    // the pose the springs go to
    function target() {
        const base = figure.poses[expression] || figure.poses.rest
        const t = Object.assign({}, base)
        const follows = expression === "rest" || expression === "speak"
        if (follows) {
            const both = gazeX !== 0 && gazeY !== 0
            t.gx = clamp(t.gx + gazeX * (both ? 0.82 : 1), -1, 1)
            t.gy = clamp(t.gy + gazeY * (both ? 0.82 : 1), -1, 1)
        }
        t.yaw += t.gx * figure.gazeTurn[0]
        t.pitch += t.gy * figure.gazeTurn[1]
        if (Date.now() < blinkUntil) t.blink = Math.max(t.blink, 1)
        return t
    }
    function snap() {
        if (!ready) return
        const t = target()
        const keys = figure.poseKeys
        for (let i = 0; i < keys.length; i++) { pose[keys[i]] = t[keys[i]]; speed[keys[i]] = 0 }
        for (const name in lag) lag[name] = {x: 0, vx: 0, y: 0, vy: 0, t: 0, vt: 0}
        body.yaw = 0; body.pitch = 0; body.vyaw = 0; body.vpitch = 0; body.vx = 0; body.vy = 0; body.ax = 0; body.ay = 0
        publish()
    }
    function wake() { if (!ready) return; if (moving) live = true; else publish() }

    // every 50 ms while visible: the timetable (blink, glance, a face now and then, the gaze that follows the pointer)
    Timer {
        interval: 50; running: root.visible && root.figure !== null; repeat: true
        onTriggered: {
            const now = Date.now()
            if (root.moving) {
                if (now >= root.nextBlink) {
                    root.blinkUntil = now + 1000 * root.figure.blink
                    root.nextBlink = now + 1000 * root.randomBetween(root.figure.blinkEvery[0], root.figure.blinkEvery[1])
                    root.wake()
                }
                if (now >= root.nextFace) {
                    const faces = root.figure.randomFaces
                    root.face = faces[Math.floor(Math.random() * faces.length)]
                    root.faceUntil = now + 1000 * (root.figure.reactions[root.face] || 1.2)
                    root.nextFace = now + 1000 * root.randomBetween(root.figure.faceEvery[0], root.figure.faceEvery[1])
                }
                if (now >= root.nextGlance) {
                    const directions = [[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]]
                    const p = directions[Math.floor(Math.random()*8)]
                    root.glance = Qt.point(p[0], p[1])
                    root.glanceUntil = now + 1000 * root.randomBetween(root.figure.glance[0], root.figure.glance[1])
                    root.nextGlance = now + 1000 * root.randomBetween(root.figure.glanceEvery[0], root.figure.glanceEvery[1])
                }
                if (root.following && now - root.pointMoved >= 1000 * root.figure.followRest) root.following = false
                if (root.following) {
                    if (now - root.pointSince >= 1000 * root.figure.followLag) { root.gazeX = root.lookedAt.x; root.gazeY = root.lookedAt.y }
                } else {
                    root.gazeX = now < root.glanceUntil ? root.glance.x : 0
                    root.gazeY = now < root.glanceUntil ? root.glance.y : 0
                }
            }
            root.choose()
        }
    }
    FrameAnimation {
        running: root.live && root.moving
        onTriggered: root.step(Math.min(0.05, Math.max(0.001, frameTime)))
    }
    // one frame: the pose's springs, the body's movement on the screen, the parts' lag, then what is drawn
    function step(dt) {
        if (!ready) return
        const t = target(), keys = figure.poseKeys
        const k = figure.poseSpring[0], c = figure.poseSpring[1]
        const n = Math.ceil(dt * 240), h = dt / n
        let restless = Date.now() < blinkUntil
        for (let i = 0; i < keys.length; i++) {
            const key = keys[i]
            let x = pose[key], v = speed[key]
            const goal = t[key]
            for (let s = 0; s < n; s++) { v += (k * (goal - x) - c * v) * h; x += v * h }
            pose[key] = x; speed[key] = v
            if (Math.abs(goal - x) > 0.002 || Math.abs(v) > 0.01) restless = true
        }
        // the body: where the item goes on the screen, turned towards where it goes; its acceleration pushes the parts
        const at = root.mapToItem(null, 0, 0), units = figure.units / Math.max(1, width)
        if (body.at === null) body.at = at
        const rvx = (at.x - body.at.x) / dt, rvy = (at.y - body.at.y) / dt
        body.at = at
        const a = Math.min(1, dt / 0.06)
        const vx = body.vx + (rvx - body.vx) * a, vy = body.vy + (rvy - body.vy) * a
        const ax = body.ax + ((vx - body.vx) / dt - body.ax) * a, ay = body.ay + ((vy - body.vy) / dt - body.ay) * a
        body.vx = vx; body.vy = vy; body.ax = ax; body.ay = ay
        const yawGoal = clamp(vx * figure.yawPerPx, -figure.yawLimit, figure.yawLimit)
        const pitchGoal = clamp(vy * figure.pitchPerPx, -figure.pitchLimit, figure.pitchLimit)
        let yawAcc = 0
        for (let s = 0; s < n; s++) {
            const before = body.vyaw
            body.vyaw += (k * 0.25 * (yawGoal - body.yaw) - c * 0.5 * body.vyaw) * h; body.yaw += body.vyaw * h
            body.vpitch += (k * 0.25 * (pitchGoal - body.pitch) - c * 0.5 * body.vpitch) * h; body.pitch += body.vpitch * h
            yawAcc += (body.vyaw - before) / dt
        }
        if (Math.abs(vx) > 1 || Math.abs(vy) > 1 || Math.abs(body.yaw) > 0.01 || Math.abs(body.pitch) > 0.01
                || Math.abs(body.vyaw) > 0.05 || Math.abs(body.vpitch) > 0.05) restless = true
        const push = ax * units + 0.55 * yawAcc, pushY = ay * units
        for (const name in lag) {
            const l = lag[name], gain = name === "hat" ? figure.turn[2] : figure.turn[3]
            for (let s = 0; s < n; s++) {
                l.vx += (-figure.lagX[0] * l.x - figure.lagX[1] * l.vx - figure.lagX[2] * push) * h; l.x += l.vx * h
                l.vy += (-figure.lagY[0] * l.y - figure.lagY[1] * l.vy - figure.lagY[2] * pushY) * h; l.y += l.vy * h
                l.vt += (-figure.turn[0] * l.t - figure.turn[1] * l.vt - gain * push) * h; l.t += l.vt * h
            }
            const limit = figure.lagLimit
            l.x = clamp(l.x, -limit, limit); l.y = clamp(l.y, -limit, limit)
            if (Math.abs(l.x) > 0.01 || Math.abs(l.y) > 0.01 || Math.abs(l.t) > 0.01 || Math.abs(l.vx) > 0.05
                    || Math.abs(l.vy) > 0.05 || Math.abs(l.vt) > 0.05) restless = true
        }
        publish()
        if (!restless && !continuous()) live = false
    }
    // the expressions that keep moving by themselves while they hold (the prototype's): speaking, happy, the wave,
    // thinking; drowsy and asleep stand still (no frames while he sleeps)
    function continuous() { return ["speak", "happy", "wave", "think"].indexOf(expression) >= 0 }
    function shown() {
        const p = Object.assign({}, pose)
        const s = (Date.now() - since) / 1000
        if (moving) {
            if (expression === "speak") { p.blink = Math.max(p.blink, 0.18 * (1 + Math.sin(s * 18)) / 2); p.faceY += 0.5 * Math.sin(s * 12) }
            if (expression === "happy") p.faceY -= 0.6 * Math.sin(s * 8)
            if (expression === "wave") { p.flap0 += 5 * Math.sin(s * 9); p.flap2 -= 5 * Math.sin(s * 9) }
            if (expression === "think") { p.flap0 += 2 * Math.sin(s * 2.4); p.flap2 -= 2 * Math.sin(s * 2.4 + 0.8) }
        }
        const turns = figure.turnLimits
        p.hairX += lag.hat.x; p.hairY += lag.hat.y; p.hat += clamp(lag.hat.t, -turns[0], turns[0])
        p.faceX += lag.face.x; p.faceY += lag.face.y
        for (const f of ["flap0", "flap1", "flap2"]) {
            p[f + "X"] += lag[f].x; p[f + "Y"] += lag[f].y; p[f] += clamp(lag[f].t, -turns[1], turns[1])
        }
        p.yaw += body.yaw; p.pitch += body.pitch
        return p
    }
    // the matrices: figure.view_matrix, compose, turn_matrix, part_matrix (the Quick tests compare them)
    readonly property real rad: Math.PI / 180
    function viewMatrix(yaw, pitch, s, ox, oy, z) {
        const cy = Math.cos(yaw * rad), sy = Math.sin(yaw * rad), cp = Math.cos(pitch * rad), sp = Math.sin(pitch * rad)
        return [s * cy, 0, ox + s * z * sy, s * sy * sp, s * cp, oy - s * z * cy * sp]
    }
    function compose(m, n) {
        return [m[0]*n[0] + m[1]*n[3], m[0]*n[1] + m[1]*n[4], m[0]*n[2] + m[1]*n[5] + m[2],
                m[3]*n[0] + m[4]*n[3], m[3]*n[1] + m[4]*n[4], m[3]*n[2] + m[4]*n[5] + m[5]]
    }
    function turnMatrix(angle, px, py, sx, sy) {
        const co = Math.cos(angle * rad), si = Math.sin(angle * rad)
        return [co, -si, px - co * px + si * py + sx, si, co, py - si * px - co * py + sy]
    }
    function partMatrix(index, p, view) {
        const key = figure.parts[index].key, pv = figure.parts[index].pivot
        // figure.turn_and_shift: the hair turns with "hat" and shifts with "hair", the face only shifts
        const angle = key === "hat" ? p.hat : key === "face" ? 0 : p[key]
        const sx = key === "hat" ? p.hairX : key === "face" ? p.faceX : p[key + "X"]
        const sy = key === "hat" ? p.hairY : key === "face" ? p.faceY : p[key + "Y"]
        return compose(view, turnMatrix(angle, pv[0], pv[1], sx, sy))
    }
    function publish() {
        if (!ready || width <= 0) return
        const p = shown()
        const s = width / figure.units, ox = width / 2, oy = height / 2 + height / 240
        const view = viewMatrix(p.yaw, p.pitch, s, ox, oy, figure.plate / 2)
        const m = []
        for (let i = 0; i < figure.parts.length; i++) m.push(partMatrix(i, p, view))
        mats = m
        const sy = Math.sin(p.yaw * rad), cy = Math.cos(p.yaw * rad), sp = Math.sin(p.pitch * rad)
        const d = Qt.point(-s * figure.plate * sy, s * figure.plate * cy * sp), w = []
        for (let i = 0; i < m.length; i++) {
            const a = m[i], det = a[0] * a[4] - a[1] * a[3]
            w.push(Qt.point((a[4] * d.x - a[1] * d.y) / det, (a[0] * d.y - a[3] * d.x) / det))
        }
        depth = d; shifts = w
        const face = m[3], e = []
        for (let i = 0; i < 2; i++) {
            const cx = figure.eyes[i][0] + p.faceX + clamp(p.gx, -1, 1) * figure.gazeReach[0]
            const cyy = figure.eyes[i][1] + p.faceY + clamp(p.gy, -1, 1) * figure.gazeReach[1]
            e.push(compose(face, [1, 0, cx, 0, 1, cyy]))
        }
        eyeMats = e
        const values = {}, parts = []
        for (const key of figure.eyeKeys) { values[key] = p[key]; parts.push(Math.round(p[key] * 100)) }
        const id = parts.join(",") + (small ? "s" : "l")
        if (id !== eyeKey) {
            if (!eyeCache[id]) eyeCache[id] = Figure.eyes(values, small)
            eyeKey = id
            eyeShapes = eyeCache[id]
        }
    }
    // the box of what he draws now, in his own coordinates (the white border and the sign included): for the tests
    // that check he is drawn whole (R612), no longer a disc filling his square
    function extent() {
        if (!ready || mats.length === 0) return Qt.rect(0, 0, 0, 0)
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
        const layers = [[figure.outlines, [0, 1]]]
        layers.push([small ? figure.stickers : figure.stickersLarge, figure.stickerCopies])
        for (const layer of layers) {
            for (let i = 0; i < mats.length; i++) {
                const m = mats[i], outline = layer[0][i]
                for (const t of layer[1]) {
                    for (let k = 0; k < outline.length; k++) {
                        const q = outline[k]
                        const x = m[0] * q.x + m[1] * q.y + m[2] + depth.x * t, y = m[3] * q.x + m[4] * q.y + m[5] + depth.y * t
                        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y)
                    }
                }
            }
        }
        return Qt.rect(x0, y0, x1 - x0, y1 - y0)
    }
    function matrix(m, t) {
        return m ? Qt.matrix4x4(m[0], m[1], 0, m[2] + depth.x * t, m[3], m[4], 0, m[5] + depth.y * t,
                                0, 0, 1, 0, 0, 0, 0, 1) : Qt.matrix4x4()
    }

    // A copy of a slab's outline `at` deep (0 the front, 1 the back): in its part's plane, under the part's matrix, the
    // depth is a shift (publish, `shifts`), so that a frame changes one matrix a part and layer, and the copies' x, y
    component Slab: Shape {
        id: slab
        property int part: 0
        property real at: 0
        property alias colour: path.fillColor
        property var outline: []
        x: at === 0 || !root.shifts[part] ? 0 : at * root.shifts[part].x
        y: at === 0 || !root.shifts[part] ? 0 : at * root.shifts[part].y
        width: root.width; height: root.height
        preferredRendererType: Shape.GeometryRenderer
        ShapePath { id: path; strokeColor: "transparent"; strokeWidth: 0; PathPolyline { path: slab.outline } }
    }
    component Layer: Item {
        id: layer
        required property int index
        readonly property int part: index
        transform: Matrix4x4 { matrix: root.matrix(root.mats[layer.part], 0) }
    }
    // the sticker's white border, under everything: the outline grown by the border, on the front, middle, back
    Repeater {
        model: root.figure ? root.figure.parts.length : 0
        Layer {
            id: stickerLayer
            Repeater {
                model: root.figure.stickerCopies
                Slab {
                    required property real modelData
                    part: stickerLayer.part; at: modelData
                    colour: root.figure.white
                    outline: root.small ? root.figure.stickers[part] : root.figure.stickersLarge[part]
                }
            }
        }
    }
    // every side of every slab: copies of its outline from the back plane to just behind the front
    Repeater {
        model: root.figure ? root.figure.parts.length : 0
        Layer {
            id: sideLayer
            Repeater {
                model: root.figure.sideCopies
                Slab {
                    required property int index
                    part: sideLayer.part; at: (root.figure.sideCopies - index) / root.figure.sideCopies
                    colour: root.figure.parts[part].side
                    outline: root.figure.outlines[part]
                }
            }
        }
    }
    // the faces: red, yellow, blue
    Repeater {
        model: root.figure ? root.figure.parts.length : 0
        Layer {
            id: faceLayer
            Slab { part: faceLayer.part; colour: root.figure.parts[part].colour; outline: root.figure.outlines[part] }
        }
    }
    // the eyes, full black, and surprise's thin arch
    Repeater {
        model: root.eyeShapes.length
        Item {
            id: eye
            required property int index
            readonly property var shape: root.eyeShapes[index]
            transform: Matrix4x4 { matrix: root.matrix(root.eyeMats[eye.index], 0) }
            Shape {
                width: root.width; height: root.height
                preferredRendererType: Shape.GeometryRenderer
                ShapePath {
                    fillColor: root.figure ? root.figure.ink : "black"; strokeColor: "transparent"; strokeWidth: 0
                    PathPolyline { path: eye.shape ? eye.shape.outline : [] }
                }
            }
            Shape {
                visible: eye.shape && eye.shape.arch.length > 0
                width: root.width; height: root.height
                preferredRendererType: Shape.GeometryRenderer
                ShapePath {
                    fillColor: "transparent"; strokeColor: root.figure ? root.figure.ink : "black"
                    strokeWidth: eye.shape ? eye.shape.archLine : 1
                    capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                    PathPolyline { path: eye.shape ? eye.shape.arch : [] }
                }
            }
        }
    }
}
