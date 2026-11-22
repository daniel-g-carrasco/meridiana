import QtQuick
import QtQuick3D
import Meridiana.Theme

// The native 3D counterpart of ViewStroke: one ink pass over the same light halo.
Node {
    id: ribbon
    property var geometry: null
    property real pixelSize: 1
    property color ink: Theme.colors.overlay.pill_ink
    property int haloCull: Material.NoCulling
    property string haloName: ""
    Model {
        objectName: ribbon.haloName
        geometry: ribbon.geometry
        castsShadows: false; receivesShadows: false
        materials: CustomMaterial {
            shadingMode: CustomMaterial.Shaded
            cullMode: ribbon.haloCull
            sourceBlend: CustomMaterial.SrcAlpha
            destinationBlend: CustomMaterial.OneMinusSrcAlpha
            property real ribbonWidth: Theme.annotation.STROKE + Theme.annotation.HALO_EXTRA
            property real pixelSize: ribbon.pixelSize
            property vector4d ribbonColor: Qt.vector4d(0,0,0,Theme.annotation.HALO_ALPHA)
            vertexShader: "ribbon.vert"; fragmentShader: "ribbon.frag"
        }
    }
    Model {
        geometry: ribbon.geometry
        castsShadows: false; receivesShadows: false
        materials: CustomMaterial {
            shadingMode: CustomMaterial.Shaded
            cullMode: Material.NoCulling
            property real ribbonWidth: Theme.annotation.STROKE
            property real pixelSize: ribbon.pixelSize
            property vector4d ribbonColor: Qt.vector4d(ribbon.ink.r,ribbon.ink.g,ribbon.ink.b,ribbon.ink.a)
            vertexShader: "ribbon.vert"; fragmentShader: "ribbon.frag"
        }
    }
}
