import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    objectName: "filePage"
    required property var backend
    property var settingsBackend: null
    property var dialogsBackend: null
    property string displayedSection: backend.section
    property string pendingSection: backend.section
    readonly property bool settingsMode: displayedSection.indexOf("preferences") === 0
    property bool changing: fading.running || crossing.running
    property real entranceOffset: 0
    signal closed()
    color: Theme.colors.panel; radius: Theme.radius.CARD
    border.color: Theme.colors.line; border.width: Theme.line.HAIR
    clip: true; focus: true
    transform: Translate { x: root.entranceOffset }
    function applySection() {
        displayedSection = pendingSection
        if (settingsMode && settingsBackend) settingsBackend.showSection(displayedSection.split(":")[1] || "appearance")
        if ((displayedSection === "new" || displayedSection === "registry") && dialogsBackend) dialogsBackend.open(displayedSection)
    }
    function showSection(key) { backend.selectSection(key) }
    function enter() {
        crossing.stop(); leaving.source = ""; fading.running = false; right.opacity = 1
        pendingSection = backend.section; applySection()
        entrance.restart(); forceActiveFocus()
    }
    Component.onCompleted: applySection()
    Keys.onEscapePressed: root.closed()
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Left && (event.modifiers & Qt.AltModifier)) { backend.back(); event.accepted = true }
    }
    Connections {
        target: root.backend
        function onSectionChanged() {
            root.pendingSection = root.backend.section
            if (Theme.reducedMotion || !root.visible) { crossing.stop(); leaving.source = ""; root.applySection(); right.opacity = 1 }
            else if (!crossing.running && !fading.running) root.crossTo()
        }
        function onClosed() { root.closed() }
        function onFileDialogRequested(kind, title, start, filters) {
            nativePicker.active = true
            nativePicker.item.operation = kind
            nativePicker.item.title = title
            nativePicker.item.nameFilters = filters
            nativePicker.item.fileMode = kind === "save" ? FileDialog.SaveFile : FileDialog.OpenFile
            nativePicker.item.selectedFile = "file:///" + start.replace(/\\/g, "/")
            nativePicker.item.open()
        }
    }
    // R471, R378: a new section crosses the old one, nothing more: the old page kept as a still picture fades out
    // while the new one, already laid out under it, fades in, 180 ms with a soft end. Before, the page dipped to the
    // ground and back (90 + 90 ms) and was built in the middle of it: a frame stood still at the darkest point.
    function crossTo() {
        fading.running = true       // the turn of the picture: a second change waits for this one
        right.grabToImage(function(still) {
            fading.running = false
            leaving.source = still.url
            leaving.opacity = 1
            root.applySection()
            right.opacity = 0
            crossing.restart()
        })
    }
    Image {
        id: leaving
        objectName: "fileLeaving"
        x: right.x; y: right.y; width: right.width; height: right.height; z: 1
        visible: source.toString() !== ""
        opacity: 0
        smooth: false
    }
    ParallelAnimation {
        id: crossing
        NumberAnimation { target: leaving; property: "opacity"; to: 0; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
        NumberAnimation { target: right; property: "opacity"; to: 1; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
        onFinished: { leaving.source = ""; if (root.pendingSection !== root.displayedSection) root.crossTo() }
    }
    QtObject {
        id: fading
        property bool running: false
    }
    ParallelAnimation {
        id: entrance
        // R471: a short way and a soft end (it came 24 px with an even fade)
        NumberAnimation { target: root; property: "entranceOffset"; from: Theme.space.M; to: 0; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
        NumberAnimation { target: root; property: "opacity"; from: 0; to: 1; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
    }
    Rectangle {
        id: navigation
        objectName: "fileNavigation"
        x: 1; y: 1 + Theme.space.S; width: Math.min(266, root.width * 0.34); height: parent.height - 2 - 2*Theme.space.S
        color: Theme.colors.panel
        M.ScrollPage {
            leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0; groundAbove: true
            id: navScroll
            anchors.fill: parent; anchors.leftMargin: Theme.space.M; anchors.rightMargin: Theme.space.XL + Theme.space.M - Theme.size.SCROLLBAR
            anchors.topMargin: Theme.space.L; anchors.bottomMargin: Theme.space.L
            Column {
                id: navColumn; width: parent.width; spacing: Theme.space.XXS
                property var entries: root.settingsMode ? ["back", "settingsBack", "appearance", "navigation", "keyboard", "assistant", "report", "maps", "performance", "privacy"]
                    : ["back", "rule1", "new", "open", "save", "registry", "rule2", "export", "rule3", "catalogues", "preferences", "help", "stretch", "quit"]
                Repeater {
                    model: navColumn.entries
                    delegate: M.Button {
                        required property string modelData
                        property bool separator: modelData.startsWith("rule")
                        property bool spacer: modelData === "stretch"
                        property string keyHint: modelData === "back" ? "Esc" : modelData === "open" ? "Ctrl+O" : modelData === "new" ? "Ctrl+N" : modelData === "help" ? "F1" : ""
                        objectName: "fileNav_" + modelData
                        width: navColumn.width
                        height: separator ? 2 * Theme.space.S + 1 : spacer ? Math.max(0, navScroll.height - 10 * Theme.size.NAV - 3 * (2 * Theme.space.S + 1) - 13 * Theme.space.XXS) : Theme.size.NAV
                        enabled: !separator && !spacer
                        flat: true
                        text: root.backend.words[modelData] || modelData
                        iconName: ({back:"arrow-left", settingsBack:"arrow-left", new:"file-plus", open:"folder-open", save:"save", registry:"library", export:"upload", catalogues:"library", preferences:"settings", help:"circle-question-mark", quit:"log-out", appearance:"eye", navigation:"select", keyboard:"keyboard", assistant:"wand", report:"file-text", maps:"map", performance:"zap", privacy:"info"})[modelData] || ""
                        active: root.settingsMode ? root.displayedSection === "preferences:" + modelData : root.displayedSection === modelData
                        background: Rectangle {
                            visible: !parent.separator && !parent.spacer
                            radius: Theme.radius.CONTROL
                            color: parent.down ? Theme.colors.press : parent.hovered ? Theme.colors.hover : parent.active ? Theme.colors.select_bg : "transparent"
                            border.width: parent.visualFocus ? Theme.line.FOCUS : 0
                            border.color: Theme.colors.accent
                        }
                        contentItem: Item {
                            visible: !parent.separator && !parent.spacer
                            implicitHeight: Theme.icon.LIST
                            M.Icon { id: navIcon; name: parent.parent.iconName; width: Theme.icon.LIST; height: width; anchors.verticalCenter: parent.verticalCenter }
                            M.Label { anchors.left: navIcon.right; anchors.leftMargin: Theme.space.M + Theme.space.XXS; anchors.verticalCenter: parent.verticalCenter; text: parent.parent.text }
                            M.Label { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: parent.parent.keyHint; textStyle: "secondary" }
                        }
                        Rectangle {
                            visible: parent.separator
                            x: Theme.space.M; y: Theme.space.S
                            width: parent.width - 2 * Theme.space.M; height: 1
                            color: Theme.colors.line_soft
                        }
                        onClicked: {
                            if (modelData === "back") root.closed()
                            else if (modelData === "quit" || modelData === "new") root.backend.request(modelData)
                            else root.showSection(modelData === "settingsBack" ? "open" : root.settingsMode ? "preferences:" + modelData : modelData === "preferences" ? "preferences:appearance" : modelData)
                        }
                    }
                }
            }
        }
    }
    Rectangle {
        x: navigation.x + navigation.width - Theme.space.XL; y: 1 + Theme.space.S
        width: Theme.line.HAIR; height: parent.height - 2 - 2*Theme.space.S
        color: Theme.colors.line_soft
    }
    Item {
        id: right
        objectName: "fileRight"
        x: navigation.x + navigation.width; y: 1 + Theme.space.S
        width: parent.width - x - 1; height: parent.height - 2 - 2*Theme.space.S
        Loader {
            id: content
            x: root.settingsMode ? root.backend.metrics.pageX : 0
            y: root.settingsMode ? settingsHeading.y + settingsHeading.height + Theme.space.XXL : 0
            width: root.settingsMode ? Math.min(760, parent.width - 2*x) : parent.width
            height: parent.height - y - (root.settingsMode ? Theme.space.XXS : 0)
            property string requestedSource: root.settingsMode && root.settingsBackend ? "../Settings/SettingsPage.qml"
                : (root.displayedSection === "new" || root.displayedSection === "registry") && root.dialogsBackend ? "../Dialogs/DialogsPage.qml" : ""
            onRequestedSourceChanged: setSource(requestedSource, {backend: root.settingsMode ? root.settingsBackend : root.dialogsBackend})
            Component.onCompleted: setSource(requestedSource, {backend: root.settingsMode ? root.settingsBackend : root.dialogsBackend})
        }
        Column {
            id: settingsHeading
            visible: root.settingsMode
            x: root.backend.metrics.pageX; y: root.backend.metrics.pageY
            width: Math.min(760, parent.width - 2*x); spacing: 0
            M.Label { text: root.backend.words.preferences; textStyle: "display" }
            M.Label { width: parent.width; text: root.backend.words.settingsLead; textStyle: "description"; wrapMode: Text.WordWrap }
        }
        FileSection {
            anchors.fill: parent
            backend: root.backend; section: root.displayedSection
            visible: root.backend.sections[root.displayedSection] !== undefined
        }
    }
    Rectangle {
        anchors.fill: parent; visible: root.backend.confirmation
        color: Theme.colors.card; radius: Theme.radius.CARD; z: 10
        MouseArea { anchors.fill: parent }
        Column {
            anchors.centerIn: parent; width: Math.min(parent.width - 2 * Theme.space.XXL, 500); spacing: Theme.space.L
            M.Label { text: root.backend.words.unsaved; textStyle: "heading" }
            M.Label { text: root.backend.words.saveFirst; width: parent.width; wrapMode: Text.WordWrap }
            Row {
                spacing: Theme.space.M
                M.Button { objectName: "fileConfirmSave"; text: root.backend.words.saveChanges; onClicked: root.backend.resolveChanges("save") }
                M.Button { objectName: "fileConfirmDiscard"; text: root.backend.words.discard; onClicked: root.backend.resolveChanges("discard") }
                M.Button { objectName: "fileConfirmCancel"; text: root.backend.words.cancel; onClicked: root.backend.resolveChanges("cancel") }
            }
        }
    }
    M.Label {
        anchors.left: right.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.margins: Theme.space.M
        text: root.backend.error || root.backend.status; textStyle: "secondary"; wrapMode: Text.WordWrap
        visible: text !== ""
    }
    Loader {
        id: nativePicker; active: false
        sourceComponent: Component {
            FileDialog {
                property string operation: "open"
                onAccepted: root.backend.fileChosen(operation, selectedFile.toString())
                onRejected: root.backend.cancelFileDialog()
            }
        }
    }
}
