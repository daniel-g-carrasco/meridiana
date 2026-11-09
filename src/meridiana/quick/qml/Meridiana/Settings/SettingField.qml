import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    required property var backend
    required property var field
    property var value: field.key === "report_profile" ? backend.defaultProfile : backend.values[field.key]
    property real labelWidth: Math.max(backend.section === "navigation" ? 104 : 116, ...backend.fields.filter(f => f.kind !== "bool").map(f => Theme.measureText(f.label).width))
    readonly property bool indentedCheck: backend.section === "navigation" && field.kind === "bool"
    objectName: "settingsRow_" + field.key
    spacing: Theme.space.XS
    GridLayout {
        width: root.width
        columns: root.width < 520 || (root.field.kind === "bool" && !root.indentedCheck) ? 1 : 2
        columnSpacing: Theme.space.S
        rowSpacing: Theme.space.XS
        M.Label {
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
    M.Label {
        width: parent.width
        text: root.field.description
        textStyle: "description"
        wrapMode: Text.WordWrap
        visible: text.length > 0 && root.backend.section !== "appearance" && root.backend.section !== "maps"
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
            onEditingFinished: root.backend.flushPending()
            onTextEdited: root.backend.stageValue(root.field.key, text)
        }
    }
}
