import QtQuick
import QtQuick.Controls as C
import QtQuick.Layouts
import Meridiana.Controls as M
import Meridiana.Theme
import "TitleTools.js" as Header

Rectangle {
    id: root
    required property var backend
    objectName: "checks-page"
    color: Theme.colors.panel
    implicitWidth: M.ControlMetrics.pageSize.checks.width
    implicitHeight: M.ControlMetrics.pageSize.checks.height
    property int menuIndex: -1
    property bool menuHasFix: false
    property string menuFixText: ""
    property bool menuHasPlace: false
    property bool askEnabled: true
    property bool keyboardMode: false
    // R663 (Daniel 16/11/2026: «cos'è questa nuova evidenziatura ... che non è possibile togliere in nessun modo tipo
    // esc, click fuori, e non è possibile muovere con tab?»): the check opened from its mark («This object») is shown
    // selected until Esc, a click on an empty place of the list, or another check chosen
    property bool openedShown: true
    function dropOpened() { openedShown = false }
    Connections {
        target: typeof shell !== "undefined" ? shell : null
        function onEscapeRequested() { root.dropOpened() }
    }
    property var titlePanel: null
    // R632: in a group of docked cards the tabs stand where the title stood (DockPanel.headLead)
    readonly property real titleWidth: (titlePanel && titlePanel.headLead !== undefined ? titlePanel.headLead
                                        : Theme.measureText(backend.title, "title").width) + 24
    M.KeyedRows { id: rowsModel
        keyOf: row => row.header ? "group|"+row.key : "item|"+row.itemIndex
        rows: root.backend.rows
        onSynced: list.forceLayout() }
    readonly property real sourceWidth: {
        const revision = Theme.revision
        let wanted = 0
        for (const source of backend.columns.sources)
            wanted = Math.max(wanted, Theme.measureText(source, "secondary").width)
        return Math.min(width * .28, wanted ? wanted + 16 : 0)
    }
    readonly property real actionWidth: (backend.columns.fix ? Theme.measureText(backend.labels.fix).width + 24 : 0)
                                       + (backend.columns.place ? 30 : 0) + 14
    function focusIndex(itemIndex) {
        // KeyedRows already holds the rows in JS. Reading the QVariantList on
        // every index converts the entire Python list each time (quadratic).
        const rows = rowsModel.rows
        for (let i = 0; i < rows.length; ++i) {
            if (!rows[i].header && rows[i].itemIndex === itemIndex) {
                list.currentIndex = i
                const item = list.currentItem
                if (!item || item.y < list.contentY || item.y + item.height > list.contentY + list.height)
                    list.positionViewAtIndex(i, ListView.Contain)
                return
            }
        }
    }
    function viewTips(item) {
        // Shared Segments currently exposes only text as its button tip.
        // Supply the existing Widgets explanation until it accepts model.tip.
        if (item.tip !== undefined) item.tip = root.backend.labels.viewsTip
        for (const child of item.children) viewTips(child)
    }
    Connections {
        target: root.backend
        function onScrollRequested(index) { root.focusIndex(index); root.openedShown = true }
    }
    ColumnLayout {
        id: columns
        anchors.fill: parent
        anchors.topMargin: root.titlePanel ? Math.max(0, toolsRow.height - Theme.size.CONTROL) : toolsRow.height + Theme.space.S
        spacing: Theme.space.S
        Item {
            id: toolsRow
            objectName: "checks-tools"
            parent: root.titlePanel || root
            x: root.titlePanel ? 12 : Theme.space.M
            y: root.titlePanel ? Theme.space.XS : 0
            z: 100
            width: Math.max(160, parent.width - x - (root.titlePanel ? 36 : Theme.space.M))
            readonly property var arrangement: Header.plan(width, root.titlePanel ? root.titleWidth - 12 : 0, Theme.size.CHIP+4,
                [{key:"views", preferred:viewsTrack.implicitWidth, minimum:120, height:viewsTrack.height},
                 {key:"counts", preferred:countsRow.implicitWidth, minimum:countsRow.implicitWidth, height:countsRow.height},
                 {key:"filters", preferred:filtersRow.width, minimum:filtersRow.width, height:filtersRow.height, align:"end"}],
                20, Theme.space.M, Theme.space.XS)
            height: arrangement.height
            M.Segments {
                id: viewsTrack
                objectName: "checks-views"
                x: toolsRow.arrangement.rectangles.views.x; y: toolsRow.arrangement.rectangles.views.y
                width: toolsRow.arrangement.rectangles.views.width
                height: implicitHeight
                model: root.backend.views
                currentIndex: root.backend.views.findIndex(view => view.key === root.backend.view)
                onActivated: index => root.backend.setView(root.backend.views[index].key)
                Component.onCompleted: root.viewTips(viewsTrack)
            }
            Row {
                id: countsRow
                objectName: "checks-counts"
                x: toolsRow.arrangement.rectangles.counts.x; y: toolsRow.arrangement.rectangles.counts.y
                spacing: Theme.space.S
                Repeater {
                    model: ["fail", "warn", "info", "ok"]
                    M.Pill {
                        required property string modelData
                        readonly property int count: root.backend.counts[modelData]
                        objectName: "checks-filter-" + modelData
                        variant: "count"
                        level: modelData
                        text: count.toString()
                        enabled: count > 0                  // R664: nought to count, not a button
                        focusPolicy: Qt.StrongFocus
                        // R664: what the click does, and how many
                        tip: (checked ? root.backend.labels.hideLevel : root.backend.labels.showLevel)
                             .replace("{level}", root.backend.labels.levels[modelData]) + " (" + count + ")"
                        checked: root.backend.shownLevels.indexOf(modelData) >= 0
                        onClicked: root.backend.toggleLevel(modelData)
                    }
                }
            }
            // R664 (Daniel 16/11/2026: «non dovrebbero essere linguette ma tasti»): two toggles, each on its own, the
            // common button that stays pressed while it is on (M.Button flat and active), no frame that made a choice
            // of the two
            Item {
                id: filtersRow
                objectName: "checks-scopes"
                x: toolsRow.arrangement.rectangles.filters.x; y: toolsRow.arrangement.rectangles.filters.y
                // the place the head's arrangement keeps for them, as tall as the counts' row with its air
                width: scopeButtons.implicitWidth; height: Theme.size.CHIP + 2 * Theme.space.XXS
                Row { id: scopeButtons; y: Theme.space.XXS; spacing: Theme.space.XS
                    M.Button { objectName: "checks-phase"; text: root.backend.labels.phase; flat: true
                        tip: root.backend.labels.phaseTip; height: Theme.size.CHIP
                        active: root.backend.phaseOnly; onClicked: root.backend.setPhaseOnly(!root.backend.phaseOnly) }
                    M.Button { objectName: "checks-object"; text: root.backend.labels.object; flat: true
                        tip: root.backend.labels.objectTip; height: Theme.size.CHIP
                        active: root.backend.objectOnly; onClicked: root.backend.setObjectOnly(!root.backend.objectOnly) }
                }
            }
            M.Button { objectName: "checks-notes"; iconName: "copy_notes"; flat: true
                x: toolsRow.arrangement.rectangles.copy.x; y: toolsRow.arrangement.rectangles.copy.y
                width: 20; height: 20; padding: Theme.space.XXS
                tip: root.backend.labels.copyNotesTip; onClicked: root.backend.copyNotes() }
        }
        // R637: what the card holds at its margins (Shell/DockPanel.qml), no margins of its own
        M.Label {
            Layout.fillWidth: true
            visible: text !== ""
            text: root.backend.error || root.backend.summary
            wrapMode: Text.Wrap
        }
        Rectangle {
            Layout.fillWidth: true
            visible: !!root.backend.preview.text
            implicitHeight: previewContents.implicitHeight + 2 * Theme.space.S
            color: Theme.colors.field
            radius: Theme.radius.CONTROL
            RowLayout {
                id: previewContents
                anchors.fill: parent; anchors.margins: Theme.space.S
                M.ReadableText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.backend.preview.text || "" }
                M.Button { objectName: "checks-preview-keep"; text: root.backend.preview.keep || ""; onClicked: root.backend.answerPreview(true) }
                M.Button { objectName: "checks-preview-drop"; text: root.backend.preview.drop || ""; onClicked: root.backend.answerPreview(false) }
            }
        }
        ListView {
            id: list
            objectName: "checks-list"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: emptyLabel.visible ? emptyLabel.implicitHeight + 24 : 32
            clip: true
            // r24-fasi: no reuseItems here. Tried (studio 41, S6): a reused row kept its old place and text (a row
            // shown twice, quick/proprieta/test_checks) and a binding loop on the row's width (test_fidelity)
            model: rowsModel.model
            onModelChanged: root.focusIndex(root.backend.currentIndex)
            onCurrentIndexChanged: {
                if (currentIndex >= 0 && currentIndex < root.backend.rows.length) {
                    const row = root.backend.rows[currentIndex]
                    if (!row.header) { root.backend.selectRow(row.itemIndex); root.openedShown = true }
                }
            }
            // R663: a click where there is no row lets the check opened go
            TapHandler { onTapped: function(point) {
                if (list.indexAt(point.position.x + list.contentX, point.position.y + list.contentY) < 0) root.dropOpened() } }
            // R663: Esc lets the check opened go here first, before the window's Esc
            Keys.onShortcutOverride: function(event) {
                event.accepted = event.key === Qt.Key_Escape && root.openedShown && root.backend.objectOnly }
            spacing: 0
            focus: true
            keyNavigationEnabled: true
            boundsBehavior: Flickable.StopAtBounds
            // R590: the veils are the bar's, M.EdgeFades; R637: the bar centred in the card's margin at the list's right
            C.ScrollBar.vertical: M.ScrollBar { id: listBar; parent: root; flickable: list
                inMargin: true; x: columns.x + list.x + list.width; y: columns.y + list.y; height: list.height }
            Keys.onPressed: function(event) {
                root.keyboardMode = true
                const row = currentIndex >= 0 && currentIndex < count ? root.backend.rows[currentIndex] : null
                if (event.key === Qt.Key_Escape && root.backend.preview.text) {
                    root.backend.answerPreview(false); event.accepted = true; return
                }
                if (event.key === Qt.Key_Escape && root.openedShown && root.backend.objectOnly) {
                    root.dropOpened(); event.accepted = true; return
                }
                // R663: Tab and Shift+Tab go from a check to the next one; past the last, the focus goes on
                if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
                    const step = event.key === Qt.Key_Tab ? 1 : -1
                    for (let i = currentIndex + step; i >= 0 && i < count; i += step) {
                        if (!root.backend.rows[i].header) {
                            currentIndex = i; positionViewAtIndex(i, ListView.Contain); event.accepted = true; return
                        }
                    }
                    return
                }
                if (!row) return
                if (row.header) {
                    if (event.key === Qt.Key_Space || (event.key === Qt.Key_Left && row.expanded)
                            || (event.key === Qt.Key_Right && !row.expanded)) {
                        const key = row.key
                        root.backend.toggleGroup(key)
                        for (let i = 0; i < root.backend.rows.length; ++i)
                            if (root.backend.rows[i].header && root.backend.rows[i].key === key) currentIndex = i
                        event.accepted = true
                    }
                } else {
                    if (event.key === Qt.Key_Space) { root.backend.toggleDetail(row.itemIndex); event.accepted = true }
                    else if ((event.key === Qt.Key_Right && !row.expanded) || (event.key === Qt.Key_Left && row.expanded)) {
                        root.backend.toggleDetail(row.itemIndex); event.accepted = true
                    }
                    else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        root.backend.showPlace(row.itemIndex); event.accepted = true
                    } else if (event.key === Qt.Key_Period && (event.modifiers & Qt.ControlModifier)) {
                        root.backend.requestFix(row.itemIndex); event.accepted = true
                    } else if (event.key === Qt.Key_C && (event.modifiers & Qt.ControlModifier)) {
                        root.backend.copyText(row.itemIndex); event.accepted = true
                    }
                }
            }
            delegate: Item {
                id: delegate
                objectName: modelData.header ? "checks-group-" + modelData.key : "checks-row-" + modelData.itemIndex
                required property int index
                required property string rowKey
                readonly property var rowNow: rowsModel.byKey[rowKey]
                // A row taken away that the ListView keeps (its current item, index -1) is not drawn: it stayed behind the
                // new rows, its arrow out at the left of the card (R450, photo of 06/11).
                visible: index >= 0
                // the last row seen, a value and not a binding: bound to rowNow it went undefined with it when the row
                // left byKey, and the delegate still in the list threw on every one of its bindings
                property var lastRow: undefined
                Component.onCompleted: if (rowNow !== undefined) lastRow = rowNow
                onRowNowChanged: if (rowNow !== undefined) lastRow = rowNow
                // made before its key reads a row (an empty row then, not undefined: no binding throws)
                readonly property var modelData: rowNow !== undefined ? rowNow : (lastRow !== undefined ? lastRow : ({header: false, expanded: false, level: "", text: ""}))
                width: list.width
                height: modelData.header ? header.height + (index === 0 ? 0 : Theme.space.XL)
                                        : rowContents.implicitHeight
                Item {
                    id: rowBackground
                    visible: !delegate.modelData.header
                    anchors.fill: parent
                    clip: true
                    // ui/checks_page._card_slice extends the rounded rectangle
                    // beyond joined edges, then clips it. Never paint over its sides.
                    Rectangle {
                        objectName: delegate.opened ? "checkOpened" : ""
                        y: delegate.modelData.first ? 0 : -Theme.radius.CONTROL
                        width: parent.width
                        height: parent.height + (delegate.modelData.first ? 0 : Theme.radius.CONTROL)
                                              + (delegate.modelData.last ? 0 : Theme.radius.CONTROL)
                        radius: Theme.radius.CONTROL
                        color: delegate.opened ? Theme.colors.select_bg : Theme.colors.card
                        border.width: delegate.opened ? 0 : Theme.line.HAIR; border.color: Theme.colors.line
                        // R555 (10), R663 (Daniel 16/11/2026: «come mai per l'evidenziatura non hai fatto cambio del
                        // colore di riempimento?»): the check opened from an object's mark («This object») is selected
                        // as a row of the program's lists, the ground `select_bg`; the pointer over it stays its layer
                        Rectangle { anchors.fill: parent; anchors.margins: 1; radius: parent.radius
                            color: cardHover.hovered || (list.activeFocus && root.keyboardMode && list.currentIndex === delegate.index)
                                   ? Theme.colors.hover : "transparent" }
                    }
                    Rectangle { visible: !delegate.modelData.last && !delegate.opened; x: .5; y: parent.height-1
                        width: parent.width-1; height: 1; color: Theme.colors.line }
                }
                HoverHandler { id: cardHover }
                RowLayout {
                    id: header
                    visible: delegate.modelData.header
                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                    height: Math.max(26, Math.ceil(Theme.measureText("Ag", "body").height) + 10)
                    spacing: Theme.space.S
                    Item { width: 31; height: 16
                        M.Chevron { x: 1; y: 1; open: delegate.modelData.expanded; width: 14; height: 14 }
                    }
                    M.Icon { visible: !!delegate.modelData.kind
                        iconName: ({building:"building", subfield:"subfield", exclusion:"exclusion", prop:"object_3d", site:"site"})[delegate.modelData.kind] || "site"
                        Layout.preferredWidth: 16; Layout.preferredHeight: 16
                        color: Theme.colors.kind[delegate.modelData.kind] || Theme.colors.text }
                    M.CheckMark { objectName: delegate.modelData.header ? "checks-group-symbol-" + delegate.modelData.key : ""
                        visible: !delegate.modelData.kind; symbols: root.backend.symbols; level: delegate.modelData.level
                        Layout.preferredWidth: 16; Layout.preferredHeight: 16 }
                    Item { width: 4; height: 1 }
                    M.Label { objectName: delegate.modelData.header ? "checks-group-text-" + delegate.modelData.key : ""
                        text: delegate.modelData.text; textStyle: "label"; elide: Text.ElideRight; Layout.maximumWidth: list.width * .6 }
                    M.Label { text: delegate.modelData.header ? "·  " + delegate.modelData.count : ""; textStyle: "secondary" }
                    Item { Layout.fillWidth: true }
                    Repeater {
                        model: delegate.modelData.header && (root.backend.view === "object" || root.backend.view === "area") ? ["fail", "warn", "info", "ok"] : []
                        Row {
                            required property string modelData
                            spacing: M.ControlMetrics.markGap
                            visible: !!delegate.modelData.counts[modelData]
                            M.CheckMark { symbols: root.backend.symbols; level: parent.modelData; width: 14; height: 14 }
                            M.Label { text: delegate.modelData.counts[parent.modelData]; textStyle: "secondary" }
                        }
                    }
                }
                Column {
                    id: rowContents
                    visible: !delegate.modelData.header
                    anchors.left: parent.left; anchors.right: parent.right
                    // inside the row's card, as the group's symbol and title above it (R637: the card at the list's sides)
                    anchors.leftMargin: Theme.space.M; anchors.rightMargin: Theme.space.M
                    RowLayout {
                        width: parent.width
                        height: M.ControlMetrics.checkRow      // one line, as the row of ui/checks_page.py; the rest in the tooltip
                        spacing: Theme.space.S
                        Item { width: 4; height: 1 }
                        M.Chevron { open: delegate.modelData.expanded
                            opacity: delegate.modelData.detail ? 1 : 0; Layout.preferredWidth: 12; Layout.preferredHeight: 12 }
                        M.CheckMark { objectName: "checks-symbol-" + delegate.modelData.itemIndex
                            symbols: root.backend.symbols; level: delegate.modelData.level; Layout.preferredWidth: 16; Layout.preferredHeight: 16 }
                        Item { width: 5; height: 1 }
                        M.Label {
                            id: titleLabel
                            objectName: "checks-text-" + delegate.modelData.itemIndex
                            Layout.fillWidth: true
                            text: delegate.modelData.text
                            textStyle: "body"
                            elide: Text.ElideRight
                        }
                        M.Label {
                            Layout.preferredWidth: root.sourceWidth
                            text: delegate.modelData.source || ""
                            textStyle: "secondary"
                            elide: Text.ElideRight
                            M.ToolTip { parent: parent; text: parent.text; visible: sourceHover.hovered && text !== "" && parent.truncated }
                            HoverHandler { id: sourceHover }
                        }
                        Item { width: root.actionWidth; height: 30 }
                    }
                    Item {
                        width: parent.width
                        height: visible ? detailLabel.implicitHeight + 18 : 0
                        visible: !!delegate.modelData.detail && delegate.modelData.expanded
                        M.ReadableText {
                            id: detailLabel
                            anchors.top: parent.top; anchors.topMargin: Theme.space.XS
                            anchors.left: parent.left; anchors.leftMargin: 61
                            width: Math.max(80, Math.min(parent.width - 64, 100 * Theme.text.secondary.size * .5))
                            text: delegate.modelData.detail || ""
                            textStyle: "secondary"
                            wrapMode: Text.Wrap
                        }
                    }
                }
                MouseArea {
                    id: rowMouse
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    height: delegate.modelData.header ? parent.height : 34
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onDoubleClicked: function(mouse) { mouse.accepted = true }
                    onClicked: function(mouse) {
                        root.keyboardMode = false
                        list.forceActiveFocus()
                        list.currentIndex = delegate.index
                        if (delegate.modelData.header) root.backend.toggleGroup(delegate.modelData.key)
                        else if (mouse.button === Qt.RightButton) {
                            root.menuIndex = delegate.modelData.itemIndex
                            root.menuHasFix = delegate.modelData.hasFix
                            root.menuFixText = delegate.modelData.fixText || ""
                            root.menuHasPlace = !!delegate.modelData.place
                            contextMenu.popup()
                        } else root.backend.toggleDetail(delegate.modelData.itemIndex)
                    }
                    M.ToolTip { pressed: rowMouse.pressed; text: delegate.modelData.text; visible: rowMouse.containsMouse && titleLabel.truncated }
                }
                Row {
                    id: actions
                    visible: !delegate.modelData.header
                    anchors.right: parent.right; anchors.rightMargin: Theme.space.M
                    anchors.top: parent.top
                    spacing: Theme.space.XXS
                    M.Button { objectName: "checks-fix-" + delegate.modelData.itemIndex
                        visible: !!delegate.modelData.hasFix; flat: true
                        // R605: the row for several objects names its command («Fill all»), the others say «Fix…»
                        text: delegate.modelData.fixText || root.backend.labels.fix
                        height: Theme.size.CHIP; y: 5
                        contentItem: M.Label { text: parent.text; textStyle: "body"; horizontalAlignment: Text.AlignHCenter }
                        background: Rectangle { radius: Theme.radius.INNER; color: parent.hovered ? Theme.colors.hover : Theme.colors.field }
                        tip: delegate.modelData.fixText ? "" : (delegate.modelData.fix_label || "")
                        onClicked: root.backend.requestFix(delegate.modelData.itemIndex) }
                    M.Button { objectName: "checks-eye-" + delegate.modelData.itemIndex
                        visible: !!delegate.modelData.place; flat: true; iconName: "eye"
                        compact: true; y: (M.ControlMetrics.checkRow - height) / 2
                        tip: delegate.modelData.eyeTip || root.backend.labels.show
                        onClicked: root.backend.showPlace(delegate.modelData.itemIndex) }
                }
                // R555 (10) (Daniel 09/11/2026: «la voce aperta va evidenziata»): the check opened from an object (its
                // mark in the plan or in the tree, «This object»); until Esc or a click on an empty place (R663)
                readonly property bool opened: root.openedShown && root.backend.objectOnly && !modelData.header
                                               && modelData.itemIndex === root.backend.currentIndex
            }
            // the kit's empty state (docs/22, row 9): the reason in the middle of the list; no sign in a card this low
            M.EmptyState { id: emptyLabel; objectName: "checks-empty"; anchors.centerIn: parent
                width: Math.max(0, Math.min(parent.width - 24, Theme.size.READING))
                visible: list.count === 0
                title: root.backend.emptyMessage }
        }
    }
    M.Menu {
        id: contextMenu
        // R662: an entry that does not apply is left out (MenuItem.shown): neither its width nor its icon count
        M.MenuItem { shown: root.menuHasPlace
            text: root.backend.labels.show; iconName: "eye"; onTriggered: root.backend.showPlace(root.menuIndex) }
        M.MenuItem { shown: root.menuHasFix
            text: root.menuFixText || root.backend.labels.fix; onTriggered: root.backend.requestFix(root.menuIndex) }
        M.MenuItem { shown: root.askEnabled
            text: root.backend.labels.ask; onTriggered: root.backend.ask(root.menuIndex) }
        M.MenuItem { text: root.backend.labels.copy; onTriggered: root.backend.copyText(root.menuIndex) }
    }
}
