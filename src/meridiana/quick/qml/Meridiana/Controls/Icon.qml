import QtQuick
import Meridiana.Theme
Item {
    id: root
    property string name: ""
    property alias iconName: root.name
    property bool inactive: false
    property bool dimDisabled: true
    // the provider's light or dark drawing (symbol:); a plan has its own (PlanSymbol), the theme's otherwise
    property bool dark: Theme.dark
    // an extra part of the provider's name: «round» draws a symbol on its enclosing centre (symbol:, R515)
    property string variant: ""
    property color color: enabled ? Theme.colors.text : Theme.disabledText
    implicitWidth: Theme.icon.CONTROL
    implicitHeight: implicitWidth
    Image {
        anchors.fill: parent
        source: root.name ? "image://meridiana/" + root.name + "/" + encodeURIComponent(root.color.toString())
                + "/" + (root.dark ? "dark" : "light") + "/" + (root.inactive || (root.dimDisabled && !root.enabled) ? "off" : "on")
                + (root.variant ? "/" + root.variant : "") : ""
        // Image applies the window DPR before asking the provider for pixels.
        sourceSize: Qt.size(width, height)
        fillMode: Image.PreserveAspectFit
    }
    Accessible.ignored: true
}
