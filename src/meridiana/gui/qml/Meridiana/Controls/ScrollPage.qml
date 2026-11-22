import QtQuick
import QtQuick.Controls as C
import Meridiana.Theme

// A page that scrolls in a card, as ui/style.FitArea with QScrollArea: the air of the soft ends above and under it
// (ui/fades.py), the bar's room always kept at the right (R100), the bar outside the page and outside the fades.
// `implicitHeight` is what the page asks: a section is as tall as that, and scrolls only with less room (R337).
// R21 F1: the one area that scrolls a page, in place of the ScrollView and Flickable of every page. It answers as a
// ScrollView does (contentItem, availableWidth, availableHeight, contentHeight), so a page's own logic and its tests
// keep reading the same names.
Item {
    id: root
    default property alias content: page.data
    property real leftMargin: Theme.space.M
    property real rightMargin: 0
    property real air: Theme.space.S
    // R489 (Daniel 07/11/2026, Meridio's conversation): the air inside what scrolls, so the text fades out right up to
    // the border instead of vanishing `air` px before it. R590: so in every page (the panels' sections cut their text
    // 6 px under their heading)
    property bool airInside: true
    property alias spacing: page.spacing
    property alias contentY: view.contentY
    property alias flickable: view
    property alias bar: bar
    // R624: the soft ends are the content's own transparency (EdgeFades), they need no colour. `ground` is still set
    // by Assistant/Conversation.qml and read by nothing: to go with that file's next change.
    property color ground
    readonly property real pageWidth: page.width
    // the names of a ScrollView (contentItem an Item, as a ScrollView's: the Python side reads it as a QQuickItem)
    readonly property Item contentItem: view
    readonly property real availableWidth: page.width
    readonly property real availableHeight: view.height
    readonly property real contentHeight: view.contentHeight
    implicitHeight: page.implicitHeight + (airInside ? 0 : 2 * air)
    // R633: the heads of the page's sections held at its edges while it scrolls (HeldHeads.qml): M.PanelPage. The
    // sections find the page by `keepsHeads` (Section.headKeeper) and come and go by themselves.
    property bool keepHeads: false
    // R637: the bar in the margin of the card at the page's right (M.ScrollBar.inMargin), and the page as
    // wide as it is (M.PanelPage); otherwise its lane is kept inside the page (R100)
    property bool barInMargin: false
    readonly property bool keepsHeads: keepHeads
    function keepHead(section) { heads.keep(section) }
    function dropHead(section) { heads.drop(section) }
    function headActivated(section) { heads.headActivated(section) }
    function bodyShown(section) { return heads.bodyShown(section) }
    // R21-F2: a field of many lines (M.TextArea) written in the page: the page keeps its cursor in view
    property Item follow: null
    Connections { target: root.follow; function onCursorRectangleChanged() {
        if (!root.follow) return
        const r = root.follow.cursorRectangle, top = root.follow.mapToItem(page, 0, r.y).y
        if (top < view.contentY) view.contentY = Math.max(0, top)
        else if (top + r.height > view.contentY + view.height) view.contentY = Math.min(view.contentHeight - view.height, top + r.height - view.height)
    } }
    Flickable {
        id: view
        y: root.airInside ? 0 : root.air
        width: Math.max(0, root.width - (root.barInMargin ? 0 : Theme.size.SCROLLBAR))
        height: Math.max(0, root.height - (root.airInside ? 0 : 2 * root.air))
        contentWidth: width
        contentHeight: page.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        C.ScrollBar.vertical: ScrollBar { id: bar; fades: false; parent: root; flickable: view
            inMargin: root.barInMargin; x: view.width; height: root.height }
        Column {
            id: page
            x: root.leftMargin
            width: Math.max(0, view.width - root.leftMargin - root.rightMargin)
            spacing: Theme.space.S
            topPadding: root.airInside ? root.air : 0
            bottomPadding: topPadding
        }
    }
    HeldHeads { id: heads; flickable: view; keeping: root.keepHeads; air: root.airInside ? root.air : 0; gap: root.spacing
        overshoot: bar.reboundShift }
    EdgeFades { flickable: view; held: heads }
}
