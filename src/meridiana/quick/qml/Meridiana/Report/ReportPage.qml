import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    property var backend
    // The phase toolbar supplies these commands when embedded in the main shell.
    property bool showCommands: true
    property bool showInspector: true
    readonly property var words: backend ? backend.labels : ({})
    function syncPages() {
        const pages = backend ? backend.pages : []
        for (let i = 0; i < pages.length; ++i) {
            const row = {"source": pages[i].source, "ratio": pages[i].ratio, "page": pages[i].page}
            if (i >= pageModel.count) pageModel.append(row)
            else if (pageModel.get(i).source !== row.source) pageModel.set(i, row)
        }
        if (pageModel.count > pages.length) pageModel.remove(pages.length, pageModel.count - pages.length)
    }
    ListModel { id: pageModel }
    Connections { target: root.backend; function onChanged() { root.syncPages() } }
    implicitWidth: M.ControlMetrics.pageSize.report.width
    implicitHeight: M.ControlMetrics.pageSize.report.height
    clip: true
    onVisibleChanged: if (backend) backend.setActive(visible)
    Component.onCompleted: { syncPages(); if (backend) backend.setActive(visible) }
    Component.onDestruction: if (backend) backend.setActive(false)

    Rectangle { anchors.fill: parent; color: Theme.colors.panel }

    M.Dialog {
        id: staleExport; objectName: "reportStaleDialog"
        parent: C.Overlay.overlay; anchors.centerIn: parent; title: root.words.staleTitle || ""
        acceptText: root.words.computeExport || ""; rejectText: root.words.exportCancel || ""
        contentItem: Column { spacing: Theme.space.M; width: 420
            M.Label { width: parent.width; wrapMode: Text.WordWrap; text: root.words.staleBody || "" }
            M.Button { objectName: "reportExportAnyway"; flat: true; text: root.words.exportAnyway || ""; onClicked: { staleExport.close(); root.backend.exportAsItIs() } }
        }
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
            M.Label { text: root.words.title || ""; textStyle: "title"; Layout.fillWidth: true }
            M.Label {
                objectName: "reportStatus"
                text: root.backend ? (root.backend.error || (root.backend.ready ? root.backend.status : "")) : ""
                color: root.backend && root.backend.error ? Theme.colors.danger : Theme.colors.muted
                textStyle: "secondary"
                Layout.maximumWidth: root.width * 0.6
                elide: Text.ElideRight
            }
            M.Button { visible: root.showCommands; text: root.words.preview || ""; enabled: root.backend && root.backend.ready && !root.backend.busy; onClicked: root.backend.requestPreview() }
            M.Button { visible: root.showCommands; text: root.words.export || ""; enabled: root.backend && root.backend.ready && !root.backend.busy; onClicked: exportDialog.open() }
            M.Button { visible: root.backend && root.backend.busy; text: root.words.cancel || ""; onClicked: root.backend.cancel() }
        }
        // R437: the numbers and the report exported last, against the project as it is now.
        M.Label {
            objectName: "reportYearState"; Layout.fillWidth: true; textStyle: "secondary"; elide: Text.ElideRight
            visible: root.backend && root.backend.exportState !== undefined
            text: visible ? [root.backend.exportState.numbers, root.backend.exportState.exported].filter(t => t).join("  ·  ") : ""
            color: visible && (root.backend.exportState.stale || root.backend.exportState.behind) ? Theme.colors.danger : Theme.colors.muted
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: M.ControlMetrics.progressLine
            visible: root.backend && root.backend.busy
            color: Theme.colors.line
            Rectangle { width: parent.width * (root.backend ? root.backend.progress : 0); height: parent.height; color: Theme.colors.accent }
        }
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.showInspector && root.width >= 850 ? 2 : 1
            columnSpacing: Theme.space.L
            rowSpacing: Theme.space.M
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 240
                Layout.preferredHeight: root.width >= 850 ? 600 : 320
                spacing: Theme.space.XS
            // R510: the page's number and the zoom in a bar of the preview that stays put, never in a tip that rides
            // on the page (it did not follow the pointer and went past the card).
            RowLayout {
                id: previewBar
                objectName: "reportPreviewBar"
                Layout.fillWidth: true
                visible: pageModel.count > 0
                spacing: Theme.space.XS
                M.Label {
                    objectName: "reportPageNumber"
                    Layout.fillWidth: true
                    textStyle: "secondary"; color: Theme.colors.muted; elide: Text.ElideRight
                    text: pageModel.count > 0 ? (root.words.pageOf || "").replace("{n}", preview.currentPage).replace("{total}", root.backend && root.backend.pageCount ? root.backend.pageCount : pageModel.count) : ""
                }
                M.ToolButton { objectName: "reportZoomOut"; mode: "icons"; iconName: "zoom_out"; Accessible.name: text; text: root.words.zoomOut || ""; enabled: preview.zoom > preview.minZoom + 0.001; onClicked: preview.zoomBy(1 / 1.25) }
                M.Label {
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
                // R509: the pages fill the column up to 822 points, times the zoom; each is drawn from the PDF in the
                // device pixels of the width it has once the zoom has settled, the old drawing scaled meanwhile.
                readonly property real minZoom: 0.5
                readonly property real maxZoom: 4
                property real zoom: 1
                readonly property real fitWidth: Math.max(120, Math.min(822, availableWidth - 2 * Theme.space.XL))
                readonly property real pageWidth: Math.round(fitWidth * zoom)
                property real drawnWidth: 0          // 0 until the first layout has settled
                Component.onCompleted: redraw.restart()
                property int currentPage: 1
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
                Connections { target: preview.contentItem; function onContentYChanged() { preview.updatePage() } }
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
                    Column {
                        visible: !root.backend || !root.backend.ready
                        width: Math.min(420, parent.width)
                        anchors.horizontalCenter: parent.horizontalCenter
                        topPadding: Math.max(Theme.space.XL, (preview.availableHeight - emptyMessage.implicitHeight - emptyCompute.implicitHeight - spacing) / 2)
                        spacing: Theme.space.L
                        M.Label { id: emptyMessage; width: parent.width; text: root.words.empty || ""; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                        M.Button { id: emptyCompute; anchors.horizontalCenter: parent.horizontalCenter; text: root.words.compute || ""; onClicked: root.backend.command("compute") }
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
