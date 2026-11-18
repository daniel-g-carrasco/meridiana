import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import QtQuick.Dialogs
import Meridiana.Controls as M
import Meridiana.Theme

ColumnLayout {
    id: root
    required property var backend
    spacing: Theme.space.S
    M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.backend.labels.intro }
    M.TextField { Layout.fillWidth: true; placeholderText: root.backend.labels.title; maximumLength: 180; onTextEdited: root.backend.setDraft('title', text) }
    M.ScrollPage {
        Layout.fillWidth: true; Layout.fillHeight: true; follow: description
        M.TextArea { id: description; width: parent.width; placeholderText: root.backend.labels.description; onTextChanged: root.backend.setDraft('description', text) }
    }
    M.CheckBox { text: root.backend.labels.environment; checked: true; onToggled: root.backend.setDraft('environment', checked) }
    M.CheckBox { text: root.backend.labels.context; onToggled: root.backend.setDraft('context', checked) }
    M.CheckBox { id: diagnostics; text: root.backend.labels.diagnostics; onToggled: root.backend.setDraft('include_diagnostics', checked) }
    M.ScrollPage {
        visible: diagnostics.checked; Layout.fillWidth: true; Layout.preferredHeight: 64; follow: diagnosticsText
        M.TextArea { id: diagnosticsText; width: parent.width; onTextChanged: root.backend.setDraft('diagnostics', text) }
    }
    M.Label { text: root.backend.labels.preview }
    M.ScrollPage { Layout.fillWidth: true; Layout.fillHeight: true; M.TextArea { bare: true; width: parent.width; readOnly: true; text: root.backend.preview } }
    M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.backend.status || root.backend.labels.note }
    Flow {
        Layout.fillWidth: true; spacing: Theme.space.S
        M.Button { text: root.backend.labels.copy; onClicked: root.backend.copyDraft() }
        M.Button { text: root.backend.labels.save; onClicked: save.open() }
        M.Button { text: root.backend.labels.open; enabled: root.backend.canShare; onClicked: root.backend.openDraft() }
    }
    FileDialog { id: save; fileMode: FileDialog.SaveFile; nameFilters: ["Text (*.txt)"]; defaultSuffix: "txt"; onAccepted: root.backend.saveDraft(selectedFile.toString()) }
}
