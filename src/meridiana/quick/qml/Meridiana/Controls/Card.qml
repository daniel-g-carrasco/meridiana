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
    default property alias content: body.data
    property alias contentItem: body
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
    Item { id: heading; x: Theme.layout.TITLE_X; y: 9; width: parent.width-2*x
        visible: !root.bare
        height: !root.bare && (root.title || root.closable || extras.children.length > 1) ? Math.max(root.titleHeight, extras.implicitHeight) : 0
        Flow { id: extras; width: Math.max(0, parent.width-(root.closable ? close.width+Theme.space.S-4 : 0)); spacing: Theme.space.M
            Label { text: root.title; textStyle: "title"; color: Theme.colors.text; width: Math.min(implicitWidth, extras.width)
                height: root.titleHeight; elide: Text.ElideRight; visible: text !== "" && root.titleShown }
        }
        Button { id: close; x: parent.width-width+4; y: (root.titleHeight-height)/2
            visible: root.closable; width: 20; height: 20; padding: 0; flat: true; focusPolicy: Qt.NoFocus
            tip: root.closeTip; Accessible.name: root.closeTip
            contentItem: Icon { name: "control:close"; color: Theme.colors.muted }
            background: Rectangle { radius: Theme.radius.INNER; color: close.hovered ? Theme.colors.hover : "transparent" }
            onClicked: root.closed() }
    }
    // Room between the heading and the body for a band of the user's own (R528: the docked cards' tabs).
    property real bodyTop: 0
    Item { id: body; x: root.bare ? 0 : Theme.layout.PAD
        y: (root.bare ? 0 : heading.height ? heading.y+heading.height+5 : Theme.layout.PAD) + root.bodyTop
        width: Math.max(0, parent.width-2*x); height: Math.max(0, parent.height-y-(root.bare ? 0 : Theme.layout.PAD)) }
}
