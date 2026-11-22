import QtQuick

// R641 (Daniel 15/11/2026: «sti tasti di errore, ecc, non sono cliccabili, non hanno tooltip»): what a check's mark on
// a view does under the pointer, one rule for the plan (Plan.qml) and the 3D view (Checks/SceneMarks.qml): the hand,
// the words of its checks in the house tooltip, and a click, whose target each view gives in onClicked. The hover is
// a handler's, so the view under the mark still follows the pointer (the plan's module under a sub-field's mark, R529).
MouseArea {
    id: root
    property string tip: ""
    readonly property bool hovered: hover.hovered
    anchors.fill: parent
    cursorShape: Qt.PointingHandCursor
    HoverHandler { id: hover }
    ToolTip { objectName: "markTip"; parent: root; text: root.tip; visible: root.hovered && root.tip !== "" }
}
