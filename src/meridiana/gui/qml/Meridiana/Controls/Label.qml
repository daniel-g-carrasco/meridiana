import QtQuick
import Meridiana.Theme
Text {
    property string textStyle: "body"
    property bool condensed: false
    readonly property var spec: Theme.text[textStyle] || Theme.text.body
    font.family: condensed ? Theme.barFontFamily : Theme.fontFamily
    font.pixelSize: spec.size
    font.weight: spec.weight
    font.capitalization: spec.caps ? Font.AllUppercase : Font.MixedCase
    font.letterSpacing: spec.caps ? spec.size * Theme.type.LETTER_SPACING / 100 : 0
    color: enabled ? Theme.colors[spec.tone] : Theme.disabledText
    renderType: Text.NativeRendering
    textFormat: Text.PlainText
    verticalAlignment: Text.AlignVCenter
    Accessible.role: Accessible.StaticText
    Accessible.name: text
}
