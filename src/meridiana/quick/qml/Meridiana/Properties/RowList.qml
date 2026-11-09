import QtQuick
import QtQuick.Layouts
import Meridiana.Controls as M
import Meridiana.Theme

Column {
    id: root
    property var rows: []
    property string emptyText: ""
    M.Label { width: parent.width; visible: root.rows.length === 0; text: root.emptyText; wrapMode: Text.Wrap }
    Repeater {
        model: root.rows
        delegate: Column {
            required property var modelData
            required property int index
            width: root.width
            Rectangle { width: parent.width; height: index ? Theme.line.HAIR : 0; color: Theme.colors.line }
            RowLayout {
                width: parent.width
                spacing: Theme.space.L
                ElidedLabel { text: modelData[0]; fullText: modelData.length > 2 ? modelData[2] : modelData[0] + ": " + modelData[1]
                    textStyle: "strong"; Layout.maximumWidth: root.width * 0.55; Layout.topMargin: Theme.space.S; Layout.bottomMargin: Theme.space.S }
                M.Label { text: modelData[1]; textStyle: "secondary"; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
            }
        }
    }
}
