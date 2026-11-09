import QtQuick
import Meridiana.Theme
import Meridiana.Controls as Controls

// What the signs of the strings mean when there are power optimizers (R424). Over the plan, in the plan's colours.
Rectangle {
    id: root
    property var words: []
    radius: Theme.radius.INNER
    color: Theme.colors.overlay.legend
    implicitWidth: row.implicitWidth + 2 * Theme.space.S
    implicitHeight: row.implicitHeight + 2 * Theme.space.XS
    width: implicitWidth; height: implicitHeight
    Row {
        id: row
        x: Theme.space.S; y: Theme.space.XS
        spacing: Theme.space.M
        Repeater {
            model: root.words
            Row {
                required property var modelData
                required property int index
                spacing: Theme.space.XS
                Item {
                    width: 16; height: 12; anchors.verticalCenter: parent.verticalCenter
                    Rectangle { visible: index === 0; anchors.centerIn: parent; width: 8; height: 8; color: Theme.colors.overlay.add; border.color: Theme.colors.overlay.legend_line }
                    Rectangle { visible: index === 1; anchors.centerIn: parent; width: 16; height: 3; color: Theme.colors.overlay.add }
                    Rectangle { visible: index === 2; anchors.centerIn: parent; width: 16; height: 1; color: Theme.colors.overlay.add }
                }
                Controls.Label { text: modelData; textStyle: "caption"; color: Theme.colors.overlay.white }
            }
        }
    }
}
