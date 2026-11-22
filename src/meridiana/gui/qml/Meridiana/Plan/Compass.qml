import QtQuick
import QtQuick.Controls
import Meridiana.Theme
import Meridiana.Controls as MC

// The plan's sign of North (R643, proposal A: Controls/NorthSign.qml, the drawing shared with the 3D view and the
// report). North up it says nothing more; turned, the degrees stand under it in their pill and a click (the hand)
// brings North up again (`north`). Placed by the plan in its corner (placeAt), travelling when the corner changes.
Item {
    id: root
    property real angle: 0
    property var points: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    property string tooltipText: ""
    property color ink: Theme.colors.overlay.ink
    property color background: Theme.colors.overlay.glass
    readonly property real bearing: ((angle % 360) + 360) % 360
    readonly property bool turned: Math.round(bearing * 10) % 3600 !== 0
    // the tooltip's words (with the octant) and the pill's (the degrees alone, only when turned)
    readonly property string headingText: bearing.toLocaleString(Qt.locale(), "f", 0) + "° " + points[Math.floor((bearing + 22.5) / 45) % 8]
    readonly property string degreesText: turned ? bearing.toLocaleString(Qt.locale(), "f", 0) + "°" : ""
    // the needle's tip, in the item: where North is, at four tenths of the sign from its middle
    readonly property point tipPoint: Qt.point(sign.side / 2 - 0.4 * sign.side * Math.sin(bearing * Math.PI / 180),
                                               sign.side / 2 - 0.4 * sign.side * Math.cos(bearing * Math.PI / 180))
    readonly property bool travelling: travel.running
    property bool _placed: false
    property bool _lower: false
    property real _targetX: 0
    property real _targetY: 0
    signal north()
    signal rotate(real degrees)
    width: MC.ControlMetrics.compass.width
    height: MC.ControlMetrics.compass.height

    function placeAt(px, py, lower) {
        if (travel.running && _targetX === px && _targetY === py) return;
        const changed = _placed && lower !== _lower;
        _placed = true;
        _lower = lower;
        travel.stop();
        _targetX = px;
        _targetY = py;
        if (changed && visible && !Theme.reducedMotion) {
            moveX.from = x;
            moveY.from = y;
            travel.start();
        } else {
            x = px;
            y = py;
        }
    }
    ParallelAnimation {
        id: travel
        NumberAnimation { id: moveX; target: root; property: "x"; to: root._targetX; duration: Theme.motion.SLOW; easing.type: Theme.motion.EASE }
        NumberAnimation { id: moveY; target: root; property: "y"; to: root._targetY; duration: Theme.motion.SLOW; easing.type: Theme.motion.EASE }
    }
    MC.NorthSign {
        id: sign
        objectName: "compassSign"
        north: -root.bearing
        degreesText: root.degreesText
        tooltipText: root.tooltipText
        ink: root.ink
        ground: root.background
        onClicked: root.north()
    }
}
