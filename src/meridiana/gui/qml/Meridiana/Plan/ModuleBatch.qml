import QtQuick
import QtQuick.Window
import Meridiana.Controls as M
import Meridiana.Theme
import QtQuick.Shapes
import Meridiana.Plan.Paths 1.0
ModulePaths {
    id: batch
    property bool curves: true
    property bool sync: false       // built on the GUI thread at once: small layers that must never go blank (R496)
    // the dashes follow the zoom the wheel settled on, not every step (R498): a new pattern is a new path
    property real viewScale: parent ? Math.max(.00002, Math.abs(parent.settledScale!==undefined ? parent.settledScale : parent.scale)) : 1
    // the scale the lines are built for (R706): the plan's, which follows the zoom in steps; elsewhere the pen is
    // cosmetic, as it was
    property real strokeScale: parent && parent.strokeScale!==undefined ? Math.max(.00002, Math.abs(parent.strokeScale)) : 0
    property real pen: Theme.annotation.STROKE
    // R706: a path says what it covers (`bounds`); outside `view` (the plan's: what its image shows and a margin
    // around it, in the scene's metres) it is not drawn, and its lines are not built again when their width
    // changes: it takes the width of the moment when it comes into view. No view: everything, as it was.
    property var view: parent && parent.viewBox!==undefined ? parent.viewBox : null
    // R707: what the level of detail of the view decides. `shown`: while false none of its paths is drawn, nor
    // built again when the lines change their width. `line`: how much ink the outlines have (1 all, 0 none, and
    // then no line is built at all).
    property bool shown: true
    property real line: 1
    onShownChanged: cull()
    // what each path covers, read once when the paths change: one pass at each new view, and a path is touched
    // only when it comes into view or leaves it (a binding for each path read its record again at every step)
    readonly property var boxes: paths.map(function(p) { return p.bounds || null })
    function shows(b) {
        const v=view
        return shown && (!v || !b || (b[0]<v[2] && b[2]>v[0] && b[1]<v[3] && b[3]>v[1]))
    }
    function cull() {
        const b=boxes
        for (var i=0;i<shapes.count && i<b.length;i++) {
            var shape=shapes.itemAt(i)
            if (!shape) continue
            var seen=shows(b[i])
            if (shape.visible!==seen) shape.visible=seen
        }
    }
    onViewChanged: cull()
    onStrokeScaleChanged: {
        for (var i=0;i<shapes.count;i++) {
            var shape=shapes.itemAt(i)
            if (shape && shape.visible) shape.penScale=strokeScale
        }
    }
    // every path in view built: counted once after the changes of a turn, not at each of them
    property bool ready: true
    function count() {
        var done=shapes.count===paths.length
        for (var i=0;done && i<shapes.count;i++) {
            var shape=shapes.itemAt(i)
            if (!shape || (shape.visible && shape.status!==Shape.Ready)) done=false
        }
        ready=done
    }
    function recount() { Qt.callLater(count) }
    // a path in view not built yet: said at once; one that leaves, or is built already, takes nothing back
    function pending(shape) {
        if (shape.visible && shape.status!==Shape.Ready) ready=false
        recount()
    }
    onPathsChanged: { ready=false; recount() }
    Repeater {
        id: shapes
        model: batch.paths
        delegate: Shape {
            id: strokeShape0
            required property var modelData
            // a path written from a corner of its own (the strings' dots, plan_wiring.dot_paths) stands there
            x: modelData.x || 0; y: modelData.y || 0
            property real penScale: batch.strokeScale
            readonly property color lineInk: modelData.stroke
            readonly property color ink: batch.line>=1 ? lineInk : Qt.rgba(lineInk.r, lineInk.g, lineInk.b, lineInk.a*Math.max(0, batch.line))
            onVisibleChanged: { if (visible) penScale=batch.strokeScale; batch.pending(strokeShape0) }
            onStatusChanged: batch.pending(strokeShape0)
            Component.onCompleted: {
                penScale=batch.strokeScale        // by hand from here on: only while in view
                visible=batch.shows(modelData.bounds)
                batch.pending(strokeShape0)
            }
            asynchronous: !batch.sync
            preferredRendererType: batch.curves ? Shape.CurveRenderer : Shape.GeometryRenderer
            M.ViewPath {
                surface: strokeShape0
                halo: true
                ink: strokeShape0.ink
                strokeColor: Qt.rgba(0, 0, 0, strokeShape0.ink.a > 0 ? Theme.annotation.HALO_ALPHA*Math.min(1, batch.line) : 0)
                viewScale: batch.viewScale
                worldScale: strokeShape0.penScale
                pen: batch.pen
                fillColor: "transparent"
                dashed: modelData.dashed ? true : false
                fillRule: ShapePath.WindingFill
                PathSvg { path: modelData.path }
            }
            M.ViewPath {
                surface: strokeShape0
                viewScale: batch.viewScale
                worldScale: strokeShape0.penScale
                pen: batch.pen
                fillColor: modelData.fill
                strokeColor: strokeShape0.ink
                dashed: modelData.dashed ? true : false
                fillRule: ShapePath.WindingFill
                PathSvg { path: modelData.path }
            }
        }
    }
}
