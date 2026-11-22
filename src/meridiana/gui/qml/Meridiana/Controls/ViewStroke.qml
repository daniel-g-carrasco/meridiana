import QtQuick
import QtQuick.Window
import QtQuick.Shapes
import Meridiana.Theme

// Screen-space strokes and their always-present, uniform translucent halo.
Shape {
    id: root
    property var points: []
    property var paths: [points]
    property string svg: ""
    property color ink: Theme.colors.overlay.pill_ink
    property color ground: "transparent"
    property bool dashed: false
    property real viewScale: 1
    readonly property real thickness: Theme.annotation.STROKE
    readonly property real haloExtra: Theme.annotation.HALO_EXTRA
    readonly property color haloInk: Qt.rgba(0, 0, 0, Theme.annotation.HALO_ALPHA)
    preferredRendererType: Shape.CurveRenderer
    antialiasing: true
    ViewPath {
                surface: root
        halo: true
        dashed: root.dashed; viewScale: root.viewScale
        PathMultiline { paths: root.svg ? [] : root.paths }
        PathSvg { path: root.svg }
    }
    ViewPath {
                surface: root
        strokeColor: root.ink; fillColor: root.ground
        dashed: root.dashed; viewScale: root.viewScale
        PathMultiline { paths: root.svg ? [] : root.paths }
        PathSvg { path: root.svg }
    }
}
