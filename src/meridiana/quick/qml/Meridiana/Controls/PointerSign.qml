import QtQuick
import Meridiana.Theme

// R535: what a modifier key does, beside the pointer, one for every view: the plan's + and - of the selection
// (SelectionOverlay, R529: Shift adds, Ctrl adds or takes away, a window with Ctrl takes away), the command's icon on a side «Align» takes (R497),
// the 3D view's corners with Ctrl. A square of the plan's halo, 18 px, 14 px right and 16 px under the pointer, the
// sign bold in the hover's light blue (adding) or the critical red (taking away). The 3D view drew a white cross of
// its own, 11 px, with a dark core (Daniel 07/11/2026: «il simbolo + non c'entra nulla con quello visto altrove»).
Rectangle {
    id: root
    property point pointer: Qt.point(0, 0)
    property string sign: "add"        // "add", "remove"; "" for an icon
    property string iconName: ""
    property color iconColor: Theme.colors.overlay.ink
    // view_colours.PHOTO (halo, sweep_remove) and the module's hover (SelectionOverlay.hoverColours.module)
    property var colours: ({halo: Theme.colors.overlay.halo, sweep_remove: Theme.colors.overlay.remove})
    property color addColor: Theme.colors.overlay.add
    readonly property real offsetX: 14
    readonly property real offsetY: 16
    x: pointer.x+offsetX; y: pointer.y+offsetY
    width: 18; height: 18; radius: 3
    color: colours.halo
    Icon {
        visible: root.iconName !== ""
        anchors.centerIn: parent; width: 14; height: 14
        name: root.iconName || "view_align"; color: root.iconColor
    }
    Icon {
        objectName: "pointerSignText"
        visible: root.iconName === ""
        anchors.centerIn: parent; width: 18; height: 18
        name: root.sign === "remove" ? "control:minus" : "control:plus"
        color: root.sign === "remove" ? root.colours.sweep_remove : root.addColor
    }
}
