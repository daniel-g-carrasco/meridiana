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
    property bool expanded: true
    readonly property bool low: !docked && height < 245
    readonly property bool hasCards: backend && backend.cards.length > 0
    signal attachmentRequested()
    signal dockRequested()
    signal closeRequested()
    signal menuRequested()
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
        Character { width: 28; height: 28; visible: root.docked; awake: true; where: "" }
        Item { Layout.fillWidth: true }
        HeaderButton {
            objectName: "assistantProvider"
            flat: true
            text: root.width >= 278 ? (root.backend ? root.backend.providerLabel : root.texts.local) : ""
            endIconName: root.width >= 278 ? "control:chevron-down" : ""
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
        Item {
            Layout.preferredWidth: 40; Layout.preferredHeight: 14
            property int step: 0
            Timer { interval: 300; running: root.backend && root.backend.state === "thinking" && !Theme.reducedMotion; repeat: true; onTriggered: parent.step = (parent.step+1)%3 }
            Repeater {
                model: 3
                Rectangle {
                    required property int index
                    visible: root.backend && root.backend.state === "thinking"
                    x: 7+index*10; y: 4-(index === parent.step && !Theme.reducedMotion ? 3 : 0)
                    width: 6; height: 6; radius: 3
                    color: index === parent.step ? Theme.colors.text : Theme.colors.muted
                }
            }
        }
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
            M.Label {
                width: parent.width
                visible: !root.backend || root.backend.displayMessages.length === 0
                text: root.backend ? root.backend.greeting : root.texts.preview
                color: Theme.colors.muted; wrapMode: Text.Wrap
                leftPadding: 4; rightPadding: 4
            }
            Repeater {
                model: root.backend ? root.backend.displayMessages : []
                Column {
                    required property var modelData
                    width: messages.width
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
                            TextEdit {
                                id: mineText
                                x: Theme.space.M; y: Theme.space.S; width: parent.width - 2 * Theme.space.M
                                text: parent.parent.visible ? '<style>b, strong {font-weight:600}</style>' + root.backend.messageInner(parent.parent.parent.modelData, Theme.colors) : ""
                                textFormat: TextEdit.RichText
                                readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                                font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
                                color: Theme.colors.text
                            }
                        }
                    }
                    TextEdit {
                        visible: !(parent.modelData.outgoing && parent.modelData.kind === "you")
                        height: visible ? implicitHeight : 0
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
                        TextEdit {
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
    ColumnLayout {
        id: suggested
        Layout.fillWidth: true
        property real shownHeight: root.expanded ? Math.max(questions.implicitHeight + suggestionTitle.height, 174) : suggestionTitle.height
        Behavior on shownHeight { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.FAST; easing.type: Theme.motion.EASE } }
        Layout.preferredHeight: shownHeight
        Layout.maximumHeight: Layout.preferredHeight
        visible: !root.hasCards && root.height >= (root.docked ? 200 : 350)
        clip: true
        spacing: Theme.space.XXS
        M.Button {
            id: suggestionTitle
            objectName: "assistantSuggestions"
            text: root.texts.suggestionsTitle
            tip: root.texts.suggestionsTip
            onClicked: root.expanded = !root.expanded
            font.pixelSize: Theme.text.caption.size
            contentItem: Row { spacing: 2
                M.Icon { name: root.expanded ? "control:chevron-down" : "control:chevron-right"; width: 14; height: 14
                    anchors.verticalCenter: parent.verticalCenter }
                M.Label { text: suggestionTitle.text; textStyle: "caption"; anchors.verticalCenter: parent.verticalCenter } }
        }
        ColumnLayout {
            id: questions
            Layout.fillWidth: true; spacing: 2
            visible: suggested.shownHeight > suggestionTitle.height
            // Three buttons kept, their texts following the phase (06/11/2026): rebuilt at every phase before.
            readonly property var suggestionTexts: root.backend ? root.backend.suggestions : []
            Repeater {
                model: Math.max(3, questions.suggestionTexts.length)
                M.Button {
                    id: suggestedQuestion
                    required property int index
                    readonly property string modelData: questions.suggestionTexts[index] || ""
                    visible: index < questions.suggestionTexts.length
                    objectName: "assistantSuggestion" + (index + 1)
                    text: modelData; tip: modelData
                    Layout.fillWidth: true
                    enabled: root.backend ? root.backend.suggestionsEnabled : false
                    implicitHeight: Math.max(28, questionLabel.implicitHeight + topPadding + bottomPadding)
                    topPadding: 6; bottomPadding: 6
                    contentItem: RowLayout {
                        spacing: Theme.space.M
                        M.Label { text: suggestedQuestion.index+1; color: Theme.colors.muted; Layout.preferredWidth: 12 }
                        M.Label { id: questionLabel; text: suggestedQuestion.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        M.Icon { name: "control:chevron-right"; color: Theme.colors.muted; width: 14; height: 14 }
                    }
                    onClicked: root.backend.ask(modelData)
                }
            }
        }
        Item { Layout.fillHeight: true }
    }
    RowLayout {
        visible: !root.low
        Layout.fillWidth: true
        M.Button { objectName: "assistantAttach"; text: root.texts.attachShort; tip: root.texts.attach; Layout.fillWidth: true; enabled: !!root.backend; onClicked: files.open() }
        M.Button { objectName: "assistantShowView"; flat: true; iconName: "image"; tip: root.texts.view; enabled: root.backend ? root.backend.canShowView : false; onClicked: root.backend.showView() }
    }
    M.TextField {
        id: question
        objectName: "assistantQuestion"
        Layout.fillWidth: true
        rightPadding: M.ControlMetrics.questionRoom
        placeholderText: root.texts.questionPlaceholder
        text: root.backend ? root.backend.draft : ""
        onTextEdited: if (root.backend) root.backend.setDraft(text)
        Keys.onPressed: event => {
            if (event.matches(StandardKey.Paste) && root.backend && root.backend.pasteClipboard()) event.accepted = true
            if (root.backend && root.backend.suggestionsEnabled && suggested.visible && !text.trim()
                && event.text >= "1" && event.text <= "3") {
                const i = Number(event.text)-1
                if (i < root.backend.suggestions.length) { root.backend.ask(root.backend.suggestions[i]); event.accepted = true }
            }
        }
        onAccepted: submit()
        function submit() { if (root.backend && !root.backend.busy && text.trim()) { root.backend.ask(text); text = "" } }
        M.Button {
            objectName: "assistantSend"
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            width: 28; height: parent.height; flat: true
            iconName: root.backend && root.backend.busy ? "square" : "arrow-up"
            tip: root.backend && root.backend.busy ? root.texts.stopAnswer : root.texts.sendMessage
            enabled: !!root.backend
            onClicked: root.backend.busy ? root.backend.stop() : question.submit()
        }
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
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(M.ControlMetrics.dialogWidth.normal, parent.width - 2 * M.ControlMetrics.dialogEdge)
        height: Math.min(M.ControlMetrics.dialogWidth.wide, parent.height - 2 * M.ControlMetrics.dialogEdge)
        title: root.backend ? (root.backend.preview.title || "") : ""
        rejectText: root.texts.close
        onClosed: if (root.backend) root.backend.closePreview()
        contentItem: ColumnLayout {
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
