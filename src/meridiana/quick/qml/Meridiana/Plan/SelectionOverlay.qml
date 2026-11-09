import QtQuick
import Meridiana.Theme
import Meridiana.Controls as Controls
import "Selection.js" as Selection

Item {
    id: root
    property var modules: []
    property var objects: []
    property var selectable: []      // the phase's rule, from the editor (PlanController.clickKinds)
    property var anchor: ({oid:"",ring:[]})
    readonly property bool takesModules: selectable.indexOf("module")>=0
    property var selectionState: ({swept:[]})
    property bool live: true
    property bool drawHover: true
    property bool sweeping: false
    property bool removing: false
    property bool modified: false
    property string kind: "window"
    property var ring: []
    property point pointer: Qt.point(0,0)
    property real viewScale: 1
    property real offsetX: 0
    property real offsetY: 0
    property real viewRotation: 0
    property var colours: ({halo:Theme.colors.overlay.halo,sweep_window:Theme.colors.overlay.sweep_window,sweep_crossing:Theme.colors.overlay.sweep_crossing,sweep_remove:Theme.colors.overlay.remove})
    property var hoverColours: Theme.colors.hot
    readonly property var moduleIndex: Selection.buildIndex(modules)
    readonly property var objectIndex: Selection.buildIndex(objects.filter(function(row){
        return selectable.indexOf(row.kind)>=0
    }))
    property var chosen: []
    property var hovered: null
    property string action: ""
    property real queryMilliseconds: 0
    property int queryCount: 0
    property int paintCount: 0
    property real paintMilliseconds: 0
    property string _maskKey: ""
    property var _lastTaken: null
    property var _lastHit: null
    property bool _wasSweeping: false
    readonly property color highlightColour: removing && sweeping || action==="remove" ? colours.sweep_remove :
        sweeping ? hoverColours.module : hovered ? hoverColours[hovered.record.kind] : hoverColours.module
    readonly property int candidateCount: chosen.length
    readonly property var hoveredOutline: !live || sweeping || !hovered ? [] : [
        {points:hovered.record.points,closed:true,fill:"transparent",stroke:colours.halo,width:3.8},
        {points:hovered.record.points,closed:true,fill:"transparent",stroke:highlightColour.toString(),width:1.8,dashed:true}]
    readonly property var hoveredRidges: {
        if (!live || sweeping || !hovered || ["building","pitch"].indexOf(hovered.record.kind)<0) return []
        var oid=hovered.record.oid.split(":")[0]
        return objects.filter(o=>o.kind==="ridge" && o.oid===oid).map(o=>({
            points:o.points,closed:false,fill:"transparent",stroke:hoverColours[hovered.record.kind],width:3.8}))
    }

    function scene(p) {
        var a=-viewRotation*Math.PI/180,c=Math.cos(a),s=Math.sin(a),x=(p.x-offsetX)/viewScale,y=(p.y-offsetY)/viewScale
        return [x*c-y*s,x*s+y*c]
    }
    function requestPaint() { update.restart() }
    function projectedBox(b) {
        var a=viewRotation*Math.PI/180,c=Math.cos(a)*viewScale,s=Math.sin(a)*viewScale
        var xs=[b[0]*c-b[1]*s,b[2]*c-b[1]*s,b[2]*c-b[3]*s,b[0]*c-b[3]*s]
        var ys=[b[0]*s+b[1]*c,b[2]*s+b[1]*c,b[2]*s+b[3]*c,b[0]*s+b[3]*c]
        return [Math.min.apply(null,xs)+offsetX,Math.min.apply(null,ys)+offsetY,
                Math.max.apply(null,xs)+offsetX,Math.max.apply(null,ys)+offsetY]
    }
    function refresh() {
        var then=Date.now(), out=[], hit=null, sign="", taken=[]
        if(live && sweeping) {
            var index=takesModules ? moduleIndex : objectIndex
            taken=Selection.chosen(index,ring.map(scene),kind)
            if(taken===_lastTaken) out=chosen
            else for(var i=0;i<taken.length;i++) out.push(index[taken[i]])
            sign=removing ? "remove" : "add"
        } else if(live) {
            var p=scene(pointer),at=takesModules ? Selection.hit(moduleIndex,p,6/viewScale) : -1
            if(at>=0) hit=moduleIndex[at]
            else { at=Selection.hit(objectIndex,p,0); if(at>=0) hit=objectIndex[at] }
            // Inside what is selected a click stays on it (R427): light only what that click would take.
            if(hit && anchor.ring.length && Selection.locate(p,anchor.ring)>=0 &&
                    (hit.record.kind!=="module" || hit.record.oid!==anchor.oid)) hit=null
            if(hit && hit.record.kind==="module" && modified && selectionState.swept.length) {
                var found=selectionState.swept.some(function(m){return m[0]===hit.record.oid && m[1]===hit.record.key})
                sign=found && removing ? "remove" : "add"      // R529: Shift only adds, Ctrl toggles
            }
        }
        var key=[live,takesModules,sweeping,viewScale,offsetX,offsetY,viewRotation,width,height].join("|")
        var dirty=Qt.rect(0,0,width,height)
        if(key===_maskKey) {
            if(sweeping && _lastTaken) {
                var change=taken===_lastTaken ? null : Selection.changedBounds(index,_lastTaken,taken)
                if(change) { var b=projectedBox(change); dirty=Qt.rect(b[0]-4,b[1]-4,b[2]-b[0]+8,b[3]-b[1]+8) }
                else dirty=null
            } else if(hit===_lastHit) dirty=null
        }
        if(out!==chosen) chosen=out
        _lastTaken=taken; _lastHit=hit; hovered=hit; action=sign
        queryMilliseconds=Date.now()-then; queryCount++
        _maskKey=key
        // Hover has native paths. Do not clear and upload two full-size empty
        // textures at every pan/zoom. One final clear removes a completed sweep.
        var hasSweep=live && sweeping
        if(hasSweep || _wasSweeping) {
            if(dirty) canvas.markDirty(Qt.rect(dirty.x*canvas.rasterScale,dirty.y*canvas.rasterScale,
                                               dirty.width*canvas.rasterScale,dirty.height*canvas.rasterScale))
            outline.requestPaint()
        }
        _wasSweeping=hasSweep
    }
    onModuleIndexChanged: { _maskKey=""; _lastTaken=null; requestPaint() }
    onObjectIndexChanged: { _maskKey=""; _lastTaken=null; requestPaint() }
    onSelectionStateChanged: requestPaint()
    onLiveChanged: requestPaint()
    onSweepingChanged: requestPaint()
    onRemovingChanged: requestPaint()
    onModifiedChanged: requestPaint()
    onKindChanged: requestPaint()
    onRingChanged: requestPaint()
    onPointerChanged: requestPaint()
    onViewScaleChanged: requestPaint()
    onOffsetXChanged: requestPaint()
    onOffsetYChanged: requestPaint()
    onViewRotationChanged: requestPaint()
    Component.onCompleted: requestPaint()
    Timer { id: update; interval: 0; onTriggered: root.refresh() }
    Canvas {
        id: canvas
        // Membership mask needs one texel per logical pixel. The GPU outline is still device-resolution.
        property real rasterScale: 1/Screen.devicePixelRatio
        width: parent.width*rasterScale; height: parent.height*rasterScale
        onWidthChanged: root.requestPaint()
        onHeightChanged: root.requestPaint()
        onPaint: function(region) {
            var then=Date.now(),ctx=getContext("2d")
            ctx.setTransform(1,0,0,1,0,0); ctx.clearRect(region.x,region.y,region.width,region.height)
            if(!root.live) return
            ctx.save()
            ctx.beginPath();ctx.rect(region.x,region.y,region.width,region.height);ctx.clip()
            ctx.scale(rasterScale,rasterScale)
            ctx.translate(root.offsetX,root.offsetY);ctx.rotate(root.viewRotation*Math.PI/180);ctx.scale(root.viewScale,root.viewScale)
            var viewportRegion=Qt.rect(region.x/rasterScale,region.y/rasterScale,region.width/rasterScale,region.height/rasterScale)
            var rows=root.sweeping ? root.chosen : []
            var projection=[root.viewScale,root.offsetX,root.offsetY,root.viewRotation].join("|")
            // Only fill the mask. Cosmetic outlines are sampled on the GPU, without raster strokes.
            for(var batch=0;batch<rows.length;batch+=64) {
                ctx.beginPath()
                for(var i=batch;i<Math.min(rows.length,batch+64);i++) {
                    if(rows[i].projection!==projection) { rows[i].screenBounds=root.projectedBox(rows[i].bounds); rows[i].projection=projection }
                    var b=rows[i].screenBounds
                    if(b[2]<viewportRegion.x-3 || b[3]<viewportRegion.y-3 || b[0]>viewportRegion.x+viewportRegion.width+3 || b[1]>viewportRegion.y+viewportRegion.height+3) continue
                    var pts=rows[i].points
                    if(!pts.length) continue
                    ctx.moveTo(pts[0][0],pts[0][1])
                    for(var j=1;j<pts.length;j++) ctx.lineTo(pts[j][0],pts[j][1])
                    ctx.closePath()
                }
                ctx.fillStyle="white";ctx.fill()
            }
            ctx.restore()
            root.paintMilliseconds=Date.now()-then;root.paintCount++
        }
    }
    ShaderEffectSource { id: mask; sourceItem: canvas; hideSource: true; live: true }
    ShaderEffect {
        anchors.fill: parent
        visible: root.sweeping
        property variant source: mask
        property vector2d pixelStep: Qt.vector2d(1/Math.max(1,width),1/Math.max(1,height))
        property color ink: root.highlightColour
        property color halo: root.colours.halo
        property real fillOpacity: root.takesModules ? 150/255 : 56/255
        fragmentShader: "selection.frag.qsb"
    }
    Item {
        visible: root.drawHover
        x: root.offsetX; y: root.offsetY; scale: root.viewScale; rotation: root.viewRotation
        transformOrigin: Item.TopLeft
        PolygonLayer { objects: root.drawHover ? root.hoveredRidges : [] }
        PolygonLayer { objects: root.drawHover ? root.hoveredOutline : [] }
    }
    Canvas {
        id: outline; anchors.fill: parent
        onPaint: {
            var ctx=getContext("2d");ctx.reset();ctx.clearRect(0,0,width,height)
            if(root.live && root.sweeping && root.ring.length) {
                ctx.beginPath();ctx.moveTo(root.ring[0].x,root.ring[0].y)
                for(var k=1;k<root.ring.length;k++) ctx.lineTo(root.ring[k].x,root.ring[k].y)
                ctx.closePath()
                var tint=root.removing ? root.colours.sweep_remove : root.kind==="window" ? root.colours.sweep_window : root.colours.sweep_crossing
                ctx.fillStyle=tint;ctx.globalAlpha=56/255;ctx.fill();ctx.globalAlpha=1
                ctx.setLineDash(root.kind==="crossing" ? [5,4] : [])
                ctx.strokeStyle=tint;ctx.lineWidth=1.3;ctx.stroke()
            }
        }
    }
    Controls.PointerSign {
        // R535: the same sign as the 3D view's corners with Ctrl
        objectName: "selectionSign"
        visible: root.live && root.action!==""
        pointer: root.pointer; sign: root.action; colours: root.colours; addColor: root.hoverColours.module
    }
}
