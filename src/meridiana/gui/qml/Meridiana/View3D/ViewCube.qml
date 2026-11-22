pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M
import "CubeMath.js" as CubeMath

Control {
    id: root
    objectName: "viewCube"
    width: M.ControlMetrics.viewCube
    height: width
    padding: 0
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.label.size
    font.weight: Theme.text.label.weight
    font.capitalization: Font.AllUppercase
    property real bearing: 30
    property real elevation: -35
    readonly property bool compact: true
    property bool dark: false
    property bool orthographic: false
    // The host binds theme tokens; the standalone component remains usable.
    property color faceColor: Theme.colors.panel
    property color edgeColor: Theme.colors.line_soft
    property color lineColor: Theme.colors.muted
    property color textColor: Theme.colors.text
    property color hoverColor: Theme.colors.hover
    palette.window: faceColor
    palette.windowText: textColor
    palette.button: faceColor
    palette.buttonText: textColor
    palette.text: textColor
    palette.highlight: hoverColor
    property var projectedCells: CubeMath.cells(bearing,elevation,64)
    property var basis: CubeMath.axes(bearing,elevation)
    property string hoverTarget: ""
    readonly property var faceNames: [qsTr("Top"),qsTr("Bottom"),qsTr("N"),qsTr("S"),qsTr("E"),qsTr("W")]
    signal orientRequested(real bearing, real elevation)
    signal homeRequested()
    signal setHomeRequested()
    signal orthographicRequested(bool enabled)
    signal fitRequested()

    function hit(x,y) {
        let part = CubeMath.pick(projectedCells,x-width/2,y-height/2);
        return part ? "part:"+part.join(",") : "";
    }
    function activate(target, doubleClick) {
        let orientation;
        if (target.indexOf("part:") === 0) {
            orientation = CubeMath.lookingFrom(target.substring(5).split(",").map(Number),bearing);
            orientRequested(orientation[0],orientation[1]);
            if (doubleClick) fitRequested();
        }
    }
    function polygonPath(polygon) {
        let points = polygon.map(function(p) { return Qt.point(width/2+p[0],height/2+p[1]); });
        points.push(points[0]);
        return points;
    }
    function shade(cell) {
        let share = cell.normal === 0 ? 0 : cell.normal === 3 ? 0.09 : 0.17;
        return Theme.mix(faceColor, textColor, share);
    }
    readonly property real drawingOpacity: 1
    Repeater {
        model: root.projectedCells.length
        Shape {
            id: cell
            required property int index
            property var modelData: root.projectedCells[index]
            anchors.fill: parent
            opacity: root.drawingOpacity
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: Theme.mix(root.faceColor, root.textColor, 0.32); strokeWidth: 0.8
                fillColor: root.shade(cell.modelData)
                PathPolyline { path: root.polygonPath(cell.modelData.polygon) }
            }
            ShapePath {
                strokeWidth: 0
                fillColor: root.hoverTarget === "part:"+cell.modelData.part.join(",") ? root.hoverColor : "transparent"
                PathPolyline { path: root.polygonPath(cell.modelData.polygon) }
            }
        }
    }
    // Text remains crisp and fully opaque; it inherits the chosen application font.
    Repeater {
        model: root.projectedCells.length
        Text {
            required property int index
            property var modelData: root.projectedCells[index]
            visible: modelData.face && width>9 && height>7
            property var xs: modelData.polygon.map(function(p) {return p[0]})
            property var ys: modelData.polygon.map(function(p) {return p[1]})
            x: root.width/2+Math.min.apply(null,xs)
            y: root.height/2+Math.min.apply(null,ys)
            width: Math.max.apply(null,xs)-Math.min.apply(null,xs)
            height: Math.max.apply(null,ys)-Math.min.apply(null,ys)
            text: root.faceNames[modelData.normal]
            color: root.textColor
            font: root.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.hoverTarget ? Qt.PointingHandCursor : Qt.ArrowCursor
        onPositionChanged: function(mouse) { root.hoverTarget=root.hit(mouse.x,mouse.y) }
        onExited: root.hoverTarget=""
        onPressed: function(mouse) { if (!root.hit(mouse.x,mouse.y)) mouse.accepted=false }
        onClicked: function(mouse) { root.activate(root.hit(mouse.x,mouse.y),false) }
        onDoubleClicked: function(mouse) { root.activate(root.hit(mouse.x,mouse.y),true) }
    }
}
