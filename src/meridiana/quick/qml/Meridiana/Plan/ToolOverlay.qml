import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as MC

// Screen-space drawing aids. Camera changes transform these entirely in QML.
Item {
    id: overlay
    objectName: "toolOverlay"
    required property var plan
    property var preview: ({})
    readonly property var draft: preview || ({})
    readonly property var colors: plan.backend.planColors
    readonly property color drawColor: colors.draw
    readonly property color haloColor: colors.halo
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
    visible: drawing || rowTool || sideDrag || draft.tool === "measure"
    clip: true

    function screen(point) {
        // Explicit dependencies: mapToItem itself does not notify QML bindings.
        const camera = plan.zoom + plan.panX + plan.panY + plan.bearing
        return plan.screen(point[0], point[1])
    }
    function mapped(points) { return points.map(function(point) { return screen(point) }) }
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

    Repeater {
        model: overlay.draft.guides || []
        delegate: Shape {
            required property var modelData
            objectName: "drawingGuide"
            ShapePath {
                strokeColor: overlay.guideColor
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                dashPattern: [5,4]
                fillColor: "transparent"
                PathPolyline { path: overlay.guidePoints(modelData) }
            }
        }
    }
    Repeater {
        // R445: the modules of a sub-field drawn as modules lay themselves as the outline is drawn
        model: overlay.gridModules
        delegate: Shape {
            required property var modelData
            objectName: "drawingGridModule"
            ShapePath {
                strokeColor: overlay.drawColor
                strokeWidth: 1
                fillColor: Qt.rgba(overlay.drawColor.r,overlay.drawColor.g,overlay.drawColor.b,0.22)
                PathPolyline { path: overlay.mapped(modelData.concat([modelData[0]])) }
            }
        }
    }
    Repeater {
        model: overlay.row.quads || []
        delegate: Shape {
            required property var modelData
            readonly property color tint: overlay.row.bad ? overlay.colors.exclusion : overlay.drawColor
            objectName: "drawingRowModule"
            ShapePath {
                strokeColor: tint
                strokeWidth: 1.2
                fillColor: Qt.rgba(tint.r,tint.g,tint.b,0.27)
                PathPolyline { path: overlay.mapped(modelData.concat([modelData[0]])) }
            }
        }
    }
    Shape {
        visible: overlay.segments.length >= 2
        ShapePath {
            strokeColor: overlay.haloColor
            strokeWidth: 5.6
            fillColor: "transparent"
            joinStyle: ShapePath.MiterJoin
            PathPolyline { path: overlay.mapped(overlay.segments) }
        }
        ShapePath {
            strokeColor: overlay.rowTool && overlay.row.bad ? overlay.colors.exclusion : overlay.drawColor
            strokeWidth: 2.6
            fillColor: "transparent"
            strokeStyle: overlay.rowTool || (overlay.draft.rectangle && overlay.vertices.length === 2)
                         ? ShapePath.DashLine : ShapePath.SolidLine
            dashPattern: [4,2]
            joinStyle: ShapePath.MiterJoin
            PathPolyline { path: overlay.mapped(overlay.segments) }
        }
    }
    Shape {
        visible: overlay.drawing && overlay.vertices.length >= 2 && overlay.segments.length >= 2
                 && !overlay.draft.rectangle && overlay.draft.tool !== "ridge" && overlay.draft.tool !== "prop_line"
        ShapePath {
            strokeColor: overlay.drawColor
            strokeWidth: 1.2
            fillColor: "transparent"
            strokeStyle: ShapePath.DashLine
            dashPattern: [4,2]
            PathPolyline {
                path: overlay.segments.length ? overlay.mapped([overlay.segments[overlay.segments.length-1],overlay.segments[0]]) : []
            }
        }
    }
    Shape {
        objectName: "drawingEave"
        visible: overlay.draft.tool === "pitch" && !!overlay.draft.pitch
        ShapePath {
            strokeColor: overlay.haloColor
            strokeWidth: 8.6
            fillColor: "transparent"
            PathPolyline { path: overlay.eavePoints() }
        }
        ShapePath {
            strokeColor: overlay.colors.sel
            strokeWidth: 5.6
            fillColor: "transparent"
            PathPolyline { path: overlay.eavePoints() }
        }
    }
    Repeater {
        model: overlay.vertices
        delegate: Rectangle {
            required property var modelData
            readonly property point at: overlay.screen(modelData)
            objectName: "drawingVertex"
            visible: overlay.draft.tool !== "measure"
            x: at.x-width/2; y: at.y-height/2
            width: 8; height: 8
            color: "transparent"
            border.color: overlay.drawColor
            border.width: MC.ControlMetrics.planStroke
        }
    }
    Shape {
        id: snapMarker
        objectName: "drawingSnap"
        readonly property point at: overlay.draft.pointer ? overlay.screen(overlay.draft.pointer) : Qt.point(0,0)
        visible: !!overlay.draft.pointer && ["vertex","midpoint","intersection","close","edge"].indexOf(overlay.draft.snap) >= 0
        ShapePath {
            strokeColor: overlay.guideColor
            strokeWidth: 1.6
            fillColor: "transparent"
            PathPolyline {
                path: overlay.draft.snap === "midpoint"
                    ? [Qt.point(snapMarker.at.x,snapMarker.at.y-5),Qt.point(snapMarker.at.x+5,snapMarker.at.y+4),
                       Qt.point(snapMarker.at.x-5,snapMarker.at.y+4),Qt.point(snapMarker.at.x,snapMarker.at.y-5)]
                    : [Qt.point(snapMarker.at.x-4,snapMarker.at.y-4),Qt.point(snapMarker.at.x+4,snapMarker.at.y-4),
                       Qt.point(snapMarker.at.x+4,snapMarker.at.y+4),Qt.point(snapMarker.at.x-4,snapMarker.at.y+4),
                       Qt.point(snapMarker.at.x-4,snapMarker.at.y-4)]
            }
        }
    }
    Shape {
        id: transformMark
        objectName: "transformBaseMark"
        readonly property var point: overlay.draft.pivot || overlay.draft.base || null
        readonly property point at: point ? overlay.screen(point) : Qt.point(0,0)
        visible: point !== null && overlay.draft.type === "transform"
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: overlay.drawColor; strokeWidth: 1.6; fillColor: "transparent"
            PathSvg {
                path: overlay.draft.mode === "rotate"
                    ? "M"+(transformMark.at.x-5)+","+(transformMark.at.y-5)+" l10,10 m-10,0 l10,-10"
                    : "M"+(transformMark.at.x-5)+","+(transformMark.at.y-5)+" h10 v10 h-10 Z"
            }
        }
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
