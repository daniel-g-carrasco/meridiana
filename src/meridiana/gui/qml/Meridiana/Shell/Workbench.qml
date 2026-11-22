import QtQuick
import QtQuick.Controls as T
import QtQuick.Layouts
import QtQuick.Shapes
import QtQml.Models
import Meridiana.Theme
import Meridiana.Controls as M
import "../../.." as Prototype

T.ApplicationWindow {
    id: root
    objectName: "quickWindow"
    width: 1600; height: 960; minimumWidth: 800; minimumHeight: 560
    visible: false; title: L.title; color: Theme.colors.window
    // with unsaved changes the closing waits for the answer to «Save the changes?» (backend/closing_part.py)
    onClosing: (close) => {
        if (typeof closingBackend !== "undefined" && closingBackend && !closingBackend.mayClose()) { close.accepted = false; return }
        shell.closeRequested()
    }
    font.family: Theme.fontFamily; font.pixelSize: Theme.type.BODY
    property string phase: "model"
    property string leavingPhase: ""
    property string displayedPhase: "model"
    function phaseChanging() {
        phaseExit.stop()
        const ids = shell.phases.map(p => p.id)
        leavingPhase = Theme.phaseMotion && !fileShown && ids.includes(phase) && ids.includes(displayedPhase) && phase !== displayedPhase ? displayedPhase : ""
        displayedPhase = phase
        if (leavingPhase) phaseExit.start()
    }
    SequentialAnimation {
        id: phaseExit
        PauseAnimation { duration: Theme.motion.FAST }
        ScriptAction { script: root.leavingPhase = "" }
    }
    Connections { target: Theme; function onPhaseMotionChanged() { if (!Theme.phaseMotion) { phaseExit.stop(); root.leavingPhase = "" } } }
    property var visitedPhases: ["model"]
    // The pages of the other phases are made a little at a time once the window is up, so that the first time a phase
    // is entered does not stop everything for a second or two; entered before, the Loader finishes at once.
    property bool pagesWarm: false
    Timer { id: warmWait; interval: 1200; running: root.visible && !root.pagesWarm && !!root.partSources.plan; onTriggered: root.warmPages() }
    // Not while the models under them are still changing: a list reset during the incubation is lost work and a warning.
    Connections { target: backend; enabled: !root.pagesWarm; function onSceneChanged() { if(warmWait.running) warmWait.restart() } }
    function warmPages() {
        pagesWarm=true
        // Not the report: its lists change under the incubator (Qt: «destroyed during incubation»), it is made on entry.
        for(const p of shell.phases) if(p.id!=="report" && !visitedPhases.includes(p.id)) { visitedPhases=visitedPhases.concat([p.id]); inspectorPhases.append({phaseId:p.id}) }
    }
    ListModel { id: inspectorPhases; ListElement { phaseId: "model" } }
    signal phaseSelected(string phase)
    // Plant opens on the plan alone, as in the Widgets; its 3D and split are chosen there (R402) and kept for the phase.
    property var viewOfPhase: ({plant:"plan"})
    property string viewPhase: "model"
    function followView() {
        if(!["model","plant"].includes(phase) || phase===viewPhase) return
        viewOfPhase[viewPhase]=viewMode; viewPhase=phase
        viewMode=viewOfPhase[phase] || "both"
    }
    onPhaseChanged: { phaseChanging(); M.Help.close(); followView(); if(!visitedPhases.includes(phase)) { visitedPhases=visitedPhases.concat([phase]); inspectorPhases.append({phaseId:phase}) }; workspace.arrangementChanged(); arrangeTimer.restart(); phaseSelected(phase) }
    property bool fileOpen: false
    property bool fileShown: false
    // R537: something to save (the « *» of the title, app.py _retitle, measured once per change): the dot on File
    property bool projectDirty: shell.projectDirty
    // R549: a size changed while File was open is arranged once it closes (arrange waits for it)
    onFileOpenChanged: { M.Help.close(); shell.fileRequested(fileOpen); if(!fileOpen) arrangeTimer.restart() }
    property real fileMotionTop: menus.height+phaseHeader.rowHeight
    property real fileMotionBottom: footer.height
    // R483: the old page as a still picture over the window (backend/shell_motion.FileMotion.cover), faded out once the
    // new page under it has been drawn (the first frame after the change), then frame by frame (at most 12 % in one, so a
    // slow frame slows it and does not skip it), Theme.motion.FAST with a soft end. R521 (Daniel 07/11/2026: «nello
    // spostamento tra le fasi, l'animazione non deve fare quel fastidioso spostamento da destra a sinistra»): a fade
    // alone, nothing slides, forwards or back, to File or from it
    // r24-fasi (studio 41, S1): no picture of the old page any more. It was Item.grabToImage of the whole window
    // (3200 x 1920 on the Dell, read back from the card and uploaded again), 40-105 ms more to every change; a picture
    // drawn on the card (ShaderEffectSource, tried in this branch, docs/quick/stato/r24-fasi.md) still cost two frames
    // of waiting and the window drawn twice, and gained 0-25 ms. Now the new page comes at once and fades in from the
    // window's ground (fileVeil, a plain veil of the ground's colour fading out over it): a fade alone, nothing slides
    // (R483, R521). Never the synchronous grabWindow() (R21 F6c: it blocked for ever on lucciola leaving Relazione).
    function captureFileMotion(serial, direction) {
        // r23-unita: a window not yet laid out (as a test's hidden window): the change goes on unveiled
        if (root.contentItem.parent.width < 1 || root.contentItem.parent.height < 1) { motion.covered(serial, false); return }
        fileVeil.direction = direction || 1
        motion.covered(serial, true)
    }
    function beginVeil() { fileVeil.t=0; fileVeil.waitFrames=1; fileVeil.running=true; root.requestUpdate() }
    function applyPhase(value) {
        if(fileOpen || fileShown) displayedPhase=value
        workspace.rememberPhase()
        fileOpen=false; fileShown=false; phase=value
    }
    function applyFile(opened) { fileShown=opened }
    function playFileMotion(_after, _entering) { }
    function stopFileMotion() { fileVeil.running=false }
    // R23 F6 (docs/studio/39-contratto-backend-qml.md): the backend's requests to the window, answered here; the items
    // are visited by name in QML (findNamed, in order, as AssistantHost.find), never from Python
    function findNamed(name) {
        let top = root.contentItem
        while (top.parent) top = top.parent
        const pending = [top]
        while (pending.length) {
            const item = pending.pop()
            if (item.objectName === name) return item
            const kids = item.children || []
            for (let i = kids.length - 1; i >= 0; i--) pending.push(kids[i])
        }
        return null
    }
    Connections {
        target: shell
        function onViewModeRequested(mode) { root.viewMode = mode }
        function onFileOpenRequested(opened) { root.fileOpen = opened }
        function onPanelRequested(id) {
            const p = workspace.panels.find(p => p.panelId === id)
            if (!p) return
            p.opened = true
            workspace.selectPanel(id)
        }
        function onFocusRequested(name) { const item = root.findNamed(name); if (item) item.forceActiveFocus(Qt.ShortcutFocusReason) }
        function onToolbarModeRequested(mode) { root.toolbarMode = mode }
        function onToolbarPositionRequested(place) { root.toolbarPosition = place }
        function onMenuBarRequested(open, always) { if (always !== null && always !== undefined) root.menuAlways = always; root.menuOpen = open }
    }
    Binding { target: shell; property: "planStatus"; value: root.planItem && root.planItem.statusText !== undefined ? root.planItem.statusText : "" }
    Binding { target: root.planItem; property: "viewMode"; value: root.viewMode; when: !!root.planItem && root.planItem.viewMode !== undefined }
    property bool menuOpen: false
    property bool menuAlways: false
    property var barMenu: null          // the menu of the bar now open (R475)
    property bool altArmed: false
    // R317, R527: Alt held while a card is carried makes the middle of the card under the pointer a tab. Told by the
    // window's filter (backend/window_frame.AltTap.held), down and up, so the target answers with the mouse still.
    property bool altHeld: false
    function setAltHeld(down) { if(altHeld===!!down) return; altHeld=!!down; workspace.retarget() }
    function altPressed(event) {
        if(event.key===Qt.Key_Alt) setAltHeld(true)
        if(event.key===Qt.Key_Alt && !(event.modifiers & Qt.ControlModifier) && !workspace.draggedPanel) { altArmed=true; event.accepted=true }
        else altArmed=false
    }
    function altReleased(event) {
        // with the window's filter (backend/window_frame.AltTap, R481) the tap comes to altTapped and its release
        // never gets here; this is for a workbench made without it
        if(event.key===Qt.Key_Alt) setAltHeld(false)
        if(event.key===Qt.Key_Alt && altArmed && !workspace.draggedPanel) { altArmed=false; event.accepted=true; altTapped() }
    }
    // R481: Alt alone, wherever the focus is. Hidden: the bar shows with the focus on its first title. Shown: it hides
    // (a menu of it closed first) and the focus goes back where it was. Always shown (menuAlways): the focus goes to
    // it and back.
    property var focusBeforeMenu: null
    readonly property bool menuFocused: { const f=root.activeFocusItem; let n=f; while(n) { if(n===menus) return true; n=n.parent } return false }
    function altTapped() {
        const showing = menuAlways ? !menuFocused && !(barMenu && barMenu.visible) : !menuOpen
        if(showing) {
            focusBeforeMenu = root.activeFocusItem
            menuOpen = true
            focusMenu(0)
        } else {
            if(barMenu && barMenu.visible) barMenu.close()
            menuOpen = menuAlways
            returnFocus()
        }
    }
    function returnFocus() {
        const back = focusBeforeMenu
        focusBeforeMenu = null
        if(back && back.visible && back.enabled !== false) back.forceActiveFocus()
        else workspace.forceActiveFocus()
    }
    // a click outside the bar hides it, as Esc does (the click takes the focus where it lands)
    function pointerPressedAt(x, y) {
        if(!menuOpen || menuAlways || (barMenu && barMenu.visible)) return
        const p = menus.mapFromItem(null, x, y)
        if(p.x < 0 || p.y < 0 || p.x > menus.width || p.y > menus.height) { menuOpen = false; focusBeforeMenu = null }
    }
    function focusMenu(index) {
        const button=menuEntries.itemAt((index+menuEntries.count)%menuEntries.count)
        if(button) button.forceActiveFocus(Qt.MenuBarFocusReason)
    }
    // R597: the phase shown, for the help of the card's «?» (help_part.HelpBook.cardKey)
    Binding { target: typeof helpBook !== "undefined" ? helpBook : null; property: "phase"; value: root.phase; when: target !== null }
    property bool helpOpen: false
    property point mascotHome: Qt.point(0,0)
    property bool helpMoving: false
    onHelpOpenChanged: {
        helpMoving=true
        if(helpOpen) {
            mascotHome=Qt.point(meridio.x,meridio.y)
            meridio.x=Math.max(Theme.space.L,workspace.slot("right").x-meridio.width)
            meridio.y=Math.max(header.height+Theme.space.L,root.height/3)
        } else { meridio.x=mascotHome.x; meridio.y=mascotHome.y }
        helpMoveTimer.restart()
    }
    Timer { id: helpMoveTimer; interval: Theme.motion.SLOW; onTriggered: root.helpMoving=false }
    property bool transitions: true
    property string viewMode: "both"
    property alias leftWidth: workspace.leftExtent
    property alias rightWidth: workspace.rightExtent
    readonly property real panelMinimum: (phase === "plant" ? 237 : 284) * Theme.type.BODY / 13
    property int checkCount: backend.checkRows.length
    property var partSources: ({})
    property url planSource: partSources.plan || ""
    property url view3dSource: partSources.view3d || ""
    property var planItem: planLoader.item
    property var chartItem: chart
    property var workspaceItem: workspace
    property var sceneItem: sceneLoader.item     // the 3D view and the central panel, for Meridio's home (AssistantHost)
    property var centralItem: central
    property string toolbarMode: "auto"
    property string toolbarPosition: "top"
    property bool cleanScreen: false
    property var cleanLayout: null
    property var arrangementInfo: ({})
    property var shapeLayouts: ({})
    // R628: with the sizes given by hand to the windows, by their kind (M.DialogSizes)
    function savedLayout() { return {layout: cleanScreen && cleanLayout ? cleanLayout : workspace.snapshot(), shapes: shapeLayouts, dialogs: M.DialogSizes.sizes} }
    // R549: the saved state comes with Project and Properties shown on their sides (shell_state.at_start); Checks as
    // the window's height wants it, as at the first start
    function restoreLayout(state) { arrange(); shapeLayouts=state.shapes; workspace.put(state.layout,false); checks.opened=arrangementInfo.checks_open
        M.DialogSizes.sizes = state.dialogs || ({}) }
    property string viewsArrangement: arrangementInfo.views || "side"
    onWidthChanged: arrangeTimer.restart()
    onHeightChanged: arrangeTimer.restart()
    onToolbarModeChanged: arrangeTimer.restart()
    Timer { id: arrangeTimer; interval: Theme.motion.NORMAL; onTriggered: root.arrange() }
    // ui/window.py _arrange: what the window should be for its size; said, with its Undo for a few seconds, when the
    // program moved something (Daniel: nothing changes by surprise). D23.
    property var shapePins: ({})
    property var arrangeUndo: null
    Timer { id: arrangeUndoTimer; interval: 15000; onTriggered: root.arrangeUndo=null }
    function arrange() {
        if(fileOpen || cleanScreen) return
        const was=arrangementInfo, before=was.shape ? workspace.snapshot() : null
        const next=shell.layoutFor(width,height,phase,{previous:was,toolbar:toolbarMode==="icons" ? "icons" : "text",needs:phaseHeader.layoutNeeds,columns:[workspace.leftExtent,workspace.rightExtent],checks:workspace.bottomExtent,pins:shapePins[was.shape || ""] || {}})
        let remembered=false
        if(next.shape!==was.shape) {
            if(was.shape) shapeLayouts[was.shape]=before
            if(shapeLayouts[next.shape]) { workspace.put(shapeLayouts[next.shape]); remembered=true; sideProject(next.panels,false) }
            else {
                sideProject(next.panels,true)
                checks.opened=next.checks_open
                workspace.selectPanel("properties")
            }
        } else {
            if(next.checks_open!==was.checks_open) checks.opened=next.checks_open
            if(next.panels!==was.panels) sideProject(next.panels,true)
        }
        arrangementInfo=next
        workspace.arrangementChanged()
        if(was.shape) {
            const said=shell.arrangedSay(was,next,remembered)
            if(said.fields.length || remembered) { arrangeUndo={before:before,was:was,fields:said.fields}; arrangeUndoTimer.restart() }
        }
    }
    // R549: the side of Project follows the room. A window too narrow for two columns has it as a tab beside Properties
    // on the right; once there is room again it goes back to the left (`back`), also within one shape: «medium» goes
    // from 800 px to well past NARROW, and Niri opens a window at half the laptop's screen (800 x 828) and widens it
    // there, where the side was set only when the shape changed and Project stayed behind Properties. A card on the
    // bottom or floating is the user's and stays.
    function sideProject(panels, back) {
        if(panels==="together" && project.zone==="left") project.zone="right"
        else if(back && panels==="apart" && project.zone==="right") project.zone="left"
        workspace.arrangementChanged()
    }
    function undoArrange() {
        if(!arrangeUndo) return
        const undo=arrangeUndo
        arrangeUndo=null; arrangeUndoTimer.stop()
        const pins=Object.assign({},shapePins)
        pins[arrangementInfo.shape]=shell.arrangePinned(pins[arrangementInfo.shape] || {},undo.was,undo.fields)
        shapePins=pins
        workspace.put(undo.before)
        arrangementInfo=Object.assign({},undo.was,{shape:arrangementInfo.shape})
        arrange()
        arrangeUndo=null
        shell.arrangeBack()
    }
    property string inspectorTitle: phase==="plant" ? L.plant : phase==="report" ? L.deliverables : ["production","consumption","economics"].includes(phase) ? L.data : L.properties
    function showPhase(value) { if(typeof motion!=="undefined" && motion) motion.phase(value, phase, fileOpen); else { fileOpen=false; phase=value } }
    function openObjects() { if (objectPicker.visible) objectPicker.close(); else objectPicker.openFrom(phaseHeader.objectTool) }
    function pickHelp() { helpPicker.visible=true }
    function helpAt(x,y) {
        let p=workspace.mapFromItem(helpPicker,x,y), node=workspace, hit=workspace.childAt(p.x,p.y)
        while(hit) { p=hit.mapFromItem(node,p.x,p.y); node=hit; hit=node.childAt(p.x,p.y) }
        helpFrom(node, workspace)
    }
    // R597: the help key, the help of what has the keyboard (a field's own, else its section's), in its bubble; nothing with a
    // help under the focus: the phase's, on the card's «?» (or the status bar's «Aiuto» when the card is closed)
    function contextHelp() { helpFrom(activeFocusItem, null) }
    function helpFrom(node, stop) {
        for (; node && node!==stop; node=node.parent) {
            const key=typeof node.helpId==="string" ? node.helpId : ""
            if(key) { M.Help.show(key, node.helpAnchor || node); return }
        }
        const mark=properties.helpAnchor
        const card=mark.visible ? mark : statusHelpButton
        M.Help.show(card===mark ? mark.helpKey : "phase."+root.phase, card)
    }
    function northUp() { if(planItem && planItem.northUp) planItem.northUp() }
    property bool toolsShown: true
    M.Menu {
        id: titleMenu; objectName: "cardTitleMenu"
        Repeater { model: workspace.panels
            M.MenuItem { required property var modelData; text: modelData.title; checkable: true
                checked: modelData.opened && modelData.phaseAllowed; enabled: modelData.phaseAllowed
                onTriggered: { modelData.opened=!modelData.opened; if(modelData.opened) workspace.selectPanel(modelData.panelId); else workspace.arrangementChanged() } }
        }
        M.MenuItem { text: L.tools; checkable: true; checked: root.toolsShown; onTriggered: root.toolsShown=!root.toolsShown }
    }
    // R375: the picker of 3D objects hangs from its tool button (PhaseHeader.objectTool); the command toggles it
    ObjectPicker { id: objectPicker; objectName: "objectPicker"; parent: phaseHeader }
    function cyclePhase(delta) {
        const ids=shell.phases.map(p => p.id)
        showPhase(ids[(ids.indexOf(phase)+delta+ids.length)%ids.length])
    }
    function runCommand(command) {
        if(command==="tool_select") planItem.tool="select"
        else if(command==="tool_building" || command==="rectangle") planItem.tool="rectangle"
        // R538: on the view that has the focus, the plan or the 3D view, never on both
        else if(command==="fit" || command==="zoom_in" || command==="zoom_out") {
            const scene=sceneLoader.item && sceneLoader.item.visible && sceneLoader.item.activeFocus ? sceneLoader.item : null
            if(command==="fit") { if(scene) scene.frameSelection(); else planItem.fit() }
            else if(scene) scene.zoomBy(command==="zoom_in" ? 1 : -1)
            else planItem.zoom*=command==="zoom_in" ? 1.2 : 1/1.2
        }
        else if(command==="view_plan") viewMode=viewMode==="plan" ? "both" : "plan"
        else if(command==="view_3d") viewMode=viewMode==="3d" ? "both" : "3d"
        else if(command==="view_both") viewMode="both"
        else if(command==="panel_help") helpOpen=!helpOpen
        else if(command==="side_left") workspace.toggleEdge("left")         // R549: Ctrl+B, the left side as in VS Code
        else if(command.startsWith("panel_")) workspace.togglePanel(command.substring(6))
        else if(command==="default_layout") workspace.restore()
        else if(command==="clean_screen") {
            if(!cleanScreen) { cleanLayout=workspace.snapshot(); workspace.panels.forEach(p=>p.opened=false); cleanScreen=true }
            else { cleanScreen=false; workspace.put(cleanLayout); arrangeTimer.restart() }
            workspace.arrangementChanged()
        }
        else if(command==="next_phase") cyclePhase(1)
        else if(command==="previous_phase") cyclePhase(-1)
        else if(command==="preferences") fileOpen=true
        else if(command==="toolbar_text") toolbarMode=toolbarMode==="icons" ? "auto" : "icons"
        else if(command==="focus_checks") { checks.opened=true; workspace.selectPanel("checks") }
          else if(command==="focus_properties") { properties.opened=true; workspace.selectPanel("properties"); properties.forceActiveFocus() }
        else if(command==="assistant") helpOpen=!helpOpen
        else if(command==="context_help") contextHelp()
        else if(command==="menu_bar") menuOpen=!menuOpen
    }
    // A little window of a page that stays open beside the work takes Esc for itself.
    property bool escTaken: false
    Shortcut { sequence: "Esc"; enabled: !root.escTaken; onActivated: { if(M.Help.close()) return; if(root.fileOpen) root.fileOpen=false; else if(root.menuOpen && !root.menuAlways) { root.menuOpen=false; root.returnFocus() } else { root.helpOpen=false; workspace.cancelDrag(); shell.escape() } } }
    Repeater {
        model: shell.keyCommands
        delegate: Item {
            required property var modelData
            Shortcut {
                sequences: modelData.keys
                enabled: !modelData.keys.some(k => k.length===1) || !root.activeFocusItem || root.activeFocusItem.cursorPosition===undefined
                onActivated: shell.trigger(modelData.id)
            }
        }
    }
    header: Column {
        Keys.onPressed: event => root.altPressed(event)
        Keys.onReleased: event => root.altReleased(event)
        spacing: 0
        Row {
            id: menus; objectName: "altMenuBar"
            // the kit (dc3d9bd, Daniel 21/11/2026: «la comparsa della barra menu Alt è molto scattosa e lenta»): its room is
            // taken and given back in one step, so the page is laid out once; the bar comes and goes by its opacity and
            // a slide (before, its height grew frame by frame and every frame laid the page out again)
            height: root.menuOpen || menusFade.running ? Theme.size.CONTROL : 0
            visible: height>0; clip: true
            opacity: root.menuOpen ? 1 : 0
            Behavior on opacity { NumberAnimation { id: menusFade; duration: Theme.reducedMotion ? 0 : Theme.motion.NORMAL; easing.type: Theme.motion.EASE } }
            transform: Translate { y: (menus.opacity-1)*Theme.space.S }
            x: Theme.layout.EDGE
            Repeater {
                id: menuEntries
                model: shell.menus
                M.Button {
                    id: menuButton
                    required property var modelData
                    required property int index
                    objectName: "mainMenu_"+index
                    readonly property bool menuOpened: menuPopup.visible
                    text: modelData.title; flat: true
                    active: activeFocus || menuPopup.visible
                    Keys.onRightPressed: root.focusMenu(index+1)
                    Keys.onLeftPressed: root.focusMenu(index-1)
                    Keys.onDownPressed: menuPopup.open()
                    Keys.onReturnPressed: menuPopup.open()
                    Keys.onEnterPressed: menuPopup.open()
                    // R475: a second click on the same title closes its menu; passing over the next title while a
                    // menu is open opens that one, as in a menu bar.
                    onClicked: menuPopup.visible ? menuPopup.close() : menuPopup.open()
                    onHoveredChanged: if (hovered && root.barMenu && root.barMenu !== menuPopup && root.barMenu.visible) menuPopup.open()
                    Shortcut { sequence: "Alt+"+menuButton.modelData.mnemonic
                        onActivated: { root.menuOpen=true; menuPopup.open() }
                        // Two menus with one letter (Varianti, Aiuto): each press goes to the next, as in a menu bar.
                        onActivatedAmbiguously: { root.menuOpen=true; menuPopup.open() } }
                    M.Menu {
                        id: menuPopup; y: menuButton.height
                        objectName: "mainMenuPopup_" + menuButton.index
                        // a press on its own title is the title's: it closes the menu by the click above
                        closePolicy: T.Popup.CloseOnEscape | T.Popup.CloseOnPressOutsideParent
                        onAboutToShow: { if (root.barMenu && root.barMenu !== menuPopup) root.barMenu.close(); root.barMenu = menuPopup }
                        onClosed: if (root.barMenu === menuPopup) root.barMenu = null
                        Repeater {
                            model: menuButton.modelData.commands
                            M.MenuItem { required property var modelData
                                text: modelData.text; shortcutText: modelData.keys.join(", "); tip: modelData.tip; enabled: modelData.enabled && shell.commandEnabled[modelData.id]!==false
                                // R646: Full screen says it is on with the check of the menus
                                // (not checkable: a click would break the binding; the window's state says it)
                                checked: modelData.id==="fullscreen" && root.visibility===Window.FullScreen
                                onTriggered: { shell.trigger(modelData.id); root.menuOpen=root.menuAlways } }
                        }
                        Instantiator {
                            model: menuButton.modelData.submenus
                            delegate: M.Menu {
                                required property var modelData
                                title: modelData.title
                                Repeater { model: modelData.commands
                                    M.MenuItem { required property var modelData
                                        text: modelData.text; shortcutText: modelData.keys.join(", "); tip: modelData.tip; enabled: modelData.enabled && shell.commandEnabled[modelData.id]!==false
                                        onTriggered: { shell.trigger(modelData.id); root.menuOpen=root.menuAlways } }
                                }
                            }
                            onObjectAdded: (index, object) => menuPopup.insertMenu(index+3,object)
                            onObjectRemoved: (index, object) => menuPopup.removeMenu(object)
                        }
                    }
                }
            }
        }
        PhaseHeader {
            id: phaseHeader; objectName: "phaseBar"
            width: root.width-2*Theme.layout.EDGE; x: Theme.layout.EDGE
            phase: root.phase; fileOpen: root.fileShown; dirty: root.projectDirty
            leavingPhase: root.leavingPhase
            trailingSource: root.partSources[root.phase+"Trailing"] || ""
            trailingCanMove: views.shown         // R553: above the views when the bar has no room; no views, it stays
            onLayoutNeedsChanged: arrangeTimer.restart()
            selectedTool: root.planItem ? root.planItem.tool : ""
            barVisible: !root.fileShown && !root.cleanScreen && root.toolbarPosition==="top" && root.toolsShown
            barMode: root.toolbarMode==="auto" ? (root.arrangementInfo.bar || (root.height < shell.metrics.lowWindow ? "beside" : "under")) : root.toolbarMode
            onPhaseChosen: phase => root.showPhase(phase)
            onFileRequested: root.fileOpen=!root.fileOpen
        }
    }
    Item {
        id: sideTools; visible: root.toolbarPosition==="left" && !root.fileShown && !root.cleanScreen && root.toolsShown
        // Native QToolBar: 33 px buttons and 2 px padding, no surrounding card.
        property real buttonExtent: Theme.icon.BAR+2*Theme.space.XS+3
        x: 0; y: 0; width: buttonExtent+2*Theme.space.XXS
        height: parent.height
        Flickable { anchors.fill: parent; anchors.margins: Theme.space.XXS; contentHeight: sideColumn.height; clip: true
            Column { id: sideColumn; spacing: Theme.space.XXS
                // Built only while the tools stand on the left (06/11/2026): hidden, they were rebuilt at every phase.
                Repeater { model: sideTools.visible ? shell.phases.find(p=>p.id===root.phase).groups : []
                    Column { required property var modelData; spacing: Theme.space.XXS
                        Repeater { model: modelData.tools
                            Loader {
                                id: sideLoader
                                required property var modelData
                                property var family: [modelData].concat(modelData.more)
                                property var face: !modelData.fixed ? (family.find(t=>phaseHeader.toolMatches(t.command)) || modelData) : modelData
                                sourceComponent: modelData.more.length ? sideSplit : sidePlain
                                Component {
                                    id: sidePlain
                                    PhaseToolButton {
                                        objectName: "sideTool_"+sideLoader.modelData.command
                                        mode: "icons"; width: sideTools.buttonExtent; height: width
                                        text: sideLoader.face.label
                                        iconName: sideLoader.face.icon; tip: sideLoader.face.tip
                                        enabled: sideLoader.face.enabled && shell.commandEnabled[sideLoader.face.command]!==false
                                        active: phaseHeader.toolMatches(sideLoader.face.command)
                                        onClicked: shell.trigger(sideLoader.face.command)
                                    }
                                }
                                Component {
                                    id: sideSplit
                                    PhaseSplitButton {
                                        objectName: "sideTool_"+sideLoader.modelData.command
                                        mode: "icons"; width: sideTools.buttonExtent; height: width; stripWidth: Theme.space.M
                                        text: sideLoader.face.label
                                        iconName: sideLoader.face.icon; tip: sideLoader.face.faceTip
                                        stripTip: sideLoader.modelData.stripTip
                                        enabled: sideLoader.family.some(t=>t.enabled)
                                        mainEnabled: sideLoader.face.enabled && shell.commandEnabled[sideLoader.face.command]!==false
                                        active: phaseHeader.toolMatches(sideLoader.face.command)
                                        stripActive: sideLoader.family.some(t=>t.command!==sideLoader.face.command && phaseHeader.toolMatches(t.command))
                                        model: sideLoader.family
                                        onClicked: shell.trigger(sideLoader.face.command)
                                        onChosen: index=>shell.trigger(sideLoader.family[index].command)
                                    }
                                }
                            }
                        }
                        Item { width: sideTools.buttonExtent; height: Theme.space.S
                            Rectangle { anchors.centerIn: parent; width: parent.width-2*Theme.space.XS; height: Theme.line.HAIR; color: Theme.colors.line_soft }
                        }
                    }
                }
            }
        }
    }
    Item {
        id: workspace
        objectName: "workspace"
        anchors.fill: parent; anchors.leftMargin: Theme.layout.EDGE+(sideTools.visible ? sideTools.width : 0); anchors.rightMargin: Theme.layout.EDGE
        // R645: no gap at the foot: the bar under the cards keeps its words and signs as far from the cards above as
        // from the window's foot (its own half height)
        anchors.topMargin: Theme.layout.GAP; anchors.bottomMargin: 0
        visible: !root.fileShown
        focus: true
        Keys.onPressed: event => root.altPressed(event)
        Keys.onReleased: event => root.altReleased(event)
        property real leftExtent: shell.metrics.leftWidth
        property real rightExtent: shell.metrics.rightWidth
        property real bottomExtent: shell.metrics.checksHeight
        property int revision: 0
        readonly property bool phaseTransition: root.leavingPhase!==""
        property var phaseSlots: ({})
        property var phaseCards: ({})
        function rememberPhase() {
            // Snapshot before changing the phase: retiring a card must not slide its neighbours under it.
            const slots={}, cards={}
            for(const zone of ["left","right","bottom","center"]) slots[zone]=slot(zone)
            if(!has("left")) delete slots.left
            for(const card of panels) if(card.visible) cards[card.panelId]=true
            phaseSlots=slots; phaseCards=cards
        }
        property bool settling: false
        // R37: an edge or the line between two cards is being dragged
        property bool resizing: false
        // The kit (31b789a, a76c485, 8d0ac5e, f8673ae; Daniel 21/11/2026: «vorrei che il contenuto si spostasse
        // dinamicamente... come Electron»): the content follows the border live. Only when a step still costs past
        // 33 ms, the median of the last five after the first eight (from the new size to its frame drawn: `stepCosts`),
        // the cards and the page hold their content for the rest of the drag (`holdContent`, DockPanel.held), as R37
        // did always. Not the time between frames: a hand moving slowly leaves long gaps with little work.
        property bool holdContent: false
        property real stepAt: 0
        property var stepCosts: []
        readonly property real stepCost: stepCosts.length ? stepCosts[stepCosts.length-1] : 0
        onResizingChanged: { holdContent=false; stepAt=0; if(resizing) stepCosts=[] }
        function stepped() { if(resizing) { stepAt=Date.now(); root.requestUpdate() } }
        Connections {
            target: workspace.resizing && workspace.stepAt>0 ? root : null
            function onFrameSwapped() {
                if(workspace.stepAt<=0) return
                workspace.stepCosts=workspace.stepCosts.concat([Date.now()-workspace.stepAt])
                workspace.stepAt=0
                const last=workspace.stepCosts.slice(-5).sort((a,b)=>a-b)
                if(!workspace.holdContent && workspace.stepCosts.length>=8 && last[2]>33) workspace.holdContent=true
            }
        }
        property var panels: [project, contents, properties, checks]
        property var selected: ({left:"project",right:"properties",bottom:"checks"})
        property string draggedPanel: ""
        property point dragStart
        property point dragOrigin
        property string candidate: ""
        property string targetZone: ""
        property bool grouping: false
        // Each zone is a line of slices: "*" the cards in tabs, any other a card with a slice of its own (ui/dock_motion.py).
        property var stacks: ({left:[],right:[],bottom:[]})
        property var weights: ({})
        property var dragTarget: null
        function stackedHere(panel) { return (stacks[panel.zone] || []).includes(panel.panelId) }
        function tabMembers(zone) { const r=revision; return members(zone).filter(p=>!(stacks[zone] || []).includes(p.panelId)) }
        // A tab joins the shared group, replacing a standalone slice if necessary.
        // The preview and the committed topology use exactly the same operation.
        function tabLine(line, anchor) {
            return line.includes("*") ? line.filter(id=>id!==anchor) : line.map(id=>id===anchor ? "*" : id)
        }
        function sliceList(zone, target=dragTarget) {
            const r=revision
            const here=panels.filter(p=>p && p.opened && p.phaseAllowed && p.zone===zone && (!target || p.panelId!==draggedPanel))
            const ids=here.map(p=>p.panelId), own=(stacks[zone] || []).filter(id=>ids.includes(id))
            let line=(stacks[zone] || []).filter(id=>id==="*" || ids.includes(id))
            const tabs=ids.filter(id=>!own.includes(id))
            if(!line.includes("*") && tabs.length) line=["*"].concat(line)
            if(line.includes("*") && !tabs.length) line=line.filter(id=>id!=="*")
            if(target && target.zone===zone && target.where==="tab") line=tabLine(line,target.anchor)
            if(target && target.zone===zone && target.where!=="tab") {
                let at=line.length
                if(target.anchor) { const key=line.includes(target.anchor) ? target.anchor : "*"; const i=line.indexOf(key); if(i>=0) at=target.where==="before" ? i : i+1 }
                line=line.slice(0,at).concat([draggedPanel]).concat(line.slice(at))
            }
            return line
        }
        function sliceRect(zone, key, target=dragTarget) {
            const line=sliceList(zone,target), whole=slot(zone,target), i=line.indexOf(key)
            if(i<0) return whole
            const across=zone==="bottom", gap=Theme.layout.GAP
            const room=(across ? whole.width : whole.height)-gap*(line.length-1)
            const sum=line.reduce((n,id)=>n+(weights[id] || 1),0)
            let at=0
            for(let k=0;k<i;k++) at+=Math.round(room*(weights[line[k]] || 1)/sum)+gap
            const size=i===line.length-1 ? room+gap*(line.length-1)-at : Math.round(room*(weights[key] || 1)/sum)
            return across ? Qt.rect(whole.x+at,whole.y,size,whole.height) : Qt.rect(whole.x,whole.y+at,whole.width,size)
        }
        function place(panel) { return sliceRect(panel.zone,stackedHere(panel) ? panel.panelId : "*") }
        function snapshot() { return {stacks:JSON.parse(JSON.stringify(stacks)),weights:Object.assign({},weights),left:leftExtent,right:rightExtent,bottom:bottomExtent,selected:Object.assign({},selected),view:root.viewMode,
            panels:panels.map(p=>({id:p.panelId,zone:p.zone,opened:p.opened,x:p.floatX,y:p.floatY,width:p.floatWidth,height:p.floatHeight}))} }
        function put(state, animate=true) { if(!state) return; settling=animate; stacks=state.stacks || {left:[],right:[],bottom:[]}; weights=state.weights || {}; leftExtent=state.left;rightExtent=state.right;bottomExtent=state.bottom;selected=state.selected;root.viewMode=state.view
            state.panels.forEach(s=>{ const p=panels.find(p=>p.panelId===s.id);if(!p) return;p.zone=s.zone;p.opened=s.opened;p.floatX=s.x;p.floatY=s.y;p.floatWidth=s.width;p.floatHeight=s.height })
            arrangementChanged(); if(animate) settleTimer.restart(); else settleTimer.stop() }
        signal arrangementChanged()
        onArrangementChanged: revision++
        function members(zone) { const r=revision; return panels.filter(p => p && p.opened && p.phaseAllowed && p.zone===zone) }
        function has(zone, target=dragTarget) { return sliceList(zone,target).length>0 }
        function activePanel(zone) { const list=tabMembers(zone); return list.some(p => p.panelId===selected[zone]) ? selected[zone] : list.length ? list[0].panelId : "" }
        // While the phase changes, a card that retires keeps its place (it fades out there) and so does the centre, so
        // that nothing slides under it; but a card that comes or stays has its place at once, and the centre is the
        // smaller of the two: from Production into Plant the centre of Production (the whole width) was kept for the
        // fade, and the map covered the Project card coming in (Daniel 21/11/2026).
        function slot(zone, target=dragTarget) {
            if(phaseTransition && phaseSlots[zone]) {
                const now=liveSlot(zone,target), was=phaseSlots[zone]
                if(zone!=="center") return has(zone,target) ? now : was
                const x0=Math.max(now.x,was.x), y0=Math.max(now.y,was.y)
                return Qt.rect(x0,y0,Math.max(0,Math.min(now.x+now.width,was.x+was.width)-x0),
                               Math.max(0,Math.min(now.y+now.height,was.y+was.height)-y0))
            }
            return liveSlot(zone,target)
        }
        function liveSlot(zone, target=dragTarget) {
            // Whole pixels: the 3D renders to a texture, and a texture at a fraction is resampled and blurred.
            const l=has("left",target) ? Math.round(Math.min(leftExtent,width*0.32)) : 0
            const r=has("right",target) ? Math.round(Math.max(root.panelMinimum,Math.min(rightExtent,width*0.34))) : 0
            const b=has("bottom",target) ? Math.round(Math.min(bottomExtent,height*0.48)) : 0
            const lg=l>0 ? Theme.layout.GAP : 0, rg=r>0 ? Theme.layout.GAP : 0, bg=b>0 ? Theme.layout.GAP : 0
            if(zone==="left") return Qt.rect(0,0,l,height-b-bg)
            if(zone==="right") return Qt.rect(width-r,0,r,height)
            if(zone==="bottom") return Qt.rect(0,height-b,width-r-rg,b)
            return Qt.rect(l+lg,0,width-l-lg-r-rg,height-b-bg)
        }
        function selectPanel(id) { const p=panels.find(p => p.panelId===id); const next=Object.assign({},selected); next[p.zone]=id; selected=next; arrangementChanged() }
        function togglePanel(id) { const p=panels.find(p => p.panelId===id); if(p) { if(p.opened && !p.selected) selectPanel(id); else p.opened=!p.opened; if(p.opened) selectPanel(id); arrangementChanged() } }
        // R549 (Daniel 08/11/2026, as VS Code): each button of the status bar is a side, the left, the bottom, the right,
        // whatever cards stand there; its picture always says the truth. Shown, it hides all the cards of its side,
        // a group of tabs as a whole (the tab in front is kept in `selected`); the side empty, it brings back the
        // cards it hid last, there, and when it never hid any the card of that side at the first start. One card
        // alone is closed by its X or from the Panels menu, by its name. Before, the bottom button took the cards of
        // the right side too, and Project moved to the right answered to the left one.
        property var collapsedEdges: ({})
        readonly property var homeCards: ({left:root.phase==="report" ? "contents" : "project",bottom:"checks",right:"properties"})
        function toggleEdge(zone) {
            const here=panels.filter(p=>p.opened && p.phaseAllowed && !p.floating && p.zone===zone)
            if(here.length) { collapsedEdges[zone]=here.map(p=>p.panelId); here.forEach(p=>p.opened=false) }
            else {
                // hidden by this button and not opened elsewhere since; when none is left, the side's own card
                let back=(collapsedEdges[zone] || []).map(id=>panels.find(p=>p.panelId===id)).filter(p=>p && !p.opened)
                if(!back.length) back=panels.filter(p=>p.panelId===homeCards[zone])
                back.forEach(p=>{ if(p.zone!==zone) { unstack(p.panelId); p.zone=zone; settling=true; settleTimer.restart() } p.opened=true })
                if(back.length===1) selectPanel(back[0].panelId)
            }
            arrangementChanged()
        }
        function unstack(id) {
            const next=Object.assign({},stacks)
            for(const zone of Object.keys(next)) next[zone]=(next[zone] || []).filter(x=>x!==id)
            stacks=next
        }
        // What a side's button says: the cards there now, or the ones it would bring back
        function edgeCards(zone) {
            const r=revision, shown=panels.filter(p=>p.opened && p.phaseAllowed && !p.floating && p.zone===zone)
            if(shown.length) return {shown:true,titles:shown.map(p=>p.title)}
            let back=(collapsedEdges[zone] || []).map(id=>panels.find(p=>p.panelId===id)).filter(p=>p && !p.opened)
            if(!back.length) back=panels.filter(p=>p.panelId===homeCards[zone])
            return {shown:false,titles:back.map(p=>p.title)}
        }
        function restore() {
            if(layoutUndo.running && previousLayout) { layoutUndo.stop(); put(previousLayout); previousLayout=null; shell.layoutRestored(true); return }
            previousLayout=snapshot(); layoutUndo.restart(); cancelDrag()
            root.cleanScreen=false; root.shapeLayouts={}; root.shapePins={}; stacks={left:[],right:[],bottom:[]}; weights={}
            settling=true; project.zone="left"; properties.zone="right"; checks.zone="bottom"
            panels.forEach(p => p.opened=true)
            leftExtent=shell.metrics.leftWidth; rightExtent=shell.metrics.rightWidth; bottomExtent=shell.metrics.checksHeight
            selected={left:"project",right:"properties",bottom:"checks"}; arrangementChanged(); settleTimer.restart()
            shell.layoutRestored(false)
        }
        property var previousLayout: null
        Timer { id: layoutUndo; interval: 15000; onTriggered: workspace.previousLayout=null }
        function floatPanel(id) { const p=panels.find(p => p.panelId===id); p.floatX=p.x; p.floatY=p.y; p.floatWidth=p.width; p.floatHeight=p.height; p.zone="floating"; arrangementChanged() }
        function beginDrag(panel, pos) {
            if(landing) completeLanding()
            settling=false; dragTarget=null; ghostReady=false; panel.frozen=Qt.rect(panel.x,panel.y,panel.width,panel.height)
            // Hit targets stay where they were when picked up; reflow must not retarget the same pointer.
            const areas={}
            for(const card of panels) areas[card.panelId]=Qt.rect(card.x,card.y,card.width,card.height)
            dragAreas=areas
            draggedPanel=panel.panelId; dragStart=pos; dragOrigin=Qt.point(panel.x,panel.y)
            ghost.opacity=0.94
            ghost.x=panel.x; ghost.y=panel.y; ghost.width=panel.width; ghost.height=panel.height; ghost.title=panel.title
            ghostPicture.sourceItem=panel.faceItem; ghostPicture.scheduleUpdate()
            candidate=""; targetZone=""
        }
        // R504, the zones (docs/studio/36-aggancio-schede.md). A band `band` wide along the workspace's left, right
        // and bottom sides: inside it the nearest side wins, whatever the half of the window (Daniel: «nell'ultimo
        // centimetro in basso deve preferire la parte bassa»); a card of that side lying under the point takes the
        // new one beside itself, by the half of the point along the side. Elsewhere, a card under the point takes it
        // in its own column or row, before or after itself by the half of the point; a tab behind it never by
        // default (R317, R527: Daniel, «mi propone di sovrapporre le schede tra di loro anche se non premo la
        // scorciatoia»): only with Alt held, and then the middle third is the tab, the first and last thirds before
        // and after it. Over the centre: nothing, it floats.
        readonly property real band: Theme.space.XXXL
        readonly property real inertia: Theme.space.M
        property var dragAreas: ({})
        function hitRect(panel) { return draggedPanel && dragAreas[panel.panelId] ? dragAreas[panel.panelId] : Qt.rect(panel.x,panel.y,panel.width,panel.height) }
        function panelAt(pos, zone) {
            return panels.find(p => {
                if(p.panelId===draggedPanel || !p.visible || p.floating || (zone && p.zone!==zone)) return false
                const r=hitRect(p)
                return zone==="bottom" ? pos.x>=r.x && pos.x<=r.x+r.width
                    : zone ? pos.y>=r.y && pos.y<=r.y+r.height
                    : pos.x>=r.x && pos.x<=r.x+r.width && pos.y>=r.y && pos.y<=r.y+r.height
            })
        }
        function targetAt(pos) {
            const sides=[[pos.x,"left"],[width-pos.x,"right"],[height-pos.y,"bottom"]].sort((a,b)=>a[0]-b[0])
            if(sides[0][0]<band) {
                const zone=sides[0][1], there=panelAt(pos,zone)
                if(!there) return {zone:zone,anchor:"",where:"after"}
                const r=hitRect(there), share=zone==="bottom" ? (pos.x-r.x)/Math.max(1,r.width) : (pos.y-r.y)/Math.max(1,r.height)
                return {zone:zone,anchor:there.panelId,where:share<0.5 ? "before" : "after"}
            }
            const hit=panelAt(pos,"")
            if(hit) {
                const r=hitRect(hit), share=hit.zone==="bottom" ? (pos.x-r.x)/Math.max(1,r.width) : (pos.y-r.y)/Math.max(1,r.height)
                if(!root.altHeld) return {zone:hit.zone,anchor:hit.panelId,where:share<0.5 ? "before" : "after",card:true}
                return {zone:hit.zone,anchor:hit.panelId,where:share<1/3 ? "before" : share>2/3 ? "after" : "tab",card:true}
            }
            return {zone:"floating",anchor:"",where:"after"}
        }
        function sameTarget(a, b) { return !!a && !!b && a.zone===b.zone && a.anchor===b.anchor && a.where===b.where }
        // Inertia (R317 of the Widgets): the zone the pointer is in holds until the pointer is `inertia` inside the
        // next one, so the answer does not hop at a boundary.
        function settledTarget(pos) {
            const wanted=targetAt(pos), here=pendingTarget
            if(!here || sameTarget(wanted,here) || pos.x<0 || pos.y<0 || pos.x>width || pos.y>height) return wanted
            for(const d of [[inertia,0],[-inertia,0],[0,inertia],[0,-inertia],
                            [inertia,inertia],[inertia,-inertia],[-inertia,inertia],[-inertia,-inertia]]) {
                const probe=Qt.point(Math.max(0,Math.min(width,pos.x+d[0])),Math.max(0,Math.min(height,pos.y+d[1])))
                if(sameTarget(targetAt(probe),here)) return here
            }
            return wanted
        }
        property point dragAt
        function moveDrag(pos) {
            // The carried card is at the pointer at once; the zones answer after the dwell, nothing else is laid out.
            ghost.x=Math.max(0,Math.min(width-Theme.size.PANEL_MIN,dragOrigin.x+pos.x-dragStart.x))
            ghost.y=Math.max(0,Math.min(height-Theme.size.CONTROL,dragOrigin.y+pos.y-dragStart.y))
            dragAt=pos
            aim(settledTarget(pos))
        }
        // Alt down or up with the mouse still: the target where the pointer is, at once (no inertia: the key is
        // a choice, not a boundary crossed by the hand).
        function retarget() { if(draggedPanel) aim(targetAt(dragAt)) }
        function aim(target) {
            const name=target.zone+"|"+target.anchor+"|"+target.where
            if(candidate!==name) {
                candidate=name; pendingTarget=target
                // The outline answers at once; the dwell brings the drop zone and the room made by the others.
                if(target.zone==="floating") hint.hide(); else hint.show(previewRect(target))
                if(Theme.reducedMotion) acceptTarget(); else dwell.restart()
            }
        }
        property var pendingTarget: null
        // Both signals promise the exact projected layout, including the space freed at the origin.
        function previewRect(target) {
            if(target.where==="tab") return sliceRect(target.zone,"*",target)
            return sliceRect(target.zone,draggedPanel,target)
        }
        function titleMenuAt(x,y) { titleMenu.popup(workspace,x,y) }
        function finishDrag() {
            if(!draggedPanel || landing) return
            // Commit the target belonging to the single displayed promise, never a fresh pointer hit.
            const p=panels.find(p => p.panelId===draggedPanel), target=hint.shown ? pendingTarget : dragTarget || pendingTarget
            settling=true; landing=true; p.floatX=ghost.x; p.floatY=ghost.y; p.floatWidth=ghost.width; p.floatHeight=ghost.height
            const next=Object.assign({},stacks)
            for(const zone of Object.keys(next)) next[zone]=(next[zone] || []).filter(id=>id!==p.panelId)
            if(target && target.zone!=="floating") {
                const zone=target.zone
                if(target.where==="tab") {
                    next[zone]=tabLine(next[zone] || [],target.anchor)
                    const chosen=Object.assign({},selected); chosen[zone]=p.panelId; selected=chosen
                }
                else {
                    let line=sliceList(zone).filter(id=>id!==p.panelId)
                    let at=line.length
                    if(target.anchor) { const key=line.includes(target.anchor) ? target.anchor : "*"; const i=line.indexOf(key); if(i>=0) at=target.where==="before" ? i : i+1 }
                    next[zone]=line.slice(0,at).concat([p.panelId]).concat(line.slice(at))
                }
                p.zone=zone
            } else p.zone="floating"
            stacks=next
            // Commit the topology under the carried picture; show the real card only at arrival.
            dragTarget=null; pendingTarget=null; dwell.stop(); hint.hide()
            arrangementChanged()
            landingRect=p.floating ? Qt.rect(p.floatX,p.floatY,p.floatWidth,p.floatHeight) : place(p)
            if(Theme.reducedMotion) completeLanding(); else landingFlight.start()
            settleTimer.restart()
        }
        property bool landing: false
        property rect landingRect
        function completeLanding() {
            if(!landing) return
            landingFlight.stop()
            const p=panels.find(p=>p.panelId===draggedPanel)
            p.frozen=landingRect
            landing=false
            cancelDrag()
        }
        SequentialAnimation {
            id: landingFlight
            ParallelAnimation {
                NumberAnimation { target: ghost; property: "x"; to: workspace.landingRect.x; duration: Theme.motion.CAREFUL; easing.type: Theme.motion.EASE }
                NumberAnimation { target: ghost; property: "y"; to: workspace.landingRect.y; duration: Theme.motion.CAREFUL; easing.type: Theme.motion.EASE }
                NumberAnimation { target: ghost; property: "width"; to: workspace.landingRect.width; duration: Theme.motion.CAREFUL; easing.type: Theme.motion.EASE }
                NumberAnimation { target: ghost; property: "height"; to: workspace.landingRect.height; duration: Theme.motion.CAREFUL; easing.type: Theme.motion.EASE }
                NumberAnimation { target: ghost; property: "opacity"; to: 1; duration: Theme.motion.CAREFUL; easing.type: Theme.motion.EASE }
            }
            ScriptAction { script: workspace.completeLanding() }
        }
        Connections { target: Theme; function onReducedMotionChanged() { if(Theme.reducedMotion) workspace.completeLanding() } }
        function cancelDrag() { if(landing) { completeLanding(); return }; draggedPanel=""; candidate=""; targetZone=""; grouping=false; dragTarget=null; pendingTarget=null; ghostReady=false; dwell.stop(); hint.hide() }
        property bool ghostReady: false
        function acceptTarget() {
            if(!pendingTarget || landing) return
            if(!dragTarget || dragTarget.zone==="floating") dropZone.jumpTo(hint.shown ? Qt.rect(hint.x,hint.y,hint.width,hint.height) : Qt.rect(ghost.x,ghost.y,ghost.width,ghost.height))
            hint.hide()
            settling=true; dragTarget=pendingTarget; targetZone=pendingTarget.zone; grouping=pendingTarget.where==="tab"
        }
        Timer { id: dwell; interval: Theme.motion.DWELL; onTriggered: workspace.acceptTarget() }
        Timer { id: settleTimer; interval: Theme.motion.CAREFUL; onTriggered: workspace.settling=false }
        DockPanel { id: project; objectName: "leftPanel"; panelId: "project"; zone: "left"; title: L.project; workspace: root.workspaceItem
            phaseAllowed: root.phase==="model" || root.phase==="plant"
            phaseLeaving: root.leavingPhase!=="" && !!workspace.phaseCards.project && !phaseAllowed
            Loader { objectName: "projectPartLoader"; anchors.fill: parent; source: root.partSources.project || "ProjectPanel.qml" } }
        // The report's contents, a card as the others (Daniel 21/11/2026: «come mai in Relazione l'Indice non è una
        // scheda come tutte le altre?»): title, cross, its edge dragged; open or closed as it was left (R696)
        DockPanel { id: contents; objectName: "contentsPanel"; panelId: "contents"; zone: "left"; workspace: root.workspaceItem
            readonly property var report: typeof reportBackend !== "undefined" ? reportBackend : null
            title: report ? report.labels.contents : ""
            phaseAllowed: root.phase==="report" && !!root.partSources.reportContents
            phaseLeaving: root.leavingPhase!=="" && !!workspace.phaseCards.contents && !phaseAllowed
            opened: report ? report.outlineOpen : true
            onOpenedChanged: if (report && report.outlineOpen !== opened) report.setOutlineOpen(opened)
            Loader { objectName: "contentsPartLoader"; anchors.fill: parent; active: contents.phaseAllowed
                source: root.partSources.reportContents || "" } }
        DockPanel { id: properties; objectName: "rightPanel"; panelId: "properties"; zone: "right"; title: root.inspectorTitle; workspace: root.workspaceItem
            // R597, R564: the card's own «?», at the right end of its head as the sections' (Card.qml)
            helpName: "propertiesHelp"; helpShown: root.phase !== "model" || typeof inspectors === "undefined"
            helpKey: typeof helpBook !== "undefined" && helpBook ? helpBook.cardKey : ""
            // R625: made again whole if Qt threw the warmed one away half made (M.WholeLoader)
            Repeater { model: inspectorPhases
                M.PhaseLoader { objectName: "propertiesPartLoader"; required property string phaseId
                    anchors.fill: parent
                    M.PhaseFade { current: root.phase===phaseId; leaving: root.leavingPhase===phaseId; animateEntry: root.leavingPhase!=="" }
                    shown: root.phase===phaseId
                    source: root.partSources[phaseId+"_properties"] || root.partSources[phaseId+"Inspector"] || (phaseId==="plant" ? root.partSources.plant : "") || root.partSources.properties || "PropertiesPanel.qml"
                }
            } }
        DockPanel { id: checks; objectName: "checksPanel"; panelId: "checks"; zone: "bottom"; title: checksLoader.item && checksLoader.item.panelTitle!==undefined ? checksLoader.item.panelTitle : L.checks; workspace: root.workspaceItem
            Loader { id: checksLoader; objectName: "checksPartLoader"; anchors.fill: parent; source: root.partSources.checks || "ChecksPanel.qml"
                onLoaded: if(!root.partSources.checks) item.phase=Qt.binding(()=>root.phase) } }
        Rectangle {
            id: central; objectName: "centralPanel"
            DockMotion on x { settling: workspace.settling }
            DockMotion on y { settling: workspace.settling }
            DockMotion on width { settling: workspace.settling }
            DockMotion on height { settling: workspace.settling }
            x: workspace.slot("center").x; y: 0; width: workspace.slot("center").width; height: workspace.slot("center").height
            radius: Theme.radius.CARD; color: Theme.colors.panel; border.color: Theme.colors.line; clip: true
            Loader {
                id: viewsTop
                objectName: "viewsTrailing"
                readonly property url part: root.partSources[root.phase+"Trailing"] || ""
                // R449: a url is never === "" (the band of 56 px stood empty above the views once the bar had no room)
                // not while the bar's own is still loading (asynchronous): it is not shown then, and the summary
                // stood for a moment above the plan as in a narrow window (Daniel 21/11/2026)
                active: part.toString() !== "" && views.shown && !phaseHeader.trailingShown && !phaseHeader.trailingLoading
                        && !root.cleanScreen
                source: active ? part : ""
                x: Theme.layout.PAD; y: Theme.layout.PAD; width: parent.width - 2 * x
                // R553: the part's own height when it asks more (the shadows of Production one above the other)
                height: active ? Math.max(3 * Math.ceil(Theme.measureText("Hg", "secondary").height) + 2 * Theme.space.XS,
                                          item ? item.implicitHeight : 0) : 0
            }
            // A visual helper inside SplitView becomes a pane, even at zero width, with its own handle.
            M.PhaseFade {
                target: views
                current: views.shown
                leaving: ["model","plant"].includes(root.leavingPhase)
                retained: true
            }
            T.SplitView {
                id: views; anchors.fill: parent; anchors.margins: Theme.layout.PAD
                anchors.topMargin: Theme.layout.PAD + (viewsTop.active ? viewsTop.height + Theme.space.S : 0)
                orientation: root.viewsArrangement==="stacked" ? Qt.Vertical : Qt.Horizontal
                // r24-fasi (studio 41, S5): the plan and the 3D stay up in the phases that do not show them, under
                // the page of the phase, not drawn (opacity 0: the scene graph skips them, the 3D does not render) and
                // out of reach (enabled): made visible again they were laid out, sized and rendered anew, 55 ms of
                // Modellazione (the 3D's targets at 3200 x 1920 with MSAA)
                readonly property bool shown: root.phase==="model" || root.phase==="plant"
                handle: Rectangle { implicitWidth: Theme.space.S; implicitHeight: Theme.space.S; color: Theme.colors.panel }
                Item {
                    visible: root.viewMode!=="3d"; T.SplitView.fillWidth: true; T.SplitView.fillHeight: true; T.SplitView.minimumWidth: Theme.size.PANEL_MIN; T.SplitView.minimumHeight: Theme.size.PANEL_MIN
                    clip: true
                    // R504: while a card is carried the views keep their size (the room made by the cards clips
                    // them at natural size): the 3D's buffers are not rebuilt at every target, and they take their place once, at the drop.
                    DockView { id: planLoader; frozen: workspace.draggedPanel!==""; anchors.fill: !frozen ? parent : null
                        source: root.planSource.toString() ? root.planSource : "../../../Plan.qml" }
                    Row {
                        visible: !root.planSource.toString()
                        x: Theme.space.M; y: Theme.space.M; spacing: Theme.space.XXS
                        M.ToolButton { iconName: "plan"; mode: "icons"; tip: L.plan; onClicked: root.viewMode="plan" }
                        M.ToolButton { iconName: "3d"; mode: "icons"; tip: L.view3d; onClicked: root.viewMode="3d" }
                        M.ToolButton { iconName: "both"; mode: "icons"; tip: L.both; onClicked: root.viewMode="both" }
                        M.ToolButton { iconName: "fit"; mode: "icons"; tip: L.fit; onClicked: root.planItem.fit() }
                    }
                }
                Rectangle {
                    objectName: "view3dHost"; visible: root.viewMode!=="plan" && (root.viewsArrangement!=="one" || root.viewMode==="3d")
                    T.SplitView.preferredWidth: Math.round(views.width*0.45); T.SplitView.minimumWidth: Theme.size.PANEL_MIN
                    T.SplitView.preferredHeight: Math.round(views.height/2); T.SplitView.minimumHeight: Theme.size.PANEL_MIN
                    color: Theme.colors.d3.sky_bottom; radius: Theme.radius.VIEW; clip: true
                    // r24-fasi: hidden (the plan alone), the 3D keeps its size, so its buffers are not made again
                    DockView { id: sceneLoader; frozen: workspace.draggedPanel!==""; anchors.fill: !frozen && parent.visible ? parent : null; source: root.view3dSource }
                    // R598: the views of a phase that does not show them are only transparent: the 3D is told
                    Binding { target: sceneLoader.item; property: "onShow"; value: views.shown; when: !!sceneLoader.item && sceneLoader.item.onShow !== undefined }
                    Column { anchors.centerIn: parent; spacing: Theme.space.M; visible: !root.view3dSource.toString()
                        M.Icon { anchors.horizontalCenter: parent.horizontalCenter; iconName: "3d"; width: Theme.icon.TILE; height: width }
                        M.CopyLabel { text: L.view3d; textStyle: "title"; anchors.horizontalCenter: parent.horizontalCenter }
                        M.CopyLabel { text: L.placeholder; textStyle: "description" }
                    }
                    M.ToolButton { visible: !root.view3dSource.toString(); x: Theme.space.M; y: Theme.space.M; iconName: "both"; mode: "icons"; tip: L.both; onClicked: root.viewMode="both" }
                }
            }
            // R437: the state of the numbers, the same on every page that shows them. The old ones stay, marked.
            Rectangle {
                id: yearBanner; objectName: "yearBanner"; z: 2
                readonly property var year: shell.yearState
                M.PhaseFade {
                    current: ["production","consumption","economics","report"].includes(root.phase) && yearBanner.year.state==="stale"
                    leaving: ["production","consumption","economics","report"].includes(root.leavingPhase) && yearBanner.year.state==="stale"
                }
                x: Theme.layout.PAD; y: Theme.layout.PAD; width: parent.width-2*Theme.layout.PAD
                height: visible ? Theme.size.CONTROL+2*Theme.space.XS : 0
                radius: Theme.radius.INNER; color: Theme.colors.select_bg
                M.CopyLabel { objectName: "yearBannerText"; x: Theme.space.M; width: parent.width-x-yearCompute.width-2*Theme.space.M; anchors.verticalCenter: parent.verticalCenter
                    text: backend.computing===true ? shell.yearComputing : yearBanner.year.text; elide: Text.ElideRight
                    M.ToolTip { text: yearBanner.year.text; visible: bannerHover.hovered }
                    HoverHandler { id: bannerHover } }
                M.Button { id: yearCompute; objectName: "yearBannerCompute"; text: L.calculate; flat: true; enabled: backend.computing!==true
                    anchors.right: parent.right; anchors.rightMargin: Theme.space.XS; anchors.verticalCenter: parent.verticalCenter
                    onClicked: shell.trigger("compute") }
            }
            // R625 (the Balance page left empty): a page warmed while hidden and thrown away half made by Qt is made
            // again, whole, when its phase is shown (M.WholeLoader)
            Repeater { model: ["production","consumption","economics","report"]
                M.PhaseLoader { required property string modelData
                    objectName: "phasePageLoader-" + modelData
                    // R37: the page in view follows a dragged edge live, unless the steps cost too much
                    // (workspace.holdContent): then it keeps its size (the centre clips it) until the release; a page
                    // not in view does not follow the drag, and at rest every page fills the centre (a page warmed
                    // before it is shown laid out at no size could not make its charts' delegates)
                    anchors.fill: !(workspace.resizing && (workspace.holdContent || !shown)) ? parent : undefined; anchors.margins: Theme.layout.PAD
                    anchors.topMargin: Theme.layout.PAD+(yearBanner.visible ? yearBanner.height+Theme.space.S : 0)
                    property bool visited: false
                    M.PhaseFade { current: root.phase===modelData; leaving: root.leavingPhase===modelData }
                    shown: root.phase===modelData
                    onShownChanged: if(shown) visited=true
                    wanted: visited || shown || (root.pagesWarm && modelData!=="report")
                    source: root.partSources[modelData] || ""
                }
            }
            Prototype.YearChart { id: chart; anchors.fill: !(workspace.resizing && workspace.holdContent) ? parent : undefined; anchors.margins: Theme.layout.PAD
                M.PhaseFade { current: root.phase==="production" && !root.partSources.production; leaving: root.leavingPhase==="production" && !root.partSources.production } }
            M.CopyLabel { anchors.centerIn: parent; text: L.placeholder; textStyle: "description"
                visible: !["model","plant","production"].includes(root.phase) && !root.partSources[root.phase] }
        }
        Repeater {
            model: ["left","right","bottom"]
            MouseArea {
                required property string modelData
                objectName: modelData+"ResizeHandle"
                visible: workspace.has(modelData)
                property bool vertical: modelData==="bottom"
                x: vertical ? 0 : modelData==="left" ? workspace.slot("left").width : workspace.slot("right").x-Theme.layout.GAP
                y: vertical ? workspace.slot("bottom").y-Theme.layout.GAP : 0
                width: vertical ? workspace.slot("bottom").width : Theme.layout.GAP
                // A side handle ends with its own slot, above any card below it.
                height: vertical ? Theme.layout.GAP : workspace.slot(modelData).height
                cursorShape: vertical ? Qt.SplitVCursor : Qt.SplitHCursor
                hoverEnabled: true
                property point start
                property real extent
                onReleased: workspace.resizing=false
                onCanceled: workspace.resizing=false
                onPressed: mouse => { workspace.settling=false; workspace.resizing=true; start=mapToItem(workspace,mouse.x,mouse.y)
                    extent=modelData==="left" ? workspace.leftExtent : modelData==="right" ? workspace.rightExtent : workspace.bottomExtent }
                onPositionChanged: mouse => {
                    if(!pressed) return
                    workspace.stepped()
                    const p=mapToItem(workspace,mouse.x,mouse.y)
                    if(modelData==="left") workspace.leftExtent=Math.max(Theme.size.PANEL_MIN,extent+p.x-start.x)
                    else if(modelData==="right") workspace.rightExtent=Math.max(root.panelMinimum,extent-p.x+start.x)
                    else workspace.bottomExtent=Math.max(Theme.size.PANEL_MIN,extent-p.y+start.y)
                }
                Rectangle { anchors.centerIn: parent; width: parent.vertical ? parent.width : Theme.line.HAIR
                    height: parent.vertical ? Theme.line.HAIR : parent.height; color: Theme.colors.accent; visible: parent.pressed }
            }
        }
        M.DropOutline { id: hint; z: 49 }
        // R527: over a card, without Alt, a word on the key that makes it a tab, low in the card, out of the way of
        // the outline's halves' meeting line; gone with Alt held (the whole card outlined says it).
        Rectangle {
            id: tabHint; objectName: "tabHint"; z: 51
            readonly property var target: workspace.pendingTarget
            readonly property var card: target && target.card ? workspace.panels.find(p=>p.panelId===target.anchor) : null
            readonly property bool shown: workspace.draggedPanel!=="" && !!card && !root.altHeld
            property rect place
            onCardChanged: if(card) place=Qt.rect(card.x,card.y,card.width,card.height)
            x: Math.round(place.x+(place.width-width)/2); y: Math.round(place.y+place.height-height-M.ControlMetrics.inset-Theme.layout.PAD)
            width: hintText.implicitWidth+2*Theme.space.S; height: hintText.implicitHeight+2*Theme.space.XXS
            radius: Theme.radius.CONTROL; color: Theme.colors.panel
            border.color: Theme.colors.line; border.width: Theme.line.HAIR
            visible: opacity>0
            opacity: shown ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.FAST } }
            M.CopyLabel { id: hintText; anchors.centerIn: parent; text: L.altTabs; textStyle: "secondary"; color: Theme.colors.text2 }
        }
        Item {
            // ui/dock_motion.py Reflow.paintEvent: where the card will fall, dashed, with its name.
            id: dropZone; objectName: "dropZone"; z: 50
            readonly property var target: workspace.dragTarget
            readonly property bool shown: workspace.draggedPanel!=="" && target!==null && target.zone!=="floating" && !hint.shown && !workspace.landing
            // The promise stands at its exact final rectangle; only the surrounding cards animate.
            property rect lastArea
            property bool animated: true
            function jumpTo(r) { animated=false; lastArea=r; animated=true }
            readonly property rect area: {
                if(!shown) return lastArea
                return workspace.previewRect(target)
            }
            onAreaChanged: if(shown) lastArea=area
            visible: shown && opacity>0
            opacity: shown ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.FAST } }
            x: area.x; y: area.y; width: area.width; height: area.height
            Shape {
                anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    // The neutral ground and border shared with the immediate outline: one place says «here».
                    id: dropPath
                    strokeColor: Theme.colors.card_line; strokeWidth: Theme.line.HAIR; strokeStyle: ShapePath.DashLine
                    fillColor: Theme.colors.hover
                    PathRectangle {
                        x: dropPath.strokeWidth/2; y: x
                        width: Math.max(0,dropZone.width-dropPath.strokeWidth)
                        height: Math.max(0,dropZone.height-dropPath.strokeWidth)
                        radius: Math.max(0,Theme.radius.CARD-dropPath.strokeWidth/2)
                    }
                }
            }
            M.CopyLabel { anchors.centerIn: parent; text: ghost.title; color: Theme.colors.text2 }
        }
        Repeater {
            // Between two slices of a zone, the line that shares them out.
            model: { const r=workspace.revision, list=[]; for(const zone of ["left","right","bottom"]) { const line=workspace.sliceList(zone); for(let i=0;i+1<line.length;i++) list.push({zone:zone,first:line[i],second:line[i+1]}) } return list }
            MouseArea {
                required property var modelData
                objectName: "sliceHandle"
                readonly property bool across: modelData.zone==="bottom"
                readonly property rect one: workspace.sliceRect(modelData.zone,modelData.first)
                x: across ? one.x+one.width : one.x; y: across ? one.y : one.y+one.height
                width: across ? Theme.layout.GAP : one.width; height: across ? one.height : Theme.layout.GAP
                cursorShape: across ? Qt.SplitHCursor : Qt.SplitVCursor; hoverEnabled: true; z: 40
                property real start
                property real a
                property real b
                onReleased: workspace.resizing=false
                onCanceled: workspace.resizing=false
                onPressed: mouse => { workspace.settling=false; workspace.resizing=true; const p=mapToItem(workspace,mouse.x,mouse.y); start=across ? p.x : p.y; a=workspace.weights[modelData.first] || 1; b=workspace.weights[modelData.second] || 1 }
                onPositionChanged: mouse => {
                    if(!pressed) return
                    workspace.stepped()
                    const p=mapToItem(workspace,mouse.x,mouse.y), whole=workspace.slot(modelData.zone), line=workspace.sliceList(modelData.zone)
                    const room=across ? whole.width : whole.height, sum=line.reduce((n,id)=>n+(workspace.weights[id] || 1),0)
                    const moved=((across ? p.x : p.y)-start)*sum/Math.max(1,room), least=Theme.size.PANEL_MIN*sum/Math.max(1,room)
                    const first=Math.max(least,Math.min(a+b-least,a+moved))
                    const next=Object.assign({},workspace.weights); next[modelData.first]=first; next[modelData.second]=a+b-first; workspace.weights=next
                }
            }
        }
        M.Card { id: ghost; objectName: "cardLift"; property string sourceId: workspace.draggedPanel; titleShown: false
            // The frame changes size; its content picture stays at natural size and is clipped.
            visible: sourceId!==""; opacity: 0.94; clip: true; z: 51; color: Theme.colors.panel; border.color: Theme.colors.line
            ShaderEffectSource { id: ghostPicture; parent: ghost; live: false; recursive: false
                width: sourceItem ? sourceItem.width : 0
                height: sourceItem ? sourceItem.height : 0
                onScheduledUpdateCompleted: workspace.ghostReady=true }
        }
    }
    Item {
        id: filePage
        objectName: "filePage"; visible: root.fileShown
        Keys.onPressed: event => root.altPressed(event)
        Keys.onReleased: event => root.altReleased(event)
        anchors.fill: parent; anchors.leftMargin: Theme.layout.EDGE; anchors.rightMargin: Theme.layout.EDGE
        anchors.topMargin: Theme.layout.GAP; anchors.bottomMargin: 0       // R645, as the cards
        Loader { objectName: "filePartLoader"; anchors.fill: parent; source: root.partSources.file || "FallbackFile.qml" }
    }
    // R536 (Daniel: «le schede che si spostano devono superare le scritte al fondo»): the bar at the foot under the
    // window's content, so a card carried, floating or docked low is drawn over its words, never under them (the
    // window has no background item: below the content there is only its colour).
    footer: RowLayout {
        z: -1
        Keys.onPressed: event => root.altPressed(event)
        Keys.onReleased: event => root.altReleased(event)
        // R645 (Daniel 15/11/2026: «il testo e i simboli fuori scheda vorrei che avessero margine sopra quanto ne hanno
        // sotto»): a control's height and Theme.space.XS above and under it, and no gap over it (the cards end at its
        // top): its signs 10 from the cards and 10 from the window's foot (until R645 19 and 10)
        height: Theme.size.CONTROL+2*Theme.space.XS; spacing: Theme.space.XXS
        // R486: as far from the window's side as the panels above and the bar's right end (Theme.layout.EDGE)
        // R537 (study 38): a save told as Office and Blender do, in this bar: the tick of the checks when done, their
        // stop sign for an error (in red, until its cross); the sentence of a save fades at its end (noticeFading).
        readonly property string noticeKind: backend.error ? "" : shell.noticeKind
        M.Icon { id: statusNoticeIcon; objectName: "statusNoticeIcon"; Layout.leftMargin: Theme.layout.EDGE; Layout.alignment: Qt.AlignVCenter
            visible: parent.noticeKind==="done" || parent.noticeKind.startsWith("error")
            name: parent.noticeKind.startsWith("error") ? "symbol:fail" : "symbol:ok"; dimDisabled: false
            width: Theme.icon.CONTROL-2; height: width; opacity: statusHint.opacity }
        M.CopyLabel { id: statusHint; objectName: "statusHint"; Layout.leftMargin: statusNoticeIcon.visible ? Theme.space.XS : Theme.layout.EDGE; Layout.alignment: Qt.AlignVCenter; text: backend.error || shell.notice || (["model","plant"].includes(root.phase) && !root.fileOpen ? (root.planItem && root.planItem.statusText!==undefined ? root.planItem.statusText : root.planItem && root.planItem.tool==="rectangle" ? L.drawHint : L.selectHint) : root.fileOpen ? "" : (backend.yearNote || ""))
            textStyle: "secondary"; Layout.fillWidth: true; elide: Text.ElideRight
            color: parent.noticeKind.startsWith("error") ? Theme.colors.danger : Theme.colors[spec.tone]
            opacity: parent.noticeKind==="done" && shell.noticeFading ? 0 : 1
            Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.SLOW; easing.type: Theme.motion.EASE } }
            // a sentence cut by a narrow window, whole under the pointer
            HoverHandler { id: statusHintHover }
            M.ToolTip { visible: statusHintHover.hovered && statusHint.truncated; text: statusHint.text } }
        M.ProgressBar { objectName: "statusSaving"; visible: parent.noticeKind==="busy"; indeterminate: true
            Layout.preferredWidth: 80; Layout.alignment: Qt.AlignVCenter }
        M.Button { objectName: "statusSaveAs"; flat: true; text: L.saveAs; visible: parent.noticeKind==="error"; padding: Theme.space.S
            onClicked: { shell.dismissNotice(); shell.trigger("save_as") } }
        M.Button { objectName: "statusNoticeClose"; flat: true; iconName: "x"; tip: L.close; visible: parent.noticeKind.startsWith("error")
            padding: Theme.space.S; onClicked: shell.dismissNotice() }
        M.Button { objectName: "arrangeUndo"; flat: true; text: L.undo; visible: root.arrangeUndo!==null; padding: Theme.space.S; onClicked: root.undoArrange() }
        // R598 (study 48): the one bar of the heavy jobs, the year among them (backend/work.py adopts its progress)
        WorkBar { id: statusProgress; Layout.alignment: Qt.AlignVCenter }
        // R623 (Daniel 15/11/2026: «togli da qua sotto in basso a destra i vari segnetti di to fix, to check, to know»):
        // no counts of the checks in this bar; they are in the Checks panel (Ctrl+J, Ctrl+Shift+M, the panels' menu)
        // ui/window.py: measure_label: what the selection measures. Where the pointer is went to the plan, by the
        // scale (R484): here its width changed at every step of the pointer and moved the counts and the progress.
        M.CopyLabel { objectName: "statusMeasure"; visible: text !== ""; textStyle: "secondary"
            text: ["model","plant"].includes(root.phase) && !root.fileOpen && root.planItem && root.planItem.measureText!==undefined ? root.planItem.measureText : "" }
        StatusButton { objectName: "statusPanelLeft"; Layout.preferredWidth: Theme.size.CONTROL; iconName: "panel-left"; tip: shell.sideTip("left",workspace.edgeCards("left")); seen: workspace.has("left"); onClicked: workspace.toggleEdge("left")
            TapHandler { acceptedButtons: Qt.RightButton; onTapped: panelMenu.open() } }
        StatusButton { objectName: "statusPanelBottom"; Layout.preferredWidth: Theme.size.CONTROL; iconName: "panel-bottom"; tip: shell.sideTip("bottom",workspace.edgeCards("bottom")); seen: workspace.has("bottom"); onClicked: workspace.toggleEdge("bottom")
            TapHandler { acceptedButtons: Qt.RightButton; onTapped: panelMenu.open() } }
        StatusButton { objectName: "statusPanelRight"; Layout.preferredWidth: Theme.size.CONTROL; iconName: "panel-right"; tip: shell.sideTip("right",workspace.edgeCards("right")); seen: workspace.has("right"); onClicked: workspace.toggleEdge("right")
            TapHandler { acceptedButtons: Qt.RightButton; onTapped: panelMenu.open() } }
        StatusButton { id: statusHelpButton; objectName: "statusHelp"; Layout.preferredWidth: Theme.size.CONTROL; iconName: "circle-question-mark"; tip: L.help; onClicked: root.helpOpen=!root.helpOpen
            TapHandler { acceptedButtons: Qt.RightButton; onTapped: panelMenu.open() }
            M.Menu { id: panelMenu; y: -implicitHeight
                M.MenuItem { text: L.project; onTriggered: workspace.togglePanel("project") }
                M.MenuItem { text: L.properties; onTriggered: workspace.togglePanel("properties") }
                M.MenuItem { text: L.checks; onTriggered: workspace.togglePanel("checks") }
                M.MenuItem { text: L.restore; onTriggered: workspace.restore() }
            }
        }
        M.Button { objectName: "statusMeridio"; text: L.meridio; flat: true; padding: Theme.space.M; onClicked: root.helpOpen=!root.helpOpen
            // As wide as the button of the Widgets (78 px): the Row's own implicit width lags behind its label.
            implicitWidth: Theme.icon.CONTROL+Theme.space.XS+meridioWord.implicitWidth+2*Theme.space.M
            contentItem: Row { spacing: Theme.space.XS
                Image { objectName: "statusMeridioIcon"; width: Theme.icon.CONTROL; height: width; anchors.verticalCenter: parent.verticalCenter
                    sourceSize: Qt.size(width, height); fillMode: Image.PreserveAspectFit
                    // R619: Meridio still, his solid faces (gui/backend/assistant.FigureImages)
                    source: root.partSources.assistant ? "image://assistant/sticker" : mascotSource }
                M.CopyLabel { id: meridioWord; text: L.meridio; textStyle: "secondary"; color: Theme.colors.text; anchors.verticalCenter: parent.verticalCenter }
            }
        }
        Item { Layout.preferredWidth: Theme.space.L }
    }
    // R628 (Daniel 15/11/2026: «non mi piace il fatto che non sia utilizzabile meridio» with a window open; his choice:
    // the windows stay inside the program and Meridio stays over them, usable): Meridio's stage (M.Stage), in Qt's
    // overlay over the windows (Theme.stack.ASSISTANT) and under the menus and tooltips (POPUP); only his own surfaces
    // take the pointer (his character, his bubble, R570's shields)
    M.Stage {
        id: assistantStage; objectName: "assistantStage"
        parent: T.Overlay.overlay
        z: Theme.stack.ASSISTANT
    }
    Item {
        id: meridio; objectName: "meridio"; parent: assistantStage.contentItem
        visible: !root.fileOpen && !root.partSources.assistant
        Keys.onPressed: event => root.altPressed(event)
        Keys.onReleased: event => root.altReleased(event)
        x: Math.max(0,root.width-shell.metrics.rightWidth-width-Theme.space.XXL)
        y: Math.max(0,root.height-shell.metrics.checksHeight-height-Theme.space.XXL)
        width: Theme.icon.TILE*2; height: width; z: 100
        Behavior on x { enabled: root.helpMoving; NumberAnimation { duration: Theme.motion.SLOW; easing.type: Theme.motion.EASE } }
        Behavior on y { enabled: root.helpMoving; NumberAnimation { duration: Theme.motion.SLOW; easing.type: Theme.motion.EASE } }
        Image { anchors.fill: parent; source: mascotSource; sourceSize.width: width*Screen.devicePixelRatio; sourceSize.height: height*Screen.devicePixelRatio }
        MouseArea { anchors.fill: parent; drag.target: meridio; drag.minimumX: 0; drag.maximumX: root.width-meridio.width
            drag.minimumY: 0; drag.maximumY: root.height-meridio.height; cursorShape: Qt.SizeAllCursor
            onClicked: root.helpOpen=!root.helpOpen }
        Accessible.role: Accessible.Button; Accessible.name: L.meridio
        M.Card {
            visible: root.helpOpen; title: L.guide; closable: true; onClosed: root.helpOpen=false
            width: Theme.size.BUBBLE_MIN_WIDTH; height: Theme.size.BUBBLE_MIN_HEIGHT
            x: Math.max(-meridio.x,Math.min(-width-Theme.space.M,root.width-meridio.x-width))
            y: Math.max(-meridio.y,Math.min(0,root.height-meridio.y-height))
            M.ReadableText { anchors.fill: parent; text: shell.helpText(root.phase); wrapMode: Text.WordWrap; textStyle: "description" }
        }
    }
    Loader {
        // Above header, pages and footer (R612: Meridio «finisce dietro la barra degli strumenti»), and since R628 over
        // the windows too: on Meridio's stage, in Qt's overlay, under the menus and tooltips. Not a full-window item of
        // the overlay itself: there it would take the presses that close a popup (D05, D07), and a modal window would
        // take his. The host and its layer are plain items, which take no press; only his surfaces do.
        parent: assistantStage.contentItem
        // visible even with File open: the host decides (the tour is hosted there, the character is not, R21 F6c)
        anchors.fill: parent; source: root.partSources.assistant || ""
        onLoaded: {
            item.workbench=root
            item.width=Qt.binding(()=>root.width)
            item.height=Qt.binding(()=>root.height)
        }
    }
    CommandDialogs { anchors.fill: parent }
    Item {
        id: fileVeil; objectName: "fileTransition"; parent: T.Overlay.overlay
        x: 0; y: root.fileMotionTop; width: root.width; height: root.height-y-root.fileMotionBottom
        property bool running: false
        property real direction: 1
        property real t: 0
        readonly property real shown: 1 - Math.pow(1 - t, 3)
        property int waitFrames: 0
        property real lastFrame: 0
        visible: running
        z: Theme.stack.TRANSITION; clip: true
        Rectangle {
            // the window's ground over the new page, fading out: the page fades in
            width: fileVeil.width; height: fileVeil.height
            color: Theme.colors.window
            opacity: 1-fileVeil.shown
        }
        Connections {
            target: fileVeil.visible ? root : null
            function onFrameSwapped() {
                const now = Date.now()
                if (fileVeil.waitFrames > 0) { fileVeil.waitFrames--; fileVeil.lastFrame = now; root.requestUpdate(); return }
                const step = Math.min((now - fileVeil.lastFrame) / Theme.motion.FAST, .12)
                fileVeil.lastFrame = now
                fileVeil.t = Math.min(1, fileVeil.t + Math.max(step, .02))
                if (fileVeil.t >= 1) fileVeil.running = false
            }
        }
    }
    MouseArea {
        id: helpPicker; parent: T.Overlay.overlay; anchors.fill: parent; z: Theme.stack.PICKER
        visible: false; cursorShape: Qt.WhatsThisCursor
        onClicked: mouse => { visible=false; root.helpAt(mouse.x,mouse.y) }
        Keys.onEscapePressed: visible=false
    }
}
