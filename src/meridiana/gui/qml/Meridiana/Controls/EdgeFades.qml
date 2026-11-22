import QtQuick
import Meridiana.Theme
// The soft ends of every area that scrolls (R624, Daniel 15/11/2026: «la sfumatura deve essere una trasparenza
// gradiente del contenuto», «mantenerla ben centralizzata»): near an edge with more content beyond it, what scrolls
// becomes transparent and what lies under the area shows through. One rule for any content: the rows on their card,
// the white sheet of the report in the dark theme, a page of text. Until R624 a band of one colour (the ground
// guessed above the area) was painted over the content: a darker strip over the Checks' rows on the card colour and a
// dark band on the report's sheet, cut by the edge in between (edgefade.frag has the curve: smoothstep, no kink).
// Placed by M.ScrollPage, M.List, M.Tree, M.Table, M.Dialog and every vertical M.ScrollBar; never by hand
// (tests/quick/sistema/test_sfumature_r624.py).
// History kept: R161 never over a card's border or bar (the dissolve is inside the viewport, the bar's lane `barRoom`
// left whole), R177 nothing whole at the edge, R192 short, R590 as tall as what has gone past the edge, whole at the
// edge from the first pixel.
// The dissolve is a layer of the flickable with a small shader, on only while the content goes beyond the area. Qt's
// software renderer (off screen, the tests) draws no shader: there the content stays whole, without dissolve.
Item {
    id: root
    objectName: "edgeFades"
    property Flickable flickable
    // the bar's lane inside the flickable, at its right: left whole
    property real barRoom: 0
    // R633: the heads held at the edges of the area (HeldHeads.qml, M.ScrollPage of a panel): the content under them is
    // not drawn, and it dissolves from their edge (topInset, bottomInset), no taller than they allow (topRoom,
    // bottomRoom: the content gone under them, never over a head in its place)
    property Item held: null
    anchors.fill: flickable
    // The template's kit (Daniel 21/11/2026, the final choice, «approccio ibrido»): the shadow only where the sides are
    // closed (a table, a list or a tree in its frame: spansSurface false), as GNOME's undershoot (libadwaita: a 6 px
    // gradient and an unblurred 1 px line, shade_color at level 1, ControlMetrics.shadeLevel); everywhere else (pages,
    // panels, Settings, dialogs) the dissolve above.
    property bool spansSurface: true
    readonly property bool undershoot: !spansSurface
    readonly property color shade: Theme.dark ? Qt.rgba(0, 0, 0.024, Math.min(1, 0.25 * ControlMetrics.shadeStrength))
                                              : Qt.rgba(0, 0, 0.024, 0.07 * ControlMetrics.shadeStrength)
    readonly property real band: flickable !== null ? Math.max(0, Math.min(Theme.size.FADE, Math.floor(flickable.height / 5))) : 0
    readonly property real above: flickable !== null ? flickable.contentY - flickable.originY : 0
    readonly property real below: flickable !== null ? flickable.originY + flickable.contentHeight - flickable.contentY - flickable.height : 0
    readonly property real topInset: held !== null ? held.topInset : 0
    readonly property real bottomInset: held !== null ? held.bottomInset : 0
    // the heights of the two dissolves: as tall as the content gone past the edge, up to the band
    readonly property real topBand: Math.max(0, Math.min(band, above, held !== null ? held.topRoom : band))
    readonly property real bottomBand: Math.max(0, Math.min(band, below, held !== null ? held.bottomRoom : band))
    readonly property bool drawn: GraphicsInfo.api !== GraphicsInfo.Software && GraphicsInfo.api !== GraphicsInfo.Unknown
    // the content goes beyond the area: the layer is on only then (one surface the size of the area)
    readonly property bool active: drawn && flickable !== null && band > 0 && (above > 0 || below > 0)
    Binding { target: root.flickable; property: "layer.effect"; value: dissolve; when: root.flickable !== null }
    Binding { target: root.flickable; property: "layer.enabled"; value: root.active && !root.undershoot; when: root.flickable !== null }
    component Undershoot: Item {
        id: shadow
        required property bool atTop
        readonly property real depth: ControlMetrics.shadeDepth
        readonly property bool overflow: atTop ? root.above > 0 : root.below > 0
        readonly property real room: root.held === null ? root.height : atTop ? root.held.topRoom : root.held.bottomRoom
        width: Math.max(0, root.width - root.barRoom)
        height: Math.max(0, Math.min(depth, root.height / 2, room))
        y: atTop ? root.topInset : root.height - root.bottomInset - height
        // GTK draws the whole undershoot as soon as the content leaves its limit
        opacity: root.undershoot && root.flickable !== null && overflow && height > 0 && width > 0 ? 1 : 0
        visible: opacity > 0
        clip: height < depth
        Rectangle {
            width: shadow.width; height: shadow.depth
            y: shadow.atTop ? 0 : shadow.height - height
            gradient: Gradient {
                GradientStop { position: 0; color: shadow.atTop ? root.shade : "transparent" }
                GradientStop { position: 1; color: shadow.atTop ? "transparent" : root.shade }
            }
        }
        Rectangle { width: parent.width; height: Math.min(1, parent.height); y: shadow.atTop ? 0 : shadow.height - height; color: root.shade }
    }
    Undershoot { objectName: "topUndershoot"; atTop: true }
    Undershoot { objectName: "bottomUndershoot"; atTop: false }
    Component {
        id: dissolve
        ShaderEffect {
            objectName: "edgeDissolve"
            readonly property size area: Qt.size(width, height)
            readonly property real topBand: root.topBand
            readonly property real bottomBand: root.bottomBand
            readonly property real room: root.barRoom
            readonly property real topInset: root.topInset
            readonly property real bottomInset: root.bottomInset
            fragmentShader: "edgefade.frag.qsb"
        }
    }
}
