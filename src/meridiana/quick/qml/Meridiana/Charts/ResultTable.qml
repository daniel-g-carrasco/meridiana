import QtQuick
import Meridiana.Controls as M
import Meridiana.ChartBackend 1.0

// The results as a table, in the one table (r23-tabelle, in place of VirtualResultTable and CommonResultTable): the
// columns are at least 14 characters wide and the table scrolls sideways when they do not fit (the annual matrices,
// only the columns in view made), the rows are made only in view (8.760 hours), headings and total stay.
M.Table {
    id: root
    property var tableData: ({headers: [], rows: [], units: [], totals: []})
    property int decimals: 0
    ChartServices { id: services }
    variant: "view"
    selectionMode: "multiple"
    viewName: "resultTableView"
    headerName: "resultTableHeader"
    totalName: "resultTableTotal"
    function formatted(value) {
        return value === null || value === undefined ? "–" : typeof value === "string" ? value :
            Number(value).toLocaleString(Qt.locale(), 'f', decimals)
    }
    // a column sorts by the raw value ("v<i>") behind the formatted text ("<i>")
    columns: (tableData.headers || []).map((text, i) => ({key: String(i), sortKey: "v" + i, sortable: true, title: text,
        unit: (tableData.units || [])[i] || "", numeric: i > 0, weight: i === 0 ? 1.4 : 1, chars: 14}))
    model: (tableData.rows || []).map(row => {
        const result = {}
        for (let i = 0; i < row.length; i++) { result[String(i)] = formatted(row[i]); result["v" + i] = row[i] }
        return result
    })
    total: (tableData.totals || []).length ? tableData.totals.reduce((row, v, i) => {
        row[String(i)] = i === 0 ? services.labels.total : v === null ? "" : formatted(v); return row
    }, {}) : null
}
