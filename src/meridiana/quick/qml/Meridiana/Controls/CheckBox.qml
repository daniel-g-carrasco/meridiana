import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.CheckBox {
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
            radius: Theme.radius.INNER
            color: root.enabled && root.checkState !== Qt.Unchecked ? Theme.colors.select_bg : Theme.colors.field
            border.width: Theme.line.HAIR
            border.color: !root.enabled ? Theme.colors.line : root.hovered ? Theme.colors.text2 : Theme.colors.field_line
            Rectangle { anchors.fill: parent; anchors.margins: 1; radius: Theme.radius.INNER - 1
                color: root.enabled ? (root.down ? Theme.colors.press : root.hovered ? Theme.colors.hover : "transparent") : "transparent" }
            CheckMark { anchors.fill: parent; visible: root.checkState !== Qt.Unchecked
                partial: root.checkState === Qt.PartiallyChecked; color: root.enabled ? Theme.colors.text : Theme.colors.muted }
        }
        Rectangle { anchors.centerIn: parent; width: Theme.icon.CONTROL + 5; height: width
            visible: root.enabled && root.activeFocus; color: "transparent"; radius: Theme.radius.CONTROL + 1
            border.width: Theme.line.FOCUS; border.color: Theme.colors.accent }
    }
    contentItem: Label { leftPadding: root.indicator.width + root.spacing; text: root.text; enabled: root.enabled; wrapMode: Text.WordWrap }
}
