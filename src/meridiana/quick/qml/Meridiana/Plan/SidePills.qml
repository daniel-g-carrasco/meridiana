import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M
import "SidePills.js" as Pills

Item {
    id: root
    required property var plan
    required property var backend
    property var ring: backend.selectedRing
    // R505: hidden while a side is chosen: a pill, even switched off, would keep the pointer from the plan
    visible: !backend.collecting
    property int hoverSide: -1
    readonly property int litSide: backend.sideEditing ? backend.sideIndex : hoverSide
    property var records: backend.labels.filter(function(p){return p.side!==undefined})
    property var pills: {
        var screen=ring.map(function(p){return plan.screen(p[0],p[1])})
        var lengths=ring.map(function(p,i){var q=ring[(i+1)%ring.length];return Math.hypot(q[0]-p[0],q[1]-p[1]).toLocaleString(Qt.locale(),"f",2)+" m"})
        var widths=lengths.map(function(t){return metrics.advanceWidth(t)})
        // R472: the side's number in a disc, a pill as wide as its digits from 10 on
        var disc=metrics.height
        var badges=ring.map(function(p,i){return Math.max(disc,digits.advanceWidth((i+1).toLocaleString(Qt.locale(),"f",0))+disc/2)})
        return Pills.layout(screen,ring,lengths,widths,metrics.height+2*Theme.space.XXS,
                            Theme.space.XXS,Theme.space.XS,Theme.space.S,Theme.space.M,badges)
    }
    FontMetrics { id: metrics; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
    FontMetrics { id: digits; font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; font.weight: Font.DemiBold }
    Shape {
        // The lit side, under the pills (R472): the pill of the side being edited stays readable over it.
        id: sideHighlight
        objectName: "sideHighlight"
        visible: root.litSide>=0 && root.ring.length>root.litSide
        preferredRendererType: Shape.CurveRenderer
        property int side: Math.max(0,root.litSide)
        property point a: root.ring.length>side ? plan.screen(root.ring[side][0],root.ring[side][1]) : Qt.point(0,0)
        property point b: root.ring.length ? plan.screen(root.ring[(side+1)%root.ring.length][0],root.ring[(side+1)%root.ring.length][1]) : Qt.point(0,0)
        ShapePath { strokeColor: root.backend.planColors.sel; strokeWidth: 5; fillColor: "transparent"
            startX: sideHighlight.a.x; startY: sideHighlight.a.y
            PathLine { x: sideHighlight.b.x; y: sideHighlight.b.y }
        }
    }
    Repeater {
        model: root.pills
        delegate: M.Pill {
            required property var modelData
            variant: "view"
            objectName: "sidePill"+modelData.side
            visible: !backend.sideEditing || backend.sideIndex!==modelData.side
            property color ink: modelData.side===root.litSide ? root.backend.planColors.sel : root.backend.planColors.label_fg
            x: modelData.x; y: modelData.y; width: modelData.width; height: modelData.height; radius: height/2
            ground: root.backend.planColors.label_bg
            Rectangle {
                objectName: "sideBadge"+modelData.side
                x: Theme.space.XXS; y: Theme.space.XXS
                width: modelData.badge; height: parent.height-2*Theme.space.XXS; radius: height/2
                color: parent.ink
                Text { anchors.fill: parent; text: (modelData.side+1).toLocaleString(Qt.locale(),"f",0)
                    color: root.backend.planColors.label_bg
                    verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
                    font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; font.weight: Font.DemiBold }
            }
            Text {
                x: Theme.space.XXS+modelData.badge+Theme.space.XS; height: parent.height
                visible: modelData.whole; text: modelData.text || ""; color: parent.ink
                verticalAlignment: Text.AlignVCenter; font: metrics.font
            }
            MouseArea {
                anchors.fill: parent; cursorShape: Qt.IBeamCursor; hoverEnabled: true
                onEntered: root.hoverSide=modelData.side
                onExited: root.hoverSide=-1
                onClicked: {
                    plan.pointer=Qt.point(parent.x+parent.width/2,parent.y+parent.height/2)
                    backend.editSide(modelData.side)
                }
            }
        }
    }
}
