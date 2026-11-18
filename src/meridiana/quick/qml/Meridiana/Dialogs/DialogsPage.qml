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
    implicitHeight: page.implicitHeight + page.anchors.topMargin + page.anchors.bottomMargin
    ColumnLayout {
        id: page
        anchors.fill: parent
        // R518: the margins of every window (M.ControlMetrics), New project's too
        anchors.margins: M.ControlMetrics.dialogPad
        spacing: M.ControlMetrics.dialogGap
        M.Label {
            text: root.backend ? root.backend.state.title : ""
            objectName: "dialogTitle"
            textStyle: "heading"
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        M.Label {
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
            Layout.fillHeight: true
            Layout.fillWidth: true
            visible: !root.backend || !["shortcuts", "about"].includes(root.backend.kind)
            sourceComponent: !root.backend ? null : root.backend.kind === "ifc" ? ifcPage : root.backend.kind === "update" ? update : ["new", "site"].includes(root.backend.kind) ? site : root.backend.kind === "report_bug" ? feedback : root.backend.kind === "registry" ? registry : root.backend.kind === "shortcuts" ? null : root.backend.kind === "about" ? null : generic
            Component { id: ifcPage; IfcImportPage { backend: root.backend } }
            Component {
                id: update
                ColumnLayout {
                    spacing: Theme.space.M
                    M.Label { text: root.backend.state.currentVersion || ""; Layout.fillWidth: true }
                    M.Button {
                        visible: !root.backend.state.releaseUrl
                        text: root.backend.labels.search; enabled: !root.backend.busy
                        onClicked: root.backend.checkUpdate()
                    }
                    Rectangle {
                        visible: !!root.backend.state.releaseNotes
                        Layout.preferredHeight: 240; Layout.fillHeight: true; Layout.fillWidth: true
                        color: Theme.colors.hover; radius: Theme.radius.CONTROL
                        M.ScrollPage {
                            leftMargin: 0; air: 0; groundAbove: true
                            anchors.fill: parent; anchors.margins: 12
                            M.Label { width: parent.width; text: root.backend.state.releaseNotes; textFormat: Text.MarkdownText; wrapMode: Text.WordWrap; onLinkActivated: link => Qt.openUrlExternally(link) }
                        }
                    }
                    M.Label {
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
                    columnSpacing: 6; rowSpacing: 6
                    M.ScrollPage {
                        leftMargin: 0; air: 0; groundAbove: true
                        Layout.preferredWidth: root.backend && root.backend.kind === "canopy" ? 340 : -1
                        Layout.maximumWidth: root.backend && root.backend.kind === "canopy" ? 340 : Infinity
                        Layout.fillWidth: true
                        Layout.fillHeight: root.backend && !["template", "ifc"].includes(root.backend.kind)
                        Layout.preferredHeight: formColumn.implicitHeight
                        Column {
                            id: formColumn
                            width: parent.width
                            spacing: Theme.space.M
                            M.Button {
                                visible: root.backend && root.backend.kind === "pvsyst"
                                text: root.backend ? root.backend.labels.chooseFile : ""
                                enabled: root.backend && !root.backend.busy
                                onClicked: importFile.open()
                            }
                            M.Label {
                                width: parent.width
                                text: root.backend ? (root.backend.state.fileDescription || root.backend.state.fileName) : ""
                                wrapMode: Text.WrapAnywhere
                                visible: text.length > 0
                            }
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
                                visible: root.backend && root.backend.state.variants.length > 0
                                text: root.backend ? root.backend.labels.read : ""
                                enabled: root.backend && !root.backend.busy
                                onClicked: root.backend.readVariants()
                            }
                            M.Button {
                                visible: root.backend && root.backend.kind === "update"
                                text: root.backend ? root.backend.labels.search : ""
                                enabled: root.backend && !root.backend.busy
                                onClicked: root.backend.checkUpdate()
                            }
                            M.Label {
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
                        Layout.preferredWidth: 320
                        Layout.preferredHeight: 240
                        Layout.minimumWidth: 300
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        visible: root.backend && ["canopy", "template"].includes(root.backend.kind)
                        backend: root.backend
                    }
                }
            }
        }
        M.ScrollPage {
            leftMargin: 0; air: 0; groundAbove: true
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(150, summary.implicitHeight)
            visible: root.backend && root.backend.kind !== "ifc" && root.backend.state.summary.length > 0
            Column {
                id: summary
                width: parent.width
                spacing: Theme.space.S
                Repeater {
                    model: root.backend ? root.backend.state.summary : []
                    delegate: M.Label {
                        required property var modelData
                        width: parent.width
                        text: modelData
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
        M.Label {
            Layout.fillWidth: true
            text: root.backend ? root.backend.state.note : ""
            visible: text.length > 0
            wrapMode: Text.WordWrap
            textStyle: "secondary"
            textFormat: root.backend && root.backend.kind === "about" ? Text.RichText : Text.AutoText
        }
        M.Label {
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
        RowLayout {
            Layout.fillWidth: true
            visible: !root.newProject
            Item {
                Layout.fillWidth: true
            }
            M.Button {
                visible: root.backend && root.backend.kind === "update" && !!root.backend.state.releaseUrl
                text: !root.backend ? "" : root.backend.state.hasInstaller ? root.backend.labels.download : root.backend.labels.release
                enabled: root.backend && !root.backend.busy
                onClicked: {
                    if (root.backend.state.hasInstaller) root.backend.downloadUpdate()
                    else { Qt.openUrlExternally(root.backend.state.releaseUrl); root.backend.cancel() }
                }
            }
            M.Button {
                objectName: root.newProject ? "dialog_accept_unused" : "dialog_accept"
                visible: root.backend && !["registry", "update", "about", "report_bug"].includes(root.backend.kind)
                text: root.backend ? (root.backend.kind === "new" ? root.backend.labels.create : ["template", "canopy"].includes(root.backend.kind) ? root.backend.labels.place : root.backend.kind === "ifc" ? root.backend.labels.addModel : root.backend.kind === "pvsyst" ? root.backend.labels.importProject : root.backend.labels.accept) : ""
                enabled: root.backend && root.backend.state.valid && !root.backend.busy
                onClicked: root.backend.accept()
            }
            M.Button {
                objectName: "dialog_cancel"
                text: !root.backend ? "" : root.backend.kind === "update" ? root.backend.labels.later : root.backend.kind === "about" ? root.backend.labels.close : root.backend.labels.cancel
                onClicked: root.backend.cancel()
            }
        }
    }
    D.FileDialog {
        id: importFile
        nameFilters: ["PVsyst (*.prj *.PRJ)"]
        onAccepted: root.backend.readFile(selectedFile.toString())
    }
}
