import QtQuick
import Meridiana.Controls as M

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
    z: 5
    Repeater {
        model: root.backend.marks3d
        delegate: M.CheckMark {
            required property var modelData
            objectName: "scene-mark-" + modelData.kind + "-" + modelData.oid
            readonly property var point: root.view.projectPoint(modelData.point)
            visible: point !== null && point[0] >= -22 && point[0] <= root.width + 22 && point[1] >= -22 && point[1] <= root.height + 22
            x: point ? point[0] - width / 2 : 0
            y: point ? point[1] - height / 2 - 18 * 0.7 : 0
            width: 22; height: 22       // R464: in a disc of the plan's pills, as on the plan (ui/marks.PILL)
            symbols: root.symbols
            level: modelData.level
            count: modelData.count
            views: true
        }
    }
}
