import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Dialogs
import QtQuick.Window
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.ChartBackend 1.0

Rectangle {
    id: root
    property var chartData: ({kind: "message", message: "", table: {headers: [], rows: []}})
    property bool tableMode: false
    property real viewStart: 0
    property real viewEnd: 1
    property var hiddenSeries: []
    property string readout: ""
    property int hoverIndex: -1
    property int hoverRow: -1
    property var geometry: null
    property int readinessRevision: 0
    property int pathBuilds: 0
    property bool tableVisited: false
    // R494 (Daniel 06/11/2026: style B «Terra e talpa», study in meridiana-studio-grafici): columns capped in width,
    // 2 px of the card between stacked pieces, the data end rounded, the unit atop the axis, the legend above; under
    // the pointer a band on the column, the others dimmed, a solid guide on lines and a card with every series, its
    // share, the total and the month in full; a sober entrance. The chart has no ground of its own: the card's shows
    // through, and grid, axes, text, band and card take the theme's tokens. The series are charts_scene.SERIES.
    property var look: ({bars: true, gap: 2, card: true, solidGuide: true, unitTop: true, lineKeys: true, animate: true,
                         barFraction: .52, barMax: 44, radius: 3, dim: .35, band: .06, lineWidth: 2, area: .12,
                         legendTop: true, keySize: 10, keyRadius: 2, legendSpacing: 18})
    function lk(key, fallback) { return look && look[key] !== undefined ? look[key] : fallback }
    readonly property var ch: look && look.chrome ? (Theme.dark ? look.chrome.dark : look.chrome.light) : ({})
    readonly property color muted: ch.muted || colors.muted
    property real pointerX: 0
    property real pointerY: 0
    property real grow: 1
    // The entrance: the columns rise from a third of their height (never a blank frame while a tab crosses to
    // another); lines and maps appear at once.
    NumberAnimation on grow { id: entrance; running: false; from: .3; to: 1; duration: Theme.motion.GROW; easing.type: Theme.motion.EASE }
    // The colour under the chart, the card's: the ring of the markers and of the dots under the pointer.
    readonly property color ground: {
        const revision = Theme.revision
        for (let up = parent; up; up = up.parent)
            if (up.color !== undefined && up.color.a > .99) return up.color
        return colors.panel
    }
    readonly property var tip: hoverIndex < 0 || !geometry ? null : tipFor(hoverIndex, hoverRow)
    function monthName(label) {
        const names = {gen: "Gennaio", feb: "Febbraio", mar: "Marzo", apr: "Aprile", mag: "Maggio", giu: "Giugno",
                       lug: "Luglio", ago: "Agosto", set: "Settembre", ott: "Ottobre", nov: "Novembre", dic: "Dicembre"}
        return names[String(label).toLowerCase()] || label
    }
    function pct(value) { return fmt(value, Math.abs(value) < 10 ? 1 : 0) + " %" }
    function tipFor(index, row) {
        const d = chartData, unit = d.unit || ""
        if (d.kind === "heatmap") {
            if (row < 0 || !d.matrix[row]) return null
            const months = (d.rows || []).length === 12
            return {title: months ? monthName(d.rows[row]) + ", ore " + d.cols[index] : d.cols[index] + ", ore " + d.rows[row], total: "",
                    rows: [{color: "", name: "", value: fmt(d.matrix[row][index]) + " " + unit, share: ""}]}
        }
        const title = d.kind === "line" ? (d.names ? d.names[index] : (d.xlabel ? d.xlabel + " " : "")
            + fmt(d.xs[index], Number.isInteger(d.xs[index]) ? 0 : 1)) : monthName(d.categories[index])
        let rows = [], total = 0
        const series = d.series || []
        for (let k = 0; k < series.length; k++) {
            if (!shown(series[k][0])) continue
            const v = series[k][1][index]
            // «changes» paints a step by its sign (charts_scene: slot 1 up, slot 8 down): the key follows the bar
            const slot = d.kind === "changes" ? (v !== null && v < 0 ? 7 : 0) : k % 8
            rows.push({color: seriesColors[slot], name: series.length > 1 ? series[k][0] : "", raw: v, share: "",
                       value: fmt(v, d.kind === "changes" ? 2 : undefined) + " " + unit})
            if (v !== null && isFinite(v)) total += v
        }
        if (d.stacked && rows.length > 1) {
            for (let r of rows) r.share = total ? pct(100 * r.raw / total) : ""
        } else if (rows.length === 1 && d.kind === "bars" && !d.mark_zero) {
            let sum = 0
            for (let v of series[0][1]) if (v !== null && isFinite(v) && v > 0) sum += v
            if (sum && rows[0].raw > 0) rows[0].share = pct(100 * rows[0].raw / sum) + (d.categories.length === 12 ? " dell'anno" : " del totale")
        } else if (rows.length === 2 && d.kind === "bars" && rows[0].raw) {
            const change = 100 * (rows[1].raw - rows[0].raw) / Math.abs(rows[0].raw)
            rows[1].share = (change > 0 ? "+" : "") + pct(change)
        }
        return {title: title, rows: rows, total: d.stacked && rows.length > 1 ? fmt(total) + " " + unit : ""}
    }
    function stackTop(k, j, value) {
        if (!chartData.stacked) return true
        const s = chartData.series
        for (let m = k + 1; m < s.length; m++) {
            if (!shown(s[m][0])) continue
            const v = s[m][1][j]
            if (v !== null && isFinite(v) && (value >= 0 ? v > 0 : v < 0)) return false
        }
        return true
    }
    function stackBase(k, j) {
        if (!chartData.stacked) return true
        const s = chartData.series
        for (let m = 0; m < k; m++) {
            if (!shown(s[m][0])) continue
            const v = s[m][1][j]
            if (v !== null && isFinite(v) && v !== 0) return false
        }
        return true
    }
    readonly property bool readyForDisplay: {
        const revision = readinessRevision
        if (isEmpty) return true
        if (tableMode) return tableLoader.status === Loader.Ready
        if (!geometry || layerRepeater.count !== geometry.layers.length) return false
        for (let i=0;i<layerRepeater.count;i++) {
            const seriesItem=layerRepeater.itemAt(i)
            if (!seriesItem || !seriesItem.shapesReady) return false
        }
        return !geometry.image || mapImage.status === Image.Ready
    }
    property string error: ""
    readonly property var colors: Theme.colors
    readonly property var chartColors: colors.chart || ({})
    readonly property var seriesColors: look && look.series ? (Theme.dark ? look.series.dark : look.series.light)
        : (Theme.dark ? services.darkSeries : services.lightSeries)
    readonly property var ramp: look && look.ramp ? look.ramp : services.sequential
    readonly property color ink: ch.ink || colors.text
    readonly property color ink2: ch.ink2 || colors.text2
    readonly property color grid: ch.grid || chartColors.grid || colors.line_soft
    readonly property int textSize: Theme.type.BODY
    readonly property real deviceScale: root.Window.window ? root.Window.window.devicePixelRatio : 1
    readonly property real pixel: 1/deviceScale
    readonly property real pointDiameter: 7 + 1.5*pixel
    readonly property real hoverDiameter: 8 + 1.5*pixel
    readonly property bool isEmpty: chartData.kind === "message"
    property string exportKind: "svg"
    signal actionRequested(string action)
    color: "transparent"
    readonly property real minimumHeight: buttons.height + Theme.space.S + Math.max(160,
        chartData.kind === "changes" ? ((chartData.categories || []).length+2)*(Math.ceil(tickMetrics.height)+Theme.space.S) : 0)
    implicitHeight: chartData.kind === "changes" ? Math.max(330, (chartData.categories.length+3)*(textSize+10)) : 380
    ChartServices { id: services; onErrorOccurred: message => root.error = message }
    FontMetrics { id: tickMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION }

    // AxisItem's major spacing, in JS: resizing never calls Python.
    function axisTicks(lo, hi, size, decimals, minor) {
        const maximum = (hi-lo)/Math.max(2.25, 2.25*Math.sqrt(Math.max(1,size)/300))
        const decade = Math.pow(10, Math.floor(Math.log10(Math.max(1e-12, maximum))))
        let step = (maximum/decade>=5 ? 5 : maximum/decade>=2 ? 2 : 1)*decade
        if (minor) step /= 2
        let digits=decimals || 0
        while(digits<8 && Math.abs(step*Math.pow(10,digits)-Math.round(step*Math.pow(10,digits)))>1e-6) digits++
        let ticks=[]
        for(let i=Math.ceil(lo/step); i<=Math.floor(hi/step); i++) ticks.push({position:(i*step-lo)/(hi-lo), label:fmt(i*step,digits)})
        return ticks
    }
    readonly property var yTicks: !geometry ? [] : ["bars","line"].includes(chartData.kind) ?
        axisTicks(geometry.ymin,geometry.ymax,plot.height,chartData.decimals,false).map(t=>({position:1-t.position,label:t.label})) : geometry.yticks
    readonly property var xTicks: !geometry ? [] : chartData.kind==="changes" || (chartData.kind==="line" && !(chartData.ticks || []).length) ?
        axisTicks(geometry.xmin,geometry.xmax,plot.width,0,false).map(t=>({position:t.position,label:t.label+(chartData.kind==="changes" ? chartData.unit : "")})) : geometry.xticks
    readonly property var scaleTicks: geometry && chartData.kind==="heatmap" ? axisTicks(geometry.ymin,geometry.ymax,plot.height,chartData.decimals,true) : []

    function prepare() {
        if (!visible || isEmpty || tableMode || geometry) return
        let prepared = services.prepare(chartData)
        prepared.left = Math.ceil(Math.max(0, ...prepared.yticks.map(t => tickMetrics.advanceWidth(t.label))) + 14 + (chartData.unit && !lk("unitTop", false) && !["heatmap","changes"].includes(chartData.kind) ? unitMetrics.height+2 : 0))
        geometry = prepared
        if (lk("animate", false) && !Theme.reducedMotion && visible && root.Window.window && root.Window.window.visible) {
            grow = .3; entrance.restart()
        }
    }
    function reset() { viewStart = 0; viewEnd = 1 }
    function fmt(value, decimals) {
        if (value === null || value === undefined || !isFinite(value)) return "–"
        const parts = Math.abs(value).toFixed(decimals === undefined ? (chartData.decimals || 0) : decimals).split(".")
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, services.italian ? "." : ",")
        return (value < 0 ? "-" : "") + parts.join(services.italian ? "," : ".")
    }
    function shown(name) { return hiddenSeries.indexOf(name) < 0 }
    function flattened(paths) { let result=[]; for (let path of paths) for (let point of path) result.push(point); return result }
    function visiblePath(points) {
        // Keep crossing segments, including both sides of a missing-data gap.
        let lo=0, hi=points.length
        while (lo<hi) { let mid=(lo+hi)>>1; if (points[mid].x<viewStart) lo=mid+1; else hi=mid }
        let first=Math.max(0,lo-1)
        lo=first; hi=points.length
        while (lo<hi) { let mid=(lo+hi)>>1; if (points[mid].x<=viewEnd) lo=mid+1; else hi=mid }
        return points.slice(first,Math.min(points.length,lo+1)).map(p =>
            Qt.point((p.x-viewStart)/(viewEnd-viewStart)*1000,p.y*500))
    }
    function toggle(name) {
        let copy = hiddenSeries.slice(); let index = copy.indexOf(name)
        if (index < 0) copy.push(name); else copy.splice(index, 1)
        hiddenSeries = copy
        readout=""; hoverIndex=-1; hoverRow=-1
    }
    function zoom(factor, fraction) {
        let span = viewEnd-viewStart
        let next = Math.min(1, Math.max(1/500, span*factor))
        let start = Math.max(0, Math.min(1-next, viewStart + span*fraction-next*fraction))
        viewStart = start; viewEnd = start+next
    }
    function inspect(px, py) {
        if (!geometry || isEmpty) return
        pointerX = px; pointerY = py
        let data = chartData; let g = geometry
        let u = viewStart + px/plot.width*(viewEnd-viewStart)
        let at = g.xmin+u*(g.xmax-g.xmin)
        let index = 0; let label = ""; let parts = []; let total = 0
        hoverRow = -1
        if (data.kind === "heatmap") {
            index = Math.max(0, Math.min(g.columns-1, Math.floor(px/plot.width*g.columns)))
            hoverRow = Math.max(0, Math.min(g.rows-1, Math.floor(py/plot.height*g.rows)))
            hoverIndex = index
            readout = data.rows[hoverRow]+", "+data.cols[index]+": "+fmt(data.matrix[hoverRow][index])+" "+data.unit
            return
        }
        if (data.kind === "line") {
            let xs = data.xs; let lo=0; let hi=xs.length-1
            while (lo<hi) { let mid=(lo+hi)>>1; if (xs[mid]<at) lo=mid+1; else hi=mid }
            index=lo
            if (index>0 && Math.abs(at-xs[index-1])<=Math.abs(xs[index]-at)) index--
            label=data.names ? data.names[index] : (data.xlabel ? data.xlabel+" " : "")+fmt(xs[index], Number.isInteger(xs[index]) ? 0 : 1)
        } else if (data.kind === "changes") {
            index=Math.max(0,Math.min(data.categories.length-1,Math.floor(py/plot.height*data.categories.length)))
            label=data.categories[index]
        } else {
            index=Math.max(0,Math.min(data.categories.length-1,Math.round(at)))
            label=data.categories[index]
        }
        hoverIndex=index
        for (let s of data.series || []) {
            if (!shown(s[0])) continue
            let value=s[1][index]
            parts.push((data.series.length>1 ? s[0]+" " : "")+fmt(value, data.kind === "changes" ? 2 : undefined)+" "+data.unit)
            if (value !== null) total+=value
        }
        if (data.stacked && parts.length>1) parts.push(services.labels.total+" "+fmt(total)+" "+data.unit)
        readout=label+(parts.length ? ": "+parts.join(" · ") : "")
    }
    onChartDataChanged: { geometry=null; hiddenSeries=[]; readout=""; hoverIndex=-1; hoverRow=-1; reset(); prepare() }
    onVisibleChanged: if (visible && !geometry) prepare()
    onTableModeChanged: { if (tableMode) tableVisited=true; if (!tableMode && !geometry) prepare() }
    Component.onCompleted: prepare()
    FontMetrics { id: unitMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }

    Text {
        id: heading; x: 0; y: (buttons.height-height)/2; width: parent.width-buttons.width-Theme.space.M
        text: root.chartData.title || ""; color: root.ink; font.family: Theme.fontFamily
        font.pixelSize: root.textSize; font.weight: Font.DemiBold; elide: Text.ElideRight
    }
    M.Segments {
        id: buttons; anchors.right: parent.right; y: 0
        model: [services.labels.graph, services.labels.table]
        currentIndex: root.tableMode ? 1 : 0
        onActivated: index => root.tableMode = index === 1
        Item { objectName: "tableButton"; x: buttons.padding+buttons.segmentX(1); width: buttons.segmentWidth(1); height: buttons.height }
        Item { objectName: "graphButton"; x: buttons.padding; width: buttons.segmentWidth(0); height: buttons.height }
    }
    Rectangle {
        id: drawing; objectName: "chartDrawing"; anchors { left: parent.left; right: parent.right; top: buttons.bottom; bottom: parent.bottom; topMargin: Theme.space.S }
        color: "transparent"
        visible: opacity>0
        opacity: root.isEmpty || !root.tableMode || tableLoader.status!==Loader.Ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : 90 } }
        Text {
            x: plot.x; y: 0; width: parent.width-x; height: 22
            text: root.readout; color: root.ink2; visible: !root.lk("card", false)
            font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; elide: Text.ElideRight
        }
        Flow {
            id: legend; x: plot.x; y: root.lk("legendTop", false) ? 0 : parent.height - height; spacing: root.lk("legendSpacing", 14)
            width: parent.width-x-24
            visible: (root.chartData.series || []).length > 1
            Repeater {
                model: root.chartData.series || []
                delegate: Item {
                    required property int index; required property var modelData
                    objectName: "legend-entry-" + index
                    width: legendText.implicitWidth+19; height: Math.max(16,tickMetrics.height+2)
                    readonly property bool lineKey: root.lk("lineKeys", false) && root.chartData.kind === "line"
                    Rectangle { x: 0; y: (parent.height-height)/2; width: parent.lineKey ? 14 : 12; height: parent.lineKey ? 3 : (root.lk("keySize", 12))
                        radius: parent.lineKey ? 1.5 : root.lk("keyRadius", 2); color: root.seriesColors[index%8]; opacity: root.shown(modelData[0]) ? 1 : .4 }
                    Text { id: legendText; x: 17; anchors.verticalCenter: parent.verticalCenter
                        text: modelData[0]; color: root.shown(modelData[0]) ? root.ink2 : root.colors.muted
                        font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; font.strikeout: !root.shown(modelData[0])
                    }
                    MouseArea { anchors.fill: parent; onClicked: root.toggle(parent.modelData[0]); cursorShape: Qt.PointingHandCursor }
                    Accessible.role: Accessible.CheckBox; Accessible.name: modelData[0]; Accessible.checked: root.shown(modelData[0])
                }
            }
        }
        Item {
            id: plot; objectName: "plotArea"
            anchors { left: parent.left; right: parent.right; top: parent.top; bottom: parent.bottom
                leftMargin: root.geometry ? Math.min(root.geometry.left,parent.width*.43) : 64
                rightMargin: root.chartData.kind === "heatmap" ? 76 : 10
                topMargin: (root.lk("legendTop", false) && legend.visible ? legend.implicitHeight + 10 : 0) + (root.lk("unitTop", false) ? unitMetrics.height + 12 : 22)
                bottomMargin: tickMetrics.height + 10 + (root.chartData.xlabel ? unitMetrics.height+2 : 0) + (legend.visible && !root.lk("legendTop", false) ? legend.implicitHeight+4 : 0) }
            Text {
                visible: root.lk("unitTop", false) && !["heatmap","changes"].includes(root.chartData.kind)
                x: -width - 6; y: -height - 8
                text: root.chartData.unit || ""; color: root.muted
                font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION
            }
            Text {
                visible: !root.lk("unitTop", false) && !["heatmap","changes"].includes(root.chartData.kind)
                x: -plot.x; y: parent.height/2 + width/2; rotation: -90; transformOrigin: Item.TopLeft
                text: root.chartData.unit || ""; color: root.ink2
                font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL
            }
            Repeater {
                model: root.yTicks
                delegate: Item {
                    required property var modelData
                    y: modelData.position*plot.height; width: plot.width
                    Rectangle { width: parent.width; height: root.pixel; color: root.grid; visible: root.chartData.kind !== "heatmap" && root.chartData.kind !== "changes" }
                    Text { x: -width-6; y: -height/2; width: plot.anchors.leftMargin-(root.chartData.unit && !root.lk("unitTop", false) && !["heatmap","changes"].includes(root.chartData.kind) ? unitMetrics.height+10 : 10)
                        text: modelData.label; color: root.muted; horizontalAlignment: Text.AlignRight
                        elide: Text.ElideRight; font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION
                    }
                }
            }
            Repeater {
                model: root.xTicks
                delegate: Text {
                    required property var modelData
                    readonly property real pos: (modelData.position-root.viewStart)/(root.viewEnd-root.viewStart)
                    x: pos*plot.width-width/2; y: plot.height+6
                    visible: pos>=0 && pos<=1; text: modelData.label; color: root.muted
                    font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION
                    Rectangle { visible: root.chartData.kind==="changes"; x: parent.width/2; y: -plot.height-6; width: root.pixel; height: plot.height; color: root.grid }
                }
            }
            Text { anchors.horizontalCenter: parent.horizontalCenter; y: parent.height+tickMetrics.height+8; text: root.chartData.xlabel || ""
                color: root.ink2; font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION }
            Rectangle { y: parent.height; width: parent.width; height: root.pixel*root.lk("axisWidth", 1); color: root.ch.axis || root.chartColors.axis || root.colors.line }
            Item {
                id: clipped; anchors.fill: parent; clip: true
                Item {
                    id: marks; width: plot.width/(root.viewEnd-root.viewStart); height: plot.height
                    x: -root.viewStart*width
                    Rectangle {
                        objectName: "hoverBand"
                        readonly property real slot: root.geometry ? marks.width/(root.geometry.xmax-root.geometry.xmin) : 0
                        visible: root.lk("band", 0) > 0 && root.hoverIndex >= 0 && !!root.geometry && root.chartData.kind === "bars"
                        x: root.geometry ? (root.hoverIndex-root.geometry.xmin)/(root.geometry.xmax-root.geometry.xmin)*marks.width - slot/2 : 0
                        width: slot; height: marks.height; radius: root.lk("radius", 0)
                        color: Qt.rgba(root.ink.r, root.ink.g, root.ink.b, root.lk("band", 0))
                    }
                    Rectangle {
                        readonly property int rows: (root.chartData.categories || []).length
                        visible: root.lk("band", 0) > 0 && root.hoverIndex >= 0 && root.chartData.kind === "changes"
                        x: 0; width: marks.width; radius: root.lk("radius", 0)
                        y: (root.hoverIndex+.15)/(rows+.2)*marks.height; height: .9/(rows+.2)*marks.height
                        color: Qt.rgba(root.ink.r, root.ink.g, root.ink.b, root.lk("band", 0))
                    }
                    Repeater {
                        id: layerRepeater
                        model: root.geometry ? root.geometry.layers : []
                        onItemAdded: root.readinessRevision++
                        onItemRemoved: root.readinessRevision++
                        delegate: Item {
                            id: seriesLayer; required property var modelData; required property int index
                            readonly property color seriesColor: root.seriesColors[index%8]
                            readonly property bool shapesReady: {
                                const revision=root.readinessRevision
                                for (let i=0;i<paths.count;i++) {
                                    const item=paths.itemAt(i)
                                    if (!item || item.status!==Shape.Ready) return false
                                }
                                return true
                            }
                            width: marks.width; height: marks.height; visible: root.shown(modelData.name)
                            Repeater {
                                model: seriesLayer.modelData.rects
                                delegate: Rectangle {
                                    id: bar
                                    required property var modelData
                                    readonly property bool styled: root.lk("bars", false) && root.chartData.kind === "bars"
                                    readonly property bool sideways: root.lk("bars", false) && root.chartData.kind === "changes"
                                    readonly property var g: root.geometry
                                    readonly property real slot: g ? seriesLayer.width/(g.xmax-g.xmin) : 0
                                    readonly property int count: (root.chartData.series || []).length
                                    readonly property bool grouped: !root.chartData.stacked && count > 1
                                    readonly property real pitch: Math.min(slot*root.lk("barFraction", .7)/(grouped ? count : 1), root.lk("barMax", 1e9))
                                    readonly property real barWidth: grouped ? pitch - root.lk("groupGap", 2) : pitch
                                    readonly property real centre: !g ? 0 : (modelData.index-g.xmin)/(g.xmax-g.xmin)*seriesLayer.width
                                        + (grouped ? (seriesLayer.index-(count-1)/2)*pitch : 0)
                                    readonly property real zeroY: g ? g.ymax/(g.ymax-g.ymin)*seriesLayer.height : 0
                                    readonly property real rawY: modelData.y*seriesLayer.height
                                    readonly property real rawH: Math.max(.1, modelData.height*seriesLayer.height)
                                    readonly property bool base: root.stackBase(seriesLayer.index, modelData.index)
                                    readonly property bool stackEnd: root.stackTop(seriesLayer.index, modelData.index, modelData.value)
                                    readonly property real gap: styled && root.chartData.stacked && !base ? root.lk("gap", 0) : 0
                                    readonly property real r: Math.max(0, Math.min(root.lk("radius", 0), (styled ? height : width)/2, (styled ? width : height)/2))
                                    x: styled ? centre - barWidth/2 : modelData.x*seriesLayer.width
                                    y: styled ? zeroY + (rawY-zeroY)*root.grow : sideways ? modelData.y*seriesLayer.height : rawY
                                    width: styled ? barWidth : modelData.width*seriesLayer.width
                                    height: styled ? Math.max(.1, rawH*root.grow - (modelData.value >= 0 ? gap : 0)) : rawH
                                    topLeftRadius: (styled && stackEnd && modelData.value >= 0) || (sideways && modelData.value < 0) ? r : 0
                                    topRightRadius: (styled && stackEnd && modelData.value >= 0) || (sideways && modelData.value >= 0) ? r : 0
                                    bottomLeftRadius: (styled && stackEnd && modelData.value < 0) || (sideways && modelData.value < 0) ? r : 0
                                    bottomRightRadius: (styled && stackEnd && modelData.value < 0) || (sideways && modelData.value >= 0) ? r : 0
                                    // The others dimmed toward the card's colour, not made see-through: the grid stays behind
                                    // them and a step's figure beside it keeps its full ink.
                                    readonly property bool dimmed: root.hoverIndex >= 0 && root.lk("dim", 1) < 1 && modelData.index !== root.hoverIndex
                                    readonly property color full: root.seriesColors[modelData.slot]
                                    color: dimmed ? Qt.tint(full, Qt.rgba(root.ground.r, root.ground.g, root.ground.b, 1 - root.lk("dim", 1))) : full
                                    Behavior on color { ColorAnimation { duration: Theme.reducedMotion ? 0 : 120 } }
                                    border.width: root.chartData.stacked && !styled ? 0.75*root.pixel : 0
                                    border.color: root.ground
                                    Rectangle { anchors.fill: parent; color: "transparent"; border.width: 1.4; border.color: root.ink
                                        visible: root.hoverIndex === parent.modelData.index && !root.lk("card", false) }
                                    Text {
                                        visible: root.chartData.kind === "changes"
                                        x: parent.modelData.value >= 0 ? parent.width+5 : -width-5
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: root.fmt(parent.modelData.value,1)+root.chartData.unit
                                        font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; color: root.ink2
                                    }
                                }
                            }
                            Repeater {
                                id: paths
                                model: seriesLayer.modelData.paths
                                onItemAdded: root.readinessRevision++
                                onItemRemoved: root.readinessRevision++
                                delegate: Shape {
                                    required property var modelData
                                    property var coordinates: root.visiblePath(modelData)
                                    onCoordinatesChanged: root.pathBuilds++
                                    width: 1000; height: 500
                                    x: -marks.x
                                    preferredRendererType: Shape.CurveRenderer
                                    transform: Scale { xScale: plot.width/1000; yScale: seriesLayer.height/500 }
                                    asynchronous: true
                                    onStatusChanged: root.readinessRevision++
                                    ShapePath {
                                        strokeColor: seriesLayer.seriesColor
                                        strokeWidth: (root.chartData.xs.length>400 ? 1 : root.lk("lineWidth", 2))*root.pixel
                                        cosmeticStroke: true
                                        fillColor: "transparent"
                                        PathPolyline { path: coordinates }
                                    }
                                    ShapePath {
                                        strokeColor: "transparent"
                                        fillColor: Qt.rgba(seriesLayer.seriesColor.r, seriesLayer.seriesColor.g, seriesLayer.seriesColor.b, root.lk("area", .10))
                                        PathPolyline { path: root.chartData.area && root.chartData.series.length===1 && root.chartData.xs.length<=400 && coordinates.length ?
                                            [Qt.point(coordinates[0].x,root.geometry.zero*500)].concat(coordinates).concat([Qt.point(coordinates[coordinates.length-1].x,root.geometry.zero*500),Qt.point(coordinates[0].x,root.geometry.zero*500)]) : [] }
                                    }
                                }
                            }
                            Repeater {
                                model: root.chartData.markers ? root.flattened(seriesLayer.modelData.paths) : []
                                delegate: Rectangle { required property var modelData
                                    x: modelData.x*seriesLayer.width-width/2; y: modelData.y*seriesLayer.height-height/2
                                    width: root.pointDiameter; height: width; radius: width/2; color: root.seriesColors[seriesLayer.index%8]
                                    border.width: 1.5*root.pixel; border.color: root.ground }
                            }
                        }
                    }
                    Image { id: mapImage; anchors.fill: parent; source: root.geometry ? root.geometry.image : ""; smooth: false
                        onStatusChanged: root.readinessRevision++ }
                    Rectangle {
                        visible: root.chartData.kind === "changes" && root.geometry
                        x: root.geometry ? root.geometry.zero*parent.width : 0
                        height: parent.height; width: root.pixel; color: root.colors.line
                    }
                    Rectangle {
                        visible: root.chartData.kind === "line" && root.chartData.mark_zero && root.geometry
                        x: 0; width: parent.width; y: root.geometry ? root.geometry.zero*parent.height : 0; height: root.pixel; color: root.colors.line
                    }
                    Item {
                        visible: !!(root.geometry && root.geometry.mark)
                        x: root.geometry && root.geometry.mark ? root.geometry.mark.position*parent.width : 0
                        width: 1; height: parent.height
                        ChartGuide { anchors.fill: parent; color: root.ink2 }
                        Text { x: 5; text: root.geometry && root.geometry.mark ? root.geometry.mark.label : ""
                            font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; color: root.ink2 }
                    }
                }
                Rectangle {
                    visible: root.hoverIndex>=0 && root.chartData.kind === "heatmap"
                    x: root.geometry ? root.hoverIndex/Math.max(1,root.geometry.columns)*plot.width : 0
                    y: root.geometry ? root.hoverRow/Math.max(1,root.geometry.rows)*plot.height : 0
                    width: root.geometry ? plot.width/Math.max(1,root.geometry.columns) : 0
                    height: root.geometry ? plot.height/Math.max(1,root.geometry.rows) : 0
                    color: "transparent"; border.color: root.ink; border.width: root.lk("card", false) ? 2 : 1; radius: root.lk("card", false) ? 2 : 0
                }
                Item {
                    visible: root.hoverIndex>=0 && root.chartData.kind === "line" && root.geometry
                    x: root.geometry ? ((root.chartData.xs[root.hoverIndex]-root.geometry.xmin)/(root.geometry.xmax-root.geometry.xmin)-root.viewStart)/(root.viewEnd-root.viewStart)*plot.width : 0
                    width: 1; height: parent.height
                    ChartGuide { anchors.fill: parent; color: root.ink2; visible: !root.lk("solidGuide", false) }
                    Rectangle { visible: root.lk("solidGuide", false); width: root.pixel; height: parent.height; color: root.ink2; opacity: .55 }
                    Repeater { model: parent.visible ? root.chartData.series : []
                        Rectangle { required property var modelData; required property int index
                            readonly property var value: modelData[1][root.hoverIndex]
                            visible: root.shown(modelData[0]) && value!==null && isFinite(value)
                            x: -width/2; y: root.geometry ? (root.geometry.ymax-value)/(root.geometry.ymax-root.geometry.ymin)*plot.height-height/2 : 0
                            width: root.hoverDiameter; height: width; radius: width/2; color: root.seriesColors[index%8]; border.width: 1.5*root.pixel; border.color: root.ground }
                    }
                }
                Rectangle {
                    visible: pointer.dragging && root.chartData.zoomable && pointer.pressedButtons===Qt.LeftButton
                    x: Math.min(pointer.startX,pointer.mouseX); width: Math.abs(pointer.mouseX-pointer.startX)
                    height: parent.height; color: root.colors.accent; opacity: .12
                }
            }
            MouseArea {
                id: pointer; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                property real startX: 0; property real startView: 0; property bool dragging: false
                onPositionChanged: mouse => {
                    root.inspect(mouse.x,mouse.y)
                    if (pressed && Math.abs(mouse.x-startX)>4) dragging=true
                    if (pressedButtons===Qt.MiddleButton && root.chartData.zoomable) {
                        let span=root.viewEnd-root.viewStart
                        root.viewStart=Math.max(0,Math.min(1-span,startView-(mouse.x-startX)/width*span))
                        root.viewEnd=root.viewStart+span
                    }
                }
                onExited: { root.readout=""; root.hoverIndex=-1; root.hoverRow=-1 }
                onWheel: wheel => { if (root.chartData.zoomable) root.zoom(Math.pow(1.02,-(wheel.angleDelta.y || wheel.angleDelta.x)/8),wheel.x/width); else wheel.accepted=false }
                onPressed: mouse => { startX=mouse.x; startView=root.viewStart; dragging=false }
                onReleased: mouse => {
                    if (dragging && mouse.button===Qt.LeftButton && root.chartData.zoomable) {
                        let span=root.viewEnd-root.viewStart; let start=root.viewStart
                        root.viewStart=Math.max(0,start+Math.min(startX,mouse.x)/width*span)
                        root.viewEnd=Math.min(1,start+Math.max(startX,mouse.x)/width*span)
                    }
                    dragging=false
                }
                onDoubleClicked: root.reset()
                onClicked: mouse => { if (mouse.button===Qt.RightButton) menu.popup() }
            }
            Rectangle {
                visible: root.chartData.kind === "heatmap"; x: parent.width+5; y: 0; width: 12; height: parent.height
                color: "transparent"
                Column {
                    anchors.fill: parent
                    Repeater { model: root.ramp.slice().reverse()
                        Rectangle { required property var modelData; width: parent.width; height: parent.height/root.ramp.length; color: modelData } }
                }
                Repeater { model: root.scaleTicks; Text { required property var modelData; x: 16; y: (1-modelData.position)*plot.height-height/2; text: modelData.label; color: root.colors.muted; font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION } }
                Text { x: 46; y: parent.height/2+width/2; rotation: -90; transformOrigin: Item.TopLeft; text: root.chartData.unit || ""; color: root.ink2; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
            }
        }
    }
    FontMetrics { id: cardStrong; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold }
    FontMetrics { id: cardPlain; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
    Rectangle {
        id: card; objectName: "hoverCard"
        parent: drawing
        visible: root.lk("card", false) && root.tip !== null && !root.tableMode
        readonly property var rows: root.tip ? root.tip.rows : []
        readonly property real valueWidth: Math.ceil(Math.max(0, ...rows.map(r => cardStrong.advanceWidth(r.value)),
            cardStrong.advanceWidth(root.tip && root.tip.total ? root.tip.total : "")))
        readonly property real nameWidth: Math.ceil(Math.max(0, ...rows.map(r => cardPlain.advanceWidth(r.name || "")),
            root.tip && root.tip.total ? cardPlain.advanceWidth(services.labels.total) : 0))
        readonly property real anchorX: plot.x + root.pointerX
        x: anchorX + 18 + width > drawing.width ? Math.max(0, anchorX - 18 - width) : anchorX + 18
        y: Math.max(0, Math.min(drawing.height - height, plot.y + root.pointerY - height/2))
        width: cardColumn.implicitWidth + 24; height: cardColumn.implicitHeight + 20
        radius: root.lk("cardRadius", 6); color: root.ch.card || root.colors.card || root.colors.panel
        border.width: 1; border.color: root.ch.cardLine || root.colors.line
        Column {
            id: cardColumn; x: 12; y: 10; spacing: 5
            Text { text: root.tip ? root.tip.title : ""; color: root.ink; font.family: Theme.fontFamily
                font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold; bottomPadding: 2 }
            Repeater {
                model: card.rows
                Row {
                    required property var modelData
                    spacing: Theme.space.M
                    Rectangle { width: 12; height: 3; radius: 1.5; anchors.verticalCenter: parent.verticalCenter
                        color: parent.modelData.color || "transparent"; visible: !!parent.modelData.color }
                    Text { width: card.valueWidth; horizontalAlignment: Text.AlignRight; text: parent.modelData.value
                        color: root.ink; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold
                        font.features: ({"tnum": 1}) }
                    Text { width: card.nameWidth; text: parent.modelData.name || ""; visible: card.nameWidth > 0; color: root.ink2
                        font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
                    Text { text: parent.modelData.share || ""; visible: text !== ""; color: root.muted
                        font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL; font.features: ({"tnum": 1}) }
                }
            }
            Rectangle { visible: !!(root.tip && root.tip.total); width: cardColumn.width; height: 1; color: root.ch.cardLine || root.colors.line }
            Row {
                visible: !!(root.tip && root.tip.total); spacing: 8
                Item { width: 12; height: 1 }
                Text { width: card.valueWidth; horizontalAlignment: Text.AlignRight; text: root.tip ? root.tip.total : ""
                    color: root.ink; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold
                    font.features: ({"tnum": 1}) }
                Text { text: services.labels.total; color: root.ink2; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
            }
        }
    }
    Loader {
        id: tableLoader
        anchors { left: parent.left; right: parent.right; top: buttons.bottom; bottom: parent.bottom; topMargin: Theme.space.S }
        active: root.tableVisited && !root.isEmpty
        visible: opacity>0
        opacity: root.tableMode && status===Loader.Ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : 90 } }
        sourceComponent: ResultTable { tableData: root.chartData.table; decimals: root.chartData.decimals || 0 }
    }
    Column {
        anchors.centerIn: parent; spacing: 12; visible: root.isEmpty
        Text { text: root.chartData.message || services.labels.empty; color: root.ink2; font.family: Theme.fontFamily; font.pixelSize: root.textSize }
        M.Button { anchors.horizontalCenter: parent.horizontalCenter; text: services.labels.calculate
            visible: !!root.chartData.action; font.family: Theme.fontFamily; onClicked: root.actionRequested(root.chartData.action) }
    }
    Text { anchors { bottom: parent.bottom; left: parent.left; margins: 10 } text: root.error; visible: !!text
        color: root.colors.text; font.family: Theme.fontFamily; font.pixelSize: root.textSize }
    M.Menu {
        id: menu; font.family: Theme.fontFamily; font.pixelSize: root.textSize
        M.MenuItem { text: services.labels.all; enabled: root.chartData.zoomable || false; onTriggered: root.reset() }
        M.MenuItem { text: services.labels.svg; enabled: !root.isEmpty; onTriggered: { root.exportKind="svg"; saveDialog.open() } }
        M.MenuItem { text: services.labels.png; enabled: !root.isEmpty; onTriggered: { root.exportKind="png"; saveDialog.open() } }
    }
    FileDialog {
        id: saveDialog; fileMode: FileDialog.SaveFile
        title: root.exportKind === "svg" ? services.labels.svg : services.labels.png
        nameFilters: root.exportKind === "svg" ? ["SVG (*.svg)"] : ["PNG (*.png)"]
        defaultSuffix: root.exportKind
        onAccepted: services.exportChart(root.chartData,selectedFile,Theme.fontFamily,root.hiddenSeries,root.viewStart,root.viewEnd)
    }
}
