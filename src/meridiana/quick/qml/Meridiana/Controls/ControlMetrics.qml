pragma Singleton
import QtQuick
import Meridiana.Theme
QtObject {
    // R502: the margin between a container's edge and what is inside it, the same on every side that has one: the
    // phase tab around its number's disc and its name (the disc is as far from the tab's top, (32 - 20) / 2), the
    // hover of a tab around the same, the card of the bar of the tools around its first tool and the summary at its
    // right. The compact tracks keep their own, already the same on every side: the plan's view bar 3 (ViewBar.qml),
    // the segments 2 (Segments.qml).
    readonly property real inset: Theme.space.S
    // R518 (Daniel 07/11/2026: «le finestre non sono congruenti… quella della stringatura in automatico non ha gli stessi
    // margini che hanno le altre. Possibile che sia difficile centralizzare queste impostazioni?»): every window of the
    // program is an M.Dialog, with these and no margins of its own. The same margin on the four sides of the frame (the
    // title on the top one, the buttons on the bottom and right ones), one gap between the title, the sections and the
    // bar of the buttons, one between the buttons; the widths a window takes, never closer than dialogEdge to the
    // window's sides.
    readonly property real dialogPad: Theme.space.XL
    readonly property real dialogGap: Theme.space.M
    readonly property real dialogButtonGap: Theme.space.M
    readonly property real dialogEdge: 16
    readonly property var dialogWidth: ({narrow: 420, normal: 560, wide: 720, page: 1200})
    // R520 (Daniel 07/11/2026: «nelle tabelle e nella scelta inverter succede che la barra per lo scrolling si
    // sovrapponga ai contenuti»): the scroll bar's lane, at the right of every list, table and page that scrolls: the
    // content ends before it, the bar is drawn in it and never over a text or a column. Its width is the bar's room of
    // R100 (Theme.size.SCROLLBAR), the gap between the content's end and the lane scrollGap.
    readonly property real scrollLane: Theme.size.SCROLLBAR
    readonly property real scrollGap: Theme.space.XXS
    // R525 (Daniel 07/11/2026: «l'hover nel menu a comparsa nella stringatura automatica non è quello grigio con angoli
    // arrotondati che c'è altrove… centralizza il centralizzabile»): every list that drops (M.Menu, M.ComboBox and the
    // controls made on it, the catalogue's makers, Meridio's selector) has one entry, M.MenuItem: the hover's grey with
    // menuItemRadius, menuPad from the popup's sides, the same height; the current choice of a combo is its check.
    readonly property real menuPad: Theme.space.XS
    readonly property real menuItemRadius: Theme.radius.INNER
    readonly property real menuItemPadV: Theme.space.S
    // R21-F2: how far a drop-down list grows (M.ComboBox's popup): as wide as its longest label up to menuWide (the
    // results' and the properties' long names, 620 as ResultChoice had), as tall as its entries up to menuTall
    readonly property real menuWide: 620
    readonly property real menuTall: 420
    // the picker of 3D objects (ObjectPicker.qml): a tile of a model, its preview inside it, the picker's width
    readonly property real modelTile: 92
    readonly property real modelPreview: 56
    readonly property real pickerWidth: 480
    // R530: how far the content goes past the end of what scrolls before it comes back (Rebound.qml)
    readonly property real reboundReach: Theme.space.L
    // F4 (the reordering of R21, 07/11/2026: «ogni misura viene da Theme o ControlMetrics»): the measures the pages
    // wrote as numbers, each under the name of what it is, the same numbers (nothing moves on the screen).
    // A page's own implicit size: what a view sized to its root takes when the page is shown alone (its gallery, its
    // tests); in the window its card sizes it. The wide pages are a laptop's 1366 x 900.
    readonly property var pageSize: ({wide: {width: 1366, height: 900}, checks: {width: 900, height: 600},
                                      dialogs: {width: 1000}, mapSources: {width: 800, height: 720},
                                      tree: {width: 320, height: 500}, properties: {width: 380, height: 700},
                                      report: {width: 1100, height: 800}})
    // a closed list that names one choice beside others in a row (the catalogue's filters, Meridio's selector):
    // narrower than an M.ComboBox alone (Theme.size.READING / 2); the catalogue's market and bifacial filters wider,
    // for their longest names
    readonly property real choiceWidth: 200
    readonly property real catalogMarketWidth: 230
    readonly property real catalogBifacialWidth: 210
    // the room at a control's right for what is drawn inside it: Meridio's question before its send button, his
    // selector before its arrow
    readonly property real questionRoom: 30
    readonly property real selectorRoom: 26
    // Meridio's figure, floating over the window
    readonly property real figure: 46
    // a check's row: one line, as the row of ui/checks_page.py (the rest in the tooltip); a level's mark and its count
    readonly property real checkRow: 34
    readonly property real markGap: 3
    // the project tree's row: its name and its marks
    readonly property real treeGap: 7
    // the one help mark (HelpMark.qml, R21-F3): a flat button of 20 px round its 12 px circle-question-mark
    readonly property real helpMark: 20
    // a tool button's padding around (above and below Theme.space.XXS): ToolButton.qml and the buttons drawn as one
    // (the variants' «+» in the phase's header)
    readonly property real toolPad: Theme.space.XS + 1
    // the plan and the maps: a row's handle; the plan's drawn lines (as the Widgets' plan); the site's marker on the
    // plan's map (a disc with a thick ring) and on the site's map; the map's tiles (the tile servers' 256 px); the compass
    readonly property real planHandle: 16
    readonly property real planStroke: 1.6
    readonly property real planMarker: 18
    readonly property real planMarkerRing: 4
    readonly property real siteMarker: 14
    readonly property real mapTile: 256
    readonly property var compass: ({width: 56, height: 78})
    // the 3D view's square buttons (the view bar, the sun's bar)
    readonly property real viewButton: 27
    // the report's thin line of progress while it exports (an M.ProgressBar is Theme.space.S)
    readonly property real progressLine: 3
    // R476: the opening of every menu (Menu.qml): a fade with a slide of a few pixels, 140 ms with a soft end, at
    // most a seventh of it in one frame
    readonly property int menuReveal: 140
    readonly property real menuSlide: 6
    readonly property real menuStepMax: .15
    readonly property int tipEnter: 90
    readonly property int tipExit: 60
    // R550 (Daniel 08/11/2026: «continua ad esserci il problema del ritardo del tooltip: sul primo elemento lo rispetta,
    // nei successivi no»): every tooltip waits tipDelay on its control, the first and the next alike, as in Meridiana's
    // own rule and no longer as QToolTip (R468 had its wake-up: the next one at once while one was shown less than 2 s
    // before; R526 kept the list of those shown for it). Shown at once, it was also placed before the pointer had
    // reached its control, under the control instead of at the pointer.
    readonly property int tipDelay: 700
    // R550 (Daniel: «compare mai vicino al cursore, ma di solito vicino all'elemento che lo ha triggerato ma allo
    // stesso tempo a 5 millimetri da esso»): one place decides where a tooltip goes, and the plan's readout of the
    // tool in hand with it: at the pointer where it is when the tooltip appears, a little below and right of its tip
    // (tipBelow: under the arrow of the cursor at 100 %, tipRight from its point). Where the room ends on the right it
    // goes left of the pointer, at the bottom above it (tipAbove); always tipEdge inside the room.
    readonly property real tipRight: 2
    readonly property real tipBelow: 21
    readonly property real tipAbove: 4
    readonly property real tipEdge: Theme.space.S
    function besidePointer(at, width, height, room) {
        let x = at.x + tipRight, y = at.y + tipBelow
        if (x + width > room.x + room.width - tipEdge) x = at.x - tipRight - width
        if (y + height > room.y + room.height - tipEdge) y = at.y - tipAbove - height
        x = Math.max(room.x + tipEdge, Math.min(x, room.x + room.width - tipEdge - width))
        y = Math.max(room.y + tipEdge, Math.min(y, room.y + room.height - tipEdge - height))
        return Qt.point(x, y)
    }
    // The room `item` can show something in, in its own coordinates: its window, and with `clipped` cut by every item
    // above it that clips (the plan's readout is drawn inside its view; a tooltip, a popup, is not cut)
    function roomOf(item, clipped) {
        let room = null
        for (let node = item; node; node = node.parent) {
            if (!(node.parent === null || (clipped && node.clip))) continue
            const corner = item.mapFromItem(node, 0, 0), next = Qt.rect(corner.x, corner.y, node.width, node.height)
            if (!room) { room = next; continue }
            const left = Math.max(room.x, next.x), top = Math.max(room.y, next.y)
            room = Qt.rect(left, top, Math.max(0, Math.min(room.x + room.width, next.x + next.width) - left),
                           Math.max(0, Math.min(room.y + room.height, next.y + next.height) - top))
        }
        return room || Qt.rect(0, 0, item.width, item.height)
    }
    // R468: a tooltip says something the control does not show already: a description, a key. The same words as
    // the text the control shows add nothing, unless the text is cut. Case, spaces, the mnemonic's & and the final
    // full stop or ellipsis do not count.
    function words(text) {
        return String(text || "").replace(/&(?!&)/g, "").replace(/[\s.…:]+$/u, "").replace(/\s+/g, " ").trim().toLocaleLowerCase()
    }
    function tipAdds(tip, shown, cut) {
        return words(tip) !== "" && (cut === true || words(tip) !== words(shown))
    }
}
