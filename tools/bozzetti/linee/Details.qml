import QtQuick
import QtQuick.Window
import QtQuick.Shapes
import Meridiana.Theme

Window {
    id: root
    width: 500; height: 610
    visible: true
    color: Theme.colors.window
    property string variant: "C"
    property url backgroundSource
    property var haloParts: []
    readonly property var points: [Qt.point(42,52), Qt.point(242,136.895), Qt.point(390,139.2), Qt.point(390,213)]
    readonly property var sides: [Qt.point(80,285), Qt.point(390,332), Qt.point(365,452), Qt.point(55,405)]
    function angle(a,b) { return Math.atan2(b.y-a.y,b.x-a.x)*180/Math.PI }
    function offset(a,b) {
        const dx=b.x-a.x, dy=b.y-a.y, length=Math.sqrt(dx*dx+dy*dy)
        return Qt.point((a.x+b.x)/2+17*dy/length, (a.y+b.y)/2-17*dx/length)
    }
    Image { anchors.fill: parent; source: root.backgroundSource; smooth: true; z: -2 }
    Repeater {
        model: 3
        delegate: DraftLine {
            required property int index
            anchors.fill: parent
            a: root.points[index]; b: root.points[index+1]
            ink: viewPaint.draw; haloInk: viewPaint.halo
            haloOpacity: root.variant === "C" ? .14 : 0
        }
    }
    Repeater {
        model: root.variant === "D" ? root.haloParts : []
        delegate: DraftLine {
            required property var modelData
            z: -1; haloOnly: true
            anchors.fill: parent
            a: Qt.point(modelData[0],modelData[1]); b: Qt.point(modelData[2],modelData[3])
            ink: viewPaint.draw; haloInk: viewPaint.halo; haloOpacity: .24
        }
    }
    Repeater {
        model: root.points
        delegate: Rectangle {
            required property var modelData
            width: 4.5; height: width; radius: width/2
            x: modelData.x-width/2; y: modelData.y-height/2
            color: viewPaint.draw; antialiasing: true
        }
    }
    Repeater {
        model: ["534,07 m", "482,16 m", "248,35 m"]
        delegate: DraftPill {
            required property int index
            required property string modelData
            readonly property point a: root.points[index]
            readonly property point b: root.points[index+1]
            readonly property point center: root.offset(a,b)
            x: center.x-width/2; y: center.y-height/2
            value: modelData; direction: root.angle(a,b)
        }
    }
    DraftPill { x: 245; y: 221; value: "Totale  1.264,58 m" }
    Repeater {
        model: 4
        delegate: Item {
            id: side
            required property int index
            readonly property point a: root.sides[index]
            readonly property point b: root.sides[(index+1)%4]
            readonly property point center: root.offset(a,b)
            anchors.fill: parent
            DraftLine {
                anchors.fill: parent; a: side.a; b: side.b
                ink: viewPaint.bld_stroke; haloInk: viewPaint.halo; haloOpacity: .14
            }
            DraftPill {
                x: side.center.x-width/2; y: side.center.y-height/2
                value: side.index%2 ? "18,04 m" : "43,49 m"; badge: String(side.index+1)
                direction: root.angle(side.a,side.b)
            }
        }
    }
    DraftLine { anchors.fill: parent; a: Qt.point(100,365); b: Qt.point(342,402); ink: viewPaint.sub_stroke }
    DraftPill { x: 175; y: 362; value: "S1 · 15 moduli"; badge: "S"; direction: 8.69 }
    Repeater {
        model: [1,2,15]
        delegate: Item {
            required property int index
            required property var modelData
            x: 100+index*140; y: 518
            Shape {
                width: 20; height: 20; preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeColor: "white"; strokeWidth: 1; fillColor: Theme.colors.warning_ink
                    startX: 10; startY: 0
                    PathLine { x: 20; y: 18 }
                    PathLine { x: 0; y: 18 }
                    PathLine { x: 10; y: 0 }
                }
            }
            DraftCounter { x: 15; y: -9; count: parent.modelData }
        }
    }
    DraftLine { anchors.fill: parent; a: Qt.point(45,598); b: Qt.point(135,559.797); ink: viewPaint.guide; dashed: true }
    DraftLine { anchors.fill: parent; a: Qt.point(205,585); b: Qt.point(460,585); ink: viewPaint.guide; dashed: true }
}
