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
    width: compact ? 76 : 112
    height: width
    padding: 0
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.label.size
    font.weight: Theme.text.label.weight
    font.capitalization: Font.AllUppercase
    property real bearing: 30
    property real elevation: -35
    property bool compact: false
    property bool dark: false
    property bool orthographic: false
    // The host binds theme tokens; the standalone component remains usable.
    property color faceColor: Theme.colors.panel
    property color edgeColor: Theme.colors.line_soft
    property color lineColor: Theme.colors.muted
    property color textColor: Theme.colors.text
    property color hoverColor: Theme.colors.select_bg
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

    function point(v, scale) {
        let p = CubeMath.project(v,basis,scale);
        return Qt.point(width/2+p[0],height/2+p[1]);
    }
    function compass() {
        return [{text:qsTr("N"),pos:point([0,-0.35,-1],45),bearing:180},
                {text:qsTr("S"),pos:point([0,-0.35,1],45),bearing:0},
                {text:qsTr("E"),pos:point([1,-0.35,0],45),bearing:270},
                {text:qsTr("W"),pos:point([-1,-0.35,0],45),bearing:90}];
    }
    function hit(x,y) {
        if (x>=width-17 && y>=height-15) return "menu";
        if (!compact) {
            if (x>=1 && x<=19 && y>=1 && y<=17) return "home";
            let arrows = [["up",56,4],["down",56,108],["left",4,56],["right",108,56]];
            for (let i=0;i<arrows.length;i++)
                if (Math.hypot(x-arrows[i][1],y-arrows[i][2])<=8) return arrows[i][0];
            let letters = compass();
            for (let j=0;j<letters.length;j++)
                if (Math.hypot(x-letters[j].pos.x,y-letters[j].pos.y)<8) return "letter:"+j;
        }
        let part = CubeMath.pick(projectedCells,x-width/2,y-height/2);
        return part ? "part:"+part.join(",") : "";
    }
    function activate(target, doubleClick) {
        let orientation;
        if (target.indexOf("part:") === 0) {
            orientation = CubeMath.lookingFrom(target.substring(5).split(",").map(Number),bearing);
            orientRequested(orientation[0],orientation[1]);
            if (doubleClick) fitRequested();
        } else if (["left","right","up","down"].indexOf(target)>=0) {
            orientation = CubeMath.turned(bearing,elevation,target);
            orientRequested(orientation[0],orientation[1]);
        } else if (target.indexOf("letter:") === 0) {
            orientRequested(compass()[Number(target.substring(7))].bearing,elevation);
        } else if (target === "home") homeRequested();
        else if (target === "menu") cubeMenu.popup(root.width-17,root.height);
    }
    function polygonPath(polygon) {
        let points = polygon.map(function(p) { return Qt.point(width/2+p[0],height/2+p[1]); });
        points.push(points[0]);
        return points;
    }
    function ringPath() {
        let points = [];
        for (let i=0;i<=48;i++) {
            let angle=2*Math.PI*i/48;
            points.push(point([Math.sin(angle),-0.35,-Math.cos(angle)],45));
        }
        return points;
    }
    readonly property real drawingOpacity: pointer.containsMouse ? 1 : 0.55
    // Native vector paths share the scene graph with View3D. A Canvas texture
    // can miss the first grab of an unexposed native window, leaving only text.
    Shape {
        anchors.fill: parent
        visible: !root.compact
        opacity: root.drawingOpacity
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: "transparent"; strokeColor: root.lineColor; strokeWidth: 1
            PathPolyline { path: root.ringPath() }
        }
    }
    Repeater {
        model: root.compact ? 0 : 4
        Text {
            required property int index
            property var modelData: root.compass()[index]
            x: modelData.pos.x-9; y: modelData.pos.y-9; width:18; height:18
            text: modelData.text; color: root.textColor; font: root.font
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
    }
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
                strokeColor: root.lineColor; strokeWidth: 0.8
                fillColor: root.hoverTarget === "part:"+cell.modelData.part.join(",") ? root.hoverColor
                           : cell.modelData.face ? root.faceColor : root.edgeColor
                PathPolyline { path: root.polygonPath(cell.modelData.polygon) }
            }
        }
    }
    Repeater {
        model: root.compact ? [] : [[0,-1],[0,1],[-1,0],[1,0]]
        Shape {
            id: arrow
            required property var modelData
            required property int index
            anchors.fill: parent
            opacity: root.drawingOpacity
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: 0
                fillColor: root.hoverTarget === ["up","down","left","right"][arrow.index] ? root.textColor : root.lineColor
                PathPolyline {
                    path: [Qt.point(56+54.5*arrow.modelData[0],56+54.5*arrow.modelData[1]),
                           Qt.point(56+50*arrow.modelData[0]-4.5*arrow.modelData[1],56+50*arrow.modelData[1]+4.5*arrow.modelData[0]),
                           Qt.point(56+50*arrow.modelData[0]+4.5*arrow.modelData[1],56+50*arrow.modelData[1]-4.5*arrow.modelData[0]),
                           Qt.point(56+54.5*arrow.modelData[0],56+54.5*arrow.modelData[1])]
                }
            }
        }
    }
    Shape {
        anchors.fill: parent
        opacity: root.drawingOpacity
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: "transparent"
            strokeColor: root.compact ? "transparent" : root.hoverTarget === "home" ? root.textColor : root.lineColor
            strokeWidth: 1.2
            PathPolyline { path: [Qt.point(3,9),Qt.point(10,3),Qt.point(17,9),Qt.point(15,9),
                                  Qt.point(15,15),Qt.point(5,15),Qt.point(5,9),Qt.point(3,9)] }
        }
        ShapePath {
            fillColor: "transparent"; strokeColor: root.hoverTarget === "menu" ? root.textColor : root.lineColor; strokeWidth: 1.2
            PathPolyline { path: [Qt.point(root.width-13,root.height-10),Qt.point(root.width-9,root.height-5),
                                  Qt.point(root.width-5,root.height-10)] }
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
    M.ToolTip {
        visible: pointer.containsMouse && (root.hoverTarget === "home" || root.hoverTarget === "menu")
        text: root.hoverTarget === "home" ? qsTr("Home: the starting view, or the one set as Home") : qsTr("Perspective or parallel, fit, set this view as Home")
    }
    M.Menu {
        id: cubeMenu
        objectName: "viewCubeMenu"
        M.MenuItem { text: qsTr("Go to Home"); visible: root.compact; enabled: visible; height: visible ? implicitHeight : 0; onTriggered: root.homeRequested() }
        M.MenuItem { text: qsTr("Parallel projection"); checkable: true; checked: root.orthographic; onTriggered: root.orthographicRequested(!root.orthographic) }
        M.MenuItem { text: qsTr("Fit to the drawing"); onTriggered: root.fitRequested() }
        M.MenuItem { text: qsTr("Set this view as Home"); onTriggered: root.setHomeRequested() }
    }
}
