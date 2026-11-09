import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    property var backend
    property bool confirmReset: false
    objectName: "settingsPage"
    onVisibleChanged: { if (!visible && backend) backend.flushPending() }
    Connections {
        target: root.backend
        function onSectionChanged() { root.confirmReset = false; scroll.contentItem.contentY = 0 }
    }
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.space.M
        M.ScrollPage {
            id: scroll
            objectName: "settingsScroll"
            Layout.fillWidth: true
            Layout.fillHeight: true
            leftMargin: 0; rightMargin: Theme.space.XS; air: 0
            Column {
                // R501: the bar's room kept at the right, as ScrollPage keeps it (R100): the bar never lies on a row
                // and a long text wraps short of it.
                objectName: "settingsColumn"
                width: scroll.pageWidth
                spacing: Theme.space.S
                M.Label {
                    width: parent.width; wrapMode: Text.WordWrap
                    visible: root.backend && ["privacy", "report"].includes(root.backend.section)
                    text: !root.backend ? "" : root.backend.section === "privacy" ? root.backend.text.privacyLead : root.backend.text.reportLead
                }
                Repeater {
                    model: root.backend ? root.backend.fields.filter(f => !["report", "maps"].includes(root.backend.section) && (root.backend.section !== "assistant" || ["assistant", "assistant_docked", "assistant_animated", "assistant_style"].includes(f.key)) && (root.backend.section !== "appearance" || ["theme", "accent", "backgrounds", "text_size", "font", "toolbar", "toolbar_place"].includes(f.key))) : []
                    delegate: SettingField {
                        required property var modelData
                        width: parent.width
                        backend: root.backend
                        field: modelData
                    }
                }
                Column {
                    width: parent.width
                    visible: root.backend && root.backend.section === "appearance"
                    spacing: Theme.space.S
                    RowLayout {
                        width: parent.width
                        spacing: Theme.space.L
                        M.Label { text: root.backend ? root.backend.text.panels : ""; Layout.preferredWidth: 116 }
                        M.Button { Layout.fillWidth: true; text: root.backend ? root.backend.text.layout : ""; onClicked: root.backend.requestCommand("default_layout") }
                    }
                    AppearancePreview { width: parent.width; backend: root.backend }
                    M.Section {
                        width: parent.width
                        title: root.backend ? root.backend.text.additional : ""
                        _open: false
                        RowLayout {
                            width: parent.width
                            M.TextField { id: custom; objectName: "settingsCustomAccent"; Layout.fillWidth: true; placeholderText: "#1c6e8c" }
                            M.Button { text: root.backend ? root.backend.text.custom : ""; onClicked: root.backend.setValue("accent", custom.text) }
                        }
                        Repeater {
                            model: root.backend ? root.backend.fields.filter(f => !["theme", "accent", "backgrounds", "text_size", "font", "toolbar", "toolbar_place"].includes(f.key)) : []
                            delegate: SettingField { required property var modelData; width: parent.width; backend: root.backend; field: modelData }
                        }
                    }
                }
                Column {
                    width: parent.width
                    visible: root.backend && root.backend.section === "navigation"
                    spacing: Theme.space.M
                    M.Label { width: parent.width; wrapMode: Text.WordWrap; text: root.backend ? root.backend.navigationHelp.hint : "" }
                    M.Label { width: parent.width; wrapMode: Text.WordWrap; text: root.backend ? root.backend.navigationHelp.audience : "" }
                    Column {
                        width: parent.width
                        spacing: Theme.space.S
                        Repeater {
                            model: root.backend ? root.backend.navigationHelp.gestures : []
                            delegate: RowLayout {
                                required property var modelData
                                width: parent.width
                                spacing: Theme.space.S
                                M.Label { Layout.preferredWidth: 122; text: modelData.action; textStyle: "strong" }
                                M.Label { Layout.fillWidth: true; text: modelData.gesture; wrapMode: Text.WordWrap }
                            }
                        }
                    }
                    M.Label { width: parent.width; wrapMode: Text.WordWrap; text: root.backend ? root.backend.navigationHelp.note : "" }
                }
                Column {
                    width: parent.width; spacing: Theme.space.S
                    visible: root.backend && root.backend.section === "privacy"
                    M.Label { width: parent.width; text: root.backend ? root.backend.text.privacyChannel : ""; wrapMode: Text.WordWrap }
                    M.Label { width: parent.width; text: root.backend ? root.backend.text.privacyRecovery : ""; wrapMode: Text.WordWrap }
                }
                Loader {
                    width: parent.width
                    active: root.backend && root.backend.section === "keyboard"
                    visible: active
                    sourceComponent: keyboard
                }
                Loader {
                    width: parent.width
                    active: root.backend && (root.backend.section === "report" || root.backend.section === "maps")
                    visible: active
                    sourceComponent: root.backend.section === "maps" ? maps : records
                }
                Loader {
                    width: parent.width
                    active: root.backend && root.backend.section === "assistant"
                    visible: active
                    sourceComponent: assistant
                }
            }
        }
        M.Label {
            objectName: "settingsError"
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.backend ? root.backend.error : ""
            color: Theme.colors.danger
            wrapMode: Text.WordWrap
        }
        M.Button {
            objectName: "settingsTakeShortcut"
            visible: root.backend && root.backend.section === "keyboard" && root.backend.shortcutConflict
            text: root.backend ? root.backend.text.takeShortcut : ""
            onClicked: root.backend.takeShortcut()
        }
        Flow {
            Layout.fillWidth: true
            visible: root.confirmReset
            spacing: Theme.space.S
            M.Label { text: root.backend ? root.backend.text.confirm : "" }
            M.Button { objectName: "settingsConfirmReset"; text: root.backend ? root.backend.text.restore : ""; onClicked: { root.backend.restoreDefaults(root.backend.section); root.confirmReset = false } }
            M.Button { text: root.backend ? root.backend.text.cancel : ""; onClicked: root.confirmReset = false }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space.S
            M.Button {
                objectName: "settingsUndo"
                text: root.backend ? root.backend.text.undo : ""
                enabled: root.backend && root.backend.canUndo
                onClicked: root.backend.undoLast()
            }
            M.Button {
                objectName: "settingsReset"
                text: root.backend ? root.backend.text.reset : ""
                onClicked: root.confirmReset = true
            }
        }
    }
    Component {
        id: keyboard
        SettingsKeyboard { backend: root.backend; height: Math.max(360, scroll.height) }
    }
    Component {
        id: maps
        SettingsMaps { backend: root.backend }
    }
    Component {
        id: records
        Column {
            spacing: Theme.space.L
            SettingsRecords { width: parent.width; backend: root.backend; maps: root.backend.section === "maps" }
            Repeater {
                model: root.backend.section === "report" ? root.backend.fields : []
                SettingField { required property var modelData; width: parent.width; backend: root.backend; field: modelData }
            }
            M.Section {
                width: parent.width
                title: root.backend.text.builtin
                visible: root.backend.section === "maps"
                Repeater {
                    model: root.backend.builtinSources
                    delegate: Column {
                        required property var modelData
                        width: parent.width
                        M.Label { width: parent.width; text: modelData.name; textStyle: "strong"; wrapMode: Text.WordWrap }
                        M.Label { width: parent.width; text: modelData.licence + " · " + modelData.attribution; textStyle: "description"; wrapMode: Text.WordWrap }
                    }
                }
            }
        }
    }
    Component {
        id: assistant
        Column {
            spacing: Theme.space.S
            Component.onCompleted: if (!root.backend.services.localBusy && !root.backend.services.localStatus) root.backend.services.searchLocal()
            Repeater {
                model: root.backend.fields.filter(f => ["assistant_provider"].includes(f.key))
                SettingField { required property var modelData; width: parent.width; backend: root.backend; field: modelData }
            }
            M.Section {
                width: parent.width
                title: root.backend.text.localModels
                M.Label { width: parent.width; text: root.backend.services.localStatus; wrapMode: Text.WordWrap }
                Column {
                    width: parent.width; spacing: Theme.space.XS
                    visible: !!root.backend.services.localGuide.title
                    M.Label { width: parent.width; text: root.backend.services.localGuide.machine || ""; wrapMode: Text.WordWrap }
                    M.Label { width: parent.width; text: root.backend.services.localGuide.title || ""; wrapMode: Text.WordWrap; textFormat: Text.RichText }
                    M.Label { width: parent.width; text: root.backend.services.localGuide.licence || ""; wrapMode: Text.WordWrap }
                    M.Button { text: root.backend.services.localGuide.card || ""; onClicked: Qt.openUrlExternally(root.backend.services.localGuide.url) }
                    Repeater {
                        model: root.backend.services.localGuide.steps || []
                        Column {
                            required property var modelData; required property int index
                            width: parent.width; spacing: Theme.space.XS
                            M.Label { width: parent.width; text: (index + 1) + ". " + modelData.text; wrapMode: Text.WordWrap }
                            RowLayout {
                                width: parent.width; visible: !!modelData.command
                                M.TextField { Layout.fillWidth: true; text: modelData.command; readOnly: true }
                                M.Button { iconName: "clipboard-copy"; flat: true; onClicked: root.backend.services.copyCommand(modelData.command) }
                            }
                        }
                    }
                }
                Flow {
                    width: parent.width; spacing: Theme.space.S
                    M.Button { objectName: "settingsSearchLocal"; text: root.backend.text.searchLocal; enabled: !root.backend.services.localBusy; onClicked: root.backend.services.searchLocal() }
                    M.Button { text: root.backend.text.testLocal; enabled: !root.backend.services.testBusy; onClicked: root.backend.services.testLocal() }
                    M.Button { text: root.backend.text.stop; visible: root.backend.services.testBusy; onClicked: root.backend.services.cancelTest() }
                }
                M.Label { width: parent.width; text: root.backend.services.testStatus; wrapMode: Text.WordWrap }
                Repeater {
                    model: root.backend.services.localModels
                    delegate: Column {
                        required property var modelData
                        required property int index
                        width: parent.width
                        M.Label { width: parent.width; text: modelData.runtime + ": " + modelData.name; wrapMode: Text.WordWrap }
                        M.Label { width: parent.width; text: modelData.note; wrapMode: Text.WordWrap; visible: text.length > 0 }
                        M.Button { text: root.backend.text.useLocal; enabled: modelData.usable; onClicked: root.backend.services.useLocal(index) }
                    }
                }
            }
            Repeater {
                model: root.backend.fields.filter(f => ["assistant_local_url", "assistant_local_runtime", "assistant_local_model"].includes(f.key))
                SettingField { required property var modelData; width: parent.width; backend: root.backend; field: modelData }
            }
            M.Label { text: root.backend.text.cloud; textStyle: "label" }
            M.Label { width: parent.width; text: root.backend.text.keyNote; wrapMode: Text.WordWrap }
            M.Label { width: parent.width; text: root.backend.text.cloudNote; wrapMode: Text.WordWrap }
            M.Button { text: root.backend.text.consent; onClicked: root.backend.setValue("assistant_consent", ({})) }
            Repeater {
                model: root.backend.cloudProfiles
                delegate: Column {
                    required property var modelData
                    property bool expanded: false
                    width: parent.width
                    spacing: Theme.space.S
                    M.Button { text: modelData.label; onClicked: parent.expanded = !parent.expanded }
                    Column {
                        width: parent.width
                        visible: parent.expanded
                        spacing: Theme.space.S
                        M.TextField { id: model; width: parent.width; text: modelData.model; placeholderText: root.backend.text.model }
                        M.TextField { id: endpoint; width: parent.width; text: modelData.endpoint; placeholderText: root.backend.text.endpoint }
                        M.Button { text: root.backend.text.save; onClicked: root.backend.setCloudProfile(modelData.key, model.text, endpoint.text) }
                        M.TextField { id: secret; width: parent.width; echoMode: TextInput.Password; placeholderText: root.backend.text.key }
                        Flow {
                            width: parent.width
                            spacing: Theme.space.S
                            M.Button { text: root.backend.text.key; onClicked: { root.backend.setSecret(modelData.key, secret.text, "meridiana-assistant"); secret.clear() } }
                            M.Button { text: root.backend.text.forget; onClicked: root.backend.setSecret(modelData.key, "", "meridiana-assistant") }
                        }
                    }
                }
            }
            Repeater {
                model: root.backend.fields.filter(f => ["assistant_voice", "assistant_voice_engine", "assistant_voice_name", "assistant_kokoro_dir", "assistant_kokoro_python"].includes(f.key))
                SettingField { required property var modelData; width: parent.width; backend: root.backend; field: modelData }
            }
            M.Label { width: parent.width; text: root.backend.text.downloadNote; wrapMode: Text.WordWrap }
            Flow {
                width: parent.width
                spacing: Theme.space.S
                M.Button { text: root.backend.text.downloadVoice; enabled: !root.backend.services.downloadBusy; onClicked: root.backend.services.downloadVoice() }
                M.Button { text: root.backend.text.stop; visible: root.backend.services.downloadBusy; onClicked: root.backend.services.cancelDownload() }
            }
            M.Label { width: parent.width; text: root.backend.services.downloadStatus; wrapMode: Text.WordWrap }
            M.Section {
                width: parent.width; title: root.backend.text.additional; _open: false
                Repeater {
                    model: root.backend.fields.filter(f => ["assistant_width", "assistant_height", "assistant_cloud_model"].includes(f.key))
                    SettingField { required property var modelData; width: parent.width; backend: root.backend; field: modelData }
                }
            }
        }
    }
}
