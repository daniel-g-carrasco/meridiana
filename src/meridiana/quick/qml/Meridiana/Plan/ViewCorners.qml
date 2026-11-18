import QtQuick
import QtQuick.Shapes
import Meridiana.Theme

// ui.cards.Corner: four native wedges over the view, transparent to input.
// No layer or full-view texture is needed while the camera moves.
Item {
    id: corners
    property real radius: Theme.radius.VIEW
    property color color: Theme.colors.panel
    Repeater {
        model: 4
        delegate: Shape {
            required property int index
            objectName: "planCorner"+index
            width: corners.radius; height: width
            x: index % 2 ? corners.width-width : 0
            y: index >= 2 ? corners.height-height : 0
            rotation: [0, 90, 270, 180][index]
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: -1; fillColor: corners.color
                PathSvg { path: "M0,0 L"+corners.radius+",0 A"+corners.radius+","+corners.radius+
                                " 0 0 0 0,"+corners.radius+" Z" }
            }
        }
    }
}
