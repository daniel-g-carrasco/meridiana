.pragma library

function inside(p, ring) {
    var yes=false
    for(var i=0,j=ring.length-1;i<ring.length;j=i++) {
        var a=ring[i],b=ring[j]
        if((a.y>p.y)!==(b.y>p.y) && p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x) yes=!yes
    }
    return yes
}

function layout(screen, world, lengths, widths, h, xxs, xs, s, m, badges) {
    var out=[],disc=h-2*xxs,area=0
    for(var i=0;i<world.length;++i) {
        var a=world[i],b=world[(i+1)%world.length]
        area+=a[0]*b[1]-b[0]*a[1]
    }
    for(i=0;i<screen.length;++i) {
        a=screen[i];b=screen[(i+1)%screen.length]
        var dx=b.x-a.x,dy=b.y-a.y,n=Math.hypot(dx,dy)
        if(n<disc) continue
        var badge=badges ? Math.max(disc,badges[i]) : disc
        var wholeWidth=xxs+badge+xs+widths[i]+s,mx=(a.x+b.x)/2,my=(a.y+b.y)/2,away=h/2+xxs
        var candidates=[{x:mx+dy/n*away,y:my-dx/n*away},{x:mx-dy/n*away,y:my+dx/n*away}]
        var c0=!inside(candidates[0],screen),c1=!inside(candidates[1],screen)
        var centre=c0!==c1 ? candidates[c0?0:1] : candidates[area>0?0:1]
        for(var j=0;j<2;++j) {
            var whole=j===0,w=whole?wholeWidth:badge+2*xxs
            if(whole && n<wholeWidth+m) continue
            var box={side:i,x:centre.x-w/2,y:centre.y-h/2,width:w,height:h,whole:whole,text:lengths[i],badge:badge}
            var collision=out.some(function(o){return box.x<o.x+o.width && box.x+box.width>o.x && box.y<o.y+o.height && box.y+box.height>o.y})
            if(!collision) {out.push(box);break}
        }
    }
    return out
}
