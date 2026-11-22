import QtQuick
import Meridiana.Theme

// A string or series colour, with its border on whole device pixels.
Item {
    id: root
    property color color: "transparent"
    implicitWidth: Theme.icon.CONTROL - 4
    implicitHeight: implicitWidth
    readonly property real dpr: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    readonly property point scene: {
        for (let node = root; node; node = node.parent) { node.x; node.y }
        return mapToItem(null, 0, 0)
    }
    Rectangle {
        x: ControlMetrics.pixelSnap(root.scene.x, 0, root.dpr)
        y: ControlMetrics.pixelSnap(root.scene.y, 0, root.dpr)
        width: Math.round(root.width * root.dpr) / root.dpr
        height: Math.round(root.height * root.dpr) / root.dpr
        radius: Theme.radius.MARK
        color: root.color
        border.width: Math.max(1, Math.round(root.dpr)) / root.dpr
        border.color: Qt.rgba(0, 0, 0, 60 / 255)
    }
    Accessible.ignored: true
}
