import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

M.ToolButton {
    id: root
    property bool primary: false
    // R396 deliberately removes the old primary emphasis from Calculate/Place.
    flat: true
    // R614: the icon and the word in the middle in every mode, so that the air the width's steps leave is the same on the
    // two sides, before the word as after it (up to a split button's strip: PhaseSplitButton's command is this button)
    contentItem: Item {
        M.Icon { id: symbol; iconName: root.iconName; width: Theme.bar.ICON[root.mode]; height: width
            x: root.mode==="beside" ? Math.round((parent.width-width-Theme.bar.WORD_GAP-word.implicitWidth)/2) : (parent.width-width)/2
            y: root.mode==="under" ? (parent.height-height-word.implicitHeight-Theme.space.XXS)/2 : (parent.height-height)/2
            color: root.enabled ? Theme.colors.text : Theme.disabledText }
        M.Label { id: word; text: root.text; textStyle: "secondary"; condensed: true; enabled: root.enabled
            visible: root.mode!=="icons"
            x: root.mode==="beside" ? symbol.x+symbol.width+Theme.bar.WORD_GAP : (parent.width-width)/2
            y: root.mode==="under" ? symbol.y+symbol.height+Theme.space.XXS : (parent.height-height)/2 }
    }
}
