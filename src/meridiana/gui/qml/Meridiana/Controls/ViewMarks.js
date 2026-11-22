.pragma library

// The shared small snap symbols, as paths for ViewStroke and batched ViewPath.
function path(kind, c, radius) {
        const r = radius, x = c.x, y = c.y
        if (kind === "vertex") return "M"+(x-r)+","+(y-r)+" h"+2*r+" v"+2*r+" h"+(-2*r)+" Z"
        if (kind === "midpoint") return "M"+x+","+(y-r)+" L"+(x+r)+","+(y+r)+" L"+(x-r)+","+(y+r)+" Z"
        if (kind === "edge") return "M"+(x-r)+","+(y-r)+" L"+(x+r)+","+(y-r)+" L"+(x-r)+","+(y+r)+" L"+(x+r)+","+(y+r)+" Z"
        if (kind === "face") return "M"+x+","+(y-r)+" L"+(x+r)+","+y+" L"+x+","+(y+r)+" L"+(x-r)+","+y+" Z"
        if (kind === "intersection") return "M"+(x-r)+","+(y-r)+" L"+(x+r)+","+(y+r)+" M"+(x+r)+","+(y-r)+" L"+(x-r)+","+(y+r)
        if (kind === "perpendicular") return "M"+(x-r)+","+(y+r)+" L"+(x+r)+","+(y+r)+" M"+x+","+(y+r)+" L"+x+","+(y-r)
        return "M"+(x-r)+","+y+" a"+r+","+r+" 0 1,0 "+2*r+",0 a"+r+","+r+" 0 1,0 "+(-2*r)+",0 Z"
    }
