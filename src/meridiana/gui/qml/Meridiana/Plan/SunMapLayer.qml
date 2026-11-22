import QtQuick
import QtQuick.Shapes
import Meridiana.Theme

// The sun map laid on the plan (study 45, package 5), in the plan's world layer under the outlines: for each surface
// its image, painted by backend/plan_map.py (the tiles in the scale's colours, cut on the surface's contour so that the
// tiles of the border never leave it, those under an obstacle hatched), laid on the plan by its matrix; a surface whose
// map is old is dimmed by a veil until the new one comes (it does not blink). One delegate per row of sun.surfaces: a
// surface that changes is one row, the others are not drawn again. Plain images and a plain fill: the same on every
// renderer, the software one too.
Item {
    id: layer
    property var sun: null
    visible: !!sun && sun.on
    Repeater {
        model: layer.sun ? layer.sun.surfaces : null
        delegate: Item {
            id: surface
            required property string sid
            required property string source
            required property var ring
            required property var matrix
            required property int cols
            required property int rows
            required property bool coloured
            required property bool stale
            objectName: "sunMapSurface-" + sid
            visible: coloured
            Image {
                objectName: "sunMapImage"
                source: surface.coloured ? surface.source : ""
                width: surface.cols; height: surface.rows
                smooth: false; cache: false; asynchronous: false
                transform: Matrix4x4 {
                    matrix: { const m = surface.matrix
                        return Qt.matrix4x4(m[0], m[1], 0, m[2], m[3], m[4], 0, m[5], 0, 0, 1, 0, 0, 0, 0, 1) }
                }
            }
            // made only while the map is old: a Shape in every row cost each new surface's row 5-8 ms on the
            // window's thread on screen (model A, 14/11/2026), past the guard's 5 ms
            Loader {
                active: surface.stale
                sourceComponent: Shape {
                    objectName: "sunMapVeil"
                    preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        strokeColor: "transparent"; fillColor: Theme.colors.sun_map.stale
                        PathPolyline { path: surface.ring }
                    }
                }
            }
        }
    }
}
