import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as MC

Item {
    id: root
    property real angle: 0
    property var points: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    property string tooltipText: ""
    property color ink: Theme.colors.overlay.ink
    property color background: Theme.colors.overlay.glass_soft
    readonly property real bearing: ((angle % 360) + 360) % 360
    readonly property string headingText: bearing.toLocaleString(Qt.locale(), "f", 0) + "° " + points[Math.floor((bearing + 22.5) / 45) % 8]
    readonly property point letterCentre: Qt.point(28 - 18.5 * Math.sin(bearing * Math.PI / 180),
                                                   28 - 18.5 * Math.cos(bearing * Math.PI / 180))
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
    Rectangle { x: 2; y: 2; width: 52; height: 52; radius: 26; color: root.background }
    Item {
        x: 28
        y: 28
        rotation: -root.bearing
        transformOrigin: Item.TopLeft
        Text {
            x: -8; y: -25.5; width: 16; height: 14
            text: root.points[0]
            color: root.ink
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: Theme.fontFamily
            font.pixelSize: Theme.text.label.size
            font.weight: Theme.text.label.weight
        }
        Shape {
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "transparent"
                fillColor: root.ink
                PathSvg { path: "M0,-11 L3.5,-4 L-3.5,-4 Z" }
            }
            ShapePath {
                strokeColor: root.ink
                strokeWidth: 1.4
                capStyle: ShapePath.RoundCap
                fillColor: "transparent"
                PathSvg { path: "M0,-4 L0,-2 M0,4 L0,10" }
            }
        }
    }
    Rectangle { x: 25.8; y: 25.8; width: 4.4; height: 4.4; radius: 2.2; color: root.ink }
    Text {
        x: 0; y: 58; width: root.width; height: 18
        text: root.headingText
        color: root.ink
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.family: Theme.fontFamily
        font.pixelSize: Theme.text.label.size
        font.weight: Theme.text.label.weight
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Math.round(root.bearing * 10) % 3600 !== 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.north()
    }
    MC.ToolTip { pressed: mouse.pressed; visible: mouse.containsMouse && root.tooltipText.length > 0; text: root.tooltipText }
}
