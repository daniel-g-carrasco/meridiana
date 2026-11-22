import QtQuick
import QtQuick.Window
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as MC
import Meridiana.Measure
// Screen-space drawing aids. Camera changes transform these entirely in QML. The measures (study 46) are the common
// MeasureLayer's: they stay drawn whatever the tool in hand, the drawing aids only with a drawing tool.
Item {
    id: overlay
    objectName: "toolOverlay"
    required property var plan
    property var preview: ({})
    readonly property var draft: preview || ({})
    readonly property var colors: plan.backend.planColors
    readonly property color drawColor: colors.draw
    readonly property color haloColor: Qt.rgba(0,0,0,Theme.annotation.HALO_ALPHA)
    readonly property color guideColor: colors.guide
    readonly property bool drawing: ["building", "pitch", "ridge", "subfield", "exclusion", "prop_line"].indexOf(draft.tool) >= 0
    readonly property bool sideDrag: draft.tool === "side"          // R473: a side dragged parallel, its card
    readonly property var gridModules: (draft.tool === "subfield" && draft.modules) ? (draft.modules.quads || []) : []
    readonly property bool rowTool: draft.tool === "row" || draft.tool === "east_west"
    readonly property var vertices: draft.points || []
    readonly property var ring: draft.ring || []
    readonly property var row: draft.row || ({quads: [], bad: false})
    readonly property var card: draft.card || ({lines: [], anchor: null})
    readonly property var segments: pathPoints()
    // the drawing aids with any tool but Select (the plan showed the whole overlay so, R563 and before)
    readonly property bool aids: plan.backend.tool !== "select"
    clip: true
    function screen(point) {
        // Explicit dependencies: mapToItem itself does not notify QML bindings.
        const camera = plan.zoom + plan.panX + plan.panY + plan.bearing
        return plan.screen(point[0], point[1])
    }
    function mapped(points) { return points.map(function(point) { return screen(point) }) }
    function closed(quads) { return quads.map(function(q) { return mapped(q.concat([q[0]])) }) }
    function pathPoints() {
        if (draft.rectangle && ring.length === 4 && vertices.length === 2 && drawing)
            return ring.concat([ring[0]])
        let points = vertices.slice()
        if (drawing && points.length && draft.pointer) {
            const last = points[points.length-1]
            if (Math.hypot(last[0]-draft.pointer[0],last[1]-draft.pointer[1]) > 0.000001)
                points.push(draft.pointer)
        }
        return points
    }
    function guidePoints(guide) {
        const a = screen(guide.a), b = screen(guide.b)
        const dx = b.x-a.x, dy = b.y-a.y, length = Math.hypot(dx,dy)
        if (length < 0.000001) return [a,b]
        const extension = Math.hypot(width,height)*2/length
        return [guide.kind === "tracking" ? Qt.point(a.x-dx*extension,a.y-dy*extension) : a,
                Qt.point(b.x+dx*extension,b.y+dy*extension)]
    }
    function eavePoints() {
        if (!draft.pitch || ring.length < 3) return []
        const side = draft.pitch.eave_side % ring.length
        return mapped([ring[side],ring[(side+1)%ring.length]])
    }
    MeasureLayer {
        anchors.fill: parent
        measure: overlay.plan.backend.measure
        view: "plan"
        obstacles: overlay.plan.sidePillBoxes
        colors: overlay.colors
        revision: overlay.plan.zoom + overlay.plan.panX + overlay.plan.panY + overlay.plan.bearing
        toScreen: function(p) { return overlay.plan.screen(p[0], p[1]) }
        picking: overlay.plan.backend.tool === "select"
        clearOf: overlay.plan.clearOfChrome         // the overlay fills the plan: the same coordinates
        onPicked: overlay.plan.forceActiveFocus()
    }
    Item {
        objectName: "drawingAids"
        anchors.fill: parent
        visible: overlay.aids
        Repeater {
            model: overlay.draft.guides || []
            delegate: Shape {
            id: strokeShape0
            preferredRendererType: Shape.CurveRenderer
                required property var modelData
                objectName: "drawingGuide"
                MC.ViewPath {
                surface: strokeShape0
                halo: true
                viewScale: 1
                    dashed: true
                    fillColor: "transparent"
                    PathPolyline { path: overlay.guidePoints(modelData) }
                }
            MC.ViewPath {
                surface: strokeShape0
                viewScale: 1
                    strokeColor: overlay.guideColor
                    dashed: true
                    fillColor: "transparent"
                    PathPolyline { path: overlay.guidePoints(modelData) }
                }
            }
        }
        // R445: the modules of a sub-field drawn as modules lay themselves as the outline is drawn; those of a row as
        // it is drawn. One shape for all of them (Daniel 21/11/2026: a shape for each module, 1500 of them made again
        // at every move of the pointer, held the window for 230 ms), up to plan_tools.PREVIEW_MODULES
        Shape {
            id: gridShape
            objectName: "drawingGridModules"
            preferredRendererType: Shape.CurveRenderer
            readonly property var rings: overlay.closed(overlay.gridModules)
            visible: rings.length > 0
            MC.ViewPath { surface: gridShape; halo: true; viewScale: 1; fillColor: "transparent"
                PathMultiline { paths: gridShape.rings } }
            MC.ViewPath { surface: gridShape; viewScale: 1; strokeColor: overlay.drawColor
                fillColor: Qt.rgba(overlay.drawColor.r,overlay.drawColor.g,overlay.drawColor.b,0.22)
                PathMultiline { paths: gridShape.rings } }
        }
        Shape {
            id: rowShape
            objectName: "drawingRowModules"
            preferredRendererType: Shape.CurveRenderer
            readonly property var rings: overlay.closed(overlay.row.quads || [])
            readonly property color tint: overlay.row.bad ? overlay.colors.exclusion : overlay.drawColor
            visible: rings.length > 0
            MC.ViewPath { surface: rowShape; halo: true; viewScale: 1; fillColor: "transparent"
                PathMultiline { paths: rowShape.rings } }
            MC.ViewPath { surface: rowShape; viewScale: 1; strokeColor: rowShape.tint
                fillColor: Qt.rgba(rowShape.tint.r,rowShape.tint.g,rowShape.tint.b,0.27)
                PathMultiline { paths: rowShape.rings } }
        }
        Shape {
            // a row past the preview's limit (plan_tools.PREVIEW_MODULES): its outline, the same cost at any length
            id: rowOutline
            objectName: "drawingRowOutline"
            preferredRendererType: Shape.CurveRenderer
            readonly property var points: overlay.row.outline || []
            readonly property color tint: overlay.row.bad ? overlay.colors.exclusion : overlay.drawColor
            visible: points.length >= 3
            MC.ViewPath {
                surface: rowOutline
                halo: true
                viewScale: 1
                fillColor: "transparent"
                PathPolyline { path: rowOutline.points.length >= 3 ? overlay.mapped(rowOutline.points.concat([rowOutline.points[0]])) : [] }
            }
            MC.ViewPath {
                surface: rowOutline
                viewScale: 1
                strokeColor: rowOutline.tint
                fillColor: Qt.rgba(rowOutline.tint.r,rowOutline.tint.g,rowOutline.tint.b,0.27)
                PathPolyline { path: rowOutline.points.length >= 3 ? overlay.mapped(rowOutline.points.concat([rowOutline.points[0]])) : [] }
            }
        }
        Shape {
            id: strokeShape3
            preferredRendererType: Shape.CurveRenderer
            visible: overlay.segments.length >= 2
            MC.ViewPath {
                surface: strokeShape3
                halo: true
                viewScale: 1
                fillColor: "transparent"
                dashed: overlay.rowTool || (overlay.draft.rectangle && overlay.vertices.length === 2)
                             ? true : false
                PathPolyline { path: overlay.mapped(overlay.segments) }
            }
            MC.ViewPath {
                surface: strokeShape3
                viewScale: 1
                strokeColor: overlay.rowTool && overlay.row.bad ? overlay.colors.exclusion : overlay.drawColor
                fillColor: "transparent"
                dashed: overlay.rowTool || (overlay.draft.rectangle && overlay.vertices.length === 2)
                             ? true : false
                PathPolyline { path: overlay.mapped(overlay.segments) }
            }
        }
        Shape {
            id: strokeShape4
            preferredRendererType: Shape.CurveRenderer
            visible: overlay.drawing && overlay.vertices.length >= 2 && overlay.segments.length >= 2
                     && !overlay.draft.rectangle && overlay.draft.tool !== "ridge" && overlay.draft.tool !== "prop_line"
            MC.ViewPath {
                surface: strokeShape4
                halo: true
                viewScale: 1
                fillColor: "transparent"
                dashed: true
                PathPolyline {
                    path: overlay.segments.length ? overlay.mapped([overlay.segments[overlay.segments.length-1],overlay.segments[0]]) : []
                }
            }
            MC.ViewPath {
                surface: strokeShape4
                viewScale: 1
                strokeColor: overlay.drawColor
                fillColor: "transparent"
                dashed: true
                PathPolyline {
                    path: overlay.segments.length ? overlay.mapped([overlay.segments[overlay.segments.length-1],overlay.segments[0]]) : []
                }
            }
        }
        Shape {
            id: strokeShape5
            preferredRendererType: Shape.CurveRenderer
            objectName: "drawingEave"
            visible: overlay.draft.tool === "pitch" && !!overlay.draft.pitch
            MC.ViewPath {
                surface: strokeShape5
                halo: true
                viewScale: 1
                fillColor: "transparent"
                PathPolyline { path: overlay.eavePoints() }
            }
            MC.ViewPath {
                surface: strokeShape5
                viewScale: 1
                strokeColor: overlay.colors.sel
                fillColor: "transparent"
                PathPolyline { path: overlay.eavePoints() }
            }
        }
        Repeater {
            model: overlay.vertices
            delegate: Rectangle {
                required property var modelData
                readonly property point at: overlay.screen(modelData)
                objectName: "drawingVertex"     // R563: of a measure too: its first click showed nothing at all
                x: at.x-width/2; y: at.y-height/2
                width: Theme.annotation.POINT; height: width
                color: "transparent"
                border.color: overlay.drawColor
                border.width: MC.ControlMetrics.planStroke
            }
        }
        MC.ViewStroke {
            id: snapMarker
            objectName: "drawingSnap"
            readonly property point at: overlay.draft.pointer ? overlay.screen(overlay.draft.pointer) : Qt.point(0,0)
            visible: !!overlay.draft.pointer && ["vertex","midpoint","intersection","close","edge"].indexOf(overlay.draft.snap) >= 0
            ink: overlay.guideColor
            svg: MC.ViewMarks.path(overlay.draft.snap === "close" ? "vertex" : overlay.draft.snap, at, Theme.annotation.POINT/2)
        }
        MC.ViewStroke {
            id: transformMark
            objectName: "transformBaseMark"
            readonly property var point: overlay.draft.pivot || overlay.draft.base || null
            readonly property point at: point ? overlay.screen(point) : Qt.point(0,0)
            visible: point !== null && overlay.draft.type === "transform"
            ink: overlay.drawColor
            svg: MC.ViewMarks.path(overlay.draft.mode === "rotate" ? "intersection" : "vertex", at, Theme.annotation.POINT/2)
        }
        Rectangle {
            id: values
            objectName: "toolCard"
            readonly property point at: overlay.card.anchor ? overlay.screen(overlay.card.anchor) : Qt.point(0,0)
            readonly property real padding: Theme.space.XS
            visible: !!overlay.card.anchor && (overlay.card.lines || []).length > 0
            width: Math.min(Math.max(0,overlay.width-24), text.implicitWidth+padding*2)
            height: text.contentHeight+padding*2
            // R550: beside the pointer as every tooltip, inside the part of the view that is seen (Daniel 08/11/2026: the
            // readout of the area being drawn was cut by the window's right edge); left of it, or above, where the room ends
            readonly property point spot: MC.ControlMetrics.besidePointer(at, width, height, MC.ControlMetrics.roomOf(overlay, true))
            x: spot.x
            y: spot.y
            color: overlay.colors.label_bg
            radius: Theme.radius.INNER
            Text {
                id: text
                objectName: "toolCardText"
                x: values.padding; y: values.padding
                width: parent.width-values.padding*2
                text: (overlay.card.lines || []).join("\n")
                textFormat: Text.PlainText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.type.BODY
                color: overlay.colors.label_fg
                wrapMode: Text.Wrap
            }
        }
    }
}
