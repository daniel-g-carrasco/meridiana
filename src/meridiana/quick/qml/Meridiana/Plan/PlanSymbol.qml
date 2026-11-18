import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// A screen-sized status symbol. Supply shapes + name, or a single shape record. Drawn by the icon provider at the
// pixels it covers (symbols.paint, the drawing of the Widgets), sharp at every scale of the screen (R464); its sign is
// cut out of the ground. `pill`: on the views, the symbol in a disc of the plan's pills (`pillColour`, their
// label_bg), whose dark shows through the sign instead of the orthophoto (Daniel 06/11/2026: «lo metti dentro un
// pallino con lo stile grafico delle pillole in pianta»).
Item {
    id: root
    property string name: "info"
    property var shapes: ({})
    property var shape: shapes[name] || ({})
    property int count: 1
    property string countText: shape.countText || count.toLocaleString(Qt.locale(), "f", 0)
    property real size: pill ? 22 : 18
    property bool pill: false
    // in a round place (a pill's round end): the sign on its enclosing centre, the warning's triangle lower (R515)
    property bool round: false
    property color pillColour: Theme.colors.overlay.glass
    property string fontFamily: Qt.application.font.family
    implicitWidth: size
    implicitHeight: size
    width: implicitWidth
    height: implicitHeight
    M.Icon {
        objectName: "planSymbolImage"
        anchors.fill: parent
        name: (root.pill ? "mark:" : "symbol:") + root.name
        color: root.pill ? root.pillColour : "black"
        dark: !!root.shape.dark
        variant: root.round && !root.pill ? "round" : ""
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
