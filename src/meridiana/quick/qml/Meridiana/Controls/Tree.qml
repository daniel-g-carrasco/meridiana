import QtQuick
import QtQuick.Shapes
import QtQuick.Templates as T
import Meridiana.Theme
import "TreeSelection.js" as TreeSelection
Item {
    id: root
    property bool framed: true
    property real rowHeight: Math.ceil(Theme.measureText("Ag", "body").height) + 4
    property var model: []
    property var expandedIds: []
    property int currentIndex: -1
    readonly property int count: flattened.length
    readonly property var flattened: flatten(model, 0)
    // More rows of one group with Ctrl and Shift (R439): off by default. A node's `group` says what goes together.
    property bool multiSelect: false
    property var selectedIds: []
    property string selectionAnchor: ""
    signal activated(var node)
    function pick(id, ctrl, shift) {
        const done = TreeSelection.click(flattened.map(r => ({id: r.node.id, group: r.node.group || "", selectable: r.node.selectable})),
                                         selectedIds, selectionAnchor, id, ctrl, shift)
        selectedIds = done.selected; selectionAnchor = done.anchor
    }
    implicitWidth: Theme.size.READING / 2
    implicitHeight: root.rowHeight * Math.min(6, count)+2
    activeFocusOnTab: true
    Accessible.role: Accessible.Tree
    function flatten(nodes, depth) {
        let rows = []
        for (let node of nodes) {
            rows.push({node: node, depth: depth})
            if (node.children && expandedIds.indexOf(node.id) >= 0) rows = rows.concat(flatten(node.children, depth+1))
        }
        return rows
    }
    function toggle(index) {
        if (index < 0 || index >= count) return
        const node = flattened[index].node
        if (!node.children || !node.children.length) return
        const next = expandedIds.slice()
        const at = next.indexOf(node.id)
        if (at < 0) next.push(node.id); else next.splice(at, 1)
        expandedIds = next
        if (currentIndex >= count) currentIndex = count - 1
    }
    function select(index) {
        if (index >= 0 && index < count) {
            currentIndex = index
            if (multiSelect) pick(flattened[index].node.id, false, false)
            activated(flattened[index].node)
        }
    }
    Keys.onDownPressed: select(Math.min(count-1, currentIndex+1))
    Keys.onUpPressed: select(Math.max(0, currentIndex-1))
    Keys.onRightPressed: {
        if (currentIndex < 0) return
        const row = flattened[currentIndex]
        if (expandedIds.indexOf(row.node.id) < 0) toggle(currentIndex)
        else if (row.node.children && row.node.children.length) select(currentIndex+1)
    }
    Keys.onLeftPressed: {
        if (currentIndex < 0) return
        if (expandedIds.indexOf(flattened[currentIndex].node.id) >= 0) toggle(currentIndex)
        else {
            const depth = flattened[currentIndex].depth
            for (let i=currentIndex-1; i>=0; i--) if (flattened[i].depth < depth) { select(i); break }
        }
    }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Home) { select(0); event.accepted = true }
        else if (event.key === Qt.Key_End) { select(count-1); event.accepted = true }
    }
    Keys.onReturnPressed: if (currentIndex >= 0) activated(flattened[currentIndex].node)
    Rectangle { anchors.fill: parent; visible: root.framed; color: Theme.colors.card; radius: Theme.radius.CONTROL; border.width: 1; border.color: Theme.colors.card_line }
    ListView { id: view; anchors.fill: parent; anchors.margins: root.framed ? 1 : 0
        anchors.rightMargin: (root.framed ? 1 : 0) + Theme.size.SCROLLBAR; clip: true; model: root.flattened; currentIndex: root.currentIndex
        onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Contain)
        delegate: MenuItem { required property var modelData; required property int index
            width: ListView.view.width; height: root.rowHeight; leftPadding: modelData.depth * 20; rightPadding: 2; topPadding: 0; bottomPadding: 0
            highlighted: root.multiSelect ? root.selectedIds.indexOf(modelData.node.id) >= 0 : root.currentIndex === index
            text: modelData.node.text
            Accessible.role: Accessible.TreeItem; Accessible.name: text
            background: Rectangle { color: parent.highlighted ? Theme.colors.select_bg : "transparent" }
            contentItem: Row { spacing: 2
                Item { width: 20; height: parent.height
                    opacity: !!modelData.node.children && modelData.node.children.length > 0 ? 1 : 0; anchors.verticalCenter: parent.verticalCenter
                    Shape { anchors.centerIn: parent; width: 8; height: 8; rotation: root.expandedIds.indexOf(modelData.node.id) >= 0 ? 90 : 0
                        ShapePath { strokeWidth: -1; fillColor: Theme.colors.muted
                            startX: 2; startY: 0; PathLine { x: 6; y: 4 } PathLine { x: 2; y: 8 } PathLine { x: 2; y: 0 } }
                    }
                    TapHandler { onTapped: root.toggle(index) } }
                Label { text: modelData.node.text; enabled: root.enabled; anchors.verticalCenter: parent.verticalCenter }
            }
            onPressed: { root.forceActiveFocus(Qt.MouseFocusReason); root.currentIndex = index }
            onClicked: root.select(index)
            onDoubleClicked: root.toggle(index)
            MouseArea { anchors.fill: parent; enabled: root.multiSelect; acceptedButtons: Qt.LeftButton
                onPressed: mouse => {
                    mouse.accepted = !!(mouse.modifiers & (Qt.ControlModifier | Qt.ShiftModifier))
                    if (mouse.accepted) {
                        root.forceActiveFocus(Qt.MouseFocusReason); root.currentIndex = index
                        root.pick(modelData.node.id, !!(mouse.modifiers & Qt.ControlModifier), !!(mouse.modifiers & Qt.ShiftModifier))
                    }
                } }
        }
        T.ScrollBar.vertical: ScrollBar { fades: false; parent: root; flickable: view; x: root.width-width-(root.framed ? 1 : 0)
            y: root.framed ? 1 : 0; height: root.height-2*y }
    }
    EdgeFades { flickable: view }
}
