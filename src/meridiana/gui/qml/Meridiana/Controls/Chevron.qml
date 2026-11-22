import QtQuick
import Meridiana.Theme

// R592 (Daniel 11/11/2026: «in Progetto è diversa ed ha un buono spessore che mi piace: please centralizziamo!!!!»):
// the open arrow, the one sign of what opens and closes: a section, a group, a row of a tree or of the checks. The
// project tree's drawing (the provider's control:chevron-down, 1.5 px on its 20 px box) at its own size wherever it
// is shown, the box on a whole pixel: pointing down when open, right when closed, turning with `progress` (1 open,
// 0 closed) when the caller moves it. A smaller item keeps the same drawing (it is not shrunk to a thinner line).
// Grey as the full arrow (M.Arrow): `muted`, `text` under the pointer (`active`), the disabled colour.
Item {
    id: root
    property bool open: true
    property real progress: open ? 1 : 0
    property bool active: false
    property color color: !enabled ? Theme.disabledText : active ? Theme.colors.text : Theme.colors.muted
    implicitWidth: ControlMetrics.chevronBox
    implicitHeight: ControlMetrics.chevronBox
    readonly property real dpr: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    readonly property point scene: { x; y; width; height; visible; parent && parent.x; parent && parent.y
                                     return mapToItem(null, 0, 0) }
    Icon {
        x: ControlMetrics.pixelSnap(root.scene.x, (root.width - width) / 2, root.dpr)
        y: ControlMetrics.pixelSnap(root.scene.y, (root.height - height) / 2, root.dpr)
        width: ControlMetrics.chevronBox; height: ControlMetrics.chevronBox
        rotation: -90 * (1 - root.progress)
        name: "control:chevron-down"; color: root.color; dimDisabled: false
    }
    Accessible.ignored: true
}
