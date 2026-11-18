import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
// r23-tabelle (F5): the one table of the Quick interface, in place of PlantTable (the strings of Impianto),
// VirtualResultTable and CommonResultTable (the results) and the delegate of the comparison written in CommandDialogs.
//
// columns: [{key, title, unit, numeric, weight, minWidth, chars, wrap, sortable, sortKey}]
//   a column is at least `minWidth` px wide (or `chars` characters of the body text, 8 when neither is given) and takes
//   its `weight` of the room left; when the minimums do not fit, the table scrolls sideways and only the columns in
//   view are made (the annual matrices of 366 days). A text too long ends with dots and is whole in the tooltip;
//   `wrap: true` lets it go on more lines instead (the row grows with the cells in view).
// model: a JS array of objects, or a live model (QAbstractListModel, ListModel: the columns' keys are its roles; it
//   sorts itself); rows are made only while in view (ListView, reuseItems).
// sorting: a click on a `sortable` heading sorts by it, a second click turns the order; `sortKey` reads another field
//   (the raw number behind a formatted text).
// selection (docs/quick/regole.md, R529): with selectionMode "multiple" a click starts again with that row, Shift+click
//   adds, Ctrl+click toggles; "single" (the default) keeps one row; "none" none. Indices are always of the model.
// variant: "card" (on a card) or "view" (on the ground of a view: the results).
// The bar keeps its lane (R520, `room`), the rows fade under heading and total (EdgeFades, table), the ends rebound
// (M.ScrollBar's Rebound).
Item {
    id: root
    property var columns: []
    property var model: []
    property int currentIndex: -1
    property var selection: []
    property string selectionMode: "single"
    // a row is chosen at the press (the Widgets lists); false: at the tap, when choosing reshapes what is around the
    // table (the strings: «Stringa scelta» opens above it) and would take the drag that scrolls it away
    property bool selectOnPress: true
    property string variant: "card"
    property int sortColumn: -1
    property bool sortAscending: true
    property var total: null
    // one line under the rows in place of the totals per column (the strings: how many, the modules left out)
    property string summary: ""
    property real rowHeight: Theme.size.NAV
    // the cell drawn strong (the best of a comparison): a function (row, column) -> bool
    property var emphasis: null
    property string emptyTitle: ""
    property string emptyDescription: ""
    property string emptyActionText: ""
    // names for the tests and the tools: the view, a row (+ model index), a cell (+ row-column), heading and total
    property string viewName: "tableView"
    property string rowName: ""
    property string cellName: ""
    property string headerName: "tableHeader"
    property string totalName: "tableTotal"
    readonly property alias view: rows
    readonly property int count: rows.count
    readonly property color ground: variant === "view" ? Theme.colors.view : Theme.colors.card
    signal rowActivated(int index)
    signal rowDoubleClicked(int index)
    signal emptyTriggered()
    implicitWidth: Theme.size.READING
    implicitHeight: Theme.size.NAV * 8
    activeFocusOnTab: true
    Accessible.role: Accessible.Table

    // ---- columns: widths, lefts, the ones in view
    function _minWidth(col) {
        return col.minWidth !== undefined ? col.minWidth : (col.chars || 8) * Theme.type.BODY * 0.62 + 2 * Theme.space.M
    }
    readonly property real available: Math.max(0, width - tableBar.room)
    readonly property var widths: {
        const mins = columns.map(col => _minWidth(col))
        const least = mins.reduce((a, b) => a + b, 0)
        const weights = columns.map(col => col.weight || 1)
        const sum = Math.max(1e-6, weights.reduce((a, b) => a + b, 0))
        const extra = Math.max(0, available - least)
        return mins.map((m, i) => m + extra * weights[i] / sum)
    }
    readonly property var lefts: {
        let x = 0
        const out = []
        for (const w of widths) { out.push(x); x += w }
        out.push(x)
        return out
    }
    readonly property real contentWidth: Math.max(available, lefts[lefts.length - 1] || 0)
    function columnWidth(index) { return widths[index] || 0 }
    function columnLeft(index) { return lefts[index] || 0 }
    readonly property int firstColumn: {
        const x = rows.contentX
        let i = 0
        while (i < columns.length - 1 && lefts[i + 1] <= x) i++
        return i
    }
    // a fixed number of cells per row while the width stays (the Repeater is not made again at each column scrolled)
    readonly property int columnsInView: {
        if (!columns.length) return 0
        const narrowest = Math.max(1, Math.min.apply(null, widths))
        return Math.min(columns.length, Math.ceil(available / narrowest) + 1)
    }
    function cell(row, column) {
        const value = row && column ? row[column.key] : undefined
        return value === undefined || value === null ? "" : String(value)
    }

    // ---- order (sorting) and selection, in model indices
    readonly property bool live: model !== null && model !== undefined && typeof model === "object" && model.length === undefined
    readonly property var rowsOf: !live && model && model.length !== undefined ? model : []
    readonly property var order: {
        const n = rowsOf.length
        const out = Array.from({length: n}, (_, i) => i)
        const col = columns[sortColumn]
        if (!col || col.sortable !== true) return out
        const key = col.sortKey || col.key, sign = sortAscending ? 1 : -1
        out.sort((a, b) => {
            const x = rowsOf[a] ? rowsOf[a][key] : null, y = rowsOf[b] ? rowsOf[b][key] : null
            if (x === y) return a - b
            if (x === null || x === undefined) return 1
            if (y === null || y === undefined) return -1
            const c = typeof x === "number" && typeof y === "number" ? x - y
                    : String(x).localeCompare(String(y), Qt.locale().name, {numeric: true})
            return c === 0 ? a - b : sign * c
        })
        return out
    }
    function sortBy(index) {
        if (index === sortColumn) sortAscending = !sortAscending
        else { sortColumn = index; sortAscending = true }
    }
    function isSelected(index) {
        if (index < 0) return false
        return selectionMode === "multiple" ? selection.indexOf(index) >= 0 || (selection.length === 0 && index === currentIndex)
                                            : selectionMode === "single" && index === currentIndex
    }
    function displayOf(index) { return live ? index : order.indexOf(index) }
    function sourceOf(at) { return live ? at : order[at] }
    function select(index, modifiers) {
        if (index < 0 || index >= rows.count || selectionMode === "none") return
        const mods = modifiers || Qt.NoModifier
        if (selectionMode === "multiple" && (mods & (Qt.ControlModifier | Qt.ShiftModifier))) {
            const next = selection.length ? selection.slice() : (currentIndex >= 0 ? [currentIndex] : [])
            const own = next.indexOf(index)
            if (mods & Qt.ControlModifier) { if (own >= 0) next.splice(own, 1); else next.push(index) }
            else if (own < 0) next.push(index)
            selection = next
        } else {
            selection = selectionMode === "multiple" ? [index] : []
        }
        currentIndex = index
        rowActivated(index)
    }
    function step(delta) {
        if (!rows.count) return
        const here = currentIndex >= 0 ? displayOf(currentIndex) : -1
        select(sourceOf(Math.max(0, Math.min(rows.count - 1, here + delta))))
    }
    onCurrentIndexChanged: if (currentIndex >= 0) {
        const at = displayOf(currentIndex)
        if (at >= 0) rows.positionViewAtIndex(at, ListView.Contain)
    }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Home) { if (rows.count) select(sourceOf(0)); event.accepted = true }
        else if (event.key === Qt.Key_End) { if (rows.count) select(sourceOf(rows.count - 1)); event.accepted = true }
    }
    Keys.onDownPressed: step(1)
    Keys.onUpPressed: step(-1)
    Keys.onReturnPressed: if (currentIndex >= 0) rowActivated(currentIndex)

    // ---- one tooltip for every text cut short (a ToolTip in each cell would be a popup per cell)
    property Item _tipCell: null
    ToolTip { parent: root._tipCell || root; visible: root._tipCell !== null && root._tipCell.truncated === true
        text: root._tipCell ? root._tipCell.text : "" }

    Rectangle { anchors.fill: parent; color: root.ground; visible: root.variant === "view" }

    component Cell: Label {
        id: cellText
        required property int column
        property bool headed: false
        readonly property var spec: root.columns[column] || ({})
        x: root.columnLeft(column) - (headed ? rows.contentX : 0)
        width: root.columnWidth(column)
        visible: column < root.columns.length
        leftPadding: Theme.space.M
        rightPadding: Theme.space.M
        horizontalAlignment: spec.numeric ? Text.AlignRight : Text.AlignLeft
        wrapMode: spec.wrap ? Text.Wrap : Text.NoWrap
        elide: spec.wrap ? Text.ElideNone : Text.ElideRight
        HoverHandler { onHoveredChanged: if (hovered) root._tipCell = cellText; else if (root._tipCell === cellText) root._tipCell = null }
    }

    Rectangle { id: header; objectName: root.headerName; width: parent.width; height: Theme.size.NAV + Theme.text.caption.size + Theme.space.XS
        color: Theme.colors.field; visible: rows.count > 0; clip: true
        readonly property real contentX: rows.contentX
        Repeater { model: root.columnsInView
            Item { id: heading; required property int index
                readonly property int column: root.firstColumn + index
                readonly property var spec: root.columns[column] || ({})
                readonly property bool sortable: spec.sortable === true
                readonly property bool sorted: sortable && root.sortColumn === column
                x: root.columnLeft(column) - rows.contentX; width: root.columnWidth(column); height: header.height
                visible: column < root.columns.length
                Column { y: Theme.space.S; width: parent.width
                    Cell { column: heading.column; headed: true; x: 0; text: heading.spec.title || ""; textStyle: "secondary"
                        rightPadding: Theme.space.M + (heading.sorted ? Theme.space.L : 0) }
                    Cell { column: heading.column; headed: true; x: 0; text: heading.spec.unit || ""; textStyle: "caption" }
                }
                Icon { visible: heading.sorted; iconName: "chevron-right"; rotation: root.sortAscending ? -90 : 90
                    anchors.right: parent.right; anchors.rightMargin: Theme.space.S; y: Theme.space.S }
                TapHandler { enabled: heading.sortable; onTapped: root.sortBy(heading.column) }
                HoverHandler { enabled: heading.sortable; cursorShape: Qt.PointingHandCursor }
            }
        }
    }
    ListView { id: rows; objectName: root.viewName; anchors.top: header.bottom; anchors.bottom: footer.top; width: parent.width; clip: true
        model: root.live ? root.model : root.order.length; reuseItems: true
        contentWidth: root.contentWidth
        flickableDirection: Flickable.AutoFlickIfNeeded
        boundsBehavior: Flickable.StopAtBounds
        delegate: Rectangle { id: row; required property int index; required property var model
            readonly property int source: root.live ? index : root.order[index] === undefined ? -1 : root.order[index]
            readonly property var rowData: root.live ? model : source >= 0 ? root.rowsOf[source] : null
            objectName: root.rowName ? root.rowName + source : ""
            width: root.contentWidth
            height: Math.max(root.rowHeight, cells.tallest + Theme.space.S)
            color: root.isSelected(source) ? Theme.colors.select_bg : hover.hovered ? Theme.colors.hover : "transparent"
            Accessible.role: Accessible.Row
            Accessible.selected: root.isSelected(source)
            Accessible.name: root.columns.map(col => root.cell(rowData, col)).join(", ")
            Item { id: cells; anchors.fill: parent
                property real tallest: 0
                function measure() {
                    let h = 0
                    for (const c of children) if (c.visible && c.spec && c.spec.wrap) h = Math.max(h, c.implicitHeight)
                    tallest = h
                }
                Repeater { model: root.columnsInView
                    Cell { required property int index
                        column: root.firstColumn + index
                        objectName: root.cellName ? root.cellName + row.source + "-" + column : ""
                        height: parent.height; verticalAlignment: Text.AlignVCenter
                        text: root.cell(row.rowData, spec)
                        textStyle: typeof root.emphasis === "function" && row.rowData && root.emphasis(row.rowData, spec) ? "strong" : "body"
                        onImplicitHeightChanged: cells.measure()
                    }
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line_soft }
            HoverHandler { id: hover }
            TapHandler { id: tap
                // the row is chosen at the press, as the Widgets lists do (test_fidelity), with the press's modifiers;
                // at the tap when selectOnPress is false
                onPressedChanged: if (pressed) {
                    root.forceActiveFocus(Qt.MouseFocusReason)
                    if (root.selectOnPress) root.select(row.source, tap.point.modifiers)
                }
                onTapped: if (!root.selectOnPress) root.select(row.source, tap.point.modifiers)
                onDoubleTapped: root.rowDoubleClicked(row.source)
            }
        }
        T.ScrollBar.vertical: ScrollBar { id: tableBar; fades: false }
        T.ScrollBar.horizontal: ScrollBar { fades: false }
    }
    EdgeFades { flickable: rows; table: true; ground: root.ground; barRoom: tableBar.room }
    Rectangle { id: footer; objectName: root.totalName; anchors.bottom: parent.bottom; width: parent.width; clip: true
        height: (root.total || root.summary) && rows.count ? root.rowHeight : 0; visible: height > 0; color: Theme.colors.field
        readonly property real contentX: rows.contentX
        Label { id: summaryText; visible: root.summary !== ""; width: root.available; height: parent.height; leftPadding: Theme.space.M
            rightPadding: Theme.space.M; verticalAlignment: Text.AlignVCenter; textStyle: "strong"; text: root.summary; elide: Text.ElideRight
            HoverHandler { onHoveredChanged: if (hovered) root._tipCell = summaryText; else if (root._tipCell === summaryText) root._tipCell = null } }
        Repeater { model: root.summary ? 0 : root.columnsInView
            Cell { required property int index
                column: root.firstColumn + index; headed: true
                height: parent.height; verticalAlignment: Text.AlignVCenter
                textStyle: "strong"; text: root.total ? root.cell(root.total, spec) : "" }
        }
    }
    EmptyState { anchors.fill: parent; visible: rows.count === 0; title: root.emptyTitle; description: root.emptyDescription
        actionText: root.emptyActionText; onTriggered: root.emptyTriggered() }
}
