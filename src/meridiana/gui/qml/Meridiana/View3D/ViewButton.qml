import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

M.Button {
    id: root
    flat: true
    focusPolicy: Qt.NoFocus
    implicitWidth: M.ControlMetrics.viewPlainWidth
    implicitHeight: M.ControlMetrics.viewButton
    padding: 0
    contentItem: Item {
        M.Icon { name: root.iconName; width: 16; height: 16; x: Math.floor((root.width-width)/2); anchors.verticalCenter: parent.verticalCenter }
    }
    background: Rectangle {
        radius: Theme.radius.INNER
        color: root.down || root.checked ? Theme.colors.press : root.hovered ? Theme.colors.hover : "transparent"
    }
}
