import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

Rectangle {
    id: plan
    objectName: "plan"
    color: D.plan_bg
    clip: true
    focus: true
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    property string tool: "select"
    property string renderer: "shapes"
    property var polygons: backend.scene
    property var selection: backend.selection
    property int renderedModules: 0
    property int polygonCount: renderer === "canvas" ? raster.primitiveCount : shapes.count
    property int paintedModules: renderer === "canvas" ? raster.moduleCount : renderedModules
    property bool fitted: false
    property var modelBounds: backend.bounds
    property bool draggingHandle: false
    property point previewA: Qt.point(0, 0)
    property point previewB: Qt.point(0, 0)
    property bool drawing: false
    function fit() {
        if (width < 100 || height < 100) return
        var b = modelBounds
        zoom = Math.min((width - 64) / b[2], (height - 64) / b[3])
        zoom = Math.max(0.02, zoom)
        panX = (width - b[2]*zoom)/2 - b[0]*zoom
        panY = (height - b[3]*zoom)/2 - b[1]*zoom
        fitted = true
    }
    function world(x, y) { return Qt.point((x-panX)/zoom, (y-panY)/zoom) }
    function screen(p) { return Qt.point(p.x*zoom+panX, p.y*zoom+panY) }
    function containsPoint(points, p) {
        var inside = false
        for (var i=0, j=points.length-1; i<points.length; j=i++) {
            var a=points[i], b=points[j]
            if (((a.y>p.y)!==(b.y>p.y)) && (p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x)) inside=!inside
        }
        return inside
    }
    function pick(x,y) {
        var p=world(x,y)
        for (var i=polygons.length-1; i>=0; --i) {
            var item=polygons[i]
            if (item.kind !== "exclusion" && containsPoint(item.points,p)) {
                backend.select(item.kind,item.oid,item.key)
                return
            }
        }
        backend.select("site","","")
    }
    onPolygonsChanged: {
        renderedModules = polygons.filter(p => p.kind === "module").length
        if (!fitted && width > 0) fit()
    }
    Component.onCompleted: fit()
    function fitOnce() { if (!fitted) fit() }
    onWidthChanged: if (!fitted) Qt.callLater(fitOnce)
    onHeightChanged: if (!fitted) Qt.callLater(fitOnce)
    Keys.onEscapePressed: { tool = "select"; drawing = false }
    Item {
        id: worldLayer
        visible: plan.renderer === "shapes"
        x: plan.panX; y: plan.panY
        scale: plan.zoom
        transformOrigin: Item.TopLeft
        Repeater {
            id: shapes
            model: plan.renderer === "shapes" ? plan.polygons : []
            delegate: Shape {
                id: polygon
                required property var modelData
                property bool selected: modelData.oid === plan.selection.oid &&
                    (plan.selection.key === "" || modelData.key === plan.selection.key)
                ShapePath {
                    strokeWidth: 0.12
                    strokeColor: polygon.selected ? D.accent : polygon.modelData.kind === "module" ? D.plan_bg : D.plan_bld_stroke
                    fillColor: polygon.selected ? D.select_bg : polygon.modelData.kind === "module" ? D.plan_module :
                               polygon.modelData.kind === "subfield" ? D.plan_sub_fill :
                               polygon.modelData.kind === "exclusion" ? D.muted : D.field
                    PathPolyline { path: modelData.points }
                }
            }
        }
    }
    Canvas {
        id: raster
        anchors.fill: parent
        visible: plan.renderer === "canvas"
        renderTarget: Canvas.Image
        property var scene: plan.polygons
        property var selection: plan.selection
        property var colors: D
        property int primitiveCount: 0
        property int moduleCount: 0
        onSceneChanged: requestPaint()
        onSelectionChanged: requestPaint()
        onColorsChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        Connections {
            target: plan
            function onPanXChanged() { raster.requestPaint() }
            function onPanYChanged() { raster.requestPaint() }
            function onZoomChanged() { raster.requestPaint() }
        }
        onPaint: {
            var ctx=getContext("2d")
            ctx.reset()
            ctx.clearRect(0,0,width,height)
            ctx.translate(plan.panX,plan.panY)
            ctx.scale(plan.zoom,plan.zoom)
            ctx.lineWidth=0.12
            var modules=0, primitives=0
            for (var i=0;i<scene.length;++i) {
                var p=scene[i], points=p.points
                if (!points.length) continue
                var selected=p.oid===selection.oid && (selection.key==="" || p.key===selection.key)
                ctx.strokeStyle=selected ? D.accent : p.kind==="module" ? D.plan_bg : D.plan_bld_stroke
                ctx.fillStyle=selected ? D.select_bg : p.kind==="module" ? D.plan_module :
                              p.kind==="subfield" ? D.plan_sub_fill : p.kind==="exclusion" ? D.muted : D.field
                ctx.beginPath()
                ctx.moveTo(points[0].x,points[0].y)
                for (var j=1;j<points.length;++j) ctx.lineTo(points[j].x,points[j].y)
                ctx.closePath()
                ctx.fill()
                ctx.stroke()
                ++primitives
                if (p.kind==="module") ++modules
            }
            primitiveCount=primitives
            moduleCount=modules
        }
    }
    MouseArea {
        id: mouse
        objectName: "planMouse"
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        property point pressedAt
        property point last
        onPressed: event => {
            plan.forceActiveFocus()
            pressedAt=Qt.point(event.x,event.y); last=pressedAt
            if (event.button===Qt.LeftButton && plan.tool==="rectangle") {
                plan.previewA=plan.world(event.x,event.y); plan.previewB=plan.previewA; plan.drawing=true
            }
        }
        onPositionChanged: event => {
            if (pressedButtons & Qt.MiddleButton) {
                plan.panX += event.x-last.x; plan.panY += event.y-last.y
            } else if (plan.drawing) plan.previewB=plan.world(event.x,event.y)
            last=Qt.point(event.x,event.y)
        }
        onReleased: event => {
            if (plan.drawing) {
                plan.drawing=false
                backend.rectangle(plan.previewA.x,-plan.previewA.y,plan.previewB.x,-plan.previewB.y)
                plan.tool="select"
            } else if (event.button===Qt.LeftButton && Math.hypot(event.x-pressedAt.x,event.y-pressedAt.y)<4)
                plan.pick(event.x,event.y)
        }
        onCanceled: plan.drawing=false
        onWheel: event => {
            var p=plan.world(event.x,event.y)
            plan.zoom=Math.max(.02,Math.min(1000,plan.zoom*Math.pow(1.0015,event.angleDelta.y)))
            plan.panX=event.x-p.x*plan.zoom; plan.panY=event.y-p.y*plan.zoom
            event.accepted=true
        }
    }
    Rectangle {
        visible: plan.drawing || plan.draggingHandle
        x: Math.min(plan.previewA.x,plan.previewB.x)*plan.zoom+plan.panX
        y: Math.min(plan.previewA.y,plan.previewB.y)*plan.zoom+plan.panY
        width: Math.abs(plan.previewA.x-plan.previewB.x)*plan.zoom
        height: Math.abs(plan.previewA.y-plan.previewB.y)*plan.zoom
        color: "transparent"; border.color: D.accent; border.width: D.focus
    }
    Repeater {
        model: plan.selection.rectangle ? 4 : 0
        delegate: Rectangle {
            id: handle
            required property int index
            objectName: "handle" + index
            width: 12; height: 12
            x: plan.screen(plan.selection.points[index]).x-width/2
            y: plan.screen(plan.selection.points[index]).y-height/2
            color: D.view; border.color: D.accent; border.width: D.focus
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.SizeFDiagCursor
                property point opposite
                property string targetId
                onPressed: {
                    opposite=plan.selection.points[(handle.index+2)%4]
                    targetId=plan.selection.oid
                    plan.previewA=opposite
                    plan.previewB=plan.selection.points[handle.index]
                    plan.draggingHandle=true
                }
                onPositionChanged: event => {
                    var p=mapToItem(plan,event.x,event.y)
                    plan.previewB=plan.world(p.x,p.y)
                }
                onReleased: {
                    plan.draggingHandle=false
                    backend.resizeRectangle(targetId,opposite.x,-opposite.y,plan.previewB.x,-plan.previewB.y)
                }
                onCanceled: plan.draggingHandle=false
            }
        }
    }
}
