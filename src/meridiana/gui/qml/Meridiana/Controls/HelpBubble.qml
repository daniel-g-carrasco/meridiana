import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
// R597 (Daniel 13/11/2026, study 47, variant 3 without the title): the help of a «?», a bubble anchored to it. It is a
// Popup (the menus' frame, shadow and opening) with the pointer turned to its mark: the key's text, the source's line
// when there is one, and a foot under a hair line with «Open in the manual» (only once the manual can be opened:
// help_part.MANUAL_PAGE) and «Ask Meridio» (only while Meridio is on). Made and closed only by Help.qml (Help.show), one
// at a time; it closes with Esc, a click outside, a second click on its mark, the scroll of what holds the mark and the
// change of phase. Where it opens comes from its mark's `helpPlace` (Help.placeOf).
Popup {
    id: root
    objectName: "helpBubble"
    property var entry: ({})
    property string helpPlace: "panel"
    readonly property var placing: Help.placeOf(helpPlace, parent)
    readonly property bool manualShown: !!entry.manual
    readonly property bool askShown: typeof helpBook !== "undefined" && !!helpBook && helpBook.canAsk
    // what holds the mark and scrolls (Help.show): the bubble goes at the first scroll (a light dismiss)
    property var flicks: []
    property Instantiator follower: Instantiator {
        model: root.flicks
        delegate: Connections {
            required property var modelData
            target: modelData
            function onContentYChanged() { root.close() }
            function onContentXChanged() { root.close() }
        }
    }
    side: placing.side
    align: placing.align
    pointer: placing.pointer
    sideOf: placing.sideOf
    gap: Theme.space.XXS
    // Esc is the window's (Workbench: Help.close() first), so that the keyboard can stay in the field the help key asked from
    closePolicy: T.Popup.CloseOnPressOutsideParent
    padding: Theme.space.L
    bottomPadding: foot.visible ? 0 : Theme.space.L
    contentItem: Item {
        implicitWidth: ControlMetrics.helpBubble - root.leftPadding - root.rightPadding
        implicitHeight: column.implicitHeight
        Column {
            id: column
            width: parent.width
            spacing: Theme.space.S
            ReadableText { objectName: "helpBubbleText"; width: parent.width; text: root.entry.text || ""; dragSelects: true
                wrapMode: Text.Wrap }
            ReadableText { objectName: "helpBubbleSource"; width: parent.width; visible: text !== ""; text: root.entry.source || ""; dragSelects: true
                textStyle: "caption"; wrapMode: Text.Wrap }
            Item {
                id: foot
                objectName: "helpBubbleFoot"
                visible: root.manualShown || root.askShown
                // R650 (Daniel 15/11/2026: «questa riga in basso dei popup di help deve avere un pochino di spazio in più
                // così da dare all'hover di ask meridio un po' di margine sopra e sotto»): the buttons' hover stands
                // ControlMetrics.helpFoot from the line above, from the bubble's foot and from its left side
                width: parent.width; height: Theme.line.HAIR + ControlMetrics.helpFoot + actions.height + ControlMetrics.helpFoot
                Rectangle { x: -root.leftPadding; width: root.width; height: Theme.line.HAIR; color: Theme.colors.line_soft }
                Row {
                    id: actions
                    x: ControlMetrics.helpFoot - root.leftPadding
                    y: Theme.line.HAIR + ControlMetrics.helpFoot
                    ToolButton { objectName: "helpBubbleManual"; mode: "beside"; visible: root.manualShown
                        iconName: "book-open"; text: helpBook.labels.manual
                        onClicked: { helpBook.openManual(root.entry.manual); root.close() } }
                    ToolButton { objectName: "helpBubbleAsk"; mode: "beside"; visible: root.askShown
                        iconName: "message-circle"; text: helpBook.labels.ask
                        onClicked: { helpBook.ask(root.entry.key); root.close() } }
                }
            }
        }
    }
}
