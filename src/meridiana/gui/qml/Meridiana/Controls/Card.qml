import QtQuick
import Meridiana.Theme
Rectangle {
    id: root
    property string title: ""
    // R528: false when something under the head says the title already (the tabs of the cards in a group)
    property bool titleShown: true
    property bool closable: false
    property string closeTip: ""
    property alias headerExtra: extras.data
    // R597, R564: the «?» of the card stands where a section's does, at the right end of its head (before the cross):
    // one place for every «?» of a head. `helpKey` is what it explains, `helpShown` whether the card has one now.
    property string helpKey: ""
    property bool helpShown: helpKey !== ""
    property string helpName: "cardHelp"
    readonly property Item helpAnchor: help
    // R632: the head's row left of the «?» and the cross, where the title stands: a band laid there (the docked cards'
    // tabs, Shell/DockPanel.qml) takes the title's place, and the row is as tall as the taller of the two
    readonly property Item headRow: extras
    default property alias content: body.data
    property alias contentItem: body
    // The frame can animate independently from a layout prepared at its destination size.
    property real layoutWidth: width
    property real layoutHeight: height
    readonly property Item faceItem: face
    Item { id: face; parent: root; z: 2; width: root.layoutWidth; height: root.layoutHeight }
    signal closed()
    // R518: inside an M.Dialog the window is the frame: no ground, no line, no title (the window's), no margins
    property bool bare: false
    color: bare ? "transparent" : Theme.colors.panel
    radius: Theme.radius.CARD
    border.color: Theme.colors.card_line
    border.width: bare ? 0 : Theme.line.HAIR
    readonly property real titleHeight: Math.ceil(Theme.measureText(title, "title").height)
    implicitHeight: bare ? body.childrenRect.height : heading.y + heading.height + body.childrenRect.height + Theme.layout.PAD + 5
    implicitWidth: Theme.size.READING
    // over the hit area a panel lays on its title to carry it (DockPanel's TitleDrag): what takes a click in the head
    // (the «?» beside the title, the cross) takes it, the title's text lets it through
    // R632: a band taller than the title (the docked cards' tabs) keeps the row's middle where the title's is, so the
    // tabs stand as high as the Checks' own segments in their head (ChecksPage, toolsRow)
    Item { id: heading; parent: face; x: Theme.layout.TITLE_X; y: 9-Math.ceil(Math.max(0, height-root.titleHeight)/2); width: parent.width-2*x; z: 2
        visible: !root.bare
        height: !root.bare && (root.title || root.closable || extras.children.length > 1) ? Math.max(root.titleHeight, extras.implicitHeight) : 0
        Flow { id: extras; width: Math.max(0, parent.width-(root.closable ? close.width+Theme.space.S-4 : 0)
                                           -(help.visible ? help.width+Theme.space.M : 0)); spacing: Theme.space.M
            Label { text: root.title; textStyle: "title"; color: Theme.colors.text; width: Math.min(implicitWidth, extras.width)
                height: root.titleHeight; elide: Text.ElideRight; visible: text !== "" && root.titleShown }
        }
        HelpMark { id: help; objectName: root.helpName; visible: !root.bare && root.helpShown
            x: Math.round((root.closable ? close.x-Theme.space.S : parent.width)-width); y: Math.round((parent.height-height)/2)
            helpKey: root.helpKey; helpPlace: "card" }
        // R632: in the middle of the row (its title's, or the taller band laid in it)
        Button { id: close; objectName: "cardClose"; x: parent.width-width+4; y: (parent.height-height)/2
            visible: root.closable; width: 20; height: 20; padding: 0; flat: true; focusPolicy: Qt.NoFocus
            tip: root.closeTip; Accessible.name: root.closeTip
            contentItem: Icon { name: "control:close"; color: Theme.colors.muted }
            background: Rectangle { radius: Theme.radius.INNER; color: close.hovered ? Theme.colors.hover : "transparent" }
            onClicked: root.closed() }
    }
    // Room between the heading and the body for a band of the user's own (R528: the docked cards' tabs).
    property real bodyTop: 0
    // R637: the same margin between the card's border and its body on the four sides, at the top from the head's row
    // (Shell/DockPanel.qml: ControlMetrics.cardMargin); unset (-1), the card's own padding (Theme.layout.PAD)
    property real bodyMargin: -1
    // While an edge of the workspace is dragged the body keeps the size it had (Shell/DockPanel.qml, held): the card
    // follows the pointer and clips it, and what it holds is laid out again once, at the release. Unset (-1), the body
    // follows the card.
    property real bodyWidth: -1
    property real bodyHeight: -1
    readonly property real _side: root.bare ? 0 : bodyMargin >= 0 ? bodyMargin : Theme.layout.PAD
    Item { id: body; parent: face; x: root._side
        // R704: at the sides and the foot the margin holds the card's line too; under the head's row there is no line,
        // so the margin less that line: the same air on the four sides
        y: (root.bare ? 0 : heading.height ? heading.y+heading.height+(root.bodyMargin >= 0 ? root.bodyMargin - root.border.width : 5) : root._side) + root.bodyTop
        width: root.bodyWidth >= 0 ? root.bodyWidth : Math.max(0, parent.width-2*x)
        height: root.bodyHeight >= 0 ? root.bodyHeight : Math.max(0, parent.height-y-root._side) }
}
