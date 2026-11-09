import QtQuick
import Meridiana.Theme

// R476, R21-F2: the one opening of everything that comes up over the window, a menu (Menu.qml) or a popup
// (Popup.qml): a fade with a slide of a few pixels, ControlMetrics.menuReveal long with a soft end. The size is whole
// from the first frame, which is drawn transparent: what the popup costs the first time (its entries laid out, the
// shadow) is paid in that frame, which is not seen. The reveal moves with the frames shown, at most menuStepMax in
// one: a slow frame slows it, it does not skip it. `item` is the popup's contentItem, whose window gives the frames.
QtObject {
    id: root
    property Item item: null
    property real reveal: 1
    readonly property real shown: 1 - Math.pow(1 - reveal, 3)
    readonly property real slide: -ControlMetrics.menuSlide * (1 - shown)
    property bool waitingFrame: false
    property bool revealing: false
    property real lastFrame: 0
    function start() { revealing = false; reveal = Theme.reducedMotion ? 1 : 0; waitingFrame = !Theme.reducedMotion }
    function stop() { waitingFrame = false; revealing = false; reveal = 1 }
    property Connections frames: Connections {
        target: (root.waitingFrame || root.revealing) && root.item ? root.item.Window.window : null
        function onFrameSwapped() {
            const now = Date.now()
            if (root.waitingFrame) { root.waitingFrame = false; root.revealing = true; root.lastFrame = now - 16 }
            const step = Math.min((now - root.lastFrame) / ControlMetrics.menuReveal, ControlMetrics.menuStepMax)
            root.lastFrame = now
            root.reveal = Math.min(1, root.reveal + Math.max(step, .02))
            if (root.reveal >= 1) root.revealing = false
        }
    }
}
