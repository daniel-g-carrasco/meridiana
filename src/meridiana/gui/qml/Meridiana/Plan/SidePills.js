.pragma library
.import "../Controls/PillPlace.js" as Place

function inside(p, ring) {
    var yes=false
    for(var i=0,j=ring.length-1;i<ring.length;j=i++) {
        var a=ring[i],b=ring[j]
        if((a.y>p.y)!==(b.y>p.y) && p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x) yes=!yes
    }
    return yes
}

// The sides' pills of the outline selected: beside each side, outside the outline; the disc alone where the whole pill
// would cover another or the side is too short. The width, the two places and the overlap are the measures' too
// (Controls/PillPlace.js).
function layout(screen, world, lengths, widths, h, xxs, xs, s, m, badges) {
    var out=[],disc=h-2*xxs,area=0
    for(var i=0;i<world.length;++i) {
        var a=world[i],b=world[(i+1)%world.length]
        area+=a[0]*b[1]-b[0]*a[1]
    }
    for(i=0;i<screen.length;++i) {
        a=screen[i];b=screen[(i+1)%screen.length]
        var n=Math.hypot(b.x-a.x,b.y-a.y)
        if(n<disc) continue
        var badge=badges ? Math.max(disc,badges[i]) : disc
        var wholeWidth=Place.width(widths[i],0,badge,xxs,xs,s),away=h/2+xxs
        var candidates=Place.beside(a,b,away)
        var c0=!inside(candidates[0],screen),c1=!inside(candidates[1],screen)
        var centre=c0!==c1 ? candidates[c0?0:1] : candidates[area>0?0:1]
        for(var j=0;j<2;++j) {
            var whole=j===0,w=whole?wholeWidth:badge+2*xxs
            if(whole && n<wholeWidth+m) continue
            var angle=Place.readable(Math.atan2(b.y-a.y,b.x-a.x)*180/Math.PI)
            var box={direction:angle,side:i,x:centre.x-w/2,y:centre.y-h/2,width:w,height:h,whole:whole,text:lengths[i],badge:badge}
            box.bounds=Place.rotatedBox(box.x,box.y,w,h,angle)
            if(!Place.overlaps(box.bounds,out.map(function(o){return o.bounds}))) {out.push(box);break}
        }
    }
    return out
}
