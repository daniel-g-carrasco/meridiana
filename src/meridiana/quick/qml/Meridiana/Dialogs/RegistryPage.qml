import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs as D
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    property var backend
    property string selectedClient: ""
    property bool exportConsent: false
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.space.M
        RowLayout {
            M.Button {
                text: root.backend ? root.backend.labels.import : ""
                onClicked: importFile.open()
            }
            M.Button {
                text: root.backend ? root.backend.labels.export : ""
                onClicked: {
                    root.exportConsent = false;
                    if (root.backend.hasReservedJobs())
                        warning.open();
                    else
                        exportFile.open();
                }
            }
            M.Button {
                visible: root.backend && root.backend.state.canApplyImport
                text: root.backend ? root.backend.labels.apply : ""
                onClicked: root.backend.applyImport()
            }
        }
        M.TextField {
            Layout.fillWidth: true
            placeholderText: root.backend ? root.backend.labels.search : ""
            onTextEdited: root.backend.refreshRegistry(text)
        }
        RowLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: Theme.space.XL
            M.ScrollPage {
                Layout.fillHeight: true
                Layout.fillWidth: true
                // three equal columns, whatever their content asks (a ScrollPage reports its content's width)
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 1
                Column {
                    width: parent.width
                    spacing: Theme.space.S
                    Repeater {
                        model: root.backend ? root.backend.state.clients : []
                        delegate: M.Button {
                            required property var modelData
                            width: parent.width
                            text: modelData.name
                            active: root.selectedClient === modelData.id
                            flat: true
                            onClicked: root.selectedClient = modelData.id
                        }
                    }
                    M.Label {
                        text: root.backend ? root.backend.labels.clientName : ""
                    }
                    M.TextField {
                        id: clientName
                        width: parent.width
                        objectName: "registry_client_name"
                    }
                    M.Button {
                        text: root.backend ? root.backend.labels.saveClient : ""
                        onClicked: {
                            if (root.backend.saveClient(clientName.text))
                                clientName.clear();
                        }
                    }
                }
            }
            M.ScrollPage {
                Layout.fillHeight: true
                Layout.fillWidth: true
                // three equal columns, whatever their content asks (a ScrollPage reports its content's width)
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 1
                // r23-f5: the lane of the bar is always kept (R100): the middle column is at least as wide as
                // «Commessa riservata» on one line, plus the margin and the lane, so that the box is never cut
                Layout.minimumWidth: reserved.implicitWidth + leftMargin + rightMargin + bar.width + Theme.space.M
                Column {
                    width: parent.width
                    spacing: Theme.space.S
                    Repeater {
                        model: root.backend ? root.backend.state.jobs : []
                        delegate: M.Button {
                            required property var modelData
                            width: parent.width
                            text: modelData.code + "  " + modelData.name
                            flat: true
                            active: root.backend.state.selectedJob === modelData.id
                            onClicked: root.backend.selectJob(modelData.id)
                        }
                    }
                    M.Label {
                        text: root.backend ? root.backend.labels.jobCode : ""
                    }
                    M.TextField {
                        id: jobCode
                        width: parent.width
                        maximumLength: 5
                    }
                    M.Label {
                        text: root.backend ? root.backend.labels.jobName : ""
                    }
                    M.TextField {
                        id: jobName
                        width: parent.width
                    }
                    M.Label {
                        text: root.backend ? root.backend.labels.clientLabel : ""
                    }
                    M.ComboBox {
                        width: parent.width
                        options: root.backend ? root.backend.state.clients.map(c => ({
                                    value: c.id,
                                    label: c.name
                                })) : []
                        value: root.selectedClient
                        onChosen: value => root.selectedClient = value
                    }
                    M.CheckBox {
                        id: reserved
                        text: root.backend ? root.backend.labels.reserved : ""
                    }
                    M.Button {
                        text: root.backend ? root.backend.labels.saveJob : ""
                        onClicked: {
                            if (root.backend.saveJob(jobCode.text, jobName.text, root.selectedClient, reserved.checked)) {
                                jobName.clear();
                                jobCode.clear();
                            }
                        }
                    }
                }
            }
            M.ScrollPage {
                Layout.fillHeight: true
                Layout.fillWidth: true
                // three equal columns, whatever their content asks (a ScrollPage reports its content's width)
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 1
                Column {
                    width: parent.width
                    spacing: Theme.space.M
                    M.Label {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: root.backend && root.backend.state.jobDetail ? Object.entries(root.backend.state.jobDetail).filter(p => ["code", "name", "status", "phase"].includes(p[0])).map(p => p[1]).join("\n") : ""
                    }
                    Repeater {
                        model: root.backend ? root.backend.state.folders : []
                        delegate: M.CheckBox {
                            required property var modelData
                            width: parent.width
                            text: modelData.path
                            checked: modelData.manifest_consent
                            enabled: root.backend.state.jobDetail && !root.backend.state.jobDetail.reserved
                            onToggled: root.backend.manifestConsent(modelData.id, checked)
                        }
                    }
                    M.Button {
                        text: root.backend ? root.backend.labels.folder : ""
                        enabled: root.backend && !!root.backend.state.selectedJob
                        onClicked: folder.open()
                    }
                }
            }
        }
    }
    D.FileDialog {
        id: importFile
        nameFilters: ["JSON (*.json)"]
        onAccepted: root.backend.importRegistry(selectedFile.toString())
    }
    D.FileDialog {
        id: exportFile
        fileMode: D.FileDialog.SaveFile
        nameFilters: ["JSON (*.json)"]
        defaultSuffix: "json"
        onAccepted: root.backend.exportRegistry(selectedFile.toString(), root.exportConsent)
    }
    D.FolderDialog {
        id: folder
        onAccepted: root.backend.linkFolder(selectedFolder.toString())
    }
    // R21-F2: the warning before an export with reserved texts is a window (M.Dialog), its two buttons in its bar
    M.Dialog {
        id: warning
        anchors.centerIn: parent
        width: Math.min(root.width, M.ControlMetrics.dialogWidth.normal)
        rejectText: root.backend ? root.backend.labels.cancel : ""
        acceptText: root.backend ? root.backend.labels.export : ""
        onAccepted: { root.exportConsent = true; exportFile.open() }
        contentItem: M.Label {
            text: root.backend ? root.backend.labels.reservedExport : ""
            wrapMode: Text.WordWrap
        }
    }
}
