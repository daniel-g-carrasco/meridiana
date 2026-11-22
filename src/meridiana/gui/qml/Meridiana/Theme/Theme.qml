pragma Singleton
import QtQuick

QtObject {
    id: root
    readonly property color disabledText: themeTokens.disabledText
    readonly property var colors: themeTokens.colors
    readonly property var options: themeTokens.options
    readonly property var status: themeTokens.status
    readonly property var space: themeTokens.space
    readonly property var radius: themeTokens.radius
    readonly property var type: themeTokens.type
    readonly property var size: themeTokens.size
    readonly property var line: themeTokens.line
    readonly property var motion: themeTokens.motion
    readonly property var layout: themeTokens.layout
    readonly property var bar: themeTokens.bar
    readonly property var icon: themeTokens.icon
    readonly property var stack: themeTokens.stack       // R616: what stands over what (design.Stack)
    readonly property var highlight: themeTokens.highlight      // R617: every highlight's one scale (design.Highlight)
    readonly property var annotation: themeTokens.annotation
    readonly property var text: themeTokens.text
    readonly property var signs: themeTokens.signs      // R643: the signs' drawings shared with the report
    readonly property var tokens: themeTokens.tokens
    readonly property string fontFamily: themeTokens.fontFamily
    readonly property string barFontFamily: themeTokens.barFontFamily
    readonly property bool dark: themeTokens.dark
    readonly property bool reducedMotion: themeTokens.reducedMotion
    // the change of phase animated: the setting «phase_animations» (off by default), never with reducedMotion
    readonly property bool phaseMotion: themeTokens.phaseMotion
    readonly property string textSize: themeTokens.textSize
    // the density of the trees and lists and the air of their rows (design.Rows, the kit 20/11/2026)
    readonly property string density: themeTokens.density
    readonly property real rowAir: themeTokens.rowAir
    readonly property int revision: themeTokens.revision

    function configure(options) {
        themeTokens.configure(options)
    }

    // R586 (c): a modal window's veil shown or gone (Controls/ModalVeil.qml), for the title bar
    function veil(on, colour) {
        if (themeTokens.veil !== undefined) themeTokens.veil(on, colour)
    }

    function tooltipLayout(text) {
        const currentRevision = root.revision
        return themeTokens.tooltipLayout(text)
    }

    function mix(a, b, share) {
        return Qt.rgba(a.r + (b.r-a.r)*share, a.g + (b.g-a.g)*share,
                       a.b + (b.b-a.b)*share, a.a + (b.a-a.a)*share)
    }

    // The one rule of the focus ring (Daniel 14/11/2026: «compare solo quando ci si arriva con la tastiera»): shown only
    // while the keyboard brought the focus there (Tab, Shift+Tab, a shortcut), never after a click, which leaves a
    // control told by its own state (pressed, checked, chosen, the caret). Every ring and field border in
    // Theme.colors.focus asks here, with the focusReason of a Control or a field, or the one an item declares
    // (PlantInverterCard); guard: tests/quick/controlli/test_anello_tastiera.py.
    function focusRing(item) {
        if (!item || !item.enabled || !item.activeFocus) return false
        const reason = item.focusReason
        return reason === Qt.TabFocusReason || reason === Qt.BacktabFocusReason || reason === Qt.ShortcutFocusReason
    }

    // R596: where a sign's ink stands in the font (ThemeTokens.glyphAxis): the middle of its lowest piece, its top, its bottom
    function glyphAxis(text, size, weight) {
        const currentRevision = root.revision
        return themeTokens.glyphAxis(text, size, weight)
    }
    function textBlockInk(text, width, style, condensed) {
        const revision = root.revision
        return themeTokens.textBlockInk(text, width, style || "body", condensed || false)
    }

    function measureText(text, style, condensed) {
        // Reading revision makes callers' bindings follow font and size changes.
        const currentRevision = root.revision
        return themeTokens.measureText(text, style || "body", condensed || false)
    }
}
