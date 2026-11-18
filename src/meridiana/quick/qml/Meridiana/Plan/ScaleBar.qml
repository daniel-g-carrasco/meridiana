import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M

// The scale in the plan's pill of its corners (R511, ViewPill): the coordinates beside it are in the same one.
M.Pill {
    id: root
    variant: "view"
    property real metresPerPixel: 0.1
    property real longest: 120
    readonly property real most: Math.max(1e-10, metresPerPixel) * longest
    readonly property real magnitude: Math.pow(10, Math.floor(Math.log10(most)))
    readonly property real length: (most / magnitude >= 5 - 1e-9 ? 5 : most / magnitude >= 2 - 1e-9 ? 2 : 1) * magnitude
    readonly property real pixels: length / Math.max(1e-10, metresPerPixel)
    readonly property string text: length < 1 ? (length * 100).toLocaleString(Qt.locale(), "f", 0) + " cm" :
                                  length >= 1000 ? (length / 1000).toLocaleString(Qt.locale(), "f", length % 1000 === 0 ? 0 : 1) + " km" :
                                  length.toLocaleString(Qt.locale(), "f", 0) + " m"
    readonly property real barY: height / 2 + 3
    readonly property string barPath: "M" + pad + "," + barY + " L" + (pad + pixels) + "," + barY +
                                     " M" + pad + "," + (barY - 6) + " L" + pad + "," + (barY + .8) +
                                     " M" + (pad + pixels) + "," + (barY - 6) + " L" + (pad + pixels) + "," + (barY + .8)
    width: Math.round(2 * pad + pixels + Theme.space.S + label.implicitWidth)
    Shape {
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: Theme.colors.overlay.glass_line
            strokeWidth: 3.6
            capStyle: ShapePath.FlatCap
            fillColor: "transparent"
            PathSvg { path: root.barPath }
        }
        ShapePath {
            strokeColor: root.ink
            strokeWidth: 1.6
            capStyle: ShapePath.FlatCap
            fillColor: "transparent"
            PathSvg { path: root.barPath }
        }
    }
    Text {
        id: label
        x: root.pad + root.pixels + Theme.space.S
        height: parent.height
        text: root.text
        verticalAlignment: Text.AlignVCenter
        color: root.ink
        font: root.font
    }
}
