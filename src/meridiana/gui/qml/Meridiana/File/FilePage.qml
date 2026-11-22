import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Settings

Rectangle {
    id: root
    objectName: "filePage"
    required property var backend
    property var settingsBackend: null
    property var dialogsBackend: null
    property string displayedSection: backend.section
    readonly property bool settingsMode: displayedSection.indexOf("preferences") === 0
    // R630 (Daniel 15/11/2026: «il passaggio tra una pagina e l'altra di File e delle impostazioni è molto lento e
    // scattante»): every page of File and of the Settings is made once and kept; a change of section fades the page
    // that goes out while the one already made fades in, Theme.motion.NORMAL with a soft end, as File and the
    // window do. Before, the page that went out was photographed (grabToImage: a frame on the graphics card and its
    // reading back) and the new one was made from nothing in the middle of the click; in the Settings the click itself
    // made every binding of the page ask Python its fields again (0.3-3 s of the window's thread). The measures:
    // docs/quick/stato/r35-pagine-file.md.
    readonly property var settingsKeys: ["appearance", "navigation", "keyboard", "assistant", "report", "maps", "performance", "privacy"]
    readonly property var pageKeys: Object.keys(backend.sections)
        .concat(settingsBackend ? settingsKeys.map(k => "preferences:" + k) : [])
        .concat(dialogsBackend ? ["dialogs"] : [])
    readonly property string currentPage: displayedSection === "new" || displayedSection === "registry" ? "dialogs"
        : displayedSection === "preferences" ? "preferences:appearance" : displayedSection
    // the pages not shown made ahead, a slice at a time between the frames, once File has come in; not with Qt's
    // software renderer (off screen), whose frames are on this thread and where Qt's incubation does not go on:
    // there a page is made the first time it is asked and kept
    property bool ahead: false
    property var dialogsType: null      // DialogsPage.qml compiled ahead (entrance.onFinished)
    property bool still: false          // a change without its fade: File coming in, the page hidden
    property int moving: 0              // the pages fading now
    property real arrival: 1            // how far in the page asked for is (its opacity): the measures and the tests
    readonly property bool changing: moving > 0
    property real entranceOffset: 0
    readonly property rect freeSide: side.freeSide
    signal closed()
    color: Theme.colors.panel; radius: Theme.radius.CARD
    border.color: Theme.colors.line; border.width: Theme.line.HAIR
    clip: true; focus: true
    transform: Translate { x: root.entranceOffset }
    // R630: one rule for the title of a page, File's and the Settings': the name of its entry in the column on the
    // left (Open, Export, Appearance, Keyboard...), never the generic «Settings» over every section
    function titleOf(key) { return backend.words[key.replace("preferences:", "")] || "" }
    // the backends told first, the page shown after: this handler runs before Python's (QML hears a signal first),
    // and the page of New and Clients and jobs made with the dialogs' kind of before built the map of New (0.5 s)
    function applySection() {
        const section = backend.section
        if (section.indexOf("preferences") === 0 && settingsBackend) settingsBackend.showSection(section.split(":")[1] || "appearance")
        if ((section === "new" || section === "registry") && dialogsBackend) dialogsBackend.open(section)
        displayedSection = section
    }
    function applyStill() { still = true; applySection(); still = false }
    function recount() {            // the pages fading, counted again (a page made again leaves no count behind)
        let n = 0
        for (let i = 0; i < pages.count; ++i) { const page = pages.itemAt(i); if (page && page.fading) ++n }
        moving = n
    }
    function compileDialogs() {
        if (dialogsBackend && !dialogsType) dialogsType = Qt.createComponent("../Dialogs/DialogsPage.qml", Component.Asynchronous)
    }
    function showSection(key) { backend.selectSection(key) }
    function enter() {
        applyStill()
        entrance.restart(); forceActiveFocus()
    }
    Component.onCompleted: applyStill()
    Keys.onEscapePressed: root.closed()
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Left && (event.modifiers & Qt.AltModifier)) { backend.back(); event.accepted = true }
    }
    Connections {
        target: root.backend
        function onSectionChanged() {
            if (Theme.reducedMotion || !root.visible) root.applyStill()
            else root.applySection()
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
    ParallelAnimation {
        id: entrance
        // R471: a short way and a soft end (it came 24 px with an even fade)
        NumberAnimation { target: root; property: "entranceOffset"; from: Theme.space.M; to: 0; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
        NumberAnimation { target: root; property: "opacity"; from: 0; to: 1; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
        onFinished: {
            root.ahead = true
            // New and Clients and jobs are not made ahead (see the page «dialogs» below), but their file is read and
            // compiled now, on Qt's loading thread: the first visit only makes the page (it compiled it too)
            Qt.callLater(root.compileDialogs)        // a turn of its own, not with the pages started above
        }
    }
    Rectangle {
        id: navigation
        objectName: "fileNavigation"
        x: 1; y: 1 + Theme.space.S; width: Math.min(266, root.width * 0.34); height: parent.height - 2 - 2*Theme.space.S
        color: Theme.colors.panel
        M.ScrollPage {
            leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0
            id: navScroll
            anchors.fill: parent; anchors.leftMargin: Theme.space.M; anchors.rightMargin: Theme.space.XL + Theme.space.M - Theme.size.SCROLLBAR
            anchors.topMargin: Theme.space.L; anchors.bottomMargin: Theme.space.L
            // R630: the two columns, File's and the Settings', made once; going from one to the other shows the
            // other (before, its 10-14 buttons were made again at every passage, 35-50 ms)
            Repeater {
                model: [["back", "rule1", "new", "open", "save", "registry", "rule2", "export", "rule3", "catalogues", "preferences", "help", "stretch", "quit"],
                        ["back", "settingsBack", "appearance", "navigation", "keyboard", "assistant", "report", "maps", "performance", "privacy"]]
                delegate: Column {
                    id: navColumn; width: parent.width; spacing: Theme.space.XXS
                    required property var modelData
                    required property int index
                    readonly property bool settings: index === 1
                    readonly property bool shown: settings === root.settingsMode
                    visible: shown
                    Repeater {
                        model: navColumn.modelData
                        delegate: M.Button {
                            required property string modelData
                            property bool separator: modelData.startsWith("rule")
                            property bool spacer: modelData === "stretch"
                            property string keyHint: modelData === "back" ? "Esc" : modelData === "open" ? "Ctrl+O" : modelData === "new" ? "Ctrl+N" : modelData === "help" ? "F1" : ""
                            objectName: navColumn.shown ? "fileNav_" + modelData : ""
                            width: navColumn.width
                            height: separator ? 2 * Theme.space.S + 1 : spacer ? Math.max(0, navScroll.height - 10 * Theme.size.NAV - 3 * (2 * Theme.space.S + 1) - 13 * Theme.space.XXS) : Theme.size.NAV
                            enabled: !separator && !spacer
                            flat: true
                            text: root.backend.words[modelData] || modelData
                            iconName: ({back:"arrow-left", settingsBack:"arrow-left", new:"file-plus", open:"folder-open", save:"save", registry:"library", export:"upload", catalogues:"library", preferences:"settings", help:"circle-question-mark", quit:"log-out", appearance:"eye", navigation:"select", keyboard:"keyboard", assistant:"wand", report:"file-text", maps:"map", performance:"zap", privacy:"info"})[modelData] || ""
                            active: navColumn.settings ? root.displayedSection === "preferences:" + modelData : root.displayedSection === modelData
                            background: Rectangle {
                                visible: !parent.separator && !parent.spacer
                                radius: Theme.radius.CONTROL
                                color: parent.down ? Theme.colors.press : parent.hovered ? Theme.colors.hover : parent.active ? Theme.colors.select_bg : "transparent"
                                border.width: Theme.focusRing(parent) ? Theme.line.FOCUS : 0
                                border.color: Theme.colors.focus
                            }
                            contentItem: Item {
                                visible: !parent.separator && !parent.spacer
                                implicitHeight: Theme.icon.LIST
                                M.Icon { id: navIcon; name: parent.parent.iconName; width: Theme.icon.LIST; height: width; anchors.verticalCenter: parent.verticalCenter }
                                M.CopyLabel { anchors.left: navIcon.right; anchors.leftMargin: Theme.space.M + Theme.space.XXS; anchors.verticalCenter: parent.verticalCenter; text: parent.parent.text }
                                M.CopyLabel { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: parent.parent.keyHint; textStyle: "secondary" }
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
                                else root.showSection(modelData === "settingsBack" ? "open" : navColumn.settings ? "preferences:" + modelData : modelData === "preferences" ? "preferences:appearance" : modelData)
                            }
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
        id: side
        objectName: "fileRight"
        // Daniel 15/11/2026 («spostalo, tienilo sul fianco libero»): what is right of the page, its column and its
        // margins (New and Clients and jobs draw in their right margin too), the same edge for every page of File and
        // of the Settings: Meridio's place while File is open (Assistant/AssistantHost.qml, fileSide). In a narrow
        // window («ci sta che la colonna gli ceda quei 42px, ma porre dei limiti»), the column gives him the room he
        // lacks there (his figure, his margin from the card's edge and as much from the page), as long as it stays as wide as
        // ControlMetrics.pageLeast; below that it gives no more, and he may stand over its edge.
        readonly property real pageX: root.backend.metrics.pageX
        readonly property real column: width - 2 * pageX                       // the column with no limit
        readonly property real meridioRoom: M.ControlMetrics.figure + 2 * Theme.space.L
        readonly property real given: Math.max(0, Math.min(meridioRoom - (column - Math.min(Theme.layout.PAGE_WIDTH, column)),
                                                           column - M.ControlMetrics.pageLeast))
        // what the pages lay themselves out in (each with its margins): the side less what is given to Meridio
        readonly property real pagesWidth: width - given
        // R578: every page of File and of the Settings is at most Theme.layout.PAGE_WIDTH wide, after its margin
        readonly property real pageWidth: Math.min(Theme.layout.PAGE_WIDTH, pagesWidth - 2 * pageX)
        readonly property rect freeSide: Qt.rect(x + 2 * pageX + pageWidth, y, Math.max(0, width - 2 * pageX - pageWidth),
                                                 height)
        x: navigation.x + navigation.width; y: 1 + Theme.space.S
        width: parent.width - x - 1; height: parent.height - 2 - 2*Theme.space.S
        Repeater {
            id: pages
            model: root.pageKeys
            onItemRemoved: root.recount()
            delegate: Loader {
                id: kept
                required property string modelData
                readonly property bool current: root.currentPage === modelData
                readonly property bool settings: modelData.indexOf("preferences:") === 0
                property bool made: false       // asked once: kept from then on
                onCurrentChanged: { if (current) { made = true; root.arrival = opacity } }
                onOpacityChanged: if (current) root.arrival = opacity
                width: side.pagesWidth; height: side.height
                z: current ? 1 : 0
                opacity: current ? 1 : 0
                visible: opacity > 0
                // New and Clients and jobs show the dialogs' backend, which also draws the other windows: made while
                // shown (and while fading out), never kept nor made ahead
                active: modelData === "dialogs" ? current || opacity > 0
                    : made || current || (root.ahead && GraphicsInfo.api !== GraphicsInfo.Software)
                asynchronous: !current && GraphicsInfo.api !== GraphicsInfo.Software
                sourceComponent: modelData === "dialogs" ? dialogsPage : settings ? settingsPage : fileSection
                Component.onCompleted: if (current) { made = true; root.arrival = 1 }
                readonly property bool fading: fade.running
                onFadingChanged: root.recount()
                Behavior on opacity {
                    enabled: !root.still && !Theme.reducedMotion && root.visible
                    NumberAnimation { id: fade; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
                }
                Component {
                    id: fileSection
                    FileSection { backend: root.backend; section: kept.modelData; title: root.titleOf(kept.modelData) }
                }
                Component {
                    id: settingsPage
                    Item {
                        Column {
                            id: heading
                            objectName: kept.current ? "settingsHeading" : ""
                            x: root.backend.metrics.pageX; y: root.backend.metrics.pageY
                            width: side.pageWidth; spacing: 0
                            M.CopyLabel { objectName: kept.current ? "settingsTitle" : ""; text: root.titleOf(kept.modelData); textStyle: "display" }
                            M.ReadableText { width: parent.width; text: root.backend.words.settingsLead; textStyle: "description"; wrapMode: Text.WordWrap }
                        }
                        SettingsPage {
                            x: root.backend.metrics.pageX
                            y: heading.y + heading.height + Theme.space.XXL
                            width: side.pageWidth; height: parent.height - y - Theme.space.XXS
                            backend: root.settingsBackend
                            section: kept.modelData.replace("preferences:", "")
                            shown: kept.current
                        }
                    }
                }
                Component {
                    id: dialogsPage
                    Item {
                        Loader {
                            width: Math.min(parent.width, side.pageWidth + 2 * root.backend.metrics.pageX); height: parent.height
                            Component.onCompleted: setSource("../Dialogs/DialogsPage.qml", {backend: root.dialogsBackend})
                        }
                    }
                }
            }
        }
    }
    Rectangle {
        anchors.fill: parent; visible: root.backend.confirmation
        color: Theme.colors.card; radius: Theme.radius.CARD; z: 10
        MouseArea { anchors.fill: parent }
        Column {
            anchors.centerIn: parent; width: Math.min(parent.width - 2 * Theme.space.XXL, 500); spacing: Theme.space.L
            M.CopyLabel { text: root.backend.words.unsaved; textStyle: "heading" }
            M.ReadableText { text: root.backend.words.saveFirst; width: parent.width; wrapMode: Text.WordWrap }
            Row {
                spacing: Theme.space.M
                M.Button { objectName: "fileConfirmSave"; text: root.backend.words.saveChanges; onClicked: root.backend.resolveChanges("save") }
                M.Button { objectName: "fileConfirmDiscard"; text: root.backend.words.discard; onClicked: root.backend.resolveChanges("discard") }
                M.Button { objectName: "fileConfirmCancel"; text: root.backend.words.cancel; onClicked: root.backend.resolveChanges("cancel") }
            }
        }
    }
    M.ReadableText {
        anchors.left: side.left; anchors.right: parent.right; anchors.bottom: parent.bottom
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
