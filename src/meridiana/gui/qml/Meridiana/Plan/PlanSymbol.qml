import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// A screen-sized status symbol. Supply shapes + name, or a single shape record. Drawn by the icon provider at the
// pixels it covers (symbols.paint), sharp at every scale of the screen (R464); its sign is white. `views`: a check's
// mark on the plan, with the thin white edge of the views' marks (symbols.paint_view, the same as the 3D's CheckMark),
// no disc round it (Daniel 14/11/2026).
Item {
    id: root
    property string name: "info"
    property var shapes: ({})
    property var shape: shapes[name] || ({})
    property int count: 1
    property string countText: shape.countText || count.toLocaleString(Qt.locale(), "f", 0)
    property real size: views ? M.ControlMetrics.viewMark : 18
    property bool views: false
    // in a round place (a pill's round end): the sign on its enclosing centre, the warning's triangle lower (R515)
    property bool round: false
    property string fontFamily: Qt.application.font.family
    implicitWidth: size
    implicitHeight: size
    width: implicitWidth
    height: implicitHeight
    M.Icon {
        objectName: "planSymbolImage"
        anchors.fill: parent
        name: (root.views ? "mark:" : "symbol:") + root.name
        color: "black"
        dark: !!root.shape.dark
        variant: root.round && !root.views ? "round" : ""
        dimDisabled: false
    }
    Rectangle {
        objectName: "markCountBadge"
        visible: root.count > 1
        x: root.size * 0.725
        y: -root.size * 0.125
        width: Math.max(root.size * 0.72, countLabel.implicitWidth + 4)
        height: root.size * 0.62
        radius: Theme.radius.INNER
        color: Theme.colors.overlay.badge
        Text {
            id: countLabel
            anchors.centerIn: parent
            text: root.countText
            color: Theme.colors.overlay.white
            font.family: root.fontFamily
            font.pixelSize: Math.floor(root.size * 0.48)
            font.bold: true
        }
    }
}
