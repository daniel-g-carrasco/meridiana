import QtQuick
import QtQuick.Controls as C
import QtQuick.Shapes
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
// The bar keeps its lane (R520, `room`), the rows dissolve under heading and total (EdgeFades), the ends rebound
// (M.ScrollBar's Rebound).
// framed: the table in its own outline, Theme.radius.CONTROL round, as a list (R555, Daniel 14/11/2026: «agli angoli
//   arrotondati manca il contorno, i due in alto (l'intestazione ci dipinge sopra) e quello in basso a sinistra (le righe
//   ci dipingono sopra)»): the outline is drawn above heading, rows, fades and total, and the square corners outside
//   its arcs are painted in `outside`, the ground the table stands on, so nothing inside shows past the round corners
//   whatever is chosen, hovered or scrolled under them.
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
    property bool framed: false
    // the first opaque ground above the table (a card, a dialog's window, a page)
    property color outside: _groundAbove()
    function _groundAbove() {
        const revision = Theme.revision
        for (let up = root.parent; up; up = up.parent) {
            const own = up.background !== undefined && up.background !== null ? up.background.color : undefined
            if (own !== undefined && own.a > .99) return own
            if (up.color !== undefined && up.color.a > .99) return up.color
        }
        return Theme.colors.panel
    }
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
    // the empty state's sign (the kit, 21/11/2026: docs/22 of the model, row 9)
    property string emptyIcon: ""
    property string emptyActionText: ""
    // names for the tests and the tools: the view, a row (+ model index), a cell (+ row-column), heading and total
    property string viewName: "tableView"
    property string rowName: ""
    property string cellName: ""
    property string headerName: "tableHeader"
    property string totalName: "tableTotal"
    readonly property alias view: rows
    // the rows made ahead of the ones in view, in the background (ListView's cacheBuffer); 0 for a table that a section
    // makes and takes away at once (Settings > Keyboard): a row still being made when the table goes is a warning
    property alias cacheBuffer: rows.cacheBuffer
    readonly property int count: rows.count
    readonly property color ground: variant === "view" ? Theme.colors.view : Theme.colors.card
    // a heading of one line when no column has a unit (the shortcuts): the line of the units would stand empty
    readonly property bool unitRow: columns.some(col => (col.unit || "") !== "")
    signal rowActivated(int index)
    signal rowDoubleClicked(int index)
    signal emptyTriggered()
    implicitWidth: Theme.size.READING
    implicitHeight: Theme.size.NAV * 8
    // R631, R601: the height that shows every row, for a table laid in a page that already scrolls (a section of a
    // panel): it takes this and never scrolls inside it. At least a row each (the rows not made yet have no height).
    readonly property real wholeHeight: rows.count ? header.height + Math.max(rows.contentHeight, rows.count * rowHeight) + footer.height : implicitHeight
    activeFocusOnTab: true
    Accessible.role: Accessible.Table

    property alias cellCopy: cellCommands
    property string frozenCell: ""
    property string frozenRows: ""
    TextActions { id: cellCommands; readOnly: true; wholeText: root.frozenCell }
    TextActions { id: rowCommands; target: root; popup: valueMenu; readOnly: true; wholeText: root.frozenRows
        canSelectAllOverride: root.selectionMode === "multiple" && root.count > (root.selection.length || (root.currentIndex >= 0 ? 1 : 0))
        selectAllHandler: () => root.selection = Array.from({length:root.count}, (_,i)=>root.sourceOf(i)) }
    function modelRow(index) {
        return !live ? rowsOf[index] : typeof model.get === "function" ? model.get(index) : textEditing.modelRow(model, index)
    }
    function quoted(value) {
        const t = String(value)
        return /[\t\n\r"]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t
    }
    function selectedText() {
        const result = [columns.map(c => quoted((c.title || "") + (c.unit ? " (" + c.unit + ")" : ""))).join("\t")]
        for (let display = 0; display < count; ++display) {
            const source = sourceOf(display)
            if (isSelected(source)) result.push(columns.map(c => quoted(cell(modelRow(source), c))).join("\t"))
        }
        return result.length > 1 ? result.join("\n") : ""
    }
    function copyRows() { frozenRows = selectedText(); rowCommands.execute("copy") }
    function freezeCell(source, column) {
        const col = columns[column]
        frozenCell = col ? cell(modelRow(source), col) + (col.unit ? " " + col.unit : "") : ""
        frozenRows = selectedText()
    }
    Menu {
        id: valueMenu
        onAboutToShow: { rowCommands.begin(); textEditing.activateMenu(rowCommands, valueMenu) }
        onClosed: { textEditing.deactivateMenu(valueMenu); rowCommands.end() }
        readonly property bool targetAvailable: root.visible && root.enabled
        onTargetAvailableChanged: if (!targetAvailable) close()
        MenuItem { text: textEditing.labels.cell; enabled: cellCommands.allowed("copy"); onTriggered: cellCommands.execute("copy") }
        MenuItem { text: textEditing.labels.rows; enabled: rowCommands.allowed("copy"); onTriggered: rowCommands.execute("copy") }
        MenuItem { text: textEditing.labels.selectAll; enabled: rowCommands.allowed("selectAll"); onTriggered: rowCommands.execute("selectAll") }
    }

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
    Keys.onShortcutOverride: event => { event.accepted = event.matches(StandardKey.Copy) || event.matches(StandardKey.SelectAll) }
    Keys.onPressed: event => {
        if (event.matches(StandardKey.Copy)) { copyRows(); event.accepted = true; return }
        if (event.matches(StandardKey.SelectAll)) {
            if (selectionMode === "multiple") selection = Array.from({length:count}, (_,i)=>sourceOf(i)); event.accepted = true; return
        }
        if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) {
            freezeCell(currentIndex, 0); valueMenu.popup(root, 0, header.height); event.accepted = true; return
        }
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

    Rectangle { anchors.fill: parent; color: root.ground; visible: root.variant === "view" || root.framed
        radius: root.framed ? Theme.radius.CONTROL : 0 }

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

    Rectangle { id: header; objectName: root.headerName; width: parent.width
        height: root.unitRow ? Theme.size.NAV + Theme.text.caption.size + Theme.space.XS : Theme.size.NAV
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
                Column { id: titles; y: root.unitRow ? Theme.space.S : Math.round((header.height - height) / 2); width: parent.width
                    Cell { column: heading.column; headed: true; x: 0; text: heading.spec.title || ""; textStyle: "secondary"
                        rightPadding: Theme.space.M + (heading.sorted ? Theme.space.L : 0) }
                    Cell { column: heading.column; headed: true; x: 0; text: heading.spec.unit || ""; textStyle: "caption"; visible: root.unitRow }
                }
                Arrow { visible: heading.sorted; direction: root.sortAscending ? "up" : "down"; width: Theme.icon.CONTROL; height: Theme.icon.CONTROL     // R592
                    anchors.right: parent.right; anchors.rightMargin: Theme.space.S; y: titles.y }
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
            C.ContextMenu.menu: valueMenu
            C.ContextMenu.onRequested: position => {
                root.forceActiveFocus(Qt.PopupFocusReason)
                let column = 0
                while (column + 1 < root.columns.length && root.columnLeft(column + 1) <= position.x) ++column
                root.freezeCell(row.source, column)
            }
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
                        height: parent ? parent.height : 0; verticalAlignment: Text.AlignVCenter     // no parent yet while it is made
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
    EdgeFades { flickable: rows; barRoom: tableBar.room; spansSurface: false }   // closed sides: the shadow (the kit)
    Rectangle { id: footer; objectName: root.totalName; anchors.bottom: parent.bottom; width: parent.width; clip: true
        height: (root.total || root.summary) && rows.count ? root.rowHeight : 0; visible: height > 0; color: Theme.colors.field
        readonly property real contentX: rows.contentX
        Label { id: summaryText; visible: root.summary !== ""; width: root.available; height: parent.height; leftPadding: Theme.space.M
            rightPadding: Theme.space.M; verticalAlignment: Text.AlignVCenter; textStyle: "strong"; text: root.summary; elide: Text.ElideRight
            HoverHandler { onHoveredChanged: if (hovered) root._tipCell = summaryText; else if (root._tipCell === summaryText) root._tipCell = null } }
        Repeater { model: root.summary ? 0 : root.columnsInView
            Cell { required property int index
                column: root.firstColumn + index; headed: true
                height: parent ? parent.height : 0; verticalAlignment: Text.AlignVCenter     // no parent yet while it is made
                textStyle: "strong"; text: root.total ? root.cell(root.total, spec) : "" }
        }
    }
    EmptyState { anchors.fill: parent; visible: rows.count === 0; title: root.emptyTitle; description: root.emptyDescription; iconName: root.emptyIcon
        actionText: root.emptyActionText; onTriggered: root.emptyTriggered() }
    // framed: the four square corners outside the round ones, in the ground outside, then the outline over everything
    Shape { id: corners; objectName: "tableCorners"; anchors.fill: parent; z: 20; visible: root.framed
        preferredRendererType: Shape.CurveRenderer
        readonly property real r: Theme.radius.CONTROL
        ShapePath { strokeWidth: -1; fillColor: root.outside; fillRule: ShapePath.OddEvenFill
            PathSvg { readonly property real w: root.width
                readonly property real h: root.height
                readonly property real r: corners.r
                path: `M0,0 H${w} V${h} H0 Z M${r},0 H${w - r} A${r},${r} 0 0 1 ${w},${r} V${h - r} A${r},${r} 0 0 1 ${w - r},${h}`
                      + ` H${r} A${r},${r} 0 0 1 0,${h - r} V${r} A${r},${r} 0 0 1 ${r},0 Z` }
        }
    }
    Rectangle { objectName: "tableFrame"; anchors.fill: parent; z: 21; visible: root.framed; color: "transparent"
        radius: Theme.radius.CONTROL; border.width: Theme.line.HAIR; border.color: Theme.colors.line }
}
