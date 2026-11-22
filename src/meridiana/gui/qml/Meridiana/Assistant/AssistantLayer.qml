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
    // Study 50, D9: where the panels are not (the File page and the Settings) he is shown floating, still docked:
    // `docked` is the setting, `dockedNow` how he is laid out; back among the panels he is their tab again
    property bool dockAllowed: true
    readonly property bool dockedNow: docked && dockAllowed
    onDockedNowChanged: placeBubble()
    property Item dockItem: null
    property bool opened: false
    property bool animated: true
    property string page: "conversation"
    property string phaseKey: "model"
    property var places: ({})
    // R642: his side, the one source (app/assistant/figure.SIZE through ControlMetrics.figure), and its half
    readonly property real figureSize: M.ControlMetrics.figure
    readonly property real figureHalf: figureSize / 2
    property rect homeRect: Qt.rect(0, 0, width, height)
    property real topInset: 0
    property real bottomInset: 0
    readonly property real bottomEdge: height-bottomInset
    property real avatarX: Math.max(12, width - 70)
    property real avatarY: Math.max(12, height - 70)
    property real bubbleWidth: 320
    property real bubbleHeight: 500
    property string tail: "right"
    property real tailOffset: bubbleHeight - figureHalf
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
    // R555 (11): the corners of the item highlighted, read from it (top-left, top-right, bottom-right, bottom-left), so
    // that the highlight's are concentric: its own highlightRadii (the phase tab), else its four corners, its radius,
    // its background's radius, else square
    function radiiOf(item) {
        if (!item) return [0, 0, 0, 0]
        if (item.highlightRadii !== undefined) return item.highlightRadii
        if (item.topLeftRadius !== undefined)
            return [item.topLeftRadius, item.topRightRadius, item.bottomRightRadius, item.bottomLeftRadius]
        if (item.radius !== undefined) return [item.radius, item.radius, item.radius, item.radius]
        const back = item.background
        if (back && back.radius !== undefined) return [back.radius, back.radius, back.radius, back.radius]
        return [0, 0, 0, 0]
    }
    onHighlightItemChanged: trackHighlight()
    onAvoidRectChanged: trackHighlight()
    Connections {
        target: root.highlightItem && root.opened ? root.Window.window : null
        function onFrameSwapped() { root.trackHighlight() }
    }
    property rect dockRect: Qt.rect(Math.max(0, width - 360), 0, Math.min(width, 360), height)
    readonly property real actualWidth: dockedNow ? dockRect.width : Math.min(bubbleWidth, Math.max(200, width - 70))
    // R474: «il fumetto occupa più spazio di quello necessario, anche quando lo si richiama con l'help»: a page other than
    // the conversation (help, tour, manual, setup) is as tall as what it shows.
    // R611 (Daniel 14/11/2026: in the tour «resta una barra di scorrimento per poche righe mancanti»): what it shows is
    // the whole column of the bubble as laid out (its title, its head, the page, their spacing), with the column's
    // margins and the frame; the sum written by hand left the title out, 24 px short at every step. It grows up to the
    // room of the window less a margin, and scrolls only past that; a height set by hand with the grip is kept.
    readonly property real fittedHeight: page !== "conversation" && content.item && content.item.implicitHeight > 0
        ? Math.ceil(column.implicitHeight + column.topRoom + column.sideRoom + 2
                    + (tail === "top" || tail === "bottom" ? 12 : 0))
        : bubbleHeight
    property bool heightByHand: false
    onPageChanged: heightByHand = false
    readonly property real room: Math.max(0, bottomEdge - topInset)
    readonly property real actualHeight: dockedNow ? dockRect.height
        : page === "conversation" || heightByHand ? Math.min(bubbleHeight, room)
        : Math.min(fittedHeight, Math.max(0, room - 2 * Theme.space.M))
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
            avatarX = clamp(anchor[0] === "left" ? anchor[2] : width-figureSize-anchor[2], 0, width-figureSize)
            avatarY = clamp(anchor[1] === "top" ? anchor[3] : height-figureSize-anchor[3], topInset, bottomEdge-figureSize)
        } else {
            avatarX = clamp(homeRect.x+homeRect.width-(figureSize + Theme.space.L), 0, width-figureSize)
            avatarY = clamp(homeRect.y+homeRect.height-(figureSize + Theme.space.L)-(phaseKey === "model" ? 32 : 0), topInset, bottomEdge-figureSize)
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
        if (projectSpot !== null) return        // over File: his place is the page's free side (placeInFile)
        if (!placedOnce) { repositionHome(); return }
        if (temporary || dragging || resizing || !root.Window.window || !root.Window.window.visible) return
        const x = clamp(avatarX, 0, width - figureSize)
        let y = clamp(avatarY, topInset, bottomEdge - figureSize)
        const band = bandRect()
        if (band.width > 0 && intersects(Qt.rect(x, y, figureSize, figureSize), band)) y = clamp(band.y - figureSize - 4, topInset, bottomEdge - figureSize)
        if (x === avatarX && y === avatarY) return
        relocating = true
        avatarX = x; avatarY = y
        relocation.restart()
    }
    // Daniel 15/11/2026 («spostalo, tienilo sul fianco libero»): over File and the Settings he stood where he was in
    // the project, over a page's words. While File is open his place is the free side of the page, right of its
    // column (File/FilePage.qml, freeSide; AssistantHost sets it, empty while File is closed): at its corner low on the
    // right, as far from its edges as his home in a phase is from the view's (repositionHome). Where he was in the
    // project is kept and given back when File closes; moved by hand over File, he stays there until it closes.
    // Guard: tests/quick/meridio/test_fianco_file.py.
    property rect fileSide: Qt.rect(0, 0, 0, 0)
    property var projectSpot: null
    property bool movedInFile: false
    onFileSideChanged: placeInFile()
    onDraggingChanged: if (!dragging && projectSpot !== null) movedInFile = true
    function placeInFile() {
        if (fileSide.width <= 0 || fileSide.height <= 0) {
            if (projectSpot === null) return
            const was = projectSpot
            projectSpot = null; movedInFile = false
            if (temporary || dragging) return
            relocating = false
            avatarX = clamp(was.x, 0, width - M.ControlMetrics.figure)
            avatarY = clamp(was.y, topInset, bottomEdge - M.ControlMetrics.figure)
            return
        }
        if (projectSpot === null) projectSpot = {x: avatarX, y: avatarY}
        if (temporary || dragging || resizing || movedInFile) return
        // he changes place with the page, at once: sliding across the window while File fades in, he seemed to
        // go with the page (test_file_s50, MeridioThroughFileFadeTest)
        relocating = false
        const size = M.ControlMetrics.figure
        avatarX = clamp(fileSide.x + fileSide.width - size - Theme.space.L, 0, width - size)
        avatarY = clamp(fileSide.y + fileSide.height - size - Theme.space.L, topInset, bottomEdge - size)
    }
    Timer { id: stayLater; interval: 0; onTriggered: root.stay() }
    onHomeRectChanged: stayLater.restart()
    onPhaseKeyChanged: stayLater.restart()
    onPlacesChanged: if (!placedOnce) repositionHome()
    function intersects(a, b) {
        return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height
    }
    function shape(x, y, side) {
        const w = actualWidth, h = actualHeight, aw = figureSize, gap = 4
        const horizontal = side === "left" || side === "right"
        const sameAxis = horizontal === (tail === "left" || tail === "right")
        const desired = sameAxis ? tailOffset : (horizontal ? (y > height / 2 ? h - figureHalf : figureHalf) : (x > width / 2 ? w - figureHalf : figureHalf))
        const at = clamp(desired, figureHalf, (horizontal ? h : w) - figureHalf)
        if (side === "left") return Qt.rect(x + aw + gap, clamp(y + figureHalf - at, topInset, bottomEdge - h), w, h)
        if (side === "right") return Qt.rect(x - gap - w, clamp(y + figureHalf - at, topInset, bottomEdge - h), w, h)
        if (side === "top") return Qt.rect(clamp(x + figureHalf - at, 0, width - w), y + aw + gap, w, h)
        return Qt.rect(clamp(x + figureHalf - at, 0, width - w), y - gap - h, w, h)
    }
    function fits(r) { return r.x >= 0 && r.y >= topInset && r.x + r.width <= width && r.y + r.height <= bottomEdge }
    // 15/11/2026, the log of the laptop: «Binding loop detected for property fittedHeight» twice at the tour's steps
    // that move him. The height that fits a page depends on the side of the tail (its 12 px on top or below, the width
    // left beside it), and placing the bubble chooses that side by the height: moveBeside set the tail of his home,
    // the height was written again, and its change placed the bubble at once, choosing another side while that height
    // was still being written (asked again inside itself). While moveBeside and dismiss set the tail, its offset and
    // his place one after the other, the bubble is not placed at each of them: once, at the end, on all of them; the
    // search for the place reads the home's tail as R612 wants, not the side a placement in between chose.
    // Guard: tests/quick/meridio/test_resize_r611.py, BindingLoopTest.
    property bool placementHeld: false
    function placeBubble() {
        if (dockedNow || placementHeld) return
        const opposite = {left: "right", right: "left", top: "bottom", bottom: "top"}
        const candidates = [tail, opposite[tail], "left", "right", "top", "bottom"]
        for (let side of candidates) {
            const r = shape(avatarX, avatarY, side)
            if (fits(r)) {
                if ((side === "left" || side === "right") !== (tail === "left" || tail === "right"))
                    tailOffset = side === "left" || side === "right" ? avatarY + figureHalf - r.y : avatarX + figureHalf - r.x
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
            if (keep !== null) edge = Math.min(edge, Math.max(start, Math.floor(keep - figureHalf)))
            return [edge, end - edge]
        }
        let edge = Math.max(Math.min(start + length + delta, limit), start + minimum)
        if (keep !== null) edge = Math.max(edge, Math.min(start + length, Math.floor(keep + (figureHalf + 0.5))))
        return [start, edge - start]
    }
    function remember() {
        if (returnState === null) returnState = {x: avatarX, y: avatarY, opened: opened, page: page,
                                                tail: tail, offset: tailOffset, width: bubbleWidth, height: bubbleHeight}
    }
    function moveBeside(rect) {
        if (dockedNow || rect.width <= 0) return
        avoidRect = rect
        // R612 (Daniel 14/11/2026: with «Previous» Meridio «non si sposta», and after it not with «Next» either): the
        // place was the free one nearest to where he stood, with the tail and its offset of the step before, so it
        // depended on the way he had come, and once on a spot free for the next targets he stayed there. Now it is
        // measured from where he was before the tour or the help (his home, returnState) with that tail: the place
        // depends on the step only, whichever way he comes to it; with no free place he goes home.
        const home = returnState !== null ? returnState : {x: avatarX, y: avatarY, tail: tail, offset: tailOffset}
        placementHeld = true
        tail = home.tail; tailOffset = home.offset
        // Compare complete character-and-bubble footprints, keeping the nearest free position.
        const points = [[rect.x - figureSize - Theme.space.XL, rect.y], [rect.x + rect.width + Theme.space.XL, rect.y],
                        [12, topInset+12], [width - (figureSize + Theme.space.L), topInset+12], [12, bottomEdge - (figureSize + Theme.space.L)], [width - (figureSize + Theme.space.L), bottomEdge - (figureSize + Theme.space.L)]]
        let best = null, score = Infinity
        for (let p of points) {
            const x = clamp(p[0], 0, width - figureSize), y = clamp(p[1], topInset, bottomEdge - figureSize)
            if (intersects(Qt.rect(x, y, figureSize, figureSize), rect)) continue
            for (let side of [tail, "left", "right", "top", "bottom"]) {
                const r = shape(x, y, side)
                if (!fits(r) || intersects(r, rect)) continue
                const d = Math.hypot(x - home.x, y - home.y)
                if (d < score) { score = d; best = {x: x, y: y, tail: side, at: side === "left" || side === "right" ? y + figureHalf - r.y : x + figureHalf - r.x} }
            }
        }
        if (!best) best = {x: home.x, y: home.y, tail: home.tail, at: home.offset}
        tail = best.tail; tailOffset = best.at; relocating = true; avatarX = best.x; avatarY = best.y; relocation.restart()
        placementHeld = false
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
    // R639: inside the window, whatever left him out of it (a place saved for a larger window, the bars grown)
    function bringIn() {
        const size = M.ControlMetrics.figure
        const x = clamp(avatarX, 0, width - size), y = clamp(avatarY, topInset, bottomEdge - size)
        if (x === avatarX && y === avatarY) return
        relocating = false
        avatarX = x; avatarY = y
    }
    function open() { if (!characterVisible) return; opened = true; panelRequested(); placeBubble(); Qt.callLater(focusQuestion) }
    function dismiss() {
        if (helpService && helpService.tourActive) helpService.pauseTour()
        if (returnState !== null) {
            const was = returnState
            returnState = null
            placementHeld = true
            page = was.page; bubbleWidth = was.width; bubbleHeight = was.height
            tail = was.tail; tailOffset = was.offset
            relocating = true; avatarX = was.x; avatarY = was.y; relocation.restart()
            placementHeld = false
            placeBubble()
        }
        avoidRect = Qt.rect(0, 0, 0, 0)
        highlightItem = null
        opened = false
    }
    onAvatarXChanged: placeBubble()
    onAvatarYChanged: placeBubble()
    onActualWidthChanged: placeBubble()
    // In the tour and the help a page's height can come after its place was chosen (the words of a step are laid out at
    // the next frame, the first time a step is shown): the place is chosen again with it, so that it depends on the
    // step only (R612), not on whether the height came before or after (the offset of the tail was taken from the
    // height of the step before: 17 px lower once in a few rounds of tests/quick/meridio/test_tour_r612.py)
    // A turn later, out of the height's own change: moveBeside sets the tail, on which the height depends.
    property bool replacing: false
    function placeBesideAgain() {
        if (!temporary || dragging || resizing || avoidRect.width <= 0) return
        replacing = true
        moveBeside(avoidRect)
        replacing = false
    }
    onActualHeightChanged: {
        placeBubble()
        if (temporary && !placementHeld && !replacing && avoidRect.width > 0) Qt.callLater(root.placeBesideAgain)
    }
    onTopInsetChanged: placeBubble()
    onBottomEdgeChanged: placeBubble()
    onTailOffsetChanged: placeBubble()
    onWidthChanged: { avatarX = clamp(avatarX, 0, width - figureSize); placeBubble() }
    onHeightChanged: { avatarY = clamp(avatarY, topInset, bottomEdge - figureSize); placeBubble() }
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
                if (!root.dockedNow) { root.bubbleWidth = 340; root.bubbleHeight = 560 }
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
        function onSetupRequested() { root.page = "setup"; root.open(); avatar.react("puzzled") }
        function onOpenRequested() { root.open() }
    }
    Connections {
        // R619: an answer ended, failed, a change of his applied: his face says it for a moment (a chat without the
        // signal, a test's, is left alone)
        target: root.chat
        ignoreUnknownSignals: true
        function onReacted(name) { avatar.react(name) }
    }
    Connections {
        target: root.chat ? root.chat.setupBackend : null
        function onConfigured() { root.page = "conversation" }
        function onDismissed() { root.page = "conversation" }
    }
    // study 50, 2.3 (4): in the tour and the help, and in his conversation on what he took the designer to (go_to,
    // AssistantHost: setTourTarget), until the conversation closes or he shows something else
    // R617: the program's one highlight (Controls/Highlight.qml), Meridio's use of it
    M.Highlight { objectName: "assistantSpotlight"
        targetRect: root.highlightRect; radii: root.radiiOf(root.highlightItem); target: root.highlightItem
        active: root.opened && (root.temporary || root.highlightItem !== null); persistent: true }
    HoverHandler {
        // On the window's root, an ancestor of everything: Qt stops the hover at the first item hovered and only
        // goes up from there, so a window-wide handler on this layer would leave every control below unhovered (D01).
        id: pointer
        parent: root.Window.contentItem
        onPointChanged: {
            if (root.dragging) return
            const at = root.mapFromItem(pointer.parent, point.position)
            avatar.lookAt((at.x - root.avatarX - root.figureHalf) / root.figureSize, (at.y - root.avatarY - root.figureHalf) / root.figureSize)
        }
    }
    Character {
        id: avatar
        objectName: "assistantCharacter"
        x: root.avatarX; y: root.avatarY
        width: figureSize; height: figureSize
        // R628: shown over the windows too, File's ones as well, to be used with one open (moved by hand off its words)
        // R632: docked, he is his tab while his conversation is open and the character when it is closed
        visible: root.characterVisible && (!root.dockedNow || !root.opened)
        animated: root.animated
        awake: root.opened
        dragging: root.dragging
        thinking: root.chat ? root.chat.state === "thinking" : false
        state: root.chat ? root.chat.state : "idle"
        greets: true
        // R570: round, as he is drawn: nothing behind him hovers, scrolls or takes a click
        M.PointerShield { radius: width / 2 }
        DragHandle { anchors.fill: parent; assistant: root; toggleOnClick: true }
    }
    Item {
        id: bubble
        objectName: "assistantBubble"
        parent: root.dockedNow && root.dockItem ? root.dockItem : root
        x: root.dockedNow ? (root.dockItem ? 0 : root.dockRect.x) : root.bubbleX * root.flipProgress + root.flipFrom.x * (1-root.flipProgress)
        y: root.dockedNow ? (root.dockItem ? 0 : root.dockRect.y) : root.bubbleY * root.flipProgress + root.flipFrom.y * (1-root.flipProgress)
        width: root.actualWidth; height: root.actualHeight
        opacity: root.opened && root.characterVisible && (!root.dockedNow || root.dockVisible) ? 1 : 0
        visible: opacity > 0
        enabled: root.opened
        Behavior on opacity { NumberAnimation {
            duration: root.motionEnabled ? (root.opened ? Theme.motion.NORMAL : Theme.motion.QUICK) : 0
            easing.type: root.opened ? Theme.motion.EASE : Theme.motion.EASE_IN
        } }
        transform: Translate {
            x: root.motionEnabled && !root.dockedNow ? (root.tail === "left" ? -10 : root.tail === "right" ? 10 : 0) * (1-bubble.opacity) : 0
            y: root.motionEnabled && !root.dockedNow ? (root.tail === "top" ? -10 : root.tail === "bottom" ? 10 : 0) * (1-bubble.opacity) : 0
        }
        readonly property real insetLeft: !root.dockedNow && root.tail === "left" ? 12 : 0
        readonly property real insetRight: !root.dockedNow && root.tail === "right" ? 12 : 0
        readonly property real insetTop: !root.dockedNow && root.tail === "top" ? 12 : 0
        readonly property real insetBottom: !root.dockedNow && root.tail === "bottom" ? 12 : 0
        BubbleOutline {
            id: outline
            anchors.fill: parent
            visible: !root.dockedNow
            tail: root.dockedNow ? "" : root.tail
            at: root.tail === "left" || root.tail === "right" ? root.avatarY + root.figureHalf - bubble.y : root.avatarX + root.figureHalf - bubble.x
            cornerRadius: root.dockedNow ? Theme.radius.CARD : 10
        }
        // R570: the bubble takes every gesture over its outline, tail included, where it has no control of its own;
        // docked, over its whole rectangle
        M.PointerShield { outline: outline }
        Item {
            id: card
            x: bubble.insetLeft + 1; y: bubble.insetTop + 1
            width: bubble.width - bubble.insetLeft - bubble.insetRight - 2
            height: bubble.height - bubble.insetTop - bubble.insetBottom - 2
        }
        // R647 (Daniel 15/11/2026: «mentre ridimensiono il fumetto di meridio i contenuti non si modificano
        // dinamicamente. Accade solo quando rilascio il cursore»): the words follow the bubble at every point of the
        // grip, as its frame does. R611 had them keep the width of the press while the grip was held (every width lays
        // the conversation out again: 56 ms a point with ten long answers, offscreen, 14/11); the measure of the cost
        // now is in tests/quick/meridio/test_resize_r611.py and docs/progetto.md.
        ColumnLayout {
            id: column
            readonly property real sideRoom: 10
            readonly property real topRoom: Theme.space.M
            width: card.width - 2 * sideRoom
            x: card.x + sideRoom
            y: card.y + topRoom
            height: card.height - topRoom - sideRoom
            spacing: Theme.space.S
            M.Label {
                objectName: "assistantTitle"
                text: root.texts.name; textStyle: "title"
                horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true
                // R611: on a page that fits its words, the room of the window decides (its own height would loop)
                visible: root.dockedNow || (root.page === "conversation" ? card.height : root.room) >= Theme.size.BUBBLE_LOW
                DragHandle { anchors.fill: parent; assistant: root; enabled: !root.dockedNow }
            }
            RowLayout {
                Layout.fillWidth: true
                visible: root.page !== "conversation"
                Character { width: 28; height: 28; visible: root.dockedNow; animated: root.animated; awake: root.opened }
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
                    M.MenuItem { text: root.dockedNow ? root.texts.floating : root.texts.dock; onTriggered: { root.docked = !root.dockedNow; root.placementSaved(root.avatarX, root.avatarY, root.bubbleWidth, root.bubbleHeight, root.docked) } }
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
            backend: root.chat; texts: root.texts; docked: root.dockedNow; held: root.resizing
            onTyping: avatar.hear()
            onDockRequested: { root.docked = !root.dockedNow; root.placementSaved(root.avatarX, root.avatarY, root.bubbleWidth, root.bubbleHeight, root.docked) }
            onCloseRequested: root.dismiss()
            onMenuRequested: menu.open()
            onAttachmentRequested: root.attachmentRequested()
        } }
        MouseArea {
            id: grip
            objectName: "assistantGrip"
            readonly property bool gripLeft: root.tail === "right" || ((root.tail === "top" || root.tail === "bottom") && root.avatarX + root.figureHalf > bubble.x + bubble.width / 2)
            readonly property bool gripTop: root.tail === "bottom" || ((root.tail === "left" || root.tail === "right") && root.avatarY + root.figureHalf > bubble.y + bubble.height / 2)
            x: gripLeft ? 0 : bubble.width - width; y: gripTop ? 0 : bubble.height - height
            width: 16; height: 16; visible: !root.dockedNow
            // R570: past the rounded corner it stands on, the pointer is not the bubble's
            // and only in its own square: a mask is the whole test, the item's bounds are not added to it, so the grip
            // took the press anywhere in the bubble (15/11/2026: the «–» did nothing with Meridio low on the right of
            // File, the grip in the bubble's top left corner)
            containmentMask: QtObject {
                function contains(point: point): bool {
                    return point.x >= 0 && point.y >= 0 && point.x < grip.width && point.y < grip.height
                        && outline.contains(grip.mapToItem(outline, point))
                }
            }
            cursorShape: gripLeft === gripTop ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor
            property point pressPoint
            property rect initial
            property bool fromLeft
            property bool fromTop
            onPressed: mouse => {
                pressPoint = mapToItem(root, mouse.x, mouse.y)
                initial = Qt.rect(bubble.x, bubble.y, bubble.width, bubble.height)
                fromLeft = gripLeft; fromTop = gripTop; root.resizing = true
                // R611: a page that fits its words takes, from now on, the height the hand gives it
                if (root.page !== "conversation") { root.bubbleHeight = bubble.height; root.heightByHand = true }
            }
            onPositionChanged: mouse => {
                if (!pressed) return
                const p = mapToItem(root, mouse.x, mouse.y)
                const dx = p.x - pressPoint.x, dy = p.y - pressPoint.y
                const horizontal = root.tail === "left" || root.tail === "right"
                const xs = root.resizedSpan(initial.x, initial.width, fromLeft, dx, root.width, Math.min(280, root.width), horizontal ? null : root.avatarX+root.figureHalf)
                const ys = root.resizedSpan(initial.y, initial.height, fromTop, dy, root.bottomEdge, Math.min(240, root.bottomEdge-root.topInset), horizontal ? root.avatarY+root.figureHalf : null, root.topInset)
                const x = xs[0], w = xs[1], y = ys[0], h = ys[1]
                root.tailOffset = root.tail === "left" || root.tail === "right" ? root.avatarY + root.figureHalf - y : root.avatarX + root.figureHalf - x
                root.bubbleWidth = w; root.bubbleHeight = h; root.placeBubble()
            }
            onReleased: { root.resizing = false; root.placementSaved(root.avatarX, root.avatarY, root.bubbleWidth, root.bubbleHeight, root.docked) }
            onCanceled: root.resizing = false
            // R648: whatever ends the gesture (a release lost outside the window, a grab taken by the compositor), the
            // grip is not held any more once it is not pressed
            onPressedChanged: if (!pressed) root.resizing = false
            // R632 (Daniel 15/11/2026: «spostala un po' più in basso e a destra così da dargli un leggerissimo margine
            // dall'angolo e dalle lo stesso colore del bordino del fumetto»): its strokes touched the rounded corner;
            // drawn a step in from it along the corner's diagonal, the same from both edges, in the outline's colour.
            // The hit area stays in the corner. Guard: tests/quick/meridio/test_grip_r632.py.
            Shape {
                objectName: "assistantGripMark"
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                // the step in first, then the mirror towards the grip's corner
                transform: [
                    Translate { x: -Theme.space.XXS; y: -Theme.space.XXS },
                    Scale { origin.x: 8; origin.y: 8; xScale: grip.gripLeft ? -1 : 1; yScale: grip.gripTop ? -1 : 1 }
                ]
                ShapePath {
                    strokeColor: Theme.colors.line; strokeWidth: Theme.line.HAIR; fillColor: "transparent"
                    PathSvg { path: "M10,14 L14,10 M6,14 L14,6" }
                }
            }
        }
    }
}
