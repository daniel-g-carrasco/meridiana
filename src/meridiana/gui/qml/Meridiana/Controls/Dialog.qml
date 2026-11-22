import QtQuick
import QtQuick.Controls as C
import QtQuick.Templates as T
import Meridiana.Theme
T.Dialog {
    id: root
    property string acceptText: ""
    property string rejectText: ""
    property bool acceptOnReturn: true
    readonly property bool hasButtons: rejectText !== "" || acceptText !== "" || actions.length > 0
    function contentHasFocus(item) {
        if (item.activeFocus) return true
        for (let child of item.children) if (contentHasFocus(child)) return true
        return false
    }
    onOpened: if (!contentHasFocus(contentItem) && acceptButton.visible) acceptButton.forceActiveFocus(Qt.TabFocusReason)
    // R628 (Daniel 15/11/2026: «non mi piace il fatto che non sia utilizzabile meridio»): what stands over the window in
    // Qt's overlay (Meridio's bubble, Theme.stack.ASSISTANT) can hold the keyboard while the window is open. Then its
    // keys are its own: Return does not press the window's button and Esc does not close the window (Qt takes both as
    // the window's shortcuts before the field hears them).
    // The child of the overlay that holds the keyboard, when it is Meridio's stage over this window (the steps from
    // Theme.stack.ASSISTANT to POPUP; a menu or a drop-down over the window keeps the keyboard as Qt gives it)
    readonly property Item keyboardOver: {
        const top = T.Overlay.overlay
        let item = bodyRoom.focused
        if (!item || !top) return null
        while (item.parent && item.parent !== top) item = item.parent
        return item.parent === top && item !== bodyRoom.parent && item.z > root.z
            && item.z >= Theme.stack.ASSISTANT && item.z < Theme.stack.POPUP ? item : null
    }
    // a control of his has the keyboard. When what had it is hidden (his bubble closed with Esc) Qt leaves the focus to
    // the scope round it, an item of no size of the stage (its popup, its Loader): nobody's, and the window takes it back
    readonly property bool keyboardAway: keyboardOver !== null && bodyRoom.focused.width > 0 && bodyRoom.focused.height > 0
    onKeyboardOverChanged: if (opened && keyboardOver !== null && !keyboardAway) Qt.callLater(takeKeyboardBack)
    onKeyboardAwayChanged: if (opened && keyboardOver !== null && !keyboardAway) Qt.callLater(takeKeyboardBack)
    function takeKeyboardBack() { if (opened && keyboardOver !== null && !keyboardAway) root.forceActiveFocus(Qt.OtherFocusReason) }
    closePolicy: keyboardAway ? T.Popup.NoAutoClose : T.Popup.CloseOnEscape
    Shortcut { sequences: ["Return", "Enter"]; enabled: root.opened && root.enabled && root.acceptOnReturn && acceptButton.visible && root.acceptEnabled && !root.keyboardAway
        onActivated: rejectButton.activeFocus ? root.reject() : root.tryAccept() }
    property bool acceptEnabled: true
    // R518: the window's other actions (copy the table, new product, remove the storage) stand on the same row of
    // buttons, at its left, in this order: [{text, enabled}]; the window stays open. One row of buttons per window.
    property var actions: []
    signal actionTriggered(int index)
    // a window that closes only when what it was given is good: false keeps it open (the value of a field)
    property var acceptCheck: null
    function tryAccept() { if (!acceptCheck || acceptCheck()) accept() }
    // R403, R518: one window for the whole program, with the metrics of ControlMetrics and no margins of its own in the
    // windows that use it: the same margin on the four sides (dialogPad), the title on the top one, the buttons on the
    // bottom and right ones, dialogGap between the title and the content and between the content and the buttons. A
    // content that draws a frame of its own (a Card) is told to leave it (bare): the window's frame is the only one
    // (R458 voce 10, «come mai la finestra ha doppi bordi?»), its margins the only ones.
    //
    // R586 (Daniel 11/11/2026, «i contenuti della finestra sbordano dalla sua finestra... correggere per tutte le
    // finestre»; «non si possono spostare trascinandole con il cursore»): the window places and sizes itself, and its
    // users say only what they would like. `implicitWidth` and `implicitHeight` are what it asks (a width of
    // ControlMetrics.dialogWidth, a height of its own or its content's); `width` and `height` are what it gets, never
    // more than the main window leaves at dialogEdge from its sides. Its content is what is declared inside it (one item,
    // given the window's width and at least its room's height): when it is taller than the room it scrolls in the body,
    // with the common fades, while the title and the buttons stay. It stands in the middle of its parent (the main
    // window, unless a view is given), moves with its title dragged, and comes back to the middle at every opening.
    //
    // R628 (Daniel 15/11/2026, the catalogue: «non posso ridimensionarlo, e inoltre me lo fa spostare solo all'interno di
    // un ristrettissimo range di movimento»; «mantiene dei margini abbastanza larghi da sopra e sotto»): dragged, it goes
    // anywhere over the main window and may pass its sides, keeping ControlMetrics.dialogHold of its head inside on every
    // side and its head never above the top (Qt's own margins kept it whole and dialogEdge inside); when the main window
    // gets smaller it comes back where it can be taken. Its sides and corners resize it (dialogGrip deep inside its
    // frame), from its least (its head, its foot, dialogLeast.body of its body, its row of buttons) to the whole main
    // window; the size chosen is kept for its kind (sizeKey, DialogSizes) and a double click on a grip forgets it.
    default property alias content: holder.data
    // the item the window was given (its first)
    // false for a content that scrolls by itself and fills what it is given (a catalogue, a list, a page in an
    // M.ScrollPage): it gets the room's height exactly, and the body does not scroll it as well
    property bool bodyScrolls: true
    readonly property Item body: holder.children.length > 0 ? holder.children[0] : null
    implicitWidth: ControlMetrics.dialogWidth.normal
    // the height of the title, the content and the buttons: a window that asks a height of its own in some cases only
    // gives this in the others
    readonly property real fitHeight: (root.title !== "" ? implicitHeaderHeight : 0) + implicitContentHeight + (root.hasButtons ? implicitFooterHeight : 0) + topPadding + bottomPadding
    implicitHeight: fitHeight
    readonly property Item room: T.Overlay.overlay
    readonly property real roomWidth: room ? room.width : implicitWidth
    readonly property real roomHeight: room ? room.height : implicitHeight
    // R628: the size given by hand (0: none, the window takes what it asks), and the key it is kept under
    property size chosen: Qt.size(0, 0)
    property string sizeKey: objectName
    property bool resizable: true
    property bool resizing: false
    // the least a window is made by hand: its row of buttons and dialogLeast.width (or what it asks, when less); its
    // head, its foot and dialogLeast.body of its body (or all of it, when less)
    readonly property real footWidth: others.implicitWidth + actions.implicitWidth + 2 * ControlMetrics.dialogPad
        + (others.implicitWidth > 0 && actions.implicitWidth > 0 ? ControlMetrics.dialogButtonGap : 0)
    readonly property real leastWidth: Math.min(roomWidth, Math.max(footWidth, Math.min(ControlMetrics.dialogLeast.width, implicitWidth)))
    readonly property real leastHeight: Math.min(roomHeight, (root.title !== "" ? implicitHeaderHeight : 0) + (root.hasButtons ? implicitFooterHeight : 0)
        + topPadding + bottomPadding + Math.min(ControlMetrics.dialogLeast.body, implicitContentHeight))
    width: chosen.width > 0 ? Math.max(leastWidth, Math.min(chosen.width, roomWidth))
                            : Math.max(0, Math.min(implicitWidth, roomWidth - 2 * ControlMetrics.dialogEdge))
    height: chosen.height > 0 ? Math.max(leastHeight, Math.min(chosen.height, roomHeight))
                              : Math.max(0, Math.min(implicitHeight, roomHeight - 2 * ControlMetrics.dialogEdge))
    parent: T.Overlay.overlay
    // where it opens (the middle of its parent, or a place of its own: the stringing beside the panel); once dragged or
    // resized, where the hand left it (`spot`, its top left corner in its parent); kept where it can be taken
    property real homeX: parent ? Math.round((parent.width - width) / 2) : 0
    property real homeY: parent ? Math.round((parent.height - height) / 2) : 0
    property bool placed: false
    property point spot: Qt.point(0, 0)
    readonly property point kept: reachable(placed ? spot.x : homeX, placed ? spot.y : homeY, width, height)
    // Qt sets back at the main window's left side a popup that asks a width (its reposition, whatever its margins; Qt
    // 6.12, measured: an M.Dialog given x -120 stood at 0, the right side and the bottom are let go). Past that side the
    // popup stands at it and its own item is moved by the rest, a translation of its drawing and of where it takes the
    // pointer (`kept` is where the window is seen)
    readonly property real pastLeft: Math.min(0, roomCorner().x + kept.x)
    x: kept.x - pastLeft
    y: kept.y
    property Translate pastShift: Translate { x: root.pastLeft }
    Component.onCompleted: bodyRoom.parent.transform = [pastShift]
    onAboutToShow: { placed = false; chosen = DialogSizes.of(sizeKey) }
    onSizeKeyChanged: if (visible) chosen = DialogSizes.of(sizeKey)
    // the parent's corner in the room (the overlay over the whole main window)
    function roomCorner() { return parent && room ? parent.mapToItem(room, 0, 0) : Qt.point(0, 0) }
    // the top left corner (in the parent) nearest to (px, py) where dialogHold of the head stays inside the room on
    // every side and the head is not above its top
    function reachable(px, py, w, h) {
        if (!parent || !room) return Qt.point(px, py)
        const at = roomCorner(), hold = Math.min(ControlMetrics.dialogHold, w), tall = Math.min(ControlMetrics.dialogHold, h)
        const rx = Math.max(hold - w, Math.min(room.width - hold, at.x + px))
        const ry = Math.max(0, Math.min(room.height - tall, at.y + py))
        return Qt.point(rx - at.x, ry - at.y)
    }
    // carried by the head: from where it stood at the press
    function carry(from, dx, dy) { spot = Qt.point(from.x + dx, from.y + dy); placed = true }
    // resized by a grip: `sx`, `sy` the sides it moves (-1 the left or the top, 1 the right or the bottom, 0 neither),
    // from the rectangle it had at the press; the sides go no further than the room's (or where they already were)
    function resizeBy(sx, sy, from, dx, dy) {
        const at = roomCorner()
        let left = from.x, top = from.y, right = from.x + from.width, bottom = from.y + from.height
        if (sx < 0) left = Math.max(Math.min(left, -at.x), Math.min(right - leastWidth, left + dx))
        if (sx > 0) right = Math.min(Math.max(right, roomWidth - at.x), Math.max(left + leastWidth, right + dx))
        if (sy < 0) top = Math.max(Math.min(top, -at.y), Math.min(bottom - leastHeight, top + dy))
        if (sy > 0) bottom = Math.min(Math.max(bottom, roomHeight - at.y), Math.max(top + leastHeight, bottom + dy))
        const w = Math.min(right - left, roomWidth), h = Math.min(bottom - top, roomHeight)
        chosen = Qt.size(w, h)
        // as wide (or as tall) as the room: on it, whatever side stood past its edge
        spot = Qt.point(w >= roomWidth ? -at.x : sx < 0 ? right - w : left, h >= roomHeight ? -at.y : sy < 0 ? bottom - h : top)
        placed = true
    }
    function keepSize() { DialogSizes.keep(sizeKey, width, height); spot = kept }
    // back to the size it asks, about the same middle
    function askedSize() {
        const middle = Qt.point(kept.x + width / 2, kept.y + height / 2)
        chosen = Qt.size(0, 0)
        DialogSizes.forget(sizeKey)
        spot = Qt.point(Math.round(middle.x - width / 2), Math.round(middle.y - height / 2))
        placed = true
    }
    readonly property bool contentFramed: false
    readonly property real frameWidth: Theme.line.HAIR
    function bareContent() { for (const child of holder.children) if (child.bare !== undefined) child.bare = true }
    leftPadding: ControlMetrics.dialogPad
    rightPadding: ControlMetrics.dialogPad
    topPadding: root.title !== "" ? ControlMetrics.dialogGap : ControlMetrics.dialogPad
    bottomPadding: root.hasButtons ? ControlMetrics.dialogGap : ControlMetrics.dialogPad
    modal: true
    popupType: T.Popup.Item
    // R628: the windows' step in Qt's overlay, under Meridio and under the menus and tooltips (design.Stack)
    z: Theme.stack.WINDOW
    focus: true
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    // R607 (Daniel 14/11/2026, «lavoriamo sulla centralizzazione della finestra fatta bene e replicabile»): the head is
    // the title and, when the window names one thing (the file it reads), a subtitle of one line: cut at its end when it
    // is long, whole in its tooltip (`subtitleTip`, the file's whole path: the window shows names, never paths)
    property string subtitle: ""
    property string subtitleTip: ""
    header: Item { objectName: "dialogHead"; visible: root.title !== ""
        implicitWidth: head.implicitWidth + 2 * ControlMetrics.dialogPad
        implicitHeight: head.implicitHeight + ControlMetrics.dialogPad
        Column { id: head; x: ControlMetrics.dialogPad; y: ControlMetrics.dialogPad; width: parent.width - 2 * ControlMetrics.dialogPad
            spacing: Theme.space.XXS
            Label { objectName: "dialogTitle"; width: parent.width; text: root.title; textStyle: "heading"; elide: Text.ElideRight }
            Label { id: subtitleLine; objectName: "dialogSubtitle"; width: parent.width; text: root.subtitle; visible: text !== ""
                textStyle: "secondary"; elide: Text.ElideRight; wrapMode: Text.NoWrap; maximumLineCount: 1
                HoverHandler { id: subtitleHover }
                ToolTip { parent: subtitleLine; text: root.subtitleTip || subtitleLine.text
                    visible: subtitleHover.hovered && (subtitleLine.truncated || (root.subtitleTip !== "" && root.subtitleTip !== subtitleLine.text)) } } }
        // R586 (b): the head carries the window (the points in the window's own frame, which the head moves with); R607:
        // the pointer over it is the one of everything that moves, four arrows, as on the panels' titles (DockPanel)
        MouseArea { objectName: "dialogCarry"; anchors.fill: parent; acceptedButtons: Qt.LeftButton; cursorShape: Qt.SizeAllCursor
            property point from: Qt.point(0, 0)
            property point pressed: Qt.point(0, 0)
            onPressed: mouse => { from = root.kept; pressed = mapToItem(null, mouse.x, mouse.y) }
            onPositionChanged: mouse => {
                const at = mapToItem(null, mouse.x, mouse.y)
                root.carry(from, at.x - pressed.x, at.y - pressed.y) }
            // R628: where it was left, as it is seen (a drag past the limit does not leave it waiting out there)
            onReleased: root.spot = root.kept } }
    // the body: what the window was given, in a view that scrolls it when it is taller than the room
    contentItem: Item {
        id: bodyRoom
        objectName: "dialogBody"
        // R607 (Daniel 14/11/2026, «poi compaiono due "Annulla"»): one command stops the job a window shows. The
        // window's own «Cancel» (rejectText) stops it and closes the window (its users wire the rejection to the job's
        // cancel, as DialogWindow does through dialogs.cancel); an M.WorkRow in the body reads this and draws no Cancel
        readonly property bool stopsJobs: root.rejectText !== ""
        implicitWidth: holder.implicitWidth
        implicitHeight: holder.implicitHeight
        Flickable {
            id: view
            objectName: "dialogView"
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: holder.height
            interactive: contentHeight > height + .5
            boundsBehavior: Flickable.StopAtBounds
            C.ScrollBar.vertical: ScrollBar { fades: false; parent: bodyRoom; x: bodyRoom.width + (root.rightPadding - width) / 2; height: bodyRoom.height }
            Item {
                id: holder
                width: view.width
                height: root.bodyScrolls ? Math.max(view.height, implicitHeight) : view.height
                implicitWidth: { let w = 0; for (const child of children) w = Math.max(w, child.implicitWidth); return w }
                implicitHeight: { let h = 0; for (const child of children) if (child.visible) h = Math.max(h, child.implicitHeight); return h }
                // each item of the content takes the window's width and the body's height
                onChildrenChanged: {
                    for (const child of children) {
                        child.x = 0; child.y = 0
                        child.width = Qt.binding(() => holder.width)
                        child.height = Qt.binding(() => holder.height)
                    }
                    root.bareContent()
                }
            }
        }
        EdgeFades { flickable: view }
        // the field with the keyboard's focus is kept in view (a Tab to a field under the edge scrolls to it)
        readonly property Item focused: Window.activeFocusItem
        // R601 (Daniel 14/11/2026: «se mi trovo in basso, dopo un po' totalmente a caso mi riporta su da solo»): only a
        // move of the keyboard's (Tab, Shift+Tab, a shortcut) scrolls; the focus that comes back by itself (the window
        // active again after another program, a control made again under the focus) leaves the body where it is
        onFocusedChanged: {
            if (!focused || !view.interactive) return
            const reason = focused.focusReason
            if (reason !== Qt.TabFocusReason && reason !== Qt.BacktabFocusReason && reason !== Qt.ShortcutFocusReason) return
            for (let up = focused; up; up = up.parent) {
                if (up !== holder) continue
                const top = focused.mapToItem(holder, 0, 0).y, bottom = top + focused.height
                if (top < view.contentY) view.contentY = Math.max(0, top)
                else if (bottom > view.contentY + view.height) view.contentY = Math.min(view.contentHeight - view.height, bottom - view.height)
                return
            }
        }
    }
    // the foot: the other actions at the left, «Cancel» and the acceptance at the right, one row, as tall as its tallest
    // side (a window with only actions at the left keeps them inside its frame)
    footer: Item { visible: root.hasButtons; implicitHeight: Math.max(actions.implicitHeight, others.implicitHeight) + ControlMetrics.dialogPad
        Row { id: others; objectName: "dialogActions"; x: ControlMetrics.dialogPad; y: 0; spacing: ControlMetrics.dialogButtonGap
            Repeater { model: root.actions
                Button { required property var modelData; required property int index
                    text: modelData.text; enabled: modelData.enabled !== false; visible: modelData.visible !== false
                    onClicked: root.actionTriggered(index) } } }
        Row { id: actions; objectName: "dialogButtons"; anchors.right: parent.right; anchors.rightMargin: ControlMetrics.dialogPad; anchors.top: parent.top; spacing: ControlMetrics.dialogButtonGap
            layoutDirection: Qt.platform.os === "windows" ? Qt.RightToLeft : Qt.LeftToRight
            Button { id: rejectButton; objectName: "dialogReject"; text: root.rejectText; visible: text !== ""; onClicked: root.reject() }
            Button { id: acceptButton; objectName: "dialogAccept"; text: root.acceptText; visible: text !== ""; enabled: root.acceptEnabled; onClicked: root.tryAccept() }
        }
    }
    background: Rectangle { objectName: "dialogFrame"; color: Theme.colors.window; radius: Theme.radius.CARD
        border.color: Theme.colors.line; border.width: root.frameWidth }
    // R628: the grips, over the head, the body and the foot, on the frame's four sides and four corners, inside it (in
    // the margin, where there is no control), with nothing drawn: the pointer says what they do. Not in the content's
    // list (an item declared in the window is its body): held by a property, given to the window's own item.
    property Item grips: Item {
        id: grips
        objectName: "dialogGrips"
        parent: bodyRoom.parent
        anchors.fill: parent
        z: 1                        // over the head (its carrying area), the body and the foot, in the window's own item
        visible: root.resizable
        Repeater {
            // [side along x, side along y]: the four sides, then the four corners (over the sides at their ends)
            model: [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]
            MouseArea {
                required property var modelData
                readonly property int sx: modelData[0]
                readonly property int sy: modelData[1]
                readonly property real deep: ControlMetrics.dialogGrip
                readonly property real corner: 2 * ControlMetrics.dialogGrip
                objectName: "dialogGrip" + (sy < 0 ? "Top" : sy > 0 ? "Bottom" : "") + (sx < 0 ? "Left" : sx > 0 ? "Right" : "")
                x: sx < 0 ? 0 : sx > 0 ? grips.width - width : corner
                y: sy < 0 ? 0 : sy > 0 ? grips.height - height : corner
                width: sx === 0 ? grips.width - 2 * corner : sy === 0 ? deep : corner
                height: sy === 0 ? grips.height - 2 * corner : sx === 0 ? deep : corner
                acceptedButtons: Qt.LeftButton
                hoverEnabled: true
                preventStealing: true
                cursorShape: sx !== 0 && sy !== 0 ? (sx === sy ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor)
                                                  : sx !== 0 ? Qt.SizeHorCursor : Qt.SizeVerCursor
                property rect from: Qt.rect(0, 0, 0, 0)
                property point pressAt: Qt.point(0, 0)
                property bool moved: false
                onPressed: mouse => {
                    from = Qt.rect(root.kept.x, root.kept.y, root.width, root.height)
                    pressAt = mapToItem(null, mouse.x, mouse.y)
                    moved = false
                    root.resizing = true
                }
                onPositionChanged: mouse => {
                    if (!root.resizing) return
                    const at = mapToItem(null, mouse.x, mouse.y)
                    if (at.x === pressAt.x && at.y === pressAt.y) return
                    moved = true
                    root.resizeBy(sx, sy, from, at.x - pressAt.x, at.y - pressAt.y)
                }
                // kept only when it changed (a click, the first of a double click, keeps nothing)
                onReleased: { if (root.resizing && moved) root.keepSize(); root.resizing = false }
                onCanceled: root.resizing = false
                // the size the window asks, again (the double click's second press has started a resize of nothing)
                onDoubleClicked: { root.resizing = false; root.askedSize() }
            }
        }
    }
    T.Overlay.modal: ModalVeil { }
}
