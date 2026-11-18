import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    property var backend
    property var fields: backend ? backend.fields : []
    spacing: Theme.space.S
    Repeater {
        model: root.fields
        delegate: GridLayout {
            id: row
            required property var modelData
            width: root.width
            columns: root.width < 300 || row.modelData.kind === "bool" ? 1 : 2
            columnSpacing: Theme.space.S; rowSpacing: Theme.space.XS
            HoverHandler { onHoveredChanged: root.backend.highlightField(hovered ? row.modelData.key : "") }
            M.Label {
                text: row.modelData.label
                visible: row.modelData.kind !== "bool"
                Layout.preferredWidth: root.width < 300 ? root.width : Math.min(root.width * 0.52, Math.max(...root.fields.filter(f => f.kind !== "bool").map(f => Theme.measureText(f.label).width)))
                wrapMode: Text.WordWrap
            }
            Loader {
                Layout.fillWidth: true
                sourceComponent: row.modelData.kind === "number" ? number : row.modelData.kind === "choice" ? choice : row.modelData.kind === "bool" ? check : text
                Component {
                    id: text
                    M.TextField {
                        objectName: "dialog_" + row.modelData.key
                        text: String(root.backend.state[row.modelData.key] ?? "")
                        onEditingFinished: root.backend.setValue(row.modelData.key, text)
                    }
                }
                Component {
                    id: number
                    M.NumberField {
                        id: numberField
                        objectName: "dialog_" + row.modelData.key
                        value: Number(root.backend.state[row.modelData.key] ?? 0)
                        minimum: row.modelData.minimum
                        maximum: row.modelData.maximum
                        decimals: row.modelData.decimals
                        unit: row.modelData.unit
                        onActiveFocusChanged: root.backend.highlightField(activeFocus ? row.modelData.key : "")
                        readonly property bool proposed: row.modelData.key === "columns" && value === 0 && !activeFocus
                        color: proposed ? "transparent" : Theme.colors.text
                        M.Label {
                            anchors.left: parent.left; anchors.leftMargin: numberField.leftPadding
                            anchors.verticalCenter: parent.verticalCenter
                            visible: numberField.proposed
                            text: root.backend.state.proposedColumns || ""
                        }
                        onValueEdited: value => root.backend.setValue(row.modelData.key, value)
                    }
                }
                Component {
                    id: choice
                    M.ComboBox {
                        objectName: "dialog_" + row.modelData.key
                        options: row.modelData.options
                        value: root.backend.state[row.modelData.key]
                        onChosen: value => root.backend.setValue(row.modelData.key, value)
                    }
                }
                Component {
                    id: check
                    M.CheckBox {
                        objectName: "dialog_" + row.modelData.key
                        text: row.modelData.label
                        checked: root.backend.state[row.modelData.key] || false
                        enabled: !(row.modelData.key === "reserved" && root.backend.state.networkLocked)
                        onToggled: root.backend.setValue(row.modelData.key, checked)
                    }
                }
            }
        }
    }
}
