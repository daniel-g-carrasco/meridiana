import QtQuick
import Meridiana.Theme

// R592 (Daniel 11/11/2026: «due segni, due significati»): the full arrow, the one sign of what chooses a value: a
// drop-down list, a button with a menu, a submenu, the steps of a number, a table's order. Drawn on the screen's
// pixels: the provider's control:arrow-*, rows of whole pixels each two shorter than the one before, asked at the
// size shown (2 x arrowDepth by arrowDepth, whole pixels at 100, 125, 150, 175 and 200 %) and placed on a whole pixel
// of the screen, so the arrow has no half-covered pixel at any scale (the arrow of the lists was a 16 x 14 drawing
// shrunk to 9 x 7 at half a pixel, and blurred). Grey: `muted`, `text2` when its control is under the pointer or has
// the focus (`active`), the disabled text's colour when disabled. Its open sibling, for what opens and closes a
// section, is M.Chevron.
Item {
    id: root
    property string direction: "down"          // down, up, right, left
    property bool active: false
    property color color: !enabled ? Theme.disabledText : active ? Theme.colors.text2 : Theme.colors.muted
    readonly property real dpr: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    readonly property bool across: direction === "right" || direction === "left"
    implicitWidth: across ? ControlMetrics.arrowDepth : 2 * ControlMetrics.arrowDepth
    implicitHeight: across ? 2 * ControlMetrics.arrowDepth : ControlMetrics.arrowDepth
    // where the item is in the window, read again when it or its control moves or changes size
    readonly property point scene: { x; y; width; height; visible; parent && parent.x; parent && parent.y
                                     return mapToItem(null, 0, 0) }
    Image {
        x: ControlMetrics.pixelSnap(root.scene.x, (root.width - width) / 2, root.dpr)
        y: ControlMetrics.pixelSnap(root.scene.y, (root.height - height) / 2, root.dpr)
        width: root.implicitWidth; height: root.implicitHeight
        sourceSize: Qt.size(width, height)
        smooth: false
        source: "image://meridiana/control:arrow-" + root.direction + "/" + encodeURIComponent(root.color.toString())
                + "/" + (Theme.dark ? "dark" : "light") + "/on"
    }
    Accessible.ignored: true
}
