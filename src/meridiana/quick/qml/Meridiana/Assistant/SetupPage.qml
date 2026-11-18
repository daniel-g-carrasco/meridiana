import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

M.ScrollPage {
    id: root
    property var backend: null
    property var texts: assistantText
    property string mode: "choose"
    leftMargin: 0; air: 0
    ColumnLayout {
        width: root.pageWidth; spacing: Theme.space.M
        M.Label { text: root.texts.setup; textStyle: "title"; Layout.fillWidth: true; wrapMode: Text.Wrap }
        M.Label { text: root.texts.setupIntro; Layout.fillWidth: true; wrapMode: Text.Wrap }
        M.ComboBox {
            objectName: "assistantSetupMode"
            Layout.fillWidth: true
            model: [{id: "choose", text: root.texts.chooseMode}, {id: "local", text: root.texts.localChoice}, {id: "cloud", text: root.texts.cloudChoice}]
            textRole: "text"; valueRole: "id"
            onActivated: root.mode = currentValue
        }
        M.Label { text: root.texts.preview; visible: !root.backend; Layout.fillWidth: true; wrapMode: Text.Wrap }
        M.Label { text: root.texts.cloud; textStyle: "strong"; visible: !!root.backend && root.mode === "cloud" }
        M.Label { text: root.texts.apiNotes; Layout.fillWidth: true; wrapMode: Text.Wrap; visible: !!root.backend && root.mode === "cloud" }
        M.ComboBox {
            id: provider
            Layout.fillWidth: true; visible: !!root.backend && root.mode === "cloud"
            model: root.backend ? root.backend.providers : []
            textRole: "text"; valueRole: "id"
            font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
            onActivated: root.backend.chooseProvider(currentValue)
            currentIndex: { for (let i = 0; i < count; ++i) if (valueAt(i) === (root.backend ? root.backend.provider : "")) return i; return 0 }
        }
        M.Label { text: root.texts.model; visible: !!root.backend && root.mode === "cloud" }
        M.TextField { id: model; objectName: "assistantSetupModel"; Layout.fillWidth: true; text: root.backend ? root.backend.model : ""; visible: !!root.backend && root.mode === "cloud" }
        M.Label { text: root.texts.endpoint; visible: !!root.backend && root.mode === "cloud" }
        M.TextField { id: endpoint; objectName: "assistantSetupEndpoint"; Layout.fillWidth: true; text: root.backend ? root.backend.endpoint : ""; visible: !!root.backend && root.mode === "cloud" }
        M.Label { text: root.texts.apiKey; visible: !!root.backend && root.mode === "cloud" }
        M.TextField { id: key; objectName: "assistantSetupKey"; Layout.fillWidth: true; echoMode: TextInput.Password; visible: !!root.backend && root.mode === "cloud" }
        Flow {
            Layout.fillWidth: true; spacing: Theme.space.XS; visible: !!root.backend && root.mode === "cloud"
            M.Button { text: root.texts.account; onClicked: root.backend.openAccount() }
            M.Button { text: root.texts.save; onClicked: { if (root.backend.saveCloud(root.backend.provider, model.text, endpoint.text, key.text)) key.clear() } }
        }
        M.Label { text: root.backend ? root.backend.status : ""; visible: root.mode === "cloud"; Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "caption" }
        LocalPage {
            visible: root.mode === "local"
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            backend: root.backend ? root.backend.localModels : null; texts: root.texts
        }
        M.Button { text: root.texts.notNow; visible: !!root.backend; onClicked: { key.clear(); root.backend.dismiss() } }
    }
    Connections { target: root.backend; function onChanged() { key.clear() } }
    Component.onDestruction: key.clear()
}
