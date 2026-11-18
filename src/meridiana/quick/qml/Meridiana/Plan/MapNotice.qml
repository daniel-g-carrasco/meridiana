import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
import Meridiana.Controls as Controls

// R463: the background fell back on another source by itself (the national orthophoto did not answer: OpenStreetMap
// instead). Information, not an error: one line in the map's own dress (the veil and the light ink of the
// attribution, the scale and the compass), with Retry, Choose the background and a close. It sits above the plan's
// mouse areas, so its buttons take the clicks, below the view bar and left of the compass, so it covers no control.
// In a narrow plan the words are cut first (their tooltip says them whole), then «Choose the background» goes (the
// background's menu is in the view bar too); nothing of it ever passes its right limit.
Rectangle {
    id: root
    objectName: "mapNotice"
    property var maps: null                 // the MapController
    property string chooseText: ""
    property string closeText: ""
    property real rightLimit: parent ? parent.width : 0
    property string closedText: ""          // the message closed: it comes back only when another one comes
    signal chooseBackground()
    readonly property string message: maps ? maps.fallbackMessage : ""
    readonly property color ink: Theme.colors.overlay.ink
    readonly property real room: Math.max(0, rightLimit - x)
    readonly property real fixed: line.leftPadding + line.rightPadding + line.spacing + Theme.space.S
                                  + retry.implicitWidth + close.implicitWidth + 2 * actions.spacing
    readonly property bool roomForChoose: room >= fixed + choose.implicitWidth + actions.spacing + 6 * Theme.space.L
    visible: message !== "" && message !== closedText && room >= fixed
    width: Math.min(room, line.implicitWidth)
    height: Theme.size.CONTROL
    radius: Theme.radius.CONTROL
    color: Theme.colors.overlay.glass_soft
    clip: true
    HoverHandler { cursorShape: Qt.ArrowCursor }
    TapHandler {}                           // a click on the line goes to no tool of the plan under it

    component Action: T.AbstractButton {
        id: action
        property string iconName: ""
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        implicitHeight: root.height - 2 * Theme.space.XXS
        implicitWidth: iconName ? implicitHeight : word.implicitWidth + 2 * Theme.space.S
        Accessible.name: text
        contentItem: Item {
            Text { id: word; visible: !action.iconName; anchors.centerIn: parent; text: action.text
                font.family: Theme.fontFamily; font.pixelSize: Theme.text.secondary.size; font.weight: Font.DemiBold
                color: root.ink }
            Controls.Icon { visible: !!action.iconName; anchors.centerIn: parent; width: 14; height: 14
                name: action.iconName; color: root.ink; dimDisabled: false }
        }
        background: Rectangle { radius: Theme.radius.INNER
            color: action.down ? Theme.colors.overlay.press : action.hovered ? Theme.colors.overlay.hover : "transparent" }
    }

    Row {
        id: line
        anchors.verticalCenter: parent.verticalCenter
        leftPadding: Theme.space.M
        rightPadding: Theme.space.XXS
        spacing: Theme.space.XXS
        Text {
            id: words
            objectName: "mapNoticeText"
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(0, Math.min(implicitWidth, root.room - line.leftPadding - line.rightPadding
                                                       - actions.implicitWidth - line.spacing))
            text: root.message
            elide: Text.ElideRight
            font.family: Theme.fontFamily
            font.pixelSize: Theme.text.secondary.size
            color: root.ink
            HoverHandler { id: wordsHover }
            Controls.ToolTip { text: root.message; visible: wordsHover.hovered && words.truncated }
        }
        Row {
            id: actions
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.XXS
            Item { width: Theme.space.S; height: 1 }
            Action { id: retry; objectName: "mapNoticeRetry"; text: root.maps ? root.maps.retryText : ""
                onClicked: root.maps.retryBackground() }
            Action { id: choose; objectName: "mapNoticeChoose"; text: root.chooseText; visible: root.roomForChoose
                onClicked: root.chooseBackground() }
            Action { id: close; objectName: "mapNoticeClose"; iconName: "x"; text: root.closeText
                Controls.ToolTip { text: parent.text; visible: parent.hovered }
                onClicked: root.closedText = root.message }
        }
    }
}
