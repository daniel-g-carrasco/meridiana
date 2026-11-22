import QtQuick
import Meridiana.Theme

// R633 (Daniel 15/11/2026, the Plant's panel: «mi piace il B: testate sempre in vista ... lo renderei un comportamento
// generale per queste schede (schede di destra), centralizziamo e unifichiamo»): the heads of a side panel's sections
// always in view. While the page scrolls, the head of a section that would leave the page at the top stays at the top,
// under the ones before it, and the heads of the sections below the page stay at the bottom: every section is one click
// away. A held head is the section's own head drawn again (SectionHead.qml), the same at the pixel; the content passes
// under the held heads and dissolves from their edge (EdgeFades, `held`), not from the page's.
// The heads held at the top, and those at the bottom, take at most ControlMetrics.heldShare of the page each: past it
// the farthest ones go on scrolling out of the page, pushed by the next (the content keeps at least the rest).
// Placed by M.ScrollPage when `keepHeads` (M.PanelPage); the sections come by themselves (Section.headKeeper). Nothing is
// made while the page scrolls: the copies are made when the sections on show change, the scroll moves them.
Item {
    id: root
    objectName: "heldHeads"
    property Flickable flickable
    // the page's air above the first head and under the last, and its gap between two heads
    property real air: 0
    property real gap: 0
    property bool keeping: false
    // R638 (Daniel 15/11/2026: «il rimbalzo che si ha quando si scorre oltre il limite fa sì che i bordi delle
    // sottoschede si sballino completamente»): the rebound's own shift of the content (ScrollBar.reboundShift), on top
    // of contentItem.y, which follows a drag or a flick past the ends by itself: the heads and the frames follow both
    property real overshoot: 0
    anchors.fill: flickable
    clip: true
    // every section that asked (Section.headKeeper), and those on show in their order down the page with their tops in
    // the content, their x and the height of their held head
    property var sections: []
    property var shownHeads: []
    property var tops: []
    property var lefts: []
    property var heights: []
    // and the whole height of each section, for its frame
    property var fulls: []
    function keep(section) {
        if (sections.indexOf(section) >= 0) return
        sections = sections.concat([section])
        section.visibleChanged.connect(measure)
        section.yChanged.connect(measure)
        section.heldHeightChanged.connect(measure)
        section.heightChanged.connect(measure)
        measure()
    }
    function drop(section) {
        const at = sections.indexOf(section)
        if (at < 0) return
        try {
            section.visibleChanged.disconnect(measure)
            section.yChanged.disconnect(measure)
            section.heldHeightChanged.disconnect(measure)
            section.heightChanged.disconnect(measure)
        } catch (error) {
            console.warn("HeldHeads: a section went before its signals:", error)
        }
        sections = sections.slice(0, at).concat(sections.slice(at + 1))
        measure()
    }
    // R677: a form changes many sections in one turn. Publish one complete set of
    // heads after that turn, before the next frame, rather than each partial set.
    property bool measurePending: false
    // Child sections may ask again while the keeper is being torn down.
    property bool disposing: false
    Component.onDestruction: { disposing = true; measurePending = false }
    function measure() {
        if (disposing) return
        measurePending = true; Qt.callLater(root.flushMeasure)
    }
    function flushMeasure() { if (measurePending) { measurePending = false; measureNow() } }
    Connections {
        target: root.Window.window
        function onAfterAnimating() { root.flushMeasure() }
    }
    function measureNow() {
        if (!flickable || !keeping) { if (shownHeads.length) { shownHeads = []; tops = []; lefts = []; heights = []; fulls = [] } return }
        const content = flickable.contentItem
        let found = []
        for (const section of sections) {
            if (!section || !section.visible || section.width <= 0) continue
            const at = section.mapToItem(content, 0, 0)
            found.push({section: section, top: at.y, left: at.x, height: section.heldHeight, full: section.height})
        }
        found.sort((a, b) => a.top - b.top)
        const same = found.length === shownHeads.length && found.every((f, i) => f.section === shownHeads[i])
        if (!same) shownHeads = found.map(f => f.section)
        tops = found.map(f => f.top)
        lefts = found.map(f => f.left)
        heights = found.map(f => f.height)
        fulls = found.map(f => f.full)
    }
    onKeepingChanged: measure()
    Connections {
        target: root.flickable
        function onContentHeightChanged() { root.measure() }
        function onWidthChanged() { root.measure() }
    }
    // where each head stands for the scroll in hand (`shift` the content's offset, contentItem.y): `at` "top", "bottom"
    // or "" (in its place), `y` in the page; the edges the content dissolves from (topInset, bottomInset: 0 when nothing
    // is held there) and how tall each dissolve may be (topRoom, bottomRoom): no taller than the content gone under the
    // held heads, and never over a head in its place (it would fade, then come back whole when held).
    // R633 (Daniel 15/11/2026: «perché la dissolvenza prende pure il bordo della sottoscheda?»): each section's frame,
    // drawn here over what scrolls so that it never dissolves (frameTop, frameBottom): from its head, in its place or
    // held, to the section's own foot, or, where the section goes on past what is seen, to the edge seen (over the
    // heads held at the bottom, or the page's air), where it closes with its rounded foot; `body` how much of the
    // section's body is seen under its head (the head's band rounds its foot as that goes under its radius).
    function place(shift, height, tops, heights, fulls) {
        const n = tops.length
        const out = {at: [], y: [], topInset: 0, bottomInset: 0, topRoom: Infinity, bottomRoom: Infinity,
                     frameTop: [], frameBottom: [], body: []}
        if (n === 0) return out
        const share = Math.floor(height * ControlMetrics.heldShare)
        const natural = tops.map(t => t + shift)
        // at the top: stacked from the page's air down, never past the share; a head arriving pushes the ones above it
        const top = new Array(n)
        let slot = air
        const slots = tops.map((t, i) => { const s = Math.min(slot, share - heights[i]); slot += heights[i] + gap; return s })
        for (let i = n - 1; i >= 0; i--)
            top[i] = Math.max(natural[i], i < n - 1 ? Math.min(slots[i], top[i + 1] - gap - heights[i]) : slots[i])
        // at the bottom, the same from the page's foot up
        const bottom = new Array(n)
        slot = height - air
        const feet = new Array(n)
        for (let i = n - 1; i >= 0; i--) { slot -= heights[i]; feet[i] = Math.max(slot, height - share); slot -= gap }
        for (let i = 0; i < n; i++)
            bottom[i] = Math.min(natural[i], i > 0 ? Math.max(feet[i], bottom[i - 1] + heights[i - 1] + gap) : feet[i])
        let lowestTop = -1, highestBottom = -1
        for (let i = 0; i < n; i++) {
            if (top[i] > natural[i] + 0.01) { out.at.push("top"); out.y.push(top[i]); lowestTop = i }
            else if (bottom[i] < natural[i] - 0.01) { out.at.push("bottom"); out.y.push(bottom[i]); if (highestBottom < 0) highestBottom = i }
            else { out.at.push(""); out.y.push(natural[i]) }
        }
        if (lowestTop >= 0) {
            out.topInset = top[lowestTop] + heights[lowestTop]
            out.topRoom = top[lowestTop] - natural[lowestTop]
        }
        if (highestBottom >= 0) {
            out.bottomInset = height - bottom[highestBottom]
            out.bottomRoom = natural[highestBottom] - bottom[highestBottom]
        }
        // the frames: no section is seen past `limit`; a section cut there hides what scrolls under it, from there down
        const limit = highestBottom >= 0 ? bottom[highestBottom] - gap : height - air
        for (let i = 0; i < n; i++) {
            const foot = out.y[i] + heights[i], end = natural[i] + fulls[i]
            const shown = out.at[i] === "bottom" ? foot : Math.max(foot, Math.min(end, limit))
            out.frameTop.push(out.y[i])
            out.frameBottom.push(shown)
            out.body.push(shown - foot)
            if (out.at[i] !== "bottom" && end > limit + 0.01 && natural[i] < limit) {
                out.bottomInset = Math.max(out.bottomInset, height - limit)
                out.bottomRoom = Math.min(out.bottomRoom, end - limit)
            }
        }
        for (let i = 0; i < n; i++) {
            if (out.at[i] !== "") continue
            if (natural[i] >= out.topInset) out.topRoom = Math.min(out.topRoom, natural[i] - out.topInset)
            if (natural[i] + heights[i] <= height - out.bottomInset)
                out.bottomRoom = Math.min(out.bottomRoom, height - out.bottomInset - natural[i] - heights[i])
        }
        return out
    }
    readonly property var placed: flickable && keeping ? place(flickable.contentItem.y + overshoot, flickable.height, tops, heights, fulls)
                                                       : place(0, 0, [], [], [])
    // how much of a section's body is seen under its head (Section.foot); a section not on show: all of it
    function bodyShown(section) {
        const index = shownHeads.indexOf(section)
        return index < 0 ? (section.progress > 0 ? Infinity : 0) : placed.body[index]
    }
    function snap(value) { return Math.round(value * dpr) / dpr }
    readonly property real topInset: placed.topInset
    readonly property real bottomInset: placed.bottomInset
    readonly property real topRoom: placed.topRoom
    readonly property real bottomRoom: placed.bottomRoom
    // a click (or the keyboard) on a head while it is held: the page brings its section into view, the head where it
    // stands at the top (Section.activate). Followed while the section opens or closes (and a little after: PATIENCE is
    // kept with less motion), so that the head stays put.
    property Item revealing: null
    function headActivated(section) {
        const index = shownHeads.indexOf(section)
        if (index < 0 || placed.at[index] === "") return
        revealing = section
        settle.restart()
        reveal()
    }
    function reveal() {
        const index = shownHeads.indexOf(revealing)
        if (index < 0 || !flickable) return
        let slot = air
        for (let i = 0; i < index; i++) slot += heights[i] + gap
        slot = Math.min(slot, Math.floor(flickable.height * ControlMetrics.heldShare) - heights[index])
        const most = Math.max(0, flickable.contentHeight - flickable.height)
        flickable.contentY = Math.max(0, Math.min(most, tops[index] - slot))
    }
    onTopsChanged: if (revealing) reveal()
    Timer { id: settle; interval: Theme.motion.NORMAL + Theme.motion.PATIENCE; onTriggered: root.revealing = null }
    readonly property real dpr: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    Repeater {
        model: root.shownHeads
        Item {
            id: slot
            required property var modelData
            required property int index
            readonly property string at: root.placed.at[index] || ""
            objectName: "held:" + modelData.headName
            visible: at !== ""
            x: root.lefts[index] || 0
            // on a whole pixel of the screen, as the head in its place stands when the page is at rest
            y: root.snap(root.placed.y[index] || 0)
            width: modelData.width
            height: modelData.heldHeight
            clip: true
            SectionHead { section: slot.modelData; held: true }
        }
    }
    // the sections' frames, over their heads as in a section, never under the dissolve
    Repeater {
        model: root.shownHeads
        Rectangle {
            required property var modelData
            required property int index
            readonly property real from: root.snap(root.placed.frameTop[index] || 0)
            objectName: "frame:" + modelData.headName
            x: root.lefts[index] || 0
            y: from
            width: modelData.width
            height: Math.max(0, root.snap(root.placed.frameBottom[index] || 0) - from)
            visible: height > 0 && !modelData.nested && modelData.framed
            radius: modelData.radius
            color: "transparent"; border.width: Theme.line.HAIR; border.color: Theme.colors.line
        }
    }
}
