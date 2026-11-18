import QtQuick
import Meridiana.Theme
import Meridiana.Shell

// The QML side of backend/assistant_part.AssistantHost (docs/studio/39-contratto-backend-qml.md): binds the backend's
// `layerSettings` and `capturing`, answers its request signals, writes back the phase shown, File, the conversation
// open and the central panel's rectangle. Items are looked up by name here, never from Python.
Item {
    id: host
    objectName: "assistantHost"
    property var workbench: null
    property Item homeItem: null
    property bool helpPressed: false
    property Item helpButton: null          // the properties card's help button: its press asks the help of the selection
    width: workbench ? workbench.width : 0
    height: workbench ? workbench.contentItem.height : 0
    z: 100
    visible: !assistantHostBackend.capturing
    Component.onCompleted: { assistantHostBackend.attached(); applySettings() }
    function applySettings() {
        const s = assistantHostBackend.layerSettings
        assistantUI.assistantEnabled = s.assistantEnabled
        assistantUI.animated = s.animated
        assistantUI.characterStyle = s.characterStyle
        assistantUI.bubbleWidth = s.bubbleWidth
        assistantUI.bubbleHeight = s.bubbleHeight
        assistantUI.docked = s.docked
    }
    // one item named `name` under root (the window's items are walked in QML, parts.py)
    function find(root, name, onlyVisible) {
        if (!root) return null
        // a window: the item every other hangs from (ApplicationWindow.contentItem is only the middle, two levels
        // under the window's own root item, which holds header, footer and Qt's overlay too)
        let top = root.contentItem || root
        while (top.parent) top = top.parent
        const pending = [top]
        while (pending.length) {
            const item = pending.pop()
            if (item.objectName === name && (!onlyVisible || item.visible)) return item
            const kids = item.children || []
            for (let i = kids.length - 1; i >= 0; i--) pending.push(kids[i])      // in order, first child first
        }
        return null
    }
    function findFirst(names) {
        for (let i = 0; i < names.length; i++) {
            const item = find(host.workbench, names[i], false) || find(host, names[i], false)
            if (item) return item
        }
        return null
    }
    function panel(id) {
        const panels = workbench && workbench.workspaceItem ? workbench.workspaceItem.panels : []
        for (let i = 0; i < panels.length; i++) if (panels[i].panelId === id) return panels[i]
        return null
    }
    function toggle() {
        if (assistantUI.opened && (!assistantUI.docked || assistantUI.dockVisible)) assistantUI.dismiss()
        else { assistantUI.open(); assistantUI.panelRequested() }
    }
    Connections {
        target: assistantHostBackend
        function onLayerSettingsChanged() { host.applySettings() }
        function onPhaseRequested(phase) { if (host.workbench) host.workbench.showPhase(phase) }
        function onFileOpenRequested() { if (host.workbench) host.workbench.fileOpen = true }
        function onChecksOpenRequested() { const p = host.panel("checks"); if (p) p.opened = true }
        function onPropertiesSectionRequested(section) {
            const page = host.find(host.workbench, "properties-page", false)
            if (page && page.closed(section)) page.toggle(section)
        }
        function onComputationTabRequested(step) { computationTimer.step = step; computationTimer.restart() }
        function onTourTargetRequested(names) { tourTimer.names = names; tourTimer.restart() }
        function onHelpRequested(key) { assistantUI.showHelpFor(key, host.panel("properties")) }
        function onToggleRequested() { host.toggle() }
        function onFocusHelpRequested() { assistantUI.focusHelp() }
        function onDismissRequested() { assistantUI.dismiss() }
    }
    // after the phase has been shown (its page Loader is synchronous on first visit): the actual tab of records
    Timer {
        id: computationTimer; interval: 0
        property string step: ""
        onTriggered: {
            const page = host.find(host.workbench, "results-scroll", true)
            if (page) {
                const tabs = (page.pageData && page.pageData.tabs) || []
                for (let i = 0; i < tabs.length; i++) if (tabs[i].records !== undefined) { page.select(i); return }
            }
            assistantHostBackend.computationUnavailable(step)
        }
    }
    Timer {
        id: tourTimer; interval: 0
        property var names: []
        onTriggered: {
            const item = host.findFirst(names)
            assistantUI.setTourTarget(item)      // R474: never the highlight of the step before
            if (!item) assistantHostBackend.tourTargetMissing()
        }
    }
    Binding { target: assistantUI; property: "places"; value: assistantHostBackend.places_by_phase }
    Binding { target: assistantHostBackend; property: "phaseShown"; value: host.workbench ? host.workbench.phase : "model" }
    Binding { target: assistantHostBackend; property: "fileOpen"; value: !!host.workbench && host.workbench.fileOpen }
    Binding { target: assistantHostBackend; property: "opened"; value: assistantUI.opened }
    Binding { target: assistantHostBackend; property: "viewRect"; value: assistantUI.homeRect }
    function updateHome() {
        if (homeItem && workbench && workbench.visible)
            assistantUI.homeRect = homeItem.mapToItem(assistantUI, 0, 0, homeItem.width, homeItem.height)
    }
    Timer { id: homeLayout; interval: 0; onTriggered: host.updateHome() }
    // R23 F6: Meridio's home, chosen here (backend/scene_part did it from Python): the 3D view in Modelling when it is
    // shown, else the central panel; settled once at the first frame of the window shown (shell_actions.exposed before)
    property bool homeSettled: false
    function chooseHome() {
        if (!workbench) return
        // the Workbench's own items, no walk of the window (15 000 items) at every change of phase
        const scene = workbench.sceneItem
        const view = workbench.phase === "model" && scene && scene.visible ? scene : null
        const next = view || workbench.centralItem || find(workbench, "centralPanel", false)
        if (next && next !== homeItem) homeItem = next
    }
    function settleHome() {
        homeSettled = true
        chooseHome()
        updateHome()
        const animated = assistantUI.animated
        assistantUI.animated = false
        assistantUI.repositionHome()
        assistantUI.animated = animated
    }
    Connections {
        target: host.workbench
        function onVisibleChanged() { homeLayout.restart() }
        function onWidthChanged() { homeLayout.restart() }
        function onHeightChanged() { homeLayout.restart() }
        // The overlay's transform settles after exposure, without changing the
        // central item's own geometry (notably for a frameless window).
        function onFrameSwapped() { if (!host.homeSettled && host.workbench.visible) host.settleHome(); else host.updateHome() }
        function onPhaseChanged() { Qt.callLater(host.chooseHome) }
        function onViewModeChanged() { Qt.callLater(host.chooseHome) }
        function onViewsArrangementChanged() { Qt.callLater(host.chooseHome) }
        function onSceneItemChanged() { Qt.callLater(host.chooseHome) }
        // the help button of the properties card, the status bar's help and Meridio's own button all flip `helpOpen`:
        // from the properties button it is the help of what is selected, from the others the conversation
        function onHelpOpenChanged() {
            if (!host.workbench.helpOpen) return
            host.workbench.helpOpen = false
            if (host.helpPressed) { host.helpPressed = false; assistantHostBackend.properties_help() }
            else host.toggle()
        }
    }
    Connections {
        target: host.homeItem
        function onWidthChanged() { homeLayout.restart() }
        function onHeightChanged() { homeLayout.restart() }
        function onXChanged() { homeLayout.restart() }
        function onYChanged() { homeLayout.restart() }
    }
    onHomeItemChanged: homeLayout.restart()
    onWorkbenchChanged: {
        if (!workbench) return
        chooseHome()
        helpButton = find(workbench, "propertiesHelp", false)
        // The shell's title drag hit area otherwise covers the help button placed beside the title by the shared
        // Card header.
        if (helpButton) helpButton.parent.parent.z = 2
    }
    Connections { target: host.helpButton; function onPressed() { host.helpPressed = true } }
    function registerPanel() {
        if (!workbench || !dockLoader.item) return
        const workspace = workbench.workspaceItem
        if (!workspace.panels.some(p => p.panelId === "assistant")) {
            workspace.panels = workspace.panels.concat([dockLoader.item])
            workspace.arrangementChanged()
        }
    }
    Loader {
        id: dockLoader
        active: !!host.workbench
        onLoaded: host.registerPanel()
        sourceComponent: DockPanel {
            id: dock
            objectName: "assistantDockPanel"
            parent: host.workbench.workspaceItem
            workspace: host.workbench.workspaceItem
            panelId: "assistant"; zone: "right"; title: assistantText.name
            // R503 (Daniel 06/11/2026: «ho premuto il tasto per farlo diventare scheda ma è scomparso e non riesco a farlo
            // ricomparire»): docked, the character is hidden, and the panel was there only while the conversation was
            // open, so once it closed nothing of Meridio was left on screen. Now docked he is a tab of the panels
            // while docked, open or closed; closing that tab puts him back floating, never nowhere.
            opened: assistantUI.docked
            onClosed: { assistantUI.dismiss(); assistantUI.docked = false
                assistantUI.placementSaved(assistantUI.avatarX, assistantUI.avatarY, assistantUI.bubbleWidth, assistantUI.bubbleHeight, false) }
            Item { id: dockSpace; anchors.fill: parent }
            property var assistantSpace: dockSpace
        }
    }
    AssistantLayer {
        id: assistantUI
        anchors.fill: parent
        chat: assistantChat
        helpService: assistantHelp
        useShortcuts: false
        topInset: Math.max(0, homeRect.y)
        bottomInset: host.workbench && host.workbench.footer ? host.workbench.footer.height : 0
        phaseKey: host.workbench ? host.workbench.phase : "model"
        readonly property var panel: dockLoader.item
        dockItem: panel ? panel.assistantSpace : null
        dockRect: panel ? panel.assistantSpace.mapToItem(assistantUI, 0, 0, panel.assistantSpace.width, panel.assistantSpace.height) : Qt.rect(0,0,360,500)
        dockVisible: !panel || panel.visible
        onPlacementSaved: (x, y, width, height, docked) =>
            assistantHostBackend.placement(x, y, width, height, docked, assistantUI.width, assistantUI.height, assistantUI.temporary)
        onDockedChanged: {
            // the tab's own close sets its `opened` and ends the binding: set again at each docking
            if (panel) panel.opened = docked
            if (docked && panel) panel.workspace.selectPanel("assistant")
            if (panel) panel.workspace.arrangementChanged()
        }
        onOpenedChanged: {
            if (docked && panel && opened) panel.workspace.selectPanel("assistant")
            if (panel) panel.workspace.arrangementChanged()
        }
        onPanelRequested: if (docked && panel) panel.workspace.selectPanel("assistant")
        visible: !host.workbench || !host.workbench.fileOpen || temporary
    }
}
