// The 3D pictures of the report (ui/report_3d.py): the project's scene on paper, without the window's interaction.
// A parallel camera (an axonometric view) placed by Python through the root's properties, a white ground, the
// buildings light and neutral with their edges, the modules in their navy, a high sun for soft shadows.
import QtQuick
import QtQuick3D
import Meridiana

Item {
    id: root
    property vector3d cameraPosition: Qt.vector3d(0, 50, 80)
    property quaternion cameraRotation: Qt.quaternion(1, 0, 0, 0)
    property real magnification: 10.0
    property color paper: "white"
    property color groundColor: "#f1efea"
    property vector3d groundCentre: Qt.vector3d(0, 0, 0)
    property real groundHalf: 100.0
    property real shadowFar: 400.0

    View3D {
        id: view
        anchors.fill: parent
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Color
            clearColor: root.paper
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.VeryHigh
        }

        camera: parallel
        OrthographicCamera {
            id: parallel
            objectName: "camera"
            position: root.cameraPosition
            rotation: root.cameraRotation
            horizontalMagnification: root.magnification
            verticalMagnification: root.magnification
            clipNear: -20000
            clipFar: 20000
        }

        // the sky's light from three sides, as in the window's view (Scene.qml); the sun high in the south-west
        // (yaw 180 - bearing 225), so that the two faces the views show are lit, its shadows soft and light
        DirectionalLight { eulerRotation: Qt.vector3d(-35, 0, 0); brightness: 0.28 }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, 120, 0); brightness: 0.28 }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, -120, 0); brightness: 0.28 }
        DirectionalLight {
            eulerRotation: Qt.vector3d(-50, -45, 0)
            brightness: 0.8
            castsShadow: true
            shadowMapQuality: Light.ShadowMapQualityVeryHigh
            shadowMapFar: root.shadowFar
            shadowFactor: 35
            shadowBias: 0.2
            csmNumSplits: 2
            pcfFactor: 0.05
            softShadowQuality: Light.PCF8
        }

        Model {
            source: "#Rectangle"
            eulerRotation.x: -90
            position: root.groundCentre
            scale: Qt.vector3d(root.groundHalf / 50, root.groundHalf / 50, 1)
            receivesShadows: true
            materials: PrincipledMaterial { baseColor: root.groundColor; roughness: 1.0 }
        }

        Model {
            castsShadows: true
            receivesShadows: true
            geometry: BuildingsGeometry { objectName: "buildingsGeometry" }
            materials: PrincipledMaterial {
                vertexColorsEnabled: true
                roughness: 0.95
                cullMode: Material.NoCulling
            }
        }

        // the buildings' edges: thin ribbons of one tint, unlit, as the lines of a drawing
        Model {
            castsShadows: false
            receivesShadows: false
            geometry: OutlineGeometry { objectName: "edgesGeometry" }
            materials: PrincipledMaterial {
                vertexColorsEnabled: true
                lighting: PrincipledMaterial.NoLighting
                cullMode: Material.NoCulling
            }
        }

        Model {
            source: "#Cube"
            castsShadows: true
            receivesShadows: true
            instancing: ModulesInstancing { objectName: "modulesTable" }
            materials: PrincipledMaterial { baseColor: "white"; metalness: 0.0; roughness: 0.75 }
        }
    }
}
