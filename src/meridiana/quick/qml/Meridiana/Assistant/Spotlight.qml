import QtQuick
import Meridiana.Theme

Rectangle {
    id: root
    property rect targetRect: Qt.rect(0, 0, 0, 0)
    property bool active: false
    property bool persistent: false
    property real progress: 0
    property color ink: Theme.colors.accent
    readonly property real growth: 3 + (Theme.reducedMotion ? 0 : 1.5*Math.pow(Math.sin(progress*Math.PI*2), 2))
    x: Math.max(1.5, targetRect.x - growth); y: Math.max(1.5, targetRect.y - growth)
    width: Math.max(0, Math.min(parent.width-1.5, targetRect.x+targetRect.width+growth)-x)
    height: Math.max(0, Math.min(parent.height-1.5, targetRect.y+targetRect.height+growth)-y)
    radius: Theme.radius.CONTROL + 2
    color: Qt.rgba(ink.r, ink.g, ink.b, 16/255)
    border.width: Theme.line.FOCUS
    border.color: Qt.rgba(ink.r, ink.g, ink.b, 220/255)
    visible: opacity > 0 && targetRect.width > 0
    opacity: active ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : 160 } }
    NumberAnimation { id: pulse; target: root; property: "progress"; from: 0; to: 1; duration: Theme.motion.PULSE }
    onActiveChanged: if (active && !Theme.reducedMotion) pulse.restart()
    onTargetRectChanged: if (active && !Theme.reducedMotion) pulse.restart()
    Timer { interval: 1500; running: root.active && !root.persistent; onTriggered: root.active = false }
    // Deliberately no input handler: the highlighted control keeps its gestures and focus.
}
