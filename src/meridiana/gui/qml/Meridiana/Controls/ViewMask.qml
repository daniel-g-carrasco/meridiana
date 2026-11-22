import QtQuick
import Meridiana.Theme

// The batched selection's raster membership, outlined with the common view style.
ShaderEffect {
    property variant source
    property color ink: Theme.colors.overlay.pill_ink
    property color halo: Qt.rgba(0, 0, 0, Theme.annotation.HALO_ALPHA)
    property vector2d pixelStep: Qt.vector2d(1/Math.max(1,width),1/Math.max(1,height))
    property real halfStroke: Theme.annotation.STROKE / 2
    property real haloReach: (Theme.annotation.STROKE + Theme.annotation.HALO_EXTRA) / 2
    property real fillOpacity: 0
    fragmentShader: "../Plan/selection.frag.qsb"
}
