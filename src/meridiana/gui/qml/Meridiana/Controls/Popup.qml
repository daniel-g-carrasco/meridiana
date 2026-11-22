import QtQuick
import QtQuick.Effects
import QtQuick.Templates as T
import Meridiana.Theme

// R21-F2 (R375: Daniel 07/11/2026, «si apre un menu a comparsa che compare stranamente lontano dal pulsante Oggetto
// 3D»): the one panel that comes up over the window and is not a menu of entries (M.Menu) nor a window with its bar
// of buttons (M.Dialog): a list with a search, a calendar, a picker of models, a page in a modal frame. It opens
// attached to its parent, the button or the field that owns it: under it (`above` over it), flush with its left side,
// never off the window (it slides in, or flips to the other side when there is no room); `centered`, it stands in
// the middle of the window (a modal frame). The frame, the shadow and the opening are the menus' (Menu.qml, Reveal);
// `framed: false` draws nothing of its own (a field written over a view). M.Button's `menu` takes it as it takes a
// menu (R480: `opener`, `closedAt`).
// R597 (study 47): `side` says where it opens, "below" (the default), "above", "left" or "right" of its parent, and it
// flips to the other side when there is no room; `align` lays it along that side, "start", "center" or "end";
// `pointer` draws the frame's pointer on that side, turned to the middle of the parent (the help bubble's).
T.Popup {
    id: root
    property bool above: false
    property string side: above ? "above" : "below"
    property string align: "start"
    property bool pointer: false
    // beside ("left", "right"): the item whose edge it stands against, when it is not the parent (the help bubble
    // beside its panel); along the side and the pointer still follow the parent
    property Item sideOf: null
    // where it ended up, after place(): the side (flipped or not) and the pointer's middle along it
    property string placedSide: side
    property real pointerAt: 0
    property bool centered: false
    property bool framed: true
    property color ground: Theme.colors.card
    property Item opener: null
    property real closedAt: 0
    // the gap between the popup and what it hangs from
    property real gap: Theme.space.XXS
    padding: ControlMetrics.menuPad
    margins: Theme.space.M
    popupType: T.Popup.Item
    // R628: over the windows and over Meridio, in Qt's overlay (design.Stack)
    z: Theme.stack.POPUP
    closePolicy: T.Popup.CloseOnEscape | T.Popup.CloseOnPressOutsideParent
    implicitWidth: contentItem ? contentItem.implicitWidth + leftPadding + rightPadding : 0
    implicitHeight: contentItem ? contentItem.implicitHeight + topPadding + bottomPadding : 0
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    x: centered && parent ? Math.round((parent.width - width) / 2) : 0
    y: centered && parent ? Math.round((parent.height - height) / 2) : above ? -height - gap : (parent ? parent.height : 0) + gap
    readonly property real shown: revealer.shown
    Reveal { id: revealer; item: root.contentItem }
    opacity: revealer.shown
    function place() {
        // Placed whole before it shows, or Qt moves it after the first frame (Menu.qml does the same).
        const overlay = T.Overlay.overlay
        if (centered || !parent || !overlay) return
        const at = parent.mapToItem(overlay, 0, 0)
        const away = gap + (pointer ? ControlMetrics.pointer * Math.SQRT1_2 : 0)
        const across = side === "left" || side === "right"
        let s = side
        if (!across) {
            const roomBelow = overlay.height - margins - (at.y + parent.height + away)
            const roomAbove = at.y - away - margins
            if (s === "below" && implicitHeight > roomBelow && roomAbove > roomBelow) s = "above"
            else if (s === "above" && implicitHeight > roomAbove && roomBelow > roomAbove) s = "below"
        } else {
            const edge = (sideOf || parent).mapToItem(overlay, 0, 0)
            const roomRight = overlay.width - margins - (edge.x + (sideOf || parent).width + away)
            const roomLeft = edge.x - away - margins
            if (s === "right" && implicitWidth > roomRight && roomLeft > roomRight) s = "left"
            else if (s === "left" && implicitWidth > roomLeft && roomRight > roomLeft) s = "right"
        }
        // on the whole pixel of the window, wherever the parent stands
        const snap = (offset, origin) => Math.round(origin + offset) - origin
        const end = Theme.radius.CARD + ControlMetrics.pointer * Math.SQRT1_2
        // with a pointer, "start" and "end" leave room for it past the parent's middle (past the rounded corner)
        const lead = (length, own) => align === "center" ? (length - own) / 2
            : pointer ? (align === "end" ? length / 2 + end - own : length / 2 - end)
            : align === "end" ? length - own : 0
        // inside the window: slid along the side, never past its margins
        const keep = (offset, origin, own, room) => {
            let value = offset
            const excess = origin + value + own + margins - room
            if (excess > 0) value -= excess
            if (origin + value < margins) value = margins - origin
            return snap(value, origin)
        }
        if (!across) {
            y = snap(s === "above" ? -height - away : parent.height + away, at.y)
            x = keep(lead(parent.width, width), at.x, width, overlay.width)
            pointerAt = Math.max(end, Math.min(width - end, parent.width / 2 - x))
        } else {
            const edge = (sideOf || parent).mapToItem(parent, 0, 0)
            x = snap(s === "left" ? edge.x - width - away : edge.x + (sideOf || parent).width + away, at.x)
            y = keep(lead(parent.height, height), at.y, height, overlay.height)
            pointerAt = Math.max(end, Math.min(height - end, parent.height / 2 - y))
        }
        placedSide = s
    }
    // R659: a panel of an item out of reach (a view under a page of results, ToolTip.qml) closes and does not open
    readonly property bool reachable: !parent || parent.enabled
    onReachableChanged: if (!reachable) close()
    onVisibleChanged: if (visible && !reachable) close()
    onAboutToShow: { revealer.start(); place() }
    onClosed: { revealer.stop(); closedAt = Date.now() }
    // the content slides with the frame (Menu.qml puts the same Translate on its list)
    property Translate slide: Translate { y: revealer.slide }
    function slideContent() { if (contentItem && contentItem.transform.indexOf(slide) < 0) contentItem.transform = [slide].concat(contentItem.transform) }
    onContentItemChanged: slideContent()
    Component.onCompleted: slideContent()
    background: Rectangle { visible: root.framed; color: root.ground; radius: Theme.radius.CARD
        border.width: Theme.line.HAIR; border.color: Theme.colors.line
        transform: Translate { y: revealer.slide }
        RectangularShadow { anchors.fill: parent; z: -1; radius: parent.radius; blur: 16; spread: 0; offset: Qt.vector2d(0, 3); color: Theme.colors.popup_shadow }
        // R570: Qt's popup stops the hover, the clicks and the wheel, not the handlers behind it (a drag, a pinch)
        PointerShield { radius: Theme.radius.CARD }
        // R597: the pointer, a square turned by 45 degrees with its half out of the frame on the side it opened on;
        // a second square of the ground, a little inside, hides the frame's line across its base
        Repeater {
            model: root.pointer ? 2 : 0
            Rectangle {
                required property int index
                readonly property real inward: index === 0 ? 0 : Theme.line.HAIR * Math.SQRT2
                objectName: index === 0 ? "popupPointer" : ""
                width: ControlMetrics.pointer; height: width; rotation: 45; color: root.ground
                border.width: index === 0 ? Theme.line.HAIR : 0; border.color: Theme.colors.line
                x: root.placedSide === "right" ? -width / 2 + inward : root.placedSide === "left" ? parent.width - width / 2 - inward
                   : root.pointerAt - width / 2
                y: root.placedSide === "below" ? -height / 2 + inward : root.placedSide === "above" ? parent.height - height / 2 - inward
                   : root.pointerAt - height / 2
            }
        }
    }
    T.Overlay.modal: ModalVeil { }
}
