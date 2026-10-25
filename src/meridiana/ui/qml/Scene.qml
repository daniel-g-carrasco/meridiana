// The 3D view of Meridiana: the buildings and the modules come from Python (view3d.py), the sun too.
// The camera is Python's (camera.py), bound here: the mouse goes to the backend with what it pressed on,
// the navigation style decides (navigation.py), and the camera comes back as bindings.
import QtQuick
import QtQuick3D
import QtQuick3D.Helpers
import Meridiana

Item {
    id: root

    // the sky, a gradient behind a transparent View3D; its colours come from the theme as bindings
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: backend.skyTop }
            GradientStop { position: 1.0; color: backend.skyBottom }
        }
    }

    View3D {
        id: view
        anchors.fill: parent
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
        }

        camera: backend.ortho ? parallel : camera
        PerspectiveCamera {
            id: camera
            objectName: "camera"
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            clipNear: 0.3
            clipFar: 20000
        }
        // the parallel view of the cube's menu: the same place, what the perspective shows at the target's depth
        OrthographicCamera {
            id: parallel
            objectName: "parallel"
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            horizontalMagnification: backend.orthoMagnification
            verticalMagnification: backend.orthoMagnification
            clipNear: -20000
            clipFar: 20000
        }

        // the sky's light, without shadows, from three sides 120 degrees apart, so that no wall is left black
        // whichever way it faces. Qt Quick 3D takes at most four directional lights ("Too many directional
        // lights in scene, maximum is 4"): with a fifth one the sun was the one left out.
        DirectionalLight { eulerRotation: Qt.vector3d(-35, 0, 0); brightness: 0.25 }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, 120, 0); brightness: 0.25 }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, -120, 0); brightness: 0.25 }
        // the sun
        DirectionalLight {
            eulerRotation: Qt.vector3d(backend.sunPitch, backend.sunYaw, 0)
            brightness: backend.sunPower
            // Qt's defaults are made for centimetres and the scene is in metres: a 2 m blur and a map 5 km
            // deep left the shadows a faint smudge. The map reaches as far as the scene does.
            castsShadow: true
            shadowMapQuality: Light.ShadowMapQualityVeryHigh
            shadowMapFar: backend.shadowFar
            shadowFactor: 75
            shadowBias: 0.2
            csmNumSplits: 2
            pcfFactor: 0.05
            softShadowQuality: Light.PCF8
        }

        Model {
            source: "#Rectangle"
            eulerRotation.x: -90
            position: Qt.vector3d(backend.groundX, 0, backend.groundZ)     // under the scene (R66)
            scale: Qt.vector3d(backend.groundHalf / 50, backend.groundHalf / 50, 1)
            receivesShadows: true
            materials: PrincipledMaterial {
                baseColor: backend.ground !== "" ? "white" : backend.groundColor
                baseColorMap: Texture { source: backend.ground }
                roughness: 1.0
            }
        }

        Model {
            objectName: "buildings"
            pickable: true
            castsShadows: true
            receivesShadows: true
            geometry: BuildingsGeometry { objectName: "buildingsGeometry" }
            materials: PrincipledMaterial {
                vertexColorsEnabled: true
                roughness: 0.9
                cullMode: Material.NoCulling
            }
        }

        // the outline of the selection and of what is under the pointer: ribbons of their own tint, unlit
        Model {
            objectName: "outline"
            pickable: false
            castsShadows: false
            receivesShadows: false
            geometry: OutlineGeometry { objectName: "outlineGeometry" }
            materials: PrincipledMaterial {
                vertexColorsEnabled: true
                lighting: PrincipledMaterial.NoLighting
                cullMode: Material.NoCulling
            }
        }

        Model {
            objectName: "modules"
            source: "#Cube"
            pickable: true
            castsShadows: true
            receivesShadows: true
            instancing: ModulesInstancing { objectName: "modulesTable" }
            materials: PrincipledMaterial { baseColor: "white"; metalness: 0.2; roughness: 0.35 }
        }
    }

    // the pivot of the view, as a cross-hair (task 16g, study 16 G): Autodesk's «ball with three belts», three
    // rings and a dot in the lime of view_colours over a dark halo, PIVOT_PX pixels wide wherever it stands. Qt
    // Quick 3D has no «draw over everything» for a model (a material has no depth test to switch off), so it is a
    // view of its own laid over the scene, with the same camera and nothing else in it: nothing can hide it, and
    // while it is not shown (the backend says when) it is not drawn at all. Not pickable, no shadows, no lights.
    View3D {
        id: cross
        objectName: "crossHair"
        anchors.fill: parent
        visible: backend.pivotVisible
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.Medium
        }

        camera: backend.ortho ? crossParallel : crossCamera
        PerspectiveCamera {
            id: crossCamera
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            clipNear: 0.3
            clipFar: 20000
        }
        OrthographicCamera {
            id: crossParallel
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            horizontalMagnification: backend.orthoMagnification
            verticalMagnification: backend.orthoMagnification
            clipNear: -20000
            clipFar: 20000
        }

        Node {
            objectName: "pivotMarker"
            visible: backend.pivotVisible
            position: backend.pivot
            scale: Qt.vector3d(backend.pivotScale, backend.pivotScale, backend.pivotScale)

            // the halo: flat dark bands in the planes of the rings, translucent, under the tubes
            Model {
                objectName: "pivotHalo"
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: RingGeometry { objectName: "pivotHaloGeometry" }
                materials: PrincipledMaterial {
                    vertexColorsEnabled: true
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                    opacity: backend.pivotHaloOpacity
                }
            }
            // the three rings
            Model {
                objectName: "pivotRings"
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: RingGeometry { objectName: "pivotRingsGeometry" }
                materials: PrincipledMaterial {
                    vertexColorsEnabled: true
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                }
            }
            // the dot at the centre
            Model {
                objectName: "pivotDot"
                source: "#Sphere"
                scale: Qt.vector3d(backend.pivotDotScale, backend.pivotDotScale, backend.pivotDotScale)
                pickable: false
                castsShadows: false
                receivesShadows: false
                materials: PrincipledMaterial { baseColor: backend.pivotColor; lighting: PrincipledMaterial.NoLighting }
            }
        }
    }

    // the gizmo of Move and Rotate (task 16b, study 16 B): arrows East (red) and North (green), the arrow up faint (a
    // move does not lift an object of a plan), the square of the horizontal plane and the ring about the vertical
    // (blue), 120 pixels long wherever they stand (backend.gizmoScale), over a dark halo drawn in a view under
    // them. Like the pivot's cross-hair they are views of their own laid over the scene, with the same camera:
    // nothing hides them. The handles are one unit long (mesh.py) and chosen on the screen in Python (gizmo.py),
    // not picked here. While a handle is dragged the outline of what moves goes with it (the preview), turned
    // about the gizmo's middle.
    View3D {
        id: gizmoHaloView
        objectName: "gizmoHaloView"
        anchors.fill: parent
        visible: backend.gizmoVisible
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.Medium
        }
        camera: backend.ortho ? gizmoHaloParallel : gizmoHaloCamera
        PerspectiveCamera {
            id: gizmoHaloCamera
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            clipNear: 0.3
            clipFar: 20000
        }
        OrthographicCamera {
            id: gizmoHaloParallel
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            horizontalMagnification: backend.orthoMagnification
            verticalMagnification: backend.orthoMagnification
            clipNear: -20000
            clipFar: 20000
        }
        Node {
            objectName: "gizmoHalo"
            visible: backend.gizmoVisible
            position: backend.gizmoPosition
            scale: Qt.vector3d(backend.gizmoScale, backend.gizmoScale, backend.gizmoScale)
            Model {
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: GizmoGeometry { objectName: "gizmoHaloXGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoColors.halo
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                    opacity: backend.gizmoHaloOpacity
                }
            }
            Model {
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: GizmoGeometry { objectName: "gizmoHaloYGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoColors.halo
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                    opacity: backend.gizmoHaloOpacity
                }
            }
            Model {
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: GizmoGeometry { objectName: "gizmoHaloRingGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoColors.halo
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                    opacity: backend.gizmoHaloOpacity
                }
            }
        }
    }

    View3D {
        id: gizmoView
        objectName: "gizmoView"
        anchors.fill: parent
        visible: backend.gizmoVisible
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.Medium
        }
        camera: backend.ortho ? gizmoParallel : gizmoCamera
        PerspectiveCamera {
            id: gizmoCamera
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            clipNear: 0.3
            clipFar: 20000
        }
        OrthographicCamera {
            id: gizmoParallel
            position: backend.cameraPosition
            rotation: backend.cameraRotation
            horizontalMagnification: backend.orthoMagnification
            verticalMagnification: backend.orthoMagnification
            clipNear: -20000
            clipFar: 20000
        }
        // the preview: the outline of what moves, where the drag puts it
        Node {
            objectName: "gizmoPreview"
            visible: backend.previewVisible
            position: backend.previewPosition
            rotation: backend.previewRotation
            Node {
                position: backend.previewBack
                Model {
                    pickable: false
                    castsShadows: false
                    receivesShadows: false
                    geometry: OutlineGeometry { objectName: "previewGeometry" }
                    materials: PrincipledMaterial {
                        vertexColorsEnabled: true
                        lighting: PrincipledMaterial.NoLighting
                        cullMode: Material.NoCulling
                    }
                }
            }
        }
        Node {
            objectName: "gizmo"
            visible: backend.gizmoVisible
            position: backend.gizmoPosition
            scale: Qt.vector3d(backend.gizmoScale, backend.gizmoScale, backend.gizmoScale)
            Model {
                objectName: "gizmoX"
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: GizmoGeometry { objectName: "gizmoXGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoHot === "x" ? backend.gizmoColors.hot : backend.gizmoColors.x
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                }
            }
            Model {
                objectName: "gizmoY"
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: GizmoGeometry { objectName: "gizmoYGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoHot === "y" ? backend.gizmoColors.hot : backend.gizmoColors.y
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                }
            }
            Model {
                objectName: "gizmoZ"
                pickable: false
                castsShadows: false
                receivesShadows: false
                opacity: 0.35
                geometry: GizmoGeometry { objectName: "gizmoZGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoColors.z
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                }
            }
            Model {
                objectName: "gizmoPlane"
                pickable: false
                castsShadows: false
                receivesShadows: false
                opacity: backend.gizmoHot === "xy" ? 0.85 : 0.5
                geometry: GizmoGeometry { objectName: "gizmoPlaneGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoHot === "xy" ? backend.gizmoColors.hot : backend.gizmoColors.z
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                }
            }
            Model {
                objectName: "gizmoRing"
                pickable: false
                castsShadows: false
                receivesShadows: false
                geometry: GizmoGeometry { objectName: "gizmoRingGeometry" }
                materials: PrincipledMaterial {
                    baseColor: backend.gizmoHot === "rz" ? backend.gizmoColors.hot : backend.gizmoColors.z
                    lighting: PrincipledMaterial.NoLighting
                    cullMode: Material.NoCulling
                }
            }
        }
    }

    // every button and the wheel go to the backend with what is under the pointer
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        hoverEnabled: true
        function hitAt(x, y) {
            const r = view.pick(x, y)
            return r.objectHit ? { hit: true, p: r.scenePosition, name: r.objectHit.objectName, index: r.instanceIndex }
                               : { hit: false, p: Qt.vector3d(0, 0, 0), name: "", index: -1 }
        }
        onPressed: (mouse) => {
            const h = hitAt(mouse.x, mouse.y)
            backend.press(mouse.button, mouse.modifiers, mouse.x, mouse.y, h.hit, h.p.x, h.p.y, h.p.z, h.name, h.index)
        }
        onPositionChanged: (mouse) => {
            backend.move(mouse.modifiers, mouse.x, mouse.y)
            if (mouse.buttons === Qt.NoButton) {         // what is under the pointer, a few times a second
                hoverTimer.px = mouse.x
                hoverTimer.py = mouse.y
                hoverTimer.restart()
                // the pivot's cross-hair follows the pointer while the orbit's key is held: a pick at each move,
                // but only then (the backend says when it needs one)
                const h = backend.pivotPick(mouse.modifiers) ? hitAt(mouse.x, mouse.y)
                                                             : { hit: false, p: Qt.vector3d(0, 0, 0) }
                backend.pivotHover(mouse.modifiers, mouse.x, mouse.y, h.hit, h.p.x, h.p.y, h.p.z)
            }
        }
        onExited: {
            hoverTimer.stop()
            backend.hover(false, 0, 0, 0, "", -1)
            backend.pivotHover(0, 0, 0, false, 0, 0, 0)  // out of the view: no cross-hair for a key held
        }
        onReleased: (mouse) => backend.release(mouse.button, mouse.modifiers, mouse.x, mouse.y)
        onDoubleClicked: (mouse) => backend.doubleClick(mouse.button, mouse.modifiers, mouse.x, mouse.y)
        onWheel: (wheel) => {
            const h = hitAt(wheel.x, wheel.y)
            const steps = wheel.angleDelta.y !== 0 ? wheel.angleDelta.y / 120 : wheel.pixelDelta.y / 60
            backend.wheel(steps, wheel.modifiers, wheel.x, wheel.y, h.hit, h.p.x, h.p.y, h.p.z)
        }
    }

    // picking at each move of the pointer would cost a ray through every module: it waits for the pointer to
    // rest 60 ms, or to have moved for 60 ms
    Timer {
        id: hoverTimer
        property real px: 0
        property real py: 0
        interval: 60
        onTriggered: {
            const r = view.pick(px, py)
            backend.hover(r.objectHit !== null, r.scenePosition.x, r.scenePosition.y, r.scenePosition.z,
                          r.objectHit ? r.objectHit.objectName : "", r.instanceIndex)
        }
    }

    onWidthChanged: backend.resized(width, height)
    onHeightChanged: backend.resized(width, height)
    Component.onCompleted: backend.resized(width, height)
}
