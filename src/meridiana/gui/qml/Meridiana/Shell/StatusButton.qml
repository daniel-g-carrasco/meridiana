import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

M.Button {
    id: root
    // A card on screen has its icon full, a closed or covered one faint (ui/panel_buttons.py, _show).
    property bool seen: true
    flat: true; focusPolicy: Qt.NoFocus
    implicitWidth: Theme.size.CONTROL; implicitHeight: Theme.size.CONTROL
    padding: (Theme.size.CONTROL-Theme.icon.CONTROL)/2
    topPadding: padding; bottomPadding: padding
    contentItem: Item {
        M.Icon { anchors.centerIn: parent; iconName: root.iconName; width: Math.min(parent.width, parent.height); height: width
            color: !root.seen ? Theme.colors.muted : Theme.colors.text }
    }
}
