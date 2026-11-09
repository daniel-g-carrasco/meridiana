import QtQuick
import Meridiana.Theme

// R524: the band of a section's head and its hover, one for every section (M.Section, Properties' CollapsibleSection,
// the Plant's panel): the hover covers the whole head, from its top to its bottom, rounded at the top as the band,
// square at the bottom while the section is open (the body goes on under it). Before, the Plant's head laid a strip of
// the band's colour over the bottom of the hover to square it, and a band of 6-8 px stayed out of the hover
// (Daniel 07/11/2026: «l'hover sui titoli delle sottoschede rimane spezzato in due»).
Item {
    id: root
    property bool open: false
    property bool hovered: false
    property bool pressed: false
    property color ground: Theme.colors.line_soft
    property real radius: Theme.radius.CONTROL
    clip: true
    Rectangle {
        objectName: "sectionBandGround"
        width: parent.width; height: parent.height + (root.open ? root.radius : 0)
        radius: root.radius; color: root.ground
        Rectangle {
            objectName: "sectionBandHover"
            anchors.fill: parent; radius: parent.radius
            color: root.pressed ? Theme.colors.press : root.hovered ? Theme.colors.hover : "transparent"
        }
    }
}
