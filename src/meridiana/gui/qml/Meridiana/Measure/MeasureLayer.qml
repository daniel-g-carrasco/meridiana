import QtQuick
import QtQuick.Window
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M
// The measuring tool drawn on a view (study 46, state of r34-righello section 2): the one component that draws the
// measures, in the plan (Plan/ToolOverlay.qml) and in the 3D view. It knows nothing of the view: `measure` is the
// window's MeasureBridge (gui/backend/measure.py), `view` the name the view registered with it, `toScreen(p)` takes a
// point [East, North, height] to the view's point, `revision` is the view's camera (bound by the host, so that the
// points follow it), `colors` the view's (draw, halo, guide, sel, label_bg, label_fg).
// What it draws: the spans of the measurements made and of the one in hand, the span to the pointer dashed, the mark of
// each point by what it snapped to (square vertex, triangle midpoint, hourglass edge, circle free, rhombus face, cross
// intersection, a T upside down perpendicular), the guides, the reference edge lit in the selection's colour, the
// dotted references (a height's source), the number of each span written along it (M.SpanLabel, R609) where it fits
// (R618: else out of the span, else a sign that shows it on hover), the total of a path in a pill at its end (R618), and
// the small words beside the pointer.
// Light at every step of the pointer: what the step does not change (the measurements made, the points placed, their
// marks and numbers) keeps its items; only the span to the pointer, its number, the guides and the words beside the
// pointer follow it.
Item {
    id: measures
    objectName: "measureLayer"
    // One multisampled overlay per view: smooth strokes on the native RHI backend too.
    layer.enabled: true
    layer.samples: Theme.annotation.SAMPLES
    property var measure: null
    property string view: "plan"
    property var toScreen: function(p) { return Qt.point(p[0], p[1]) }
    property real revision: 0
    property var colors: ({})
    // the pills of the measurements made take a click (the host's Select tool): it chooses the measurement by the rule
    // of the selection (measure.select); with Measure in hand they take none, the click measures through them
    property bool picking: false
    signal picked()             // a pill was clicked: the host gives its view the keys (Delete, Ctrl+C, Esc)
    // the rule of place of what is written over a view (R555 (1), Plan.clearOfChrome): a pill tied to a place of the
    // drawing is not drawn while it would touch the view's chrome. The host gives its rule, in the layer's own
    // coordinates (the plan's layer fills the plan); none: every pill is drawn
    property var obstacles: []
    property var clearOf: null
    function clear(x, y, w, h) { return !clearOf || clearOf(x, y, w, h) }
    // the 3D view while the pointer moves (it looks for no point then): the pointer on the screen, the span to it
    // drawn there without numbers until the view finds the point under it; null in the plan, and at rest
    property var pointerScreen: null
    readonly property bool following: pointerScreen !== null && !!placed && (placed.marks || []).length > 0
    readonly property var display: { const seen = measure ? measure.revision : 0; return measure ? measure.display(view) : ({}) }
    readonly property var done: { const seen = measure ? measure.doneRevision : 0; return measure ? measure.done(view) : [] }
    // the points placed of the measurement in hand ({marks, segments, closed}): asked only when they change
    readonly property var placed: { const seen = measure ? measure.placedRevision : 0; return measure ? measure.placed(view) : null }
    readonly property var current: display.current || null
    readonly property var elastic: current ? current.elastic || null : null
    readonly property real mark: M.ControlMetrics.measureMark
    readonly property real line: M.ControlMetrics.measureLine
    readonly property real halo: M.ControlMetrics.measureLine + M.ControlMetrics.measureHalo
    // A 3D host supplies solid visibility; the plan leaves the world path whole.
    property var visibleParts: null
    property var pointVisible: null
    property var worldAtScreen: null
    property var worldOnFollow: null
    function portions(a, b) { const camera=revision; return visibleParts ? visibleParts(a,b) : [{a:a,b:b}] }
    function seen(p) { const camera=revision; return !pointVisible || pointVisible(p) }
    function projectedParts(a,b) { return portions(a,b).map(function(s) { return [at(s.a),at(s.b)] }) }
    function at(p) { const camera = revision; return toScreen(p) }
    function mapped(points, closed) {
        const out = points.map(function(p) { return at(p) })
        return closed && out.length ? out.concat([out[0]]) : out
    }
    function path(m) { return m ? mapped((m.marks || []).map(function(k) { return k.at }), m.closed) : [] }
    function paths(list, selected) {
        const out=[]
        list.filter(function(m) { return !!m.selected === selected }).forEach(function(m) {
            (m.segments || []).forEach(function(s) { out.push.apply(out, projectedParts(s.a,s.b)) })
        })
        return out
    }
    // the outline of a point's mark by its kind, centred on c
    function markPath(kind, c) { return M.ViewMarks.path(kind,c,mark/2) }
    function guidePoints(guide) {
        const a = at(guide.a), b = at(guide.b)
        if (guide.kind === "constraint") return [a, b]
        const dx = b.x-a.x, dy = b.y-a.y, length = Math.hypot(dx, dy)
        if (length < 1e-6) return [a, b]
        const extension = Math.hypot(width, height)/length     // past the view's edge, no further: fewer dashes
        return [guide.kind === "tracking" ? Qt.point(a.x-dx*extension, a.y-dy*extension) : a,
                Qt.point(b.x+dx*extension, b.y+dy*extension)]
    }
    function guides(constraint) {
        return (display.guides || []).filter(function(g) { return (g.kind === "constraint") === constraint })
                                     .reduce(function(out,g) { return out.concat(visibleParts ? projectedParts(g.a,g.b) : [guidePoints(g)]) }, [])
    }
    // R609 (Daniel 14/11/2026: «le varie pillole e popup sono troppo invasive; avrei preferito delle semplici scritte
    // allineate con le linee di misurazione»): every span writes its number along itself (M.SpanLabel); the rest is in
    // the hint bar (measure_tool.hint). R618: the words laid out together (`places`, below), the total in a pill
    readonly property var doneSegments: {
        const out = []
        done.forEach(function(m) {
            (m.segments || []).forEach(function(s, i) {
                out.push({a: s.a, b: s.b, pill: s.pill, selected: !!m.selected, id: m.id, key: "d" + m.id + ":" + i})
            })
        })
        return out
    }
    readonly property var doneMarks: {
        const out = []
        done.forEach(function(m) { (m.marks || []).forEach(function(k) { out.push(k) }) })
        return out
    }
    FontMetrics { id: wordMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE; font.weight: Theme.annotation.WEIGHT }
    FontMetrics { id: pillMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE }
    function shownText(pill) {
        const value = pill ? pill.label || pill.text || "" : ""
        return (pill && pill.approx && value.indexOf("≈") !== 0 ? "≈" : "") + value
    }
    function wordSize(pill) {
        return {width: Math.ceil(wordMetrics.advanceWidth(shownText(pill)) + 2*Theme.space.S),
                height: Math.ceil(wordMetrics.height + 2*Theme.annotation.LABEL_PAD)}
    }
    function pillSize(total) {
        const text = total ? total.text || "" : ""
        return {width: Math.ceil(M.PillPlace.width(pillMetrics.advanceWidth(text), 0, 0, Theme.space.XXS, Theme.space.XS,
                                                   Theme.space.S, 0)),
                height: Math.ceil(M.PillPlace.height(pillMetrics.height, 0, Theme.annotation.LABEL_PAD))}
    }
    // the words' sizes as laid out, with the spans (found again only when the measures change)
    readonly property var labels: doneSegments.concat(placed ? (placed.segments || []).map(function(s, i) {
        return {a: s.a, b: s.b, pill: s.pill, selected: false, id: 0, key: "p:" + i}
    }) : []).map(function(s) { s.size = wordSize(s.pill); return s })
    // R618: the totals of the paths made, a pill at the path's end (a path of more than one span)
    readonly property var doneTotals: done.filter(function(m) { return !!m.total && (m.segments || []).length > 1 })
                                          .map(function(m) {
        return {key: "t" + m.id, id: m.id, selected: !!m.selected, total: m.total, size: pillSize(m.total),
                last: m.segments[m.segments.length - 1]}
    })
    readonly property point pointerAt: pointerScreen !== null ? pointerScreen
                                       : display.pointer ? at(display.pointer.at) : Qt.point(0, 0)
    // where the words may go (the view as it is seen): found again when the view changes size
    readonly property rect room: { const size = width + height; return M.ControlMetrics.roomOf(measures, true) }
    // R618 (Daniel 14/11/2026: «c'è una linea corta nella quale la misura si accavalla alla linea di fianco»): the
    // words and the totals laid out together in the screen's pixels (Controls/LabelPlace.js: on the span when it fits
    // and touches nothing, else out of it past the freer end, else hidden with a sign; the total a pill at the path's
    // end). The layout gives each a place by key (`places`: {mode, end, turn}), at once when the measures change and
    // once the view has moved (Qt.callLater: one layout for the zoom, the pan and the turn that came together); each
    // word finds its point from its place and its span as seen now, at every step of the view (LabelPlace.wordAt).
    // `places` is also the layout's memory, for the hysteresis.
    function scene(lines, marks, taken) {
        const occupied = obstacles.map(function(b) { return M.LabelPlace.shape(b.x+b.width/2,b.y+b.height/2,b.width,b.height,0) })
        return {lines: lines, marks: marks, taken: occupied.concat(taken), halo: halo / 2, mark: mark / 2 + M.ControlMetrics.planStroke / 2,
                gap: Theme.annotation.LABEL_GAP - (wordMetrics.height + 2*Theme.annotation.LABEL_PAD)/2, totalGap: Theme.space.XS, margin: M.ControlMetrics.measureWordMargin,
                hysteresis: M.ControlMetrics.measureWordHysteresis, outMin: M.ControlMetrics.measureWordOutMin,
                room: room, edge: Theme.space.XS}
    }
    readonly property var params: scene([], [], [])
    property var places: ({})
    property var fixed: ({lines: [], marks: [], taken: []})     // what the layout placed, for the span to the pointer
    function relayout() {
        const lines = labels.map(function(s) { const p=visibleSpan(s); return p ? {a:at(p.a),b:at(p.b)} : {a:Qt.point(-9999,-9999),b:Qt.point(-9999,-9999)} })
        const marks = doneMarks.concat(placed ? placed.marks || [] : []).map(function(k) { return at(k.at) })
                     .concat(doneSources.map(function(s) { return at(s.a) }))
        const space = scene(lines, marks, [])
        let totals = []
        const words = M.LabelPlace.words(labels.map(function(s, i) {
            return {key: s.key, line: i, width: s.size.width, height: s.size.height, outside: completeSpan(s)}
        }), space, places, function(taken) {
            totals = M.LabelPlace.totals(doneTotals.map(function(t) {
                return {key: t.key, end: at(t.last.b), from: at(t.last.a), width: t.size.width, height: t.size.height}
            }), taken, places)
        })
        const now = M.LabelPlace.memory(words.concat(totals), {})
        fixed = {lines: lines, marks: marks, taken: space.taken}
        if (JSON.stringify(now) !== JSON.stringify(places))
            places = now
    }
    onRevisionChanged: Qt.callLater(relayout)
    onRoomChanged: Qt.callLater(relayout)
    onLabelsChanged: relayout()
    onDoneTotalsChanged: relayout()
    Component.onCompleted: relayout()
    function completeSpan(span) {
        if(!visibleParts) return true
        const parts=portions(span.a,span.b)
        function same(a,b) { return Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]) < 1e-6 }
        return parts.length===1 && same(parts[0].a,span.a) && same(parts[0].b,span.b)
    }
    function visibleSpan(span) {
        const parts=portions(span.a,span.b)
        let best=null, length=-1
        parts.forEach(function(s) { const a=at(s.a), b=at(s.b), n=Math.hypot(b.x-a.x,b.y-a.y)
            if(n>length) {best=s; length=n} })
        return best
    }
    function wordPlace(span, place) {
        if (!span || !place) return null
        const camera = revision, shown=visibleSpan(span)
        if (!shown) return null
        return M.LabelPlace.wordAt(at(shown.a), at(shown.b), span.size.width, span.size.height, place.mode, place.end,
                                   params)
    }
    function totalPlace(total, place) {
        if (!total || !place || !seen(total.last.b)) return null
        const camera = revision
        const p = M.LabelPlace.totalAt(at(total.last.b), at(total.last.a), total.size.width, total.size.height,
                                       place.turn, params)
        p.mode = place.mode
        return p
    }
    // the span to the pointer's number and the total in hand: laid out at every step of the pointer against what the
    // layout placed (one word and one pill: the measures made are not laid out again); their memory in `liveMemo`
    // (changed in place, read by no binding)
    readonly property var liveMemo: ({})
    readonly property var live: {
        const e = elastic && pointerScreen === null ? elastic : null
        if (!e) return null
        const size = wordSize(e.pill), a = at(e.a), b = at(e.b)
        const lines = fixed.lines.concat([{a: a, b: b}])
        const space = scene(lines, fixed.marks.concat([b]), fixed.taken.slice())
        const t = current && current.total ? {key: "te", id: 0, selected: false, total: current.total,
                                              size: pillSize(current.total), last: e} : null
        let total = null
        const word = M.LabelPlace.words([{key: "e", line: lines.length - 1, width: size.width, height: size.height, outside: completeSpan(e)}],
                                        space, liveMemo, function(taken) {
            if (t) total = M.LabelPlace.totals([{key: "te", end: b, from: a, width: t.size.width,
                                                 height: t.size.height}], taken, liveMemo)[0]
        })[0]
        M.LabelPlace.memory(total ? [word, total] : [word], liveMemo)
        const span = {a: e.a, b: e.b, pill: e.pill, selected: false, id: 0, key: "e", size: size}
        return {span: span, word: wordPlace(span, word), total: t, totalPlace: total ? totalPlace(t, total) : null}
    }
    // the spans: the measurements made (selected in the selection's colour), the points placed, the span to the pointer
    Shape {
            id: strokeShape0
            preferredRendererType: Shape.CurveRenderer
        objectName: "measureLines"
        // none at all without a measure: an empty path drawn by the software renderer over the plan hid the map under it
        visible: measures.done.length > 0 || !!measures.placed
        M.ViewPath {
                surface: strokeShape0
                halo: true
                viewScale: 1;   fillColor: "transparent"
            PathMultiline { paths: measures.paths(measures.done, false).concat(measures.placed ? measures.paths([measures.placed], false) : []) } }
            M.ViewPath {
                surface: strokeShape0
                viewScale: 1; strokeColor: measures.colors.draw;  fillColor: "transparent"
            PathMultiline { paths: measures.paths(measures.done, false).concat(measures.placed ? measures.paths([measures.placed], false) : []) } }
        M.ViewPath {
                surface: strokeShape0
                halo: true
                viewScale: 1;   fillColor: "transparent"
            PathMultiline { paths: measures.paths(measures.done, true) } }
            M.ViewPath {
                surface: strokeShape0
                viewScale: 1; strokeColor: measures.colors.sel;  fillColor: "transparent"
            PathMultiline { paths: measures.paths(measures.done, true) } }
    }
    // p on the screen's line through a and b (a when they are one point: a vertical seen from straight above)
    function onLine(p, a, b) {
        const dx = b.x-a.x, dy = b.y-a.y, n = dx*dx + dy*dy
        if (n < 1e-9) return a
        const t = ((p.x-a.x)*dx + (p.y-a.y)*dy)/n
        return Qt.point(a.x + t*dx, a.y + t*dy)
    }
    // while the 3D pointer moves: the end of the span to it, on the line the tool keeps it to (the foot's vertical of a
    // height, an axis, the direction held: display.follow) where there is one, else the pointer itself
    readonly property point followEnd: {
        if (!following) return Qt.point(0, 0)
        const f = display.follow
        return f ? onLine(pointerScreen, at(f.a), at(f.b)) : pointerScreen
    }
    // the references: the dotted lines from where a height took its height (made, placed, in hand at rest) and, while
    // the 3D pointer moves along a line, from the pointer to the span's end
    readonly property var movingReference: following && display.follow && worldAtScreen
        ? ({a: worldAtScreen(pointerScreen, elastic ? elastic.b : placed.marks[placed.marks.length-1].at),
            b: worldOnFollow ? worldOnFollow(followEnd) : worldAtScreen(followEnd, elastic ? elastic.b : placed.marks[placed.marks.length-1].at)}) : null
    readonly property var references: {
        const out = []
        function add(s) { out.push.apply(out, projectedParts(s.a,s.b)) }
        done.forEach(function(m) { (m.sources || []).forEach(add) })
        if (placed) (placed.sources || []).forEach(add)
        if (display.source && pointerScreen === null) add(display.source)
        if (following && display.follow) {
            if(visibleParts && movingReference) out.push.apply(out,projectedParts(movingReference.a,movingReference.b))
            else out.push([pointerScreen, followEnd])
        }
        return out
    }
    readonly property var doneSources: {
        const out = []
        done.forEach(function(m) { (m.sources || []).forEach(function(s) { out.push(s) }) })
        return out
    }
    Shape {
            preferredRendererType: Shape.CurveRenderer
        id: elasticLine
        objectName: "measureElastic"
        visible: measures.following || (!!measures.elastic && measures.pointerScreen === null)
        readonly property var worldSpan: measures.following && measures.worldAtScreen
            ? ({a: measures.placed.marks[measures.placed.marks.length-1].at,
                b: measures.worldOnFollow ? measures.worldOnFollow(measures.followEnd) : measures.worldAtScreen(measures.followEnd, measures.elastic ? measures.elastic.b : measures.placed.marks[measures.placed.marks.length-1].at)})
            : measures.elastic
        readonly property var ends: measures.following
            ? [measures.at(measures.placed.marks[measures.placed.marks.length-1].at), measures.followEnd]
            : measures.elastic ? measures.mapped([measures.elastic.a, measures.elastic.b]) : []
        M.ViewPath {
                surface: elasticLine
                halo: true
                viewScale: 1;   fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.visibleParts && elasticLine.worldSpan ? measures.projectedParts(elasticLine.worldSpan.a,elasticLine.worldSpan.b) : [elasticLine.ends] } }
            M.ViewPath {
                surface: elasticLine
                viewScale: 1; strokeColor: measures.colors.draw;  fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.visibleParts && elasticLine.worldSpan ? measures.projectedParts(elasticLine.worldSpan.a,elasticLine.worldSpan.b) : [elasticLine.ends] } }
    }
    Shape {
            id: strokeShape2
            preferredRendererType: Shape.CurveRenderer
        objectName: "measureReference"
        readonly property int count: measures.references.length
        visible: count > 0 || (measures.following && !!measures.display.follow)
        M.ViewPath {
                surface: strokeShape2
                halo: true
                viewScale: 1;   fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.references } }
            M.ViewPath {
                surface: strokeShape2
                viewScale: 1; strokeColor: measures.colors.guide;  fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.references } }
    }
    Shape {
            preferredRendererType: Shape.CurveRenderer
        id: edgeLine
        objectName: "measureEdge"
        visible: !!measures.display.edge && measures.pointerScreen === null
        readonly property var ends: measures.display.edge ? measures.mapped([measures.display.edge.a, measures.display.edge.b]) : []
        M.ViewPath {
                surface: edgeLine
                halo: true
                viewScale: 1;   fillColor: "transparent"
            PathMultiline { paths: measures.display.edge ? measures.projectedParts(measures.display.edge.a,measures.display.edge.b) : [] } }
            M.ViewPath {
                surface: edgeLine
                viewScale: 1; strokeColor: measures.colors.sel;  fillColor: "transparent"
            PathMultiline { paths: measures.display.edge ? measures.projectedParts(measures.display.edge.a,measures.display.edge.b) : [] } }
    }
    Shape {
            id: strokeShape4
            preferredRendererType: Shape.CurveRenderer
        objectName: "measureGuides"
        readonly property int count: (measures.display.guides || []).length
        visible: count > 0
        M.ViewPath {
                surface: strokeShape4
                halo: true
                viewScale: 1;   fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.guides(false) } }
            M.ViewPath {
                surface: strokeShape4
                viewScale: 1; strokeColor: measures.colors.guide;  fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.guides(false) } }
        M.ViewPath {
                surface: strokeShape4
                halo: true
                viewScale: 1;   fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.guides(true) } }
            M.ViewPath {
                surface: strokeShape4
                viewScale: 1; strokeColor: measures.colors.draw;  fillColor: "transparent"
            dashed: true;
            PathMultiline { paths: measures.guides(true) } }
    }
    // the marks of the points placed, by what each snapped to, and the one under the pointer
    component Mark: Shape {
            id: strokeShape5
            preferredRendererType: Shape.CurveRenderer
        property string kind: "free"
        property point centre: Qt.point(0, 0)
        property color ink: measures.colors.draw
        M.ViewPath {
                surface: strokeShape5
                halo: true
                viewScale: 1;   fillColor: "transparent"
            PathSvg { path: measures.markPath(kind, centre) } }
            M.ViewPath {
                surface: strokeShape5
                viewScale: 1; strokeColor: ink;  fillColor: Qt.rgba(0,0,0,Theme.annotation.HALO_ALPHA)
            PathSvg { path: measures.markPath(kind, centre) } }
    }
    Repeater {
        model: measures.doneMarks
        delegate: Mark {
            required property var modelData
            objectName: "measureMark"
            visible: measures.seen(modelData.at)
            kind: modelData.kind; centre: measures.at(modelData.at)
        }
    }
    Repeater {
        model: measures.placed ? measures.placed.marks : []
        delegate: Mark {
            required property var modelData
            objectName: "measureMark"
            visible: measures.seen(modelData.at)
            kind: modelData.kind; centre: measures.at(modelData.at)
        }
    }
    Repeater {
        model: measures.doneSources
        delegate: Mark {
            required property var modelData
            objectName: "measureSourceMark"
            visible: measures.seen(modelData.a)
            kind: modelData.kind; centre: measures.at(modelData.a); ink: measures.colors.guide
        }
    }
    Mark {
        objectName: "measurePointer"
        visible: !!measures.display.pointer && measures.pointerScreen === null && measures.seen(measures.display.pointer.at)
        kind: measures.display.pointer ? measures.display.pointer.kind : "free"
        centre: measures.pointerAt
        ink: measures.colors.guide
    }
    // a click on a measurement made's number or total chooses it (Shift adds, Ctrl adds or takes away), with Select only
    component Pick: MouseArea {
        property int measureId: 0
        objectName: "measurePick"
        anchors.fill: parent
        enabled: measures.picking && measureId > 0
        acceptedButtons: Qt.LeftButton
        onClicked: function(mouse) {
            // the choice redraws the words (this one too): the host told first, the bridge last
            const bridge = measures.measure, id = measureId
            const bits = ((mouse.modifiers & Qt.ControlModifier) ? 1 : 0) | ((mouse.modifiers & Qt.ShiftModifier) ? 2 : 0)
            measures.picked()
            bridge.select(id, bits)
        }
    }
    // the numbers of the spans, written along them (M.SpanLabel) where the layout placed them
    component Word: M.SpanLabel {
        id: word
        property var span: null
        property bool selected: false
        property int measureId: 0
        readonly property string mode: place ? place.mode : ""     // "on", "out" or "hidden" (R618)
        value: span ? span.pill.label || span.pill.text || "" : ""
        approx: span ? !!span.pill.approx : false
        ink: selected ? measures.colors.sel : measures.colors.draw
        halo: measures.colors.halo
        ground: measures.colors.label_bg
        room: measures.room
        visible: !!span && !!place && place.mode !== "hidden" && measures.clear(box.x, box.y, box.width, box.height)
        Pick { measureId: word.measureId }
    }
    // the total of a path: a pill at its end (R618, Daniel: «starei sul tipo pillola»), the plan's pill of a length
    component Total: M.LengthPill {
        id: pill
        property var total: null
        property var place: null
        property bool selected: false
        property int measureId: 0
        property bool revealed: false               // hidden by the layout, shown while the pointer is on its end
        objectName: "measureTotal"
        value: total ? total.text || "" : ""
        approx: total ? !!total.approx : false
        ground: measures.colors.label_bg
        ink: selected ? measures.colors.sel : measures.colors.label_fg
        x: place ? place.x : 0; y: place ? place.y : 0
        width: place ? place.box.width : implicitWidth; height: place ? place.box.height : implicitHeight
        visible: !!total && !!place && (place.mode === "on" || revealed)
                 && measures.clear(place.box.x, place.box.y, place.box.width, place.box.height)
        Pick { measureId: pill.measureId }
    }
    // a word or a total the layout hid: the pointer on its span (or on the path's end) shows it, in front of the rest
    component Hover: Item {
        property point centre: Qt.point(0, 0)
        property real length: 0
        property real angle: 0
        readonly property alias hovered: handler.hovered
        objectName: "measureHover"
        x: centre.x - width / 2; y: centre.y - height / 2
        width: Math.max(length, M.ControlMetrics.measureHover); height: M.ControlMetrics.measureHover
        rotation: angle
        HoverHandler { id: handler }
    }
    // a hidden word: its sign is drawn with the others (measureSigns, below); while the pointer is on the span, the
    // number in the pill of a length over the middle of the span, in front of the rest (made only then)
    component HiddenWord: Item {
        id: hiddenWord
        property var place: null
        property var span: null
        property int measureId: 0
        readonly property bool hovered: hover.hovered
        Hover { id: hover; centre: hiddenWord.place.mid; length: hiddenWord.place.length; angle: hiddenWord.place.angle }
        Loader {
            active: hover.hovered
            sourceComponent: M.LengthPill {
                objectName: "measureReveal"
                value: hiddenWord.span ? hiddenWord.span.pill.label || hiddenWord.span.pill.text || "" : ""
                approx: hiddenWord.span ? !!hiddenWord.span.pill.approx : false
                ground: measures.colors.label_bg
                ink: measures.colors.label_fg
                x: Math.max(measures.room.x, Math.min(hiddenWord.place.mid.x - implicitWidth / 2,
                                                      measures.room.x + measures.room.width - implicitWidth))
                y: Math.max(measures.room.y, hiddenWord.place.mid.y - implicitHeight - measures.mark)
                Pick { measureId: hiddenWord.measureId }
            }
        }
    }
    // the signs of the hidden words, all in one drawing (one path to make again when the view moves, not one each): a
    // short stroke across the middle of each span, in the measure's colour (the selection's for a measure chosen) on
    // its halo
    function signOf(span) {
        const p = places[span.key]
        if (!p || p.mode !== "hidden" || !visibleSpan(span)) return null
        const visible = visibleSpan(span), a = at(visible.a), b = at(visible.b), dx = b.x - a.x, dy = b.y - a.y, n = Math.hypot(dx, dy)
        const half = M.ControlMetrics.measureSign / 2, nx = n > 1e-6 ? -dy / n : 0, ny = n > 1e-6 ? dx / n : 1
        const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
        return [Qt.point(mx - nx * half, my - ny * half), Qt.point(mx + nx * half, my + ny * half)]
    }
    readonly property var signs: {
        const camera = revision, out = {plain: [], chosen: []}
        labels.forEach(function(s) {
            const sign = signOf(s)
            if (sign) (s.selected ? out.chosen : out.plain).push(sign)
        })
        return out
    }
    Shape {
            id: strokeShape6
            preferredRendererType: Shape.CurveRenderer
        objectName: "measureSigns"
        readonly property int count: measures.signs.plain.length + measures.signs.chosen.length
        visible: count > 0
        M.ViewPath {
                surface: strokeShape6
                halo: true
                viewScale: 1;   fillColor: "transparent"
            PathMultiline { paths: measures.signs.plain } }
            M.ViewPath {
                surface: strokeShape6
                viewScale: 1; strokeColor: measures.colors.draw;  fillColor: "transparent"
            PathMultiline { paths: measures.signs.plain } }
        M.ViewPath {
                surface: strokeShape6
                halo: true
                viewScale: 1;   fillColor: "transparent"
            PathMultiline { paths: measures.signs.chosen } }
            M.ViewPath {
                surface: strokeShape6
                viewScale: 1; strokeColor: measures.colors.sel;  fillColor: "transparent"
            PathMultiline { paths: measures.signs.chosen } }
    }
    component Slot: Item {
        id: slot
        property var span: null
        property var place: null
        property bool selected: false
        property int measureId: 0
        readonly property bool hidden: !!span && !!place && place.mode === "hidden"
        z: hiddenLoader.item && hiddenLoader.item.hovered ? 1 : 0
        Word { objectName: "measurePill"; span: slot.span; place: slot.place; selected: slot.selected
               measureId: slot.measureId }
        // made only for a hidden word (most words are not)
        Loader {
            id: hiddenLoader
            active: slot.hidden
            sourceComponent: HiddenWord { place: slot.place; span: slot.span; measureId: slot.measureId }
        }
    }
    Repeater {
        model: measures.labels
        delegate: Slot {
            required property var modelData
            span: modelData; selected: modelData.selected; measureId: modelData.id
            place: measures.wordPlace(modelData, measures.places[modelData.key])
        }
    }
    component TotalSlot: Item {
        id: totalSlot
        property var total: null
        property var place: null
        property point end: Qt.point(0, 0)
        property bool selected: false
        property int measureId: 0
        readonly property bool hidden: !!place && place.mode === "hidden"
        z: endLoader.item && endLoader.item.hovered ? 1 : 0
        Total { total: totalSlot.total; place: totalSlot.place; selected: totalSlot.selected
                measureId: totalSlot.measureId; revealed: !!endLoader.item && endLoader.item.hovered }
        Loader { id: endLoader; active: totalSlot.hidden; sourceComponent: Hover { centre: totalSlot.end } }
    }
    Repeater {
        model: measures.doneTotals
        delegate: TotalSlot {
            required property var modelData
            total: modelData.total; selected: modelData.selected; measureId: modelData.id
            place: measures.totalPlace(modelData, measures.places[modelData.key])
            end: { const camera = measures.revision; return measures.at(modelData.last.b) }
        }
    }
    // the span to the pointer's number and the total in hand: none while the 3D pointer moves (no point is looked for)
    Slot {
        span: measures.live ? measures.live.span : null
        place: measures.live ? measures.live.word : null
    }
    TotalSlot {
        total: measures.live && measures.live.total ? measures.live.total.total : null
        place: measures.live ? measures.live.totalPlace : null
        end: measures.live && measures.live.total ? measures.at(measures.live.total.last.b) : Qt.point(0, 0)
    }
    // beside the pointer, a small word each: the number being typed, the constraint on, the snap asked (no ground)
    component Note: M.SpanLabel {
        property var note: null
        along: false
        visible: !!note
        value: note ? note.text || "" : ""
        ink: measures.colors.draw; halo: measures.colors.halo
    }
    Column {
        id: beside
        objectName: "measureBeside"
        readonly property point spot: visible ? M.ControlMetrics.besidePointer(measures.pointerAt, width, height, measures.room)
                                              : Qt.point(0, 0)
        visible: !!measures.display.pointer && (!!measures.display.typed || !!measures.display.constraint
                 || !!measures.display.request)
        x: spot.x; y: spot.y
        spacing: Theme.space.XXS
        Note { objectName: "measureTyped"; note: measures.display.typed || null }
        Note { objectName: "measureConstraint"; note: measures.display.constraint || null }
        Note { objectName: "measureRequest"; note: measures.display.request || null }
    }
}
