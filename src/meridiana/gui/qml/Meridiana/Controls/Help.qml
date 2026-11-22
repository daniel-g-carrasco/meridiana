pragma Singleton
import QtQuick
// R596, R597 (study 47, P3): the one entry of the help next to things, `Help.show(key, mark)`, for the sections' and
// the tiles' «?», the card's, the help key and «What's this?». It opens the bubble of `key` (HelpBubble.qml, the texts of
// app/interface/help.py through the `helpBook` backend) anchored to `mark`, one at a time: a second call on the same
// mark closes it, a call on another mark moves it there. `close()` closes it (Esc, the change of phase).
QtObject {
    id: root
    // The one setting of where the bubble opens in the panels (study 47, choice 4, still Daniel's to make): "above"
    // the section's title, aligned to the right, with the pointer on the «?» (the study's recommendation); or
    // "beside" the panel, against its inner edge, without the pointer.
    property string panelSide: "above"
    property Item mark: null
    property var bubble: null
    property Component maker: Component { HelpBubble { } }
    // where the bubble of a mark's `helpPlace` opens: its side, its alignment along it, its pointer
    function placeOf(place, mark) {
        if (place === "panel" && panelSide === "beside") {
            let panel = mark
            while (panel && panel.panelId === undefined) panel = panel.parent
            const zone = panel ? panel.zone : "right"
            return {side: zone === "left" ? "right" : "left", align: "center", pointer: false, sideOf: panel}
        }
        if (place === "field") return {side: "right", align: "start", pointer: true, sideOf: null}
        // over a section's title; under a tile and under the card's header
        return {side: place === "panel" ? "above" : "below", align: "end", pointer: true, sideOf: null}
    }
    function show(key, mark) {
        const again = bubble !== null && mark === root.mark
        close()
        if (again || !key || !mark || typeof helpBook === "undefined" || !helpBook) return
        const entry = helpBook.entry(key)
        if (!entry.text) return
        const made = maker.createObject(mark, {entry: entry, helpPlace: mark.helpPlace !== undefined ? mark.helpPlace : "field",
                                               flicks: scrollers(mark)})
        bubble = made
        root.mark = mark
        made.closed.connect(() => root.forget(made))
        made.open()
    }
    // the bubble goes when what holds its mark scrolls (Microsoft's teaching tip: a light dismiss)
    function scrollers(mark) {
        const found = []
        for (let item = mark.parent; item; item = item.parent)
            if (item.contentY !== undefined && item.flicking !== undefined) found.push(item)
        return found
    }
    function forget(made) {
        if (bubble === made) { bubble = null; mark = null }
        made.destroy()
    }
    // true when there was one to close
    function close() {
        if (!bubble) return false
        const open = bubble
        bubble = null; mark = null
        open.close()
        return true
    }
}
