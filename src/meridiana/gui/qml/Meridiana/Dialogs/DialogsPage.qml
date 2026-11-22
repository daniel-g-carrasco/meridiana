import QtQuick
import QtQuick.Controls as C
import QtQuick.Layouts
import QtQuick.Dialogs as D
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    property var backend
    readonly property bool newProject: backend && backend.kind === "new"
    implicitWidth: M.ControlMetrics.pageSize.dialogs.width
    // the height the content asks: the window takes it when this kind of dialog has no size of its own
    // R586: the content of the window of File (DialogWindow, M.Dialog): its title, its margins and its buttons are the
    // window's
    implicitHeight: page.implicitHeight
    // R607: the window's «Choose the file…» (DialogWindow's row of buttons) opens the chooser of the page in hand
    function pickFile() { if (kindPage.item && kindPage.item.pickFile) kindPage.item.pickFile(); else importFile.open() }
    ColumnLayout {
        id: page
        anchors.fill: parent
        spacing: M.ControlMetrics.dialogGap
        M.ReadableText {
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.space.M
            visible: root.newProject
            text: root.backend ? root.backend.labels.newLead : ""
            textStyle: "description"; wrapMode: Text.WordWrap
        }
        ShortcutsPage {
            Layout.fillHeight: true
            Layout.fillWidth: true
            visible: root.backend && root.backend.kind === "shortcuts"
            backend: root.backend
        }
        Loader {
            id: kindPage
            Layout.fillHeight: true
            Layout.fillWidth: true
            visible: !root.backend || !["shortcuts", "about"].includes(root.backend.kind)
            sourceComponent: !root.backend ? null : root.backend.kind === "ifc" ? ifcPage : root.backend.kind === "update" ? update : ["new", "site"].includes(root.backend.kind) ? site : root.backend.kind === "report_bug" ? feedback : root.backend.kind === "registry" ? registry : root.backend.kind === "shortcuts" ? null : root.backend.kind === "about" ? null : generic
            Component { id: ifcPage; IfcImportPage { backend: root.backend } }
            Component {
                id: update
                ColumnLayout {
                    spacing: Theme.space.M
                    M.CopyLabel { text: root.backend.state.currentVersion || ""; Layout.fillWidth: true }
                    // R601: the notes whole in their box; the window's body scrolls them with the rest
                    Rectangle {
                        visible: !!root.backend.state.releaseNotes
                        Layout.preferredHeight: notes.implicitHeight + 2 * Theme.space.L; Layout.fillWidth: true
                        color: Theme.colors.hover; radius: Theme.radius.CONTROL
                        M.ReadableText { id: notes; x: Theme.space.L; y: Theme.space.L; width: parent.width - 2 * Theme.space.L
                            text: root.backend.state.releaseNotes; textFormat: Text.MarkdownText; wrapMode: Text.WordWrap; onLinkActivated: link => Qt.openUrlExternally(link) }
                    }
                    M.ReadableText {
                        Layout.fillWidth: true; text: root.backend.state.releaseLink || ""
                        textFormat: Text.RichText; wrapMode: Text.WordWrap
                        onLinkActivated: link => Qt.openUrlExternally(link)
                    }
                }
            }
            Component { id: feedback; FeedbackPage { backend: filesActions } }
            Component {
                id: site
                NewProjectPage {
                    backend: root.backend
                }
            }
            Component {
                id: registry
                RegistryPage {
                    backend: root.backend
                }
            }
            Component {
                id: generic
                GridLayout {
                    columns: root.backend && root.backend.kind === "canopy" ? 2 : 1
                    columnSpacing: Theme.space.S; rowSpacing: Theme.space.S
                    // R601: the form whole, in its height; when the window is shorter its body scrolls (no scroll in a
                    // scroll)
                    Item {
                        id: formHolder
                        Layout.preferredWidth: root.backend && root.backend.kind === "canopy" ? M.ControlMetrics.dialogParts.sideForm : -1
                        Layout.maximumWidth: root.backend && root.backend.kind === "canopy" ? M.ControlMetrics.dialogParts.sideForm : Infinity
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredHeight: formColumn.implicitHeight
                        Layout.minimumHeight: formColumn.implicitHeight
                        Column {
                            id: formColumn
                            width: formHolder.width
                            spacing: Theme.space.M
                            FormFields {
                                visible: root.backend && root.backend.kind !== "canopy"
                                width: parent.width
                                backend: root.backend
                            }
                            M.Section {
                                visible: root.backend && root.backend.kind === "canopy"
                                width: parent.width; title: root.backend.labels.parkingSpaces; collapsible: false; nested: true
                                FormFields { width: parent.width; backend: root.backend; fields: root.backend.kind === "canopy" ? root.backend.fields.slice(0,4) : [] }
                            }
                            M.Section {
                                visible: root.backend && root.backend.kind === "canopy"
                                width: parent.width; title: root.backend.labels.structure; collapsible: false; nested: true
                                FormFields { width: parent.width; backend: root.backend; fields: root.backend.kind === "canopy" ? root.backend.fields.slice(4) : [] }
                            }
                            Repeater {
                                model: root.backend ? root.backend.state.variants : []
                                delegate: M.CheckBox {
                                    required property var modelData
                                    text: modelData.label + "\n" + modelData.detail
                                    checked: root.backend.state.selectedVariants.includes(modelData.index)
                                    onToggled: root.backend.selectVariant(modelData.index, checked)
                                }
                            }
                            M.Button {
                                visible: root.backend && root.backend.kind === "update"
                                text: root.backend ? root.backend.labels.search : ""
                                enabled: root.backend && !root.backend.busy
                                onClicked: root.backend.checkUpdate()
                            }
                            M.ReadableText {
                                width: parent.width
                                text: root.backend ? root.backend.state.releaseNotes : ""
                                textFormat: Text.MarkdownText
                                wrapMode: Text.WordWrap
                                onLinkActivated: link => Qt.openUrlExternally(link)
                            }
                            M.Button {
                                visible: root.backend && !!root.backend.state.releaseUrl
                                text: root.backend ? root.backend.labels.release : ""
                                onClicked: Qt.openUrlExternally(root.backend.state.releaseUrl)
                            }
                            M.Button {
                                visible: root.backend && root.backend.state.hasInstaller
                                text: root.backend ? root.backend.labels.download : ""
                                enabled: root.backend && !root.backend.busy
                                onClicked: root.backend.downloadUpdate()
                            }
                        }
                    }
                    GeometryPreview {
                        Layout.preferredWidth: M.ControlMetrics.dialogParts.geometry.width
                        Layout.preferredHeight: M.ControlMetrics.dialogParts.geometry.height
                        Layout.minimumWidth: M.ControlMetrics.dialogParts.geometry.least
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        visible: root.backend && ["canopy", "template"].includes(root.backend.kind)
                        backend: root.backend
                    }
                }
            }
        }
        // R601: the summary whole; the window's body scrolls it with the rest
        Item {
            id: summaryHolder
            Layout.fillWidth: true
            Layout.preferredHeight: summary.implicitHeight
            visible: root.backend && root.backend.kind !== "ifc" && root.backend.state.summary.length > 0
            Column {
                id: summary
                width: summaryHolder.width
                spacing: Theme.space.S
                Repeater {
                    model: root.backend ? root.backend.state.summary : []
                    delegate: M.ReadableText {
                        required property var modelData
                        width: parent.width
                        text: modelData
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
        M.ReadableText {
            Layout.fillWidth: true
            text: root.backend ? root.backend.state.note : ""
            visible: text.length > 0
            wrapMode: Text.WordWrap
            textStyle: "secondary"
            textFormat: root.backend && root.backend.kind === "about" ? Text.RichText : Text.AutoText
        }
        M.ReadableText {
            Layout.fillWidth: true
            text: root.backend ? root.backend.status : ""
            visible: text.length > 0 && root.backend.kind !== "ifc"
            wrapMode: Text.WordWrap
        }
        M.ProgressBar {
            Layout.fillWidth: true
            visible: root.backend && root.backend.busy && root.backend.kind !== "ifc"
            indeterminate: !root.backend || root.backend.state.progress === 0
            value: root.backend ? root.backend.state.progress : 0
        }
    }
    D.FileDialog {
        id: importFile
        nameFilters: ["PVsyst (*.prj *.PRJ)"]
        onAccepted: root.backend.readFile(selectedFile.toString())
    }
}
