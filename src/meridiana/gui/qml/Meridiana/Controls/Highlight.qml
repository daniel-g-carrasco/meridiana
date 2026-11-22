import QtQuick
import Meridiana.Theme

// R617 (Daniel 14/11/2026: «unifica pure»): the one highlight drawn around an element of the interface, variant E of
// the sketches of 14/11/2026 that Daniel chose for Meridio (R555 (11): «più minimal e senza colore d'accento»). A hair
// line of the focus' grey (Theme.colors.focus), Theme.highlight.GAP from the element on its four sides, each corner
// concentric to the element's (its radius = the element's + the gap), so that the margin stays the same along the
// curve. It arrives once at every new target, Theme.highlight.ARRIVAL farther, as thick as the focus and see-through,
// and settles in Theme.highlight.SETTLE, never in a loop; with less motion it is there at once, still.
// `inside`: an element with no room around it (a row of a card, its neighbours touching it) has the same line
// Theme.highlight.GAP inside its own edge line (`edgeLine`), its corners the element's - the gap.
// Every number is design.Highlight's; who uses it gives only where (targetRect, radii) and when (active, target).
// Uses: Meridio's (Assistant/AssistantLayer, «assistantSpotlight»). The check opened from its mark is a selected row,
// select_bg, since R663 (Checks/ChecksPage).
Rectangle {
    id: root
    property rect targetRect: Qt.rect(0, 0, 0, 0)
    // the element's four corners at its outer edge: top-left, top-right, bottom-right, bottom-left
    property var radii: [0, 0, 0, 0]
    // what is shown: a new one (another item, «Previous» too) makes the line arrive again; the same one moving does not
    property var target: null
    property bool active: false
    // kept while active; otherwise it goes after Theme.highlight.HOLD
    property bool persistent: false
    property bool inside: false
    property real edgeLine: 0
    property real progress: 1
    property color ink: Theme.colors.focus
    readonly property real line: Theme.highlight.LINE
    readonly property real away: 1 - progress
    // the room the parent leaves around the element: when it is short (the phase tab is Theme.space.XXS under the
    // window's top) the gap is smaller on the four sides together, never on the side without room alone
    readonly property real room: inside ? Infinity : parent ? Math.min(targetRect.x, targetRect.y,
        parent.width - targetRect.x - targetRect.width, parent.height - targetRect.y - targetRect.height) : 0
    readonly property real gap: inside ? Theme.highlight.GAP + edgeLine
                                       : Math.max(0, Math.min(Theme.highlight.GAP, room - line))
    // how far the line's outer edge stands out of the element's edge (less than nought: inside it)
    readonly property real outset: (inside ? -gap : gap + border.width) + away * Theme.highlight.ARRIVAL
    function corner(i) { return Math.max(0, (root.radii && root.radii[i] > 0 ? root.radii[i] : 0) + outset) }
    x: targetRect.x - outset; y: targetRect.y - outset
    width: targetRect.width + 2 * outset; height: targetRect.height + 2 * outset
    topLeftRadius: corner(0); topRightRadius: corner(1); bottomRightRadius: corner(2); bottomLeftRadius: corner(3)
    color: "transparent"
    border.width: line + away * (Theme.highlight.ARRIVAL_LINE - line)
    border.color: ink
    property real shown: active ? 1 : 0
    Behavior on shown { NumberAnimation { duration: Theme.highlight.FADE } }
    opacity: shown * progress
    visible: opacity > 0 && targetRect.width > 0
    NumberAnimation { id: arrival; target: root; property: "progress"; from: 0; to: 1; duration: Theme.highlight.SETTLE; easing.type: Theme.motion.EASE }
    function arrive() {
        if (!active) return
        if (Theme.reducedMotion) { arrival.stop(); progress = 1 }
        else arrival.restart()
    }
    onActiveChanged: arrive()
    onTargetChanged: arrive()
    Timer { interval: Theme.highlight.HOLD; running: root.active && !root.persistent; onTriggered: root.active = false }
    // Deliberately no input handler: the highlighted control keeps its gestures and focus.
}
