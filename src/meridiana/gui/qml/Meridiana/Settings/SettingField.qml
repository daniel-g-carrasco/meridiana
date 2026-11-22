import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    required property var backend
    required property var field
    // R630: the section, the values and the width of the labels are the page's (SettingsPage), read once for all
    // its rows; before, each row asked Python the values and the fields and measured every label of the section
    property string section: ""
    property var values: ({})
    property var value: field.key === "report_profile" ? backend.defaultProfile : values[field.key]
    property real labelWidth: 116
    readonly property bool indentedCheck: section === "navigation" && field.kind === "bool"
    // the name on the page shown only (R630 keeps every section's page): Meridio lights the row he takes one to (study 50)
    property bool shown: true
    objectName: shown ? "settingsRow_" + field.key : ""
    spacing: Theme.space.XS
    GridLayout {
        width: root.width
        columns: root.width < 520 || (root.field.kind === "bool" && !root.indentedCheck) ? 1 : 2
        columnSpacing: Theme.space.S
        rowSpacing: Theme.space.XS
        M.ReadableText {
            Layout.preferredWidth: parent.columns === 1 ? root.width : root.labelWidth
            Layout.fillWidth: parent.columns === 1
            text: root.indentedCheck ? "" : root.field.label
            visible: root.field.kind !== "bool" || root.indentedCheck
            wrapMode: Text.WordWrap
        }
        Loader {
            Layout.fillWidth: true
            sourceComponent: root.field.kind === "bool" ? switchControl :
                             root.field.kind === "choice" ? choiceControl :
                             root.field.kind === "number" ? numberControl : textControl
            enabled: root.field.enabled
        }
    }
    M.Button {
        // a field's action beside it: «Listen» reads a sentence with the voice's settings (R492)
        objectName: "settingAction_" + root.field.key
        visible: !!root.field.action
        text: root.field.actionLabel || ""
        onClicked: root.backend.runAction(root.field.action)
    }
    M.ReadableText {
        width: parent.width
        // the memory's note says what the window holds now (R548): read when Performance is shown
        text: root.field.key === "memory_mode" ? root.backend.memoryNote : root.field.description
        textStyle: "description"
        wrapMode: Text.WordWrap
        visible: text.length > 0 && root.section !== "appearance" && root.section !== "maps"
    }
    Component {
        id: switchControl
        M.CheckBox {
            objectName: "setting_" + root.field.key
            checked: !!root.value
            text: root.field.label
            contentItem: M.Label { text: parent.text; leftPadding: Theme.icon.CONTROL + Theme.space.M; wrapMode: Text.WordWrap }
            implicitHeight: Math.max(Theme.size.CONTROL, contentItem.implicitHeight)
            onClicked: root.backend.setValue(root.field.key, checked)
        }
    }
    Component {
        id: choiceControl
        M.ComboBox {
            objectName: "setting_" + root.field.key
            options: root.field.options
            value: root.value
            onChosen: value => root.backend.setValue(root.field.key, value)
        }
    }
    Component {
        id: numberControl
        M.NumberField {
            objectName: "setting_" + root.field.key
            value: root.value
            minimum: root.field.minimum
            maximum: root.field.maximum
            decimals: root.field.decimals
            stepSize: root.field.step || (decimals ? 0.05 : 10)
            onValueEdited: value => root.backend.setValue(root.field.key, value)
        }
    }
    Component {
        id: textControl
        M.TextField {
            id: edit
            objectName: "setting_" + root.field.key
            text: String(root.value)
            onCommitRequested: root.backend.flushPending()
            onTextEdited: root.backend.stageValue(root.field.key, text)
        }
    }
}
