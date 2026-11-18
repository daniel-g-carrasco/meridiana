import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.Control {
    id: root
    property var model: []
    property int _selection: 0
    property int currentIndex: _selection
    property bool dimDisabled: true
    property real segmentExtra: 2
    signal activated(int index)
    readonly property var segmentWidths: model.map(entry => Math.round(Theme.measureText(typeof entry === "string" ? entry : entry.text, "control", false).width) + 2 * Theme.space.L + segmentExtra)
    readonly property real naturalWidth: segmentWidths.reduce((sum, width) => sum + width, 0)
    implicitWidth: naturalWidth + 2 * padding
    implicitHeight: Theme.size.CHIP + 2 * padding
    padding: Theme.space.XXS
    focusPolicy: Qt.StrongFocus
    function choose(index) {
        if (index >= 0 && index < choices.count && index !== currentIndex) { _selection = index; activated(index) }
    }
    function segmentWidth(index) {
        if (!choices.count || !naturalWidth || index < 0 || index >= choices.count) return 0
        return availableWidth >= naturalWidth ? segmentWidths[index] + (availableWidth-naturalWidth)/choices.count
                                             : segmentWidths[index] * availableWidth / naturalWidth
    }
    function segmentX(index) { let x = 0; for (let i = 0; i < index; i++) x += segmentWidth(i); return x }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Home) { choose(0); event.accepted = true }
        else if (event.key === Qt.Key_End) { choose(choices.count-1); event.accepted = true }
    }
    Keys.onRightPressed: choose(Math.min(choices.count-1, currentIndex+1))
    Keys.onLeftPressed: choose(Math.max(0, currentIndex-1))
    background: Rectangle { color: Theme.colors.field; radius: Theme.radius.CONTROL }
    contentItem: Item {
        Rectangle { id: raised
            objectName: "segmentSelection"
            x: root.segmentX(Math.max(0, root.currentIndex)); width: root.segmentWidth(root.currentIndex); height: parent.height
            color: Theme.colors.panel; radius: Theme.radius.INNER
            border.width: root.visualFocus ? Theme.line.FOCUS : Theme.line.HAIR
            border.color: root.visualFocus ? Theme.colors.accent : Theme.colors.line
            Behavior on x { NumberAnimation { duration: Theme.motion.FAST; easing.type: Theme.motion.EASE } }
            Behavior on width { NumberAnimation { duration: Theme.motion.FAST; easing.type: Theme.motion.EASE } }
        }
        Row { anchors.fill: parent
            Repeater { id: choices; model: root.model
                Button { required property var modelData; required property int index
                    text: typeof modelData === "string" ? modelData : modelData.text
                    width: root.segmentWidth(index); height: root.availableHeight
                    flat: true; padding: Theme.space.S; focusPolicy: Qt.NoFocus
                    Accessible.role: Accessible.RadioButton; Accessible.checked: index === root.currentIndex
                    tip: typeof modelData === "object" && modelData.tip ? modelData.tip : text
                    textCut: segmentText.truncated      // R528: read from the label itself (through contentItem it stayed false)
                    background: Rectangle { radius: Theme.radius.INNER
                        color: index !== root.currentIndex && parent.enabled ? (parent.down ? Theme.colors.press : parent.hovered ? Theme.colors.hover : "transparent") : "transparent" }
                    contentItem: Label { id: segmentText; text: parent.text; textStyle: "control"; horizontalAlignment: Text.AlignHCenter
                        enabled: root.enabled; color: !enabled && root.dimDisabled ? Theme.disabledText : index === root.currentIndex || parent.hovered ? Theme.colors.text : Theme.colors.text2
                        elide: Text.ElideRight }
                    onClicked: { root.forceActiveFocus(Qt.MouseFocusReason); root.choose(index) }
                }
            }
        }
    }
}
