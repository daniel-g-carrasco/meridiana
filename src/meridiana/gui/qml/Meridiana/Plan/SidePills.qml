import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
import "SidePills.js" as Pills

Item {
    id: root
    required property var plan
    required property var backend
    property var ring: backend.selectedRing
    // R505: hidden while a side is chosen: a pill, even switched off, would keep the pointer from the plan
    // R707: and while the object is large enough on screen for its measures to be read (the plan's measuresShown)
    property bool shown: true
    visible: !backend.collecting && shown
    property int hoverSide: -1
    readonly property int litSide: backend.sideEditing ? backend.sideIndex : hoverSide
    property var records: backend.plainLabels.filter(function(p){return p.side!==undefined})
    property var pills: {
        var screen=ring.map(function(p){return plan.screen(p[0],p[1])})
        var lengths=ring.map(function(p,i){var q=ring[(i+1)%ring.length];return Math.hypot(q[0]-p[0],q[1]-p[1]).toLocaleString(Qt.locale(),"f",2)+" m"})
        var widths=lengths.map(function(t){return metrics.advanceWidth(t)})
        // R472: the side's number in a disc, a pill as wide as its digits from 10 on
        var disc=metrics.height+2*Theme.annotation.LABEL_PAD-2*Theme.space.XXS
        var badges=ring.map(function(p,i){return i<9 ? disc : Math.max(disc,digits.advanceWidth((i+1).toLocaleString(Qt.locale(),"f",0))+disc/2)})
        return Pills.layout(screen,ring,lengths,widths,metrics.height+2*Theme.annotation.LABEL_PAD,
                            Theme.space.XXS,Theme.space.XS,Theme.space.S,Theme.space.M,badges)
    }
    FontMetrics { id: metrics; font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE }
    FontMetrics { id: digits; font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE; font.weight: Theme.annotation.WEIGHT }
    M.LitSide {
        // The lit side, under the pills (R472): the pill of the side being edited stays readable over it. R617: the
        // program's one lit side, as the Properties' (Properties/SideHighlight)
        id: sideHighlight
        objectName: "sideHighlight"
        visible: root.litSide>=0 && root.ring.length>root.litSide
        property int side: Math.max(0,root.litSide)
        a: root.ring.length>side ? plan.screen(root.ring[side][0],root.ring[side][1]) : Qt.point(0,0)
        b: root.ring.length ? plan.screen(root.ring[(side+1)%root.ring.length][0],root.ring[(side+1)%root.ring.length][1]) : Qt.point(0,0)
        ink: root.backend.planColors.sel
    }
    Repeater {
        model: root.pills
        // the pill of a length, the one the measures have too (study 46): M.LengthPill
        delegate: M.LengthPill {
            required property var modelData
            objectName: "sidePill"+modelData.side
            direction: modelData.direction
            visible: !backend.sideEditing || backend.sideIndex!==modelData.side
            ink: modelData.side===root.litSide ? root.backend.planColors.sel : root.backend.planColors.label_fg
            ground: root.backend.planColors.label_bg
            x: modelData.x; y: modelData.y; width: modelData.width; height: modelData.height
            value: modelData.text || ""; whole: modelData.whole
            badge: (modelData.side+1).toLocaleString(Qt.locale(),"f",0); badgeWidth: modelData.badge
            badgeName: "sideBadge"+modelData.side
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
