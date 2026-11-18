import QtQuick
import Meridiana.Theme

// Where a carried thing will fall, told at once (R504, study 36, proposal 1: VS Code and AutoCAD, «release it
// when the outline appears»). The accent's line of Line.FOCUS (2 px) and its faint tint, round as a card, no
// shadow, nothing inside: it marks the place, it does not describe it. It comes and goes with a FAST fade; moved
// while it is shown it slides in FAST; shown again after being hidden it appears in place (`show` jumps first).
// Beside it the Workbench's dashed drop zone, which only answers after the dwell, grows out of this outline.
Rectangle {
    id: outline
    objectName: "dropOutline"
    property bool shown: false
    property bool animated: true
    readonly property int slide: Theme.reducedMotion ? 0 : Theme.motion.FAST
    color: Theme.colors.accent_soft
    border.color: Theme.colors.accent
    border.width: Theme.line.FOCUS
    radius: Theme.radius.CARD
    visible: opacity > 0
    opacity: shown ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: outline.slide } }
    // The place: still when it was out of sight, in FAST when it is already shown.
    function show(r) {
        animated = shown && opacity > 0
        x = r.x; y = r.y; width = r.width; height = r.height
        animated = true
        shown = true
    }
    function hide() { shown = false }
    Behavior on x { enabled: outline.animated; NumberAnimation { duration: outline.slide; easing.type: Theme.motion.EASE } }
    Behavior on y { enabled: outline.animated; NumberAnimation { duration: outline.slide; easing.type: Theme.motion.EASE } }
    Behavior on width { enabled: outline.animated; NumberAnimation { duration: outline.slide; easing.type: Theme.motion.EASE } }
    Behavior on height { enabled: outline.animated; NumberAnimation { duration: outline.slide; easing.type: Theme.motion.EASE } }
}
