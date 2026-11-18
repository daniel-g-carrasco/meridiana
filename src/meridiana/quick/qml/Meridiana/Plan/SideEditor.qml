import QtQuick
import Meridiana.Theme
import Meridiana.Controls as Controls

// The length of a side, written where its pill is: the field over a view of every view (OverlayField, R534).
Controls.OverlayField {
    id: editor
    objectName: "sideEditor"
    required property var plan
    required property var backend
    required property var pills
    property var pill: pills.find(function(p) { return p.side===backend.sideIndex })
    property point centre: {
        var r=backend.selectedRing, i=backend.sideIndex
        if (i<0 || !r.length) return plan.pointer
        var a=r[i], b=r[(i+1)%r.length]
        return plan.screen((a[0]+b[0])/2,(a[1]+b[1])/2)
    }
    colours: backend.planColors
    badge: backend.sideIndex+1
    visible: backend.sideEditing
    x: Math.max(0,Math.min(plan.width-width,pill ? pill.x : centre.x-width/2))
    y: Math.max(0,Math.min(plan.height-height,pill ? pill.y : centre.y-height/2))
    Component.onCompleted: input.objectName="sideLengthField"
    onVisibleChanged: if (visible) edit(backend.sideValue)
    onAccepted: {
        if (backend.commitSide(text)) plan.forceActiveFocus()
        else { input.forceActiveFocus(); input.selectAll() }
    }
    onCanceled: { backend.cancelSide(); plan.forceActiveFocus() }
    onFocusLost: backend.cancelSide()
}
