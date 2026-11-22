pragma Singleton
import QtQuick
import Meridiana.Theme
QtObject {
    // The first line's painted middle, also for a wrapped caption or a replacement contentItem.
    // baselineOffset belongs to the live text, so its padding and vertical alignment are included.
    function firstLineMiddle(words) {
        const width = words.width - (words.leftPadding || 0) - (words.rightPadding || 0)
        const ink = Theme.textBlockInk(words.text, width, words.textStyle, words.condensed || false)
        return words.y + words.baselineOffset + (ink.top + ink.firstBottom) / 2
    }
    function textMiddleOffset(words) {
        const ink = Theme.textBlockInk(words.text, words.width, words.textStyle, words.condensed)
        return words.baselineOffset + (ink.top + ink.bottom) / 2
    }
    // R502: the margin between a container's edge and what is inside it, the same on every side that has one: the
    // phase tab around its number's disc and its name (the disc is as far from the tab's top, (32 - 20) / 2), the
    // hover of a tab around the same, the card of the bar of the tools around its first tool and the summary at its
    // right. The compact tracks keep their own, already the same on every side: the plan's view bar 3 (ViewBar.qml),
    // the segments 2 (Segments.qml).
    readonly property real inset: Theme.space.S
    // R582 (Daniel 11/11/2026: «ci sono dei problemi nel centramento del testo in queste caselle di input… vorrei che
    // questi elementi siano generalizzati e comuni»): the one line of text in a field (M.TextField and the controls made
    // on it, M.NumberField and its unit, M.ComboBox, the hint of an empty field, M.OverlayField) stands with its
    // capitals and digits on the field's middle, at every size of the text: the baseline at (height + cap height) / 2,
    // on a whole pixel of the screen (dpr: the item's Screen.devicePixelRatio, 1 when not given). Qt's AlignVCenter centres the line's box (ascent and descent), which put the hint of an empty
    // field 1.5 px over the text of a filled one. The text starts fieldInset from the field's left edge in all of them
    // (the combo and the number started 2 px before the text field).
    readonly property real fieldInset: Theme.space.M + 2
    // R592 (Daniel 11/11/2026, «due segni, due significati»): the full arrow of what chooses a value (M.Arrow), rows
    // of whole pixels, arrowDepth deep, in a box 2 x arrowDepth wide: 4 keeps the box whole pixels at every quarter of
    // scale (the triangle is 7 x 4 at 100 %); the open arrow of what opens a section (M.Chevron), the project tree's
    // drawing on its chevronBox
    readonly property int arrowDepth: 4
    readonly property real chevronBox: 20
    // where a drawing goes so that it starts on a whole pixel of the screen: `local` in its item, the item at `scene`
    // in the window (mapToItem(null, 0, 0)), dpr the screen's ratio. A drawing of whole pixels started half a pixel
    // off is either blurred or one pixel lopsided (at 125 % the full arrow's rows fell one on each side).
    function pixelSnap(scene, local, dpr) {
        return (Math.round((scene + local) * dpr) - scene * dpr) / dpr
    }
    function textBaseline(height, metrics, dpr) {
        const ratio = dpr > 0 ? dpr : 1
        return Math.round((height + metrics.tightBoundingRect("H").height) / 2 * ratio) / ratio
    }
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
    // R628 (Daniel 15/11/2026, the catalogue: «non posso ridimensionarlo, e inoltre me lo fa spostare solo all'interno
    // di un ristrettissimo range di movimento»): a window moves anywhere over the program's window and may pass its
    // sides, but always keeps dialogHold of its head inside it on every side (its head never above the top), so it can
    // be taken again; its sides and corners take the pointer dialogGrip deep inside its frame (the corners twice as
    // much), within the margin dialogPad, clear of the controls and of the body's scroll bar, centred in that margin
    // (the bar's lane 10 in 16 leaves 3 a side, its thumb narrower: the grip of 6 touches the lane, not the thumb).
    // Made smaller by hand it keeps its head, its foot and dialogLeast.body of its body (the body scrolls), and at least
    // dialogLeast.width or its row of buttons
    readonly property real dialogHold: 2 * Theme.size.CONTROL
    readonly property real dialogGrip: Theme.space.S
    readonly property var dialogLeast: ({width: dialogWidth.narrow, body: 3 * Theme.size.CONTROL})
    // R607: the column of a job's phase in its row (M.WorkRow): fixed, so the bar and the percentage stay where they are
    // when the phase changes; in the import's window (680) it leaves the bar about twice Theme.size.PROGRESS
    readonly property real workPhase: 200
    // R607: the thread of a job's progress (M.ProgressBar), as thick as the focus' line; the words above it (M.WorkRow)
    // stand this far from it
    readonly property real progressThread: Theme.line.FOCUS
    readonly property real progressGap: Theme.space.XS
    // R607: the parts the windows of File drew with numbers of their own, the same numbers: the IFC model's preview and
    // a Revit file's, the label column of what was read, the canopy's form beside its preview (and the preview's sizes)
    readonly property var dialogParts: ({ifcPreview: 220, rvtPreview: 128, factLabel: 96, sideForm: 340,
                                         geometry: {width: 320, height: 240, least: 300}})
    readonly property var dialogWidth: ({narrow: 420, normal: 560, wide: 720, page: 1200})
    // R586: the windows that ask a size of their own (M.Dialog's implicitWidth and implicitHeight; a height of 0 is
    // their content's), each under its name, the same numbers they wrote before; `file` the windows of File by kind
    // (Dialogs/DialogWindow.qml, [width, height])
    readonly property var dialogSize: ({dxf: {width: 600}, mapKey: {width: 480}, relayout: {width: 440},
        placeOverlap: {width: 520}, placeCoordinates: {width: 560}, mapSources: {width: 920, height: 800},
        pvsystReview: {width: 600}, catalog: {width: 1280, height: 820}, storage: {width: 620, height: 720},
        sizing: {width: 420}, groups: {height: 540}, datasheet: {width: 660, height: 640}, variant: {width: 520},
        message: {width: 640}, compare: {width: 900, height: 660}, sceneRename: {width: 360}, fileCatalog: {height: 800},
        file: {shortcuts: [640, 560], update: [520, 0], pvsyst: [720, 0], ifc: [680, 0], template: [344, 590],
               canopy: [760, 548], "canopy-layout": [440, 0], site: [640, 600], report_bug: [640, 640], about: [560, 0],
               registry: [720, 640], new: [720, 640], other: [720, 0]}})
    // R520 (Daniel 07/11/2026: «nelle tabelle e nella scelta inverter succede che la barra per lo scrolling si
    // sovrapponga ai contenuti»): the scroll bar's lane, at the right of every list, table and page that scrolls: the
    // content ends before it, the bar is drawn in it and never over a text or a column. Its width is the bar's room of
    // R100 (Theme.size.SCROLLBAR), the gap between the content's end and the lane scrollGap.
    readonly property real scrollLane: Theme.size.SCROLLBAR
    readonly property real scrollGap: Theme.space.XXS
    // R654: how far a notch of the wheel (15 degrees) scrolls a list when the pointer is over its scroll bar: what Qt's
    // Flickable does over its content (measured 15/11/2026, Qt 6.12: 72 px)
    readonly property real wheelNotch: 72
    // R631 (Daniel 15/11/2026: «come mai i margini della scheda destra, con il posizionamento della barra di
    // scorrimento, sono molto diversi da quella in Impianto? dove sarebbe l'armonizzazione e la centralizzazione
    // richiesta?»): the body of every side panel is one M.PanelPage, the one scroll of the panel with its bar at the
    // card's right, panelGap between two sections (as Properties).
    // R637 (Daniel 15/11/2026: «non mi piace che il margine sotto e sopra, e i margini laterali non siano della stessa
    // dimensione, preferisco l'approccio salvaspazio del margine basso. Anche nelle altre schede»): every docked card
    // (Shell/DockPanel.qml: the side panels, Project, Checks) keeps cardMargin between its border and what it holds, on
    // the four sides; at the top from its head's row. Until R637 the side panels had 22 at the sides, 11 under the head
    // and 14 at the foot (8 of the card and 6 of the page's air), Project 12 / 11 / 238 rows / 6, Checks 17 / 47 / 26 /
    // 14: the foot's 14 is no step of Theme.space, so the step under it, 12. The scroll bar of what fills a card stands
    // in the margin at its right, as wide as the margin (where the pointer takes it), its thumb centred
    // (M.ScrollBar.inMargin).
    // R704 (Daniel 17/11/2026: «non era meglio ampliare l'aria di 1 px?», «pixel d'aria ok»): the card's own line takes
    // the outermost HAIR of the margin, so the margin is Theme.space.L of air plus that line: 12 of air on the four
    // sides, and the scroll bar's thumb (4 at rest, 6 under the pointer) centred in it at every scale (1, 1,25, 2, 2,5)
    readonly property real cardMargin: Theme.space.L + Theme.line.HAIR
    // R655 (Daniel 15/11/2026, the thumb in the cards' margin, variant 3 of his board: «anche la 3 è carina e il suo
    // stesso ingrandimento è un hover»): marginThumb wide at rest, marginThumbHover under the pointer and while
    // dragged, centred in the margin (4 and 4, then 3 and 3); the same two numbers give his variant 2 (4 always).
    // Since the kit (Daniel 20/11/2026, «la barra come GNOME, ovunque uguale»): every bar so, 4 at rest and 8 under
    // the pointer on its lane, as GNOME's overlay bar (3 and 8 there: 4 keeps the thumb on whole pixels)
    readonly property real marginThumb: Theme.space.XS
    readonly property real marginThumbHover: Theme.space.M
    readonly property real panelGap: Theme.space.S
    // R633: the heads of a side panel's sections held at the top of its page while it scrolls take at most this share
    // of the page's height, and those held at the bottom as much (HeldHeads.qml): the content always has the rest
    readonly property real heldShare: 1 / 4
    // R525 (Daniel 07/11/2026: «l'hover nel menu a comparsa nella stringatura automatica non è quello grigio con angoli
    // arrotondati che c'è altrove… centralizza il centralizzabile»): every list that drops (M.Menu, M.ComboBox and the
    // controls made on it, the catalogue's makers, Meridio's selector) has one entry, M.MenuItem: the hover's grey with
    // menuItemRadius, menuPad from the popup's sides, the same height; the current choice of a combo is its check.
    readonly property real menuPad: Theme.space.XS
    readonly property real menuItemRadius: Theme.radius.INNER
    readonly property real menuItemPadV: Theme.space.S
    // R662 (Daniel 15/11/2026, the plan's menu: «guarda quanto spazio rimane a destra di "propose inverters...". Rimane
    // quasi attaccato al bordo, quando a sinistra ci sono 5mm!!»): one margin from the menu's side to what an entry
    // shows, the same at the left (to the mark, or to the text when no entry of the menu has a mark) and at the right
    // (from the widest entry's last ink: its text, its key or its submenu's arrow). menuItemPadH is what of it lies
    // inside the hover's grey, which stands menuPad off the sides.
    readonly property real menuInset: Theme.space.L
    readonly property real menuItemPadH: menuInset - menuPad
    // a row of a tree or a list (the kit, 20/11/2026): a menu entry's shape, menuPad in from the sides with its radius,
    // chosen in select_bg and lit in hover under the pointer; the tables keep their band across the columns
    readonly property real rowInset: menuPad
    // The edges (the kit, Daniel 21/11/2026): what a body holds stands on its two lines, cardMargin in from the border,
    // also the lit row of a list or a tree without a frame of its own (rowGround); the words start rowPad in from it.
    readonly property real rowPad: rowInset + Theme.space.S
    readonly property real scrollBreath: Theme.space.S
    // The shadow at the closed edges of what scrolls (EdgeFades.undershoot, the kit): level 0 is libadwaita 1.8, 1 and 2
    // more marked; Daniel 21/11/2026: level 1
    readonly property int shadeLevel: 1
    readonly property real shadeStrength: [1, 1.8, 2.6][shadeLevel]
    readonly property real shadeDepth: [4, 6, 8][shadeLevel]
    function rowGround(framed) { return framed ? rowInset : 0 }
    readonly property real rowRadius: menuItemRadius
    function rowFill(chosen, hovered, enabled) {
        return chosen ? Theme.colors.select_bg : hovered && enabled ? Theme.colors.hover : "transparent"
    }
    // R662: the column of the marks, reserved to every entry of a menu as soon as one has an icon or a check, and the
    // room between the text and the column at the right (the keys, or the submenu's arrow)
    readonly property real menuCheck: Theme.space.L
    readonly property real menuColumnGap: Theme.space.XXL
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
    // R636: the most lines a field that grows with its text (M.GrowingField) takes before its text scrolls inside it
    readonly property int growLines: 6
    readonly property real selectorRoom: 26
    // the least a page's column of File and of the Settings takes when it gives Meridio his room in a narrow window
    // (File/FilePage.qml, freeSide): a reading column (Theme.size.READING, about 70 characters at 13 px), the width of
    // the texts of those pages; narrower, it keeps its width and he stands over its edge
    readonly property real pageLeast: Theme.size.READING
    // Meridio's figure, floating over the window
    readonly property real figure: Theme.size.FIGURE        // R642: app/assistant/figure.SIZE
    // a check's row: one line, as the row of ui/checks_page.py (the rest in the tooltip); a level's mark and its count
    readonly property real checkRow: 34
    readonly property real markGap: 3
    // a check's mark on the views (the plan, the 3D view): the symbol with its thin white edge (symbols.paint_view),
    // the symbol about 18 of it; the same in PlanSymbol and in the 3D's CheckMark (Daniel 14/11/2026: no disc round it)
    readonly property real viewMark: 20
    // the project tree's row: its name and its marks
    readonly property real treeGap: 7
    // R637: how far each level of the project tree goes in from the one before (the first level at the card's
    // margin); Theme.space.L as the kit's tree (form E, Daniel 20/11/2026), before the arrow's box (20)
    readonly property real treeIndent: Theme.space.L
    // the column of a group's arrow, before the icons and the names
    readonly property real treeArrow: Theme.space.XL
    // R665: the fewest characters of a name the project tree shows before its value (with the dots); fewer fit, the
    // name goes and the value stays alone
    readonly property int treeNameLeast: 3
    // the one help mark (HelpMark.qml, R596): the zone that takes the click, round its disc of Theme.icon.CONTROL
    readonly property real helpMark: 20
    // the focus ring round a small indicator (CheckBox, RadioButton, HelpMark): its size over the indicator's. R555 (7)
    // (Daniel 09/11/2026: «l'evidenziatura del quadratino non è centrata»): even, so that the ring stands the same whole
    // pixels from the indicator on every side (5 left it 2.5 px away, a half pixel that fell one side or the other)
    readonly property real focusGrow: 6
    // a position put on a whole device pixel goes this far past it, so that no rounding of the sum drops it on the
    // pixel before (HelpMark's disc and «?»: 1/64 of a device pixel, nothing that can be seen)
    readonly property real pixelEpsilon: 1 / 64
    // the help bubble (HelpBubble.qml, R597): its width, the text's lines at most (help.py: 350 characters), the
    // pointer's side (a square turned by 45 degrees, its half out of the frame)
    readonly property real helpBubble: 264
    // R650: the room round the buttons at the bubble's foot («Manual», «Ask Meridio»): from the line above, the foot and
    // the left side, the same
    readonly property real helpFoot: Theme.space.XS
    readonly property int helpLines: 8
    readonly property real pointer: 10
    // a tool button's padding around (above and below Theme.space.XXS): ToolButton.qml and the buttons drawn as one
    // (the variants' «+» in the phase's header)
    readonly property real toolPad: Theme.space.XS + 1
    // the plan and the maps: a row's handle; the plan's drawn lines (as the Widgets' plan); the site's marker on the
    // plan's map (a disc with a thick ring) and on the site's map; the map's tiles (the tile servers' 256 px); the compass
    readonly property real planHandle: 16
    readonly property real planStroke: Theme.annotation.STROKE
    readonly property real planMarker: 18
    readonly property real planMarkerRing: 4
    readonly property real siteMarker: 14
    // the dashes of the plan's guides (ToolOverlay, the measures)
    readonly property var planDash: [Theme.annotation.DASH_ON / Theme.annotation.STROKE, Theme.annotation.DASH_OFF / Theme.annotation.STROKE]
    // Shared by drawing previews and measurements, in logical screen pixels.
    readonly property real planDrawStroke: Theme.annotation.STROKE
    readonly property real planDrawHalo: Theme.annotation.HALO_EXTRA
    // the measuring tool (study 46, Measure/MeasureLayer.qml): its spans as the plan's line being drawn
    // (view_colours.WIDTHS "measure" over its "halo"); the mark of a point, a little larger than the drawing's corner
    // square (8) so that its shape tells what it snapped to (square, triangle, hourglass, circle, rhombus)
    readonly property real measureLine: planDrawStroke
    readonly property real measureHalo: planDrawHalo
    readonly property real measureMark: Theme.annotation.POINT
    // the measures' references, never a measure (the height's source, the pointer off the axis it keeps to): a thin
    // dotted line in the guides' colour, so that the dashed span (the measure in hand) and the solid one (made) are
    // the only lines that measure; in strokes of planStroke, a dot and a gap two and a half times as long
    readonly property var measureDots: planDash
    // R609: a measure's number written along its span (Controls/SpanLabel.qml), as a dimension of a drawing: clear of
    // the span's halo by two pixels, no more (so it reads as the span's)
    readonly property real measureTextGap: Theme.annotation.LABEL_GAP - (Theme.annotation.LABEL_SIZE + 3) / 2
    // R618: where the words of the measures go (Controls/LabelPlace.js, words and totals), in the screen's pixels. A
    // word on its span keeps measureWordMargin from each end (the same air as the pills, and clear of the marks: half a
    // mark and a hair); out of its span only on a span at least measureWordOutMin long (two marks: shorter, the marks
    // touch and there is no line to read the word with); a word changes place measureWordHysteresis past the limit,
    // so that it does not flicker at the limit while zooming. A hidden word leaves a stroke measureSign long across its
    // span; the pointer within measureHover of the span (or of the path's end, for a total) shows the number.
    readonly property real measureWordMargin: Math.max(Theme.space.S, measureMark / 2 + Theme.space.XXS)
    readonly property real measureWordOutMin: 2 * Theme.annotation.HIT_POINT
    readonly property real measureWordHysteresis: Theme.space.XS
    readonly property real measureSign: Theme.space.M
    readonly property real measureHover: Theme.space.L
    readonly property real mapTile: 256
    // R643: the sign of North over a view (Controls/NorthSign.qml, proposal A): the needle on a disc of northSign, and
    // in the plan the degrees under it in a pill of northPill (Space.XS between), only while the view is turned
    readonly property real northSign: 40
    readonly property real northPill: 18
    readonly property var compass: ({width: northSign, height: northSign + Theme.space.XS + northPill})
    // the view cube of the 3D view, one compact size since 16/11/2026 (it was 76 or 112)
    readonly property real viewCube: 76
    // the 3D view's square buttons (the view bar, the sun's bar)
    readonly property real viewButton: 27
    readonly property real viewArrow: Theme.space.XL
    readonly property real viewPlainWidth: 19 + 2 * Theme.space.S
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
    // R555 (Daniel 14/11/2026: «il suggerimento della voce si apre sopra il menu e ne copre il bordo»): the tooltip of a
    // menu's entry goes outside the menu, as a submenu does: beside its frame on the right, tipGap off it, its top at
    // the entry's top; on the left of the frame where the room ends on the right. Only the entries of a menu: at the
    // pointer (besidePointer) it covered the menu's side and the entries below. `frameAt` is the frame's corner in
    // the entry's coordinates, `room` roomOf(entry); the answer in the entry's coordinates.
    readonly property real tipGap: Theme.space.XS
    function besideMenu(frameAt, frameWidth, width, height, room) {
        let x = frameAt.x + frameWidth + tipGap
        if (x + width > room.x + room.width - tipEdge) x = frameAt.x - tipGap - width
        x = Math.max(room.x + tipEdge, Math.min(x, room.x + room.width - tipEdge - width))
        const y = Math.max(room.y + tipEdge, Math.min(0, room.y + room.height - tipEdge - height))
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
