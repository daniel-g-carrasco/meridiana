// Scene.qml's lighting, ground, mesh and module materials, directly in a Quick window.
import QtQuick
import QtQuick.Controls
import QtQuick3D
import Meridiana.Theme
import Meridiana.Controls as M
import "CameraMath.js" as Cam
import "Navigation.js" as Nav
import "GizmoMath.js" as Gizmo

Control {
    id: root
    objectName: "viewport3d"
    required property var sceneBackend
    property bool dark: Theme.dark
    property color panelColor: Theme.colors.card
    property color textColor: Theme.colors.text
    property color accentColor: Theme.colors.accent
    property bool reducedMotion: Theme.reducedMotion
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    palette.window: panelColor
    palette.windowText: textColor
    palette.button: panelColor
    palette.buttonText: textColor
    palette.base: panelColor
    palette.text: textColor
    palette.highlight: accentColor
    property string navigationStyle: "autocad"
    property string orbitMode: "turntable"
    property string pivotMode: "cursor"
    property bool pivotHint: true
    // The edges (study 41, slice E; config edges_3d): "full" multisampled at the highest always, "moving" without
    // multisampling while the camera moves (orbit, pan, zoom, a flight) and full again once it has rested, "low"
    // without always. On the Dell at 4K the highest costs 25-28 ms of drawing a frame (docs/quick/stato/r24-3d.md).
    property string edgeQuality: "full"
    property bool moving: false
    readonly property bool edgesReduced: edgeQuality === "low" || (edgeQuality === "moving" && moving)
    onCameraStateChanged: if (root.edgeQuality === "moving") { root.moving = true; movingRest.restart() }
    onEdgeQualityChanged: { movingRest.stop(); root.moving = false }
    property bool touchpad: false
    property bool shadows: true
    property string viewMode: "shaded"
    property bool editVertices: false
    property bool moveMode: false
    // R554: the plan's tool «3D object» is on: a click places the object where the ray meets the scene or the ground
    property bool placing: false
    signal placeRequested(string how, var point, int bits, real mpp)
    property bool snaps: true
    property var gizmoData: JSON.parse(JSON.stringify(sceneBackend.gizmo))
    property var verticesData: JSON.parse(sceneBackend.verticesJson)
    property var edgesData: JSON.parse(sceneBackend.selectionEdgesJson)
    property var hoverData: JSON.parse(sceneBackend.hoverDataJson)
    property var selectionCentre: JSON.parse(JSON.stringify(sceneBackend.selectionCentre))
    property var navStyles: JSON.parse(JSON.stringify(sceneBackend.navigationStyles))
    property var gizmoDrag: null
    property var gizmoValue: [0,0,0]
    property string gizmoHot: ""
    property string lastHandle: "x"
    property var heightDrag: null
    property var sweepStart: null
    property bool ctrlHeld: false
    property int hotCorner: -1
    property var sweepEnd: null
    property bool sweepRemove: false
    property bool showTools: true
    property bool showViewSelector: false
    signal viewRequested(string mode)
    property bool commandsLinked: false
    signal commandRequested(string command)
    readonly property real sceneHeight: sceneCanvas.height
    readonly property real sunBarHeight: showTools ? sunBar.height : 0
    property bool modulesVisible: true
    property bool benchmark: false
    property var frameTimes: []
    property int renderedFrames: 0
    property var cameraState: Cam.create()
    property var nav: Nav.create(navStyles[navigationStyle])
    property var homeState: null
    property var orbitPoint: [0, 0, 0]
    property var depthPoint: null
    property var pressedHit: null
    property bool spaceHeld: false
    property bool orbiting: false
    property var hintPoint: null
    property int gestureFrames: 0
    property int vertexIndex: -1
    property string vertexCycle: ""
    property int lastVertexPick: -1
    property var vertexOrigin: null
    property real vertexStart: 0
    property real vertexDelta: 0
    property bool vertexMoved: false
    property var fieldAnchor: null
    property string fieldMode: "height"
    property bool fitted: false
    property bool userMoved: false
    property var animationFrom: null
    property var animationTo: null
    property real animationProgress: 0
    readonly property real bearing: Cam.bearing(cameraState)
    readonly property real elevation: Cam.elevation(cameraState)
    readonly property var cameraPosition: Qt.vector3d(...cameraState.position)
    readonly property var cameraRotation: Qt.quaternion(...cameraState.rotation)
    readonly property real magnification: sceneHeight / (2 * Cam.halfHeight(cameraState))
    readonly property real outlinePixel: {
        if (cameraState.ortho) return 2*Cam.halfHeight(cameraState)/Math.max(1,sceneHeight)
        let centre=[0,0,0]
        for (let edge of edgesData) for (let point of edge) centre=Cam.add(centre,point)
        if (edgesData.length) centre=Cam.scale(centre,1/(edgesData.length*2))
        let depth=Math.max(Cam.MIN_DISTANCE,Cam.dot(Cam.sub(centre,cameraState.position),Cam.forward(cameraState)))
        return 2*depth*Math.tan(Cam.radians(cameraState.fov)/2)/Math.max(1,sceneHeight)
    }
    function ribbonPixel(edges) {
        if (cameraState.ortho) return 2*Cam.halfHeight(cameraState)/Math.max(1,sceneHeight)
        let centre=[0,0,0]
        for (let edge of edges) for (let point of edge) centre=Cam.add(centre,point)
        if (edges.length) centre=Cam.scale(centre,1/(edges.length*2))
        let depth=Math.max(Cam.MIN_DISTANCE,Cam.dot(Cam.sub(centre,cameraState.position),Cam.forward(cameraState)))
        return 2*depth*Math.tan(Cam.radians(cameraState.fov)/2)/Math.max(1,sceneHeight)
    }
    clip: true
    focus: true

    function go(state, animate) {
        flight.stop(); depthPoint = null
        if (!animate || reducedMotion) { cameraState = state; return }
        animationFrom = Cam.copy(cameraState); animationTo = state
        animationProgress = 0; flight.start()
    }
    function projectPoint(point) { return Cam.project(cameraState, point, width, root.sceneHeight) }
    // R554: the metres of a pixel at a point of the scene, for the reach of the plan's snaps
    function metresAt(point) {
        if (cameraState.ortho) return 2*Cam.halfHeight(cameraState)/Math.max(1,sceneHeight)
        let depth=Math.max(Cam.MIN_DISTANCE,Cam.dot(Cam.sub(point,cameraState.position),Cam.forward(cameraState)))
        return 2*depth*Math.tan(Cam.radians(cameraState.fov)/2)/Math.max(1,sceneHeight)
    }
    // R554: the point the tool «3D object» is given: on what the ray met at the press (a click) or under the pointer,
    // else on the ground; the plan's machine does the rest (backend/scene_part.SceneControls.viewPlace)
    function placeAt(how, x, y, mods) {
        let hit = how === "click" ? pressedHit : hitAt(x, y)
        let point = hit ? hit.point : Cam.ground(cameraState, x, y, width, sceneHeight)
        if (!point) return false
        let bits = (mods.indexOf("ctrl") >= 0 ? 1 : 0) | (mods.indexOf("shift") >= 0 ? 2 : 0) | (mods.indexOf("alt") >= 0 ? 4 : 0)
        placeRequested(how, point, bits, metresAt(point))
        return true
    }
    function requestCommand(command) {
        if (commandsLinked) { commandRequested(command); return }
        if (command === "fit") frameSelection()
        else if (command === "zoom_in") zoomBy(1)
        else if (command === "zoom_out") zoomBy(-1)
    }
    function frameSelection() {
        let bounds = sceneBackend.frameBounds()
        go(Cam.fit(cameraState, bounds.centre, bounds.radius, width/Math.max(1,sceneHeight)), true)
        userMoved = true
    }
    function fitScene() {
        go(Cam.fit(cameraState, sceneBackend.bounds.centre, sceneBackend.bounds.radius,
                   Math.max(1, width) / Math.max(1, sceneHeight)), fitted)
        fitted = true
        userMoved = false
    }
    function resizeFit() {
        if (!userMoved && width > 0 && sceneHeight > 0) {
            go(Cam.fit(cameraState, sceneBackend.bounds.centre, sceneBackend.bounds.radius, width/sceneHeight), false)
            fitted = true
        }
    }
    function zoomBy(steps) { flight.stop(); userMoved=true; cameraState=Cam.zoom(cameraState,steps*Math.log(1.2)/Math.log(1/Cam.ZOOM_STEP),cameraState.target) }
    function home() {
        go(homeState ? Cam.copy(homeState) : Cam.view(cameraState, "home", sceneBackend.bounds.centre,
           sceneBackend.bounds.radius, Math.max(1, width) / Math.max(1, sceneHeight)), true)
    }
    function mods(flags) {
        let result = []
        if (flags & Qt.ControlModifier) result.push("ctrl")
        if (flags & Qt.ShiftModifier) result.push("shift")
        if (flags & Qt.AltModifier) result.push("alt")
        if (spaceHeld) result.push("space")
        return result
    }
    function button(flag) { return flag === Qt.LeftButton ? "left" : flag === Qt.RightButton ? "right" : "middle" }
    function hitAt(x, y) {
        let r = view.pick(x, y)
        return r.objectHit ? {point: [r.scenePosition.x, r.scenePosition.y, r.scenePosition.z],
                             name: r.objectHit.objectName, index: r.instanceIndex} : null
    }
    function pivotAt(x, y, hit) {
        if (pivotMode === "centre") return cameraState.target.slice()
        if (pivotMode === "selection" && root.selectionCentre.length)
            return Cam.keepInView(cameraState, root.selectionCentre, width, root.sceneHeight)
        return Cam.pivot(cameraState, x, y, width, sceneHeight, hit ? hit.point : null)
    }
    function actions(list) {
        for (let a of list) {
            if (a.phase === "begin") {
                flight.stop()
                let start=nav.start || [a.x,a.y]
                orbitPoint = pivotAt(start[0], start[1], pressedHit)
                depthPoint = pressedHit ? pressedHit.point : Cam.zoomPoint(cameraState,start[0],start[1],width,root.sceneHeight,null)
                orbiting = a.kind === "orbit"
            } else if (a.phase === "move") {
                userMoved = true
                gestureFrames++
                if (a.kind === "orbit") cameraState = Cam.orbit(cameraState, a.dx, a.dy, orbitPoint, orbitMode)
                if (a.kind === "pan") cameraState = Cam.pan(cameraState, a.dx, a.dy, width, sceneHeight, depthPoint)
                if (a.kind === "zoom") cameraState = Cam.zoom(cameraState, -a.dy / 40,cameraState.target)
            } else if (a.phase === "end") { orbiting = false; depthPoint = null }
            else if (a.kind === "fit") fitScene()
            else if (a.kind === "recentre") {
                let point=pressedHit ? pressedHit.point : Cam.ground(cameraState,a.x,a.y,width,sceneHeight)
                if (point) go(Cam.recentre(cameraState,point),true)
            }
            else if (a.kind === "select" && placing) placeAt("click", a.x, a.y, a.mods || [])
            else if (a.kind === "select") {
                let h = pressedHit
                sceneBackend.pick(h ? h.name : "", h ? h.index : -1,
                                  h ? h.point[0] : 0, h ? h.point[1] : 0, h ? h.point[2] : 0)
            } else if (a.kind === "menu") {
                let h = pressedHit
                sceneBackend.pick(h ? h.name : "", h ? h.index : -1,
                                  h ? h.point[0] : 0, h ? h.point[1] : 0, h ? h.point[2] : 0)
                viewMenu.actions = sceneBackend.contextActions
                viewMenu.popup(a.x, a.y)
            }
        }
    }
    function alongVertical(x, y, point) {
        let ray = Cam.ray(cameraState, x, y, width, root.sceneHeight), d = ray[1], o = ray[0]
        let denom = 1 - d[1]*d[1]
        if (denom < 1e-9) return null
        let v = Cam.sub(o, point)
        return (v[1] - d[1] * Cam.dot(v, d)) / denom
    }
    function vertexAt(x, y, cycle) {
        if (!editVertices) return -1
        let near=Gizmo.pickPoints(cameraState,x,y,width,root.sceneHeight,verticesData.map(v=>v.point),12)
        if (!near.length) return -1
        let first=projectPoint(verticesData[near[0]].point)
        near=near.filter(i=>{let p=projectPoint(verticesData[i].point);return Math.hypot(p[0]-first[0],p[1]-first[1])<2})
        let signature=near.join(","), chosen=near[0]
        if (signature===vertexCycle && near.indexOf(lastVertexPick)>=0)
            chosen=near[(near.indexOf(lastVertexPick)+(cycle ? 1 : 0))%near.length]
        if (cycle) { vertexCycle=signature;lastVertexPick=chosen }
        return chosen
    }
    // R534: the corner's field opens beside the corner it was opened from (the one clicked, or the first chosen when
    // a key starts it): with more corners chosen its value is that corner's, and their centre is where the
    // manipulator stands, so a field there would always cover it.
    function openField(point, value, mode, select) {
        fieldMode = mode; fieldAnchor = point.slice()
        vertexField.visible = true; vertexField.edit(value, select)
        if (!select) vertexField.input.cursorPosition = vertexField.text.length
    }
    function closeField() { vertexField.visible = false; fieldAnchor = null }
    // Where the field stands: under and to the right of its corner, or in the first of the other three corners'
    // places that keeps it inside the view and off the manipulator and the other chosen corners; failing them all,
    // just under or over the manipulator. A corner gone out of the view leaves the field at the view's edge, with what
    // is written in it (closing it would lose what is being typed; Esc or a click closes it). Read again at every
    // change of the camera, in the same frame.
    function fieldPlace(w, h) {
        let W = width, H = sceneHeight, gap = Theme.space.S + 7
        let at = fieldAnchor ? projectPoint(fieldAnchor) : null
        if (!at) return [Math.max(0, (W-w)/2), Math.max(0, H-h-Theme.space.S)]
        let circles = []
        if (moveMode && gizmoData.on) {
            let c = projectPoint(gizmoData.centre)
            if (c) circles.push([c[0], c[1], Gizmo.PIXELS+Theme.space.XS])
        }
        for (let v of verticesData) {
            if (!v.selected) continue
            let p = projectPoint(v.point)
            if (p && Math.hypot(p[0]-at[0], p[1]-at[1]) > 1) circles.push([p[0], p[1], 7])
        }
        let hits = (x, y) => circles.filter(c => {
            let dx = c[0]-Math.max(x, Math.min(c[0], x+w)), dy = c[1]-Math.max(y, Math.min(c[1], y+h))
            return dx*dx+dy*dy < c[2]*c[2]
        }).length
        let inside = (x, y) => x >= 0 && y >= 0 && x+w <= W && y+h <= H
        let places = [[at[0]+gap, at[1]+gap], [at[0]+gap, at[1]-gap-h], [at[0]-gap-w, at[1]+gap], [at[0]-gap-w, at[1]-gap-h]]
        if (circles.length && circles[0][2] > 7) {
            let g = circles[0]
            places.push([at[0]-w/2, g[1]+g[2]+Theme.space.XS], [at[0]-w/2, g[1]-g[2]-Theme.space.XS-h])
        }
        let best = null, score = 1e9
        places.forEach((p, i) => {
            let s = hits(p[0], p[1])*100 + (inside(p[0], p[1]) ? 0 : 50) + i
            if (s < score) { score = s; best = p }
        })
        return [Math.max(0, Math.min(W-w, best[0])), Math.max(0, Math.min(H-h, best[1]))]
    }
    function cancel(escape) {
        previewTimer.stop(); vertexIndex = -1; vertexOrigin = null
        transformTimer.stop(); gizmoDrag=null; sweepStart=null; sweepEnd=null
        transformField.visible=false
        closeField()
        if (escape && placing) placeRequested("escape", [0, 0, 0], 0, 0)       // R554: Esc ends the tool, as on the plan
        else if (escape) { if (sceneBackend.escapeSelection(moveMode || editVertices)==="tool") { moveMode=false; editVertices=false } }
        else sceneBackend.cancelEdit()
        Nav.reset(nav); orbiting = false; spaceHeld = false
    }
    onNavigationStyleChanged: Nav.setStyle(nav, navStyles[navigationStyle] || navStyles.autocad)
    onAnimationProgressChanged: if (animationFrom && animationTo) cameraState = Cam.between(animationFrom, animationTo, animationProgress)
    NumberAnimation { id: flight; target: root; property: "animationProgress"; from: 0; to: 1; duration: Theme.motion.SLOW }
    FrameAnimation {
        running: root.benchmark
        onTriggered: {
            root.frameTimes.push(frameTime * 1000)
            root.renderedFrames++
            root.cameraState = Cam.orbit(root.cameraState, 0.5, 0, root.cameraState.target, "turntable")
        }
    }
    onWidthChanged: resizeFit()
    onSceneHeightChanged: resizeFit()
    Component.onCompleted: fitScene()
    Connections {
        target: sceneBackend
        function onSceneChanged() { if (!root.userMoved) root.resizeFit() }
        function onSelectionChanged() {  }
    }

    Item {
        id: sceneCanvas
        anchors.fill: parent
        anchors.bottomMargin: root.sunBarHeight
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: sceneBackend.sceneColors.sky_top }
            GradientStop { position: 1; color: sceneBackend.sceneColors.sky_bottom }
        }
    }
    View3D {
        id: view
        objectName: "sceneView"
        anchors.fill: parent
        environment: SceneEnvironment {
            objectName: "sceneEnvironment"
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: root.edgesReduced ? SceneEnvironment.NoAA : SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
            debugSettings: DebugSettings { wireframeEnabled: root.viewMode === "wireframe" }
        }
        camera: root.cameraState.ortho ? parallel : perspective
        PerspectiveCamera {
            id: perspective
            position: root.cameraPosition; rotation: root.cameraRotation
            fieldOfView: root.cameraState.fov
            clipNear: 0.3; clipFar: 20000
        }
        OrthographicCamera {
            id: parallel
            position: root.cameraPosition; rotation: root.cameraRotation
            horizontalMagnification: root.magnification; verticalMagnification: root.magnification
            clipNear: -20000; clipFar: 20000
        }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, 0, 0); brightness: 0.25 }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, 120, 0); brightness: 0.25 }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, -120, 0); brightness: 0.25 }
        DirectionalLight {
            eulerRotation: Qt.vector3d(-Math.max(sceneBackend.sunData.elevation, 2), 180-sceneBackend.sunData.bearing, 0)
            brightness: sceneBackend.sunData.elevation > 0 ? 1.25 : 0
            castsShadow: root.shadows && sceneBackend.sunData.elevation > 0
            shadowMapQuality: Light.ShadowMapQualityVeryHigh
            shadowMapFar: Math.max(100, sceneBackend.bounds.radius * 6)
            shadowFactor: 75; shadowBias: 1; csmNumSplits: 2; pcfFactor: 0.05; softShadowQuality: Light.PCF8
        }
        Model {
            objectName: "ground"
            source: "#Rectangle"
            eulerRotation.x: -90
            // ui/qml/Scene.qml: under the scene (R66), as wide as the scene and its margin, so the sky shows.
            position: Qt.vector3d(sceneBackend.bounds.centre[0], 0, sceneBackend.bounds.centre[2])
            scale: Qt.vector3d(sceneBackend.bounds.groundHalf/50, sceneBackend.bounds.groundHalf/50, 1)
            castsShadows: false
            receivesShadows: true
            materials: PrincipledMaterial { baseColor: sceneBackend.sceneColors.ground; roughness: 1 }
        }
        Model {
            objectName: "buildings"
            pickable: true; castsShadows: true; receivesShadows: true
            geometry: sceneBackend.buildingGeometry
            materials: PrincipledMaterial {
                vertexColorsEnabled: true; roughness: 0.9; cullMode: Material.NoCulling
                opacity: root.viewMode === "xray" ? 0.35 : 1
            }
        }
        // r21-ifc-vista: the bodies of an IFC import whose true geometry is shown: unseen, no shadow (they made grey
        // ghosts and shades over the model), still what is picked; the selection's outline shows the body chosen
        Model {
            objectName: "buildingsFaint"
            pickable: true; castsShadows: false; receivesShadows: false
            geometry: sceneBackend.ghostGeometry
            materials: PrincipledMaterial {
                vertexColorsEnabled: true; roughness: 0.9; cullMode: Material.NoCulling
                opacity: sceneBackend.ghostOpacity
            }
        }
        // the true geometry of that import, as context: not picked, no shadow (the bodies make the shadows)
        Repeater3D {
            model: sceneBackend.contextModels
            delegate: Model {
                required property var modelData
                objectName: modelData.name
                geometry: modelData.geometry
                position: Qt.vector3d(modelData.position[0], modelData.position[1], modelData.position[2])
                eulerRotation.y: modelData.turn
                pickable: false; castsShadows: false; receivesShadows: false
                materials: CustomMaterial {
                    shadingMode: CustomMaterial.Unshaded; cullMode: Material.NoCulling
                    property color tint: Qt.rgba(modelData.colour[0], modelData.colour[1], modelData.colour[2], 1)
                    property real opacity: modelData.colour[3]
                    sourceBlend: opacity < 1 ? CustomMaterial.SrcAlpha : CustomMaterial.NoBlend
                    destinationBlend: opacity < 1 ? CustomMaterial.OneMinusSrcAlpha : CustomMaterial.NoBlend
                    vertexShader: "context.vert"; fragmentShader: "context.frag"
                }
            }
        }
        Model {
            objectName: "outlineHalo"
            geometry: sceneBackend.outlineGeometry
            visible: root.edgesData.length > 0
            castsShadows: false; receivesShadows: false
            materials: CustomMaterial {
                shadingMode: CustomMaterial.Shaded
                cullMode: Material.FrontFaceCulling
                property real ribbonWidth: 2.5
                property real pixelSize: root.outlinePixel
                property vector4d ribbonColor: Qt.vector4d(11/255,13/255,16/255,1)
                vertexShader: "ribbon.vert"; fragmentShader: "ribbon.frag"
            }
        }
        Model {
            objectName: "outline"
            geometry: sceneBackend.outlineGeometry
            visible: root.edgesData.length > 0
            castsShadows: false; receivesShadows: false
            materials: CustomMaterial {
                shadingMode: CustomMaterial.Shaded
                cullMode: Material.NoCulling
                property real ribbonWidth: 1.6
                property real pixelSize: root.outlinePixel
                property color ink: sceneBackend.selectionColor
                property vector4d ribbonColor: Qt.vector4d(ink.r,ink.g,ink.b,1)
                vertexShader: "ribbon.vert"; fragmentShader: "ribbon.frag"
            }
        }
        // the strings over the modules, and a cross on each module with an optimizer, in the Plant (R433, R456)
        Model {
            objectName: "strings3d"
            geometry: sceneBackend.stringGeometry
            visible: sceneBackend.stringsShown
            castsShadows: false; receivesShadows: false
            materials: CustomMaterial {
                shadingMode: CustomMaterial.Shaded; cullMode: Material.NoCulling
                property real ribbonWidth: 2.0
                property real pixelSize: root.outlinePixel
                property vector4d ribbonColor: Qt.vector4d(0.95, 0.70, 0.20, 1)
                vertexShader: "ribbon.vert"; fragmentShader: "ribbon.frag"
            }
        }
        Model {
            objectName: "optimizers3d"
            geometry: sceneBackend.optimizerGeometry
            visible: sceneBackend.stringsShown
            castsShadows: false; receivesShadows: false
            materials: CustomMaterial {
                shadingMode: CustomMaterial.Shaded; cullMode: Material.NoCulling
                property real ribbonWidth: 2.4
                property real pixelSize: root.outlinePixel
                property vector4d ribbonColor: Qt.vector4d(0.10, 0.12, 0.16, 1)
                vertexShader: "ribbon.vert"; fragmentShader: "ribbon.frag"
            }
        }
        Model {
            objectName: "hoverOutline"
            geometry: sceneBackend.hoverGeometry
            visible: root.hoverData.edges.length > 0 && !root.orbiting
            castsShadows: false; receivesShadows: false
            materials: CustomMaterial {
                shadingMode: CustomMaterial.Shaded; cullMode: Material.NoCulling
                property real ribbonWidth: 1.3
                property real pixelSize: root.ribbonPixel(root.hoverData.edges)
                property color ink: root.hoverData.color
                property vector4d ribbonColor: Qt.vector4d(ink.r,ink.g,ink.b,1)
                vertexShader: "ribbon.vert"; fragmentShader: "ribbon.frag"
            }
        }
        Model {
            // In the scene, not over it: a corner behind a solid is covered as the lines are (R401).
            objectName: "vertexDots"
            geometry: sceneBackend.vertexGeometry
            visible: root.editVertices && root.verticesData.length > 0
            castsShadows: false; receivesShadows: false; pickable: false
            materials: CustomMaterial {
                shadingMode: CustomMaterial.Unshaded; cullMode: Material.NoCulling
                property real pixelSize: root.outlinePixel
                property vector2d viewPixels: Qt.vector2d(view.width, view.height)
                vertexShader: "dots.vert"; fragmentShader: "dots.frag"
            }
        }
        Model {
            objectName: "modules"
            source: "#Cube"
            visible: root.modulesVisible && sceneBackend.moduleCount > 0
            pickable: true; castsShadows: true; receivesShadows: true
            instancing: FileInstancing { objectName: "modulesTable"; source: sceneBackend.modulesSource }
            materials: PrincipledMaterial { baseColor: "white"; metalness: 0.2; roughness: 0.35 }
        }
        Repeater3D {
            // R554: one Model per model of the catalogue for the whole session (backend/scene_slots.py): made again
            // at every change, the last one of a model took its shared mesh out of the scene and it came back empty
            model: sceneBackend.decorationSlots
            delegate: Model {
                required property string slotName
                required property var slotGeometry
                required property url slotSource
                required property int slotCount
                objectName: slotName
                geometry: slotGeometry
                visible: slotCount > 0
                instancing: FileInstancing { source: slotSource }
                pickable: true; castsShadows: true; receivesShadows: true
                materials: PrincipledMaterial { vertexColorsEnabled: true; roughness: 0.9; cullMode: Material.NoCulling }
            }
        }
    }

    SceneCorners { anchors.fill: parent }
    SceneHandles { anchors.fill: parent; viewport: root }
    SceneOverlay {
        id: overlay
        objectName: "selectionOverlay"
        anchors.fill: parent
        viewport: root
    }
    MouseArea {
        id: mouseArea
        objectName: "sceneInput"
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        hoverEnabled: true
        cursorShape: root.spaceHeld ? Qt.OpenHandCursor : Qt.ArrowCursor
        onPressed: mouse => {
            hoverRest.stop()
            // R534: the corner's field stays, with what is written in it, while the middle button turns or moves the
            // view; any other press closes it, as a click away from the plan's side field does.
            let keepField = vertexField.visible && mouse.button === Qt.MiddleButton
            if (vertexField.visible && !keepField) root.closeField()
            if (!keepField) root.forceActiveFocus()
            flight.stop()
            root.pressedHit = root.hitAt(mouse.x, mouse.y)
            let index = root.vertexAt(mouse.x, mouse.y,mouse.button===Qt.LeftButton)
            if (mouse.button === Qt.RightButton && index >= 0) {
                sceneBackend.beginVertex(index,false)
                root.vertexOrigin=root.verticesData[index].point.slice()
                vertexMenu.popup(mouse.x,mouse.y); return
            }
            if (mouse.button === Qt.LeftButton && index >= 0 && !root.spaceHeld) {
                root.userMoved = true
                root.vertexIndex = index; root.vertexOrigin = root.verticesData[index].point.slice()
                root.heightDrag=Gizmo.beginHeight(root.cameraState,mouse.x,mouse.y,width,height,root.vertexOrigin)
                root.vertexDelta = 0; root.vertexMoved = false
                // R529: Ctrl adds or takes away, Shift adds
                sceneBackend.beginVertex(index, !!(mouse.modifiers & Qt.ControlModifier), !!(mouse.modifiers & Qt.ShiftModifier))
                return
            }
            if (root.moveMode && root.gizmoData.on && mouse.button===Qt.LeftButton && !root.spaceHeld) {
                let centre=root.gizmoData.centre
                let handle=Gizmo.pick(root.cameraState,mouse.x,mouse.y,width,root.sceneHeight,centre,Gizmo.length(root.cameraState,centre,height))
                if (handle) {
                    root.gizmoDrag=Gizmo.begin(handle,root.cameraState,mouse.x,mouse.y,width,root.sceneHeight,centre)
                    if (root.gizmoDrag) { root.userMoved=true; root.lastHandle=handle; root.gizmoValue=[0,0,0]; sceneBackend.beginTransform(); return }
                }
            }
            if (root.editVertices && mouse.button===Qt.LeftButton && !root.spaceHeld && !(mouse.modifiers & Qt.ShiftModifier)) {
                root.sweepEnd=[mouse.x,mouse.y]; root.sweepStart=root.sweepEnd
                root.sweepRemove=!!(mouse.modifiers & Qt.ControlModifier); return   // R529: Ctrl takes away
            }
            root.actions(Nav.press(root.nav, root.button(mouse.button), root.mods(mouse.modifiers), mouse.x, mouse.y))
        }
        onPositionChanged: mouse => {
            root.ctrlHeld=!!(mouse.modifiers & Qt.ControlModifier)
            if (root.editVertices && !mouse.buttons) {
                const corner=root.vertexAt(mouse.x,mouse.y,false)
                root.hotCorner=corner
                sceneBackend.hoverVertex(corner)
            }
            if (root.sweepStart) { root.sweepEnd=[mouse.x,mouse.y]; return }
            if (root.gizmoDrag) {
                root.gizmoValue=Gizmo.update(root.gizmoDrag,root.cameraState,mouse.x,mouse.y,width,height,root.mods(mouse.modifiers),root.snaps)
                if (!transformTimer.running) transformTimer.start()
                return
            }
            if (root.vertexIndex >= 0) {
                if (root.heightDrag) {
                    root.vertexDelta=Gizmo.updateHeight(root.heightDrag,root.cameraState,mouse.x,mouse.y,width,height,root.mods(mouse.modifiers),root.snaps)
                    root.vertexMoved = root.vertexMoved || Math.abs(root.vertexDelta) > 0.001
                    if (!previewTimer.running) previewTimer.start()
                }
                return
            }
            if (root.moveMode && root.gizmoData.on) root.gizmoHot=Gizmo.pick(root.cameraState,mouse.x,mouse.y,width,root.sceneHeight,
                    root.gizmoData.centre,Gizmo.length(root.cameraState,root.gizmoData.centre,root.sceneHeight))
            root.actions(Nav.move(root.nav, mouse.x, mouse.y, root.mods(mouse.modifiers)))
            if (!mouse.buttons && root.placing) { if (!placeMove.running) placeMove.start() }
            else if (!mouse.buttons) hoverRest.restart()
            if (!mouse.buttons && Nav.previewsOrbit(root.nav, root.mods(mouse.modifiers))) {
                root.hintPoint = root.pivotAt(mouse.x, mouse.y, root.hitAt(mouse.x, mouse.y)); 
            } else if (root.hintPoint) { root.hintPoint = null;  }
        }
        onReleased: mouse => {
            if (root.sweepStart) {
                let a=root.sweepStart,b=root.sweepEnd,indices=[]
                for (let i=0;i<root.verticesData.length;i++) {
                    let p=root.projectPoint(root.verticesData[i].point)
                    if (p && p[0]>=Math.min(a[0],b[0]) && p[0]<=Math.max(a[0],b[0]) && p[1]>=Math.min(a[1],b[1]) && p[1]<=Math.max(a[1],b[1])) indices.push(i)
                }
                sceneBackend.selectVertices(indices,root.sweepRemove,!root.sweepRemove)
                root.sweepStart=null;root.sweepEnd=null;return
            }
            if (root.gizmoDrag) {
                transformTimer.stop()
                sceneBackend.commitTransform(...root.gizmoValue,!!(mouse.modifiers & Qt.ControlModifier))
                root.gizmoDrag=null;return
            }
            if (root.vertexIndex >= 0) {
                previewTimer.stop()
                if (root.vertexMoved) sceneBackend.commitVertex(root.vertexDelta)
                else root.openField(root.vertexOrigin, root.vertexOrigin[1].toFixed(2).replace(".",","), "height", true)
                root.vertexIndex = -1; return
            }
            root.actions(Nav.release(root.nav, root.button(mouse.button), root.mods(mouse.modifiers), mouse.x, mouse.y))
        }
        onCanceled: root.cancel()
        onExited: { hoverRest.stop(); placeMove.stop(); sceneBackend.hover("",-1,0,0,0); root.hintPoint=null; root.gizmoHot="" }
        onDoubleClicked: mouse => {
            if (root.placing && mouse.button === Qt.LeftButton) { root.placeAt("double", mouse.x, mouse.y, root.mods(mouse.modifiers)); return }
            root.actions(Nav.doubleClick(root.nav, root.button(mouse.button), root.mods(mouse.modifiers), mouse.x, mouse.y))
        }
        onWheel: wheel => {
            hoverRest.stop()
            flight.stop()
            root.userMoved = true
            let a = Nav.wheelAction([wheel.angleDelta.x,wheel.angleDelta.y], [wheel.pixelDelta.x,wheel.pixelDelta.y],
                                    wheel.phase !== Qt.NoScrollPhase, false, !!(wheel.modifiers & Qt.ControlModifier), root.touchpad)
            if (a[0] === "pan") {
                if (root.depthPoint === null) root.depthPoint = Cam.zoomPoint(root.cameraState,wheel.x,wheel.y,width,root.sceneHeight,null)
                root.cameraState = Cam.pan(root.cameraState,a[1],a[2],width,height,root.depthPoint)
                panRest.restart()
            } else {
                let hit = root.hitAt(wheel.x,wheel.y)
                root.cameraState = Cam.zoom(root.cameraState, a[2], Cam.zoomPoint(root.cameraState,wheel.x,wheel.y,width,root.sceneHeight,hit ? hit.point : null))
            }
            root.gestureFrames++; wheel.accepted = true
        }
    }
    Timer {
        id: hoverRest; interval: 80
        onTriggered: {
            let h=root.hitAt(mouseArea.mouseX,mouseArea.mouseY)
            sceneBackend.hover(h ? h.name : "",h ? h.index : -1,h ? h.point[0] : 0,h ? h.point[1] : 0,h ? h.point[2] : 0)
        }
    }
    // R554: the object of the tool follows the pointer, a few times a second at most
    Timer { id: placeMove; interval: 30; onTriggered: if (root.placing) root.placeAt("move", mouseArea.mouseX, mouseArea.mouseY, root.mods(root.ctrlHeld ? Qt.ControlModifier : 0)) }
    Timer { id: panRest; interval: 180; onTriggered: root.depthPoint = null }
    // the camera at rest this long: the edges full again (edgeQuality "moving")
    Timer { id: movingRest; interval: 180; onTriggered: root.moving = false }
    PinchHandler {
        target: null
        acceptedDevices: PointerDevice.TouchPad | PointerDevice.TouchScreen
        rotationAxis.enabled: false
        xAxis.enabled: false
        yAxis.enabled: false
        onActiveChanged: { flight.stop(); root.depthPoint=null }
        onScaleChanged: delta => {
            if (!(delta>0)) return
            root.userMoved = true
            root.cameraState=Cam.zoom(root.cameraState,Math.log(delta)/Math.log(1/Cam.ZOOM_STEP),
                Cam.zoomPoint(root.cameraState,centroid.position.x,centroid.position.y,root.width,root.sceneHeight,null))
            root.gestureFrames++
        }
    }
    Timer { id: previewTimer; interval: 50; onTriggered: if (root.vertexIndex >= 0) sceneBackend.previewVertex(root.vertexDelta) }
    Timer { id: transformTimer; interval: 50; onTriggered: if (root.gizmoDrag) sceneBackend.previewTransform(...root.gizmoValue) }
    M.ToolTip { objectName: "vertexTip"; parent: mouseArea; text: sceneBackend.vertexHelp; pressed: mouseArea.pressed
        visible: root.editVertices && root.hotCorner>=0 && mouseArea.containsMouse }
    M.PointerSign {
        // R412: with Ctrl a click takes one more corner, or gives back one already taken (R535: the plan's sign).
        objectName: "vertexPlus"
        visible: root.editVertices && root.ctrlHeld && mouseArea.containsMouse
        pointer: Qt.point(Math.round(mouseArea.mouseX), Math.round(mouseArea.mouseY))
        colours: sceneBackend.overlayColors
        sign: root.hotCorner>=0 && root.hotCorner<root.verticesData.length && root.verticesData[root.hotCorner].selected ? "remove" : "add"
    }
    Rectangle {
        visible: root.sweepStart!==null
        x: root.sweepStart ? Math.min(root.sweepStart[0],root.sweepEnd[0]) : 0
        y: root.sweepStart ? Math.min(root.sweepStart[1],root.sweepEnd[1]) : 0
        width: root.sweepStart ? Math.abs(root.sweepStart[0]-root.sweepEnd[0]) : 0
        height: root.sweepStart ? Math.abs(root.sweepStart[1]-root.sweepEnd[1]) : 0
        color: Theme.colors.overlay.sweep_fill; border.color: root.sweepRemove ? Theme.colors.overlay.remove_3d : root.accentColor
    }
    M.TextField {
        id: transformField
        objectName: "transformValue"
        visible:false;width:110;height:32
        x: root.width/2;y:root.height/2
        onAccepted: { sceneBackend.transformTyped(root.lastHandle,text);visible=false;root.forceActiveFocus() }
        Keys.onEscapePressed: root.cancel(true)
    }
    M.OverlayField {
        // R534: the plan's field over a view, with what it is and its unit, held by the corner it was opened from
        id: vertexField
        objectName: "vertexHeight"
        visible: false
        colours: sceneBackend.overlayColors
        readonly property int chosen: root.verticesData.filter(v=>v.selected).length
        label: root.fieldMode==="shift" ? sceneBackend.vertexFieldText.shift
               : chosen>1 ? sceneBackend.vertexFieldText.heights.replace("{n}", chosen) : sceneBackend.vertexFieldText.height
        readonly property var place: root.fieldPlace(width, height)
        x: place[0]; y: place[1]
        onAccepted: { sceneBackend.vertexHeight(text); root.closeField(); root.forceActiveFocus() }
        onCanceled: { root.cancel(false); root.forceActiveFocus() }
    }
    M.Menu {
        id: vertexMenu
        M.MenuItem { text: qsTr("Height above the ground…"); onTriggered: root.openField(root.vertexOrigin, root.vertexOrigin[1].toFixed(2).replace(".",","), "height", true) }
        M.MenuItem { text: qsTr("Raise or lower by…"); onTriggered: root.openField(root.vertexOrigin, "+", "shift", false) }
        M.MenuItem { text: qsTr("Make it pitched"); onTriggered: sceneBackend.vertexAction("pitched") }
        M.MenuItem { text: qsTr("Weld with…"); onTriggered: sceneBackend.vertexAction("weld") }
        M.MenuItem { text: qsTr("Part"); onTriggered: sceneBackend.vertexAction("detach") }
        M.MenuItem { text: qsTr("Back on one plane"); onTriggered: sceneBackend.vertexAction("unfold") }
        M.MenuItem { text: qsTr("Choose all the corners"); onTriggered: sceneBackend.vertexAction("all") }
    }
    M.Menu {
        id: viewMenu
        objectName: "sceneContextMenu"
        // The entries are asked when the menu opens, not at every selection: made at each selectionChanged they
        // cost 40-230 ms of items (06/11/2026, R465).
        property var actions: []
        Instantiator {
            model: viewMenu.actions
            delegate: M.MenuItem {
                required property var modelData
                objectName: "sceneAction_" + modelData.key
                text: modelData.text
                enabled: modelData.key !== ""
                implicitHeight: modelData.key === "" ? 9 : Theme.size.CONTROL
                background: Rectangle {
                    color: parent.highlighted ? Theme.colors.hover : "transparent"
                    Rectangle { visible: modelData.key === ""; height: 1; color: Theme.colors.line; width: parent.width; anchors.centerIn: parent }
                }
                onTriggered: {
                    if (modelData.key === "rename") { renameField.text=sceneBackend.selectionName; renameDialog.open() }
                    else if (modelData.key === "frame") root.requestCommand("fit")
                    else sceneBackend.contextCommand(modelData.key, "")
                }
            }
            onObjectAdded: (index, object) => viewMenu.insertItem(index, object)
            onObjectRemoved: (index, object) => viewMenu.removeItem(object)
        }
    }
    M.Dialog {
        id: renameDialog
        objectName: "sceneRename"
        x: Math.max(0,(root.width-width)/2); y: Math.max(0,(root.sceneHeight-height)/2)
        width: Math.min(root.width,360)
        title: qsTr("Rename")
        acceptText: qsTr("OK"); rejectText: qsTr("Cancel")
        contentItem: M.TextField { id: renameField; objectName: "sceneRenameField"; onAccepted: renameDialog.accept() }
        onOpened: { renameField.forceActiveFocus(); renameField.selectAll() }
        onAccepted: sceneBackend.contextCommand("rename",renameField.text)
    }
    ViewCube {
        id: cube
        anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 6
        compact: root.width*root.sceneHeight < 256000
        bearing: root.bearing; elevation: root.elevation; dark: root.dark
        orthographic: root.cameraState.ortho
        onOrientRequested: (b,e) => { root.userMoved=true; root.go(Cam.orient(root.cameraState,b,e),true) }
        onHomeRequested: root.home()
        onFitRequested: root.fitScene()
        onSetHomeRequested: root.homeState = Cam.copy(root.cameraState)
        onOrthographicRequested: enabled => { let s=Cam.copy(root.cameraState); s.ortho=enabled; root.cameraState=s }
    }
    SceneToolbar {
        visible: root.showTools
        x: 8; y: x+width > cube.x ? cube.y+cube.height+8 : 8
        viewport: root
        showViews: root.showViewSelector
        onViewRequested: mode => root.viewRequested(mode)
    }
    Text {
        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 12
        font: root.font
        text: sceneBackend.error; color: Theme.colors.danger; width: Math.min(420,root.width/2)
        wrapMode: Text.Wrap
    }
    }
    Keys.onShortcutOverride: event => { if (event.key === Qt.Key_Escape) event.accepted=true }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Control) root.ctrlHeld=true
        if (event.key === Qt.Key_Space) { if (!event.isAutoRepeat) { root.spaceHeld=true; root.depthPoint=null }; event.accepted=true }
        else if (event.key === Qt.Key_Escape) { root.cancel(true); event.accepted=true }
        else if (root.placing && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) { root.placeRequested("enter", [0, 0, 0], 0, 0); event.accepted=true }
        else if (event.key === Qt.Key_F) { root.requestCommand("fit"); event.accepted=true }
        else if (event.key === Qt.Key_Home) { root.home(); event.accepted=true }
        else if (event.key === Qt.Key_Plus || event.key === Qt.Key_Equal) { root.requestCommand("zoom_in"); event.accepted=true }
        else if (event.key === Qt.Key_Minus) { root.requestCommand("zoom_out"); event.accepted=true }
        else if (event.key === Qt.Key_Delete) { sceneBackend.contextCommand("delete",""); event.accepted=true }
        else if (event.key === Qt.Key_Z && event.modifiers & Qt.ControlModifier) { sceneBackend.undo(); event.accepted=true }
        else if (event.key === Qt.Key_Y && event.modifiers & Qt.ControlModifier) { sceneBackend.redo(); event.accepted=true }
        else if (event.key === Qt.Key_F3) { root.snaps=!root.snaps; event.accepted=true }
        else if (root.editVertices && root.verticesData.some(v=>v.selected) && event.text && /^[0-9+.,-]$/.test(event.text)) {
            let index=root.verticesData.findIndex(v=>v.selected)
            sceneBackend.beginVertex(index,false);root.vertexOrigin=root.verticesData[index].point.slice()
            root.openField(root.vertexOrigin, event.text, "height", false);event.accepted=true
        }
        else if (root.editVertices && root.verticesData.some(v=>v.selected) && (event.key===Qt.Key_Up || event.key===Qt.Key_Down)) {
            // R356: the arrows raise or lower the corners chosen together, one undo step each
            let step=event.modifiers&Qt.ControlModifier ? 0.01 : event.modifiers&Qt.ShiftModifier ? 1 : 0.1
            sceneBackend.beginVertex(root.verticesData.findIndex(v=>v.selected),false)
            sceneBackend.commitVertex(event.key===Qt.Key_Up ? step : -step);event.accepted=true
        }
        else if (root.moveMode && [Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down].indexOf(event.key)>=0) {
            let step=event.modifiers&Qt.ControlModifier ? 0.01 : event.modifiers&Qt.ShiftModifier ? 1 : 0.1
            sceneBackend.nudge(event.key===Qt.Key_Left ? -step : event.key===Qt.Key_Right ? step : 0,
                               event.key===Qt.Key_Down ? -step : event.key===Qt.Key_Up ? step : 0);event.accepted=true
        } else if (root.moveMode && event.text && /^[0-9+.,-]$/.test(event.text)) {
            transformField.text=event.text;transformField.visible=true;transformField.forceActiveFocus();event.accepted=true
        }
    }
    Keys.onReleased: event => {
        if (event.key === Qt.Key_Control) root.ctrlHeld=false
        if (event.key === Qt.Key_Space && !event.isAutoRepeat) { root.spaceHeld=false; Nav.reset(root.nav); event.accepted=true }
    }
    onActiveFocusChanged: if (!activeFocus) { spaceHeld=false; Nav.reset(nav) }
    SunBar {
        id: sunBar
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: implicitHeight; visible: root.showTools
        backend: root.sceneBackend
        surfaceColor: root.commandsLinked ? Theme.colors.panel : Theme.colors.window
    }
}
