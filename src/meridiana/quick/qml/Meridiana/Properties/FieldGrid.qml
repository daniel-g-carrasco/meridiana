import QtQuick
import QtQuick.Layouts
import Meridiana.Controls as M
import Meridiana.Theme

Column {
    id: root
    property var rowNames: []
    property var columns: []
    property var values: []
    property string unit: ""
    property int decimals: 0
    property string totalLabel: ""
    signal edited(var values)
    spacing: Theme.space.XS
    function valueAt(i, column) { return values[i] && values[i][column] ? values[i][column] : 0 }
    function editCell(i, column, value) {
        const updated = values.map(row => Object.assign({}, row))
        while (updated.length < rowNames.length) updated.push({})
        updated[i][column] = value
        values = updated
        edited(updated)
    }
    GridLayout {
        width: parent.width
        columns: root.columns.length + 1
        columnSpacing: Theme.space.S
        rowSpacing: Theme.space.XS
        Item { Layout.preferredWidth: 50 }
        Repeater { model: root.columns; M.Label { required property var modelData; text: modelData; textStyle: "secondary"; Layout.fillWidth: true } }
        Repeater {
            model: root.rowNames.length * (root.columns.length + 1)
            Loader {
                required property int index
                property int row: Math.floor(index / (root.columns.length + 1))
                property int column: index % (root.columns.length + 1) - 1
                Layout.fillWidth: true
                sourceComponent: column < 0 ? rowLabel : cell
                Component { id: rowLabel; M.Label { text: root.rowNames[row]; textStyle: "secondary" } }
                Component { id: cell; M.NumberField { value: root.valueAt(row, root.columns[column]); unit: root.unit; decimals: root.decimals
                        minimum: 0; maximum: 1e9; onValueEdited: value => root.editCell(row, root.columns[column], value) } }
            }
        }
        M.Label { text: root.totalLabel; textStyle: "strong" }
        Repeater { model: root.columns
            M.Label { required property var modelData; textStyle: "strong"; Layout.fillWidth: true
                text: root.values.reduce((sum, row) => sum + (row[modelData] || 0), 0).toLocaleString(Qt.locale("it_IT"), 'f', 0) }
        }
    }
}
