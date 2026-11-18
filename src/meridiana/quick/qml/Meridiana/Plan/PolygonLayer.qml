import QtQuick
import QtQuick.Shapes
import Meridiana.Theme

Item {
    id: polygonsLayer
    property var objects: []
    property bool modules: false
    property bool halo: false
    // the dashes follow the zoom the wheel settled on, as in ModuleBatch (R541): a dash pattern made again at every
    // step of the wheel is every dashed outline laid out again at every frame
    property real viewScale: parent ? Math.max(.00002, Math.abs(parent.settledScale!==undefined ? parent.settledScale : parent.scale)) : 1
    property url hatchSource
    property matrix4x4 patternTransform: Qt.matrix4x4()
    Image { id: hatchImage; source: polygonsLayer.hatchSource; smooth: false }
    ShaderEffectSource {
        id: hatch; visible: false; width: 8; height: 8; textureSize: Qt.size(8,8)
        sourceItem: hatchImage; hideSource: true; wrapMode: ShaderEffectSource.Repeat; smooth: false
    }
    property color moduleFill: Theme.colors.overlay.module
    property color moduleStroke: Theme.colors.overlay.module_line
    Repeater {
        model: polygonsLayer.objects
        delegate: Shape {
            required property var modelData
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: polygonsLayer.halo && modelData.closed ? Theme.colors.overlay.halo : "transparent"
                fillColor: "transparent"
                strokeWidth: modelData.width+3
                cosmeticStroke: true
                joinStyle: ShapePath.BevelJoin
                PathPolyline { path: modelData.points }
                PathLine {
                    x: modelData.points.length ? modelData.points[modelData.closed ? 0 : modelData.points.length-1].x : 0
                    y: modelData.points.length ? modelData.points[modelData.closed ? 0 : modelData.points.length-1].y : 0
                }
            }
            ShapePath {
                strokeColor: polygonsLayer.modules ? polygonsLayer.moduleStroke : modelData.stroke
                fillColor: polygonsLayer.modules ? polygonsLayer.moduleFill : modelData.fill
                fillItem: polygonsLayer.halo && modelData.kind==="exclusion" ? hatch : null
                fillTransform: polygonsLayer.patternTransform
                strokeWidth: polygonsLayer.modules ? 1 : modelData.width
                cosmeticStroke: true
                strokeStyle: modelData.dashed ? ShapePath.DashLine : ShapePath.SolidLine
                dashPattern: modelData.dashed ? [4/polygonsLayer.viewScale, 2/polygonsLayer.viewScale] : [4,2]
                joinStyle: ShapePath.BevelJoin
                PathPolyline { path: modelData.points }
                PathLine {
                    x: modelData.points.length ? modelData.points[polygonsLayer.modules || modelData.closed ? 0 : modelData.points.length-1].x : 0
                    y: modelData.points.length ? modelData.points[polygonsLayer.modules || modelData.closed ? 0 : modelData.points.length-1].y : 0
                }
            }
        }
    }
}
