import QtQuick
import Meridiana.Theme
// ui/fades.py: overlays only the viewport, never its border or scroll bar.
Item {
    id: root
    property Flickable flickable
    property bool page: false
    property bool table: false
    property color ground: Theme.colors.panel
    // A page of text (Meridio's conversation, the panels' pages) veils a whole line, 24 px over lines of about 20: a
    // veil of 12 px left the half of a line cut by the edge almost bare (R489, Daniel 07/11/2026, the third time).
    // Lists and tables keep the short veil, their rows are the unit and the first one must read at once (R192).
    readonly property real bandHeight: Math.min(page ? Theme.space.XXL : Theme.space.L, Math.floor(height / 5))
    // A bar inside the list keeps out of the veil (R161: never over a border or a bar).
    property real barRoom: 0
    anchors.fill: flickable
    anchors.rightMargin: barRoom
    z: 10
    component Band: Image {
        required property bool topEdge
        width: root.width
        height: root.bandHeight
        // Image multiplies sourceSize by the window DPR before asking the provider.
        sourceSize: Qt.size(Math.round(width), Math.round(height))
        source: width > 0 && height > 0 ? "image://meridiana/fade:" + (topEdge ? "top" : "bottom") + "/" + encodeURIComponent(root.ground) + "/" + Screen.devicePixelRatio + "/" + (root.page ? "page" : root.table ? "table" : "list") : ""
        smooth: false
    }
    // R489: a veil comes in with the scrolling, whole once the list has moved by its height: shown whole at the first
    // pixel, it was a jump.
    readonly property real above: flickable !== null ? flickable.contentY - flickable.originY : 0
    readonly property real below: flickable !== null ? flickable.originY + flickable.contentHeight - flickable.contentY - flickable.height : 0
    Band { objectName: "topFade"; topEdge: true
        opacity: Math.max(0, Math.min(1, root.above / Math.max(1, root.bandHeight))); visible: opacity > 0 }
    Band { objectName: "bottomFade"; topEdge: false; anchors.bottom: parent.bottom
        opacity: Math.max(0, Math.min(1, root.below / Math.max(1, root.bandHeight))); visible: opacity > 0 }
}
