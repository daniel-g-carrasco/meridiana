import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

M.Button {
    id: root
    property bool arrow: false
    flat: true
    focusPolicy: Qt.NoFocus
    implicitWidth: 31 + (arrow ? 16 : 0)
    implicitHeight: M.ControlMetrics.viewButton
    padding: 0
    contentItem: Item {
        M.Icon { name: root.iconName; width: 16; height: 16; x: Math.floor((root.width-(root.arrow ? 16 : 0)-width)/2); anchors.verticalCenter: parent.verticalCenter }
        M.Icon { visible: root.arrow; name: "field:down"; width: 10; height: 6
            anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter }
    }
    background: Rectangle {
        radius: Theme.radius.INNER
        color: root.down || root.checked ? Theme.colors.press : root.hovered ? Theme.colors.hover : "transparent"
    }
}
