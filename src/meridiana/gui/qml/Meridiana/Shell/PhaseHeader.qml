import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: header
    property string phase: "model"
    property string leavingPhase: ""
    property bool fileOpen: false
    property bool dirty: false          // R537: something to save, the dot on File (VS Code's on a tab, study 38)
    property string selectedTool: "select"
    property string barMode: "under"
    property bool barVisible: !fileOpen
    property var phases: shell.phases
    property int currentIndex: Math.max(0, phases.findIndex(p => p.id === phase))
    property var metrics: shell.metrics
    // The corner controls have a 4 px bottom margin in Widgets: their row is
    // 34 px, with the 32 px tab bar aligned to its bottom.
    property real rowHeight: metrics.tabHeight + Theme.space.XXS
    property real fileWidth: fileButton.width + Theme.space.L
    property real tailWidth: variants.width + Theme.space.XL
    property var stalePhases: shell.stalePhases
    property url trailingSource: ""
    property bool trailingCanMove: true
    // R375: the button of «3D object», which the picker hangs from (Workbench.openObjects)
    property Item objectTool: null
    readonly property bool trailingShown: trailing.visible
    // its part is still being made (an asynchronous Loader): whether it fits is not known yet
    readonly property bool trailingLoading: trailing.status === Loader.Loading
    function phaseTitle(p) { return p.title+(stalePhases.includes(p.id) ? " ·" : "") }
    // R502: the same margin before the disc, after the name and above the disc (the disc is centred in the tab:
    // (tabHeight - badge) / 2 is that margin), ControlMetrics.inset; the width is the name's in the open tab's weight,
    // so that a tab keeps its width when it opens. R555 (2) (Daniel 08/11/2026: «lo spazio tra la scritta e il cerchio
    // col numero uguale ai margini esterni della linguetta»): the disc and the name's ink are as far apart as the
    // outline and the disc, pad less the outline's hair line; the name's own room before its first letter (the font's
    // side bearing, read by nameMetrics) is taken off the gap, so the ink and not the letter's box keeps the margin.
    readonly property real pad: M.ControlMetrics.inset
    FontMetrics { id: nameMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.text.strong.size; font.weight: Theme.text.strong.weight }
    function nameGap(p) { const revision = Theme.revision
        return Math.max(0, pad - Theme.line.HAIR - Math.max(0, nameMetrics.tightBoundingRect(phaseTitle(p)).x)) }
    property var widths: phases.map(p => 2*pad + metrics.badge + nameGap(p) + Math.ceil(Theme.measureText(phaseTitle(p), "strong", false).width))
    property bool compact: width < fileWidth + widths.reduce((a,b) => a+b, 0) + tailWidth
    readonly property real dotWidth: Math.ceil(Theme.measureText("·", "control", false).width)
    function tabWidth(i) { return compact && i !== currentIndex ? metrics.badge + 2*pad+(stalePhases.includes(phases[i].id) ? Theme.space.M+dotWidth : 0) : widths[i] }
    function tabX(i) { let x=fileWidth; for(let j=0;j<i;j++) x+=tabWidth(j); return x }
    // The tool in hand a command stands for, "" for a command run once (docs/design/sistema-grafico.md §4: only a mode
    // goes on a split button's face)
    function toolOf(command) { return command.startsWith("tool_") ? command.slice(5) : command==="strings_manual" ? "string" : "" }
    function toolMatches(command) { const tool=toolOf(command); return tool!=="" && tool===selectedTool }
    // R614 (Daniel 14/11/2026: «Measure» twice as wide as «Square», with air between the word and the arrow): the words
    // that can stand on the face, the button's own and the modes of its menu; a command run once, as «Remove all
    // measurements», and what a fixed button holds stay in the menu and never widen the button. They are measured in the
    // condensed face the button writes them in, as the plain buttons' (the split ones were measured in the wider one).
    function faceWords(tool) { return [tool].concat(tool.fixed ? [] : tool.more.filter(t=>toolOf(t.command)!=="")).map(t=>t.label) }
    function commandWidth(tool, mode=barMode) {
        if(mode==="icons") return Theme.bar.ICON_WIDTH
        const word=Math.max(...faceWords(tool).map(w=>Math.round(Theme.measureText(w,"secondary",true).width)))
        const need=word+Theme.bar.PAD+(mode==="beside" ? Theme.bar.ICON.beside+Theme.bar.WORD_GAP : 0)
        return Math.max(mode==="under" ? Theme.bar.WORD_MIN : 0,Math.ceil(need/Theme.bar.STEP[mode])*Theme.bar.STEP[mode])
    }
    readonly property var layoutNeeds: {
        const result={}
        for(const mode of ["under","beside","icons"]) {
            result[mode]={}
            for(const phase of phases) {
                let width=2*Theme.space.XS+Math.max(0,phase.groups.length-1)*(Theme.line.HAIR+2*Theme.bar.GROUP_AIR)
                for(const group of phase.groups) {
                    const row=group.tools.reduce((sum,t)=>sum+commandWidth(t,mode)+(t.more.length ? Theme.bar.STRIP : 0),0)+Math.max(0,group.tools.length-1)*Theme.bar.GAP
                    width+=mode==="beside" ? row : Math.max(row,Theme.measureText(group.title,"group",true).width)
                }
                result[mode][phase.id]=width
            }
        }
        return result
    }
    signal phaseChosen(string phase)
    signal fileRequested()
    // R23 F6 (docs/studio/39): the dot of a stale computation or layout on Plant's compute and on Layout (R564: «Fill» is in
    // its menu), made as a child of the tool's button when the Plant part is there
    function staleMark(button, command) {
        if (typeof plantBackend === "undefined" || !plantBackend || (command !== "compute" && command !== "tool_subfield")) return
        const mark = Qt.createComponent("../Plant/StaleMark.qml")
        if (mark.status === Component.Ready) mark.createObject(button, {backend: plantBackend, command: command})
        else console.warn(mark.errorString())
    }
    property real buttonHeight: barMode === "under" ? Theme.bar.ICON.under + Math.round(Theme.measureText("Ag", "strong", true).height) + 2*Theme.space.XS + Theme.space.XXS : Theme.bar.HEIGHT
    property real groupHeight: buttonHeight + (barMode === "beside" ? 0 : Theme.space.XS + Math.round(Theme.measureText("Ag", "group", true).height))
    // R502: the bar's tools start ControlMetrics.inset from the card's left side and top, as the summary ends from its
    // right side; the tools' row is groupHeight + 1 tall, with the card's bottom padding under the groups' titles.
    implicitHeight: rowHeight + (barVisible ? pad + groupHeight + 1 + metrics.cardPad[3] : 0)

    Rectangle {
        visible: !header.fileOpen && !header.barVisible
        x: header.tabX(header.currentIndex)+0.5; y: header.rowHeight-header.metrics.tabHeight+0.5
        width: header.tabWidth(header.currentIndex)-1; height: header.metrics.tabHeight-1
        radius: Theme.radius.CARD; color: Theme.colors.panel; border.color: Theme.colors.card_line
    }

    Shape {
        id: outline
        objectName: "phaseOutline"
        preferredRendererType: Shape.CurveRenderer
        antialiasing: true
        visible: header.barVisible
        anchors.fill: parent
        property real tx: header.tabX(header.currentIndex)
        property real tw: header.tabWidth(header.currentIndex)
        property real tabTop: header.rowHeight-header.metrics.tabHeight+0.5
        property real r: Theme.radius.CARD
        property real h: header.rowHeight + 0.5
        // the tab's marker slides to the phase chosen only with the phase animations on (Theme.phaseMotion)
        Behavior on tx { enabled: Theme.phaseMotion; NumberAnimation { duration: Theme.motion.FAST; easing.type: Theme.motion.EASE } }
        Behavior on tw { enabled: Theme.phaseMotion; NumberAnimation { duration: Theme.motion.FAST; easing.type: Theme.motion.EASE } }
        ShapePath {
            fillColor: Theme.colors.panel
            strokeColor: Theme.colors.card_line
            strokeWidth: Theme.line.HAIR
            startX: outline.r+0.5; startY: outline.h
            PathLine { x: outline.tx+0.5-outline.r; y: outline.h }
            PathArc { x: outline.tx+0.5; y: outline.h-outline.r; radiusX: outline.r; radiusY: outline.r; direction: PathArc.Counterclockwise }
            PathLine { x: outline.tx+0.5; y: outline.tabTop+outline.r }
            PathArc { x: outline.tx+0.5+outline.r; y: outline.tabTop; radiusX: outline.r; radiusY: outline.r }
            PathLine { x: outline.tx+outline.tw-0.5-outline.r; y: outline.tabTop }
            PathArc { x: outline.tx+outline.tw-0.5; y: outline.tabTop+outline.r; radiusX: outline.r; radiusY: outline.r }
            PathLine { x: outline.tx+outline.tw-0.5; y: outline.h-outline.r }
            PathArc { x: outline.tx+outline.tw-0.5+outline.r; y: outline.h; radiusX: outline.r; radiusY: outline.r; direction: PathArc.Counterclockwise }
            PathLine { x: header.width-0.5-outline.r; y: outline.h }
            PathArc { x: header.width-0.5; y: outline.h+outline.r; radiusX: outline.r; radiusY: outline.r }
            PathLine { x: header.width-0.5; y: header.height-0.5-outline.r }
            PathArc { x: header.width-0.5-outline.r; y: header.height-0.5; radiusX: outline.r; radiusY: outline.r }
            PathLine { x: outline.r+0.5; y: header.height-0.5 }
            PathArc { x: 0.5; y: header.height-0.5-outline.r; radiusX: outline.r; radiusY: outline.r }
            PathLine { x: 0.5; y: outline.h+outline.r }
            PathArc { x: outline.r+0.5; y: outline.h; radiusX: outline.r; radiusY: outline.r }
        }
    }
    // R555 (3) (Daniel 08/11/2026: «File: hover e riempimento premuto con le stesse dimensioni degli hover delle linguette
    // delle fasi»): its hover and its press are a tab's: the same top and height (tabHeight less Theme.space.XXS above and
    // below) and the same margin from their sides to what is inside (inset less Theme.space.XXS, as a tab's hover round
    // its disc and its name).
    M.Button {
        id: fileButton
        objectName: "fileButton"
        readonly property real margin: header.pad - Theme.space.XXS
        x: 0; y: header.rowHeight - header.metrics.tabHeight + Theme.space.XXS
        width: Math.ceil(fileFace.implicitWidth) + 2 * margin; height: header.metrics.tabHeight - 2 * Theme.space.XXS
        padding: 0; leftPadding: margin; rightPadding: margin
        checked: header.fileOpen
        text: L.file; iconName: "folder-open"; flat: true; onClicked: header.fileRequested()
        tip: header.dirty ? L.unsaved : ""
        contentItem: Item { Row { id: fileFace; anchors.centerIn: parent; spacing: Theme.space.XS
            M.Icon { id: fileIcon; iconName: "folder-open"; width: Theme.icon.CONTROL-1; height: width; anchors.verticalCenter: parent.verticalCenter
                // R537: the dot of «modified», in the accent, lit by a change, off once saved; R555 (3): on the
                // folder's corner, so that the button's margins stay the same with it and without it
                Rectangle { objectName: "fileDirtyDot"; visible: header.dirty; width: 6; height: 6; radius: 3
                    color: Theme.colors.accent; x: parent.width - width / 2 - 1; y: -1
                    border.width: Theme.line.HAIR; border.color: Theme.colors.window }
            }
            M.Label { text: L.file; textStyle: "strong"; anchors.verticalCenter: parent.verticalCenter }
        } }
    }
    // R705 (Daniel 17/11/2026: «come nel widget, scorrere tra le fasi con la rotella del mouse quando ho il puntatore
    // sulle linguette»): as a QTabBar, the wheel up goes to the phase before, down to the one after, with no wrap at the
    // ends; a high-resolution wheel's small steps add up to a notch (120). The mouse's wheel only: two fingers on a
    // touchpad (events in scroll phases, also Windows' touchpad as WindowsTouchpad hands it on) brushing the tabs would
    // change phase by mistake, and Wayland's touchpad steps are multiplied by 2,5 (TouchpadPace)
    readonly property real tabsEnd: phases.length ? tabX(phases.length - 1) + tabWidth(phases.length - 1) : 0
    property real wheelCarry: 0
    function wheelPhases(event) {
        if (event.phase !== Qt.NoScrollPhase) return
        wheelCarry += event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x
        const steps = wheelCarry > 0 ? Math.floor(wheelCarry / 120) : Math.ceil(wheelCarry / 120)
        if (steps === 0) return
        wheelCarry -= steps * 120
        const to = Math.max(0, Math.min(phases.length - 1, currentIndex - steps))
        if (to !== currentIndex || fileOpen) phaseChosen(phases[to].id)
    }
    Item {
        objectName: "phaseTabsWheel"
        x: header.fileWidth; width: Math.max(0, header.tabsEnd - header.fileWidth); height: header.rowHeight
        WheelHandler {
            target: null
            acceptedDevices: PointerDevice.Mouse
            onWheel: function(event) { header.wheelPhases(event) }
        }
    }
    Repeater {
        model: header.phases
        delegate: Item {
            id: phaseTab
            required property var modelData
            required property int index
            readonly property bool selected: header.currentIndex === index && !header.fileOpen
            // R555 (11): its corners for Meridio's highlight (AssistantLayer.radiiOf): open, the outline's at the top
            // (its hair line is half a line inside) and none at the bottom, where it goes on into the bar; closed, its
            // hover's, Theme.space.XXS inside
            readonly property var highlightRadii: selected ? [outline.r + Theme.line.HAIR / 2, outline.r + Theme.line.HAIR / 2, 0, 0]
                                                           : Array(4).fill(Theme.radius.CONTROL + Theme.space.XXS)
            objectName: modelData.id + "Tab"
            x: header.tabX(index); y: header.rowHeight-height; width: header.tabWidth(index); height: header.metrics.tabHeight
            Rectangle {
                // R502: the hover hugs the disc and the name as the open tab does, in the weight shown (a closed tab's
                // name is lighter, so narrower than the width kept for it). R519 (Daniel 07/11/2026: «quando si
                // trovano a sinistra della linguetta selezionata sembra che lascino un po' di spazio in più»): the disc
                // and the name stand on the side of the open tab, the room the lighter name leaves on the far side, so
                // the hover is Theme.space.XXS from the open tab whether it is at its left or at its right.
                objectName: modelData.id + "TabHover"
                x: content.x - header.pad + Theme.space.XXS; y: Theme.space.XXS; height: parent.height - 2*Theme.space.XXS
                width: Math.min(parent.width, content.width + 2*header.pad) - 2*Theme.space.XXS
                radius: Theme.radius.CONTROL
                color: tabMouse.pressed ? Theme.colors.press : tabMouse.containsMouse ? Theme.colors.hover : "transparent"
                visible: header.fileOpen || header.currentIndex !== phaseTab.index
            }
            Row {
                id: content
                x: !header.fileOpen && phaseTab.index < header.currentIndex ? Math.max(header.pad, parent.width - width - header.pad) : header.pad
                Behavior on x { enabled: Theme.phaseMotion; NumberAnimation { duration: Theme.motion.FAST; easing.type: Theme.motion.EASE } }
                anchors.verticalCenter: parent.verticalCenter; spacing: header.nameGap(phaseTab.modelData)
                Rectangle {
                    width: header.metrics.badge; height: width; radius: width/2; anchors.verticalCenter: parent.verticalCenter
                    color: header.currentIndex === phaseTab.index && !header.fileOpen ? Theme.colors.accent : Theme.colors.line_soft
                    Shape { anchors.fill: parent; preferredRendererType: Shape.CurveRenderer; antialiasing: true
                        ShapePath { strokeWidth: -1
                            fillColor: header.currentIndex === phaseTab.index && !header.fileOpen ? Theme.colors.accent_fg : Theme.colors.muted
                            PathSvg { path: shell.glyphPath(Theme.fontFamily,Theme.text.label.size,Theme.text.label.weight,phaseTab.modelData.number,header.metrics.badge) }
                        }
                    }
                }
                M.Label { text: header.compact && header.currentIndex!==phaseTab.index ? "·" : header.phaseTitle(phaseTab.modelData); anchors.verticalCenter: parent.verticalCenter
                    textStyle: header.currentIndex === phaseTab.index && !header.fileOpen ? "strong" : "control"
                    color: header.currentIndex === phaseTab.index && !header.fileOpen || tabMouse.containsMouse ? Theme.colors.text : Theme.colors.text2
                    visible: !header.compact || header.currentIndex === phaseTab.index || header.stalePhases.includes(phaseTab.modelData.id) }
            }
            MouseArea { id: tabMouse; anchors.fill: parent; hoverEnabled: true
                onClicked: header.phaseChosen(phaseTab.modelData.id) }
            M.ToolTip { pressed: tabMouse.pressed; visible: tabMouse.containsMouse && (header.compact || header.stalePhases.includes(phaseTab.modelData.id))
                text: (header.compact ? phaseTab.modelData.title : "")+(header.stalePhases.includes(phaseTab.modelData.id) ? (header.compact ? "\n" : "")+shell.staleTip : "") }
            Accessible.role: Accessible.PageTab
            Accessible.name: modelData.title
            Accessible.selected: selected
        }
    }
    Row {
        id: variants
        property var shown: shell.variants.length<=4 ? shell.variants : shell.variants.filter(v=>v.id===shell.currentVariant || shell.variants.filter(o=>o.id!==shell.currentVariant).slice(0,3).some(o=>o.id===v.id))
        anchors.right: parent.right; y: (header.rowHeight-height-Theme.space.XS)/2
        spacing: Theme.space.XXS
        M.Segments { objectName: "variantBar"; model: variants.shown
            currentIndex: variants.shown.findIndex(v => v.id === shell.currentVariant)
            onActivated: index => shell.chooseVariant(variants.shown[index].id) }
        M.Button { visible: shell.variants.length>4; text: "…"; flat: true; onClicked: otherVariants.open()
            M.Menu { id: otherVariants; y: parent.height
                Repeater { model: shell.variants.filter(v=>!variants.shown.some(s=>s.id===v.id))
                    M.MenuItem { required property var modelData; text: modelData.text; onTriggered: shell.chooseVariant(modelData.id) }
                }
            }
        }
        M.Button { objectName: "variantAdd"; iconName: "plus"; flat: true; tip: L.newVariant
            padding: M.ControlMetrics.toolPad
            width: Theme.size.CHIP; height: Theme.size.CHIP; anchors.verticalCenter: parent.verticalCenter
            contentItem: M.Icon { iconName: "plus"; width: Theme.icon.CONTROL-2; height: width }
            onClicked: shell.trigger("new_variant") }
        TapHandler { acceptedButtons: Qt.RightButton; onTapped: variantMenu.open() }
        M.Menu { id: variantMenu; y: variants.height
            M.MenuItem { text: shellTasks.labels.newVariant; onTriggered: shell.trigger("new_variant") }
            M.MenuItem { text: shellTasks.labels.renameVariant; onTriggered: shell.variantRequested("rename") }
            M.MenuItem { text: shellTasks.labels.deleteVariant; onTriggered: shell.variantRequested("delete") }
            M.MenuSeparator { }
            M.MenuItem { text: shellTasks.labels.compare; onTriggered: shell.trigger("compare_variants") }
        }
    }
    Loader {
        id: trailing
        objectName: "phaseTrailing"
        // Keep the summary and its controls when another phase has no trailing part.
        property url cachedSource: ""
        source: cachedSource
        function remember() { if (header.trailingSource.toString() !== "") cachedSource = header.trailingSource }
        Component.onCompleted: remember()
        Connections { target: header; function onTrailingSourceChanged() { trailing.remember() } }
        asynchronous: GraphicsInfo.api !== GraphicsInfo.Software
        // The room the tools leave, up to a measure; under 300 px, or under what the part asks (its `need`, R553: the
        // shadows of Production side by side), it goes above the plan (Workbench). Made while the bar is shown, so
        // that its need is known; seen only when it fits, or always where there are no views to stand above
        // (Production): there the part makes do with the room.
        readonly property real room: toolbar.parent.width - 2 * toolbar.x - groups.width - Theme.space.XL
        readonly property real need: item && item.need !== undefined ? item.need : 0
        readonly property bool fits: room >= Math.max(300 * Theme.type.BODY / 13, need) || (!header.trailingCanMove && room > 0)
        visible: header.barVisible && header.trailingSource.toString() !== "" && fits && status === Loader.Ready
        x: parent.width - width - header.pad; y: toolbar.y
        width: Math.min(720 * Theme.type.BODY / 13, room); height: toolbar.height - Theme.space.XXS
    }
    Flickable {
        id: toolbar
        objectName: "phaseToolbar"
        visible: header.barVisible
        x: header.pad; y: header.rowHeight + header.pad
        width: parent.width-2*x-(trailing.visible ? trailing.width+Theme.space.L : 0); height: parent.height-y-header.metrics.cardPad[3]
        contentWidth: groups.width; contentHeight: height; clip: true
        boundsBehavior: Flickable.StopAtBounds
        Item {
            id: groups
            width: { const row=phaseRows.itemAt(header.currentIndex); return row ? row.implicitWidth : 0 }
            height: toolbar.height
            // One row of groups for each phase, built once and shown for its phase (06/11/2026): a change of phase
            // used to build the bar again, 35-42 items each time.
            Repeater {
                id: phaseRows
                model: header.phases
                delegate: Row {
                    id: phaseGroups
                    required property var modelData
                    required property int index
                    readonly property var phaseGroupsList: modelData.groups
                    readonly property string phaseId: modelData.id
                    M.PhaseFade { current: phaseGroups.index === header.currentIndex; leaving: phaseGroups.modelData.id === header.leavingPhase }
                    spacing: Theme.bar.GROUP_AIR
            Repeater {
                model: phaseGroups.phaseGroupsList
                delegate: Row {
                    required property var modelData
                    required property int index
                    spacing: Theme.bar.GROUP_AIR
                    Column {
                        spacing: Theme.space.XS
                        Row {
                            spacing: Theme.bar.GAP
                            Repeater {
                                model: modelData.tools
                                delegate: Loader {
                                    id: toolLoader
                                    required property var modelData
                                    property var family: [modelData].concat(modelData.more)
                                    property var face: !modelData.fixed ? (family.find(t=>header.toolMatches(t.command)) || modelData) : modelData
                                    sourceComponent: modelData.more.length ? splitTool : plainTool
                                    Component {
                                        id: plainTool
                                        PhaseToolButton {
                                            objectName: "tool_" + toolLoader.modelData.command
                                            primary: toolLoader.modelData.primary
                                            text: toolLoader.face.label; iconName: toolLoader.face.icon
                                            tip: toolLoader.face.tip; mode: header.barMode
                                            height: header.buttonHeight
                                            width: header.commandWidth(toolLoader.modelData)
                                            enabled: toolLoader.modelData.enabled && shell.commandEnabled[toolLoader.modelData.command]!==false
                                            active: header.toolMatches(toolLoader.modelData.command) || (toolLoader.modelData.command==="tool_building" && header.selectedTool==="rectangle")
                                            onClicked: shell.trigger(toolLoader.modelData.command)
                                            // R23 F6: Plant's stale mark (header.staleMark) made here, not from Python
                                            Component.onCompleted: { if (toolLoader.modelData.command === "object_3d") header.objectTool = this; header.staleMark(this, toolLoader.modelData.command) }
                                        }
                                    }
                                    Component {
                                        id: splitTool
                                        PhaseSplitButton {
                                            objectName: "tool_" + toolLoader.modelData.command
                                            text: toolLoader.face.label; iconName: toolLoader.face.icon
                                            tip: toolLoader.face.faceTip; stripTip: toolLoader.modelData.stripTip; mode: header.barMode
                                            height: header.buttonHeight
                                            width: header.commandWidth(toolLoader.modelData)+Theme.bar.STRIP
                                            enabled: toolLoader.modelData.enabled || toolLoader.modelData.more.some(t => t.enabled)
                                            mainEnabled: toolLoader.face.enabled && shell.commandEnabled[toolLoader.face.command]!==false
                                            active: header.toolMatches(toolLoader.face.command)
                                            stripActive: toolLoader.family.some(t=>t.command!==toolLoader.face.command && header.toolMatches(t.command))
                                            model: toolLoader.family
                                            onClicked: shell.trigger(toolLoader.face.command)
                                            onChosen: index => shell.trigger(toolLoader.family[index].command)
                                            Component.onCompleted: header.staleMark(this, toolLoader.modelData.command)
                                        }
                                    }
                                }
                            }
                        }
                        M.Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.title
                            textStyle: "group"; condensed: true; visible: header.barMode !== "beside" }
                    }
                    Rectangle { visible: index < phaseGroups.phaseGroupsList.length-1
                        width: Theme.line.HAIR; height: header.buttonHeight; color: Theme.colors.line_soft }
                }
            }
                }
            }
        }
    }
}
