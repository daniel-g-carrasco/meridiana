import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Dialogs as NativeDialogs
import Meridiana.Theme
import Meridiana.Controls as Controls
import "Navigation.js" as Navigation

Rectangle {
    id: plan
    objectName: "plan"
    required property var backend
    property string renderer: "batched"
    property real zoom: 1
    property real panX: width / 2
    property real panY: height / 2
    property real bearing: 0
    property rect toolbarBounds: Qt.rect(0,0,0,0)
    property real previousWidth: 0
    property real previousHeight: 0
    property bool fitted: true
    property bool spaceHeld: false
    property string localHint: ""
    readonly property string statusText: backend.error || localHint || backend.hint
    // ui/plan.py cursorInfo; only while the pointer is here, and without Python at each step.
    readonly property string cursorText: {
        if (!mouse.containsMouse) return ""
        const q=world(pointer.x,pointer.y), locale=Qt.locale()
        return "E "+q.x.toLocaleString(locale,'f',2)+"  N "+q.y.toLocaleString(locale,'f',2)+" m"
    }
    // the longest the pointer's coordinates are on this plan (R484): the farthest of its extent, both signs, at least
    // four digits before the comma, in digits all as wide as each other
    readonly property string cursorLongest: {
        const locale=Qt.locale(), extent=Math.max(9999.99, 0)
        const n=(-extent).toLocaleString(locale,'f',2).replace(/[0-9]/g,"0")
        return "E "+n+"  N "+n+" m"
    }
    property string viewMode: "both"
    property int pointerModifiers: 0
    // R529: how far the hand may move between press and release and still click, in logical pixels: 4 was 4 physical
    // pixels at scale 1, where a hand on a real mouse moves 1-4 (a click became a selection window or a side dragged)
    readonly property real clickSlop: 6
    property var navigator: Navigation.create(backend.navigationStyle)
    property point pointer: Qt.point(0, 0)
    property int vertexDragIndex: -1
    property int hotVertex: -1       // the corner the pointer is on (R427): it wins over all that lies under it
    onHotVertexChanged: localHint=hotVertex>=0 ? backend.texts.vertex+" "+backend.texts.corners : ""
    // R356: the corners chosen move with the one dragged, by the same step
    property bool cornerGroup: false
    function cornerAt(i, x, y) {
        if (vertexDragIndex<0) return screen(x,y)
        if (i===vertexDragIndex) return screen(vertexDragPoint.x,vertexDragPoint.y)
        if (cornerGroup && backend.chosenCorners.indexOf(i)>=0) {
            var g=backend.grips[vertexDragIndex]
            return screen(x+vertexDragPoint.x-g.x,y+vertexDragPoint.y-g.y)
        }
        return screen(x,y)
    }
    // the arrows move the corners chosen along the screen, whatever way the plan is turned
    function moveCornersBy(sx, sy, step) {
        var a=world(width/2,height/2), b=world(width/2+sx,height/2+sy)
        var dx=b.x-a.x, dy=b.y-a.y, n=Math.hypot(dx,dy) || 1
        backend.moveCorners(step*dx/n,step*dy/n)
    }
    property point vertexDragPoint: Qt.point(0,0)
    property var polygons: backend.objects
    property var modules: backend.modules
    property int paintedModules: modules.length
    readonly property int renderedModules: geometry.visible ? (geometry.ready ? modules.length : 0) : modules.length
    property int polygonCount: polygons.length + modules.length
    property var preview: backend.preview
    property color ink: backend.planColors.label_fg
    color: backend.planColors.bg
    clip: true
    focus: true

    ViewCorners { anchors.fill: parent; z: 1000 }

    function world(x, y) {
        var p = worldLayer.mapFromItem(plan, x, y)
        return Qt.point(p.x, -p.y)
    }
    function screen(x, y) {
        // Explicit dependencies keep screen-sized overlays attached during camera changes.
        var a=bearing*Math.PI/180, c=Math.cos(a), s=Math.sin(a)
        return Qt.point(panX+zoom*(x*c+y*s),panY+zoom*(x*s-y*c))
    }
    function fit() {
        fitBounds(backend.bounds)
    }
    function fitBounds(b) {
        if (!b || width < 1 || height < 1) return
        var margin=Math.max(b[2],b[3])*.15+5
        var a=bearing*Math.PI/180,c=Math.cos(a),s=Math.sin(a)
        var w=b[2]+2*margin,h=b[3]+2*margin
        zoom = Math.max(.00002,Math.min((width-4)/(Math.abs(w*c)+Math.abs(h*s)),
                                      (height-4)/(Math.abs(w*s)+Math.abs(h*c))))
        var cx=b[0]+b[2]/2,cy=b[1]+b[3]/2
        panX = width/2 - (cx*c-cy*s)*zoom
        panY = height/2 - (cx*s+cy*c)*zoom
        fitted = true
    }
    function zoomAt(factor, x, y) {
        fitted = false
        var old = worldLayer.mapFromItem(plan,x,y)
        zoom = Math.max(0.00002, Math.min(5000,zoom*factor))
        var now = worldLayer.mapToItem(plan,old)
        panX += x-now.x; panY += y-now.y
    }
    function rotateView(degrees) {
        fitted = false
        var old = worldLayer.mapFromItem(plan,width/2,height/2)
        bearing = (bearing+degrees)%360
        var now = worldLayer.mapToItem(plan,old)
        panX += width/2-now.x; panY += height/2-now.y
    }
    function keyName(event) {
        var names = {}
        names[Qt.Key_Escape]="Escape"; names[Qt.Key_Return]="Enter"; names[Qt.Key_Enter]="Enter"
        names[Qt.Key_Backspace]="Backspace"; names[Qt.Key_Delete]="Delete"; names[Qt.Key_Tab]="Tab"; names[Qt.Key_Backtab]="Backtab"
        names[Qt.Key_C]="C"; names[Qt.Key_X]="X"; names[Qt.Key_V]="V"    // with Ctrl the text is a control character
        names[Qt.Key_Left]="Left"; names[Qt.Key_Right]="Right"; names[Qt.Key_Up]="Up"; names[Qt.Key_Down]="Down"
        names[Qt.Key_Shift]="Shift"; names[Qt.Key_Control]="Control"
        names[Qt.Key_F3]="F3"; names[Qt.Key_F8]="F8"
        return names[event.key] || event.text.toUpperCase()
    }
    function mods(value) { return ((value & Qt.ControlModifier) && !(value & Qt.AltModifier) ? 1 : 0)
                               | ((value & Qt.ShiftModifier) ? 2 : 0) | ((value & Qt.AltModifier) ? 4 : 0) }
    function navMods(value) {
        var out=[]
        if(value & Qt.ControlModifier) out.push("ctrl")
        if(value & Qt.ShiftModifier) out.push("shift")
        if(value & Qt.AltModifier) out.push("alt")
        if(spaceHeld) out.push("space")
        return out
    }
    // The menu first: a command renews the entries, and a menu whose triggered entry has gone stays open.
    function runContext(command) { menu.close(); Qt.callLater(function(){ backend.contextCommand(command) }) }
    function buttonName(value) { return value===Qt.LeftButton ? "left" : value===Qt.MiddleButton ? "middle" : "right" }
    function navigate(actions) {
        for(var i=0;i<actions.length;i++) {
            var a=actions[i]
            if(a.kind==="pan" && a.phase==="move") { fitted=false; panX+=a.dx; panY+=a.dy }
            else if(a.kind==="zoom" && a.phase==="move") zoomAt(Math.pow(1.2,-a.dy/40),width/2,height/2)
            else if(a.kind==="recentre") { fitted=false; panX+=width/2-a.x; panY+=height/2-a.y }
            else if(a.kind==="fit") fit()
            else if(a.kind==="menu") {
                backend.pointerScale(1/zoom,bearing)
                var point=world(a.x,a.y); backend.contextAt(point.x,point.y); menu.popup(a.x,a.y)
            }
        }
    }
    function vertexAt(x, y) {
        if(!backend.grips.length) return -1
        var p=world(x,y)
        return backend.vertexAt(p.x,p.y,1/zoom)
    }
    function changedView() {
        mapDelay.restart()
        if(vertexDragIndex<0) hotVertex=-1
        if (backend.sideEditing) backend.cancelSide()
    }
    // R496/R498: the labels and the dashes are laid out at the zoom the wheel settled on, and only scaled meanwhile.
    // R541: settled 300 ms after the last step, a lone step too: a hand turns the wheel a notch every 150-250 ms, and
    // a step that settled at once laid out the strings' names and the dashes again at every notch (40-110 ms each).
    property real settledZoom: 1
    readonly property int settleDelay: 300
    Timer { id: settleZoom; interval: plan.settleDelay; onTriggered: plan.settledZoom=plan.zoom }
    onZoomChanged: {
        changedView()
        if (startingUp) { settleZoom.stop(); settledZoom=zoom } else settleZoom.restart()
    }
    onPanXChanged: changedView()
    onPanYChanged: changedView()
    onBearingChanged: changedView()
    // R431: the plan's scale and centre stay when a panel or a section takes room from it, framed or not: it is framed
    // again only while the window comes up and when the window itself changes size. The Widgets frame again at any
    // resize until the designer moves the view (ui/plan.py resizeEvent), which is what Daniel saw there.
    property bool startingUp: true
    Timer { interval: 1500; running: plan.visible && plan.startingUp; onTriggered: plan.startingUp=false }
    property size seenWindow: Qt.size(0,0)
    function frameAgain() {
        const now=Qt.size(plan.Window.width,plan.Window.height), changed=now.width!==seenWindow.width || now.height!==seenWindow.height
        seenWindow=now
        return fitted && (startingUp || changed)
    }
    // While the window is being resized the drawing only keeps its centre (a translation, nothing laid out again);
    // it is framed again once the size has stopped changing (R470: framed at every step, each step cost a zoom
    // change of 40-180 ms and the resize stuttered). While the window comes up it is framed at once, as before.
    Timer { id: refit; interval: 120; onTriggered: plan.fit() }
    function sizeChanged() {
        if (!frameAgain()) return
        if (startingUp) Qt.callLater(fit)
        else refit.restart()
    }
    onWidthChanged: {
        if (previousWidth>0) panX+=(width-previousWidth)/2
        previousWidth=width
        sizeChanged()
    }
    onHeightChanged: {
        if (previousHeight>0) panY+=(height-previousHeight)/2
        previousHeight=height
        sizeChanged()
    }
    Component.onCompleted: Qt.callLater(fit)
    Keys.onShortcutOverride: function(event) {
        // The window's Esc must not bypass the drawing machine's three levels.
        // R454: placing an imported IFC model takes R, C, M, Enter and the arrows as Move does
        var moving=backend.tool==="move" || backend.tool==="rotate" || !!backend.placing.active
            || (backend.tool==="select" && backend.chosenCorners.length>0 && !backend.sideEditing)
        var arrows=[Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down]
        var moveKeys=[Qt.Key_R,Qt.Key_C,Qt.Key_M,Qt.Key_Tab,Qt.Key_Backtab,Qt.Key_Return,Qt.Key_Enter,Qt.Key_Backspace]
        var plain=!(event.modifiers & (Qt.ControlModifier|Qt.AltModifier))
        var clipTool=backend.tool==="select" || backend.tool==="paste"
        var clipKey=[Qt.Key_C,Qt.Key_X,Qt.Key_V].indexOf(event.key)>=0
            && (event.modifiers & Qt.ControlModifier) && !(event.modifiers & Qt.AltModifier)
        if (clipTool && clipKey) { event.accepted=true; return }
        if (backend.tool==="select" && plain && (event.key===Qt.Key_Tab || event.key===Qt.Key_Backtab)) { event.accepted=true; return }
        if (event.key===Qt.Key_Escape || (moving && (arrows.indexOf(event.key)>=0 ||
            (plain && (moveKeys.indexOf(event.key)>=0 || /^[0-9,.;-]+$/.test(event.text)))))) event.accepted=true
    }
    Keys.onPressed: function(event) {
        pointerModifiers=event.modifiers
        if(event.key===Qt.Key_Shift) pointerModifiers|=Qt.ShiftModifier
        if(event.key===Qt.Key_Control) pointerModifiers|=Qt.ControlModifier
        if (event.key===Qt.Key_Escape && vertexDragIndex>=0) { vertexDragIndex=-1; hotVertex=-1; event.accepted=true; return }
        if (backend.tool==="select" && backend.chosenCorners.length>0 && !backend.sideEditing) {
            // R356: Esc lets the corners go, the arrows move them (Shift 1 m, Ctrl 1 cm), a figure opens the measure
            if (event.key===Qt.Key_Escape) { backend.chooseCorners([],0); event.accepted=true; return }
            var arrow=[Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down].indexOf(event.key)
            if (arrow>=0) {
                moveCornersBy([-1,1,0,0][arrow],[0,0,-1,1][arrow],
                              event.modifiers&Qt.ControlModifier ? 0.01 : event.modifiers&Qt.ShiftModifier ? 1 : 0.1)
                event.accepted=true; return
            }
            if (event.text && /^[0-9,.;-]$/.test(event.text) && !(event.modifiers & (Qt.ControlModifier|Qt.AltModifier))) {
                cornerField.open(event.text); event.accepted=true; return
            }
        }
        if (event.key===Qt.Key_Tab || event.key===Qt.Key_Backtab || event.key===Qt.Key_V) {
            // Tab and a paste work where the pointer stands, which Select does not otherwise tell the backend.
            var here=world(pointer.x,pointer.y)
            backend.pointer(here.x,here.y,0,1/zoom)
        }
        if (event.key===Qt.Key_Escape && mouse.swept) {
            mouse.swept=false; mouse.navigated=true; mouse.leftPending=false; sweep.requestPaint()
            event.accepted=true; return
        }
        if (event.key===Qt.Key_Space) {
            if (backend.hotGrip) backend.key("Space",event.text,mods(event.modifiers))
            else if (!event.isAutoRepeat) spaceHeld=true
            event.accepted=true; return
        }
        if (event.key===Qt.Key_N && !event.modifiers && backend.tool==="select") { rotateView(-bearing); event.accepted=true; return }
        if (event.key===Qt.Key_F && !event.modifiers && backend.tool==="select") { fitBounds(backend.targetBounds); event.accepted=true; return }
        backend.key(keyName(event),event.text,mods(event.modifiers))
        event.accepted=true
    }
    Keys.onReleased: function(event) {
        pointerModifiers=event.modifiers
        if(event.key===Qt.Key_Shift) pointerModifiers&=~Qt.ShiftModifier
        if(event.key===Qt.Key_Control) pointerModifiers&=~Qt.ControlModifier
        if (event.key===Qt.Key_Space && !event.isAutoRepeat) spaceHeld=false
        if (event.key===Qt.Key_Shift || event.key===Qt.Key_Control) backend.releaseKey(keyName(event))
    }
    onActiveFocusChanged: if (!activeFocus) { spaceHeld=false; navigator.reset() }
    Connections {
        target: backend
        function onAlignRequested(angle) { plan.rotateView(angle-plan.bearing) }
        function onViewCommand(command) {
            if (command==="frame") plan.fitBounds(backend.targetBounds)
            else if (command==="fit") plan.fitBounds(backend.targetBounds)
            else if (command==="zoom_in") plan.zoomAt(1.2,width/2,height/2)
            else if (command==="zoom_out") plan.zoomAt(1/1.2,width/2,height/2)
            else if (command==="north") plan.rotateView(-plan.bearing)
            else if (command==="rename") { renameField.text=backend.selectionName; renameDialog.open() }
        }
        function onStateChanged() { if (backend.tool!=="select" && !backend.sideEditing) plan.forceActiveFocus() }
        function onOverlayChanged() { if (plan.vertexDragIndex<0 && !vertexMouse.containsMouse) plan.hotVertex=-1 }
        function onNavigationChanged() { plan.navigator.setStyle(backend.navigationStyle) }
    }
    Timer {
        id: mapDelay; interval: 140
        onTriggered: {
            var a=plan.world(0,0), b=plan.world(plan.width,0), c=plan.world(0,plan.height), d=plan.world(plan.width,plan.height)
            backend.viewSettled(Math.min(a.x,b.x,c.x,d.x),Math.min(a.y,b.y,c.y,d.y),
                Math.max(a.x,b.x,c.x,d.x),Math.max(a.y,b.y,c.y,d.y),1/plan.zoom,Screen.devicePixelRatio)
        }
    }
    Loader {
        anchors.fill: parent
        active: backend.maps !== null
        source: active ? "MapLayer.qml" : ""
        onLoaded: {
            item.backend=Qt.binding(function(){return backend.maps})
            item.viewScale=Qt.binding(function(){return plan.zoom})
            item.offsetX=Qt.binding(function(){return plan.panX})
            item.offsetY=Qt.binding(function(){return plan.panY})
            item.viewRotation=Qt.binding(function(){return plan.bearing})
        }
    }
    Item {
        id: worldLayer
        objectName: "worldLayer"
        x: plan.panX; y: plan.panY
        scale: plan.zoom; rotation: plan.bearing
        transformOrigin: Item.TopLeft
        property real settledScale: plan.settledZoom
        PolygonLayer {
            objects: plan.polygons.filter(function(o){return o.kind!=="prop" && o.kind!=="prop_mark"}); halo: true
            hatchSource: backend.hatchSource
            patternTransform: {
                var a=plan.bearing*Math.PI/180,c=Math.cos(a)/plan.zoom,s=Math.sin(a)/plan.zoom
                return Qt.matrix4x4(c,s,0,-c*plan.panX-s*plan.panY,-s,c,0,s*plan.panX-c*plan.panY,0,0,1,0,0,0,0,1)
            }
        }
        ModuleBatch {
            id: geometry
            objectName: "moduleGeometry"
            width: 1; height: 1
            curves: plan.renderer!=="triangles"
            visible: plan.renderer==="batched" || plan.renderer==="triangles" || plan.renderer==="geometry"
            modules: visible ? plan.modules : []
            // R547: a layout that moves modules: they fade in at their place, no jump and no flash
            NumberAnimation on opacity { id: modulesFade; running: false; from: 0.35; to: 1; duration: Theme.motion.FAST; easing.type: Theme.motion.EASE }
            Connections { target: backend; function onModulesMoved() { if (!Theme.reducedMotion) modulesFade.restart() } }
        }
        PolygonLayer { objects: plan.renderer==="shapes" ? plan.modules : []; modules: true }
        PolygonLayer { objects: plan.polygons.filter(function(o){return o.kind==="prop" || o.kind==="prop_mark"}); halo: true }
        Repeater {
            model: backend.shadows
            delegate: Shape {
                required property var modelData
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    fillColor: Theme.colors.overlay.shade; strokeColor: "transparent"; fillRule: ShapePath.OddEvenFill
                    PathSvg { path: modelData.path }
                }
            }
        }
        // R496: the finished strings, the modules in no string, the draft and the band to the pointer are layers of
        // their own, each made again only when it changes; the small ones are built at once, never in a thread
        // that leaves them blank for a few frames.
        // They stay built in every phase and are only shown in Plant (R483): no item made again on the way back.
        ModuleBatch { objectName: "wireFills"; width: 1; height: 1; modules: backend.wireFills; visible: backend.stringsVisible }
        ModuleBatch { objectName: "unwiredBatch"; width: 1; height: 1; modules: backend.unwiredPaths; sync: true; visible: backend.stringsVisible }
        ModuleBatch { objectName: "wiresBatch"; modules: backend.wires; visible: backend.stringsVisible }
        ModuleBatch { objectName: "optimizerBatch"; preset: backend.optimizerPaths; visible: backend.stringsVisible }
        ModuleBatch { objectName: "draftFills"; width: 1; height: 1; modules: backend.draftFills; sync: true; visible: backend.stringsVisible }
        ModuleBatch { objectName: "draftWires"; modules: backend.draftWires; sync: true; visible: backend.stringsVisible }
        Shape {
            id: band; objectName: "draftBand"
            readonly property var ends: backend.draftBand
            visible: ends.length===4 && backend.stringsVisible
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: backend.draftColour || plan.ink; strokeWidth: 1.5; cosmeticStroke: true
                strokeStyle: ShapePath.DashLine; dashPattern: [6/worldLayer.settledScale, 4/worldLayer.settledScale]
                fillColor: "transparent"
                startX: band.visible ? band.ends[0] : 0; startY: band.visible ? band.ends[1] : 0
                PathLine { x: band.visible ? band.ends[2] : 0; y: band.visible ? band.ends[3] : 0 }
            }
        }
        // Widgets put hover at Z_SELECTION - 1: it must not erase the solid selection.
        PolygonLayer { objects: sweep.hoveredRidges }
        PolygonLayer { objects: sweep.hoveredOutline }
        PolygonLayer { objects: backend.highlights }
        ModuleBatch { width: 1; height: 1; preset: backend.moduleHighlightPaths }
        PolygonLayer { objects: backend.draftObjects }
    }
    Canvas {
        id: raster
        anchors.fill: parent
        visible: plan.renderer==="canvas"
        onVisibleChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections {
            target: plan
            function onModulesChanged() { raster.requestPaint() }
            function onZoomChanged() { if (raster.visible) raster.requestPaint() }
            function onPanXChanged() { if (raster.visible) raster.requestPaint() }
            function onPanYChanged() { if (raster.visible) raster.requestPaint() }
            function onBearingChanged() { if (raster.visible) raster.requestPaint() }
        }
        onPaint: {
            if (!visible) return
            var ctx=getContext("2d"); ctx.reset(); ctx.clearRect(0,0,width,height)
            ctx.translate(plan.panX,plan.panY); ctx.rotate(plan.bearing*Math.PI/180); ctx.scale(plan.zoom,plan.zoom)
            ctx.fillStyle=Theme.colors.overlay.module; ctx.strokeStyle=Theme.colors.overlay.module_line; ctx.lineWidth=1/plan.zoom
            for (var i=0;i<plan.modules.length;++i) {
                var pts=plan.modules[i].points
                ctx.beginPath(); ctx.moveTo(pts[0].x,pts[0].y)
                for(var j=1;j<pts.length;++j) ctx.lineTo(pts[j].x,pts[j].y)
                ctx.closePath(); ctx.fill(); ctx.stroke()
            }
        }
    }
    MouseArea {
        id: mouse
        objectName: "planMouse"
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        cursorShape: plan.spaceHeld ? Qt.OpenHandCursor : backend.tool==="select" ? Qt.ArrowCursor : Qt.CrossCursor
        property point last: Qt.point(0,0)
        property point start: Qt.point(0,0)
        property bool swept: false
        property bool lasso: false
        property string sweepKind: "window"
        property bool navigated: false
        property bool stringPress: false
        property bool leftPending: false
        property int leftModifiers: 0
        property var trail: []
        property double pressedAt: 0
        onPressed: function(event) {
            plan.forceActiveFocus(); backend.pointerScale(1/plan.zoom,plan.bearing); plan.pointer=Qt.point(event.x,event.y)
            if(event.button!==Qt.LeftButton) { swept=false; sweep.requestPaint() }
            if(event.button!==Qt.LeftButton && leftPending) {
                plan.navigator.press("left",plan.navMods(leftModifiers),start.x,start.y)
                leftPending=false
            }
            if(event.button!==Qt.LeftButton || plan.navigator.held.length || plan.spaceHeld) {
                navigated=true
                plan.navigate(plan.navigator.press(plan.buttonName(event.button),plan.navMods(event.modifiers),event.x,event.y))
                return
            }
            plan.hotVertex=-1
            start=last=plan.pointer
            pressedAt=Date.now(); swept=false; lasso=false; navigated=false; trail=[last]
            leftPending=true; leftModifiers=event.modifiers
            stringPress=event.button===Qt.LeftButton && (backend.tool==="string" || backend.tool==="draw_string")
            if(stringPress) { var p=plan.world(event.x,event.y); backend.click(p.x,p.y,plan.mods(event.modifiers)) }
        }
        onPositionChanged: function(event) {
            plan.pointer=Qt.point(event.x,event.y)
            plan.pointerModifiers=event.modifiers
            plan.hotVertex=-1       // this area has the pointer: it is on no corner
            if(plan.navigator.held.length || (!event.buttons &&
                    (plan.navigator.gesture || plan.navigator.drags([],plan.navMods(event.modifiers))))) {
                plan.navigate(plan.navigator.move(event.x,event.y,plan.navMods(event.modifiers)))
                return
            }
            if(!event.buttons) plan.navigator.move(event.x,event.y,plan.navMods(event.modifiers))
            if(event.buttons===Qt.LeftButton && backend.tool==="select" && !backend.collecting) {
                if(!swept && Math.hypot(event.x-start.x,event.y-start.y)>plan.clickSlop) {
                    swept=true; lasso=Date.now()-pressedAt>350; sweepKind=event.x>=start.x ? "window" : "crossing"
                }
                if(swept) { if(lasso) trail=trail.concat([plan.pointer]); sweep.requestPaint() }
            }
            else if(backend.tool!=="select" || backend.collecting) {
                var p=plan.world(event.x,event.y)
                if(event.buttons===Qt.LeftButton && (backend.tool==="string" || backend.tool==="draw_string"))
                    backend.drag(p.x,p.y,plan.mods(event.modifiers))
                else backend.pointer(p.x,p.y,plan.mods(event.modifiers),1/plan.zoom)
            }
            last=Qt.point(event.x,event.y)
        }
        onReleased: function(event) {
            var button=plan.buttonName(event.button)
            if(plan.navigator.held.indexOf(button)>=0) {
                plan.navigate(plan.navigator.release(button,plan.navMods(event.modifiers),event.x,event.y))
                if(event.button===Qt.LeftButton) leftPending=false
                return
            }
            var p=plan.world(event.x,event.y)
            if(swept) {
                var points=lasso ? trail : [start,Qt.point(event.x,start.y),Qt.point(event.x,event.y),Qt.point(start.x,event.y)]
                // R356: a window over some corners of what is selected (not all of them: that is the thing) takes them
                var inside=[], grips=backend.grips
                for(var gi=0;gi<grips.length;gi++) {
                    var gp=plan.screen(grips[gi].x,grips[gi].y)
                    if(!lasso && gp.x>=Math.min(start.x,event.x) && gp.x<=Math.max(start.x,event.x)
                       && gp.y>=Math.min(start.y,event.y) && gp.y<=Math.max(start.y,event.y)) inside.push(grips[gi].index)
                }
                if(inside.length>0 && inside.length<grips.length) {
                    backend.chooseCorners(inside,plan.mods(event.modifiers))
                    swept=false; sweep.requestPaint(); leftPending=false; return
                }
                backend.sweep(points.map(function(p){var q=plan.world(p.x,p.y); return [q.x,q.y]}),
                    lasso ? sweepKind : event.x>=start.x ? "window" : "crossing",plan.mods(event.modifiers))
                swept=false; sweep.requestPaint()
            } else if(!navigated && Math.hypot(event.x-start.x,event.y-start.y)<=plan.clickSlop) {
                // R529: a click takes what was under the press: the hand moves a pixel or two before the release
                var q=plan.world(start.x,start.y)
                if(event.button===Qt.LeftButton && !stringPress) backend.click(q.x,q.y,plan.mods(event.modifiers))
            }
            leftPending=false
        }
        onDoubleClicked: function(event) {
            if(event.button!==Qt.LeftButton) {
                plan.navigate(plan.navigator.double(plan.buttonName(event.button),plan.navMods(event.modifiers),event.x,event.y))
                return
            }
            var p=plan.world(event.x,event.y)
            navigated=true; leftPending=false
            backend.doubleClick(p.x,p.y,plan.mods(event.modifiers))
        }
    }
    function wheel(event) {
        // R454: the wheel held with Shift turns the model being placed (Qt may give the notch on x with Shift)
        if (backend.placing.active && (event.modifiers & Qt.ShiftModifier)) {
            var notch=event.angleDelta.y!==0 ? event.angleDelta.y : event.angleDelta.x
            if (notch!==0) backend.placeWheel(notch>0 ? 1 : -1, plan.mods(event.modifiers))
            event.accepted=true
            return
        }
        // QQuickWheelEvent exposes its device, but does not expose QWheelEvent.source().
        var action=Navigation.wheelAction([event.angleDelta.x,event.angleDelta.y],
            [event.pixelDelta.x,event.pixelDelta.y],event.phase!==Qt.NoScrollPhase,false,
            !!(event.modifiers & Qt.ControlModifier) && !(event.modifiers & Qt.AltModifier),
            event.device.type===PointerDevice.TouchPad)
        if(action[0]==="pan") { plan.fitted=false; plan.panX+=action[1]; plan.panY+=action[2] }
        else plan.zoomAt(Math.pow(1.2,action[2]),event.x,event.y)
        event.accepted=true
    }
    // R545 (Daniel 08/11/2026: «lo scrolling laterale non funziona»): a WheelHandler takes only the wheel of its
    // `orientation` (Qt.Vertical by default) until it is active, so two fingers moved sideways, which give no y at all,
    // never reached the plan, on Wayland and on Windows alike. The twin takes those, and only while the upright one is
    // not already in a gesture (an active handler takes every event, sideways ones included).
    WheelHandler {
        id: uprightWheel
        objectName: "uprightWheel"
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(event) { plan.wheel(event) }
    }
    WheelHandler {
        objectName: "sidewaysWheel"
        target: null
        orientation: Qt.Horizontal
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(event) {
            if (uprightWheel.active || event.angleDelta.y!==0 || event.pixelDelta.y!==0) return
            plan.wheel(event)
        }
    }
    PinchHandler {
        target: null
        rotationAxis.enabled: false
        onScaleChanged: function(delta) { plan.zoomAt(delta,centroid.position.x,centroid.position.y) }
    }
    SelectionOverlay {
        id: sweep; objectName: "selectionOverlay"; anchors.fill: parent
        drawHover: false
        modules: plan.modules; objects: plan.polygons
        selectable: backend.clickKinds; anchor: backend.anchor; selectionState: backend.selectionState
        live: backend.tool==="select" && !backend.collecting && mouse.containsMouse && !plan.spaceHeld
              && plan.hotVertex<0 && plan.vertexDragIndex<0
        sweeping: mouse.swept
        // R529: Shift adds, Ctrl adds or takes away (a window with Ctrl takes away): the sign beside the pointer says it
        removing: !!(plan.pointerModifiers & Qt.ControlModifier) && !(plan.pointerModifiers & Qt.AltModifier)
        modified: !!(plan.pointerModifiers & (Qt.ShiftModifier | Qt.ControlModifier))
        kind: mouse.lasso ? mouse.sweepKind : plan.pointer.x>=mouse.start.x ? "window" : "crossing"
        ring: mouse.lasso ? mouse.trail : [mouse.start,Qt.point(plan.pointer.x,mouse.start.y),plan.pointer,Qt.point(mouse.start.x,plan.pointer.y)]
        pointer: plan.pointer
        viewScale: plan.zoom; offsetX: plan.panX; offsetY: plan.panY; viewRotation: plan.bearing
        colours: backend.planColors
    }
    ToolOverlay { anchors.fill: parent; plan: plan; preview: backend.preview; visible: backend.tool!=="select" }
    Controls.PointerSign {
        // R497: the command's icon beside the pointer on a side «Align» takes, as SelectionOverlay's + and - (R535)
        objectName: "collectBadge"
        visible: backend.collectBadge!=="" && mouse.containsMouse && !plan.spaceHeld
        pointer: plan.pointer; colours: backend.planColors
        sign: ""; iconName: backend.collectBadge || "view_align"; iconColor: plan.ink
    }
    RowHandle { plan: plan; backend: plan.backend }
    SidePills { id: sidePills; plan: plan; backend: plan.backend }
    Shape {
        id: vertexPreview; visible: plan.vertexDragIndex>=0
        preferredRendererType: Shape.CurveRenderer
        property var points: backend.grips.map(function(p,i) {
            return plan.cornerAt(i,p.x,p.y)
        })
        ShapePath { strokeColor: backend.planColors.sel; strokeWidth: 2; strokeStyle: ShapePath.DashLine; fillColor: "transparent"
            PathPolyline { path: vertexPreview.points }
            PathLine { x: vertexPreview.points.length ? vertexPreview.points[0].x : 0; y: vertexPreview.points.length ? vertexPreview.points[0].y : 0 }
        }
    }
    StringLabels { plan: plan; backend: plan.backend; avoid: sidePills.pills; visible: backend.stringsVisible }
    Repeater {
        model: backend.marks
        delegate: PlanSymbol {
            required property var modelData
            shape: modelData; name: modelData.name; count: modelData.count
            pill: true; pillColour: backend.planColors.label_bg     // R464: in a disc of the plan's pills
            fontFamily: Theme.fontFamily
            property point location: plan.screen(modelData.x,-modelData.y)
            x: location.x-width/2; y: location.y-height/2
            MouseArea {
                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onClicked: function(event) {
                    // R529: on the modules of its sub-field the click takes the module under it
                    var at=mapToItem(plan,event.x,event.y), p=plan.world(at.x,at.y)
                    plan.forceActiveFocus()
                    backend.markClick(modelData.target[0],modelData.target[1],p.x,p.y)
                }
            }
        }
    }
    // the dots are children of the plan (the tests find them there); hidden, not destroyed, outside Plant (R483)
    readonly property bool stringsShown: backend.stringsVisible
    component Dots: Repeater {
        delegate: Rectangle {
            required property var modelData
            property point location: plan.screen(modelData.x,modelData.y)
            visible: plan.stringsShown
            width: modelData.diameter; height: width; radius: width/2
            x: location.x-width/2; y: location.y-height/2
            color: modelData.colour; border.color: plan.ink
        }
    }
    Dots { model: backend.dots }
    Dots { model: backend.draftDots }
    Repeater {
        model: backend.labels.filter(function(p){return p.side===undefined && p.kind!=="name" && p.kind!=="number"})
        delegate: Rectangle {
            required property var modelData
            property point location: plan.screen(modelData.x,modelData.y)
            x: location.x-width/2+(modelData.offsetX || 0); y: location.y-height/2+(modelData.offsetY || 0)
            width: label.implicitWidth+16; height: label.implicitHeight+6
            radius: height/2; color: Theme.colors.overlay.glass
            Text { id: label; anchors.centerIn: parent; color: plan.ink; text: modelData.text
                font.family: Theme.fontFamily; font.pixelSize: Theme.text.caption.size }
            MouseArea { anchors.fill: parent; enabled: modelData.side!==undefined && backend.tool==="select"
                onClicked: backend.editSide(modelData.side) }
        }
    }
    Repeater {
        model: backend.grips
        delegate: Rectangle {
            required property var modelData
            objectName: "vertexGrip"+modelData.index
            property point location: plan.cornerAt(modelData.index,modelData.x,modelData.y)
            readonly property bool chosen: backend.chosenCorners.indexOf(modelData.index)>=0
            readonly property bool hot: chosen || plan.hotVertex===modelData.index || plan.vertexDragIndex===modelData.index
            width: hot ? 16 : 10; height: width; radius: width/2
            x: location.x-width/2; y: location.y-height/2
            color: hot ? backend.planColors.sel : "transparent"
            border.color: hot ? backend.planColors.label_bg : backend.planColors.sel; border.width: 1.6
        }
    }
    SideEditor { plan: plan; backend: plan.backend; pills: sidePills.pills }
    // R356: the measure the corners chosen move by, «East; North» or one length along the last move
    Controls.OverlayField {
        id: cornerField
        objectName: "cornersField"
        visible: false
        colours: backend.planColors
        label: backend.texts.cornersField.replace("{n}",backend.chosenCorners.length)
        sample: "0,00; 0,00"
        property point at: {
            var c=backend.chosenCorners, g=backend.grips
            return c.length && g[c[0]] ? plan.screen(g[c[0]].x,g[c[0]].y) : Qt.point(plan.width/2,plan.height/2)
        }
        x: Math.max(0,Math.min(plan.width-width,at.x+Theme.space.S))
        y: Math.max(0,Math.min(plan.height-height,at.y+Theme.space.S))
        function open(first) { visible=true; edit(first,false) }
        onAccepted: {
            if (backend.cornersTyped(text)) { visible=false; plan.forceActiveFocus() }
            else { input.forceActiveFocus(); input.selectAll() }
        }
        onCanceled: { visible=false; plan.forceActiveFocus() }
        onFocusLost: visible=false
    }
    Controls.PointerSign {
        // R529 on the corners: Shift adds one, Ctrl adds or takes it away
        objectName: "cornerSign"
        visible: plan.hotVertex>=0 && plan.vertexDragIndex<0 && !plan.spaceHeld
                 && !!(plan.pointerModifiers & (Qt.ShiftModifier|Qt.ControlModifier))
        pointer: plan.pointer; colours: backend.planColors
        sign: (plan.pointerModifiers & Qt.ControlModifier) && backend.chosenCorners.indexOf(plan.hotVertex)>=0 ? "remove" : "add"
    }
    // A side of what is selected, taken away from its corners (R473; R445 phase B): dragged, it moves parallel to
    // itself; a sub-field that is its modules shows the modules that come and go. Elsewhere the mask lets the
    // events through.
    MouseArea {
        id: sideMouse
        objectName: "sideMouse"
        anchors.fill: parent
        enabled: backend.grips.length>0 && !backend.sideEditing && !plan.spaceHeld && !backend.collecting
        hoverEnabled: true; preventStealing: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.SizeAllCursor
        property int side: -1
        property bool dragging: false
        property bool moved: false       // past the click slop once: a drag, wherever the release falls
        property point began: Qt.point(0,0)
        function sideUnder(x,y) {
            if(plan.vertexAt(x,y)>=0) return -1
            var p=plan.world(x,y)
            return backend.sideAt(p.x,p.y,1/plan.zoom)
        }
        containmentMask: QtObject {
            function contains(point: point): bool { return sideMouse.pressed || sideMouse.sideUnder(point.x,point.y)>=0 }
        }
        onPositionChanged: function(event) {
            if(!pressed) { side=sideUnder(event.x,event.y); return }
            if(dragging) {
                plan.pointer=Qt.point(event.x,event.y)
                if(Math.hypot(event.x-began.x,event.y-began.y)>plan.clickSlop) moved=true
                var p=plan.world(event.x,event.y)
                backend.dragSide(p.x,p.y,plan.mods(event.modifiers))
            }
        }
        onExited: if(!pressed) side=-1
        onPressed: function(event) {
            if(event.modifiers & (Qt.ShiftModifier|Qt.ControlModifier)) { event.accepted=false; return }
            var index=sideUnder(event.x,event.y)
            if(index<0) { event.accepted=false; return }
            plan.forceActiveFocus(); plan.pointer=Qt.point(event.x,event.y)
            backend.pointerScale(1/plan.zoom,plan.bearing)
            began=plan.pointer; side=index; dragging=true; moved=false
            var p=plan.world(event.x,event.y)
            backend.beginSide(index,p.x,p.y)
        }
        onReleased: function(event) {
            if(!dragging) return
            dragging=false
            var p=plan.world(event.x,event.y)
            if(moved || backend.sideTyped() || Math.hypot(event.x-began.x,event.y-began.y)>plan.clickSlop)
                backend.endSide(p.x,p.y,plan.mods(event.modifiers))
            else {
                // a click on a side moves nothing; it is a click on what lies there, as anywhere else (R529: the
                // modules along the outline of a selected sub-field could not be taken)
                backend.cancelSideDrag()
                if(!backend.sideEditing) { var q=plan.world(began.x,began.y); backend.click(q.x,q.y,0) }
            }
            side=sideUnder(event.x,event.y)
        }
    }
    // One area for all the corners, over the pills, the marks and the plan under them: near a corner of what is selected
    // the corner wins, the nearest of two (R427); everywhere else the mask lets the events through.
    MouseArea {
        id: vertexMouse
        objectName: "vertexMouse"
        anchors.fill: parent
        enabled: backend.grips.length>0 && !backend.sideEditing && !plan.spaceHeld && !backend.collecting
        hoverEnabled: true; preventStealing: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.SizeAllCursor
        containmentMask: QtObject {
            function contains(point: point): bool { return vertexMouse.pressed || plan.vertexAt(point.x,point.y)>=0 }
        }
        property point began: Qt.point(0,0)
        property int pressMods: 0
        property var pressChosen: []
        function follow(x,y) {
            plan.pointer=Qt.point(x,y)
            if(!pressed) plan.hotVertex=plan.vertexAt(x,y)
        }
        onEntered: follow(mouseX,mouseY)
        onPositionChanged: function(event) {
            if(!pressed) { follow(event.x,event.y); return }
            plan.pointer=Qt.point(event.x,event.y)
            if(plan.vertexDragIndex>=0) {
                var p=plan.world(event.x,event.y)
                plan.vertexDragPoint=backend.snapCorner(plan.vertexDragIndex,p.x,p.y,plan.mods(event.modifiers),1/plan.zoom)
            }
        }
        onExited: if(!pressed) plan.hotVertex=-1
        onPressed: function(event) {
            var index=plan.vertexAt(event.x,event.y)
            if(index<0) { event.accepted=false; return }
            plan.forceActiveFocus(); plan.pointer=Qt.point(event.x,event.y)
            backend.pointerScale(1/plan.zoom,plan.bearing)
            began=plan.pointer
            // R356, R529: Shift or Ctrl with a click choose corners; a drag of a corner chosen moves them all
            pressMods=plan.mods(event.modifiers) & 3
            pressChosen=backend.chosenCorners.slice()
            plan.cornerGroup=pressChosen.length>1 && pressChosen.indexOf(index)>=0
            var grip=backend.grips[index]
            plan.hotVertex=index; plan.vertexDragIndex=index
            plan.vertexDragPoint=Qt.point(grip.x,grip.y)
        }
        onReleased: function(event) {
            var index=plan.vertexDragIndex
            plan.vertexDragIndex=-1
            // A click on a corner changes nothing: the snap must not move it.
            var group=plan.cornerGroup
            plan.cornerGroup=false
            if(index>=0 && Math.hypot(event.x-began.x,event.y-began.y)>plan.clickSlop) {
                var p=plan.world(event.x,event.y)
                var snapped=backend.snapCorner(index,p.x,p.y,plan.mods(event.modifiers),1/plan.zoom)
                var grip=backend.grips[index]
                if(group) backend.moveCorners(snapped.x-grip.x,snapped.y-grip.y)
                else { backend.chooseCorner(index,0); backend.vertex(index,snapped.x,snapped.y) }
            } else if(index>=0 && pressMods) {
                backend.chooseCorner(index,pressMods)
            } else if(index>=0 && !backend.chooseCorner(index,0)) {
                // R529: a second click on the corner chosen is a click on what lies there (the module in the corner)
                var q=plan.world(began.x,began.y)
                backend.click(q.x,q.y,0)
            }
            plan.hotVertex=plan.vertexAt(event.x,event.y)
        }
    }
    Repeater {
        model: 2
        delegate: Rectangle {
            required property int index
            property var modelData: backend.transformGrips[index] || {x:0,y:0,grip:"",hot:false,free:false}
            visible: modelData.grip!=="" && !backend.collecting     // R505: choosing a side, only the sides
            onVisibleChanged: if(!visible) plan.localHint=""
            property point location: plan.screen(modelData.x,modelData.y)
            width: Theme.size.COMPACT; height: width; radius: width/2
            x: location.x-width/2; y: location.y-height/2
            color: modelData.hot || gripMouse.containsMouse ? backend.planColors.sel : backend.planColors.label_bg
            border.color: backend.planColors.sel; border.width: 2
            Controls.Icon {
                anchors.centerIn: parent; name: modelData.grip
                color: modelData.hot || gripMouse.containsMouse ? backend.planColors.label_bg : plan.ink
                width: parent.width-2*Theme.space.XS; height: width
            }
            MouseArea {
                id: gripMouse
                objectName: "transformGripMouse"+modelData.grip
                anchors.fill: parent; hoverEnabled: true; preventStealing: true
                anchors.margins: -Theme.space.XXS
                containmentMask: QtObject {
                    function contains(point: point): bool {
                        var r=gripMouse.width/2, dx=point.x-r, dy=point.y-r
                        return dx*dx+dy*dy<=r*r
                    }
                }
                enabled: modelData.free || pressed
                onEnabledChanged: if(!enabled) plan.localHint=""     // no exit comes from an area switched off
                property string cursorKind: modelData.grip
                onCursorKindChanged: backend.setGripCursor(gripMouse,cursorKind)
                Component.onCompleted: backend.setGripCursor(gripMouse,cursorKind)
                property point began: Qt.point(0,0)
                onEntered: plan.localHint=modelData.grip==="move" ? backend.texts.gripMove : backend.texts.gripRotate
                onExited: plan.localHint=""
                onPressed: function(event) {
                    began=mapToItem(plan,event.x,event.y); plan.forceActiveFocus()
                    backend.startGrip(modelData.grip,modelData.x,modelData.y)
                }
                onPositionChanged: function(event) {
                    if (!pressed) return
                    var pos=mapToItem(plan,event.x,event.y), p=plan.world(pos.x,pos.y)
                    backend.pointer(p.x,p.y,plan.mods(event.modifiers),1/plan.zoom)
                }
                onReleased: function(event) {
                    var pos=mapToItem(plan,event.x,event.y), p=plan.world(pos.x,pos.y)
                    if (Math.hypot(pos.x-began.x,pos.y-began.y)>4) backend.click(p.x,p.y,plan.mods(event.modifiers))
                }
            }
            Controls.ToolTip {
                visible: gripMouse.containsMouse && !gripMouse.pressed
                text: modelData.grip==="move" ? backend.texts.gripMove : backend.texts.gripRotate
            }
        }
    }
    // R425: the words of the module under the pointer, at the pointer, changing as soon as it passes to the next.
    Controls.ToolTip {
        id: moduleTip
        objectName: "moduleTip"
        readonly property var record: sweep.hovered && sweep.hovered.record && sweep.hovered.record.kind==="module" ? sweep.hovered.record : null
        readonly property int revision: backend.moduleTipsRevision !== undefined ? backend.moduleTipsRevision : 0
        text: { const r=revision; return record && backend.moduleTip ? backend.moduleTip(record.oid,record.key) : "" }
        visible: text!=="" && mouse.containsMouse && !mouse.pressed && !mouse.swept
        placed: true
        shownAt: plan.pointer           // R550: beside it as every tooltip (ControlMetrics.besidePointer)
    }
    PlanLegend {
        objectName: "optimizerLegend"
        visible: backend.optimizerPaths !== undefined && backend.optimizerPaths.length>0
        x: Theme.space.M; y: plan.height-height-Theme.space.XXXL-Theme.space.L
        words: backend.optimizerLegendWords || []
    }
    Compass {
        id: compass
        objectName: "compass"
        function place() {
            var left=plan.width-width-Theme.space.M
            var lower=plan.toolbarBounds.width>0 && plan.toolbarBounds.x+plan.toolbarBounds.width+Theme.space.M>left
            placeAt(left,lower?plan.toolbarBounds.y+plan.toolbarBounds.height+Theme.space.M:Theme.space.M,lower)
        }
        Component.onCompleted: place()
        Connections { target:plan
            function onWidthChanged() {compass.place()}
            function onToolbarBoundsChanged() {compass.place()} }
        angle: plan.bearing; points: backend.compassPoints
        tooltipText: backend.compassText.replace("{heading}",headingText)+(Math.round(bearing*10)%3600!==0 ? "\n"+backend.texts.northClick : "")
        ink: plan.ink
        onNorth: plan.rotateView(-plan.bearing)
        onRotate: function(degrees) { plan.rotateView(degrees) }
    }
    ScaleBar {
        id: scaleBar
        objectName: "scaleBar"
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: Theme.space.M
        metresPerPixel: 1/plan.zoom; ink: plan.ink; ground: backend.planColors.label_bg
        visible: backend.maps===null || !backend.maps.equalEarth
    }
    // R552 (Daniel 08/11/2026: «questa scritta si nasconde dietro i pannelli»): the credit of the background stands
    // with the scale, the compass and the bars above the project's drawing, on a full dark ground; it was in MapLayer,
    // under the drawing, and the modules passed over it and through its half-clear ground
    Rectangle {
        id: credit
        objectName: "mapCredit"
        readonly property var maps: backend.maps
        visible: maps !== null && attribution.text.length > 0
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.space.M
        width: Math.min(Math.max(40,plan.width-120-2*Theme.space.M-Theme.space.S-40-5*Theme.space.M), attribution.implicitWidth)+2*Theme.space.M
        height: Theme.size.CONTROL
        radius: Theme.radius.CONTROL
        color: Theme.colors.overlay.glass_solid
        Text {
            id: attribution
            anchors.fill: parent
            anchors.leftMargin: Theme.space.M; anchors.rightMargin: Theme.space.M
            // R516: while the area of the project is kept for the plan without network, its progress after the credit
            text: credit.maps ? credit.maps.attribution + (credit.maps.offlineText ? "  ·  " + credit.maps.offlineText : "") : ""
            elide: Text.ElideMiddle; verticalAlignment: Text.AlignVCenter
            font.family: Theme.fontFamily
            font.pixelSize: Theme.text.secondary.size
            color: Theme.colors.overlay.ink
        }
    }
    // R484: where the pointer is, by the scale (it was in the status bar, where its width changed at every step and
    // moved the rest): a pill of the plan's pills, the digits of one width (Plex's tabular figures) and the pill as
    // wide as the longest of the plan's coordinates, so that nothing moves; only while the pointer is on the plan.
    // R511: in the pill of the scale (ViewPill), its height, radius, ground, margins and type.
    Controls.Pill {
        id: cursorPill
        variant: "view"
        objectName: "planCursor"
        visible: plan.cursorText !== ""
        anchors.bottom: parent.bottom; anchors.bottomMargin: Theme.space.M
        x: scaleBar.visible ? scaleBar.x + scaleBar.width + Theme.space.S : Theme.space.M
        width: Math.ceil(Math.max(cursorWords.implicitWidth, cursorLongest.advanceWidth(plan.cursorLongest))) + 2 * pad
        ground: backend.planColors.label_bg; ink: plan.ink
        FontMetrics { id: cursorLongest; font: cursorWords.font }
        Text {
            id: cursorWords; objectName: "planCursorText"
            x: cursorPill.pad; height: parent.height; verticalAlignment: Text.AlignVCenter
            text: plan.cursorText; color: cursorPill.ink
            font: cursorPill.font
        }
    }
    ViewBar {
        id: viewbar; objectName: "planViewBar"
        x: Theme.space.M; y: Theme.space.M
        plan: plan; backend: plan.backend; viewMode: plan.viewMode; backgroundMenu: backgroundMenu
        onWidthChanged: plan.toolbarBounds=Qt.rect(x,y,width,height)
        onHeightChanged: plan.toolbarBounds=Qt.rect(x,y,width,height)
        Component.onCompleted: plan.toolbarBounds=Qt.rect(x,y,width,height)
        onBackgroundRequested: backgroundMenu.popup(x,y+height)
    }
    MapNotice {
        maps: backend.maps
        x: Theme.space.M; y: plan.toolbarBounds.y + plan.toolbarBounds.height + Theme.space.S
        rightLimit: compass.x - Theme.space.S
        chooseText: backend.texts.chooseBackground; closeText: backend.texts.closeWindow
        onChooseBackground: backgroundMenu.popup(viewbar.x, viewbar.y + viewbar.height)
    }
    Controls.Menu {
        // ui/window.py, _fill_sources: Automatic | photos | maps | None | other sources, veil | images
        id: backgroundMenu; objectName: "backgroundMenu"; title: backend.texts.background
        onAboutToShow: backend.refreshMapChoices()
        function sourceChecked(key) { return backend.mapChoices.checked===key }
        function indexAfter(item) { for (let i=0;i<count;i++) if (itemAt(i)===item) return i+1; return count }
        Controls.MenuItem { objectName: "backgroundAutomatic"; text: backend.mapChoices.automatic.text; tip: backend.mapChoices.automatic.tip; checkable: true
            checked: backgroundMenu.sourceChecked(backend.mapChoices.automatic.key); onTriggered: backend.chooseMapOptions({source:backend.mapChoices.automatic.key}) }
        Controls.MenuSeparator { id: photosRule }
        Instantiator {
            model: backend.mapChoices.photos
            delegate: Controls.MenuItem {
                required property var modelData
                text: modelData.text; tip: modelData.tip; checkable: true
                checked: backgroundMenu.sourceChecked(modelData.key)
                onTriggered: backend.chooseMapOptions({source:modelData.key})
            }
            onObjectAdded: function(index, object) { backgroundMenu.insertItem(backgroundMenu.indexAfter(photosRule)+index, object) }
            onObjectRemoved: function(index, object) { backgroundMenu.removeItem(object) }
        }
        Controls.MenuSeparator { id: mapsRule; visible: backend.mapChoices.photos.length>0; height: visible ? implicitHeight : 0 }
        Instantiator {
            model: backend.mapChoices.maps
            delegate: Controls.MenuItem {
                required property var modelData
                text: modelData.text; tip: modelData.tip; checkable: true
                checked: backgroundMenu.sourceChecked(modelData.key)
                onTriggered: backend.chooseMapOptions({source:modelData.key})
            }
            onObjectAdded: function(index, object) { backgroundMenu.insertItem(backgroundMenu.indexAfter(mapsRule)+index, object) }
            onObjectRemoved: function(index, object) { backgroundMenu.removeItem(object) }
        }
        Controls.MenuSeparator { visible: backend.mapChoices.maps.length>0; height: visible ? implicitHeight : 0 }
        Controls.MenuItem { text: backend.mapChoices.none.text; tip: backend.mapChoices.none.tip; checkable: true
            checked: backgroundMenu.sourceChecked(backend.mapChoices.none.key); onTriggered: backend.chooseMapOptions({source:backend.mapChoices.none.key}) }
        Controls.MenuSeparator {}
        Controls.MenuItem { objectName: "backgroundOtherSources"; text: backend.texts.otherSources; tip: backend.texts.otherSourcesTip; onTriggered: backend.preferencesRequested("maps") }
        Controls.Menu {
            id: veilMenu; title: backend.texts.darken
            Instantiator {
                model: backend.veilChoices
                delegate: Controls.MenuItem {
                    required property var modelData
                    text: modelData.text; checkable: true
                    checked: backend.maps!==null && Math.abs(backend.maps.veil-modelData.value)<.01
                    onTriggered: backend.chooseMapOptions({veil:modelData.value})
                }
                onObjectAdded: function(index, object) { veilMenu.insertItem(index, object) }
                onObjectRemoved: function(index, object) { veilMenu.removeItem(object) }
            }
        }
        Controls.MenuSeparator {}
        Controls.MenuItem { text: backend.texts.importImage; tip: backend.texts.importImageTip; onTriggered: importImage.open() }
        Instantiator {
            model: backend.underlays.images
            delegate: UnderlayMenu {
                required property var modelData
                backend: plan.backend.underlays; imageData: modelData
            }
            onObjectAdded: function(index, object) { backgroundMenu.addMenu(object) }
            onObjectRemoved: function(index, object) { backgroundMenu.removeMenu(object) }
        }
    }
    NativeDialogs.FileDialog {
        id: importImage; title: backend.underlays.texts.importImage
        nameFilters: [backend.underlays.texts.filter]
        onAccepted: {
            var corners=[plan.world(0,0),plan.world(plan.width,0),plan.world(0,plan.height),plan.world(plan.width,plan.height)]
            var xs=corners.map(p=>p.x),c=plan.world(plan.width/2,plan.height/2)
            backend.underlays.importImage(selectedFile,c.x,c.y,.8*(Math.max(...xs)-Math.min(...xs)))
        }
    }
    Connections {
        target: backend.underlays
        function onPrompt(title, label) {
            imageValueDialog.title=title; imageValueLabel.text=label; imageValue.text=""; imageValueDialog.open()
        }
    }
    // R518: the buttons are the window's, as in every other
    Controls.Dialog {
        id: imageValueDialog; objectName: "imageValueDialog"; anchors.centerIn: parent
        acceptText: backend.texts.apply; rejectText: backend.texts.cancel
        acceptCheck: () => backend.underlays.accept(imageValue.text)
        Column {
            width: parent.width; spacing: Theme.space.S
            Controls.Label { id: imageValueLabel; width: parent.width; wrapMode: Text.Wrap }
            Controls.TextField { id: imageValue; width: parent.width
                onAccepted: imageValueDialog.tryAccept() }
        }
        onOpened: imageValue.forceActiveFocus()
        onClosed: plan.forceActiveFocus()
    }
    Controls.Menu {
        id: menu
        objectName: "planContextMenu"
        // R533: what the menu acts on at the top, under muted titles; the levels above it (sub-field, roof) and the
        // point's coordinates in submenus, from the field «menu» of each entry
        Component {
            id: contextEntry
            Controls.MenuItem {
                required property var modelData
                objectName: modelData.header ? "planContextTitle" : "planContext-"+modelData.command
                text: modelData.text
                enabled: modelData.enabled
                height: modelData.separator && !modelData.header ? 9 : implicitHeight
                topPadding: modelData.header ? Theme.space.XS : modelData.separator ? 4 : Theme.space.S
                bottomPadding: modelData.header ? Theme.space.XXS : modelData.separator ? 4 : Theme.space.S
                leftPadding: Theme.space.M
                contentItem: Loader {
                    sourceComponent: modelData.header ? menuTitle : modelData.separator ? separatorLine : menuLabel
                    Component { id: separatorLine; Rectangle { height: 1; color: Theme.colors.line } }
                    Component { id: menuTitle; Text {
                        text: modelData.text; color: Theme.colors.muted
                        font.family: Theme.fontFamily; font.pixelSize: Theme.text.caption.size; font.bold: true
                        verticalAlignment: Text.AlignVCenter
                    } }
                    Component { id: menuLabel; Text {
                        text: modelData.text; color: modelData.enabled ? Theme.colors.text : Theme.colors.muted
                        font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
                        verticalAlignment: Text.AlignVCenter
                    } }
                }
                onTriggered: plan.runContext(modelData.command)
            }
        }
        Instantiator {
            model: backend.contextItems.filter(function(e){ return !e.menu })
            delegate: contextEntry
            onObjectAdded: function(index, object) { menu.insertItem(index, object) }
            onObjectRemoved: function(index, object) { menu.removeItem(object) }
        }
        Instantiator {
            model: backend.contextItems.reduce(function(titles,e){
                if(e.menu && titles.indexOf(e.menu)<0) titles.push(e.menu); return titles },[])
            delegate: Controls.Menu {
                id: contextSub
                required property var modelData
                objectName: "planContextMenu-"+modelData
                title: modelData
                Instantiator {
                    model: backend.contextItems.filter(function(e){ return e.menu===contextSub.modelData })
                    delegate: contextEntry
                    onObjectAdded: function(index, object) { contextSub.insertItem(index, object) }
                    onObjectRemoved: function(index, object) { contextSub.removeItem(object) }
                }
            }
            onObjectAdded: function(index, object) { menu.addMenu(object) }
            onObjectRemoved: function(index, object) { menu.removeMenu(object) }
        }
        onClosed: plan.forceActiveFocus()
    }
    Controls.Dialog {
        id: renameDialog; title:backend.texts.rename; anchors.centerIn:parent
        acceptText: "OK"; rejectText: backend.texts.cancel
        Controls.TextField { id:renameField; width:parent.width; selectByMouse:true
            onAccepted:renameDialog.accept() }
        onOpened: {renameField.forceActiveFocus();renameField.selectAll()}
        onAccepted:backend.rename(renameField.text)
        onClosed:plan.forceActiveFocus()
    }
    Connections {
        target: backend
        function onRelayoutRequested(title, message) {
            relayoutDialog.title=title; relayoutMessage.text=message; relayoutDialog.open()
        }
    }
    Controls.Dialog {
        id: relayoutDialog; objectName: "relayoutConfirmation"
        anchors.centerIn: parent; width: Math.min(440,plan.width-32)
        acceptText: backend.texts.yes; rejectText: backend.texts.no          // R518: the window's buttons
        contentItem: Controls.Label { id: relayoutMessage; wrapMode: Text.Wrap }
        onAccepted: backend.confirmRelayout(true)
        onRejected: backend.confirmRelayout(false)
        onClosed: plan.forceActiveFocus()
    }
    // R454: placing an imported IFC model, the question when it falls on a building and the window of its coordinates
    Connections {
        target: backend
        function onPlaceAsked(title, message) {
            overlapDialog.title=title; overlapMessage.text=message; overlapDialog.answer=""; overlapDialog.open()
        }
        function onCoordinatesAsked() { coordinatesDialog.load(); coordinatesDialog.open() }
    }
    Controls.Dialog {
        id: overlapDialog; objectName: "placeOverlap"
        property string answer: ""
        anchors.centerIn: parent; width: Math.min(520,plan.width-32)
        function choose(value) { answer=value; close() }
        Column {
            width: parent.width; spacing: Theme.space.M
            Text { id: overlapMessage; width: parent.width; wrapMode: Text.Wrap
                font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size; color: Theme.colors.text }
            Flow { width: parent.width; spacing: Theme.space.S
                Controls.Button { objectName: "placeReplace"; text: backend.placing.texts ? backend.placing.texts.replace : ""
                    onClicked: overlapDialog.choose("replace") }
                Controls.Button { objectName: "placeKeep"; text: backend.placing.texts ? backend.placing.texts.keep : ""
                    onClicked: overlapDialog.choose("keep") }
                Controls.Button { objectName: "placeBeside"; text: backend.placing.texts ? backend.placing.texts.beside : ""
                    onClicked: overlapDialog.choose("beside") }
                Controls.Button { objectName: "placeBack"; text: backend.placing.texts ? backend.placing.texts.back : ""
                    onClicked: overlapDialog.choose("back") }
            }
        }
        onClosed: { backend.placeAnswer(answer || "back"); plan.forceActiveFocus() }
    }
    Controls.Dialog {
        id: coordinatesDialog; objectName: "placeCoordinates"
        anchors.centerIn: parent; width: Math.min(560,plan.width-32)
        title: backend.placing.texts ? backend.placing.texts.title : ""
        property var info: backend.placing
        property string system: "utm"
        property var check: ({ok: true, text: "", warning: false})
        function labels() { return info.labels ? info.labels[system] : ["", ""] }
        function fill(values) {
            if (!values) return
            coordA.text=values.a; coordB.text=values.b; coordTurn.text=values.turn; refresh()
        }
        function load() {
            var offer=info.proposal
            system=offer ? offer.system : "local"
            systemBox.currentIndex=Math.max(0,(info.systems || []).findIndex(function(s){ return s.value===system }))
            fill(offer || info.values[system])
        }
        function refresh() { check=backend.checkCoordinates(system,coordA.text,coordB.text,coordTurn.text) }
        Column {
            width: parent.width; spacing: Theme.space.M
            Controls.ComboBox { id: systemBox; objectName: "placeSystem"; width: parent.width
                model: coordinatesDialog.info.systems || []; textRole: "text"; valueRole: "value"
                onActivated: { coordinatesDialog.system=currentValue; coordinatesDialog.fill(coordinatesDialog.info.values[currentValue]) }
            }
            Grid { columns: 2; columnSpacing: Theme.space.M; rowSpacing: Theme.space.S; width: parent.width
                verticalItemAlignment: Grid.AlignVCenter
                Controls.Label { text: coordinatesDialog.labels()[0] }
                Controls.TextField { id: coordA; objectName: "placeA"; width: 200; selectByMouse: true; onTextEdited: coordinatesDialog.refresh() }
                Controls.Label { text: coordinatesDialog.labels()[1] }
                Controls.TextField { id: coordB; objectName: "placeB"; width: 200; selectByMouse: true; onTextEdited: coordinatesDialog.refresh() }
                Controls.Label { text: coordinatesDialog.info.texts ? coordinatesDialog.info.texts.turn : ""; width: parent.width - 200 - Theme.space.M
                    wrapMode: Text.Wrap }
                Controls.TextField { id: coordTurn; objectName: "placeTurn"; width: 200; selectByMouse: true; onTextEdited: coordinatesDialog.refresh() }
            }
            Controls.Label { width: parent.width; wrapMode: Text.Wrap; textStyle: "caption"
                text: coordinatesDialog.info.texts ? coordinatesDialog.info.texts.point : "" }
            Controls.Label { objectName: "placeCheck"; width: parent.width; wrapMode: Text.Wrap
                text: coordinatesDialog.check.text
                color: coordinatesDialog.check.warning ? Theme.colors.danger : Theme.colors.text }
            Flow { width: parent.width; spacing: Theme.space.S
                Controls.Button { objectName: "placeThere"; text: coordinatesDialog.info.texts ? coordinatesDialog.info.texts.place : ""
                    enabled: coordinatesDialog.check.ok
                    onClicked: if (backend.placeCoordinates(coordinatesDialog.system,coordA.text,coordB.text,coordTurn.text)) coordinatesDialog.close() }
                Controls.Button { objectName: "placeUseFile"; visible: !!coordinatesDialog.info.proposal
                    text: coordinatesDialog.info.proposal ? coordinatesDialog.info.texts.useFile + ": " + coordinatesDialog.info.proposal.text : ""
                    onClicked: coordinatesDialog.load() }
                Controls.Button { text: coordinatesDialog.info.texts ? coordinatesDialog.info.texts.cancel : ""; onClicked: coordinatesDialog.close() }
            }
        }
        onClosed: plan.forceActiveFocus()
    }
    Controls.Dialog {
        id:sourcesDialog; title:backend.texts.sources; anchors.centerIn:parent
        width:Math.min(920,plan.width-40);height:Math.min(800,plan.height-40)
        rejectText: backend.texts.closeWindow
        // R518: «Applica» on the window's row of buttons, the window stays open
        acceptText: sourcesPage.item && sourcesPage.item.showApply ? sourcesPage.item.words.apply : ""
        acceptOnReturn: false
        acceptCheck: () => { sourcesPage.item.backend.apply(); return false }
        Loader { id: sourcesPage; anchors.fill:parent; active: sourcesDialog.opened && backend.sourceEditor!==null
            sourceComponent:MapSources { backend:plan.backend.sourceEditor; embedded: true } }
        onClosed:plan.forceActiveFocus()
    }
}
