import QtQuick
import QtQuick.Controls as QQ
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    objectName: "project-tree-page"
    required property var backend
    property bool showVariants: false
    property string menuKind: ""
    property string menuId: ""
    property var menuActions: []
    property string editMode: "rename"
    property string editId: ""
    property string errorText: ""
    property real savedScroll: 0
    property string savedSelection: ""
    property string lastSelection: ""
    property string selectionAnchor: ""
    color: Theme.colors.panel
    implicitWidth: M.ControlMetrics.pageSize.tree.width
    implicitHeight: M.ControlMetrics.pageSize.tree.height
    // form E of the kit's tree (Daniel 20/11/2026): the bar's condensed Plex, the air of the density chosen
    FontMetrics { id: rowMetrics; font.family: Theme.barFontFamily; font.pixelSize: Theme.text.body.size }

    // Ctrl and Shift take more rows of one kind (R439), by the tree's own rule. A group's row is not chosen: a click
    // opens or closes it (R575); the rows of a closed group are not in backend.rows, so the rule sees the rows shown.
    // A row that does not join (row.join: the site, an imported model, R604) is chosen alone.
    function clickRow(row, ctrl, shift) {
        if (!row.pick) { if (row.fold) backend.toggle(row.fold); return }
        const rows = backend.rows.map(r => ({id: r.kind + "/" + r.oid, group: r.kind, selectable: r.join}))
        const id = row.kind + "/" + row.oid
        if (!(ctrl || shift) || !row.join) { selectionAnchor = row.join ? id : ""; backend.select(row.kind, row.oid); return }
        const lit = backend.selectedRows.filter(k => k.startsWith(row.kind + "/"))
        const done = M.TreeSelection.click(rows, lit, selectionAnchor || lit[0] || "", id, ctrl, shift)
        selectionAnchor = done.anchor
        backend.selectMany(row.kind, done.selected.filter(k => k.startsWith(row.kind + "/")).map(k => k.slice(row.kind.length + 1)))
    }
    function openMenu(kind, oid, x, y) {
        menuActions = backend.actions(kind, oid)
        if (!menuActions.length) return
        if (backend.selectedRows.length < 2 || backend.selectedRows.indexOf(kind + "/" + oid) < 0) backend.select(kind, oid)
        menuKind = kind; menuId = oid
        contextMenu.x = Math.min(x, width - contextMenu.width)
        contextMenu.y = y
        contextMenu.open()
    }
    function editName(mode, oid, value) {
        editMode = mode; editId = oid; nameField.text = value
        editor.open(); nameField.forceActiveFocus(); nameField.selectAll()
    }
    function commitName() {
        if (!nameField.text.trim()) return
        if (editMode === "new") backend.newVariant(nameField.text)
        else if (editMode === "variant") backend.renameVariant(editId, nameField.text)
        else backend.rename(menuKind, menuId, nameField.text)
        editor.close()
        list.forceActiveFocus()
    }
    Connections {
        target: root.backend
        function onErrorOccurred(message) { root.errorText = message }
        function onRowsAboutToChange() { root.savedScroll = list.contentY; root.savedSelection = root.lastSelection }
        function onChanged() {
            Qt.callLater(function() {
                if (root.lastSelection === root.savedSelection)
                    list.contentY = Math.max(0, Math.min(root.savedScroll, list.contentHeight - list.height))
            })
        }
        function onSelectionChanged() {
            let key = root.backend.selectionKind + "/" + root.backend.selectionId
            if (key === root.lastSelection) return
            root.lastSelection = key
            let index = root.backend.rows.findIndex(r => r.kind === root.backend.selectionKind && r.oid === root.backend.selectionId)
            if (index >= 0) list.positionViewAtIndex(index, ListView.Contain)
        }
    }
    M.KeyedRows { id: treeRows; keyOf: row => row.kind + "|" + row.oid + "|" + (row.group || ""); rows: root.backend.rows }
    ListView {
        id: list
        objectName: "project-tree-list"
        // R637: as wide as the card's body; its bar stands centred in the card's margin at its right
        anchors { left: parent.left; right: parent.right; top: parent.top; bottom: variants.top
                  bottomMargin: root.showVariants ? Theme.space.M : 0 }
        clip: true
        model: treeRows.model
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        keyNavigationEnabled: false
        function moveSelection(direction) {
            let entries = root.backend.rows
            let current = entries.findIndex(r => r.kind === root.backend.selectionKind && r.oid === root.backend.selectionId)
            for (let i = current + direction; i >= 0 && i < entries.length; i += direction) {
                if (entries[i].pick) {
                    root.backend.select(entries[i].kind, entries[i].oid)
                    positionViewAtIndex(i, ListView.Contain); return
                }
            }
        }
        // R575: Right opens the group of the row chosen, Left closes it, or goes to the row that holds it
        function fold(open) {
            let entries = root.backend.rows
            let current = entries.findIndex(r => r.kind === root.backend.selectionKind && r.oid === root.backend.selectionId)
            if (current < 0) return
            let row = entries[current]
            if (row.fold && row.open !== open) { root.backend.setOpen(row.fold, open); return }
            if (open) return
            for (let i = current - 1; i >= 0; i--) {
                if (entries[i].depth < row.depth) {
                    if (entries[i].pick) { root.backend.select(entries[i].kind, entries[i].oid); positionViewAtIndex(i, ListView.Contain) }
                    else if (entries[i].fold) root.backend.setOpen(entries[i].fold, false)
                    return
                }
            }
        }
        Keys.onDownPressed: moveSelection(1)
        Keys.onUpPressed: moveSelection(-1)
        Keys.onRightPressed: fold(true)
        Keys.onLeftPressed: fold(false)
        Keys.onDeletePressed: root.backend.trigger("delete", root.backend.selectionKind, root.backend.selectionId)
        Keys.onPressed: event => {
            if (event.key === Qt.Key_F2) {
                let row = root.backend.rows.find(r => r.kind === root.backend.selectionKind && r.oid === root.backend.selectionId)
                // an imported model is all its bodies lit with its row, renamed as one (R604)
                if (row && (row.kind === "model" || ((row.kind === "building" || row.kind === "subfield")
                                                     && root.backend.selectedRows.length < 2))) {
                    root.menuKind = row.kind; root.menuId = row.oid
                    root.editName("rename", row.oid, row.label)
                }
                event.accepted = true
            } else if (event.key === Qt.Key_Z && event.modifiers & Qt.ControlModifier) {
                root.backend.undo(); event.accepted = true
            } else if (event.key === Qt.Key_Y && event.modifiers & Qt.ControlModifier) {
                root.backend.redo(); event.accepted = true
            } else if (event.key === Qt.Key_Menu) {
                root.openMenu(root.backend.selectionKind, root.backend.selectionId, 8, 8)
                event.accepted = true
            }
        }
        QQ.ScrollBar.vertical: M.ScrollBar { id: treeBar; parent: list.parent; flickable: list   // R590: the veils are the bar's
            inMargin: true; x: list.x + list.width; y: list.y; height: list.height }
        delegate: Item {
            id: row
            required property int index
            required property string rowKey
            readonly property var rowNow: treeRows.byKey[rowKey]      // by its key, never by an index that moves (R450)
            // A row taken away that the ListView keeps (its current item, index -1) is not drawn: it stayed behind the
            // new rows, its arrow out at the left of the card (R450, photo of 06/11).
            visible: index >= 0
            property var lastRow: rowNow
            onRowNowChanged: if (rowNow !== undefined) lastRow = rowNow
            readonly property var modelData: rowNow !== undefined ? rowNow : lastRow
            objectName: "tree-row-" + modelData.kind + "-" + modelData.oid
            width: list.width
            height: Math.ceil(rowMetrics.height) + Theme.rowAir + (modelData.group ? Theme.space.M : Theme.space.XS)
            readonly property bool selected: modelData.pick &&
                root.backend.selectedRows.indexOf(modelData.kind + "/" + modelData.oid) >= 0
            Rectangle {
                // the kit's row (ControlMetrics.rowFill): on the body's lines, a menu entry's radius, lit under the pointer
                anchors { fill: parent; topMargin: 1; bottomMargin: 1 }
                radius: M.ControlMetrics.rowRadius
                color: M.ControlMetrics.rowFill(row.selected, pointer.containsMouse && row.modelData.pick, true)
            }
            MouseArea {
                id: pointer
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onClicked: mouse => {
                    list.forceActiveFocus()
                    if (mouse.button === Qt.RightButton) {
                        let point = mapToItem(root, mouse.x, mouse.y)
                        root.openMenu(row.modelData.kind, row.modelData.oid, point.x, point.y)
                    } else root.clickRow(row.modelData, !!(mouse.modifiers & Qt.ControlModifier), !!(mouse.modifiers & Qt.ShiftModifier))
                }
                onDoubleClicked: mouse => { if (mouse.button === Qt.LeftButton && row.modelData.fold && row.modelData.pick) root.backend.toggle(row.modelData.fold) }
                // R665: a name that gave way to its value whole in the tooltip
                M.ToolTip { pressed: pointer.pressed; visible: pointer.containsMouse && text.length > 0
                    text: textRow.nameHidden ? [row.modelData.label, row.modelData.tip].filter(x => !!x).join("\n") : row.modelData.tip }
            }
            // R637 (Daniel 15/11/2026, the Project card: «mi sembra un po' troppo spazio ancora»): the first level
            // starts at the card's margin (its arrow's box there, nothing more before it), each level
            // ControlMetrics.treeIndent further; a row of the first level without an arrow (the site) puts its icon in
            // the arrows' column, its text under the groups' text
            readonly property bool topItem: row.modelData.depth === 0 && !row.modelData.group && row.modelData.fold === ""
            Item {
                // the edges' rule (ControlMetrics): the words and the marks rowPad in from the row's ground
                anchors { fill: parent; topMargin: row.modelData.group ? Theme.space.M : 0; rightMargin: M.ControlMetrics.rowPad
                          leftMargin: M.ControlMetrics.rowPad + row.modelData.depth * M.ControlMetrics.treeIndent }
                // R575: the group's arrow, as a section's (Section.qml): a click opens or closes it
                Item {
                    id: arrow
                    objectName: "tree-fold-" + row.modelData.kind + "-" + row.modelData.oid
                    visible: row.modelData.fold !== ""
                    anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                    width: Theme.space.XL; height: Theme.space.XL
                    M.Chevron { anchors.fill: parent; open: row.modelData.open; active: arrowPointer.containsMouse }     // R592
                    MouseArea { id: arrowPointer; anchors.fill: parent; hoverEnabled: true
                        onClicked: { list.forceActiveFocus(); root.backend.toggle(row.modelData.fold) } }
                }
                Item {
                    id: lead
                    anchors { fill: parent; leftMargin: row.topItem ? 0 : M.ControlMetrics.treeArrow + Theme.space.XXS }
                    M.Icon {
                        id: kindIcon
                        visible: !row.modelData.group && row.modelData.kind !== "fold" && row.modelData.state !== "error"
                        anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                        width: 16; height: 16
                        iconName: row.modelData.icon
                        color: Theme.colors.kind[row.modelData.tint] || Theme.colors.text      // a model as a building (R604)
                    }
                    M.Icon {
                        visible: row.modelData.state === "error"
                        anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                        width: 16; height: 16
                        // R464: the icon provider draws it at the pixels it covers (a data-URL SVG came out blurred)
                        name: visible ? "symbol:stop" : ""; color: "black"; dimDisabled: false
                    }
                    Row {
                        id: textRow
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                                  leftMargin: row.modelData.group || row.modelData.kind === "fold" ? 0
                                            : row.topItem ? M.ControlMetrics.treeArrow + Theme.space.XXS : 22 }
                        spacing: M.ControlMetrics.treeGap
                        // R665 (Daniel 16/11/2026: «se la scheda si restringe troppo, i nomi scompaiono e si vedono solo
                        // potenze»): a building's or a sub-field's value (its kWp, its modules) is never cut: the name
                        // gives way to it, cut at its end, and goes when not even ControlMetrics.treeNameLeast of its
                        // characters and the dots fit (the value alone stays, the name in the tooltip)
                        readonly property bool valued: (row.modelData.value || "") !== ""
                        readonly property real valueWidth: valued ? Math.ceil(Theme.measureText(row.modelData.tail, "body", true).width) : 0
                        readonly property real nameRoom: width - valueWidth - spacing
                        readonly property bool nameHidden: valued && nameRoom < Math.ceil(Theme.measureText(
                            row.modelData.label.substring(0, M.ControlMetrics.treeNameLeast) + "…", "body", true).width)
                        // R575: otherwise the name keeps at least half of a narrow row, the tail (counts, kWp) gives way first
                        M.Label {
                            id: name
                            visible: !textRow.nameHidden
                            text: row.modelData.group ? row.modelData.label.toUpperCase() : row.modelData.label
                            textStyle: row.modelData.group ? "label" : "body"
                            condensed: true
                            color: row.modelData.group ? Theme.colors.text2 : Theme.colors.text
                            // the name's own measure, not implicitWidth: a label hidden while the row was narrow kept an
                            // implicitWidth of 0 when shown again (the name stayed empty beside its value)
                            width: textRow.nameHidden ? 0 : textRow.valued
                                 ? Math.min(Math.ceil(Theme.measureText(text, "body", true).width), textRow.nameRoom)
                                 : Math.min(implicitWidth, Math.max(textRow.width / 2, textRow.width - tail.implicitWidth - textRow.spacing))
                            elide: Text.ElideRight
                        }
                        M.Label {
                            id: tail
                            text: textRow.nameHidden ? row.modelData.value
                                : row.modelData.group || row.modelData.kind === "fold" ? row.modelData.count + row.modelData.tail : row.modelData.tail
                            textStyle: row.modelData.group ? "label" : "body"
                            font.capitalization: Font.MixedCase        // a group's «kWp» as it is written (R575)
                            condensed: true
                            color: Theme.colors.muted
                            width: Math.min(implicitWidth, Math.max(0, textRow.width - (name.visible ? name.width + textRow.spacing : 0)))
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
    // the kit's empty state (docs/27 of the model): a tree with no rows says so, in the middle of the card
    M.EmptyState {
        objectName: "project-tree-empty"
        anchors { left: list.left; right: list.right; verticalCenter: list.verticalCenter }
        visible: root.backend.rows.length === 0
        iconName: "building"
        title: root.backend.labels.empty || ""
    }
    Column {
        id: variants
        // R637: at the card's margins (Shell/DockPanel.qml), a gap from the tree above (the tree's bottomMargin)
        anchors { left: parent.left; right: parent.right; bottom: errorLabel.top }
        visible: root.showVariants
        height: visible ? implicitHeight : 0
        spacing: Theme.space.XS
        M.Label { text: root.backend.labels.variants; textStyle: "label" }
        Repeater {
            model: root.showVariants ? root.backend.variants : []
            RowLayout {
                width: variants.width
                required property var modelData
                M.Button { objectName: "tree-variant-" + modelData.id; text: modelData.name; active: modelData.active; flat: true; Layout.fillWidth: true
                    onClicked: root.backend.switchVariant(modelData.id) }
                M.Button { objectName: "tree-variant-rename-" + modelData.id; iconName: "ellipsis"; tip: root.backend.labels.renameVariant; flat: true
                    onClicked: root.editName("variant", modelData.id, modelData.name) }
                M.Button { objectName: "tree-variant-delete-" + modelData.id; iconName: "trash"; tip: root.backend.labels.deleteVariant; flat: true; enabled: !modelData.active
                    onClicked: root.backend.deleteVariant(modelData.id) }
            }
        }
        M.Button { objectName: "tree-new-variant"; text: root.backend.labels.newVariant; iconName: "new_variant"; flat: true
            onClicked: root.editName("new", "", "") }
    }
    M.ReadableText {
        id: errorLabel
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: text ? implicitHeight : 0
        text: root.errorText; wrapMode: Text.Wrap; color: Theme.colors.danger
    }
    M.Menu {
        id: contextMenu
        objectName: "project-tree-context-menu"
        onAboutToShow: nameCopy.begin()
        onClosed: nameCopy.end()
        M.TextActions { id: nameCopy; readOnly: true
            wholeText: { const row = root.backend.rows.find(r => r.kind === root.menuKind && r.oid === root.menuId); return row ? row.label : "" } }
        M.MenuItem { text: textEditing.labels.name; enabled: nameCopy.allowed("copy"); onTriggered: nameCopy.execute("copy") }
        Repeater {
            model: root.menuActions
            // R564: the common entry, as the bar's, the plan's and the 3D view's
            M.MenuEntry {
                required property var modelData
                entry: modelData
                onTriggered: {
                    if (modelData.id === "rename") {
                        let row = root.backend.rows.find(r => r.kind === root.menuKind && r.oid === root.menuId)
                        root.editName("rename", root.menuId, row.label)
                    } else if (modelData.id === "relayout") confirmation.open()
                    else root.backend.trigger(modelData.id, root.menuKind, root.menuId)
                }
            }
        }
    }
    // R21-F2: the name of a variant and the question before a new layout are windows (M.Dialog), their buttons in the bar
    M.Dialog {
        id: editor
        objectName: "project-tree-name-editor"
        implicitWidth: M.ControlMetrics.dialogWidth.narrow
        title: root.editMode === "new" ? root.backend.labels.newVariant : root.backend.labels.rename
        rejectText: root.backend.labels.cancel
        acceptText: root.backend.labels.apply
        acceptEnabled: nameField.text.trim().length > 0
        acceptOnReturn: false
        onAccepted: root.commitName()
        M.TextField { id: nameField; objectName: "project-tree-name-field"; onAccepted: if (editor.acceptEnabled) root.commitName() }
    }
    M.Dialog {
        id: confirmation
        implicitWidth: M.ControlMetrics.dialogWidth.narrow
        rejectText: root.backend.labels.cancel
        acceptText: root.backend.labels.apply
        onAccepted: root.backend.trigger("relayout", root.menuKind, root.menuId)
        M.ReadableText { text: root.backend.labels.relayoutQuestion; wrapMode: Text.Wrap }
    }
}
