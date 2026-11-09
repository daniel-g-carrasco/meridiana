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
    readonly property var text: themeTokens.text
    readonly property var tokens: themeTokens.tokens
    readonly property string fontFamily: themeTokens.fontFamily
    readonly property string barFontFamily: themeTokens.barFontFamily
    readonly property bool dark: themeTokens.dark
    readonly property bool reducedMotion: themeTokens.reducedMotion
    readonly property string textSize: themeTokens.textSize
    readonly property int revision: themeTokens.revision

    function configure(options) {
        themeTokens.configure(options)
    }

    function tooltipLayout(text) {
        const currentRevision = root.revision
        return themeTokens.tooltipLayout(text)
    }

    function mix(a, b, share) {
        return Qt.rgba(a.r + (b.r-a.r)*share, a.g + (b.g-a.g)*share,
                       a.b + (b.b-a.b)*share, a.a + (b.a-a.a)*share)
    }

    function measureText(text, style, condensed) {
        // Reading revision makes callers' bindings follow font and size changes.
        const currentRevision = root.revision
        return themeTokens.measureText(text, style || "body", condensed || false)
    }
}
