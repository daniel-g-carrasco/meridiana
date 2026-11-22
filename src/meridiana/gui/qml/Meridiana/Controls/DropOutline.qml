import QtQuick
import Meridiana.Theme

// A neutral promise of the exact destination, rounded and bordered like a card.
// Its geometry is immediate; opacity follows the theme's FAST motion.
Rectangle {
    id: outline
    objectName: "dropOutline"
    property bool shown: false
    property bool animated: true
    readonly property int slide: Theme.reducedMotion ? 0 : Theme.motion.FAST
    color: Theme.colors.hover
    border.color: Theme.colors.card_line
    border.width: Theme.line.HAIR
    radius: Theme.radius.CARD
    visible: shown && opacity > 0
    opacity: shown ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: outline.slide } }
    // The place: still when it was out of sight, in FAST when it is already shown.
    function show(r) {
        animated = false
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
