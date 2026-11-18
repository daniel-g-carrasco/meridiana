import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

M.ToolButton {
    id: root
    property bool primary: false
    // R396 deliberately removes the old primary emphasis from Calculate/Place.
    flat: true
    contentItem: Item {
        M.Icon { id: symbol; iconName: root.iconName; width: Theme.bar.ICON[root.mode]; height: width
            x: root.mode==="beside" ? 0 : (parent.width-width)/2
            y: root.mode==="under" ? (parent.height-height-word.implicitHeight-Theme.space.XXS)/2 : (parent.height-height)/2
            color: root.enabled ? Theme.colors.text : Theme.disabledText }
        M.Label { id: word; text: root.text; textStyle: "secondary"; condensed: true; enabled: root.enabled
            visible: root.mode!=="icons"
            x: root.mode==="beside" ? symbol.width+Theme.bar.WORD_GAP : (parent.width-width)/2
            y: root.mode==="under" ? symbol.y+symbol.height+Theme.space.XXS : (parent.height-height)/2 }
    }
}
