import QtQuick
import QtQuick.Shapes

// The plan's public projection follows zoom, bearing and pan entirely in QML.
Shape {
    id: root
    objectName: "property-side-highlight"
    required property var view
    required property var backend
    anchors.fill: parent
    z: 10
    visible: backend.sideSegment.length === 2 && view.backend.tool === "select"
    readonly property point a: visible ? view.screen(backend.sideSegment[0][0], backend.sideSegment[0][1]) : Qt.point(0, 0)
    readonly property point b: visible ? view.screen(backend.sideSegment[1][0], backend.sideSegment[1][1]) : Qt.point(0, 0)
    preferredRendererType: Shape.CurveRenderer
    ShapePath {
        strokeColor: root.view.backend.planColors.sel
        strokeWidth: 5
        fillColor: "transparent"
        capStyle: ShapePath.SquareCap
        startX: root.a.x; startY: root.a.y
        PathLine { x: root.b.x; y: root.b.y }
    }
}
