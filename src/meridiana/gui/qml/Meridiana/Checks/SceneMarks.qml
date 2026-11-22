import QtQuick
import Meridiana.Controls as M
import Meridiana.Theme

// Same world anchors and screen-size marks as ui/marks.MarksOverlay.
Item {
    id: root
    objectName: "check-scene-marks"
    required property var view
    required property var backend
    required property var symbols
    width: view.width
    height: view.sceneHeight
    clip: true
    z: Theme.stack.MARK            // R616: under the cube and the tools (its Loader's step too)
    Repeater {
        model: root.backend.marks3d
        delegate: M.CheckMark {
            required property var modelData
            objectName: "scene-mark-" + modelData.kind + "-" + modelData.oid
            readonly property var point: root.view.projectPoint(modelData.point)
            visible: point !== null && point[0] >= -width && point[0] <= root.width + width && point[1] >= -height && point[1] <= root.height + height
            x: point ? point[0] - width / 2 : 0
            y: point ? point[1] - height / 2 - 18 * 0.7 : 0
            width: M.ControlMetrics.viewMark; height: width     // as on the plan (PlanSymbol, views)
            symbols: root.symbols
            level: modelData.level
            count: modelData.count
            views: true
            // R641: the hand, the words of its checks, and the click to them, as on the plan
            M.MarkArea {
                tip: modelData.tip || ""
                onClicked: { root.view.forceActiveFocus(); root.backend.markClick(modelData.kind, modelData.oid) }
            }
        }
    }
}
