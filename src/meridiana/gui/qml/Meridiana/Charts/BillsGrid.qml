import QtQuick
import Meridiana.Controls as M
import Meridiana.Theme
Column {
    id: root
    required property var backend
            visible: root.backend.phaseId === "consumption" && root.backend.mode === "bills"
            spacing: Theme.space.XS
            Row {
                width: parent.width
                M.Label { width: parent.width / (root.backend.billColumns.length + 1); text: "kWh" }
                Repeater { model: root.backend.billColumns; M.Label { required property string modelData; width: parent.width / (root.backend.billColumns.length + 1); text: modelData } }
            }
            Repeater {
                model: root.backend.bills
                Row {
                    required property var modelData
                    required property int index
                    property int month: index
                    property var values: modelData
                    width: parent.width
                    M.Label { width: parent.width / (root.backend.billColumns.length + 1); text: Qt.locale().monthName(parent.month, Locale.ShortFormat); height: Theme.size.CONTROL; verticalAlignment: Text.AlignVCenter }
                    Repeater {
                        model: root.backend.billColumns
                        M.NumberField {
                            required property string modelData
                            objectName: "bill-" + parent.month + "-" + modelData
                            width: parent.width / (root.backend.billColumns.length + 1)
                            value: parent.values[modelData] || 0
                            minimum: 0; maximum: 1e9; decimals: 1
                            onValueEdited: value => root.backend.setBill(parent.month, modelData, value)
                        }
                    }
                }
            }
            Row {
                width: parent.width
                M.Label { width: parent.width / (root.backend.billColumns.length + 1); text: root.backend.labels.total; textStyle: "strong" }
                Repeater { model: root.backend.billColumns; M.CopyLabel {
                    required property string modelData
                    width: parent.width / (root.backend.billColumns.length + 1); text: Number(root.backend.billTotals[modelData]).toLocaleString(Qt.locale(), 'f', 1)
                    textStyle: "strong"
                    copyText: root.backend.labels.total + " " + modelData + ": " + text + " kWh"
                } }
            }
        }
