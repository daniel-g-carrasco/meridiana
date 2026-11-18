import QtQuick
import QtQuick.Shapes
import Meridiana.Plan.Paths 1.0

ModulePaths {
    id: batch
    property bool curves: true
    property bool sync: false       // built on the GUI thread at once: small layers that must never go blank (R496)
    // the dashes follow the zoom the wheel settled on, not every step (R498): a new pattern is a new path
    property real viewScale: parent ? Math.max(.00002, Math.abs(parent.settledScale!==undefined ? parent.settledScale : parent.scale)) : 1
    readonly property bool ready: {
        for (var i=0;i<shapes.count;i++) {
            var shape=shapes.itemAt(i)
            if (!shape || shape.status!==Shape.Ready) return false
        }
        return shapes.count===paths.length
    }
    Repeater {
        id: shapes
        model: batch.paths
        delegate: Shape {
            required property var modelData
            asynchronous: !batch.sync
            preferredRendererType: batch.curves ? Shape.CurveRenderer : Shape.GeometryRenderer
            ShapePath {
                fillColor: modelData.fill
                strokeColor: modelData.stroke
                strokeWidth: modelData.width
                cosmeticStroke: true
                strokeStyle: modelData.dashed ? ShapePath.DashLine : ShapePath.SolidLine
                dashPattern: modelData.dashed ? [4/batch.viewScale, 2/batch.viewScale] : [4,2]
                joinStyle: ShapePath.MiterJoin
                fillRule: ShapePath.WindingFill
                PathSvg { path: modelData.path }
            }
        }
    }
}
