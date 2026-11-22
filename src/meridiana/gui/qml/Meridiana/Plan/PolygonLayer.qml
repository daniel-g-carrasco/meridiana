import QtQuick
import QtQuick.Window
import Meridiana.Controls as M
import QtQuick.Shapes
import Meridiana.Theme
Item {
    id: polygonsLayer
    property var objects: []
    property bool modules: false
    property bool halo: false
    // the tint of the buildings and of the sub-fields; off over the sun map, whose colours are what is read there
    property bool grounds: true
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
            id: strokeShape0
            required property var modelData
            readonly property var outline: {
                const p = modelData.points
                const closed = polygonsLayer.modules || modelData.closed
                return closed && p.length ? p.concat([p[0]]) : p
            }
            // GeometryRenderer retains the polygons in full native windows; Plan supplies MSAA.
            preferredRendererType: Shape.GeometryRenderer
            antialiasing: true
            // A dashed outline is the curve renderer's (R706), as the strings' dashes: it keeps the dashes it built
            // at the settled zoom. The triangle renderer strokes a cosmetic pen again at every new scale, and for a
            // dashed one that is every dash of the whole outline, on screen or not: a sub-field's outline cost
            // 50-170 ms at each step nearer, more the nearer the view.
            readonly property bool dashedOutline: modelData.dashed ? true : false
            M.ViewPath {
                surface: strokeShape0
                halo: true
                ink: strokeShape0.dashedOutline ? "transparent"
                     : polygonsLayer.modules ? polygonsLayer.moduleStroke : modelData.stroke
                viewScale: polygonsLayer.viewScale
                fillColor: "transparent"
                fillItem: null
                cosmeticStroke: true
                PathPolyline { path: strokeShape0.outline }
            }
            M.ViewPath {
                surface: strokeShape0
                viewScale: polygonsLayer.viewScale
                strokeColor: strokeShape0.dashedOutline ? "transparent"
                    : polygonsLayer.modules ? polygonsLayer.moduleStroke : modelData.stroke
                fillColor: polygonsLayer.modules ? polygonsLayer.moduleFill
                    : !polygonsLayer.grounds && (modelData.kind==="building" || modelData.kind==="subfield") ? "transparent"
                    : modelData.fill
                fillItem: polygonsLayer.halo && modelData.kind==="exclusion" ? hatch : null
                // only where the hatch is: a transform set anew makes Qt build the whole path again
                fillTransform: fillItem ? polygonsLayer.patternTransform : Qt.matrix4x4()
                cosmeticStroke: true
                PathPolyline { path: strokeShape0.outline }
            }
            Loader {
                active: strokeShape0.dashedOutline
                sourceComponent: Shape {
                    id: dashes
                    objectName: "dashedOutline"
                    preferredRendererType: Shape.CurveRenderer
                    asynchronous: true          // the dashes of a whole outline, built off the window's thread
                    M.ViewPath {
                        surface: dashes
                        halo: true
                        ink: polygonsLayer.modules ? polygonsLayer.moduleStroke : modelData.stroke
                        viewScale: polygonsLayer.viewScale
                        fillColor: "transparent"
                        cosmeticStroke: true
                        dashed: true
                        PathPolyline { path: strokeShape0.outline }
                    }
                    M.ViewPath {
                        surface: dashes
                        viewScale: polygonsLayer.viewScale
                        strokeColor: polygonsLayer.modules ? polygonsLayer.moduleStroke : modelData.stroke
                        fillColor: "transparent"
                        cosmeticStroke: true
                        dashed: true
                        PathPolyline { path: strokeShape0.outline }
                    }
                }
            }
        }
    }
}
