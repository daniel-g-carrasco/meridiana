import QtQuick
import QtQuick.Controls as QQ
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Properties as P

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
    FontMetrics { id: rowMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size }
    M.Label { id: markMeasure; visible: false; textStyle: "label" }

    // Ctrl and Shift take more rows of one kind (R439), by the tree's own rule.
    function clickRow(row, ctrl, shift) {
        const rows = backend.rows.map(r => ({id: r.kind + "/" + r.oid, group: r.kind, selectable: !r.group && r.kind !== "site"}))
        const id = row.kind + "/" + row.oid
        const selectable = !row.group && row.kind !== "site"
        if (!(ctrl || shift) || !selectable) { selectionAnchor = selectable ? id : ""; backend.select(row.kind, row.oid); return }
        const done = M.TreeSelection.click(rows, backend.selectedRows, selectionAnchor || backend.selectedRows[0] || "", id, ctrl, shift)
        selectionAnchor = done.anchor
        backend.selectMany(row.kind, done.selected.map(k => k.slice(row.kind.length + 1)))
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
        anchors { left: parent.left; right: parent.right; top: parent.top; bottom: variants.top }
        anchors.rightMargin: Theme.size.SCROLLBAR
        clip: true
        model: treeRows.model
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        keyNavigationEnabled: false
        function moveSelection(direction) {
            let entries = root.backend.rows
            let current = entries.findIndex(r => r.kind === root.backend.selectionKind && r.oid === root.backend.selectionId)
            for (let i = current + direction; i >= 0 && i < entries.length; i += direction) {
                if (!entries[i].group) {
                    root.backend.select(entries[i].kind, entries[i].oid)
                    positionViewAtIndex(i, ListView.Contain); return
                }
            }
        }
        Keys.onDownPressed: moveSelection(1)
        Keys.onUpPressed: moveSelection(-1)
        Keys.onDeletePressed: root.backend.trigger("delete", root.backend.selectionKind, root.backend.selectionId)
        Keys.onPressed: event => {
            if (event.key === Qt.Key_F2) {
                let row = root.backend.rows.find(r => r.kind === root.backend.selectionKind && r.oid === root.backend.selectionId)
                if (row && (row.kind === "building" || row.kind === "subfield") && root.backend.selectedRows.length < 2) {
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
        QQ.ScrollBar.vertical: M.ScrollBar { id: treeBar; fades: false }   // the veils: P.ScrollEdges below
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
            width: list.width - treeBar.room
            height: Math.ceil(rowMetrics.height) + (modelData.group ? 8 + Theme.space.M : 10)
            readonly property bool selected: !modelData.group && modelData.kind !== "site" &&
                root.backend.selectedRows.indexOf(modelData.kind + "/" + modelData.oid) >= 0
            Rectangle {
                anchors { fill: parent; leftMargin: 4; rightMargin: 4; topMargin: 1; bottomMargin: 1 }
                radius: Theme.radius.INNER
                color: row.selected ? Theme.colors.select_bg : pointer.containsMouse && !row.modelData.group ? Theme.colors.hover : "transparent"
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
                M.ToolTip { pressed: pointer.pressed; visible: pointer.containsMouse && text.length > 0; text: row.modelData.tip }
            }
            Item {
                anchors { fill: parent; topMargin: row.modelData.group ? Theme.space.M : 0; leftMargin: 8; rightMargin: 10 }
                M.Icon {
                    id: kindIcon
                    visible: !row.modelData.group && row.modelData.state !== "error"
                    anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                    width: 16; height: 16
                    iconName: row.modelData.icon
                    color: {
                        return Theme.colors.kind[row.modelData.kind] || Theme.colors.text
                    }
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
                    anchors { left: parent.left; leftMargin: row.modelData.group ? 0 : 22; right: parent.right; rightMargin: root.backend.markWidth(99, markMeasure.font) + 4; verticalCenter: parent.verticalCenter }
                    spacing: M.ControlMetrics.treeGap
                    M.Label {
                        text: row.modelData.group ? row.modelData.label.toUpperCase() : row.modelData.label
                        textStyle: row.modelData.group ? "label" : "body"
                        color: row.modelData.group ? Theme.colors.text2 : Theme.colors.text
                        width: Math.min(implicitWidth, Math.max(0, textRow.width - tail.implicitWidth - 7))
                        elide: Text.ElideRight
                    }
                    M.Label {
                        id: tail
                        text: row.modelData.group ? row.modelData.count : row.modelData.tail
                        textStyle: row.modelData.group ? "label" : "body"
                        color: Theme.colors.muted
                    }
                }
                Rectangle {
                    id: mark
                    objectName: "tree-mark-" + row.modelData.kind + "-" + row.modelData.oid
                    anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                    visible: row.modelData.markCount > 0
                    width: root.backend.markWidth(row.modelData.markCount, markMeasure.font)
                    height: Theme.size.CHIP
                    radius: Theme.radius.INNER
                    readonly property color ink: row.modelData.markLevel === "fail" ? Theme.colors.danger : row.modelData.markLevel === "warn" ? Theme.colors.warning_ink : Theme.colors.text2
                    color: "transparent"
                    M.Icon {
                        x: 6; anchors.verticalCenter: parent.verticalCenter
                        width: 12; height: 12
                        objectName: "tree-mark-image"
                        name: "symbol:" + (row.modelData.markLevel || "info"); color: "black"; dimDisabled: false
                    }
                    M.Label { x: parent.width - 8 - width; anchors.verticalCenter: parent.verticalCenter
                        text: row.modelData.markCount; color: Theme.colors.text; textStyle: "label" }
                    MouseArea {
                        id: markPointer
                        anchors.fill: parent; hoverEnabled: true
                        onClicked: root.backend.activateMark(row.modelData.kind, row.modelData.oid)
                        M.ToolTip { pressed: markPointer.pressed; visible: markPointer.containsMouse; text: row.modelData.markTip }
                    }
                }
            }
        }
    }
    P.ScrollEdges { viewport: list; page: false }
    Column {
        id: variants
        anchors { left: parent.left; right: parent.right; bottom: errorLabel.top; margins: root.showVariants ? 8 : 0 }
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
    M.Label {
        id: errorLabel
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: text ? implicitHeight : 0
        text: root.errorText; wrapMode: Text.Wrap; color: Theme.colors.danger
    }
    M.Menu {
        id: contextMenu
        objectName: "project-tree-context-menu"
        Repeater {
            model: root.menuActions
            M.MenuItem {
                required property var modelData
                text: modelData.text
                enabled: !modelData.separator
                implicitHeight: modelData.separator ? Theme.space.M : Theme.size.CONTROL
                Rectangle {
                    visible: modelData.separator
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Theme.space.M }
                    height: Theme.line.HAIR; color: Theme.colors.line
                }
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
        anchors.centerIn: parent
        width: Math.min(M.ControlMetrics.dialogWidth.narrow, root.width - 2 * M.ControlMetrics.dialogEdge)
        title: root.editMode === "new" ? root.backend.labels.newVariant : root.backend.labels.rename
        rejectText: root.backend.labels.cancel
        acceptText: root.backend.labels.apply
        acceptEnabled: nameField.text.trim().length > 0
        acceptOnReturn: false
        onAccepted: root.commitName()
        contentItem: M.TextField { id: nameField; objectName: "project-tree-name-field"; onAccepted: if (editor.acceptEnabled) root.commitName() }
    }
    M.Dialog {
        id: confirmation
        anchors.centerIn: parent
        width: Math.min(M.ControlMetrics.dialogWidth.narrow, root.width - 2 * M.ControlMetrics.dialogEdge)
        rejectText: root.backend.labels.cancel
        acceptText: root.backend.labels.apply
        onAccepted: root.backend.trigger("relayout", root.menuKind, root.menuId)
        contentItem: M.Label { text: root.backend.labels.relayoutQuestion; wrapMode: Text.Wrap }
    }
}
