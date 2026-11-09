import QtQuick
import QtQuick.Shapes
import QtQuick.Window

Shape {
    id: root
    property color color
    readonly property real pixel: 1/(root.Window.window ? root.Window.window.devicePixelRatio : 1)
    preferredRendererType: Shape.CurveRenderer
    ShapePath {
        strokeColor: root.color; strokeWidth: root.pixel; fillColor: "transparent"
        strokeStyle: ShapePath.DashLine; dashPattern: [4,2]
        startX: .5; startY: 0
        PathLine { x: .5; y: root.height }
    }
}
