import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
// R596 (Daniel 13/11/2026, study 47, variant D): the one «?» of the program, a full grey disc of Theme.icon.CONTROL
// with the «?» of the font, in a zone of ControlMetrics.helpMark that takes the click. One grey for the whole program
// (Theme.colors.help_disc); under the pointer and pressed it darkens with the house's state layers, never the accent;
// it stays pressed while its bubble is open. The keyboard's focus is the radio button's ring, round the disc. No line
// round the disc on any ground, the grey ones too (a section's band, a tile): Daniel 14/11/2026, «mi piace senza il
// bordino», for a more minimal look (it had a hair line on the grounds close to the disc, R596).
// A click opens the bubble of `helpKey` (Help.show); the tooltip is the key's short sentence (`tip` overrides it).
// Guard: tests/quick/sistema/test_simboli.py (no other «?» button, no other circle-question-mark). It was Lucide's
// circle-question-mark at 12 px in a flat button (R21, third slice), and before that R469's 16 px square.
T.AbstractButton {
    id: root
    readonly property bool helpMark: true     // how a test finds every help mark of a window
    property string helpKey: ""
    readonly property string helpId: helpKey      // the help key and «What's this?» on the mark itself (Workbench.helpFrom)
    property string tip: ""
    // where the bubble opens (Help.qml): "panel" over a section's title, "tile" under a tile, "card" under the
    // card's header, "field" beside a field
    property string helpPlace: "panel"
    readonly property bool shown: Help.mark === root
    readonly property string shownTip: tip !== "" ? tip : helpKey !== "" && typeof helpBook !== "undefined" && helpBook ? helpBook.tip(helpKey) : ""
    implicitWidth: ControlMetrics.helpMark
    implicitHeight: ControlMetrics.helpMark
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    Accessible.role: Accessible.Button
    Accessible.name: shownTip !== "" ? shownTip : "?"
    onClicked: if (helpKey !== "") Help.show(helpKey, root)
    Keys.onReturnPressed: root.clicked()
    Keys.onEnterPressed: root.clicked()
    background: Item {
        Rectangle {
            id: disc
            objectName: "helpDisc"
            width: Theme.icon.CONTROL; height: width; radius: width / 2
            // on whole device pixels of the window, as some renderers draw it anyway (see the «?» below)
            x: root.onPixel((parent.width - width) / 2, root.deviceAt.x)
            y: root.onPixel((parent.height - height) / 2, root.deviceAt.y)
            color: !root.enabled ? Theme.colors.help_disc : root.down || root.shown ? Theme.colors.help_disc_press
                 : root.hovered ? Theme.colors.help_disc_hover : Theme.colors.help_disc
        }
        // The «?» by its outline (Theme.glyphAxis), not by its advance: its dot on the disc's vertical axis. Qt may draw
        // a glyph from the device pixel under its origin and a rectangle on the nearest one (the software renderer
        // does, at every scale), so the disc and the glyph's origin both go on whole device pixels of the window, the
        // nearest to the ideal ones: with any renderer the dot then lands within half a device pixel of the axis, and
        // the sign stays sharp. `deviceAt` follows the mark on the window, frame by frame (a scroll, a layout),
        // because no property says where an item is in the window.
        Text {
            id: sign
            objectName: "helpSign"
            readonly property var glyph: Theme.glyphAxis(text, font.pixelSize, font.weight)
            text: "?"
            x: root.onPixel(disc.x + disc.width / 2 - glyph.axis, root.deviceAt.x)
            y: root.onPixel(disc.y + disc.height / 2 - (glyph.top + glyph.bottom) / 2 - baselineOffset, root.deviceAt.y)
            font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; font.weight: Theme.type.SEMIBOLD
            color: !root.enabled ? Theme.disabledText : root.hovered || root.down || root.shown ? Theme.colors.text : Theme.colors.help_ink
        }
        Rectangle {
            objectName: "helpFocus"
            anchors.centerIn: disc; width: Theme.icon.CONTROL + ControlMetrics.focusGrow; height: width; radius: width / 2
            visible: Theme.focusRing(root); color: "transparent"
            border.width: Theme.line.FOCUS; border.color: Theme.colors.focus
        }
    }
    contentItem: Item { }
    // the mark's corner on the window, in device pixels (see the «?» above), and a local position put on the nearest
    // whole device pixel of the window (a hair past it, so that no rounding of the sum drops it on the pixel before)
    property point deviceAt: Qt.point(0, 0)
    readonly property real dpr: Screen.devicePixelRatio
    function onPixel(local, origin) {
        return (Math.round(origin + local * dpr) - origin + ControlMetrics.pixelEpsilon) / dpr
    }
    function follow() {
        const at = root.mapToItem(null, 0, 0)
        const next = Qt.point(at.x * dpr, at.y * dpr)
        if (next.x !== deviceAt.x || next.y !== deviceAt.y) deviceAt = next
    }
    // only while it is seen (`visible` is false under any hidden ancestor): the marks of the pages kept alive but not
    // shown cost nothing per frame (measured 13/11/2026: 79 alive, 11 seen at most; about 290 us a frame for all of
    // them off screen, 40 for those seen)
    Component.onCompleted: follow()
    onVisibleChanged: if (visible) follow()
    Connections { target: root.Window.window; enabled: root.visible; function onAfterAnimating() { root.follow() } }
    ToolTip { objectName: "controlTip"; parent: root; text: root.shownTip; visible: root.hovered && root.shownTip !== "" && !root.shown }
}
