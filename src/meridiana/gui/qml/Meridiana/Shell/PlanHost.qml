import QtQuick
import Meridiana.Plan
import Meridiana.Theme

// The real plan in the window's slot, with the little the Workbench asks of what stands there.
Item {
    id: host
    property string tool: "select"
    property alias zoom: plan.zoom
    property string statusText: plan.statusText
    property string cursorText: plan.cursorText
    property string measureText: plan.backend.measureText
    property string viewMode: "both"        // bound by Workbench.qml (R23 F6: plan_part wrote the plan's from Python)
    readonly property Item view: plan       // the plan itself, for the tools that read its camera (gesture_trace.py)
    function fit() { plan.fit() }
    function northUp() { plan.bearing=0 }
    onToolChanged: if (planBackend.tool !== tool) planBackend.setTool(tool === "rectangle" ? "building" : tool)
    Connections { target: planBackend; function onStateChanged() { host.tool = planBackend.tool } }
    // the sun map of the window (backend/plan_map.py), where the window has one
    readonly property var sunMapBridge: typeof sunMap !== "undefined" ? sunMap : null
    Plan { id: plan; anchors.fill: parent; backend: planBackend; viewMode: host.viewMode; sun: host.sunMapBridge }
    // R23 F6 (docs/studio/39): the side of the selection highlighted on the plan, made here (properties_part made it
    // from Python and kept it); the inspectors' request to frame bounds answered here. R616: a mark of the drawing,
    // under the bars over the plan (it had their z and, made after them, passed over all of them)
    Loader {
        parent: plan; anchors.fill: parent; z: Theme.stack.MARK
        Component.onCompleted: if (typeof inspectors !== "undefined" && inspectors) setSource("../Properties/SideHighlight.qml", {view: plan, backend: inspectors})
    }
    Connections {
        target: typeof inspectors !== "undefined" ? inspectors : null
        function onFitBoundsRequested(bounds) { plan.fitBounds(bounds) }
    }
}
