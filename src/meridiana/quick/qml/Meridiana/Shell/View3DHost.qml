import QtQuick
import Meridiana.View3D

// The real 3D view in the window's slot; the Loader around it gives it its size.
// R23 F6 (docs/studio/39-contratto-backend-qml.md): the scene controls (backend/scene_part.SceneControls) are bound
// here, their requests answered here; the backend never holds this view nor writes its properties.
Viewport {
    id: view
    sceneBackend: sceneBackendObject
    readonly property QtObject controls: typeof sceneControls !== "undefined" ? sceneControls : null
    property bool applyingControls: false
    commandsLinked: controls !== null
    navigationStyle: controls ? controls.navigationStyle : "autocad"
    orbitMode: controls ? controls.orbitMode : "turntable"
    pivotMode: controls ? controls.pivotMode : "cursor"
    pivotHint: controls ? controls.pivotHint : true
    edgeQuality: controls ? controls.edgeQuality : "full"
    showViewSelector: controls ? controls.viewSelector : false
    placing: controls ? controls.placing : false        // R554: the plan's tool «3D object», fed from the 3D view too
    // the plan's tool and snaps, applied at a change (the user writes them too: a binding would be broken)
    function applyControls() {
        if (!controls) return
        applyingControls = true
        moveMode = controls.moveMode
        editVertices = controls.moveMode
        snaps = controls.snaps
        applyingControls = false
    }
    Component.onCompleted: applyControls()
    Connections {
        target: view.controls
        function onToolChanged() { view.applyControls() }
        function onFitRequested() { view.frameSelection() }
        function onZoomRequested(direction) { view.zoomBy(direction) }
    }
    Binding { target: view.controls; property: "viewFocused"; value: view.visible && view.activeFocus; when: view.controls !== null }
    onCommandRequested: command => { if (controls) controls.viewButton(command) }
    onViewRequested: mode => { if (controls) controls.viewWanted(mode) }
    onPlaceRequested: (how, point, bits, mpp) => { if (controls) controls.viewPlace(how, point[0], point[1], point[2], bits, mpp) }
    onMoveModeChanged: if (controls && !applyingControls) controls.viewTool(moveMode || editVertices)
    onEditVerticesChanged: if (controls && !applyingControls) controls.viewTool(moveMode || editVertices)
    onSnapsChanged: if (controls && !applyingControls) controls.viewSnaps(snaps)
    // the checks' marks on the scene, made here (properties_part made them from Python and kept them)
    Loader {
        parent: view; z: 5
        Component.onCompleted: if (typeof inspectors !== "undefined" && inspectors)
            setSource("../Checks/SceneMarks.qml", {view: view, backend: inspectors, symbols: checksBackend.symbols})
    }
}
