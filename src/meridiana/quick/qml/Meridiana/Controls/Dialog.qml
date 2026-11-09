import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.Dialog {
    id: root
    property string acceptText: ""
    property string rejectText: ""
    property bool acceptOnReturn: true
    readonly property bool hasButtons: rejectText !== "" || acceptText !== "" || actions.length > 0
    function contentHasFocus(item) {
        if (item.activeFocus) return true
        for (let child of item.children) if (contentHasFocus(child)) return true
        return false
    }
    onOpened: if (!contentHasFocus(contentItem) && acceptButton.visible) acceptButton.forceActiveFocus(Qt.TabFocusReason)
    Shortcut { sequences: ["Return", "Enter"]; enabled: root.opened && root.enabled && root.acceptOnReturn && acceptButton.visible && root.acceptEnabled
        onActivated: rejectButton.activeFocus ? root.reject() : root.tryAccept() }
    property bool acceptEnabled: true
    // R518: the window's other actions (copy the table, new product, remove the storage) stand on the same row of
    // buttons, at its left, in this order: [{text, enabled}]; the window stays open. One row of buttons per window.
    property var actions: []
    signal actionTriggered(int index)
    // a window that closes only when what it was given is good: false keeps it open (the value of a field)
    property var acceptCheck: null
    function tryAccept() { if (!acceptCheck || acceptCheck()) accept() }
    // R403, R518: one window for the whole program, with the metrics of ControlMetrics and no margins of its own in the
    // windows that use it: the same margin on the four sides (dialogPad), the title on the top one, the buttons on the
    // bottom and right ones, dialogGap between the title and the content and between the content and the buttons. A
    // content that draws a frame of its own (a Card) is told to leave it (bare): the window's frame is the only one
    // (R458 voce 10, «come mai la finestra ha doppi bordi?»), its margins the only ones.
    implicitWidth: ControlMetrics.dialogWidth.normal
    implicitHeight: (root.title !== "" ? implicitHeaderHeight : 0) + implicitContentHeight + (root.hasButtons ? implicitFooterHeight : 0) + topPadding + bottomPadding
    readonly property bool contentFramed: false
    readonly property real frameWidth: Theme.line.HAIR
    function bareContent() { if (contentItem && contentItem.bare !== undefined) contentItem.bare = true }
    onContentItemChanged: bareContent()
    Component.onCompleted: bareContent()
    leftPadding: ControlMetrics.dialogPad
    rightPadding: ControlMetrics.dialogPad
    topPadding: root.title !== "" ? ControlMetrics.dialogGap : ControlMetrics.dialogPad
    bottomPadding: root.hasButtons ? ControlMetrics.dialogGap : ControlMetrics.dialogPad
    modal: true
    popupType: T.Popup.Item
    focus: true
    closePolicy: T.Popup.CloseOnEscape
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    header: Label { objectName: "dialogTitle"; text: root.title; textStyle: "heading"; elide: Text.ElideRight
        leftPadding: ControlMetrics.dialogPad; rightPadding: ControlMetrics.dialogPad; topPadding: ControlMetrics.dialogPad; visible: text !== "" }
    footer: Item { visible: root.hasButtons; implicitHeight: actions.implicitHeight + ControlMetrics.dialogPad
        Row { objectName: "dialogActions"; x: ControlMetrics.dialogPad; y: 0; spacing: ControlMetrics.dialogButtonGap
            Repeater { model: root.actions
                Button { required property var modelData; required property int index
                    text: modelData.text; enabled: modelData.enabled !== false; visible: modelData.visible !== false
                    onClicked: root.actionTriggered(index) } } }
        Row { id: actions; objectName: "dialogButtons"; anchors.right: parent.right; anchors.rightMargin: ControlMetrics.dialogPad; anchors.top: parent.top; spacing: ControlMetrics.dialogButtonGap
            layoutDirection: Qt.platform.os === "windows" ? Qt.RightToLeft : Qt.LeftToRight
            Button { id: rejectButton; objectName: "dialogReject"; text: root.rejectText; visible: text !== ""; onClicked: root.reject() }
            Button { id: acceptButton; objectName: "dialogAccept"; text: root.acceptText; visible: text !== ""; enabled: root.acceptEnabled; onClicked: root.tryAccept() }
        }
    }
    background: Rectangle { objectName: "dialogFrame"; color: Theme.colors.window; radius: Theme.radius.CARD
        border.color: Theme.colors.line; border.width: root.frameWidth }
    T.Overlay.modal: Rectangle { color: Theme.colors.press }
}
