import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    required property var backend
    property bool expanded: true
    objectName: "settingsAppearancePreview"
    color: Theme.colors.panel
    radius: Theme.radius.CONTROL
    border.color: Theme.colors.line
    implicitHeight: heading.height + (expanded ? sample.height + Theme.space.M * 2 : 0)
    M.Button {
        id: heading
        width: parent.width; height: Theme.size.CONTROL - Theme.space.XXS
        flat: true; text: root.backend.text.preview
        contentItem: Row {
            spacing: Theme.space.S
            M.Icon { name: "chevron-right"; rotation: root.expanded ? 90 : 0; anchors.verticalCenter: parent.verticalCenter }
            M.Label { text: heading.text; textStyle: "strong"; anchors.verticalCenter: parent.verticalCenter }
        }
        background: Rectangle { radius: Theme.radius.CONTROL; color: Theme.colors.hover }
        onClicked: root.expanded = !root.expanded
    }
    Column {
        id: sample
        visible: root.expanded
        x: Theme.space.M + Theme.space.XXS; y: heading.height + Theme.space.M
        width: parent.width - 2*x
        spacing: Theme.space.S
        Rectangle {
            width: parent.width; height: sampleBody.height + 2 * (Theme.space.M + Theme.space.XXS)
            color: Theme.colors.window; border.color: Theme.colors.line
            Column {
                id: sampleBody
                x: Theme.space.M + Theme.space.XXS; y: x; width: parent.width - 2*x
                spacing: Theme.space.S
                Rectangle {
                    width: parent.width; height: 76; radius: Theme.radius.CONTROL
                    color: Theme.colors.card; border.color: Theme.colors.line
                    Column {
                        x: 3; y: 2; width: parent.width - 6
                        Repeater {
                            model: [root.backend.text.building, root.backend.text.south, root.backend.text.east]
                            delegate: Rectangle {
                                required property string modelData
                                required property int index
                                width: parent.width; height: label.implicitHeight
                                objectName: index === 1 ? "settingsPreviewSelection" : ""
                                color: index === 1 ? Theme.colors.select_bg : "transparent"
                                M.Label { id: label; x: 1; text: modelData }
                            }
                        }
                    }
                }
                Item {
                    width: parent.width; height: Theme.size.CONTROL
                    M.Button { text: root.backend.text.lay; height: parent.height
                        background: Rectangle { color: Theme.colors.field; radius: Theme.radius.CONTROL; border.color: Theme.colors.accent; border.width: Theme.line.FOCUS }
                    }
                    Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 22; height: 22; radius: 11; color: Theme.colors.assistant; border.color: Theme.colors.assistant_line }
                }
                Row {
                    width: parent.width; spacing: Theme.space.XS
                    M.Icon { name: "symbol:warning"; color: Theme.status.warning || Theme.colors.accent; width: 14; height: 14 }
                    M.Label { objectName: "settingsPreviewWarning"; width: parent.width - 18; text: root.backend.text.warning; wrapMode: Text.WordWrap }
                }
            }
        }
        M.Label { width: parent.width; text: root.backend.appearancePreview.contrast; wrapMode: Text.WordWrap }
        M.Label { width: parent.width; text: root.backend.appearancePreview.note; wrapMode: Text.WordWrap }
    }
}
