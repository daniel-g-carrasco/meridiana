import QtQuick

MouseArea {
    required property var assistant
    property bool toggleOnClick: false
    property point pressPoint
    property point start
    property bool moved: false
    cursorShape: pressed ? Qt.ClosedHandCursor : toggleOnClick ? Qt.PointingHandCursor : Qt.SizeAllCursor
    onPressed: mouse => {
        assistant.relocating = false
        pressPoint = mapToItem(assistant, mouse.x, mouse.y)
        start = Qt.point(assistant.avatarX, assistant.avatarY)
        moved = false
    }
    onPositionChanged: mouse => {
        if (!pressed) return
        const p = mapToItem(assistant, mouse.x, mouse.y)
        const dx = p.x-pressPoint.x, dy = p.y-pressPoint.y
        if (Math.abs(dx)+Math.abs(dy) >= Qt.styleHints.startDragDistance) moved = true
        if (!moved) return
        assistant.dragging = true
        assistant.avatarX = assistant.clamp(start.x+dx, 0, assistant.width-46)
        assistant.avatarY = assistant.clamp(start.y+dy, assistant.topInset, assistant.bottomEdge-46)
    }
    onReleased: {
        assistant.dragging = false
        if (moved) assistant.placementSaved(assistant.avatarX, assistant.avatarY, assistant.bubbleWidth, assistant.bubbleHeight, assistant.docked)
        else if (toggleOnClick) assistant.opened ? assistant.dismiss() : assistant.open()
    }
    onCanceled: assistant.dragging = false
}
