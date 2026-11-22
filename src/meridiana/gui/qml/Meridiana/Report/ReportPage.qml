import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M
import "Outline.js" as Outline

Item {
    id: root
    property var backend
    // The phase toolbar supplies these commands when embedded in the main shell.
    property bool showCommands: true
    property bool showInspector: true
    readonly property var words: backend ? backend.labels : ({})
    // the contents in a card of the page (the page alone, the tests); in the workbench they are a card of their own
    // (Workbench.qml, «contents», Daniel 21/11/2026)
    property bool showContents: true
    readonly property var outlineNodes: backend ? Outline.flat(Outline.nodesOf(Outline.rowsOf(backend.outline))) : []
    property var savedLocation: null
    // the paragraph the preview shows: the last starting at or before its page
    function nodeAt(page) {
        let found = null
        for (const node of outlineNodes) if (node.page <= page) found = node
        return found
    }
    function rememberLocation() {
        scrollMove.stop()
        const node = nodeAt(preview.currentPage)
        savedLocation = {key: node ? node.key : "", parentKey: node ? node.parentKey : "", page: preview.currentPage}
        if (backend) backend.setReplacingPages(true)
    }
    function restoreLocation() {
        const saved = savedLocation
        savedLocation = null
        if (backend) backend.setReplacingPages(false)
        if (pageModel.count === 0) {
            scrollMove.stop(); preview.contentItem.contentY = 0; preview.currentPage = 1
            return
        }
        if (saved) {
            const node = outlineNodes.find(n => n.key === saved.key) || outlineNodes.find(n => n.key === saved.parentKey)
            goToPage(node ? node.page : saved.page, false)
        }
    }
    // `animate` for the keys of the preview; a chapter chosen in the contents goes there at once, in one frame: the
    // scroll animated through the pages between drew each page it swept and lit every chapter on its way
    function goToPage(number, animate) {
        const index = Math.max(0, Math.min(pageRepeater.count - 1, Math.round(number) - 1))
        const row = pageRepeater.itemAt(index)
        if (!row) return
        scrollMove.stop()
        const top = Math.max(0, Math.min(row.y, preview.contentHeight - preview.availableHeight))
        if (animate === false || Theme.reducedMotion) {
            preview.contentItem.contentY = top
            // the last pages cannot come to the middle: the page asked is the one shown
            if (top < row.y) preview.currentPage = Number(row.page) || index + 1
        } else {
            scrollMove.to = top
            scrollMove.start()
        }
    }
    Connections {
        target: root.backend; ignoreUnknownSignals: true
        function onPageAsked(page) { root.goToPage(page, false) }
    }
    NumberAnimation {
        id: scrollMove; target: preview.contentItem; property: "contentY"
        duration: Theme.reducedMotion ? 0 : Theme.motion.NORMAL
        easing.type: Theme.motion.EASE
    }
    function syncPages() {
        const pages = backend ? backend.pages : []
        for (let i = 0; i < pages.length; ++i) {
            const row = {"source": pages[i].source, "ratio": pages[i].ratio, "page": pages[i].page}
            if (i >= pageModel.count) pageModel.append(row)
            else if (pageModel.get(i).source !== row.source) pageModel.set(i, row)
        }
        if (pageModel.count > pages.length) pageModel.remove(pages.length, pageModel.count - pages.length)
    }
    function setPage(i, page) {
        const row = {"source": page.source, "ratio": page.ratio, "page": page.page}
        if (i < pageModel.count) pageModel.set(i, row)
        else pageModel.append(row)
    }
    property string pageTextTarget: ""
    M.Menu {
        id: reportPageMenu
        property string targetKey: ""
        onAboutToShow: targetKey = root.pageTextTarget
        M.MenuItem { text: textEditing.labels.page; enabled: !reportText.busy && reportText.canCopy(reportPageMenu.targetKey); onTriggered: reportText.request(reportPageMenu.targetKey, true) }
        M.MenuItem { text: textEditing.labels.readPage; enabled: !reportText.busy; onTriggered: reportText.request(reportPageMenu.targetKey, false) }
    }
    ListModel { id: pageModel }
    Connections {
        target: reportText
        function onReadReady() { if (root.visible) pageTextDialog.open() }
        function onErrorOccurred(message) { if (root.backend) root.backend.pageTextError(message) }
    }
    M.Dialog {
        id: pageTextDialog
        title: textEditing.labels.readPage
        implicitWidth: M.ControlMetrics.dialogWidth.wide
        acceptText: ""
        rejectText: textEditing.labels.close
        M.ReadableText { width: parent.width; text: reportText.text || textEditing.labels.noPageText; wrapMode: TextEdit.Wrap }
    }
    // R598: a new preview comes in a page per turn of the window (pageSet), then whole (pagesChanged)
    Connections {
        target: root.backend; ignoreUnknownSignals: true
        function onPagesReplacing() { root.rememberLocation() }
        function onPagesChanged() {
            reportText.cancel(); root.syncPages()
            Qt.callLater(root.restoreLocation)
        }
        function onPageTextCancelled() { reportText.cancel() }
        function onPageSet(i, page) { root.setPage(i, page) }
    }
    implicitWidth: M.ControlMetrics.pageSize.report.width
    implicitHeight: M.ControlMetrics.pageSize.report.height
    clip: true
    onVisibleChanged: { if (backend) backend.setActive(visible); if (!visible) reportText.cancel() }
    Component.onCompleted: { syncPages(); if (backend) backend.setActive(visible) }
    Component.onDestruction: if (backend) backend.setActive(false)

    Rectangle { anchors.fill: parent; color: Theme.colors.panel }

    M.Dialog {
        id: staleExport; objectName: "reportStaleDialog"
        title: root.words.staleTitle || ""
        acceptText: root.words.computeExport || ""; rejectText: root.words.exportCancel || ""
        // R607: «export as it is» on the window's row of buttons (at its left), not a button of its own in the body
        actions: [{text: root.words.exportAnyway || ""}]
        onActionTriggered: { staleExport.close(); root.backend.exportAsItIs() }
        M.ReadableText { wrapMode: Text.WordWrap; text: root.words.staleBody || "" }
        onAccepted: root.backend.recomputeThenExport()
        onRejected: root.backend.dropExport()
    }
    Connections { target: root.backend; ignoreUnknownSignals: true; function onRecomputeAsked() { staleExport.open() } }
    FileDialog {
        id: attachmentsDialog
        title: root.words.add || ""
        fileMode: FileDialog.OpenFiles
        nameFilters: ["PDF (*.pdf)"]
        onAccepted: root.backend.addAttachments(selectedFiles)
    }
    FileDialog {
        id: exportDialog
        title: root.words.export || ""
        fileMode: FileDialog.SaveFile
        defaultSuffix: "pdf"
        nameFilters: ["PDF (*.pdf)"]
        onAccepted: root.backend.exportPdf(selectedFile.toString())
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.L - Theme.space.XXS
        spacing: Theme.space.M
        GridLayout {
            columns: root.width < 700 ? 1 : 5
            Layout.fillWidth: true
            M.CopyLabel { text: root.words.title || ""; textStyle: "title"; Layout.fillWidth: true }
            M.CopyLabel {
                objectName: "reportStatus"
                text: root.backend ? (root.backend.error || (root.backend.ready ? root.backend.status : "")) : ""
                color: root.backend && root.backend.error ? Theme.colors.danger : Theme.colors.muted
                textStyle: "secondary"
                Layout.maximumWidth: root.width * 0.6
                elide: Text.ElideRight
            }
            M.Button { visible: root.showCommands; text: root.words.preview || ""; enabled: root.backend && root.backend.ready && !root.backend.busy; onClicked: root.backend.requestPreview() }
            M.Button { visible: root.showCommands; text: root.words.export || ""; enabled: root.backend && root.backend.ready && !root.backend.busy; onClicked: exportDialog.open() }
        }
        // R437: the numbers and the report exported last, against the project as it is now.
        M.CopyLabel {
            objectName: "reportYearState"; Layout.fillWidth: true; textStyle: "secondary"; elide: Text.ElideRight
            visible: root.backend && root.backend.exportState !== undefined
            text: visible ? [root.backend.exportState.numbers, root.backend.exportState.exported].filter(t => t).join("  ·  ") : ""
            color: visible && (root.backend.exportState.stale || root.backend.exportState.behind) ? Theme.colors.danger : Theme.colors.muted
        }
        // R598: the report's job in the one row of the jobs (its phase, bar, time left and Cancel), as in the status bar
        M.WorkRow {
            objectName: "reportWork"; Layout.fillWidth: true
            row: typeof work !== "undefined" && work !== null ? work.slots.report : ({})
        }
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.showInspector && root.width >= 850 ? 3 : 2
            columnSpacing: Theme.space.L
            rowSpacing: Theme.space.M
            M.Card {
                objectName: "reportOutlinePanel"
                title: root.words.contents || ""
                closable: true; closeTip: root.words.closeContents || ""
                bodyMargin: M.ControlMetrics.cardMargin
                visible: root.showContents && root.backend && root.backend.outlineOpen
                Layout.preferredWidth: Math.min(280, root.width * 0.28)
                Layout.fillHeight: true
                Layout.rowSpan: root.showInspector && root.width < 850 ? 2 : 1
                onClosed: root.backend.setOutlineOpen(false)
                ReportContents { anchors.fill: parent; backend: root.backend }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 240
                Layout.preferredHeight: root.width >= 850 ? 600 : 320
                spacing: Theme.space.XS
                M.Button {
                    objectName: "reportOutlineToggle"
                    text: root.words.contents || ""
                    visible: root.showContents && root.backend && !root.backend.outlineOpen
                    onClicked: root.backend.setOutlineOpen(true)
                }
            // R510: the page's number and the zoom in a bar of the preview that stays put, never in a tip that rides
            // on the page (it did not follow the pointer and went past the card).
            RowLayout {
                id: previewBar
                objectName: "reportPreviewBar"
                Layout.fillWidth: true
                visible: pageModel.count > 0
                spacing: Theme.space.XS
                M.CopyLabel {
                    objectName: "reportPageNumber"
                    Layout.fillWidth: true
                    textStyle: "secondary"; color: Theme.colors.muted; elide: Text.ElideRight
                    text: pageModel.count > 0 ? (root.words.pageOf || "").replace("{n}", preview.currentPage).replace("{total}", root.backend && root.backend.pageCount ? root.backend.pageCount : pageModel.count) : ""
                }
                M.TextField {
                    id: pageEntry; objectName: "reportGoToPage"
                    Layout.preferredWidth: Math.ceil(Theme.measureText(String(pageModel.count), "body").width) + 2 * Theme.space.L
                    Accessible.name: root.words.goToPage || ""
                    text: String(preview.currentPage)
                    validator: IntValidator { bottom: 1; top: Math.max(1, pageModel.count) }
                    onAccepted: {
                        if (acceptableInput) root.goToPage(Number(text), false)
                        preview.forceActiveFocus(Qt.OtherFocusReason)
                    }
                    onActiveFocusChanged: if (!activeFocus) text = String(preview.currentPage)
                    Connections {
                        target: preview
                        function onCurrentPageChanged() { if (!pageEntry.activeFocus) pageEntry.text = String(preview.currentPage) }
                    }
                }
                M.ToolButton { objectName: "reportZoomOut"; mode: "icons"; iconName: "zoom_out"; Accessible.name: text; text: root.words.zoomOut || ""; enabled: preview.zoom > preview.minZoom + 0.001; onClicked: preview.zoomBy(1 / 1.25) }
                M.CopyLabel {
                    objectName: "reportZoom"
                    Layout.preferredWidth: Math.ceil(Theme.measureText("300 %", "secondary").width) + Theme.space.S
                    horizontalAlignment: Text.AlignHCenter; textStyle: "secondary"; font.features: {"tnum": 1}
                    text: Math.round(preview.zoom * 100) + " %"
                    TapHandler { onTapped: preview.zoomTo(1) }
                }
                M.ToolButton { objectName: "reportZoomIn"; mode: "icons"; iconName: "zoom_in"; Accessible.name: text; text: root.words.zoomIn || ""; enabled: preview.zoom < preview.maxZoom - 0.001; onClicked: preview.zoomBy(1.25) }
            }
            C.ScrollView {
                id: preview
                objectName: "reportPreview"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                activeFocusOnTab: true
                Keys.onPressed: event => {
                    if (event.modifiers & (Qt.AltModifier | Qt.MetaModifier)) return
                    let page = 0
                    if (event.key === Qt.Key_PageDown) page = currentPage + 1
                    else if (event.key === Qt.Key_PageUp) page = currentPage - 1
                    else if (event.key === Qt.Key_Home) page = 1
                    else if (event.key === Qt.Key_End) page = pageModel.count
                    else return
                    root.goToPage(page, true); event.accepted = true
                }
                // R509: the pages fill the column up to 822 points, times the zoom; each is drawn from the PDF in the
                // device pixels of the width it has once the zoom has settled, the old drawing scaled meanwhile.
                readonly property real minZoom: 0.5
                readonly property real maxZoom: 4
                property real zoom: 1
                readonly property real fitWidth: Math.max(120, Math.min(822, availableWidth - 2 * Theme.space.XL))
                readonly property real pageWidth: Math.round(fitWidth * zoom)
                property real drawnWidth: 0          // 0 until the first layout has settled
                Component.onCompleted: { redraw.restart(); if (root.backend) root.backend.setShownPage(currentPage) }
                property int currentPage: 1
                onCurrentPageChanged: if (root.backend) root.backend.setShownPage(currentPage)
                function zoomTo(value) {
                    const flick = contentItem, before = Math.max(1, pageWidth)
                    const centreX = flick.contentX + width / 2, centreY = flick.contentY + height / 2
                    zoom = Math.max(minZoom, Math.min(maxZoom, value))
                    const k = pageWidth / before
                    flick.contentX = Math.max(0, Math.min(contentWidth - width, centreX * k - width / 2))
                    flick.contentY = Math.max(0, Math.min(pages.height - height, centreY * k - height / 2))
                }
                function zoomBy(factor) { zoomTo(zoom * factor) }
                function updatePage() {
                    const middle = contentItem.contentY + height / 2
                    let found = 1
                    for (let i = 0; i < pageRepeater.count; ++i) {
                        const row = pageRepeater.itemAt(i)
                        if (row && row.y <= middle) found = Number(row.page) || i + 1
                    }
                    currentPage = found
                }
                onPageWidthChanged: redraw.restart()
                Timer { id: redraw; interval: 150; onTriggered: preview.drawnWidth = preview.pageWidth }
                Connections {
                    target: preview.contentItem
                    function onContentYChanged() { preview.updatePage() }
                    function onMovementStarted() { scrollMove.stop() }
                }
                contentWidth: Math.max(availableWidth, pageWidth + 2 * Theme.space.XL)
                C.ScrollBar.horizontal.policy: pageWidth + 2 * Theme.space.XL > availableWidth ? C.ScrollBar.AsNeeded : C.ScrollBar.AlwaysOff
                C.ScrollBar.vertical: M.ScrollBar { parent: preview; x: preview.width - width; height: preview.height }
                Column {
                    id: pages
                    width: preview.contentWidth - Theme.space.XL
                    onHeightChanged: preview.updatePage()          // laid out again: the pages moved under the middle
                    topPadding: Theme.space.L
                    bottomPadding: Theme.space.XL
                    spacing: Theme.space.XL
                    // Ctrl and the wheel zoom the pages, as in the plan; the wheel alone scrolls them.
                    WheelHandler {
                        acceptedModifiers: Qt.ControlModifier
                        target: null
                        onWheel: (event) => preview.zoomBy(event.angleDelta.y > 0 ? 1.25 : 1 / 1.25)
                    }
                    Repeater {
                        id: pageRepeater
                        model: pageModel
                        onCountChanged: Qt.callLater(preview.updatePage)
                        delegate: Item {
                            id: pageRow
                            required property string source
                            required property real ratio
                            required property string page
                            objectName: "reportPreviewPage"
                            activeFocusOnTab: true
                            TapHandler { onTapped: pageRow.forceActiveFocus(Qt.MouseFocusReason) }
                            Keys.onPressed: event => {
                                if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) {
                                    root.pageTextTarget = pageRow.source; reportPageMenu.popup(pageRow, 0, pageRow.height); event.accepted = true
                                }
                            }
                            C.ContextMenu.menu: reportPageMenu
                            C.ContextMenu.onRequested: position => root.pageTextTarget = pageRow.source
                            width: preview.pageWidth
                            height: Math.round(width * ratio) + 2
                            anchors.horizontalCenter: parent.horizontalCenter
                            // Only the pages near the view are drawn: 38 pages at 2.000 px would be about a gigabyte.
                            readonly property bool near: y + height > preview.contentItem.contentY - preview.height
                                                         && y < preview.contentItem.contentY + 2 * preview.height
                            // what this page wants drawn: its key and its width in device pixels, once the zoom and
                            // the layout have settled (drawnWidth); `shown` the drawing it has, kept until the next
                            // one is there, so a zoom never shows a blank page
                            readonly property string want: near && preview.drawnWidth > 2 && source !== ""
                                ? source + "/" + Math.round((preview.drawnWidth - 2) * Screen.devicePixelRatio) : ""
                            property string asked: ""
                            property string shown: ""
                            function ask() {
                                if (want === "") { asked = ""; shown = ""; return }
                                if (want !== asked && root.backend) { asked = want; root.backend.drawPage(want) }
                            }
                            onWantChanged: Qt.callLater(ask)
                            Connections {
                                target: root.backend
                                ignoreUnknownSignals: true
                                function onPageDrawn(done) { if (done === pageRow.asked && done === pageRow.want) pageRow.shown = done }
                            }
                            Rectangle {
                                anchors.fill: parent
                                color: "white"
                                border.color: Theme.colors.line
                                Image {
                                    objectName: "reportPreviewImage"
                                    readonly property string want: pageRow.want
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    // drawn by a job on the pool, handed over here at once: never Python on the
                                    // image reader's thread (report_pages.py)
                                    source: pageRow.shown !== "" ? "image://reportpage/" + pageRow.shown : ""
                                    asynchronous: false
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    mipmap: true
                                    cache: false
                                }
                            }
                        }
                    }
                    // the kit's empty state: its sign, the reason and the command that fills the preview
                    M.EmptyState {
                        objectName: "reportEmpty"
                        visible: !root.backend || !root.backend.ready
                        width: parent.width
                        height: visible ? Math.max(implicitHeight, preview.availableHeight - pages.topPadding - pages.bottomPadding - 1) : 0
                        iconName: "file-text"
                        title: root.words.empty || ""
                        actionText: root.words.compute || ""
                        onTriggered: root.backend.command("compute")
                    }
                }
            }
            }
            ReportInspector {
                visible: root.showInspector
                backend: root.backend
                Layout.preferredWidth: 340
                Layout.fillHeight: true
                Layout.fillWidth: root.width < 850
            }
        }
    }
}
