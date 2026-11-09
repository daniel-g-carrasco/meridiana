import QtQuick
import QtQuick3D
import Meridiana.Theme
import "CameraMath.js" as Cam
import "GizmoMath.js" as Gizmo

Item {
    id: root
    required property var viewport
    readonly property var shapes: viewport.sceneBackend.handleGeometry
    readonly property var mark: viewport.orbiting ? viewport.orbitPoint : viewport.hintPoint
    readonly property real pivotScale: mark ? Math.max(.001,16*Cam.pixelSize(viewport.cameraState,mark,height)) : .001
    readonly property real gizmoScale: Math.max(.001,Gizmo.length(viewport.cameraState,viewport.gizmoData.centre,height))
    visible: (viewport.pivotHint && mark !== null) || (viewport.moveMode && viewport.gizmoData.on)
    View3D {
        anchors.fill: parent
        visible: root.viewport.moveMode && root.viewport.gizmoData.on
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA; antialiasingQuality: SceneEnvironment.Medium
        }
        camera: root.viewport.cameraState.ortho ? haloParallel : haloPerspective
        PerspectiveCamera { id: haloPerspective; position: root.viewport.cameraPosition; rotation: root.viewport.cameraRotation
            fieldOfView: root.viewport.cameraState.fov; clipNear: .3; clipFar: 20000 }
        OrthographicCamera { id: haloParallel; position: root.viewport.cameraPosition; rotation: root.viewport.cameraRotation
            horizontalMagnification: root.viewport.magnification; verticalMagnification: root.viewport.magnification
            clipNear: -20000; clipFar: 20000 }
        Node {
            position: Qt.vector3d(...root.viewport.gizmoData.centre)
            scale: Qt.vector3d(root.gizmoScale,root.gizmoScale,root.gizmoScale)
            Repeater3D {
                model: ["xHalo","yHalo","rzHalo"]
                Model { required property string modelData; geometry: root.shapes[modelData]; castsShadows: false; receivesShadows: false
                    materials: PrincipledMaterial { baseColor: Theme.colors.overlay.halo_solid; lighting: PrincipledMaterial.NoLighting
                        cullMode: Material.NoCulling; opacity: .75 } }
            }
        }
    }
    View3D {
    anchors.fill: parent
    environment: SceneEnvironment {
        backgroundMode: SceneEnvironment.Transparent
        antialiasingMode: SceneEnvironment.MSAA; antialiasingQuality: SceneEnvironment.Medium
    }
    camera: root.viewport.cameraState.ortho ? parallel : perspective
    PerspectiveCamera { id: perspective; position: root.viewport.cameraPosition; rotation: root.viewport.cameraRotation
        fieldOfView: root.viewport.cameraState.fov; clipNear: .3; clipFar: 20000 }
    OrthographicCamera { id: parallel; position: root.viewport.cameraPosition; rotation: root.viewport.cameraRotation
        horizontalMagnification: root.viewport.magnification; verticalMagnification: root.viewport.magnification
        clipNear: -20000; clipFar: 20000 }
    Node {
        visible: root.viewport.pivotHint && root.mark !== null
        position: root.mark ? Qt.vector3d(...root.mark) : Qt.vector3d(0,0,0)
        scale: Qt.vector3d(root.pivotScale,root.pivotScale,root.pivotScale)
        Model { geometry: root.shapes.pivotHalo; castsShadows: false; receivesShadows: false
            materials: PrincipledMaterial { vertexColorsEnabled: true; lighting: PrincipledMaterial.NoLighting
                cullMode: Material.NoCulling; opacity: .7 } }
        Model { geometry: root.shapes.pivot; castsShadows: false; receivesShadows: false
            materials: PrincipledMaterial { vertexColorsEnabled: true; lighting: PrincipledMaterial.NoLighting; cullMode: Material.NoCulling } }
        Model { source: "#Sphere"; scale: Qt.vector3d(.0052,.0052,.0052); castsShadows: false; receivesShadows: false
            materials: PrincipledMaterial { baseColor: Theme.colors.gizmo.handle; lighting: PrincipledMaterial.NoLighting } }
    }
    Node {
        visible: root.viewport.moveMode && root.viewport.gizmoData.on
        position: Qt.vector3d(...root.viewport.gizmoData.centre)
        scale: Qt.vector3d(root.gizmoScale,root.gizmoScale,root.gizmoScale)
        Repeater3D {
            model: ["x","y","z","xy","rz"]
            Model {
                required property string modelData
                geometry: root.shapes[modelData]; castsShadows: false; receivesShadows: false
                opacity: modelData === "z" ? .35 : modelData === "xy" ? (root.viewport.gizmoHot==="xy" ? .85 : .5) : 1
                materials: PrincipledMaterial {
                    baseColor: root.viewport.gizmoHot===modelData ? Theme.colors.gizmo.hot : Theme.colors.gizmo[modelData] || Theme.colors.gizmo.z
                    lighting: PrincipledMaterial.NoLighting; cullMode: Material.NoCulling
                }
            }
        }
    }
    }
}
