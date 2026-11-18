import QtQuick
import Meridiana.Theme
Item {
    id: root
    property string title: ""
    property string description: ""
    property string actionText: ""
    property string iconName: ""
    signal triggered()
    implicitWidth: Theme.size.READING
    implicitHeight: content.implicitHeight + Theme.space.XL * 2
    Column { id: content; anchors.centerIn: parent; width: Math.max(0, Math.min(parent.width - 2 * Theme.space.XL, Theme.size.READING)); spacing: Theme.space.M
        Icon { name: root.iconName; visible: name !== ""; width: Theme.icon.TILE; height: width; anchors.horizontalCenter: parent.horizontalCenter; color: Theme.colors.muted }
        Label { text: root.title; textStyle: "secondary"; color: Theme.colors.text2; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
        Label { text: root.description; textStyle: "description"; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; visible: text !== "" }
        Button { text: root.actionText; visible: text !== ""; anchors.horizontalCenter: parent.horizontalCenter; onClicked: root.triggered() }
    }
}
