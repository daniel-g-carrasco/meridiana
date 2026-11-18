import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.ChartBackend 1.0

M.ScrollPage {
    leftMargin: 0; air: Theme.space.XL; airInside: true; spacing: 0; implicitHeight: 0; groundAbove: true
    id: root
    objectName: "results-scroll"
    property var pageData: ({})
    property int currentIndex: 0
    property int displayedIndex: 0
    property Item displayedPage: null
    property bool stale: !!pageData.stale
    property var visited: [0]
    signal actionRequested(string action)
    signal helpRequested(string topic)
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
    component Copy: Text {
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
        contentItem: Copy { text: button.text; color: Theme.colors.text; horizontalAlignment: Text.AlignHCenter }
        background: Rectangle {
            radius: Theme.radius.CONTROL
            color: button.down || button.checked ? Theme.colors.line_soft : button.hovered ? Theme.colors.chrome : "transparent"
            border.width: button.activeFocus ? 1 : 0
            border.color: Theme.colors.text2
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
            readonly property real labelHeight: members.reduce((height, tile) => Math.max(height, tile ? tile.labelContentHeight : 0), 0)
            readonly property real tileHeight: members.reduce((height, tile) => Math.max(height, tile ? tile.desiredHeight : 0), 0)
            readonly property real wantedWidth: members.reduce((width, tile) => Math.max(width, tile ? tile.numberWidth : 0), 165)
            columns: Math.max(1, Math.min(5, (root.pageData.tiles || []).length,
                                        Math.floor((width + spacing) / (wantedWidth + spacing))))
            Repeater {
                model: root.pageData.tiles || []
                onItemAdded: (index, item) => tiles.members = tiles.members.concat([item])
                onItemRemoved: (index, item) => tiles.members = tiles.members.filter(tile => tile !== item)
                delegate: Rectangle {
                    id: tile
                    required property var modelData
                    required property int index
                    objectName: "result-tile-" + index
                    readonly property real labelContentHeight: tileLabel.implicitHeight
                    readonly property real desiredHeight: tileContent.implicitHeight + 2 * Theme.space.M
                    readonly property var valueParts: {
                        const value = modelData.value || "–"
                        const at = value.lastIndexOf(" ")
                        return at > 0 && /[0-9]/.test(value.slice(0, at)) && !/[0-9]/.test(value.slice(at+1))
                            ? [value.slice(0, at), value.slice(at+1)] : [value, ""]
                    }
                    readonly property real numberWidth: figure.implicitWidth + unit.implicitWidth + Theme.space.XS + 2*Theme.space.L
                    width: (tiles.width - (tiles.columns - 1) * tiles.spacing) / tiles.columns
                    height: tiles.tileHeight
                    color: Theme.colors.field
                    radius: Theme.radius.CARD
                    M.HelpMark { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: Theme.space.S
                        visible: !!tile.modelData.help
                        onClicked: root.helpRequested(tile.modelData.help) }
                    Column {
                        id: tileContent
                        x: Theme.space.L; y: Theme.space.M
                        width: parent.width - 2 * x
                        spacing: Theme.space.XXS
                        Copy { id: tileLabel; width: parent.width-(tile.modelData.help ? 12 : 0); height: tiles.labelHeight; text: tile.modelData.label || ""; color: Theme.colors.text2; font.pixelSize: Theme.type.SMALL }
                        Item {
                            width: parent.width; height: figure.implicitHeight
                            Copy { id: figure; objectName: "tile-value-" + tile.index; text: tile.valueParts[0]; font.pixelSize: Theme.type.DISPLAY; font.weight: Font.DemiBold; color: root.stale ? Theme.colors.muted : Theme.colors.text }
                            Copy { id: unit; objectName: "tile-unit-" + tile.index; x: figure.width + Theme.space.XS; anchors.baseline: figure.baseline; text: tile.valueParts[1] }
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
           x: Theme.space.M; y: Theme.space.XS
           width: parent.width-2*x
           spacing: Theme.space.M
        M.Segments {
            id: tabBar
            width: Math.min(implicitWidth, parent.width)
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
                delegate: Loader {
                    id: pageLoader
                    required property var modelData
                    required property int index
                    width: tabBody.width
                    active: root.visited.indexOf(index) >= 0
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
                            delegate: Loader {
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
                                active: wasVisible
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
                        Copy { id: pageNote; width: parent.width; text: pageLoader.modelData.note || ""; visible: text.length > 0 }
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
