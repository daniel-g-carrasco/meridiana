import QtQuick
import Meridiana.Controls as M

M.Label {
    id: root
    property string fullText: text
    elide: Text.ElideRight
    HoverHandler { id: hover }
    M.ToolTip { text: root.fullText; visible: hover.hovered && root.truncated }
    Accessible.name: fullText
}
