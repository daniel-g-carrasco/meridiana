// The Widgets card clips its four six-pixel corners. Four small paths avoid
// adding another full-scene offscreen texture just to mask the native view.
import QtQuick
import QtQuick.Shapes
import Meridiana.Theme

Item {
    id: root
    Repeater {
        model: 4
        Shape {
            required property int index
            width: Theme.radius.CONTROL; height: width
            x: index === 1 || index === 2 ? root.width-width : 0
            y: index >= 2 ? root.height-height : 0
            rotation: index*90
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: 0; fillColor: Theme.colors.card
                startX: 0; startY: 0
                PathLine { x: Theme.radius.CONTROL; y: 0 }
                PathArc { x: 0; y: Theme.radius.CONTROL; radiusX: Theme.radius.CONTROL; radiusY: radiusX; direction: PathArc.Counterclockwise }
                PathLine { x: 0; y: 0 }
            }
        }
    }
}
