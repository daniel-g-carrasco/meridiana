import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
import "TreeSelection.js" as TreeSelection
Item {
    id: root
    property bool framed: true
    property bool sideSelection: false
    // The kit's tree (Daniel 20/11/2026, variant E of the sketches): denser than the band of before.
    // `rowShape`: "inset" is the rows' shape of the lists (ControlMetrics.rowInset, rowRadius, rowFill: a menu
    // entry's, lit under the pointer); "band" is the band from side to side, the selection only.
    property string rowShape: "inset"
    // the text in the bar's condensed Plex
    property bool condensed: true
    // how far each level goes in (before: 20)
    property real indentStep: Theme.space.L
    // the air above and below the text of a row: the density chosen in the appearance settings (design.Rows)
    property real rowAir: Theme.rowAir
    readonly property bool inset: rowShape === "inset"
    property real rowHeight: Math.ceil(Theme.measureText("Ag", "body", condensed).height) + rowAir
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
        anchors.rightMargin: root.framed ? 1 + Theme.size.SCROLLBAR : 0; clip: true; model: root.flattened; currentIndex: root.currentIndex
        onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Contain)
        delegate: MenuItem { required property var modelData; required property int index
            readonly property bool opens: !!modelData.node.children && modelData.node.children.length > 0
            // the edges' rule (ControlMetrics): the ground on the body's lines, the words rowPad inside it
            width: ListView.view.width; height: root.rowHeight
            leftPadding: modelData.depth * root.indentStep + (root.inset ? ControlMetrics.rowGround(root.framed) : 0)
            rightPadding: root.inset ? ControlMetrics.rowGround(root.framed) + ControlMetrics.rowPad : Theme.space.XXS
            topPadding: 0; bottomPadding: 0
            highlighted: root.multiSelect ? root.selectedIds.indexOf(modelData.node.id) >= 0 : root.currentIndex === index
            text: modelData.node.text
            Accessible.role: Accessible.TreeItem; Accessible.name: text
            background: Rectangle {
                x: root.inset ? ControlMetrics.rowGround(root.framed) : 0; width: parent.width - 2 * x
                radius: root.inset ? ControlMetrics.rowRadius : 0
                color: ControlMetrics.rowFill(parent.highlighted, root.inset && parent.hovered, root.enabled)
                Rectangle {
                    visible: root.sideSelection && parent.parent.highlighted
                    width: Theme.space.XXS; height: parent.height - 2 * Theme.space.XXS
                    y: Theme.space.XXS; radius: width / 2; color: Theme.colors.select_fg
                }
            }
            contentItem: Row { id: line; spacing: Theme.space.XXS
                Item { width: 20; height: parent.height
                    opacity: line.parent.opens ? 1 : 0; anchors.verticalCenter: parent.verticalCenter
                    Chevron { anchors.fill: parent; open: root.expandedIds.indexOf(modelData.node.id) >= 0 }     // R592
                    TapHandler { enabled: line.parent.opens; onTapped: root.toggle(index) } }
                Label { text: modelData.node.text; enabled: root.enabled; anchors.verticalCenter: parent.verticalCenter
                    condensed: root.condensed
                    width: Math.max(0, line.width - 20 - Theme.space.XXS); elide: Text.ElideRight }
            }
            onPressed: root.currentIndex = index
            // Moving focus away from a pressed MenuItem cancels its click on Qt 6.12.
            onClicked: { root.forceActiveFocus(Qt.MouseFocusReason); root.select(index) }
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
        // without a frame the bar scrolls in the card's margin beside the rows (the edges' rule, ControlMetrics)
        T.ScrollBar.vertical: ScrollBar { fades: false; parent: root; flickable: view; inMargin: !root.framed
            x: root.framed ? root.width-width-1 : root.width
            y: root.framed ? 1 : 0; height: root.height-2*y }
    }
    EdgeFades { flickable: view; spansSurface: !root.framed }   // in its frame the shadow, else the dissolve (the kit)
}
