import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    required property var tile
    signal triggered(string action)
    property real descriptionHeight: Math.max(description.implicitHeight, Theme.text.description.size * 2.5)
    // the formats beside the button when both fit on its line, otherwise on a line of their own above it (large text
    // in a narrow tile: «Salva con nome…» covered «.meridiana», test_confini R406)
    readonly property bool stacked: formats.width > 0
        && title.x + formats.width + Theme.space.M + action.width > root.width - Theme.space.XL
    implicitHeight: Theme.space.L * 2 + title.implicitHeight + descriptionHeight + Theme.space.S * 3 + action.height
        + (stacked ? formats.height + Theme.space.S : 0)
    color: Theme.colors.field
    radius: Theme.radius.CARD
    M.Icon { id: mark; x: Theme.space.XL; y: M.ControlMetrics.firstLineMiddle(title) - height / 2
        width: Theme.icon.TILE; height: width; iconName: root.tile.icon }
    M.ReadableText {
        id: title
        x: mark.x + mark.width + Theme.space.L; y: Theme.space.L
        width: root.width - x - Theme.space.XL
        text: root.tile.title; textStyle: "title"; wrapMode: Text.WordWrap
    }
    M.ReadableText {
        id: description
        x: title.x; y: title.y + title.height + Theme.space.S; width: title.width
        text: root.tile.description; textStyle: "description"; wrapMode: Text.WordWrap
    }
    Row {
        id: formats
        x: title.x
        y: root.stacked ? action.y - Theme.space.S - height : action.y + (action.height - height) / 2
        spacing: Theme.space.S
        Repeater {
            model: root.tile.formats ? root.tile.formats.split(" · ") : []
            Rectangle {
                required property string modelData
                width: formatLabel.implicitWidth + 2 * Theme.space.S + 2
                height: action.height
                color: "transparent"; radius: Theme.radius.CONTROL
                border.width: Theme.line.HAIR; border.color: Theme.colors.line
                M.CopyLabel { id: formatLabel; anchors.centerIn: parent; text: modelData; textStyle: "caption"; color: Theme.colors.text2 }
            }
        }
    }
    M.Button {
        id: action
        objectName: "fileAction_" + root.tile.action
        anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.rightMargin: Theme.space.XL; anchors.bottomMargin: Theme.space.L
        text: root.tile.button
        background: Rectangle {
            radius: Theme.radius.CONTROL
            color: Theme.colors.panel
            border.width: Theme.focusRing(action) ? Theme.line.FOCUS : 0
            border.color: Theme.colors.focus
            Rectangle { anchors.fill: parent; radius: parent.radius; color: action.down ? Theme.colors.press : action.hovered ? Theme.colors.hover : "transparent" }
        }
        onClicked: root.triggered(root.tile.action)
    }
}
