import QtQuick
import Meridiana.Theme

// R592: the two steps of a number, one for every field that has them (M.NumberField, the numbers of the Properties):
// two flat buttons in a column, each with its full arrow (M.Arrow) on its middle, repeating while held.
Column {
    id: root
    property bool upEnabled: true
    property bool downEnabled: true
    signal stepped(int direction)
    width: Theme.space.XL
    Repeater {
        model: [1, -1]
        Button {
            id: step
            required property int modelData
            width: root.width; height: root.height / 2; padding: 0; flat: true; focusPolicy: Qt.NoFocus
            enabled: root.enabled && (modelData > 0 ? root.upEnabled : root.downEnabled)
            autoRepeat: true
            contentItem: Item { Arrow { anchors.fill: parent; direction: modelData > 0 ? "up" : "down"; active: step.hovered || step.down } }
            background: Item {}
            onClicked: root.stepped(modelData)
        }
    }
}
