import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

M.Card {
    id: panel
    property string panelId
    property string zone
    property bool opened: true
    property bool phaseAllowed: true
    property bool phaseLeaving: false
    property var workspace
    property var members: workspace ? workspace.tabMembers(zone) : []
    property bool stacked: workspace ? workspace.stackedHere(panel) : false
    property bool selected: !workspace || stacked || workspace.activePanel(zone) === panelId
    // Carried, it keeps its size: its picture is what goes with the pointer.
    property rect frozen
    readonly property rect placed: moving ? frozen : floating || !workspace ? Qt.rect(floatX,floatY,floatWidth,floatHeight) : workspace.place(panel)
    property real floatX: Theme.space.XXXL
    property real floatY: Theme.space.XXXL
    property real floatWidth: Theme.size.READING
    property real floatHeight: Theme.size.READING
    property bool floating: zone === "floating"
    property bool moving: workspace && workspace.draggedPanel === panelId
    clip: true
    layoutWidth: workspace && (workspace.draggedPanel!=="" || workspace.settling) ? placed.width : width
    layoutHeight: workspace && (workspace.draggedPanel!=="" || workspace.settling) ? placed.height : height
    // R37 (Daniel 21/11/2026: «il ridimensionamento delle schede è molto scattante in qualsiasi fase»): while an
    // edge of the workspace is dragged what the card holds keeps its size, laid out again once at the release. The
    // card itself, its head and its cross follow the pointer. Before, every pixel laid out the whole inspector again
    // (30-45 ms a step on the Plant inspector). Since the kit's live drag (r39): only when the steps measured cost too
    // much (Workbench.qml, workspace.holdContent); otherwise what the card holds follows the edge live.
    property size held
    readonly property bool holding: !!(workspace && workspace.resizing && workspace.holdContent)
    onHoldingChanged: if (holding) held=Qt.size(contentItem.width, contentItem.height)
    bodyWidth: holding ? held.width : -1
    bodyHeight: holding ? held.height : -1
    closable: true
    closeTip: L.closeCard
    color: Theme.colors.panel
    // Carried, its picture goes with the pointer, and the place it left closes (ui/dock_motion.py Reflow).
    M.PhaseFade {
        target: panel
        current: panel.opened && panel.phaseAllowed && (panel.floating || panel.selected)
        leaving: panel.phaseLeaving && panel.opened
        animated: !!(panel.workspace && panel.workspace.phaseTransition)
        suppressed: !!(panel.moving && panel.workspace && (panel.workspace.ghostReady || panel.workspace.landing))
    }
    z: floating ? 20 : 0
    x: placed.x
    y: placed.y
    width: placed.width
    height: placed.height
    onClosed: { opened=false; workspace.arrangementChanged() }
    DockMotion on x { settling: workspace && workspace.settling && !panel.moving }
    DockMotion on y { settling: workspace && workspace.settling && !panel.moving }
    DockMotion on width { settling: workspace && workspace.settling && !panel.moving }
    DockMotion on height { settling: workspace && workspace.settling && !panel.moving }
    // R637: what it holds stands ControlMetrics.cardMargin from its border on the four sides (from the head's row above)
    bodyMargin: M.ControlMetrics.cardMargin
    // R528: the cards grouped as tabs have the segmented control of Checks (Controls/Segments) at their head, under
    // the title, as wide as the body: a click brings a card forward, the card shown is the raised segment, a long
    // name is cut with the dots and its tooltip says it whole. A tab carried away takes its card out of the group,
    // as the title does for the card shown (Daniel: «come mai le linguette nel caso di schede sovrapposte non sono
    // di questo tipo?»).
    // R632 (Daniel 15/11/2026: «è possibile dare a queste linguette delle dimensioni più piccole (anche perché quando si
    // impilano scheda in basso, con Verifiche, diventano larghissime) e spostarle da lì mettendole nella riga sopra?
    // praticamente di fianco a "?" e alla "X"»): they stand in the head's row, where the title stands alone, as wide
    // as their words (the segments' own measure), the «?» and the cross at the right of the same row; the row of their
    // own under the head is gone. Where they do not fit (a narrow column, many cards) they share the room left of the
    // «?» in proportion to their words, a cut name ends with the dots and its tooltip says it whole, as before.
    // R528 (r23-f5): the tabs say the titles, the one shown raised: the head does not say it again beside them
    titleShown: !groupTabs.visible
    // R632: what the head's start takes, the title or the tabs: a page that lays its own tools in the head (Checks,
    // ChecksPage.titleWidth) starts them after it
    readonly property real headLead: groupTabs.visible ? groupTabs.width : Theme.measureText(title, "title").width
    M.Segments {
        id: groupTabs; parent: panel.headRow; objectName: panel.panelId+"GroupTabs"
        visible: panel.members.length>1 && !panel.floating
        width: Math.min(implicitWidth, panel.headRow.width)
        model: visible ? panel.members.map(p=>({text:p.title,tip:p.title})) : []
        currentIndex: panel.members.findIndex(p=>p.panelId===panel.panelId)
        onActivated: index => panel.workspace.selectPanel(panel.members[index].panelId)
        function indexAt(x) { for(let i=0;i<panel.members.length;i++) if(x-leftPadding<segmentX(i)+segmentWidth(i)) return i; return panel.members.length-1 }
        // Over the segments, leaving them the hover (their tooltip): a click chooses the segment under it, a press
        // carried past the title's distance carries that segment's card (its picture, even if it is behind the
        // one shown, which stays). A DragHandler here took the click of the segment for a drag.
        MouseArea {
            objectName: panel.panelId+"GroupTabsGrip"
            anchors.fill: parent; z: 1
            acceptedButtons: Qt.LeftButton
            property point start
            property string carried: ""
            property real pressX
            onPressed: mouse => { start=mapToItem(panel.workspace,mouse.x,mouse.y); pressX=mouse.x; carried="" }
            onPositionChanged: mouse => {
                if(!pressed) return
                const pos=mapToItem(panel.workspace,mouse.x,mouse.y)
                if(!carried && Math.abs(pos.x-start.x)+Math.abs(pos.y-start.y)>Theme.space.M) {
                    const card=panel.members[groupTabs.indexAt(pressX)]
                    if(!card) return
                    carried=card.panelId; panel.workspace.beginDrag(card,start)
                }
                if(carried) panel.workspace.moveDrag(pos)
            }
            onReleased: mouse => { if(carried) { carried=""; panel.workspace.finishDrag() } else groupTabs.choose(groupTabs.indexAt(mouse.x)) }
            onCanceled: if(carried) { carried=""; panel.workspace.cancelDrag() }
        }
    }
    // R570: carried off its column it floats over the views: it keeps the pointer where its content does not take it
    M.PointerShield { parent: panel; enabled: panel.floating; radius: Theme.radius.CARD }
    // This hit area is parented to the card, not its default content slot.
    MouseArea {
        parent: panel
        objectName: panel.panelId + "TitleDrag"
        x: Theme.layout.TITLE_X; y: Theme.space.XS
        width: Math.max(Theme.space.XXXL, panel.width-Theme.space.XXXL*2)
        height: Theme.size.CONTROL
        cursorShape: Qt.SizeAllCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        property point start
        property bool carrying: false
        onPressed: mouse => {
            if(mouse.button===Qt.RightButton) { const p=mapToItem(panel.workspace,mouse.x,mouse.y); panel.workspace.titleMenuAt(p.x,p.y); return }
            start=mapToItem(panel.workspace, mouse.x, mouse.y); carrying=false }
        onPositionChanged: mouse => {
            if (!pressed) return
            const pos=mapToItem(panel.workspace,mouse.x,mouse.y)
            if (!carrying && Math.abs(pos.x-start.x)+Math.abs(pos.y-start.y)>Theme.space.M) {
                carrying=true; panel.workspace.beginDrag(panel, start)
            }
            if(carrying) panel.workspace.moveDrag(pos)
        }
        onReleased: { if(carrying) panel.workspace.finishDrag(); carrying=false }
        onCanceled: { panel.workspace.cancelDrag(); carrying=false }
        onDoubleClicked: panel.workspace.floatPanel(panel.panelId)
    }
    MouseArea {
        parent: panel; visible: panel.floating
        anchors.right: parent.right; anchors.bottom: parent.bottom
        width: Theme.space.L; height: width; cursorShape: Qt.SizeFDiagCursor
        property point start
        property real oldWidth
        property real oldHeight
        onPressed: mouse => { start=mapToItem(panel.workspace,mouse.x,mouse.y); oldWidth=panel.width; oldHeight=panel.height }
        onPositionChanged: mouse => {
            if (!pressed) return
            const p=mapToItem(panel.workspace,mouse.x,mouse.y)
            panel.floatWidth=Math.max(Theme.size.PANEL_MIN,oldWidth+p.x-start.x)
            panel.floatHeight=Math.max(Theme.size.PANEL_MIN,oldHeight+p.y-start.y)
        }
    }
}
