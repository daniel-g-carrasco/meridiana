import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.ScrollBar {
    id: root
    // R655: a bar standing in a card's margin (M.PanelPage's, the Project tree's, the Checks'): as wide as the margin.
    // Every bar as GNOME's overlay scroll bar (libadwaita 1.8, Daniel 20/11/2026): at rest a thin thumb
    // (ControlMetrics.marginThumb); under the pointer or dragged a wider one (marginThumbHover) on its lane, the whole
    // way it can run, in a faint ground; the pointer away, thin again and no lane. A short change, none with less
    // motion; centred in its room
    property bool inMargin: false
    readonly property bool wide: hovered || pressed
    readonly property real thumbWidth: wide ? ControlMetrics.marginThumbHover : ControlMetrics.marginThumb
    property real _thumb: thumbWidth
    Behavior on _thumb { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.FAST; easing.type: Theme.motion.EASE } }
    implicitWidth: orientation === Qt.Vertical ? (inMargin ? ControlMetrics.cardMargin : Theme.size.SCROLLBAR) : Theme.size.CONTROL
    implicitHeight: orientation === Qt.Horizontal ? Theme.size.SCROLLBAR : Theme.size.CONTROL
    padding: Theme.space.XXS
    readonly property real _across: orientation === Qt.Vertical ? width : height
    topPadding: orientation === Qt.Vertical ? Theme.radius.CARD : Math.round((height - _thumb) / 2 * _ratio) / _ratio
    bottomPadding: orientation === Qt.Vertical ? topPadding : height - topPadding - _thumb
    // In a card's margin the card's own line takes the last Theme.line.HAIR of it: the thumb is centred in the air
    // between the content and that line, on the device's pixels (Daniel 17/11/2026: «la barra di scorrimento non è
    // perfettamente centrata nel suo spazio»: 5 pixels of air on the content's side, 3 on the border's, at scale 2)
    readonly property real _ratio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    leftPadding: orientation === Qt.Horizontal ? Theme.radius.CARD
        : Math.round((width - (inMargin ? Theme.line.HAIR : 0) - _thumb) / 2 * _ratio) / _ratio
    rightPadding: orientation === Qt.Horizontal ? Theme.radius.CARD : width - leftPadding - _thumb
    minimumSize: Math.min(1, Theme.size.CONTROL / Math.max(1, orientation === Qt.Vertical ? availableHeight : availableWidth))
    visible: size < 1
    // R520: what the content leaves at its right for the bar's lane while the bar is shown: a list, a table, a page
    // that scrolls ends its rows, its columns and its texts that far from its right side (ControlMetrics.scrollLane and
    // scrollGap), and the bar never covers them
    readonly property real room: visible && orientation === Qt.Vertical ? ControlMetrics.scrollLane + ControlMetrics.scrollGap : 0
    hoverEnabled: true
    policy: T.ScrollBar.AsNeeded
    // the soft ends of every area that scrolls (EdgeFades, R624): the bar brings them. False where the list has its own
    // (List, Tree, Table, ScrollPage, Dialog) or is a popup's.
    property bool fades: true
    // the list it scrolls (`flickable`: its parent, or the list it was given when moved out of it, R637)
    readonly property Item fadesOf: fades && orientation === Qt.Vertical ? flickable : null
    property Item _fades: null
    function _attach() {
        if (_fades) { _fades.destroy(); _fades = null }
        if (fadesOf) _fades = fadeMaker.createObject(fadesOf, {flickable: fadesOf, barRoom: parent === fadesOf ? Theme.size.SCROLLBAR : 0})
    }
    onFadesOfChanged: if (_made) _attach()
    // R530: the list the bar scrolls (its parent, unless the bar was moved out of it: then the list says it), with the
    // rebound at its ends (Rebound.qml)
    property Item flickable: orientation === Qt.Vertical && parent ? (parent.contentY !== undefined ? parent
        : parent.contentItem && parent.contentItem.contentY !== undefined ? parent.contentItem : null) : null
    property QtObject _rebound: null
    // R638: how far the rebound moves the content at this moment (Rebound.qml's shift, a transform the list's contentY
    // does not tell): what is drawn over the content follows it (HeldHeads.qml)
    readonly property real reboundShift: _rebound && _rebound.shift ? _rebound.shift.y : 0
    function _bounce() {
        if (_rebound) { _rebound.destroy(); _rebound = null }
        if (flickable && flickable.contentItem && flickable.boundsMovement !== undefined)
            _rebound = reboundMaker.createObject(flickable, {flickable: flickable})
    }
    onFlickableChanged: if (_made) _bounce()
    Component { id: reboundMaker; Rebound { } }
    // R638: made once the bar is complete. A change of the list's binding while the bar was being made called these
    // before the properties above had their first values: `_rebound` and `_fades` were then set back to null and the
    // first Rebound and EdgeFades stayed, unknown to the bar, beside the second (two rebounds moved a panel's page
    // twice as far as the bar said, and the held heads followed only one)
    property bool _made: false
    Component.onCompleted: { _made = true; _attach(); _bounce() }
    Component { id: fadeMaker; EdgeFades { } }
    // R654 (Daniel 15/11/2026: «quando ho il puntatore sopra la barra di scorrimento e questa va in hover, non posso
    // muoverla facendo scrolling con due dita»): the wheel and the touchpad over the bar, its lane too, scroll the list
    // it belongs to, as over the list: a touchpad's pixels at once, a wheel's notch by ControlMetrics.wheelNotch in a
    // short glide (Qt's Flickable over its content: the bar took the event and did nothing with it, the list beside or
    // under it never had it). At an end the list's rebound answers, once (Rebound.kick).
    WheelHandler {
        enabled: root.flickable !== null && root.orientation === Qt.Vertical
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: event => root._wheel(event)
    }
    NumberAnimation { id: glide; target: root.flickable; property: "contentY"; duration: Theme.reducedMotion ? 0 : Theme.motion.FAST
        easing.type: Theme.motion.EASE }
    function _wheel(event) {
        const view = flickable
        if (!view || view.contentHeight <= view.height) return
        const top = view.originY, end = view.originY + view.contentHeight - view.height
        const pixels = event.pixelDelta.y !== 0
        const delta = pixels ? -event.pixelDelta.y : -event.angleDelta.y / 120 * ControlMetrics.wheelNotch
        const from = glide.running ? glide.to : view.contentY
        if ((delta < 0 && from <= top) || (delta > 0 && from >= end)) {
            if (_rebound) _rebound.kick(delta < 0 ? 1 : -1)
            return
        }
        const to = Math.max(top, Math.min(end, from + delta))
        if (pixels) { glide.stop(); view.contentY = to; return }
        glide.stop()
        glide.from = view.contentY
        glide.to = to
        glide.start()
    }
    // libadwaita 1.8 (_scrolling.scss, overlay-indicator): the thumb in the text's colour at 20 %, 40 % under the
    // pointer, 60 % dragged; the lane at 10 % while the bar is under the pointer; a line of the ground around the thumb
    // (white in the light theme, black at half in the dark), 35 % at rest and 60 % while wide, that keeps it apart
    // from the content under it
    function _ink(alpha) { return Qt.alpha(Theme.colors.text, alpha) }
    // What the bar looks like now: a view drawn by the software compositor (RasterSurface) redraws when it changes
    readonly property string appearance: [_thumb, thumbFill.color, lane.opacity, visible].join("|")
    readonly property color _outline: Theme.dark ? Qt.rgba(0, 0, 0.024, 0.5) : Qt.rgba(1, 1, 1, 1)
    background: Item {
        Rectangle {
            id: lane
            objectName: "scrollLane"
            x: root.leftPadding; y: root.topPadding
            width: root.orientation === Qt.Vertical ? root._thumb : root.availableWidth
            height: root.orientation === Qt.Vertical ? root.availableHeight : root._thumb
            radius: root._thumb / 2
            color: root._ink(0.1)
            opacity: root.wide ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.FAST; easing.type: Theme.motion.EASE } }
        }
    }
    contentItem: Rectangle {
        id: thumbFill
        implicitWidth: ControlMetrics.marginThumb; implicitHeight: ControlMetrics.marginThumb
        radius: root._thumb/2
        color: root.pressed ? root._ink(0.6) : thumbHover.hovered ? root._ink(0.4) : root._ink(0.2)
        HoverHandler { id: thumbHover }
        Rectangle { z: -1; anchors.fill: parent; anchors.margins: -Theme.line.HAIR; radius: width / 2
            color: "transparent"; border.width: Theme.line.HAIR
            border.color: Qt.alpha(root._outline, root._outline.a * (root.wide ? 0.6 : 0.35)) }
    }
}
