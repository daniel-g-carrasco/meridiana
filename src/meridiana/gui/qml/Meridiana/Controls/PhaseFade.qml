import QtQuick
import Meridiana.Theme

// A changing body stays drawn while leaving, but loses input (and its popups) at once.
// The target owns its geometry and lifetime; unchanged shared bodies never start an animation.
Item {
    id: root
    property Item target: parent
    property bool current: true
    property bool leaving: false
    property bool animateEntry: false
    property bool animated: true
    property bool suppressed: false
    property bool retained: false
    property bool ready: false
    Binding { target: root.target; property: "visible"; value: root.retained || root.current || root.leaving }
    Binding { target: root.target; property: "enabled"; value: root.current }
    function update() {
        if (!ready || !target) return
        fade.stop()
        if (!Theme.phaseMotion || !animated || suppressed || (!current && !leaving)) target.opacity = current && !suppressed ? 1 : 0
        else {
            // Set both ends before starting: dependent bindings may still be queued at currentChanged.
            fade.from = current ? 0 : 1
            fade.to = current ? 1 : 0
            target.opacity = fade.from
            fade.start()
        }
    }
    onCurrentChanged: update()
    onLeavingChanged: if (!current) update()
    onSuppressedChanged: update()
    Component.onCompleted: { ready = true; target.opacity = current ? 1 : 0; if (current && animateEntry) update() }
    Connections { target: Theme; function onPhaseMotionChanged() { if (!Theme.phaseMotion) root.update() } }
    OpacityAnimator {
        id: fade; target: root.target
        duration: Theme.motion.FAST; easing.type: Theme.motion.EASE
    }
}
