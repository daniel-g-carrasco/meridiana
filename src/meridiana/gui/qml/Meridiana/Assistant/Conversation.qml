import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: root
    property var backend: null
    property var texts: assistantText
    property bool docked: false
    // R647: the bubble's grip held (AssistantLayer.resizing): the messages in view take every width at once, the
    // others the last one at the release (each width lays a message out again: with ten long answers, all of them at
    // every point of the grip took the frame past the pointer)
    property bool held: false
    onHeldChanged: if (!held) messages.lay()
    readonly property bool low: !docked && height < 245
    readonly property bool hasCards: backend && backend.cards.length > 0
    signal attachmentRequested()
    signal dockRequested()
    signal closeRequested()
    signal menuRequested()
    signal typing()                 // a key typed in the question: Meridio listens (R619)
    function focusQuestion() { question.forceActiveFocus(Qt.ShortcutFocusReason) }
    spacing: Theme.space.S
    component HeaderButton: M.Button {
        flat: true
        implicitHeight: Theme.size.CHIP
        implicitWidth: Math.max(24, contentItem.implicitWidth+8)
        leftPadding: 4; rightPadding: 4; topPadding: 2; bottomPadding: 2
        font.weight: Font.Normal
    }
    RowLayout {
        Layout.fillWidth: true
        Character { width: 28; height: 28; visible: root.docked; awake: true }
        Item { Layout.fillWidth: true }
        HeaderButton {
            objectName: "assistantProvider"
            flat: true
            text: root.width >= 278 ? (root.backend ? root.backend.providerLabel : root.texts.local) : ""
            menuArrow: root.width >= 278
            iconName: root.backend && root.backend.destination !== "local" ? "cloud" : "house"
            tip: root.backend ? root.backend.status : root.texts.local
            onClicked: providers.open()
            M.Menu {
                id: providers
                Repeater {
                    model: root.backend ? root.backend.providerOptions : []
                    M.MenuItem {
                        required property var modelData
                        text: modelData.text || modelData.label || modelData.name || modelData.id
                        checkable: true
                        checked: modelData.checked || false
                        enabled: modelData.enabled !== false
                        onTriggered: modelData.model ? root.backend.chooseModel(modelData.id, modelData.model) : root.backend.chooseProvider(modelData.id)
                    }
                }
                M.MenuItem { text: root.backend ? root.backend.setupLabel : root.texts.setup; onTriggered: root.backend.showSetup() }
                M.MenuItem { text: root.texts.reserved; checkable: true; checked: root.backend ? root.backend.reserved : false; onTriggered: root.backend.setReserved(!root.backend.reserved) }
                M.MenuItem { text: root.texts.withdraw; onTriggered: root.backend.withdrawConsent() }
                M.MenuItem { text: root.texts.preferences; onTriggered: root.backend.requestPreferences() }
            }
        }
        HeaderButton {
            objectName: "assistantVoice"
            flat: true
            iconName: root.backend && root.backend.voiceEnabled ? "volume-2" : "volume-x"; tip: root.texts.voice
            checkable: true
            checked: root.backend ? root.backend.voiceEnabled : false
            enabled: root.backend ? root.backend.voiceAvailable : false
            onClicked: if (root.backend) root.backend.toggleVoice()
        }
        HeaderButton { objectName: "assistantMore"; visible: root.low; iconName: "ellipsis"; tip: root.texts.attach; onClicked: root.menuRequested() }
        HeaderButton { objectName: "assistantDock"; iconName: "dock"; tip: root.docked ? root.texts.floating : root.texts.dock; onClicked: root.dockRequested() }
        HeaderButton { objectName: "assistantClose"; text: "–"; tip: root.texts.back; onClicked: root.closeRequested() }
    }
    RowLayout {
        Layout.fillWidth: true; Layout.preferredHeight: Theme.size.BUBBLE_STATUS
        M.Label { text: root.backend ? root.backend.contextLine : ""; textStyle: "caption" }
        M.Label { text: root.backend ? root.backend.costLine : ""; textStyle: "caption"; Layout.fillWidth: true; elide: Text.ElideRight; horizontalAlignment: Text.AlignRight }
    }
    Item {
        Layout.fillWidth: true; Layout.fillHeight: true
        Layout.minimumHeight: 24
        Rectangle { anchors.fill: parent; color: Theme.colors.view; radius: 6; border.color: Theme.colors.line }
    M.ScrollPage {
        id: conversationScroll
        objectName: "conversationScroll"
        // R489 (Daniel 07/11/2026: «il taglio bianco arriva molto prima e in modo netto. Deve essere graduale fino
        // alla fine»): the view reaches the box's border above and below (1 px inside it), the air is inside what
        // scrolls, so the text fades out right up to the border instead of vanishing 7 px before it.
        anchors.fill: parent; anchors.margins: 1
        leftMargin: 6; rightMargin: 6; air: 7; airInside: true; spacing: 0
        ground: Theme.colors.view
        bar.objectName: "assistantScrollBar"
        bar.y: 6; bar.height: height - 12
        property bool follow: true
        function followEnd() {
            if (follow) Qt.callLater(function() {
                if (conversationScroll.follow)
                    conversationScroll.contentY = Math.max(0, conversationScroll.contentHeight - conversationScroll.availableHeight)
            })
        }
        onAvailableHeightChanged: followEnd()
        Column {
            id: messages
            width: conversationScroll.availableWidth
            spacing: Theme.space.S
            onHeightChanged: conversationScroll.followEnd()
            onWidthChanged: lay()
            function lay() {
                const top = conversationScroll.contentY, bottom = top + conversationScroll.height
                for (let i = 0; i < children.length; i++) {
                    const m = children[i]
                    if (m.laid === undefined) continue
                    if (!root.held || (m.y + m.height >= top && m.y <= bottom)) m.laid = width
                }
            }
            M.Label {
                width: parent.width
                visible: !root.backend || root.backend.displayMessages.length === 0
                text: root.backend ? root.backend.greeting : root.texts.preview
                color: Theme.colors.muted; wrapMode: Text.Wrap
                leftPadding: 4; rightPadding: 4
            }
            Repeater {
                id: shownMessages
                model: root.backend ? root.backend.displayMessages : []
                Column {
                    required property var modelData
                    property real laid: 0                       // set by messages.lay(), never bound
                    Component.onCompleted: laid = messages.width
                    width: laid
                    Image {
                        source: parent.modelData.imageSource || ""
                        visible: source.toString().length > 0
                        width: parent.width; height: visible ? Math.min(180, implicitHeight) : 0
                        fillMode: Image.PreserveAspectFit
                    }
                    // R489 (Daniel 06/11/2026: «lo sfondo delle porzioni di testo inviate da me» in grey blocks line by line):
                    // one's own message is one rounded bubble around all its text, with margins inside
                    Item {
                        visible: !!parent.modelData.outgoing && parent.modelData.kind === "you"
                        width: parent.width; height: visible ? mine.height : 0
                        Rectangle {
                            id: mine; objectName: "ownMessage"
                            width: Math.round(parent.width * .78); x: parent.width - width
                            height: mineText.implicitHeight + 2 * Theme.space.S
                            radius: Theme.radius.CARD; color: Theme.colors.field
                            border.width: Theme.line.HAIR; border.color: Theme.colors.line
                            M.ReadableText {
                                id: mineText
                                textActions.wholeLabel: textEditing.labels.message
                                Accessible.name: parent.parent.parent.modelData.author || ""
                                x: Theme.space.M; y: Theme.space.S; width: parent.width - 2 * Theme.space.M
                                text: parent.parent.visible ? '<style>b, strong {font-weight:600}</style>' + root.backend.messageInner(parent.parent.parent.modelData, Theme.colors) : ""
                                textFormat: TextEdit.RichText
                                readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                                font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
                                color: Theme.colors.text
                            }
                        }
                    }
                    M.ReadableText {
                        objectName: "conversationMessage"
                        dragSelects: true
                        markdownSource: parent.modelData.kind === "assistant" || parent.modelData.kind === "info" ? parent.modelData.text || "" : ""
                        textActions.wholeLabel: textEditing.labels.message
                        textActions.wholeText: textEditing.plainHtml(parent.modelData.bodyHtml || "")
                        visible: !(parent.modelData.outgoing && parent.modelData.kind === "you")
                        height: visible ? implicitHeight : 0
                        // R667: his answers carry no name over them; who speaks is said to screen readers
                        Accessible.name: parent.modelData.author || ""
                        width: parent.width
                        textMargin: 4
                        text: visible ? '<style>b, strong {font-weight:600}</style>' + root.backend.messageBlock(parent.modelData, Theme.colors) : ""
                        textFormat: TextEdit.RichText
                        readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                        font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
                        color: Theme.colors.text
                    }
                }
            }

            // R667: where the answer will come, until its first words: what he is doing (WaitingLine.qml)
            WaitingLine {
                objectName: "assistantWaiting"
                width: messages.width
                text: root.backend ? root.backend.waitingText : ""
                shown: !!root.backend && root.backend.state === "thinking"
                answered: !!root.backend && root.backend.state === "answering"
                lineHeight: oneLine.implicitHeight
                lineLeft: oneLine.first.x
                lineTop: oneLine.first.y
            }
        }
        Connections {
            target: conversationScroll.contentItem
            function onMovementStarted() { conversationScroll.follow = false }
            function onMovementEnded() {
                conversationScroll.follow = conversationScroll.contentY >= conversationScroll.contentHeight - conversationScroll.availableHeight - 24
            }
        }
    }
    }
    M.ScrollPage {
        id: cardsScroll
        objectName: "assistantCards"
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(implicitHeight, Math.max(56, root.docked ? root.height*0.48 : root.height-150))
        Layout.maximumHeight: Layout.preferredHeight
        visible: root.hasCards
        leftMargin: 0; air: 0
        Column {
            id: cardsColumn
            width: cardsScroll.availableWidth
            spacing: Theme.space.S
            Repeater {
                model: root.backend ? root.backend.cards : []
                M.Section {
                    id: cardItem
                    required property var modelData
                    width: cardsColumn.width
                    title: modelData.title
                    Column {
                        id: cardColumn
                        width: parent.width
                        spacing: Theme.space.S
                        Image {
                            source: modelData.thumbnail || ""
                            visible: source.toString().length > 0
                            width: Math.min(parent.width, implicitWidth); height: visible ? implicitHeight : 0
                            fillMode: Image.PreserveAspectFit
                        }
                        M.ReadableText {
                            text: "<p>" + (modelData.lines || []).join("</p><p>") + "</p>"; textFormat: TextEdit.RichText
                            width: parent.width; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                            color: Theme.colors.text; font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
                        }
                        Flow {
                            width: parent.width; spacing: Theme.space.XS
                            Repeater {
                                model: modelData.buttons || []
                                M.Button {
                                    required property var modelData
                                    objectName: "assistantCardButton:" + (modelData.id || modelData.key)
                                    text: modelData.text
                                    enabled: modelData.enabled !== false
                                    onClicked: root.backend.cardAction(cardItem.modelData.id, modelData.id || modelData.key)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    RowLayout {
        visible: !root.low
        Layout.fillWidth: true
        M.Button { objectName: "assistantAttach"; text: root.texts.attachShort; tip: root.texts.attach; Layout.fillWidth: true; enabled: !!root.backend; onClicked: files.open() }
        M.Button { objectName: "assistantShowView"; flat: true; iconName: "image"; tip: root.texts.view; enabled: root.backend ? root.backend.canShowView : false; onClicked: root.backend.showView() }
    }
    // R636 (Daniel 15/11/2026: «darei la possibilità alla casella di input di testo di meridio di accettare anche il
    // multiriga se gli si sta scrivendo un messaggio più lungo»): the common field that grows with its text
    // (M.GrowingField), up to its lines and never past a third of the conversation; Return sends, Shift+Return breaks
    // the line; the send button stays on its last line
    M.GrowingField {
        id: question
        objectName: "assistantQuestion"
        Layout.fillWidth: true
        rightRoom: M.ControlMetrics.questionRoom
        maxHeight: Math.floor(root.height / 3)
        placeholderText: root.backend && root.backend.preparationText ? root.backend.preparationText : root.texts.questionPlaceholder
        onActiveFocusChanged: { if (activeFocus && root.backend) root.backend.prepareLocal() }
        text: root.backend ? root.backend.draft : ""
        onTextEdited: { if (root.backend) root.backend.setDraft(text); root.typing() }
        textActions.pasteHandler: () => !!root.backend && root.backend.pasteClipboard()
        textActions.canPasteOverride: textEditing.canPaste
        onAccepted: submit()
        // the wheel over the field scrolls its text when it has some to scroll (its own Flickable takes it), else the
        // conversation above it
        WheelHandler {
            enabled: !question.scrolls
            onWheel: event => {
                const f = conversationScroll.flickable
                const step = event.pixelDelta.y !== 0 ? event.pixelDelta.y
                    : event.angleDelta.y / 120 * Qt.styleHints.wheelScrollLines * question.lineHeight
                f.contentY = Math.max(0, Math.min(f.contentHeight - f.height, f.contentY - step))
                conversationScroll.follow = f.contentY >= f.contentHeight - f.height - 24
            }
        }
        // nothing of spaces and empty lines alone is sent
        function submit() { if (root.backend && !root.backend.busy && text.trim()) { root.backend.ask(text); text = "" } }
        M.Button {
            objectName: "assistantSend"
            anchors.right: parent.right; anchors.bottom: parent.bottom
            width: 28; height: question.oneLine; flat: true
            iconName: root.backend && root.backend.busy ? "square" : "arrow-up"
            tip: root.backend && root.backend.busy ? root.texts.stopAnswer : root.texts.sendMessage
            enabled: !!root.backend
            onClicked: root.backend.busy ? root.backend.stop() : question.submit()
        }
    }
    // R667: an answer of one line, never shown: the waiting line is as tall as it and its words where its words are
    TextEdit {
        id: oneLine
        visible: false
        width: messages.width; textMargin: 4
        textFormat: TextEdit.RichText; wrapMode: TextEdit.Wrap
        font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
        text: root.backend ? '<style>b, strong {font-weight:600}</style>' + root.backend.messageBlock(
            {kind: "assistant", author: "", bodyHtml: "<p>M</p>", outgoing: false}, Theme.colors) : ""
        // 0 is the table's place, 1 its first letter; read again when the text is laid out again
        readonly property rect first: implicitHeight > 0 && width > 0 ? positionToRectangle(1) : Qt.rect(0, 0, 0, 0)
    }
    FileDialog {
        id: files
        title: root.texts.attach
        fileMode: FileDialog.OpenFiles
        onAccepted: if (root.backend) root.backend.addAttachments(selectedFiles.map(url => url.toString()))
    }
    DropArea {
        // A sibling of the layout: an overlay must not add a trailing layout gap.
        parent: root.parent
        x: root.x; y: root.y
        width: root.width; height: root.height
        onDropped: drop => { if (root.backend && drop.hasUrls) root.backend.addAttachments(drop.urls.map(url => url.toString())) }
    }
    Connections {
        target: root.backend
        function onAttachmentsRequested() { files.open() }
        function onPreviewChanged() { if (root.backend.preview.title) preview.open(); else preview.close() }
    }
    // R21-F2: the preview of an attachment is a window (M.Dialog): the title in its header, «Close» in its bar
    M.Dialog {
        id: preview
        // R628: Meridio's own window, over his stage (the other windows stand under him)
        z: Theme.stack.ASSISTANT_WINDOW
        implicitHeight: M.ControlMetrics.dialogWidth.wide
        bodyScrolls: false
        title: root.backend ? (root.backend.preview.title || "") : ""
        rejectText: root.texts.close
        onClosed: if (root.backend) root.backend.closePreview()
        ColumnLayout {
            Image {
                Layout.fillWidth: true; Layout.fillHeight: true
                source: root.backend ? (root.backend.preview.imageSource || "") : ""
                visible: source.toString().length > 0; fillMode: Image.PreserveAspectFit
            }
            M.ScrollPage {
                Layout.fillWidth: true; Layout.fillHeight: true
                M.TextArea { bare: true; width: parent.width; readOnly: true
                    text: root.backend ? (root.backend.preview.text || "") : "" }
            }
        }
    }
}
