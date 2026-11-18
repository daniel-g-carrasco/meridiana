import QtQuick
import Meridiana.Theme

// String names and module numbers (R467, R496). They lie over every string's dots and lines (z), and never on a dot:
// each label tries the sides of its module, across the string first, then a little further with a short leader.
// The draft's numbers come first (they are what the hand is doing), then the measures of the sides (`avoid`), then
// the names, which make way. They are laid out at the settled zoom and, while the wheel or the fingers zoom, only
// moved with the plan (`follow`): a zoom step costs a multiplication per pill, not a layout. R560 (Daniel 08/11/2026:
// «le pillole in pianta degli inverter e delle stringhe vengono zoommate insieme allo zoom della pianta»): the pills
// keep their size on screen at every zoom, like the measures of the sides; until r26 the whole layer was scaled
// (R496), and since R541 (settled 300 ms after the last notch) a zoom showed them growing and shrinking.
// What they say depends on the modules' size on screen:
//   near (14 px and more)  names with their state, numbers of the chosen string, dots;
//   mid  (6 to 14 px)      names without the state symbol;
//   far  (under 6 px)      a coloured disc for each string, one notice for each inverter with something to check;
//                          the name shows under the pointer.
Item {
    id: root
    required property var plan
    required property var backend
    property var avoid: []                 // boxes of other pills (the sides' measures) the names keep off
    x: plan.panX
    y: plan.panY
    z: 2
    // the zoom now against the settled one: the pills' centres move by it, their size does not
    readonly property real follow: plan.settledZoom>0 ? plan.zoom/plan.settledZoom : 1
    readonly property real pixels: backend.moduleSize*plan.settledZoom
    readonly property string level: pixels>=14 ? "near" : pixels>=6 ? "mid" : "far"
    readonly property var labels: backend.stringLabels
    readonly property var draftLabels: backend.draftLabels
    readonly property real discSize: 12
    readonly property real markSize: 14              // the state's disc at the end of a name
    readonly property real dotSize: 8                // the string's colour at the start of a name
    function endGap(h) { return (h-markSize)/2 }     // the state's disc in the round end: as far from it all round

    function place(items, used, avoidBoxes, far) {
        var a=plan.bearing*Math.PI/180,c=Math.cos(a),s=Math.sin(a),zoom=plan.settledZoom
        var cell=32,grid={},dots=far ? [] : backend.dots,reach=4+2
        for(var d=0;d<dots.length;++d) {
            var dx=zoom*(dots[d].x*c+dots[d].y*s),dy=zoom*(dots[d].x*s-dots[d].y*c)
            var key=Math.floor(dx/cell)+":"+Math.floor(dy/cell)
            if(!grid[key]) grid[key]=[]
            grid[key].push([dx,dy])
        }
        function covered(b) {
            var n=0
            for(var gx=Math.floor((b.x-reach)/cell);gx<=Math.floor((b.x+b.width+reach)/cell);++gx)
                for(var gy=Math.floor((b.y-reach)/cell);gy<=Math.floor((b.y+b.height+reach)/cell);++gy) {
                    var list=grid[gx+":"+gy]
                    if(!list) continue
                    for(var i=0;i<list.length;++i) {
                        var qx=Math.max(b.x,Math.min(list[i][0],b.x+b.width))-list[i][0]
                        var qy=Math.max(b.y,Math.min(list[i][1],b.y+b.height))-list[i][1]
                        if(qx*qx+qy*qy<reach*reach) ++n
                    }
                }
            return n
        }
        function hits(b,list) {
            for(var i=0;i<list.length;++i) {
                var o=list[i]
                if(b.x-2<o.x+o.width && b.x+b.width+2>o.x && b.y-2<o.y+o.height && b.y+b.height+2>o.y) return true
            }
            return false
        }
        var chosen=backend.chosenString
        function rank(l){return (l.kind==="number"?0:2)+(l.run===chosen?0:1)}
        var ordered=items.slice().sort(function(p,q){return rank(p)-rank(q)})
        var out=[]
        for(var k=0;k<ordered.length;++k) {
            var item=ordered[k],isName=item.kind==="name",disc=isName && far
            var fm=isName ? names : numbers
            var h=disc ? root.discSize : isName ? Math.max(fm.height,16)+6 : Math.max(fm.height,12)+4
            // R514: the state's disc has its room also in an inverter's notice (run -1: it covered the end of the
            // text, whose digit showed through the cut sign as an arrow), and the two ends are alike: the string's
            // dot as far from the left end as the disc from the right one, the text as far from either
            var symbol=isName && !disc && (root.level==="near" || item.run===-1) ? root.markSize : 0
            var left=isName && !disc ? root.endGap(h)+root.dotSize+Theme.space.XS : 0
            var w=disc ? h : isName ? left+fm.advanceWidth(item.text)+(symbol ? Theme.space.XS+symbol+root.endGap(h) : left)
                                    : Math.max(h,fm.advanceWidth(item.text)+10)
            var px=zoom*(item.x*c+item.y*s),py=zoom*(item.x*s-item.y*c)
            var best=null
            if(disc) {
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
                    var ux=ways[j][0],uy=ways[j][1],reachOut=Math.abs(ux)*w/2+Math.abs(uy)*h/2
                    var dist=reachOut+7+ways[j][2]*(h+4)
                    var b={x:px+ux*dist-w/2,y:py+uy*dist-h/2,width:w,height:h,ux:ux,uy:uy,leader:dist-reachOut-5}
                    if(hits(b,used) || hits(b,avoidBoxes)) continue
                    b.dots=covered(b)
                    if(best===null || b.dots<best.dots) best=b
                    if(b.dots===0) break
                }
                if(best===null) {
                    if(isName || item.number!==1) continue      // names and numbers between others make way, as before
                    best={x:px+nx*(h/2+7)-w/2,y:py+ny*(h/2+7)-h/2,width:w,height:h,ux:nx,uy:ny,leader:2}
                }
            }
            used.push(best)
            out.push({x:best.x,y:best.y,width:w,height:h,left:left,symbol:symbol,item:item,disc:disc,
                      leaderX:px+best.ux*5-best.x,leaderY:py+best.uy*5-best.y,leader:best.leader,
                      angle:Math.atan2(best.uy,best.ux)*180/Math.PI})
        }
        return out
    }
    // the draft's numbers first: nothing in their way but each other
    readonly property var draftBoxes: place(draftLabels, [], [], false)
    readonly property var boxes: {
        var used=draftBoxes.map(function(b){return {x:b.x,y:b.y,width:b.width,height:b.height}})
        return place(labels, used, avoid, level==="far")
    }
    // far: one notice for each inverter with strings to check, at its first string's name (R496 c)
    readonly property var notices: {
        if(level!=="far") return []
        var by={},order=[]
        for(var i=0;i<labels.length;++i) {
            var l=labels[i]
            if(l.kind!=="name") continue
            var inv=l.inverter||0
            if(!by[inv]) { by[inv]={inverter:inv,x:l.x,y:l.y,dirX:l.dirX,dirY:l.dirY,count:0,fail:0,kind:"name",run:-1,colour:l.colour,text:""}; order.push(inv) }
            if(l.state==="fail") by[inv].fail++
            if(l.state!=="ok") by[inv].count++
        }
        var items=[]
        for(var k=0;k<order.length;++k) {
            var n=by[order[k]]
            if(!n.count) continue
            n.text=(n.inverter ? qsTr("Inv. %1").arg(n.inverter) : qsTr("No inverter"))+"  "+n.count
            n.state=n.fail ? "fail" : "check"
            items.push(n)
        }
        var used=boxes.map(function(b){return {x:b.x,y:b.y,width:b.width,height:b.height}})
        return place(items, used, avoid, false)
    }
    FontMetrics { id: names; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL; font.weight: Font.Bold }
    FontMetrics { id: numbers; font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION; font.weight: Font.Bold }

    component Pill: Rectangle {
        id: pill
        required property var modelData
        readonly property bool isName: modelData.item.kind==="name"
        readonly property bool showSymbol: modelData.symbol>0 || modelData.item.run===-1 && modelData.item.kind==="name" && !modelData.disc
        objectName: "stringLabel-"+modelData.item.kind+"-"+modelData.item.run
        x:(modelData.x+modelData.width/2)*root.follow-modelData.width/2
        y:(modelData.y+modelData.height/2)*root.follow-modelData.height/2
        width:modelData.width; height:modelData.height; radius:height/2
        color: modelData.disc ? modelData.item.colour : backend.planColors.label_bg
        border.color: modelData.disc ? backend.planColors.label_fg : "transparent"; border.width: modelData.disc ? 1 : 0
        Rectangle {
            // the leader from the module's dot to the label, when the label had to move away
            visible: modelData.leader>3
            x:modelData.leaderX; y:modelData.leaderY-.5; width:modelData.leader; height:1
            transformOrigin: Item.Left; rotation: modelData.angle
            color: backend.planColors.label_fg; opacity: .85
        }
        Rectangle {
            visible: isName && !modelData.disc
            x:root.endGap(parent.height); y:(parent.height-height)/2; width:root.dotSize; height:width; radius:width/2
            color:modelData.item.colour; border.color:backend.planColors.label_fg
        }
        Text {
            visible: !modelData.disc
            x: isName ? modelData.left : 0
            width: isName ? implicitWidth : parent.width
            height:parent.height
            text:modelData.item.text; color:backend.planColors.label_fg
            font: isName ? names.font : numbers.font
            horizontalAlignment: isName ? Text.AlignLeft : Text.AlignHCenter
            verticalAlignment:Text.AlignVCenter
        }
        PlanSymbol {
            visible:pill.showSymbol; size:root.markSize; round: true
            x:parent.width-root.endGap(parent.height)-width; y:(parent.height-height)/2
            name: modelData.item.state==="ok" ? "check" : modelData.item.state==="fail" ? "stop" : "warning"
            shapes:backend.statusSymbols; fontFamily:Theme.fontFamily
        }
        // No MouseArea: a label lies over the modules and the click belongs to the module under it, as in the
        // Widgets plan (06/11/2026). The string is chosen from the Plant panel or by clicking its modules.
    }
    Repeater { model: root.boxes; delegate: Pill {} }
    Repeater { model: root.draftBoxes; delegate: Pill {} }
    Repeater { model: root.notices; delegate: Pill {} }

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
    Rectangle {
        visible: root.hovered!==null
        objectName: "stringLabel-hover"
        x: root.hovered ? (root.hovered.x+root.hovered.width/2)*root.follow+root.hovered.width/2+6 : 0
        y: root.hovered ? (root.hovered.y+root.hovered.height/2)*root.follow-height/2 : 0
        width: 2*(root.endGap(height)+Theme.space.XS)+root.dotSize+hoverText.implicitWidth+root.markSize; height: Math.max(names.height,16)+6; radius: height/2
        color: backend.planColors.label_bg; z: 3
        Rectangle { x:root.endGap(parent.height); y:(parent.height-height)/2; width:root.dotSize; height:width; radius:width/2
            color: root.hovered ? root.hovered.item.colour : "transparent"; border.color: backend.planColors.label_fg }
        Text { id: hoverText; x: root.endGap(parent.height)+root.dotSize+Theme.space.XS; height: parent.height
            text: root.hovered ? root.hovered.item.text : ""; color: backend.planColors.label_fg; font: names.font
            verticalAlignment: Text.AlignVCenter }
        PlanSymbol { visible: root.hovered!==null; size: root.markSize; round: true; x: parent.width-root.endGap(parent.height)-width; y: (parent.height-height)/2
            name: root.hovered && root.hovered.item.state==="ok" ? "check" : root.hovered && root.hovered.item.state==="fail" ? "stop" : "warning"
            shapes: backend.statusSymbols; fontFamily: Theme.fontFamily }
    }
}
