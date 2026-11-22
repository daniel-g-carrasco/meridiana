import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// The side shown from the Properties (inspectors.sideSegment) on the plan: the program's lit side (R617, M.LitSide).
// The plan's public projection follows zoom, bearing and pan entirely in QML.
M.LitSide {
    id: root
    objectName: "property-side-highlight"
    required property var view
    required property var backend
    anchors.fill: parent
    z: Theme.stack.MARK            // R616: a mark of the drawing, under the bars over the plan (its Loader's step too)
    visible: backend.sideSegment.length === 2 && view.backend.tool === "select"
    a: visible ? view.screen(backend.sideSegment[0][0], backend.sideSegment[0][1]) : Qt.point(0, 0)
    b: visible ? view.screen(backend.sideSegment[1][0], backend.sideSegment[1][1]) : Qt.point(0, 0)
    ink: view.backend.planColors.sel
}
