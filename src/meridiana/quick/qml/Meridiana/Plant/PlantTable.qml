import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// The strings of Impianto in the one table (r23-tabelle): this file only says the columns and answers the backend;
// M.Table draws, scrolls (both ways: the columns keep their minimum and the table scrolls sideways when narrower),
// selects and cuts the texts with their tooltip.
M.Table {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var strings: backend.strings
    readonly property var inputs: backend.inputs
    readonly property var plantData: backend.data
    // the widths of before (540 px at 13 px, in shares), now the columns' minimums: the same layout when wide enough
    readonly property real least: Theme.type.BODY * 540 / 13
    viewName: "stringsHorizontalScroll"
    rowName: "stringRow"
    cellName: "string-cell-"
    model: strings
    // choosing a string opens «Stringa scelta» above the table in the inspector: at the press, the drag that scrolls
    // the table sideways was lost (test_workbench_journey)
    selectOnPress: false
    Binding on currentIndex { value: root.backend.selected }
    columns: [
        {key: "label", title: backend.tr("String"), minWidth: least * 0.14, weight: 0.14},
        {key: "modules", title: backend.tr("Modules"), numeric: true, minWidth: least * 0.12, weight: 0.12},
        {key: "voc", title: "Uoc", unit: "V", numeric: true, minWidth: least * 0.14, weight: 0.14},
        {key: "vmpp", title: "Umpp", unit: "V", numeric: true, minWidth: least * 0.22, weight: 0.22},
        {key: "stateText", title: backend.tr("State"), minWidth: least * 0.38, weight: 0.38}]
    summary: strings.length + " " + backend.tr("Strings") + " · " + plantData.left + " " + backend.tr("modules in no string")
    onRowActivated: index => backend.selectString(index)
    onRowDoubleClicked: index => { const s = strings[index]; if (s) backend.draw(s.inverter, s.mppt, index) }
    emptyTitle: backend.tr("No strings yet. Draw a string on an input, or ask Meridiana to propose them.")
    emptyActionText: backend.tr("Draw a string")
    onEmptyTriggered: if (inputs.length) { const i = inputs[0]; backend.draw(i.unit, i.mppt, -1) }
}
