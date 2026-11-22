import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.Slider {
    id: root
    implicitWidth: horizontal ? 180 : Theme.size.COMPACT
    implicitHeight: horizontal ? Theme.size.COMPACT : 180
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    wheelEnabled: activeFocus
    property real pageStep: stepSize > 0 ? 10*stepSize : Math.abs(to-from)/10
    function page(direction) { value = Math.max(from, Math.min(to, value + direction*pageStep)); moved() }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_PageUp) { page(1); event.accepted = true }
        else if (event.key === Qt.Key_PageDown) { page(-1); event.accepted = true }
        else if (event.key === Qt.Key_Home) { value = from; moved(); event.accepted = true }
        else if (event.key === Qt.Key_End) { value = to; moved(); event.accepted = true }
    }
    MouseArea { id: pageArea; anchors.fill: parent; z: 1
        property int direction: 0
        property real targetValue: 0
        function repeatTowardPointer() {
            const next = root.value + direction*root.pageStep
            root.value = direction > 0 ? Math.min(next, targetValue) : Math.max(next, targetValue)
            root.moved()
            if (root.value === targetValue) repeatPage.stop()
        }
        onPressed: mouse => {
            const point = mapToItem(root.handle, mouse.x, mouse.y)
            if (root.handle.contains(point)) { mouse.accepted = false; return }
            root.forceActiveFocus(Qt.MouseFocusReason)
            direction = root.horizontal ? (mouse.x < root.handle.x ? -1 : 1) * (root.mirrored ? -1 : 1)
                                        : (mouse.y < root.handle.y ? 1 : -1)
            let position = root.horizontal ? (mouse.x-root.handle.width/2)/(root.width-root.handle.width)
                                           : 1-(mouse.y-root.handle.height/2)/(root.height-root.handle.height)
            if (root.horizontal && root.mirrored) position = 1-position
            targetValue = root.from + Math.max(0, Math.min(1, position))*(root.to-root.from)
            if (root.stepSize > 0) targetValue = root.from + Math.round((targetValue-root.from)/root.stepSize)*root.stepSize
            root.page(direction)
            repeatDelay.restart()
        }
        onReleased: { repeatDelay.stop(); repeatPage.stop() }
        onCanceled: { repeatDelay.stop(); repeatPage.stop() }
        Timer { id: repeatDelay; interval: 500; onTriggered: { pageArea.repeatTowardPointer(); if (root.value !== pageArea.targetValue) repeatPage.start() } }
        Timer { id: repeatPage; interval: 50; repeat: true; onTriggered: pageArea.repeatTowardPointer() }
    }
    background: Rectangle {
        x: root.horizontal ? 0 : (root.width-width)/2
        y: root.horizontal ? (root.height-height)/2 : 0
        width: root.horizontal ? root.width : 4
        height: root.horizontal ? 4 : root.height
        radius: 2; color: Theme.colors.line
        Rectangle { x: root.horizontal && root.mirrored ? parent.width-width : 0
            y: root.horizontal ? 0 : root.visualPosition*parent.height
            width: root.horizontal ? root.position*parent.width : parent.width
            height: root.horizontal ? parent.height : root.position*parent.height
            radius: 2; color: Theme.colors.muted }
    }
    handle: Rectangle {
        x: root.horizontal ? root.visualPosition*(root.availableWidth-width) : (root.width-width)/2
        y: root.horizontal ? (root.height-height)/2 : root.visualPosition*(root.availableHeight-height)
        width: 16; height: 16; radius: 8; color: Theme.colors.card
        border.width: Theme.line.HAIR
        border.color: handleHover.hovered && root.enabled ? Theme.colors.text2 : Theme.colors.field_line
        HoverHandler { id: handleHover }
    }
}
