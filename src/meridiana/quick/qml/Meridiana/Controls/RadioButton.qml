import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme

// R21-F2: one choice among a few, on M.CheckBox's metrics: the same square of room, a disc instead of the box, a dot
// instead of the check; the same ground, borders, hover, press and focus ring.
T.RadioButton {
    id: root
    implicitWidth: contentItem.implicitWidth
    implicitHeight: Math.max(Theme.size.CONTROL, contentItem.implicitHeight)
    spacing: Theme.space.M
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    indicator: Item {
        width: Theme.icon.CONTROL + Theme.space.S; height: width; y: (root.height-height)/2
        Rectangle {
            anchors.centerIn: parent; width: Theme.icon.CONTROL; height: width
            radius: width / 2
            color: root.enabled && root.checked ? Theme.colors.select_bg : Theme.colors.field
            border.width: Theme.line.HAIR
            border.color: !root.enabled ? Theme.colors.line : root.hovered ? Theme.colors.text2 : Theme.colors.field_line
            Rectangle { anchors.fill: parent; anchors.margins: 1; radius: width / 2
                color: root.enabled ? (root.down ? Theme.colors.press : root.hovered ? Theme.colors.hover : "transparent") : "transparent" }
            Rectangle { anchors.centerIn: parent; width: parent.width / 2; height: width; radius: width / 2
                visible: root.checked; color: root.enabled ? Theme.colors.text : Theme.colors.muted }
        }
        Rectangle { anchors.centerIn: parent; width: Theme.icon.CONTROL + 5; height: width
            visible: root.enabled && root.activeFocus; color: "transparent"; radius: width / 2
            border.width: Theme.line.FOCUS; border.color: Theme.colors.accent }
    }
    contentItem: Label { leftPadding: root.indicator.width + root.spacing; text: root.text; enabled: root.enabled; wrapMode: Text.WordWrap }
}
