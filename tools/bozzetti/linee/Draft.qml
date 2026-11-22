import QtQuick
import QtQuick.Window
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M

Window {
    id: root
    width: 1920; height: 1080
    visible: true
    color: Theme.colors.window
    Rectangle { anchors.fill: parent; color: Theme.colors.window }
    property string variant: "A"
    property string viewName: "Pianta"
    property url backgroundSource
    property var haloParts: []
    readonly property bool current: variant === "A"
    readonly property color measureInk: viewPaint.draw
    readonly property var points: [Qt.point(260, 190), Qt.point(760, 402.2374), Qt.point(1250, 410), Qt.point(1250, 670)]
    readonly property var sides: [Qt.point(260, 460), Qt.point(690, 525), Qt.point(660, 655), Qt.point(230, 590)]
    function angle(a, b) { return Math.atan2(b.y-a.y, b.x-a.x)*180/Math.PI }
    function label(a, b, offset) {
        const dx=b.x-a.x, dy=b.y-a.y, len=Math.sqrt(dx*dx+dy*dy)
        return Qt.point((a.x+b.x)/2 + dy/len*offset, (a.y+b.y)/2 - dx/len*offset)
    }
    Text {
        x: 28; y: 18
        text: root.variant + "  /  " + ({A:"Oggi", B:"Sottile", C:"Fuori linea", D:"Alone locale"})[root.variant] + "    ·    " + root.viewName
        color: Theme.colors.text; font.family: Theme.fontFamily; font.pixelSize: Theme.type.HEADING
    }
    Text {
        x: 28; y: 48; text: "Bozzetto su cattura reale · misure illustrative · 1920 × 1080 logici"
        color: Theme.colors.text2; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL
    }
    Item {
        id: drawing
        x: 0; y: 80; width: 1920; height: 700; clip: true
        Image { anchors.fill: parent; source: root.backgroundSource; fillMode: Image.PreserveAspectCrop; smooth: true }
        Repeater {
            model: 3
            delegate: DraftLine {
                required property int index
                anchors.fill: parent
                a: root.points[index]; b: root.points[index+1]; ink: root.measureInk
                thickness: root.current ? M.ControlMetrics.measureLine : 1.5
                haloExtra: root.current ? M.ControlMetrics.measureHalo : 2
                haloInk: viewPaint.halo
                haloOpacity: root.current ? 1 : root.variant === "D" ? 0 : .14
            }
        }
        Repeater {
            model: root.variant === "D" ? root.haloParts : []
            delegate: DraftLine {
                required property var modelData
                anchors.fill: parent
                a: Qt.point(modelData[0], modelData[1]); b: Qt.point(modelData[2], modelData[3])
                ink: root.measureInk; thickness: 1.5; haloOpacity: .24; haloInk: viewPaint.halo
            }
        }
        Repeater {
            model: root.points
            delegate: Rectangle {
                required property var modelData
                width: root.current ? 10 : 4.5; height: width; radius: width/2
                x: modelData.x-width/2; y: modelData.y-height/2
                color: root.measureInk; border.width: root.current ? 1.6 : 0
                border.color: viewPaint.halo; antialiasing: true
            }
        }
        Repeater {
            model: ["534,07 m", "482,16 m", "248,35 m"]
            delegate: Item {
                id: measure
                required property int index
                required property string modelData
                readonly property point a: root.points[index]
                readonly property point b: root.points[index+1]
                readonly property point midpoint: root.label(a,b, root.current ? 15 : root.variant === "B" ? 0 : 17)
                x: midpoint.x; y: midpoint.y
                M.SpanLabel {
                    visible: root.current; along: false; value: measure.modelData
                    x: -width/2; y: -height/2; rotation: root.angle(measure.a, measure.b) >= 90 ? root.angle(measure.a, measure.b)-180 : root.angle(measure.a, measure.b)
                    ink: root.measureInk; halo: viewPaint.halo
                }
                DraftPill {
                    visible: !root.current; value: measure.modelData
                    x: -width/2; y: -height/2; direction: root.angle(measure.a, measure.b)
                }
            }
        }
        DraftPill { x: 1320; y: 640; value: "Totale  1.264,58 m"; visible: !root.current }
        M.LengthPill { x: 1320; y: 640; value: "Totale  1.264,58 m"
            visible: root.current; ink: viewPaint.label_fg; ground: viewPaint.label_bg }
        Repeater {
            model: 4
            delegate: Item {
                id: side
                required property int index
                readonly property point a: root.sides[index]
                readonly property point b: root.sides[(index+1)%4]
                readonly property point center: root.label(a,b, 17)
                anchors.fill: parent
                DraftLine { anchors.fill: parent; a: side.a; b: side.b; ink: viewPaint.bld_stroke
                    thickness: root.current ? 2.5 : 1.5; haloOpacity: root.current ? 1 : .14
                    haloExtra: root.current ? 3 : 2; haloInk: viewPaint.halo }
                M.LengthPill { visible: root.current; x: side.center.x-width/2; y: side.center.y-height/2
                    value: side.index%2 ? "18,04 m" : "43,49 m"; badge: String(side.index+1)
                    ground: viewPaint.label_bg; ink: viewPaint.label_fg }
                DraftPill { visible: !root.current; x: side.center.x-width/2; y: side.center.y-height/2
                    value: side.index%2 ? "18,04 m" : "43,49 m"; badge: String(side.index+1)
                    direction: root.angle(side.a, side.b) }
            }
        }
        DraftLine { a: Qt.point(320,565); b: Qt.point(605,608); ink: viewPaint.sub_stroke
            thickness: root.current ? 2 : 1.5; haloOpacity: root.current ? .8 : 0; haloInk: viewPaint.halo }
        M.LengthPill { visible: root.current; x: 390; y: 570; value: "S1 · 15 moduli"; badge: ""
            badgeShown: true; badgeFill: viewPaint.sub_stroke }
        DraftPill { visible: !root.current; x: 390; y: 570; value: "S1 · 15 moduli"; badge: "S"
            direction: root.angle(Qt.point(320,565),Qt.point(605,608)) }
    }
    // Common diagnostic strip: counts, dash rhythm and reversed directions.
    Rectangle {
        x: 20; y: 800; width: 1880; height: 260; radius: Theme.radius.CARD
        color: Theme.colors.panel
        Text { x: 22; y: 16; text: "Linee tratteggiate"; color: Theme.colors.text2
            font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
        DraftLine { a: Qt.point(24,90); b: Qt.point(470,90); ink: viewPaint.guide; dashed: true
            thickness: root.current ? 2.6 : 1.5 }
        DraftLine { a: Qt.point(510,42); b: Qt.point(900,207.545); ink: viewPaint.guide; dashed: true
            thickness: root.current ? 1.3 : 1.5 }
        DraftPill { x: 980; y: 112; value: "Letta dal basso"; direction: -90; visible: !root.current }
        Repeater {
            model: [1,2,15]
            delegate: Item {
                required property var modelData
                required property int index
                x: 1350 + index*150; y: 68; width: 60; height: 100
                Shape {
                    width: 20; height: 20; preferredRendererType: Shape.CurveRenderer
                    ShapePath { strokeColor: "white"; strokeWidth: 1; fillColor: Theme.colors.warning_ink
                        startX: 10; startY: 0
                        PathLine { x: 20; y: 18 }
                        PathLine { x: 0; y: 18 }
                        PathLine { x: 10; y: 0 }
                    }
                }
                DraftCounter { x: 15; y: -9; count: parent.modelData; current: root.current
                    visible: !root.current || count > 1 }
                Text { y: 42; text: String(parent.modelData); color: Theme.colors.text2
                    font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
            }
        }
        Text { x: 22; y: 214
            text: root.current ? "Riferimento: tratti e contatori attuali; 1 senza badge" : "1,5 px · punti 4,5 px · testo 400 · lati e stringhe: altezza e carattere −1 px · tratteggio 6 / 4 px"
            color: Theme.colors.text2; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL
        }
    }
}
