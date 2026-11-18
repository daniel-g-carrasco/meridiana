import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// ui/plant_page.MarginBar (study 23, E and F): a figure against its limit as a bar, the label at the left, a track as
// long as the limit, the span in the state's colour, the figures at the right.
Item {
    id: root
    required property var observation
    required property var colors
    FontMetrics { id: small; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
    implicitHeight: Math.ceil(small.lineSpacing) + Theme.space.XS
    M.Label { id: label; width: 40; height: parent.height; text: root.observation.label; textStyle: "secondary"; color: Theme.colors.muted }
    M.Label { id: value; anchors.right: parent.right; height: parent.height; text: root.observation.text; textStyle: "secondary"; color: Theme.colors.text }
    Rectangle { id: track; x: 40; y: (parent.height - 6) / 2; width: Math.max(0, parent.width - 40 - value.implicitWidth - 2 * Theme.space.S)
        height: 6; radius: 3; color: Theme.colors.line; opacity: .35 }
    Rectangle { x: track.x + track.width * root.observation.low; y: track.y
        width: Math.max(3, track.width * (root.observation.high - root.observation.low)); height: 6; radius: 3
        visible: track.width > 0; color: root.colors[root.observation.state] || Theme.colors.accent }
    HoverHandler { id: hover }
    M.ToolTip { visible: hover.hovered; text: root.observation.label + " " + root.observation.text }
}
