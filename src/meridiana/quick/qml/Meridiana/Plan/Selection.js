.pragma library

// Preview geometry only. The session still commits through core sweep at release.
var EPS = 1e-9;
function point(p) { return Array.isArray(p) ? p : [p.x,p.y]; }
function box(ring) {
    var b=[Infinity,Infinity,-Infinity,-Infinity];
    for(var i=0;i<ring.length;i++) { var p=ring[i]; b[0]=Math.min(b[0],p[0]); b[1]=Math.min(b[1],p[1]);
        b[2]=Math.max(b[2],p[0]); b[3]=Math.max(b[3],p[1]); }
    return b;
}
function buildIndex(records) {
    var index=records.map(function(record) {
        var points=Array.prototype.map.call(record.points,point);
        return {points:points, bounds:box(points), record:record};
    });
    index.bounds=[Infinity,Infinity,-Infinity,-Infinity];index.all=[];
    for(var i=0;i<index.length;i++) {
        var b=index[i].bounds;
        index.bounds[0]=Math.min(index.bounds[0],b[0]);index.bounds[1]=Math.min(index.bounds[1],b[1]);
        index.bounds[2]=Math.max(index.bounds[2],b[2]);index.bounds[3]=Math.max(index.bounds[3],b[3]);
        if(index[i].points.length>=3) index.all.push(i);
    }
    return index;
}
function cross(a,b,c) { return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]); }
function onSegment(p,a,b) {
    return Math.abs(cross(a,b,p))<=EPS && p[0]>=Math.min(a[0],b[0])-EPS &&
        p[0]<=Math.max(a[0],b[0])+EPS && p[1]>=Math.min(a[1],b[1])-EPS && p[1]<=Math.max(a[1],b[1])+EPS;
}
function locate(p,ring) {
    var inside=false;
    for(var i=0,j=ring.length-1;i<ring.length;j=i++) {
        var a=ring[j],b=ring[i];
        if(onSegment(p,a,b)) return 0;
        if((a[1]>p[1])!==(b[1]>p[1]) && p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
    }
    return inside ? 1 : -1;
}
function cuts(a,b,c,d) {
    var rx=b[0]-a[0],ry=b[1]-a[1],sx=d[0]-c[0],sy=d[1]-c[1],det=rx*sy-ry*sx;
    if(Math.abs(det)<EPS) {
        if(Math.abs(cross(a,b,c))>EPS) return [];
        var den=rx*rx+ry*ry;
        if(den<EPS) return onSegment(a,c,d) ? [0] : [];
        return [((c[0]-a[0])*rx+(c[1]-a[1])*ry)/den,((d[0]-a[0])*rx+(d[1]-a[1])*ry)/den]
            .filter(function(t){return t>=-EPS && t<=1+EPS;}).map(function(t){return Math.max(0,Math.min(1,t));});
    }
    var t=((c[0]-a[0])*sy-(c[1]-a[1])*sx)/det, u=((c[0]-a[0])*ry-(c[1]-a[1])*rx)/det;
    return t>=-EPS && t<=1+EPS && u>=-EPS && u<=1+EPS ? [Math.max(0,Math.min(1,t))] : [];
}
function samples(a,b,ring) {
    var ts=[0,1],out=[];
    for(var i=0;i<ring.length;i++) ts=ts.concat(cuts(a,b,ring[i],ring[(i+1)%ring.length]));
    ts.sort(function(x,y){return x-y;});
    for(var j=1;j<ts.length;j++) if(ts[j]-ts[j-1]>EPS) {
        var t=(ts[j]+ts[j-1])/2;
        out.push([a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])]);
    }
    return out;
}
function prepare(ring) {
    var bounds=box(ring),axis=ring.length===4;
    for(var i=0;i<ring.length;i++) {
        var a=ring[i],b=ring[(i+1)%ring.length];
        if(a[0]!==b[0] && a[1]!==b[1]) axis=false;
    }
    if(axis) {
        var distinct={};for(var v=0;v<ring.length;v++) distinct[ring[v].join(",")]=true;
        axis=Object.keys(distinct).length===4 && bounds[2]>bounds[0] && bounds[3]>bounds[1];
    }
    var holes=[];
    if(!axis) {
        var delta=Math.max(1,bounds[2]-bounds[0],bounds[3]-bounds[1])*1e-7;
        for(var k=0;k<ring.length;k++) {
            var c=ring[k],d=ring[(k+1)%ring.length],dx=d[0]-c[0],dy=d[1]-c[1],length=Math.hypot(dx,dy);
            if(length<EPS) continue;
            var mids=samples(c,d,ring);
            for(var j=0;j<mids.length;j++) for(var side=-1;side<=1;side+=2) {
                var p=[mids[j][0]-side*dy/length*delta,mids[j][1]+side*dx/length*delta];
                if(locate(p,ring)<0) holes.push(p);
            }
        }
    }
    return {ring:ring,bounds:bounds,axis:axis,holes:holes};
}
function matches(points,area,kind) {
    var ring=area.ring,i,j;
    if(kind==="crossing") {
        if(points.some(function(p){return locate(p,ring)>=0;}) || ring.some(function(p){return locate(p,points)>=0;})) return true;
        for(i=0;i<points.length;i++) for(j=0;j<ring.length;j++)
            if(cuts(points[i],points[(i+1)%points.length],ring[j],ring[(j+1)%ring.length]).length) return true;
        return false;
    }
    if(points.some(function(p){return locate(p,ring)<0;})) return false;
    if(area.axis) return true;
    for(i=0;i<points.length;i++) {
        var mids=samples(points[i],points[(i+1)%points.length],ring);
        if(mids.some(function(p){return locate(p,ring)<0;})) return false;
    }
    return !area.holes.some(function(p){return locate(p,points)>0;});
}
function chosen(index,ring,kind) {
    if(ring.length<3) return [];
    var area=prepare(ring),b=area.bounds,out=[];
    if(area.axis && index.bounds && index.bounds[0]>=b[0] && index.bounds[1]>=b[1] &&
            index.bounds[2]<=b[2] && index.bounds[3]<=b[3]) return index.all;
    for(var i=0;i<index.length;i++) {
        var item=index[i],q=item.bounds;
        if(item.points.length<3) continue;
        if(kind==="window" ? q[0]<b[0] || q[1]<b[1] || q[2]>b[2] || q[3]>b[3] :
                             q[2]<b[0] || q[3]<b[1] || q[0]>b[2] || q[1]>b[3]) continue;
        if((area.axis && kind==="window") || matches(item.points,area,kind)) out.push(i);
    }
    return out;
}
function distance(p,a,b) {
    var dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy;
    var t=den ? Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) : 0;
    return Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy);
}
function changedBounds(index,before,after) {
    var i=0,j=0,dirty=null;
    while(i<before.length || j<after.length) {
        if(i<before.length && j<after.length && before[i]===after[j]) { i++;j++;continue; }
        var at=j>=after.length || (i<before.length && before[i]<after[j]) ? before[i++] : after[j++];
        var b=index[at].bounds;
        if(!dirty) dirty=b.slice();
        else { dirty[0]=Math.min(dirty[0],b[0]);dirty[1]=Math.min(dirty[1],b[1]);
               dirty[2]=Math.max(dirty[2],b[2]);dirty[3]=Math.max(dirty[3],b[3]); }
    }
    return dirty;
}
function hit(index,p,tolerance) {
    var winner=-1,best=Infinity;
    for(var i=index.length-1;i>=0;i--) {
        var q=index[i],b=q.bounds;
        if(p[0]<b[0]-tolerance || p[1]<b[1]-tolerance || p[0]>b[2]+tolerance || p[1]>b[3]+tolerance) continue;
        if(q.points.length>=3 && locate(p,q.points)>=0) return i;
        for(var j=0;j<q.points.length;j++) {
            var d=distance(p,q.points[j],q.points[(j+1)%q.points.length]);
            if(d<=tolerance && d<best) { winner=i; best=d; }
        }
    }
    return winner;
}
