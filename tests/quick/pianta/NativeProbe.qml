import QtQuick
import QtQuick.Window
import QtQuick3D

Window {
    id: probeRoot
    width: 1366; height: 900; visible: true
    property real cameraX: probeCentre.x
    property real cameraY: probeCentre.y
    property real zoom: probeZoom
    View3D {
        anchors.fill: parent
        environment: SceneEnvironment { backgroundMode: SceneEnvironment.Color; clearColor: "#2b2f33" }
        camera: ortho
        OrthographicCamera {
            id: ortho
            x: probeRoot.cameraX; y: probeRoot.cameraY; z: 1000; clipNear: -20000; clipFar: 20000
            horizontalMagnification: probeRoot.zoom; verticalMagnification: probeRoot.zoom
        }
        Loader3D {
            sourceComponent: probeInstances ? instanceModel : uploadedModel
        }
        Component {
            id: instanceModel
            Model {
                source: "#Rectangle"
                instancing: table
                materials: probeShader ? shaderMaterial : material
            }
        }
        Component {
            id: uploadedModel
            Model {
                geometry: probeGeometry
                materials: probeShader ? shaderMaterial : material
            }
        }
        DefaultMaterial {
                id: material
                lighting: DefaultMaterial.NoLighting; cullMode: Material.NoCulling
                diffuseColor: "#192d5a"
        }
        CustomMaterial {
                id: shaderMaterial
                shadingMode: CustomMaterial.Unshaded; cullMode: Material.NoCulling
                fragmentShader: "module-probe.frag"
        }
        FileInstancing { id: table; objectName: "probeTable"; source: probeInstances ? probeFile : "" }
    }
}
