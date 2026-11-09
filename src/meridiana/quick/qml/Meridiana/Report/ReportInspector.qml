import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    property var backend
    readonly property var words: backend ? backend.labels : ({})
    FileDialog {
        id: attachmentsDialog
        title: root.words.add || ""
        fileMode: FileDialog.OpenFiles
        nameFilters: ["PDF (*.pdf)"]
        onAccepted: root.backend.addAttachments(selectedFiles)
    }
            M.ScrollPage {
                id: choices
                anchors.fill: parent
                leftMargin: 0; air: 0
                ColumnLayout {
                    width: choices.availableWidth
                    spacing: Theme.space.M
                    M.Label { text: root.words.section || ""; textStyle: "strong" }
                    GridLayout {
                        columns: 2; Layout.fillWidth: true; columnSpacing: Theme.space.L; rowSpacing: Theme.space.M
                        M.Label { text: root.words.template || "" }
                        ReportChoice {
                            objectName: "reportTemplate"; Layout.fillWidth: true
                            model: root.backend ? root.backend.templates : []
                            selectedValue: root.backend ? root.backend.settings.template : ""
                            onActivated: root.backend.setSetting("template", currentValue)
                        }
                        M.Label {
                            Layout.columnSpan: 2; Layout.fillWidth: true
                            text: root.backend ? (root.backend.templates.find(t => t.id === root.backend.settings.template) || {}).note || "" : ""
                            color: Theme.colors.muted; wrapMode: Text.Wrap
                        }
                        M.Label { text: root.words.profile || "" }
                        RowLayout {
                            Layout.fillWidth: true; spacing: Theme.space.S
                            ReportChoice {
                                Layout.fillWidth: true
                                model: root.backend ? root.backend.profiles : []
                                selectedValue: root.backend ? root.backend.settings.profile : null
                                onActivated: root.backend.setSetting("profile", currentValue)
                            }
                            M.Button { text: root.words.profiles || ""; onClicked: root.backend.command("report_profile") }
                        }
                        M.Label { text: root.words.client || "" }
                        M.TextField {
                            id: clientField; objectName: "reportClient"; Layout.fillWidth: true
                            placeholderText: root.words.clientHint || ""
                            onEditingFinished: root.backend.setSetting("client", text.trim())
                            Binding { target: clientField; property: "text"; value: root.backend ? root.backend.settings.client : ""; when: !clientField.activeFocus; restoreMode: Binding.RestoreNone }
                        }
                        M.Label { text: root.words.revision || "" }
                        M.TextField {
                            id: revisionField; objectName: "reportRevision"; Layout.fillWidth: true
                            placeholderText: root.words.revisionHint || ""
                            onEditingFinished: root.backend.setSetting("revision", text.trim())
                            Binding { target: revisionField; property: "text"; value: root.backend ? root.backend.settings.revision : ""; when: !revisionField.activeFocus; restoreMode: Binding.RestoreNone }
                        }
                    }
                    M.CheckBox { text: root.words.address || ""; checked: root.backend && root.backend.settings.address; onToggled: root.backend.setSetting("address", checked) }
                    M.CheckBox {
                        Layout.fillWidth: true
                        text: root.words.register || ""
                        checked: root.backend && root.backend.settings.register
                        contentItem: M.Label { text: parent.text; leftPadding: Theme.icon.CONTROL + Theme.space.M; wrapMode: Text.Wrap }
                        implicitHeight: Math.max(Theme.size.CONTROL, contentItem.implicitHeight)
                        onToggled: root.backend.setSetting("register", checked)
                    }
                    M.Label { text: root.words.chapters || ""; textStyle: "strong" }
                    Repeater {
                        model: root.backend ? root.backend.chapters : []
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: Theme.space.XXS
                            M.CheckBox {
                                Layout.fillWidth: true
                                text: modelData.title
                                enabled: modelData.enabled
                                checked: modelData.checked
                                contentItem: M.Label { text: parent.text; leftPadding: Theme.icon.CONTROL + Theme.space.M; wrapMode: Text.Wrap }
                                implicitHeight: Math.max(Theme.size.CONTROL - Theme.space.XS, contentItem.implicitHeight)
                                onToggled: root.backend.setChapter(modelData.id, checked)
                                M.ToolTip { visible: parent.hovered; text: modelData.reason || modelData.note }
                            }
                        }
                    }
                    M.Label { text: root.words.attachments || ""; textStyle: "strong" }
                    M.Label { Layout.fillWidth: true; text: root.words.attachmentNote || ""; textStyle: "secondary"; wrapMode: Text.Wrap }
                    Repeater {
                        model: root.backend ? root.backend.attachments : []
                        delegate: ColumnLayout {
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            M.TextField {
                                Layout.fillWidth: true
                                text: modelData.title
                                onEditingFinished: root.backend.retitleAttachment(index, text)
                            }
                            M.Label { Layout.fillWidth: true; text: modelData.detail || ""; wrapMode: Text.Wrap; textStyle: "caption" }
                            RowLayout {
                                M.Button { text: root.words.up || ""; enabled: index > 0; onClicked: root.backend.moveAttachment(index, -1) }
                                M.Button { text: root.words.down || ""; enabled: index + 1 < root.backend.attachments.length; onClicked: root.backend.moveAttachment(index, 1) }
                                M.Button { text: root.words.remove || ""; onClicked: root.backend.removeAttachment(index) }
                            }
                        }
                    }
                    M.Button { text: root.words.add || ""; onClicked: attachmentsDialog.open() }
                }
            }
}
