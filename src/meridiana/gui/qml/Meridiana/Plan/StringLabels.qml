import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// String names and module numbers (R467, R496). They lie over every string's dots and lines (z), and never on a dot:
// each label tries the sides of its module, across the string first, then a little further with a short leader.
// The draft's numbers come first (they are what the hand is doing), then the measures of the sides (`avoid`), then
// the names, which make way. They are laid out at the settled zoom and, while the wheel or the fingers zoom, only
// moved with the plan (`follow`): a zoom step costs a multiplication per pill, not a layout. R560 (Daniel 08/11/2026:
// «le pillole in pianta degli inverter e delle stringhe vengono zoommate insieme allo zoom della pianta»): the pills
// keep their size on screen at every zoom, like the measures of the sides; until r26 the whole layer was scaled
// (R496), and since R541 (settled 300 ms after the last notch) a zoom showed them growing and shrinking.
// R555 (14) (Daniel 09/11/2026: «le pillole delle stringhe più simili a quelle delle quote dei lati»): every label is
// the sides' pill, M.LengthPill: a name is the string's colour in the side's disc, the name, its state in a disc as
// large at the other end; a number is the pill with its number alone. They give way in one manner, the sides' one:
// whole, or the disc alone. Until then a name lost its state between 6 and 14 px a module (3 px narrower) and became
// a bare coloured disc of its own drawing under 6.
// What they say depends on the modules' size on screen (R707, study 55; the thresholds are the backend's levels):
//   from 40 px             the numbers of the chosen string too;
//   near (14 px and more)  a name for each string, with its state;
//   mid  (5 to 14 px)      one pill for each inverter, in the middle of its strings' modules: «Inverter 3 · 10
//                          strings» and the worst state of its strings, or how many are to check;
//   far  (under 5 px)      «Inverter 3» and the state alone; under 2.5 px nothing.
// (until R707 the names stayed down to 6 px, then a bare disc for each string and a notice for each inverter with
// something to check: eighty discs without a name over four buildings of a hundred pixels)
Item {
    id: root
    objectName: "stringLabels"
    required property var plan
    required property var backend
    property var avoid: []                 // boxes of other pills (the sides' measures) the names keep off
    // R706: the same boxes again lay nothing out. The plan's signal of the overlays makes the sides' pills anew
    // (mostly none: nothing is selected), and each time the names were all laid out again, 10 ms of the window.
    readonly property string avoidKey: JSON.stringify(avoid.map(function(b){var o=b.bounds || b; return [o.x,o.y,o.width,o.height]}))
    property var avoided: []
    onAvoidKeyChanged: avoided=avoid
    // A scene transform avoids sending geometry changes through every pill and its attached text menu.
    transform: Translate { x: plan.annotationCamera.x; y: plan.annotationCamera.y }
    z: Theme.stack.LABEL           // over the dots, under the bars over the plan (R577, R616)
    // the zoom now against the settled one: the pills' centres move by it, their size does not
    readonly property real follow: plan.settledZoom>0 ? plan.annotationCamera.zoom/plan.settledZoom : 1
    Scale { id: followInk; xScale: 1/root.follow; yScale: 1/root.follow }
    readonly property real pixels: backend.moduleSize*plan.settledZoom
    readonly property string level: pixels>=backend.levels.string ? "near" : pixels>=backend.levels.field ? "mid" : "far"
    readonly property var labels: backend.stringLabels
    readonly property var draftLabels: backend.draftLabels
    // M.LengthPill's height and disc, the same for every label (its width is the layout's)
    readonly property real line: M.PillPlace.height(metrics.height, 0, Theme.annotation.LABEL_PAD)
    readonly property real disc: line-2*Theme.space.XXS
    function stateSign(state) { return state==="ok" ? "check" : state==="fail" ? "stop" : "warning" }

    // R706: the dots in squares of `dotCell` metres, turned as the plan is (East, North as plain numbers, the list
    // of their records was a tenth of a second at 2000 modules): made when the dots or the bearing change. Every
    // layout sorted them all again in squares of the screen, at each settled zoom and each signal of the plan.
    readonly property real dotCell: 2
    readonly property var dotGrid: {
        var a=plan.bearing*Math.PI/180,c=Math.cos(a),s=Math.sin(a),dots=backend.dotPlaces,cell=dotCell,grid={}
        for(var d=0;d<dots.length;d+=2) {
            var dx=dots[d]*c+dots[d+1]*s,dy=dots[d]*s-dots[d+1]*c
            var key=Math.floor(dx/cell)+":"+Math.floor(dy/cell)
            if(!grid[key]) grid[key]=[]
            grid[key].push(dx,dy)
        }
        return grid
    }
    // the string chosen as a number: the plan's signal of the overlays, with the same string, lays nothing out
    readonly property int chosen: backend.chosenString
    // what a level of detail does not show: the strings' names below the strings' scale, the numbers of the chosen
    // string below the modules' (what the hand is drawing always shows)
    function hides(item) {
        if(item.draft) return false
        return item.kind==="number" ? pixels<backend.levels.module : item.kind==="name" && level!=="near"
    }
    function place(items, used, avoidBoxes, far) {
        var a=plan.bearing*Math.PI/180,c=Math.cos(a),s=Math.sin(a),zoom=plan.settledZoom
        // the dots are in the way only where they show: near the modules
        var cell=dotCell*zoom,grid=far || root.level!=="near" ? null : dotGrid,reach=Theme.annotation.POINT/2+Theme.space.XXS
        function covered(b) {
            var n=0
            if(!grid || !(cell>0)) return n
            for(var gx=Math.floor((b.x-reach)/cell);gx<=Math.floor((b.x+b.width+reach)/cell);++gx)
                for(var gy=Math.floor((b.y-reach)/cell);gy<=Math.floor((b.y+b.height+reach)/cell);++gy) {
                    var list=grid[gx+":"+gy]
                    if(!list) continue
                    for(var i=0;i<list.length;i+=2) {
                        var px=list[i]*zoom,py=list[i+1]*zoom
                        var qx=Math.max(b.x,Math.min(px,b.x+b.width))-px
                        var qy=Math.max(b.y,Math.min(py,b.y+b.height))-py
                        if(qx*qx+qy*qy<reach*reach) ++n
                    }
                }
            return n
        }
        function hits(b,list) {
            for(var i=0;i<list.length;++i) {
                var o=list[i].bounds || list[i]
                if(b.x-2<o.x+o.width && b.x+b.width+2>o.x && b.y-2<o.y+o.height && b.y+b.height+2>o.y) return true
            }
            return false
        }
        var chosen=root.chosen
        function rank(l){return (l.kind==="number"?0:2)+(l.run===chosen?0:1)}
        var ordered=items.map(function(l,i){return {label:l,index:i}}).sort(function(p,q){return rank(p.label)-rank(q.label)})
        var out=[]
        for(var k=0;k<ordered.length;++k) {
            var item=ordered[k].label,isName=item.kind==="name",centred=item.kind==="inverter",disc=isName && far
            if(root.hides(item)) continue
            // the sides' pill: one height; a name's state at every zoom where its name shows (R555 14)
            var h=root.line,symbol=(isName || centred) && !disc ? root.disc : 0
            var w=disc ? h : M.PillPlace.width(metrics.advanceWidth(item.text), 0, isName ? root.disc : 0,
                                              Theme.space.XXS, Theme.space.XS, Theme.space.S, symbol)
            var dirX=item.dirX===undefined?1:item.dirX,dirY=item.dirY===undefined?0:item.dirY
            var direction=centred ? 0 : M.PillPlace.readable(Math.atan2(dirX*s-dirY*c,dirX*c+dirY*s)*180/Math.PI)
            var px=zoom*(item.x*c+item.y*s),py=zoom*(item.x*s-item.y*c)
            var best=null
            if(disc || centred) {           // on its point: a string's disc, an inverter's pill
                var b0={x:px-w/2,y:py-h/2,width:w,height:h,ux:0,uy:0,leader:0}
                if(hits(b0,used) || hits(b0,avoidBoxes)) continue
                best=b0
            } else {
                var ex=item.dirX===undefined?1:item.dirX,ey=item.dirY===undefined?0:item.dirY
                var tx=ex*c+ey*s,ty=ex*s-ey*c,tl=Math.sqrt(tx*tx+ty*ty)||1
                tx/=tl; ty/=tl
                var nx=-ty,ny=tx
                if(ny>1e-9 || (Math.abs(ny)<=1e-9 && nx<0)) { nx=-nx; ny=-ny }    // the upper side of the screen first
                var ways=isName ? [[nx,ny,0],[-nx,-ny,0],[-tx,-ty,0],[nx,ny,1],[-nx,-ny,1],[-tx,-ty,1]]
                                : [[nx,ny,0],[-nx,-ny,0],[nx,ny,1],[-nx,-ny,1]]
                for(var j=0;j<ways.length;++j) {
                    var ux=ways[j][0],uy=ways[j][1],reachOut=Math.abs(ux*tx+uy*ty)*w/2+Math.abs(-ux*ty+uy*tx)*h/2
                    var dist=reachOut+7+ways[j][2]*(h+4)
                    var b={x:px+ux*dist-w/2,y:py+uy*dist-h/2,width:w,height:h,ux:ux,uy:uy,leader:dist-reachOut-5}
                    b.bounds=M.PillPlace.rotatedBox(b.x,b.y,w,h,direction)
                    if(hits(b.bounds,used) || hits(b.bounds,avoidBoxes)) continue
                    b.dots=covered(b.bounds)
                    if(best===null || b.dots<best.dots) best=b
                    if(b.dots===0) break
                }
                if(best===null) {
                    if(isName || item.number!==1) continue      // names and numbers between others make way, as before
                    best={x:px+nx*(h/2+7)-w/2,y:py+ny*(h/2+7)-h/2,width:w,height:h,ux:nx,uy:ny,leader:2}
                }
            }
            used.push(best)
            out.push({index:ordered[k].index,direction:direction,bounds:best.bounds,x:best.x,y:best.y,width:w,height:h,symbol:symbol,item:item,disc:disc,
                      leaderX:px+best.ux*5-best.x,leaderY:py+best.uy*5-best.y,leader:best.leader,
                      angle:Math.atan2(best.uy,best.ux)*180/Math.PI})
        }
        return out
    }
    // the draft's numbers first: nothing in their way but each other
    readonly property var draftBoxes: place(draftLabels, [], [], false)
    readonly property var boxes: {
        var used=draftBoxes.map(function(b){return b.bounds || {x:b.x,y:b.y,width:b.width,height:b.height}})
        return place(labels, used, avoided, level==="far")
    }
    // R706: a pill for each label, kept: a new layout (the zoom settled, the scene of another scale) gives each its
    // place, or hides it, and makes none again. They were all destroyed and made anew at every settled zoom: 80
    // names were half a second of the window near the modules (Daniel 20/11/2026: «un blocco da mezzo secondo
    // circa, immancabile quando faccio un paio di zoom in e zoom out»), four hundred two seconds and more.
    // (a pill not shown keeps a pill's measures: nothing in it is ever of no size)
    readonly property var blank: ({index:-1,direction:0,x:0,y:0,width:2*line,height:line,symbol:disc,disc:false,leaderX:0,
                                   leaderY:0,leader:0,angle:0,item:{kind:"",run:-1,text:" ",colour:"transparent",state:"ok"}})
    readonly property var slots: {
        var out=[]
        for(var i=0;i<labels.length;++i) out.push(blank)
        for(var k=0;k<boxes.length;++k) out[boxes[k].index]=boxes[k]
        return out
    }
    // R707: below the strings' scale one pill for each inverter, in the middle of the modules of its strings (the
    // backend's inverterCentres; its first string's name where it has none): how many strings it has, or how many
    // are to check, and the worst of their states; from far its name and the state alone
    readonly property var notices: {
        if(level==="near" || pixels<backend.levels.colourGone) return []
        var by={},order=[]
        for(var i=0;i<labels.length;++i) {
            var l=labels[i]
            if(l.kind!=="name") continue
            var inv=l.inverter||0
            if(!by[inv]) { by[inv]={inverter:inv,x:l.x,y:l.y,strings:0,count:0,fail:0,kind:"inverter",run:inv,colour:"transparent",text:""}; order.push(inv) }
            by[inv].strings++
            if(l.state==="fail") by[inv].fail++
            if(l.state!=="ok") by[inv].count++
        }
        var centres=backend.inverterCentres
        for(var m=0;m<centres.length;++m) {
            var at=by[centres[m].inverter]
            if(at) { at.x=centres[m].x; at.y=centres[m].y }
        }
        var items=[]
        for(var k=0;k<order.length;++k) {
            var n=by[order[k]]
            var name=n.inverter ? qsTr("Inverter %1").arg(n.inverter) : qsTr("Without an inverter")
            n.text=level!=="mid" ? name : name+" · "+(n.count ? qsTr("%1 to check").arg(n.count)
                                                      : n.strings===1 ? qsTr("1 string") : qsTr("%1 strings").arg(n.strings))
            n.state=n.fail ? "fail" : n.count ? "check" : "ok"
            items.push(n)
        }
        return place(items, [], avoided, false)
    }
    FontMetrics { id: metrics; font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE }

    component PillAnchor: Item {
        required property var modelData
        x: modelData.x+modelData.width/2
        y: modelData.y+modelData.height/2
        transform: followInk
        Pill { modelData: parent.modelData }
    }
    component Pill: M.LengthPill {
        id: pill
        required property var modelData
        readonly property bool isName: modelData.item.kind==="name"
        objectName: modelData.item.kind==="" ? "" : "stringLabel-"+modelData.item.kind+"-"+modelData.item.run
        x: -width/2
        y: -height/2
        width:modelData.width; height:modelData.height
        direction: modelData.disc ? 0 : modelData.direction
        ground: backend.planColors.label_bg; ink: backend.planColors.label_fg
        value: modelData.item.text; whole: !modelData.disc
        badgeShown: isName; badgeFill: modelData.item.colour || "transparent"; badgeLine: backend.planColors.label_fg
        end: modelData.symbol
        M.ViewStroke {
            visible: modelData.leader > 3
            x: modelData.leaderX; y: modelData.leaderY
            points: [Qt.point(0,0), Qt.point(modelData.leader,0)]
            transformOrigin: Item.TopLeft
            rotation: modelData.angle - pill.rotation
            ink: backend.planColors.label_fg
        }
        PlanSymbol {
            visible: pill.end>0; size: pill.end; round: true
            x: pill.endX; y: (pill.height-height)/2
            name: root.stateSign(modelData.item.state)
            shapes: backend.statusSymbols; fontFamily: Theme.fontFamily
        }
        // No MouseArea: a label lies over the modules and the click belongs to the module under it, as in the
        // Widgets plan (06/11/2026). The string is chosen from the Plant panel or by clicking its modules.
    }
    Item {
        transform: Scale { xScale: root.follow; yScale: root.follow }
        Repeater {
            model: root.labels.length
            delegate: Item {
                required property int index
                readonly property var box: root.slots[index] || root.blank
                visible: box!==root.blank
                PillAnchor { modelData: parent.box }
            }
        }
        Repeater { model: root.draftBoxes; delegate: PillAnchor {} }
        Repeater { model: root.notices; delegate: PillAnchor {} }
    }

    // far: the name of the string under the pointer (its disc), in a pill that follows the pointer (R496 a)
    HoverHandler { id: hover; enabled: root.level==="far" }
    readonly property var hovered: {
        if(!hover.hovered || level!=="far") return null
        var p=hover.point.position,best=null,bestD=14*14
        for(var i=0;i<boxes.length;++i) {
            var b=boxes[i]
            if(!b.disc) continue
            var dx=(b.x+b.width/2)*root.follow-p.x,dy=(b.y+b.height/2)*root.follow-p.y
            if(dx*dx+dy*dy<bestD) { bestD=dx*dx+dy*dy; best=b }
        }
        return best
    }
    M.LengthPill {
        id: hoverPill
        visible: root.hovered!==null
        objectName: "stringLabel-hover"
        x: root.hovered ? (root.hovered.x+root.hovered.width/2)*root.follow+root.hovered.width/2+Theme.space.S : 0
        y: root.hovered ? (root.hovered.y+root.hovered.height/2)*root.follow-height/2 : 0
        z: 3
        ground: backend.planColors.label_bg; ink: backend.planColors.label_fg
        value: root.hovered ? root.hovered.item.text : ""
        badgeShown: true; badgeFill: root.hovered ? root.hovered.item.colour : "transparent"
        badgeLine: backend.planColors.label_fg
        end: root.disc
        PlanSymbol { visible: root.hovered!==null; size: hoverPill.end; round: true; x: hoverPill.endX; y: (hoverPill.height-height)/2
            name: root.stateSign(root.hovered ? root.hovered.item.state : "")
            shapes: backend.statusSymbols; fontFamily: Theme.fontFamily }
    }
}
