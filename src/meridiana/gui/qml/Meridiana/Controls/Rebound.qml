import QtQuick
import Meridiana.Theme

// R530 (Daniel 07/11/2026: «prima c'era una bella animazione: quando si arrivava al fondo di un qualsiasi scrolling, c'era
// una sorta di rimbalzo. Come mai adesso non c'è più?»): at the top or the bottom of what scrolls, a little overshoot and a
// soft return, the same everywhere; made by M.ScrollBar for its list. Dragged (finger, pen, mouse on a touch list), the
// Flickable's own overshoot with its rebound; with the wheel or the touchpad, which in Qt Quick never overshoot, an
// impulse: the content goes ControlMetrics.reboundReach past the end in Theme.motion.FAST and comes back in
// Theme.motion.NORMAL, on a Translate of the content only (the bar and the fades stay where they are). The handler
// does not block: the Flickable gets every wheel event as before.
WheelHandler {
    id: root
    property Flickable flickable: null
    readonly property bool scrolls: !!flickable && flickable.contentHeight > flickable.height + 1
    target: null
    blocking: false
    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    property Translate shift: Translate { objectName: "reboundShift" }
    property int bounces: 0
    function kick(direction) {
        if (root.reach.running || Theme.reducedMotion) return
        root.reach.direction = direction
        bounces++
        root.reach.restart()
    }
    onWheel: event => {
        if (!scrolls) return
        const delta = event.angleDelta.y !== 0 ? event.angleDelta.y : event.pixelDelta.y
        if (delta < 0 && flickable.atYEnd) kick(-1)
        else if (delta > 0 && flickable.atYBeginning) kick(1)
    }
    property SequentialAnimation reach: SequentialAnimation {
        property int direction: 1
        NumberAnimation { target: root.shift; property: "y"; to: root.reach.direction * ControlMetrics.reboundReach
            duration: Theme.motion.FAST; easing.type: Theme.motion.EASE }
        NumberAnimation { target: root.shift; property: "y"; to: 0; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
    }
    property Transition rebound: Transition {
        NumberAnimation { properties: "x,y"; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
    }
    function attach() {
        if (!flickable) return
        flickable.boundsBehavior = Flickable.DragAndOvershootBounds
        flickable.boundsMovement = Flickable.FollowBoundsBehavior
        flickable.rebound = rebound
        const content = flickable.contentItem
        const list = []
        for (let i = 0; i < content.transform.length; i++) list.push(content.transform[i])
        if (list.indexOf(shift) < 0) { list.push(shift); content.transform = list }
    }
    Component.onCompleted: attach()
}
