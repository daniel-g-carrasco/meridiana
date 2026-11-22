import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as MC

// R643 (Daniel 15/11/2026, proposal A of the sketches r35-bussola: «ago a due colori»): the sign of North over a view,
// the same in the plan (Plan/Compass.qml) and in the 3D view (View3D/Viewport.qml, under the cube). A needle on the
// overlays' glass, the North half in the overlays' ink, the South half in the same ink at Theme.signs.north.soft; the
// drawing is app/interface/north_sign.py, the one the report prints (report/figures.py). Turned (North not up) the
// pointer becomes a hand, the glass takes the hover layer under it and a click asks for North up again (`clicked`); the
// degrees, when given, stand under it in a pill of the same glass, never on the picture bare.
Item {
    id: root
    property real north: 0                  // where North points, degrees clockwise from the top of the screen
    property string degreesText: ""         // the pill under the sign: "" none
    property string tooltipText: ""
    property color ink: Theme.colors.overlay.ink
    property color ground: Theme.colors.overlay.glass
    property color hoverLayer: Theme.colors.overlay.hover
    readonly property var drawing: Theme.signs.north
    readonly property real side: MC.ControlMetrics.northSign
    readonly property bool turned: Math.round((((north % 360) + 360) % 360) * 10) % 3600 !== 0
    readonly property bool hovered: mouse.containsMouse
    signal clicked()
    width: side
    height: side + (degreesText.length > 0 ? Theme.space.XS + MC.ControlMetrics.northPill : 0)

    readonly property color _floor: hovered && turned ? Qt.tint(ground, hoverLayer) : ground

    Rectangle {
        objectName: "northDisc"
        width: root.side; height: root.side; radius: width / 2
        color: root._floor
    }
    Item {
        objectName: "northNeedle"
        width: root.drawing.box; height: root.drawing.box
        transform: [Rotation { origin.x: root.drawing.box / 2; origin.y: root.drawing.box / 2; angle: root.north },
                    Scale { xScale: root.side / root.drawing.box; yScale: root.side / root.drawing.box }]
        Shape {
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "transparent"
                fillColor: Qt.rgba(root.ink.r, root.ink.g, root.ink.b, root.drawing.soft)
                PathSvg { path: root.drawing.south }
            }
            ShapePath {
                strokeColor: "transparent"
                fillColor: root.ink
                PathSvg { path: root.drawing.north }
            }
        }
    }
    Rectangle {
        objectName: "northDegrees"
        visible: root.degreesText.length > 0
        y: root.side + Theme.space.XS
        x: (root.side - width) / 2
        width: degrees.implicitWidth + 2 * Theme.space.S
        height: MC.ControlMetrics.northPill
        radius: Theme.radius.CONTROL
        color: root._floor
        Text {
            id: degrees
            anchors.centerIn: parent
            text: root.degreesText
            color: root.ink
            font.family: Theme.fontFamily
            font.pixelSize: Theme.text.label.size
            font.weight: Theme.text.label.weight
            font.features: { "tnum": 1 }
        }
    }
    MouseArea {
        id: mouse
        width: root.side; height: root.side
        hoverEnabled: true
        cursorShape: root.turned ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
    MC.ToolTip { pressed: mouse.pressed; visible: mouse.containsMouse && root.tooltipText.length > 0; text: root.tooltipText }
}
