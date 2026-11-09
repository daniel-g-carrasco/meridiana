import QtQuick
import Meridiana.Theme

// ui/fades.py: a 12 px veil, on the side that has more content to scroll.
// Kept here until the shared Controls owner adopts it for the other pages.
Item {
    id: root
    required property var viewport
    property bool page: true
    property color ground: Theme.colors.panel
    parent: viewport
    width: viewport ? viewport.width : 0
    height: viewport ? viewport.height : 0
    z: 100
    function tint(alpha) { return Qt.rgba(ground.r, ground.g, ground.b, alpha) }
    Repeater {
        model: [true, false]
        Rectangle {
            required property bool modelData
            objectName: modelData ? "scroll-fade-top" : "scroll-fade-bottom"
            width: root.width
            height: Math.min(12, Math.floor(root.height/5))
            y: modelData ? 0 : root.height-height
            rotation: modelData ? 0 : 180
            visible: root.viewport && (modelData ? !root.viewport.atYBeginning : !root.viewport.atYEnd)
            gradient: Gradient {
                GradientStop { position: 0; color: root.tint(1) }
                GradientStop { position: root.page ? .18 : .16; color: root.tint(root.page ? .75 : .42) }
                GradientStop { position: .5; color: root.tint(root.page ? .28 : .10) }
                GradientStop { position: 1; color: root.tint(0) }
            }
        }
    }
}
