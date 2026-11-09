import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    objectName: "assistantLayer"
    property var chat: null
    property var helpService: null
    property var texts: assistantText
    property bool assistantEnabled: true
    property bool docked: false
    property bool dockVisible: true
    property Item dockItem: null
    property bool opened: false
    property bool animated: true
    property string characterStyle: "smooth"
    property string page: "conversation"
    property string phaseKey: "model"
    property var places: ({})
    property rect homeRect: Qt.rect(0, 0, width, height)
    property real topInset: 0
    property real bottomInset: 0
    readonly property real bottomEdge: height-bottomInset
    property real avatarX: Math.max(12, width - 70)
    property real avatarY: Math.max(12, height - 70)
    property real bubbleWidth: 320
    property real bubbleHeight: 500
    property string tail: "right"
    property real tailOffset: bubbleHeight - 23
    property real bubbleX: 0
    property real bubbleY: 0
    property bool dragging: false
    property bool resizing: false
    property bool relocating: false
    property real flipProgress: 1
    property point flipFrom: Qt.point(0, 0)
    property bool whatsThis: false
    property bool useShortcuts: true
    readonly property bool motionEnabled: animated && !Theme.reducedMotion
    onMotionEnabledChanged: if (chat) chat.setMotion(motionEnabled)
    property var returnState: null
    property rect avoidRect: Qt.rect(0, 0, 0, 0)
    property Item highlightItem: null
    // R474 (Daniel 06/11/2026: «le evidenziature di Meridio non coincidono spesso con la scheda o il pulsante, e
    // rimangono bloccate»): the rect followed only the item's size, not where it went (a phase laid out after the
    // step, a list scrolled), and a step without an item kept the one of the step before. Read again at every frame
    // while it is shown, set only when it changed; a step without an item clears it (setTourTarget).
    property rect highlightRect: Qt.rect(0, 0, 0, 0)
    function trackHighlight() {
        // an item not shown (a panel closed) is not highlighted where it would be
        const r = !highlightItem ? avoidRect : !highlightItem.visible ? Qt.rect(0, 0, 0, 0)
            : highlightItem.mapToItem(root, 0, 0, highlightItem.width, highlightItem.height)
        if (r.x !== highlightRect.x || r.y !== highlightRect.y || r.width !== highlightRect.width || r.height !== highlightRect.height)
            highlightRect = r
    }
    onHighlightItemChanged: trackHighlight()
    onAvoidRectChanged: trackHighlight()
    Connections {
        target: root.highlightItem && root.opened ? root.Window.window : null
        function onFrameSwapped() { root.trackHighlight() }
    }
    property rect dockRect: Qt.rect(Math.max(0, width - 360), 0, Math.min(width, 360), height)
    readonly property real actualWidth: docked ? dockRect.width : Math.min(bubbleWidth, Math.max(200, width - 70))
    // R474: «il fumetto occupa più spazio di quello necessario, anche quando lo si richiama con l'help»: a page other than
    // the conversation (help, tour, manual, setup) is as tall as what it shows, up to the bubble's height
    readonly property real fittedHeight: page !== "conversation" && content.item && content.item.implicitHeight > 0
        ? Math.ceil(content.item.implicitHeight + 8 + 10 + 6 + Theme.size.CONTROL + 2 + (tail === "top" || tail === "bottom" ? 12 : 0))
        : bubbleHeight
    readonly property real actualHeight: docked ? dockRect.height : Math.min(bubbleHeight, fittedHeight, Math.max(0, bottomEdge-topInset))
    readonly property bool temporary: returnState !== null
    readonly property bool characterVisible: assistantEnabled || temporary
    signal placementSaved(real x, real y, real width, real height, bool docked)
    signal attachmentRequested()
    signal helpUnavailable(string id)
    signal panelRequested()

    function clamp(n, lo, hi) { return Math.max(lo, Math.min(n, Math.max(lo, hi))) }
    function repositionHome() {
        if (temporary || dragging || resizing || !root.Window.window || !root.Window.window.visible) return
        const anchor = places[phaseKey]
        relocating = true
        if (anchor) {
            avatarX = clamp(anchor[0] === "left" ? anchor[2] : width-46-anchor[2], 0, width-46)
            avatarY = clamp(anchor[1] === "top" ? anchor[3] : height-46-anchor[3], topInset, bottomEdge-46)
        } else {
            avatarX = clamp(homeRect.x+homeRect.width-58, 0, width-46)
            avatarY = clamp(homeRect.y+homeRect.height-58-(phaseKey === "model" ? 32 : 0), topInset, bottomEdge-46)
        }
        relocation.restart()
        placedOnce = root.Window.window && root.Window.window.visible && homeRect.width > 0
    }
    // R155, R500 (Daniel 06/11/2026: «tra una fase e l'altra Meridio non doveva continuare a spostarsi»): placed once at
    // his home (or where he was dragged, a place for every phase); then, when the phase or the layout changes, he
    // stays where he is and moves only as much as needed: into the area, and off the band the phase keeps at the
    // bottom of its view (the sun bar of the 3D view), sliding in 320 ms with his bubble.
    property bool placedOnce: false
    function bandRect() {
        const window = root.Window.window
        if (!window) return Qt.rect(0, 0, 0, 0)
        let stack = [window.contentItem]
        while (stack.length) {
            const node = stack.pop()
            if (node.objectName === "sunBar") return node.visible && node.height > 0
                ? node.mapToItem(root, 0, 0, node.width, node.height) : Qt.rect(0, 0, 0, 0)
            for (let i = 0; i < node.children.length; i++) stack.push(node.children[i])
        }
        return Qt.rect(0, 0, 0, 0)
    }
    function stay() {
        if (!placedOnce) { repositionHome(); return }
        if (temporary || dragging || resizing || !root.Window.window || !root.Window.window.visible) return
        const x = clamp(avatarX, 0, width - 46)
        let y = clamp(avatarY, topInset, bottomEdge - 46)
        const band = bandRect()
        if (band.width > 0 && intersects(Qt.rect(x, y, 46, 46), band)) y = clamp(band.y - 46 - 4, topInset, bottomEdge - 46)
        if (x === avatarX && y === avatarY) return
        relocating = true
        avatarX = x; avatarY = y
        relocation.restart()
    }
    Timer { id: stayLater; interval: 0; onTriggered: root.stay() }
    onHomeRectChanged: stayLater.restart()
    onPhaseKeyChanged: stayLater.restart()
    onPlacesChanged: if (!placedOnce) repositionHome()
    function intersects(a, b) {
        return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height
    }
    function shape(x, y, side) {
        const w = actualWidth, h = actualHeight, aw = 46, gap = 4
        const horizontal = side === "left" || side === "right"
        const sameAxis = horizontal === (tail === "left" || tail === "right")
        const desired = sameAxis ? tailOffset : (horizontal ? (y > height / 2 ? h - 23 : 23) : (x > width / 2 ? w - 23 : 23))
        const at = clamp(desired, 23, (horizontal ? h : w) - 23)
        if (side === "left") return Qt.rect(x + aw + gap, clamp(y + 23 - at, topInset, bottomEdge - h), w, h)
        if (side === "right") return Qt.rect(x - gap - w, clamp(y + 23 - at, topInset, bottomEdge - h), w, h)
        if (side === "top") return Qt.rect(clamp(x + 23 - at, 0, width - w), y + aw + gap, w, h)
        return Qt.rect(clamp(x + 23 - at, 0, width - w), y - gap - h, w, h)
    }
    function fits(r) { return r.x >= 0 && r.y >= topInset && r.x + r.width <= width && r.y + r.height <= bottomEdge }
    function placeBubble() {
        if (docked) return
        const opposite = {left: "right", right: "left", top: "bottom", bottom: "top"}
        const candidates = [tail, opposite[tail], "left", "right", "top", "bottom"]
        for (let side of candidates) {
            const r = shape(avatarX, avatarY, side)
            if (fits(r)) {
                if ((side === "left" || side === "right") !== (tail === "left" || tail === "right"))
                    tailOffset = side === "left" || side === "right" ? avatarY + 23 - r.y : avatarX + 23 - r.x
                if (side !== tail && dragging && motionEnabled) {
                    flipFrom = Qt.point(bubble.x, bubble.y)
                    flip.restart()
                }
                tail = side; bubbleX = r.x; bubbleY = r.y; return
            }
        }
        const fallback = shape(avatarX, avatarY, tail)
        bubbleX = clamp(fallback.x, 0, width - actualWidth)
        bubbleY = clamp(fallback.y, topInset, bottomEdge - actualHeight)
    }
    function resizedSpan(start, length, movingStart, delta, limit, minimum, keep, lower=0) {
        // assistant.resized: fixed opposite edge; the tail must still reach him.
        if (movingStart) {
            const end = start + length
            let edge = Math.min(Math.max(start + delta, lower), end - minimum)
            if (keep !== null) edge = Math.min(edge, Math.max(start, Math.floor(keep - 23)))
            return [edge, end - edge]
        }
        let edge = Math.max(Math.min(start + length + delta, limit), start + minimum)
        if (keep !== null) edge = Math.max(edge, Math.min(start + length, Math.floor(keep + 23.5)))
        return [start, edge - start]
    }
    function remember() {
        if (returnState === null) returnState = {x: avatarX, y: avatarY, opened: opened, page: page,
                                                tail: tail, offset: tailOffset, width: bubbleWidth, height: bubbleHeight}
    }
    function moveBeside(rect) {
        if (docked || rect.width <= 0) return
        avoidRect = rect
        // Compare complete character-and-bubble footprints, keeping the nearest free position.
        const points = [[rect.x - 62, rect.y], [rect.x + rect.width + 16, rect.y],
                        [12, topInset+12], [width - 58, topInset+12], [12, bottomEdge - 58], [width - 58, bottomEdge - 58]]
        let best = null, score = Infinity
        for (let p of points) {
            const x = clamp(p[0], 0, width - 46), y = clamp(p[1], topInset, bottomEdge - 46)
            if (intersects(Qt.rect(x, y, 46, 46), rect)) continue
            for (let side of [tail, "left", "right", "top", "bottom"]) {
                const r = shape(x, y, side)
                if (!fits(r) || intersects(r, rect)) continue
                const d = Math.hypot(x - avatarX, y - avatarY)
                if (d < score) { score = d; best = {x: x, y: y, tail: side, at: side === "left" || side === "right" ? y + 23 - r.y : x + 23 - r.x} }
            }
        }
        if (best) { tail = best.tail; tailOffset = best.at; relocating = true; avatarX = best.x; avatarY = best.y; relocation.restart() }
        placeBubble()
    }
    function showHelpFor(id, item) {
        if (!helpService) return
        highlightItem = item
        const target = item ? item.mapToItem(root, 0, 0, item.width, item.height) : Qt.rect(0, 0, 0, 0)
        if (helpService.request(id)) moveBeside(target)
        else helpUnavailable(id)
    }
    function focusHelp() {
        let item = root.Window.window ? root.Window.window.activeFocusItem : null
        while (item && item !== root) {
            const id = item.helpId || item.help || ""
            if (id) { showHelpFor(id, item); return }
            item = item.parent
        }
        showHelpFor("phase.model", null)
    }
    function setTourTarget(item) {
        if (!item) avoidRect = Qt.rect(0, 0, 0, 0)
        if (item) {
            let ancestor = item.parent
            while (ancestor && ancestor !== root.Window.window.contentItem) {
                if (ancestor.contentY !== undefined && ancestor.contentItem) {
                    const p = item.mapToItem(ancestor.contentItem, 0, 0)
                    if (p.y < ancestor.contentY) ancestor.contentY = Math.max(0, p.y-12)
                    else if (p.y+item.height > ancestor.contentY+ancestor.height)
                        ancestor.contentY = Math.min(ancestor.contentHeight-ancestor.height, p.y+item.height-ancestor.height+12)
                }
                ancestor = ancestor.parent
            }
        }
        highlightItem = item
        if (item) moveBeside(item.mapToItem(root, 0, 0, item.width, item.height))
    }
    function focusQuestion() {
        if (page === "conversation" && content.item) content.item.focusQuestion()
    }
    function open() { if (!characterVisible) return; opened = true; panelRequested(); placeBubble(); Qt.callLater(focusQuestion) }
    function dismiss() {
        if (helpService && helpService.tourActive) helpService.pauseTour()
        if (returnState !== null) {
            const was = returnState
            returnState = null
            page = was.page; bubbleWidth = was.width; bubbleHeight = was.height
            tail = was.tail; tailOffset = was.offset
            relocating = true; avatarX = was.x; avatarY = was.y; relocation.restart()
        }
        avoidRect = Qt.rect(0, 0, 0, 0)
        highlightItem = null
        opened = false
    }
    onAvatarXChanged: placeBubble()
    onAvatarYChanged: placeBubble()
    onActualWidthChanged: placeBubble()
    onActualHeightChanged: placeBubble()
    onTopInsetChanged: placeBubble()
    onBottomEdgeChanged: placeBubble()
    onTailOffsetChanged: placeBubble()
    onWidthChanged: { avatarX = clamp(avatarX, 0, width - 46); placeBubble() }
    onHeightChanged: { avatarY = clamp(avatarY, topInset, bottomEdge - 46); placeBubble() }
    onDockedChanged: { opened = true; placeBubble() }
    onOpenedChanged: { if (chat) chat.setOpened(opened); if (opened) Qt.callLater(focusQuestion) }
    Component.onCompleted: { placeBubble(); if (chat) { chat.setMotion(motionEnabled); chat.setOpened(opened) } }
    Behavior on avatarX { enabled: root.relocating && !root.dragging; NumberAnimation { duration: root.motionEnabled ? Theme.motion.SLIDE : 0; easing.type: Theme.motion.EASE } }
    Behavior on avatarY { enabled: root.relocating && !root.dragging; NumberAnimation { duration: root.motionEnabled ? Theme.motion.SLIDE : 0; easing.type: Theme.motion.EASE } }
    NumberAnimation { id: flip; target: root; property: "flipProgress"; from: 0; to: 1; duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE }
    Timer { id: relocation; interval: 340; onTriggered: root.relocating = false }
    Shortcut { sequence: "Esc"; enabled: root.useShortcuts && root.opened; onActivated: root.dismiss() }
    Shortcut { sequence: "Ctrl+L"; enabled: root.useShortcuts; onActivated: root.opened ? root.dismiss() : root.open() }
    Shortcut { sequence: "F1"; enabled: root.useShortcuts; onActivated: root.focusHelp() }
    Shortcut { sequence: "Shift+F1"; enabled: root.useShortcuts; onActivated: root.whatsThis = true }
    MouseArea {
        anchors.fill: parent; z: 1000
        visible: root.whatsThis
        cursorShape: Qt.WhatsThisCursor
        onClicked: mouse => {
            root.whatsThis = false
            let candidates = root.parent.children
            for (let i = candidates.length - 1; i >= 0; --i) {
                let item = candidates[i]
                if (item === root || !item.visible) continue
                let p = root.mapToItem(item, mouse.x, mouse.y)
                if (!item.contains(p)) continue
                let child = item.childAt(p.x, p.y)
                while (child) { item = child; p = root.mapToItem(item, mouse.x, mouse.y); child = item.childAt(p.x, p.y) }
                while (item) {
                    const id = item.helpId || item.help || ""
                    if (id) { root.showHelpFor(id, item); return }
                    item = item.parent
                }
            }
        }
    }
    Connections {
        target: root.helpService
        function onRequested() { root.remember(); root.page = "help"; root.open() }
        function onManualOpened() { root.remember(); root.page = "manual"; root.open() }
        function onTourChanged() {
            if (root.helpService.tourActive) {
                root.remember(); root.page = "tour"
                if (!root.docked) { root.bubbleWidth = 340; root.bubbleHeight = 560 }
                root.open()
            }
        }
        function onDismissed() { root.dismiss() }
        function onAskRequested(text) {
            root.page = "conversation"
            if (root.chat) root.chat.setDraft(text)
        }
    }
    Connections {
        target: root.chat
        function onSetupRequested() { root.page = "setup"; root.open() }
        function onOpenRequested() { root.open() }
    }
    Connections {
        target: root.chat ? root.chat.setupBackend : null
        function onConfigured() { root.page = "conversation" }
        function onDismissed() { root.page = "conversation" }
    }
    Spotlight { targetRect: root.highlightRect; active: root.temporary && root.opened; persistent: true }
    HoverHandler {
        // On the window's root, an ancestor of everything: Qt stops the hover at the first item hovered and only
        // goes up from there, so a window-wide handler on this layer would leave every control below unhovered (D01).
        id: pointer
        parent: root.Window.contentItem
        onPointChanged: {
            if (root.dragging) return
            const at = root.mapFromItem(pointer.parent, point.position)
            avatar.lookAt((at.x - root.avatarX - 23) / 46, (at.y - root.avatarY - 23) / 46)
        }
    }
    Character {
        id: avatar
        objectName: "assistantCharacter"
        x: root.avatarX; y: root.avatarY
        width: 46; height: 46
        // it lives on the overlay, above everything: a dialog of the file part must not have it standing on its words
        visible: root.characterVisible && !root.docked && !(typeof filePart !== "undefined" && filePart && filePart.dialogVisible)
        animated: root.animated
        awake: root.opened
        dragging: root.dragging
        thinking: root.chat ? root.chat.state === "thinking" : false
        state: root.chat ? root.chat.state : "idle"
        style: root.characterStyle
        where: root.chat ? root.chat.destination : ""
        DragHandle { anchors.fill: parent; assistant: root; toggleOnClick: true }
    }
    Item {
        id: bubble
        objectName: "assistantBubble"
        parent: root.docked && root.dockItem ? root.dockItem : root
        x: root.docked ? (root.dockItem ? 0 : root.dockRect.x) : root.bubbleX * root.flipProgress + root.flipFrom.x * (1-root.flipProgress)
        y: root.docked ? (root.dockItem ? 0 : root.dockRect.y) : root.bubbleY * root.flipProgress + root.flipFrom.y * (1-root.flipProgress)
        width: root.actualWidth; height: root.actualHeight
        opacity: root.opened && root.characterVisible && (!root.docked || root.dockVisible) ? 1 : 0
        visible: opacity > 0
        enabled: root.opened
        Behavior on opacity { NumberAnimation {
            duration: root.motionEnabled ? (root.opened ? Theme.motion.NORMAL : Theme.motion.QUICK) : 0
            easing.type: root.opened ? Theme.motion.EASE : Theme.motion.EASE_IN
        } }
        transform: Translate {
            x: root.motionEnabled && !root.docked ? (root.tail === "left" ? -10 : root.tail === "right" ? 10 : 0) * (1-bubble.opacity) : 0
            y: root.motionEnabled && !root.docked ? (root.tail === "top" ? -10 : root.tail === "bottom" ? 10 : 0) * (1-bubble.opacity) : 0
        }
        readonly property real insetLeft: !root.docked && root.tail === "left" ? 12 : 0
        readonly property real insetRight: !root.docked && root.tail === "right" ? 12 : 0
        readonly property real insetTop: !root.docked && root.tail === "top" ? 12 : 0
        readonly property real insetBottom: !root.docked && root.tail === "bottom" ? 12 : 0
        BubbleOutline {
            anchors.fill: parent
            visible: !root.docked
            tail: root.docked ? "" : root.tail
            at: root.tail === "left" || root.tail === "right" ? root.avatarY + 23 - bubble.y : root.avatarX + 23 - bubble.x
            cornerRadius: root.docked ? Theme.radius.CARD : 10
        }
        Item {
            id: card
            x: bubble.insetLeft + 1; y: bubble.insetTop + 1
            width: bubble.width - bubble.insetLeft - bubble.insetRight - 2
            height: bubble.height - bubble.insetTop - bubble.insetBottom - 2
        }
        ColumnLayout {
            anchors.fill: card
            anchors.leftMargin: 10; anchors.rightMargin: 10
            anchors.topMargin: 8; anchors.bottomMargin: 10
            spacing: Theme.space.S
            M.Label {
                objectName: "assistantTitle"
                text: root.texts.name; textStyle: "title"
                horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true
                visible: root.docked || card.height >= Theme.size.BUBBLE_LOW
                DragHandle { anchors.fill: parent; assistant: root; enabled: !root.docked }
            }
            RowLayout {
                Layout.fillWidth: true
                visible: root.page !== "conversation"
                Character { width: 28; height: 28; visible: root.docked; animated: root.animated; awake: root.opened; where: "" }
                Item { Layout.fillWidth: true }
                // R474: the two buttons of the head the same icon button (the three dots were a character of the font,
                // of another size from the cross)
                M.Button { objectName: "assistantMenuButton"; iconName: "ellipsis"; flat: true; padding: 0; tip: root.texts.more || ""; menu: menu
                    Layout.preferredWidth: Theme.size.CONTROL; Layout.preferredHeight: Theme.size.CONTROL }
                M.Button { objectName: "assistantHelpClose"; iconName: "x"; flat: true; padding: 0; tip: root.texts.close; onClicked: root.dismiss()
                    Layout.preferredWidth: Theme.size.CONTROL; Layout.preferredHeight: Theme.size.CONTROL }
                M.Menu {
                    id: menu
                    M.MenuItem { text: root.texts.attach; enabled: !!root.chat; onTriggered: root.chat.choose_attachments() }
                    M.MenuItem { text: root.texts.view; enabled: root.chat ? root.chat.canShowView : false; onTriggered: root.chat.showView() }
                    M.MenuItem { text: root.docked ? root.texts.floating : root.texts.dock; onTriggered: { root.docked = !root.docked; root.placementSaved(root.avatarX, root.avatarY, root.bubbleWidth, root.bubbleHeight, root.docked) } }
                    M.MenuItem { text: root.texts.newChat; onTriggered: { if (root.chat) root.chat.newConversation(); root.page = "conversation" } }
                    M.MenuItem { text: root.texts.setup; onTriggered: root.page = "setup" }
                    M.MenuItem { text: root.texts.manual; onTriggered: root.helpService.openManual("README.md") }
                    M.MenuItem { text: root.texts.tour; onTriggered: root.helpService.startTour(false) }
                }
            }
            Loader {
                id: content
                objectName: "assistantContent"
                Layout.fillWidth: true; Layout.fillHeight: true
                sourceComponent: root.page === "help" ? helpPage : root.page === "manual" ? manualPage : root.page === "tour" ? tourPage : root.page === "setup" ? setupPage : root.page === "local" ? localPage : conversationPage
            }
        }
        Component { id: helpPage; HelpPage { service: root.helpService } }
        Component { id: manualPage; ManualPage { service: root.helpService } }
        Component { id: tourPage; TourPage { service: root.helpService } }
        Component { id: setupPage; SetupPage { backend: root.chat ? root.chat.setupBackend : null; texts: root.texts } }
        Component { id: localPage; LocalPage { backend: root.chat ? root.chat.setupBackend.localModels : null; texts: root.texts } }
        Component { id: conversationPage; Conversation {
            backend: root.chat; texts: root.texts; docked: root.docked
            onDockRequested: { root.docked = !root.docked; root.placementSaved(root.avatarX, root.avatarY, root.bubbleWidth, root.bubbleHeight, root.docked) }
            onCloseRequested: root.dismiss()
            onMenuRequested: menu.open()
            onAttachmentRequested: root.attachmentRequested()
        } }
        MouseArea {
            id: grip
            objectName: "assistantGrip"
            readonly property bool gripLeft: root.tail === "right" || ((root.tail === "top" || root.tail === "bottom") && root.avatarX + 23 > bubble.x + bubble.width / 2)
            readonly property bool gripTop: root.tail === "bottom" || ((root.tail === "left" || root.tail === "right") && root.avatarY + 23 > bubble.y + bubble.height / 2)
            x: gripLeft ? 0 : bubble.width - width; y: gripTop ? 0 : bubble.height - height
            width: 16; height: 16; visible: !root.docked
            cursorShape: gripLeft === gripTop ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor
            property point pressPoint
            property rect initial
            property bool fromLeft
            property bool fromTop
            onPressed: mouse => {
                pressPoint = mapToItem(root, mouse.x, mouse.y)
                initial = Qt.rect(bubble.x, bubble.y, bubble.width, bubble.height)
                fromLeft = gripLeft; fromTop = gripTop; root.resizing = true
            }
            onPositionChanged: mouse => {
                if (!pressed) return
                const p = mapToItem(root, mouse.x, mouse.y)
                const dx = p.x - pressPoint.x, dy = p.y - pressPoint.y
                const horizontal = root.tail === "left" || root.tail === "right"
                const xs = root.resizedSpan(initial.x, initial.width, fromLeft, dx, root.width, Math.min(280, root.width), horizontal ? null : root.avatarX+23)
                const ys = root.resizedSpan(initial.y, initial.height, fromTop, dy, root.bottomEdge, Math.min(240, root.bottomEdge-root.topInset), horizontal ? root.avatarY+23 : null, root.topInset)
                const x = xs[0], w = xs[1], y = ys[0], h = ys[1]
                root.tailOffset = root.tail === "left" || root.tail === "right" ? root.avatarY + 23 - y : root.avatarX + 23 - x
                root.bubbleWidth = w; root.bubbleHeight = h; root.placeBubble()
            }
            onReleased: { root.resizing = false; root.placementSaved(root.avatarX, root.avatarY, root.bubbleWidth, root.bubbleHeight, root.docked) }
            onCanceled: root.resizing = false
            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                transform: Scale { origin.x: 8; origin.y: 8; xScale: grip.gripLeft ? -1 : 1; yScale: grip.gripTop ? -1 : 1 }
                ShapePath {
                    strokeColor: Theme.colors.muted; strokeWidth: 1; fillColor: "transparent"
                    PathSvg { path: "M10,14 L14,10 M6,14 L14,6" }
                }
            }
        }
    }
}
