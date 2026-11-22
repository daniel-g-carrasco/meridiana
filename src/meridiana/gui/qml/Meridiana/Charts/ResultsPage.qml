import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.ChartBackend 1.0

M.ScrollPage {
    leftMargin: 0; air: Theme.space.XL; airInside: true; spacing: 0; implicitHeight: 0
    id: root
    objectName: "results-scroll"
    property var pageData: ({})
    property int currentIndex: 0
    property int displayedIndex: 0
    property Item displayedPage: null
    // a year's page greys on the controller's `stale`, told alone (charts_controller._session_changed); a page of no
    // year (storage) never does
    property bool stale: pageData.stale !== undefined && typeof results !== "undefined" && results.stale
    property var visited: [0]
    signal actionRequested(string action)
    readonly property var tabs: pageData.tabs || []
    ChartServices { id: services }

    function select(index) {
        currentIndex = index
        if (visited.indexOf(index) < 0) visited = visited.concat([index])
        const loader = pages.itemAt(index)
        if (loader && loader.status === Loader.Ready && loader.item.prepared) reveal(index, loader.item)
    }
    function reveal(index, page) { displayedIndex = index; displayedPage = page }
    onPageDataChanged: {
        if (currentIndex >= tabs.length) { currentIndex = 0; displayedIndex = 0 }
    }
    // R625: a page made in the background (Workbench.qml warms it while hidden) can have had a tile thrown away by Qt
    // half made («Cannot create delegate»): shown with a tile missing, the tiles are made again from the same data.
    // Only when the tile is still missing a while later: a tile still being made in the background is missing too,
    // and making the tiles again then threw it away half made, the very loss this mends (on Linux)
    Timer { id: mendCheck; interval: Theme.motion.PATIENCE; onTriggered: root.mendTiles(true) }
    function mendTiles(confirmed) {
        const wanted = (root.pageData.tiles || []).length
        if (!root.visible || tiles.shown.length >= wanted) return
        if (confirmed !== true) { mendCheck.restart(); return }
        console.warn("ResultsPage: tiles made again,", tiles.shown.length, "of", wanted, "were made")
        tileRepeater.model = []
        tileRepeater.model = Qt.binding(() => root.tilesMade ? Math.max(root.tilesKept, root.tileCount) : 0)
    }
    onVisibleChanged: if (visible) Qt.callLater(mendTiles)
    // the tiles are made once the page is whole, a turn of events after it, not a slice at a time with it: a page
    // warmed in the background whose results changed (or that was closed) half way through threw away the tiles
    // still being made («Cannot create delegate», «Object or context destroyed during incubation», on Linux)
    property bool tilesMade: false
    readonly property int tileCount: (root.pageData.tiles || []).length
    property int tilesKept: 0
    onTileCountChanged: tilesKept = Math.max(tilesKept, tileCount)
    Component.onCompleted: Qt.callLater(() => { root.tilesMade = true; mendCheck.restart() })
    component Copy: M.CopyLabel {
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        font.family: Theme.fontFamily
        font.pixelSize: Theme.type.BODY
        color: Theme.colors.text
    }
    component Command: Basic.Button {
        id: button
        font.family: Theme.fontFamily
        font.pixelSize: Theme.type.BODY
        leftPadding: Theme.space.L
        rightPadding: Theme.space.L
        topPadding: Theme.space.M
        bottomPadding: Theme.space.M
        contentItem: M.Label { text: button.text; color: Theme.colors.text; horizontalAlignment: Text.AlignHCenter }
        background: Rectangle {
            radius: Theme.radius.CONTROL
            color: button.down || button.checked ? Theme.colors.line_soft : button.hovered ? Theme.colors.chrome : "transparent"
            border.width: Theme.focusRing(button) ? Theme.line.FOCUS : 0
            border.color: Theme.colors.focus
        }
    }
    Column {
        id: contents
        x: Theme.space.XL
        width: Math.max(0, root.width - 2 * Theme.space.XL)
        spacing: Theme.space.L
        Copy {
            width: parent.width
            text: root.pageData.basis ? root.pageData.basis.text : ""
            visible: text.length > 0
            color: root.stale ? Theme.colors.muted : Theme.colors.text
            M.ToolTip { visible: basisHover.hovered && text !== ""; text: root.pageData.basis ? root.pageData.basis.tip || "" : "" }
            HoverHandler { id: basisHover }
        }
        Grid {
            id: tiles
            width: parent.width
            spacing: Theme.space.M
            property var members: []
            // the tiles of the results in hand: the ones kept past their number are hidden and measure nothing
            readonly property var shown: members.filter(tile => tile && tile.index < root.tileCount)
            readonly property real labelHeight: shown.reduce((height, tile) => Math.max(height, tile ? tile.labelContentHeight : 0), 0)
            // whole pixels (R596): the text heights of Linux are fractions, and the second row stood on a fraction
            readonly property real tileHeight: Math.ceil(shown.reduce((height, tile) => Math.max(height, tile ? tile.desiredHeight : 0), 0))
            readonly property real wantedWidth: shown.reduce((width, tile) => Math.max(width, tile ? tile.numberWidth : 0), 165)
            columns: Math.max(1, Math.min(5, (root.pageData.tiles || []).length,
                                        Math.floor((width + spacing) / (wantedWidth + spacing))))
            Repeater {
                id: tileRepeater
                readonly property bool mendsItself: true     // mendTiles; PhaseLoader.integrity leaves it alone
                // the number of tiles, not the array: new results with as many tiles keep the tiles made (a new array
                // threw away the tiles still being made in the background, «Cannot create delegate»); each reads its own
                // never fewer than were made: a tile thrown away while Qt was still making it in the background lost the
                // making («Object or context destroyed during incubation»); a tile past the results' number is hidden
                model: root.tilesMade ? Math.max(root.tilesKept, root.tileCount) : 0
                onItemAdded: (index, item) => tiles.members = tiles.members.concat([item])
                onItemRemoved: (index, item) => tiles.members = tiles.members.filter(tile => tile !== item)
                delegate: Rectangle {
                    id: tile
                    required property int index
                    readonly property var modelData: (root.pageData.tiles || [])[index] || ({})
                    objectName: "result-tile-" + index
                    visible: index < root.tileCount
                    readonly property real labelContentHeight: tileLabel.implicitHeight
                    readonly property real desiredHeight: tileContent.implicitHeight + 2 * Theme.space.M
                    readonly property var valueParts: {
                        const value = modelData.value || "–"
                        const at = value.lastIndexOf(" ")
                        return at > 0 && /[0-9]/.test(value.slice(0, at)) && !/[0-9]/.test(value.slice(at+1))
                            ? [value.slice(0, at), value.slice(at+1)] : [value, ""]
                    }
                    readonly property real numberWidth: figure.implicitWidth + unit.implicitWidth + Theme.space.XS + 2*Theme.space.L
                    // whole pixels (R596): a fraction moved every tile after the first, and its «?», on half a pixel
                    width: Math.floor((tiles.width - (tiles.columns - 1) * tiles.spacing) / tiles.columns)
                    height: tiles.tileHeight
                    color: Theme.colors.field
                    radius: Theme.radius.CARD
                    M.HelpMark { x: Math.round(parent.width - width - Theme.space.S); y: Theme.space.S
                        visible: !!tile.modelData.help; helpKey: tile.modelData.help || ""; helpPlace: "tile" }
                    Column {
                        id: tileContent
                        x: Theme.space.L; y: Theme.space.M
                        width: parent.width - 2 * x
                        spacing: Theme.space.XXS
                        // D7 (Linux 14/11/2026: «Tasso interno di rendimento» touched its «?»): the label ends
                        // Theme.space.S before the help mark's zone, as the mark stands Theme.space.S from the tile's side
                        Copy { id: tileLabel; width: parent.width-(tile.modelData.help ? M.ControlMetrics.helpMark + 2*Theme.space.S - Theme.space.L : 0); height: tiles.labelHeight; text: tile.modelData.label || ""; color: Theme.colors.text2; font.pixelSize: Theme.type.SMALL }
                        Item {
                            width: parent.width; height: figure.implicitHeight
                            Copy { copyText: (tile.modelData.label || "") + "\t" + tile.valueParts.join(" "); id: figure; objectName: "tile-value-" + tile.index; text: tile.valueParts[0]; font.pixelSize: Theme.type.DISPLAY; font.weight: Font.DemiBold; color: root.stale ? Theme.colors.muted : Theme.colors.text }
                            Copy { copyText: (tile.modelData.label || "") + "\t" + tile.valueParts.join(" "); id: unit; objectName: "tile-unit-" + tile.index; x: figure.width + Theme.space.XS; anchors.baseline: figure.baseline; text: tile.valueParts[1] }
                        }
                        Copy {
                            id: detail
                            objectName: "tile-detail-" + tile.index
                            property string more: tile.modelData.more || ""
                            width: parent.width; height: Math.max(implicitHeight, detailMetrics.height*2)
                            text: tile.modelData.detail || ""; font.pixelSize: Theme.type.SMALL; color: Theme.colors.text2
                            FontMetrics { id: detailMetrics; font: detail.font }
                            HoverHandler { id: detailHover }
                            M.ToolTip { visible: detailHover.hovered && text !== ""; text: tile.modelData.more || "" }
                        }
                    }
                }
            }
        }
        Copy {
            width: parent.width
            text: root.pageData.kind === "production" && !root.pageData.empty ? "" : root.pageData.status || ""
            visible: text.length > 0
            color: Theme.colors.text2
        }
        Command {
            objectName: "results-empty-action"
            visible: root.tabs.length === 0 && !!root.pageData.empty && !!root.pageData.action
            text: root.pageData.action === "choose_battery" ? (services.labels.chooseBattery || services.labels.source) : services.labels.calculate
            onClicked: root.actionRequested(root.pageData.action)
        }
        Rectangle {
          id: chartCard
          width: parent.width
          readonly property real foot: Theme.space.M     // under the tab's body, inside the card
          height: chartContents.implicitHeight + chartContents.y + foot
          visible: root.tabs.length > 0
          color: "transparent"
          border.width: 1; border.color: Theme.colors.line_soft
          radius: Theme.radius.CARD
          Column {
           id: chartContents
           // R652 (Daniel 15/11/2026: «a questa barra con le linguette manca un po' di margine sopra, e sarebbe bello che
           // margine sinistro, basso e alto fossero lo stesso»): the tabs ControlMetrics.cardMargin from the card's top,
           // from its left side and from the line under them, the margin of every card (R637)
           x: Theme.space.M; y: M.ControlMetrics.cardMargin
           width: parent.width-2*x
           spacing: Theme.space.M
        Item {
          width: parent.width
          height: tabBar.height + M.ControlMetrics.cardMargin - chartContents.spacing
          visible: root.tabs.length > 0
        M.Segments {
            id: tabBar
            x: M.ControlMetrics.cardMargin - chartContents.x
            width: Math.min(implicitWidth, parent.width - x)
            visible: root.tabs.length > 0
            model: root.tabs.map(tab => tab.title)
            currentIndex: root.currentIndex
            onActivated: index => root.select(index)
            Repeater {
                model: root.tabs
                Item {
                    required property int index
                    objectName: "result-tab-" + index
                    x: tabBar.padding + tabBar.segmentX(index)
                    width: tabBar.segmentWidth(index); height: tabBar.height
                }
            }
        }
        }
        Rectangle { width: parent.width; height: 1; color: Theme.colors.line_soft }
        Item {
            id: tabBody
            visible: root.tabs.length > 0
            width: parent.width
            // R495: the room under the tabs down to the page's foot, every margin above and under it counted (the card's
            // own top, chartContents.y, was missing: 4 px over, a bar that never went away however tall the window).
            // Whole pixels, so a sum of fractions never leaves the bar on for half a pixel.
            readonly property real availableHeight: Math.max(160, Math.floor(root.height - contents.y - chartCard.y
                - chartContents.y - tabBody.y - chartCard.foot - Theme.space.XL))
            implicitHeight: root.displayedPage ? root.displayedPage.implicitHeight : availableHeight
            height: implicitHeight
            Repeater {
                id: pages
                model: root.tabs
                delegate: M.WholeLoader {
                    id: pageLoader
                    required property var modelData
                    required property int index
                    width: tabBody.width
                    wanted: root.visited.indexOf(index) >= 0
                    asynchronous: true
                    visible: index === root.displayedIndex || index === root.currentIndex || opacity > 0
                    opacity: index === root.displayedIndex ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.QUICK } }
                    onLoaded: if (index === root.currentIndex && item.prepared) root.reveal(index, item)
                    sourceComponent: Column {
                        id: pageContent
                        width: pageLoader.width
                        spacing: Theme.space.L
                        property Item firstChart: null
                        // R495: what the page shows besides its charts (the note, the provenance) takes its room
                        // first; the charts share the rest, each never under its own minimum.
                        readonly property real besides: (pageNote.visible ? pageNote.height + spacing : 0)
                            + (pagePedigree.visible && pagePedigree.height > 0 ? pagePedigree.height + spacing : 0)
                        readonly property bool prepared: (pageLoader.modelData.charts || []).length === 0 ||
                            (firstChart !== null && firstChart.status === Loader.Ready && firstChart.item.readyForDisplay)
                        onPreparedChanged: if (prepared && pageLoader.status === Loader.Ready && pageLoader.index === root.currentIndex) root.reveal(pageLoader.index, pageContent)
                        Repeater {
                            id: chartItems
                            model: pageLoader.modelData.charts || []
                            onItemAdded: (index, item) => { if (index === 0) pageContent.firstChart = item }
                            delegate: M.WholeLoader {
                                id: chartLoader
                                required property var modelData
                                property bool wasVisible: false
                                readonly property bool intersects: {
                                    const offset = root.contentY
                                    const position = contents.y + chartCard.y + chartContents.y + tabBody.y + chartLoader.y
                                    return pageLoader.status === Loader.Ready
                                        && (pageLoader.index === root.displayedIndex || pageLoader.index === root.currentIndex)
                                        && position + height >= offset && position < offset + root.height
                                }
                                width: pageLoader.width
                                height: Math.max(item ? item.minimumHeight : 160+Theme.size.CHIP+Theme.space.S,
                                    Math.floor((tabBody.availableHeight - pageContent.besides
                                        - Math.max(0, chartItems.count-1)*pageContent.spacing) / Math.max(1, chartItems.count)))
                                wanted: wasVisible
                                asynchronous: true
                                onIntersectsChanged: activation.restart()
                                Component.onCompleted: activation.restart()
                                Timer {
                                    id: activation
                                    interval: 16
                                    onTriggered: if (chartLoader.intersects) chartLoader.wasVisible = true
                                }
                                sourceComponent: Chart {
                                    objectName: "chart-" + chartLoader.modelData.id
                                    chartData: chartLoader.modelData
                                    onActionRequested: action => root.actionRequested(action)
                                }
                            }
                        }
                        M.ReadableText { id: pageNote; width: parent.width; text: pageLoader.modelData.note || ""; visible: text.length > 0 }
                        Pedigree {
                            id: pagePedigree
                            width: parent.width
                            records: pageLoader.modelData.records || []
                            sourceKinds: root.pageData.source_kinds || ({})
                            limits: pageLoader.modelData.records ? (root.pageData.limits || []) : []
                            limitsTitle: root.pageData.limits_title || ""
                            limitsIntro: root.pageData.limits_intro || ""
                            viewport: root.flickable
                            renderingEnabled: pageLoader.status === Loader.Ready && pageLoader.index === root.displayedIndex
                        }
                    }
                }
            }
        }
          }
        }
        Loader {
            width: parent.width
            active: root.tabs.length === 0 && (root.pageData.records || []).length > 0
            sourceComponent: Pedigree {
                records: root.pageData.records || []
                sourceKinds: root.pageData.source_kinds || ({})
                limits: root.pageData.limits || []
                limitsTitle: root.pageData.limits_title || ""
                limitsIntro: root.pageData.limits_intro || ""
                viewport: root.flickable
            }
        }
    }
}
