import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.ToolTip {
    id: root
    readonly property var layout: Theme.tooltipLayout(text)
    // R379, R468, R550: the wait has one source, in ControlMetrics, the same for every tooltip
    delay: ControlMetrics.tipDelay
    timeout: -1
    padding: Theme.space.M
    topPadding: Theme.space.S
    bottomPadding: Theme.space.S
    margins: Theme.space.M
    implicitWidth: layout.width
    implicitHeight: layout.height
    // R550: `shownAt` is the pointer, in the parent's coordinates; where the tooltip goes beside it is
    // ControlMetrics.besidePointer's, inside the window
    property point shownAt: Qt.point(0, parent ? parent.height : 0)
    readonly property point spot: parent ? ControlMetrics.besidePointer(shownAt, implicitWidth, implicitHeight, ControlMetrics.roomOf(parent, false)) : shownAt
    x: spot.x
    y: spot.y
    HoverHandler { id: pointer; parent: root.parent }
    // where the pointer was last seen on the control, for a tooltip that opens when the hover has gone quiet
    property point lastAt: shownAt
    // (the handler goes first when the tooltip is taken apart)
    readonly property point pointerNow: pointer ? pointer.point.position : lastAt
    onPointerNowChanged: if (pointer && pointer.hovered) lastAt = pointerNow
    // A press hides the tip until the pointer leaves and comes back, as QToolTip does, at once (R476: fading out under
    // a menu that comes it left a dark slab for two frames at the press, frame by frame from a tool's arrow). close() does not touch the
    // caller's visible binding: it opens again when that binding next turns true.
    property bool pressed: parent && parent.pressed === true
    // Held after a press until the pointer has been off the control for a moment: at the press Qt sends the control a
    // hover off and on again, and the tooltip came back for three frames under the menu that opened (R476, when the
    // next tooltip still came at once).
    property bool held: false
    // what it shows goes at once (its own fade out, captured when it starts, would still be seen)
    onPressedChanged: if (pressed) { held = true; close() }
    onVisibleChanged: if (visible && held) close()
    Timer { id: away; interval: 150; onTriggered: if (!pointer.hovered) root.held = false }
    Connections { target: pointer; function onHoveredChanged() { if (!pointer.hovered) away.restart() } }
    // Who sets shownAt keeps it: a tooltip that follows a pointer of its own (R425: the plan's module under the
    // pointer); the others take the pointer where it is when they appear (R550)
    property bool placed: false
    onAboutToShow: if (!placed) shownAt = pointer.hovered ? pointer.point.position : lastAt
    contentItem: Label { opacity: root.held ? 0 : 1; text: root.layout.html; textFormat: Text.RichText; textStyle: "body"; color: Theme.colors.tooltip_fg; wrapMode: Text.WordWrap }
    background: Rectangle { opacity: root.held ? 0 : 1; color: Theme.colors.tooltip_bg; radius: Theme.radius.INNER
        border.width: Theme.line.HAIR; border.color: Theme.colors.line }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.reducedMotion ? 0 : ControlMetrics.tipEnter } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.reducedMotion ? 0 : ControlMetrics.tipExit } }
}
