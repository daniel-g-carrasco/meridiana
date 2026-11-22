import QtQuick
import QtQuick.Shapes

// Screen-space stroke, shared by every proposed line in this study.
Item {
    id: root
    required property point a
    required property point b
    property color ink: "orange"
    property real thickness: 1.5
    property real haloOpacity: 0
    property color haloInk: "black"
    property real haloExtra: 2
    property bool dashed: false
    property bool haloOnly: false
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        antialiasing: true
        opacity: root.haloOpacity
        ShapePath {
            strokeColor: root.haloInk
            strokeWidth: root.thickness + root.haloExtra
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: root.a.x; startY: root.a.y
            PathLine { x: root.b.x; y: root.b.y }
        }
    }
    Shape {
        visible: !root.haloOnly
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        antialiasing: true
        ShapePath {
            strokeColor: root.ink
            strokeWidth: root.thickness
            fillColor: "transparent"
            capStyle: root.dashed ? ShapePath.FlatCap : ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            strokeStyle: root.dashed ? ShapePath.DashLine : ShapePath.SolidLine
            // Six logical pixels on, four off, independent of stroke width.
            dashPattern: [6 / root.thickness, 4 / root.thickness]
            startX: root.a.x; startY: root.a.y
            PathLine { x: root.b.x; y: root.b.y }
        }
    }
}
