.pragma library

// Qt scene axes: x East, y up, z South. The cube keeps parallel projection
// in both camera modes, as navicube.py does, so its click targets stay stable.
var normals = [[0,1,0],[0,-1,0],[0,0,-1],[0,0,1],[1,0,0],[-1,0,0]];

function dot(a, b) { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]; }
function axes(bearing, elevation) {
    var b = bearing*Math.PI/180, e = elevation*Math.PI/180;
    return {right: [Math.cos(b),0,Math.sin(b)],
            up: [-Math.sin(b)*Math.sin(e),Math.cos(e),Math.cos(b)*Math.sin(e)],
            forward: [Math.sin(b)*Math.cos(e),Math.sin(e),-Math.cos(b)*Math.cos(e)]};
}
function project(point, basis, scale) {
    return [dot(point,basis.right)*scale, -dot(point,basis.up)*scale];
}
function cells(bearing, elevation, size) {
    var basis = axes(bearing,elevation), scale = size/(2*Math.sqrt(3)), out = [];
    var bounds = [[-1,-0.44],[-0.44,0.44],[0.44,1]];
    for (var n = 0; n < normals.length; n++) {
        var normal = normals[n];
        if (-dot(normal,basis.forward) <= 0.000001) continue;
        var free = [];
        for (var axis = 0; axis < 3; axis++) if (normal[axis] === 0) free.push(axis);
        for (var i = -1; i <= 1; i++) for (var j = -1; j <= 1; j++) {
            var a = bounds[i+1], b = bounds[j+1], polygon = [], depth = 0;
            var corners = [[a[0],b[0]],[a[1],b[0]],[a[1],b[1]],[a[0],b[1]]];
            for (var k = 0; k < 4; k++) {
                var v = normal.slice(); v[free[0]] = corners[k][0]; v[free[1]] = corners[k][1];
                polygon.push(project(v,basis,scale)); depth += dot(v,basis.forward)/4;
            }
            var part = normal.slice(); part[free[0]] = i; part[free[1]] = j;
            out.push({part:part,polygon:polygon,depth:depth,face:i === 0 && j === 0,normal:n});
        }
    }
    out.sort(function(a,b) { return b.depth-a.depth; });
    return out;
}
function inside(polygon,x,y) {
    var result = false;
    for (var i = 0; i < polygon.length; i++) {
        var a = polygon[i], b = polygon[(i+1)%polygon.length];
        if ((a[1]>y) !== (b[1]>y) && x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]) result = !result;
    }
    return result;
}
function pick(cells,x,y) {
    for (var i = cells.length-1; i >= 0; i--) if (inside(cells[i].polygon,x,y)) return cells[i].part;
    return null;
}
function lookingFrom(part,bearing) {
    var norm = Math.sqrt(dot(part,part));
    var elevation = -Math.asin(part[1]/norm)*180/Math.PI;
    if (!part[0] && !part[2]) {
        var quarter = bearing/90, floor = Math.floor(quarter);
        var rounded = Math.abs(quarter-floor-0.5)<1e-12 ? floor+(floor%2) : Math.round(quarter);
        return [(rounded*90+360)%360,elevation];
    }
    return [(Math.atan2(-part[0],part[2])*180/Math.PI+360)%360,elevation];
}
function turned(bearing,elevation,arrow) {
    if (arrow === "left") return [(bearing+315)%360,elevation];
    if (arrow === "right") return [(bearing+45)%360,elevation];
    if (arrow === "up") return [bearing,Math.max(-90,elevation-45)];
    return [bearing,Math.min(90,elevation+45)];
}
