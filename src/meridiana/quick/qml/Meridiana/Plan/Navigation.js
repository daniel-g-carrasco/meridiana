.pragma library

// Exact state-machine counterpart of core navigation.Navigator. Style data comes from Python once.
function same(a, b) { return a.slice().sort().join("|") === b.slice().sort().join("|"); }
function has(table, buttons, mods) {
    return table.some(function(g) { return same(g[0], buttons) && same(g[1], mods); });
}
function action(kind, phase, x, y, dx, dy, mods) {
    return {kind:kind, phase:phase, x:x, y:y, dx:dx || 0, dy:dy || 0, mods:mods.slice().sort()};
}
function create(style) {
    var nav = {
        style:style, held:[], mods:[], start:null, last:null, gesture:"", moved:false,
        swallow:"", before:"", spent:false,
        reset:function() {
            this.held=[]; this.start=null; this.last=null; this.gesture=""; this.moved=false;
            this.swallow=""; this.before=""; this.spent=false;
        },
        setStyle:function(data) { this.style=data; this.reset(); },
        chorded:function(button) {
            return this.style.pan.concat(this.style.orbit, this.style.zoom).some(function(g) {
                return g[0].length > 1 && g[0].indexOf(button) >= 0;
            });
        },
        previewsOrbit:function(mods) {
            return !this.held.length && !this.gesture && this.style.orbit.some(function(g) {
                return g[0].length && g[1].length && same(g[1], mods);
            });
        },
        match:function(buttons, mods) {
            var kinds=["orbit", "pan", "zoom"];
            for(var i=0;i<kinds.length;i++) if(has(this.style[kinds[i]], buttons, mods)) return kinds[i];
            if(has([[[],["space"]],[["left"],["space"]]],buttons,mods)) return "pan";
            if(has([[["left"],["shift"]]],buttons,mods)) return "orbit";
            return "";
        },
        drags:function(buttons, mods) { return !!this.match(buttons, mods); },
        switchGesture:function(x, y) {
            var out=[];
            var kind=(this.moved || !this.held.length) && !this.spent ? this.match(this.held,this.mods) : "";
            if(kind !== this.gesture) {
                if(this.gesture) out.push(action(this.gesture,"end",x,y,0,0,this.mods));
                this.gesture=kind;
                if(kind) out.push(action(kind,"begin",x,y,0,0,this.mods));
            }
            return out;
        },
        press:function(button,mods,x,y) {
            this.mods=mods.slice();
            if(!this.held.length) { this.start=[x,y]; this.moved=false; }
            else this.before=this.gesture;
            if(this.held.indexOf(button)<0) this.held.push(button);
            this.last=[x,y];
            return this.gesture ? this.switchGesture(x,y) : [];
        },
        move:function(x,y,mods) {
            if(mods !== undefined && mods !== null) this.mods=mods.slice();
            var out=[];
            if(this.last === null) this.last=[x,y];
            if(this.held.length && !this.moved && this.start !== null &&
                    Math.abs(x-this.start[0])+Math.abs(y-this.start[1])>4) this.moved=true;
            if(!this.held.length && !this.match([],this.mods) && !this.gesture) { this.last=[x,y]; return out; }
            if(this.moved || !this.held.length) out=out.concat(this.switchGesture(x,y));
            if(this.gesture) out.push(action(this.gesture,"move",x,y,x-this.last[0],y-this.last[1],this.mods));
            this.last=[x,y];
            return out;
        },
        release:function(button,mods,x,y) {
            this.mods=mods.slice();
            var out=[], was=this.held.slice();
            this.held=this.held.filter(function(b) { return b !== button; });
            if(this.gesture) {
                if(!this.held.length) { out.push(action(this.gesture,"end",x,y,0,0,this.mods)); this.gesture=""; }
                else if(["",this.before].indexOf(this.match(this.held,this.mods))<0) {
                    out.push(action(this.gesture,"end",x,y,0,0,this.mods)); this.gesture=""; this.spent=true;
                } else out=out.concat(this.switchGesture(x,y));
            } else if(button===this.swallow) this.swallow="";
            else if(!this.moved && same(was,[button])) out=out.concat(this.click(button,x,y));
            if(!this.held.length) { this.start=null; this.moved=false; this.spent=false; this.before=""; }
            return out;
        },
        click:function(button,x,y) {
            var kind="";
            if(button==="left" && has(this.style.select,["left"],this.mods)) kind="select";
            if(button==="middle") kind=this.style.middle_click;
            if(button==="right") kind=this.style.right_click;
            return kind ? [action(kind,"once",x,y,0,0,this.mods)] : [];
        },
        double:function(button,mods,x,y) {
            if(button==="middle" && this.style.middle_double) {
                this.swallow=button;
                return [action(this.style.middle_double,"once",x,y,0,0,mods)];
            }
            return [];
        },
        wheel:function(steps,mods,x,y) { return [action("wheel","once",x,y,0,steps,mods)]; }
    };
    return nav;
}
function wheelAction(angle,pixel,phased,synthesized,ctrl,touchpad) {
    var steps=angle[1] ? angle[1]/120 : pixel[1]/60;
    if(ctrl) return ["zoom",0,steps];
    var pixels=pixel[0] !== 0 || pixel[1] !== 0;
    if(touchpad || phased || synthesized || angle[0] || (pixels && angle[0]===0 && angle[1]===0)) {
        var delta=phased || pixels ? pixel : angle;
        return ["pan",delta[0],delta[1]];
    }
    return ["wheel",0,steps];
}
