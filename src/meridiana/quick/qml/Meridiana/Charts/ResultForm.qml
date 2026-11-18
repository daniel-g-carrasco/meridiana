import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Properties

Column {
    id: root
    property var sections: []
    required property var backend
    required property var stateOwner
    spacing: Theme.space.L
    topPadding: Theme.space.S + 1
    bottomPadding: Theme.space.L
    Repeater {
        model: root.sections
        M.Section {
            id: group
            density: "form"
            required property var modelData
            width: root.width - 2*Theme.space.L; x: Theme.space.L
            title: modelData.title; helpId: modelData.help; helpTip: modelData.helpTip
            framed: modelData.framed
            collapsed: root.stateOwner.closed(modelData.key)
            onToggled: root.stateOwner.toggle(modelData.key)
            onHelpRequested: root.backend.help(helpId)
            readonly property real naturalLabelWidth: {
                let wanted = 0
                for (const field of modelData.fields) {
                    if (!["check", "action", "note", "heading"].includes(field.data.kind))
                        wanted = Math.max(wanted, Theme.measureText(field.data.label).width)
                }
                return wanted
            }
            readonly property real labelWidth: Math.min(naturalLabelWidth, (width-2*Theme.space.M)*.52)
            Repeater {
                model: group.modelData.fields
                Loader {
                    id: editor
                    required property var modelData
                    width: parent.width
                    sourceComponent: modelData.data.id.startsWith("array_") ? arrayRow : modelData.data.id === "mode" ? modeButtons : modelData.data.kind === "choice" ? choiceEditor : fieldEditor
                    Component {
                        id: arrayRow
                        RowList { rows: { const lines=editor.modelData.data.display.split("\n"); return [[lines[0],lines.slice(1).join("\n")]] } }
                    }
                    Component {
                        id: choiceEditor
                        RowLayout {
                            spacing: Theme.space.S
                            M.Label { visible: text !== ""; text: editor.modelData.data.label; Layout.preferredWidth: group.labelWidth; wrapMode: Text.Wrap }
                            M.ComboBox {
                                objectName: "editor:" + editor.modelData.data.id
                                Layout.fillWidth: true
                                options: editor.modelData.data.options; value: editor.modelData.data.value
                                enabled: editor.modelData.data.enabled
                                accessibleName: editor.modelData.data.label
                                onChosen: value => root.backend.commit(editor.modelData.data.id, value, root.backend.epoch)
                            }
                        }
                    }
                    Component {
                        id: fieldEditor
                        PropertyEditor { field: editor.modelData; backend: root.backend; labelWidth: group.labelWidth }
                    }
                    Component {
                        id: modeButtons
                        Column {
                            spacing: Theme.space.XS
                            Repeater {
                                model: editor.modelData.data.options
                                M.Button {
                                    required property var modelData
                                    objectName: "consumption-mode-" + modelData.value
                                    width: parent.width; height: Math.max(24, label.implicitHeight+4)
                                    text: modelData.label; flat: true; padding: 0
                                    Accessible.role: Accessible.RadioButton
                                    Accessible.checked: root.backend.mode === modelData.value
                                    contentItem: Item {
                                        Rectangle { width: 12; height: 12; radius: 6; y: (parent.height-height)/2
                                            color: "transparent"; border.color: Theme.colors.muted; border.width: 1
                                            Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: Theme.colors.text; visible: root.backend.mode === modelData.value }
                                        }
                                        M.Label { id: label; x: 18; width: parent.width-x; height: parent.height; text: modelData.label; wrapMode: Text.Wrap }
                                    }
                                    onClicked: root.backend.commit("mode", modelData.value, root.backend.epoch)
                                }
                            }
                        }
                    }
                }
            }
            BillsGrid { width: parent.width; backend: root.backend; visible: group.modelData.key === "consumption" && root.backend.mode === "bills" }
        }
    }
}
