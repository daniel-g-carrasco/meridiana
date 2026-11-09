import QtQuick
import QtQuick.Effects
import QtQuick.Templates as T
import Meridiana.Theme
T.Menu {
    id: root
    readonly property real measuredWidth: {
        const revision = Theme.revision
        let widest = Theme.size.CONTROL
        for (let i = 0; i < count; i++) { const entry = itemAt(i); if (entry) widest = Math.max(widest, entry.implicitWidth + 2 * padding) }
        return widest
    }
    // R491 (Daniel 06/11/2026: «il menu si sposta di piccoli movimenti» choosing another agent): an open menu keeps
    // its width; an entry that changes (bold, a check) only widens it if it no longer fits, never narrows it.
    property real heldWidth: 0
    implicitWidth: Math.max(measuredWidth, heldWidth)
    implicitHeight: contentItem.implicitHeight + 2 * padding
    padding: ControlMetrics.menuPad
    margins: Theme.space.M
    popupType: T.Popup.Item
    cascade: true
    overlap: Theme.space.XS
    // R480: the button that opened it (M.Button's `menu`), and when it last closed: a press on that button closes the
    // menu before the button hears it, so the button reads this to know its click is the second one.
    property Item opener: null
    property real closedAt: 0
    // R476: one opening for every menu, of a bar, a button or the right button: a fade with a slide of a few pixels,
    // ControlMetrics.menuReveal long with a soft end. Its size is whole from the first frame, which is drawn
    // transparent: what a menu costs the first time (its entries laid out, the shadow) is paid in that frame, which
    // is not seen. The unroll of before grew its height from 0, so the entries were laid out while it came, and
    // that frame, slow, came when the time of the roll was over: under load (the suite) the menu showed whole at
    // once (148 of 182 px). The reveal moves with the frames, at most 15 % in one: a slow frame slows it, it
    // does not skip it.
    // (R21-F2: the reveal is Reveal.qml, shared with Popup.qml)
    Reveal { id: revealer; item: root.contentItem }
    property alias reveal: revealer.reveal
    readonly property real shown: revealer.shown
    opacity: shown
    onAboutToShow: {
        revealer.start()
        heldWidth = 0
        // Placed for its whole height before it shows, or Qt pushes it up near the bottom.
        const overlay = T.Overlay.overlay
        if (!parent || !overlay || parent.subMenu !== undefined) return
        const excess = parent.mapToItem(overlay, x, y).y + implicitHeight + margins - overlay.height
        if (excess > 0) y -= excess
    }
    onOpened: heldWidth = measuredWidth
    onClosed: { revealer.stop(); heldWidth = 0; closedAt = Date.now() }
    delegate: MenuItem { }
    contentItem: ListView { implicitHeight: contentHeight; model: root.contentModel; currentIndex: root.currentIndex
        clip: true; interactive: contentHeight > height; keyNavigationEnabled: false
        transform: Translate { y: revealer.slide }
        T.ScrollBar.vertical: ScrollBar { fades: false; visible: size < 1 } }
    background: Rectangle { color: Theme.colors.card; radius: Theme.radius.CARD
        border.width: Theme.line.HAIR; border.color: Theme.colors.line
        transform: Translate { y: revealer.slide }
        RectangularShadow { anchors.fill: parent; z: -1; radius: parent.radius; blur: 16; spread: 0; offset: Qt.vector2d(0, 3); color: Theme.colors.popup_shadow }
    }
}
