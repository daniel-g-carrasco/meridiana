import QtQuick

// R570 (Daniel 09/11 and 14/11/2026: «continua ad esserci con il fumetto di Meridio il problema che il cursore può
// interagire dietro di lui»): a surface that floats over the window (Meridio's bubble and character, a floating card)
// takes for itself every gesture of the pointer over its drawing, also where it has no control of its own (its
// margins, between its lines, the ground inside its outline): the hover, the cursor, the clicks of every button, the
// double click, the drag, the wheel (also sideways and with Ctrl), a touch and a pinch of the touchscreen. What falls outside
// its drawing (past a rounded corner, beside its tail) goes through to what is behind. It fills its parent and lies
// under the parent's own content (z -1), so the surface's controls keep their gestures; the cursor over it is the
// arrow unless a control of its own sets another. A hover it takes still goes up to the window's own HoverHandlers
// (Meridio's eyes follow the pointer). `radius` rounds its corners (a circle at half the side); `outline`,
// a Shape with `containsMode: Shape.FillContains`, is the drawing instead (the bubble with its tail).
MouseArea {
    id: root
    objectName: "pointerShield"
    property real radius: 0
    property Item outline: null
    anchors.fill: parent
    z: -1
    hoverEnabled: true
    acceptedButtons: Qt.AllButtons
    // a drag begun on it is its own: a DragHandler behind (the plan's, the 3D view's) does not take it over
    preventStealing: true
    cursorShape: Qt.ArrowCursor
    onWheel: wheel => { wheel.accepted = true }
    containmentMask: QtObject {
        function contains(point: point): bool {
            if (root.outline && root.outline.visible) return root.outline.contains(root.mapToItem(root.outline, point))
            if (point.x < 0 || point.y < 0 || point.x > root.width || point.y > root.height) return false
            const r = Math.min(root.radius, root.width / 2, root.height / 2)
            const cx = Math.max(r, Math.min(root.width - r, point.x)), cy = Math.max(r, Math.min(root.height - r, point.y))
            return (point.x - cx) * (point.x - cx) + (point.y - cy) * (point.y - cy) <= r * r
        }
    }
    // the points of a touchscreen: a mouse area takes only the first finger (as a mouse), the others went behind
    MultiPointTouchArea { anchors.fill: parent; mouseEnabled: false; containmentMask: root.containmentMask }
    // the touchpad's pinch, which comes as a gesture of its own (Wayland, macOS; Windows gives Ctrl and the wheel). Not
    // enough today: Qt still hands that gesture to a PinchHandler behind (KNOWN in docs/quick/stato/r35-meridio.md)
    PinchHandler { target: null }
}
