import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: root
    required property var backend
    property var rows: []
    spacing: Theme.space.S
    Repeater {
        model: root.rows
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: Theme.space.XXS
            RowLayout {
                Layout.fillWidth: true
                Rectangle { width: 6; height: 6; radius: 3; color: root.backend.statusColors[modelData.level] || Theme.colors.muted }
                M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "secondary"
                    text: modelData.label + (modelData.detail ? ": " + modelData.detail : "") }
            }
            M.Label { Layout.fillWidth: true; visible: text !== ""; wrapMode: Text.Wrap
                textStyle: "caption"; text: modelData.source || "" }
            Rectangle { Layout.fillWidth: true; height: Theme.line.HAIR; color: Theme.colors.line }
        }
    }
}
