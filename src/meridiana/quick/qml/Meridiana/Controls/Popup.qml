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
T.Popup {
    id: root
    property bool above: false
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
        const roomBelow = overlay.height - margins - (at.y + parent.height + gap)
        const roomAbove = at.y - gap - margins
        const wanted = implicitHeight
        let up = above
        if (!up && wanted > roomBelow && roomAbove > roomBelow) up = true
        else if (up && wanted > roomAbove && roomBelow > roomAbove) up = false
        y = up ? -height - gap : parent.height + gap
        let left = 0
        const excess = at.x + width + margins - overlay.width
        if (excess > 0) left -= excess
        if (at.x + left < margins) left = margins - at.x
        x = left
    }
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
    }
    T.Overlay.modal: Rectangle { color: Theme.colors.press }
}
