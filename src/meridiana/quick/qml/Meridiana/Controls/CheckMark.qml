import QtQuick
import Meridiana.Theme

// F5 (r23-f5): one check mark for the whole program. Without a level it is the tick of the boxes and the menus
// (partial: the stop sign). With a level (fail, warn, info, ok) it is the symbol of a check (it was Checks/CheckMark):
// drawn by the icon provider at the pixels it covers (R464, symbols.paint as in the Widgets, never a data-URL SVG
// scaled by the scene graph), on the views (the 3D) in a disc of the plan's pills, with the count over it when the
// same place has more than one.
Icon {
    id: root
    property bool partial: false
    property string level: ""
    property int count: 1
    property bool views: false
    // kept for the callers of the checks: the symbols come from the icon provider
    property var symbols: null
    property color pillColour: Theme.colors.overlay.glass
    readonly property bool levelMark: level !== ""
    name: levelMark ? (views ? "mark:" : "symbol:") + level : partial ? "sign:stop" : "sign:check"
    color: levelMark ? (views ? pillColour : "black") : enabled ? Theme.colors.text : Theme.disabledText
    dimDisabled: !levelMark
    implicitWidth: levelMark ? (views ? 22 : 18) : Theme.icon.CONTROL
    Rectangle {
        visible: root.levelMark && root.count > 1
        x: root.width / 2 + root.width / 2 * .45
        y: root.height / 2 - root.height / 2 * 1.25
        width: root.width * .72
        height: root.height * .62
        radius: Theme.radius.INNER
        color: Theme.colors.overlay.badge
        Text { anchors.centerIn: parent; text: root.count
            font.family: Theme.fontFamily; font.pixelSize: Math.floor(root.width * .48); font.bold: true; color: "white" }
    }
}
