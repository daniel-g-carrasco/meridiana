import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// A row of ui/properties.make_form (QFormLayout, WrapLongRows): label and field on one line while they fit, the field
// under its label when the panel is narrow. `labelWidth` holds a column for rows that go together; `wrapLabel` is the
// label that goes on two lines before the field is pushed down (the words wrap, the field stays).
Item {
    id: root
    property string label: ""
    property bool wrapLabel: false
    property real labelWidth: 0
    property real fieldMinimum: 80
    property string tip: ""
    default property alias field: slot.data
    readonly property real gap: Theme.space.S
    readonly property real wanted: labelWidth > 0 ? labelWidth : wrapLabel ? Math.min(words.implicitWidth, 120 * Theme.type.BODY / 13) : words.implicitWidth
    readonly property bool stacked: wanted + gap + fieldMinimum > width
    readonly property real fieldHeight: slot.children.length ? slot.children[0].implicitHeight : Theme.size.CONTROL
    implicitHeight: stacked ? words.implicitHeight + Theme.space.XS + fieldHeight : Math.max(words.height, fieldHeight)
    M.Label {
        id: words
        width: root.stacked ? root.width : root.wanted
        height: root.stacked ? implicitHeight : Math.max(implicitHeight, root.fieldHeight)
        text: root.label; wrapMode: Text.Wrap
    }
    Item {
        id: slot
        x: root.stacked ? 0 : root.wanted + root.gap
        y: root.stacked ? words.height + Theme.space.XS : 0
        width: root.width - x
        height: root.fieldHeight
        HoverHandler { id: fieldHover }
        M.ToolTip { visible: fieldHover.hovered && root.tip !== ""; text: root.tip }
    }
}
