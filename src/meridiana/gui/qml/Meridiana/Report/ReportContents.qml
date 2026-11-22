import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
import "Outline.js" as Outline

// The report's contents (Daniel 21/11/2026: «come mai in Relazione l'Indice non è una scheda come tutte le altre?»):
// the chapters and paragraphs of the preview in the common tree, a card of the workbench (Workbench.qml, «contents»)
// or the card beside the preview of the page alone (ReportPage.showContents). It speaks with the preview through the
// backend only: `askPage` to go to a chapter, `shownPage` the page the preview shows. The row chosen is lit at once
// and stays lit while the preview gets there: before, the preview's scroll walked through the pages between and the
// light went through every chapter on its way (and every page swept was drawn).
Item {
    id: root
    property var backend
    readonly property var outlineRows: backend ? Outline.rowsOf(backend.outline) : []
    readonly property alias tree: contentsTree
    function sync() {
        const nodes = Outline.nodesOf(outlineRows)
        contentsTree.model = nodes
        contentsTree.expandedIds = nodes.map(n => n.id)
        follow()
    }
    // the last row starting at or before the page shown; the row chosen stays if it starts on the same page
    function follow() {
        if (!backend || backend.replacingPages) return
        const page = backend.shownPage, rows = contentsTree.flattened
        let found = -1
        for (let i = 0; i < rows.length; ++i) if (rows[i].node.page <= page) found = i
        const now = contentsTree.currentIndex
        if (found >= 0 && now >= 0 && now < rows.length && rows[now].node.page === rows[found].node.page) return
        contentsTree.currentIndex = found
    }
    onOutlineRowsChanged: sync()
    Component.onCompleted: sync()
    Connections {
        target: root.backend; ignoreUnknownSignals: true
        function onShownPageChanged() { root.follow() }
        function onReplacingChanged() { root.follow() }
    }
    M.Tree {
        id: contentsTree; objectName: "reportOutline"
        anchors.fill: parent; framed: false; sideSelection: true
        onActivated: node => { if (root.backend) root.backend.askPage(node.page) }
        onFlattenedChanged: root.follow()
    }
    M.EmptyState {
        objectName: "reportOutlineEmpty"
        anchors.fill: parent
        iconName: "file-text"
        visible: contentsTree.count === 0
        title: root.backend ? root.backend.labels.contentsEmpty || "" : ""
    }
}
