import QtQuick
import QtQuick.Controls
import Meridiana.Controls as MC

Item {
    id: handle
    objectName: "rowHandle"
    required property var plan
    required property var backend
    property var spec: backend.rowHandle || ({})
    property point dragged: Qt.point(0, 0)
    property bool dragging: false
    property point location: dragging ? dragged : plan.screen(spec.x || 0, spec.y || 0)
    visible: spec.oid !== undefined && !backend.collecting      // R505
    x: location.x-width/2
    y: location.y-height/2
    width: MC.ControlMetrics.planHandle
    height: MC.ControlMetrics.planHandle

    Rectangle {
        anchors.centerIn: parent
        width: 10; height: 10; radius: 5
        color: mouse.pressed || mouse.containsMouse ? backend.planColors.sel : backend.planColors.label_bg
        border.color: backend.planColors.sel
        border.width: MC.ControlMetrics.planStroke
    }
    MC.ToolTip { pressed: mouse.pressed; visible: mouse.containsMouse && !mouse.pressed && text !== ""; text: spec.hint || "" }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true
        cursorShape: Qt.SizeHorCursor
        property string rowId: ""
        property point began: Qt.point(0, 0)
        onPressed: function(event) {
            rowId=handle.spec.oid
            began=mapToItem(handle.plan,event.x,event.y)
            handle.dragged=began
            handle.dragging=true
            handle.plan.forceActiveFocus()
        }
        onPositionChanged: function(event) {
            if (pressed) handle.dragged=mapToItem(handle.plan,event.x,event.y)
        }
        onReleased: function(event) {
            var pos=mapToItem(handle.plan,event.x,event.y)
            handle.dragging=false
            if (Math.hypot(pos.x-began.x,pos.y-began.y)<=1) return
            var p=handle.plan.world(pos.x,pos.y)
            handle.backend.resizeRow(rowId,p.x,p.y)
        }
        onCanceled: handle.dragging=false
    }
}
