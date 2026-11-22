import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Dialogs as NativeDialogs
import Meridiana.Theme
import Meridiana.Controls as Controls
import Meridiana.Measure as Measure
import Meridiana.Plan.Paths 1.0
import "Navigation.js" as Navigation
Rectangle {
    id: plan
    objectName: "plan"
    required property var backend
    // the sun map of the window (backend/plan_map.py), null where there is none (a plan alone, PlanWindow)
    property var sun: null
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
    // R609: with Measure in hand the numbers the drawing does not write (along the slope, height difference, slope,
    // direction, the path's total) come first, once the pointer rests (gui/backend/measure.py `numbers`)
    readonly property string measureNumbers: backend.tool === "measure" && backend.measure ? backend.measure.numbers : ""
    readonly property string statusText: backend.error || localHint
                                         || (measureNumbers ? measureNumbers + " · " + backend.hint : backend.hint)
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
    property bool markHovered: false        // R641: a check's mark under the pointer says its words, not the module's
    color: backend.planColors.bg
    clip: true
    focus: true
    // R577, R616: the bars, the compass, the scale, the pointer's coordinates, the credit and the notices lie over the
    // drawing and over every label of it: each of them at Theme.stack.VIEW_BAR, the strings' names at LABEL, the side
    // highlighted at MARK (design.Stack). The coordinates had none, and the strings' names passed over them (R616).
    // R555 (1), D4, D5 (Daniel 08/11/2026 and Linux 14/11/2026: the words of the sun map behind its legend, under the
    // compass and the bar; the pointer's coordinates under the credit): what is written over the plan is one family
    // with one rule. The chrome (the view bar, the compass, the map's notice, the legends, the scale, the pointer's
    // coordinates, the credit) has a place each and never moves for the drawing; in the bottom row the credit gives
    // way, cut in its middle, to the scale and the coordinates beside it, whose room it keeps even while the pointer is
    // away. A label tied to a place of the drawing (the sun map's words, the plan's labels) gives way to the chrome: it
    // is not drawn while it would touch one of them (clearOfChrome).
    readonly property var chrome: [viewbar, compass, mapNotice, optimizerLegend, sunOverlay.legend, scaleBar, cursorPill, credit]
    // the chrome's boxes in the plan's coordinates, read once for every label (each label read the 8 items and mapped
    // them: 53-67 us a check against 5-9 us, off screen, 14/11/2026): a key in words, which tells only when a box truly
    // moved, grew, shrank, showed or hid (a string bound again to the same words tells nothing: checked), and the boxes
    // made of it. The chrome stands on the plan, or on an overlay over it (the sun map's legend).
    readonly property string chromeKey: {
        const out = []
        for (const c of chrome) {
            if (!c || !c.visible) continue
            const p = c.parent, dx = p && p !== plan ? p.x : 0, dy = p && p !== plan ? p.y : 0
            out.push([c.x + dx, c.y + dy, c.width, c.height].join(","))
        }
        return out.join(";")
    }
    readonly property var chromeBoxes: chromeKey === "" ? [] : chromeKey.split(";").map(box => box.split(",").map(Number))
    function clearOfChrome(x, y, w, h) {
        const air = Theme.space.XS
        for (const b of chromeBoxes)
            if (x < b[0] + b[2] + air && x + w > b[0] - air && y < b[1] + b[3] + air && y + h > b[1] - air) return false
        return true
    }
    ViewCorners { anchors.fill: parent; z: Theme.stack.VIEW_FRAME }
    function world(x, y) {
        // the camera in hand, not the one the geometry was last drawn at (worldLayer follows renderCamera)
        var a=bearing*Math.PI/180, c=Math.cos(a), s=Math.sin(a), u=(x-panX)/zoom, v=(y-panY)/zoom
        return Qt.point(u*c+v*s, u*s-v*c)
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
        pendingMotion=null
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
        zoomBy(factor,x,y)
        applyMotion()
    }
    // Accumulate device events against the latest goal, preserving each event's anchor. The frame applies the goal
    // once: several touchpad updates before a refresh must not repeat the complete camera binding graph.
    property var pendingMotion: null
    function motionGoal() {
        return pendingMotion || {x:panX,y:panY,zoom:zoom}
    }
    function panBy(dx, dy) {
        fitted=false
        const goal=motionGoal()
        pendingMotion={x:goal.x+dx,y:goal.y+dy,zoom:goal.zoom}
    }
    function zoomBy(factor, x, y) {
        fitted=false
        const goal=motionGoal(), next=Math.max(.00002,Math.min(5000,goal.zoom*factor)), ratio=next/goal.zoom
        pendingMotion={x:x+(goal.x-x)*ratio,y:y+(goal.y-y)*ratio,zoom:next}
    }
    function applyMotion() {
        const goal=pendingMotion
        if (!goal) return
        pendingMotion=null
        applyingMotion=true
        zoom=goal.zoom; panX=goal.x; panY=goal.y
        applyingMotion=false
        followMotion()
    }
    // R706: the geometry (map, outlines, modules, strings) is drawn at `renderCamera` into one retained image,
    // which is moved and scaled to the camera in hand at every frame: a step of the fingers costs a quad, not the
    // curves of every module. It is drawn again at the camera in hand as soon as it would be stretched by more
    // than `motionStretch`, or would no longer cover the view, and once the hand rests: lines stay sharp along the
    // whole travel. Until then (R702) the image was a second texture taken when the gesture began and stretched up
    // to four times (the drawing lost its resolution while zooming), and the geometry's own layer was switched
    // off and on around every gesture, which built all its batches again each time (blocks of 100-350 ms).
    readonly property bool retained: GraphicsInfo.api !== GraphicsInfo.Software
    property bool motionActive: false
    property bool gestured: false
    property bool applyingMotion: false
    property var renderCamera: ({x:0,y:0,zoom:1})
    readonly property real motionRatio: zoom/renderCamera.zoom
    // R706: Python's collector waits while the view moves and a moment after (a whole collection is 125-165 ms of
    // the window with 10 000 modules, and fell where it happened to)
    onMotionActiveChanged: { backend.viewMoving(motionActive); if (motionActive) restCollect.stop(); else restCollect.restart() }
    // The engine's own collector likewise. What the QML reads again from the backend is handed to its JavaScript
    // memory as copies to be collected later, and the collection it decides by itself fell where it happened to:
    // 0.4-0.7 s of the window in the middle of a zoom with 10 000 modules (its native stack, sampled as it stalled).
    // Made here, two seconds after the view has come to rest, it leaves little for that one (0.2-0.3 s measured
    // instead) at the price of a stop at rest: 0.13 s with 2000 modules, 0.26 s with 10 000.
    Timer { id: restCollect; interval: backend.movingRest; onTriggered: if (!plan.motionActive) gc() }
    // R707 (study 55): the levels of detail. A module's shorter side on screen, at the scale the geometry is drawn
    // at: what comes and goes with the scale is decided at each redraw, during the gesture, not when it settles.
    // The thresholds are the backend's (app/view/plan_levels), in one place.
    readonly property var levels: backend.levels
    readonly property real modulePixels: backend.moduleSize>0 ? backend.moduleSize*renderCamera.zoom : 1e6
    // R707 (study 55, 3.4): the corners of what is selected show while its shorter side on screen is at least
    // levels.vertexSide (below it a corner cannot be taken: they were a heap of points over an object of twenty
    // pixels), the measures of its sides while its longer side is at least levels.measureSide, and never at the
    // scales where the site is a few buildings. Lines keep their width at every scale, as before.
    readonly property var gripSpan: {       // shorter and longer side of what the corners enclose, in metres
        var g=backend.grips
        if(g.length<3) return [Infinity, Infinity]
        var x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity
        for(var i=0;i<g.length;++i) { x0=Math.min(x0,g[i].x); x1=Math.max(x1,g[i].x); y0=Math.min(y0,g[i].y); y1=Math.max(y1,g[i].y) }
        return [Math.min(x1-x0,y1-y0), Math.max(x1-x0,y1-y0)]
    }
    readonly property bool cornersShown: gripSpan[0]*zoom>=levels.vertexSide
    // R714: the checks' marks one by one fade out from levels.marks down to levels.building, and go with the drawing
    readonly property real checkMarksShown: seen(levels.building, levels.marks)*(1-siteMark.shown)
    readonly property bool measuresShown: gripSpan[1]*zoom>=levels.measureSide && modulePixels>=levels.building
    // how much of something shows that fades from `full` pixels down to `gone`
    function seen(gone, full) { return Math.max(0, Math.min(1, (modulePixels-gone)/(full-gone))) }
    readonly property real motionMargin: 192
    // R37 (Daniel 21/11/2026, the panels' edges dragged): the geometry's image is as large as the view rounded up to
    // 256 px, so a view a few pixels wider or narrower moves the image already drawn instead of drawing a new one of
    // another size at every pixel (25-30 ms a step with 2000 modules)
    readonly property real imageWidth: Math.ceil(Math.max(1, width)/256)*256
    readonly property real imageHeight: Math.ceil(Math.max(1, height)/256)*256
    readonly property real motionStretch: 1.3
    readonly property int motionRest: Theme.motion.REST      // a wait, not a movement: kept with less motion
    property int geometryDraws: 0
    function drawGeometry() {
        if (renderCamera.x===panX && renderCamera.y===panY && renderCamera.zoom===zoom) return
        renderCamera={x:panX,y:panY,zoom:zoom}
        geometryDraws+=1
    }
    // The lines of the modules and of the strings are pens in metres, as wide on screen as they should be at
    // `strokeZoom` (ViewPath.worldScale): drawing them at another scale builds nothing. Building them again
    // costs a frame or two for 2000 modules, so it is done in steps: while the hand moves, once the lines would
    // be twice as thick or as thin as they should (then for a view a little further on, to last longer); once
    // the hand rests, if they are more than a sixth off; never while the last ones are still being built.
    property real strokeZoom: 1
    readonly property real strokeStep: 2
    function followStrokes(resting) {
        const r=zoom/strokeZoom
        if (resting ? (r<1.16 && r>1/1.16) : (r<strokeStep && r>1/strokeStep)) return true
        if (!geometry.ready) return false
        strokeZoom=resting ? zoom : r>1 ? zoom*1.3 : zoom/1.3
        return true
    }
    Timer { id: strokeRest; interval: plan.motionRest; onTriggered: if (!plan.motionActive && !plan.followStrokes(true)) restart() }
    function followMotion() {
        if (!retained) return
        const r=motionRatio, m=motionMargin, left=panX-r*(renderCamera.x+m), top=panY-r*(renderCamera.y+m)
        if (r>motionStretch || left>0 || top>0 || left+r*(imageWidth+2*m)<width || top+r*(imageHeight+2*m)<height)
            drawGeometry()
        followStrokes(false)
        motionActive=true
        gestured=true
        motionHold.restart()
    }
    Timer {
        id: motionHold; interval: plan.motionRest
        onTriggered: {
            if (plan.pendingMotion) { restart(); return }
            plan.drawGeometry()
            plan.motionActive=false
            strokeRest.restart()
            mapDelay.restart()
            if (settleZoom.due) settleZoom.restart()
        }
    }
    function rotateView(degrees) {
        applyMotion()
        fitted = false
        var old = world(width/2,height/2)
        bearing = (bearing+degrees)%360
        var now = screen(old.x,old.y)
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
            if(a.kind==="pan" && a.phase==="move") panBy(a.dx,a.dy)
            else if(a.kind==="zoom" && a.phase==="move") zoomBy(Math.pow(1.2,-a.dy/40),width/2,height/2)
            else if(a.kind==="recentre") { applyMotion(); fitted=false; panX+=width/2-a.x; panY+=height/2-a.y }
            else if(a.kind==="fit") fit()
            else if(a.kind==="menu") {
                backend.pointerScale(1/zoom,bearing)
                var point=world(a.x,a.y); backend.contextAt(point.x,point.y); menu.popup(a.x,a.y)
            }
        }
    }
    function vertexAt(x, y) {
        if(!backend.grips.length || !cornersShown) return -1      // corners not shown are not taken (R707)
        var p=world(x,y)
        return backend.vertexAt(p.x,p.y,1/zoom)
    }
    function changedView() {
        annotationPending=true
        // a camera set at once (framing, a turn, a command, a new size) is drawn at once; a gesture's follows it
        if (!applyingMotion || !retained) { drawGeometry(); if (!applyingMotion) strokeRest.restart() }
        mapDelay.restart()
        if(vertexDragIndex<0) hotVertex=-1
        if (backend.sideEditing) backend.cancelSide()
    }
    // Pointer devices can send several events before a frame. Moving the shared transforms still invalidates their
    // native descendants: publish one camera to the annotations in the animation phase, before scene graph sync.
    // The geometry and the ink therefore reach the same frame, with no delayed final jump.
    property var annotationCamera: ({x: panX, y: panY, zoom: zoom, bearing: bearing})
    property bool annotationPending: true
    FrameAnimation {
        running: plan.annotationPending || plan.pendingMotion !== null
        onTriggered: {
            plan.applyMotion()
            plan.annotationCamera={x:plan.panX,y:plan.panY,zoom:plan.zoom,bearing:plan.bearing}
            plan.annotationPending=false
        }
    }
    // R496/R498: the labels and the dashes are laid out at the zoom the wheel settled on, and only scaled meanwhile.
    // R541: settled 300 ms after the last step, a lone step too: a hand turns the wheel a notch every 150-250 ms, and
    // a step that settled at once laid out the strings' names and the dashes again at every notch (40-110 ms each).
    property real settledZoom: 1
    readonly property int settleDelay: 300
    Timer {
        id: settleZoom; interval: plan.settleDelay
        // the hand still moving: the labels and the dashes wait for it to rest (motionHold asks again)
        property bool due: false
        onTriggered: {
            due=plan.motionActive
            if (due || plan.settledZoom===plan.zoom) return
            // after a gesture the names fade over to their new places; a camera set at once has them at once
            if (plan.gestured) settleLabels.restart()
            else plan.settledZoom=plan.zoom
            plan.gestured=false
        }
    }
    SequentialAnimation {
        id: settleLabels
        NumberAnimation { target: stringLabels; property: "opacity"; to: 0; duration: Theme.motion.LABELS_OUT }
        ScriptAction { script: plan.settledZoom=plan.zoom }
        NumberAnimation { target: stringLabels; property: "opacity"; to: 1; duration: Theme.motion.LABELS_IN }
    }
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
        if (previousWidth>0) keepCentre((width-previousWidth)/2, 0)
        previousWidth=width
        sizeChanged()
    }
    onHeightChanged: {
        if (previousHeight>0) keepCentre(0, (height-previousHeight)/2)
        previousHeight=height
        sizeChanged()
    }
    // R37: a new size keeps the drawing's centre by moving the image already drawn, as a gesture does: it is drawn
    // again once the size rests, or at once if it no longer covers the view
    function keepCentre(dx, dy) {
        applyingMotion=true
        panX+=dx; panY+=dy
        applyingMotion=false
        followMotion()
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
        // Measure (study 46): with a point placed the arrows, a length typed, Enter and Backspace are the tool's
        var measuring=backend.tool==="measure" && backend.measure.inHand
        if (measuring && (arrows.indexOf(event.key)>=0 || (plain && ([Qt.Key_Return,Qt.Key_Enter,Qt.Key_Backspace].indexOf(event.key)>=0
                          || /^[0-9,.-]+$/.test(event.text))))) { event.accepted=true; return }
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
        function onOverlayChanged() {
            if (plan.vertexDragIndex<0 && !vertexMouse.containsMouse) plan.hotVertex=-1
        }
        function onNavigationChanged() { plan.navigator.setStyle(backend.navigationStyle) }
    }
    Timer {
        id: mapDelay; interval: 140
        onTriggered: {
            if (plan.motionActive) { restart(); return }
            var a=plan.world(0,0), b=plan.world(plan.width,0), c=plan.world(0,plan.height), d=plan.world(plan.width,plan.height)
            backend.viewSettled(Math.min(a.x,b.x,c.x,d.x),Math.min(a.y,b.y,c.y,d.y),
                Math.max(a.x,b.x,c.x,d.x),Math.max(a.y,b.y,c.y,d.y),1/plan.zoom,Screen.devicePixelRatio)
        }
    }
    Item {
        id: geometrySurface
        objectName: "planGeometrySurface"
        width: plan.imageWidth; height: plan.imageHeight     // R37: rounded up, see imageWidth
        Loader {
            objectName: "mapLayer"
            x: -plan.motionMargin; y: -plan.motionMargin
            width: parent.width+2*plan.motionMargin; height: parent.height+2*plan.motionMargin
            active: backend.maps !== null
            source: active ? "MapLayer.qml" : ""
            onLoaded: {
                item.backend=Qt.binding(function(){return backend.maps})
                item.viewScale=Qt.binding(function(){return plan.renderCamera.zoom})
                item.offsetX=Qt.binding(function(){return plan.renderCamera.x+plan.motionMargin})
                item.offsetY=Qt.binding(function(){return plan.renderCamera.y+plan.motionMargin})
                item.viewRotation=Qt.binding(function(){return plan.bearing})
            }
        }
        Item {
            id: worldLayer
            objectName: "worldLayer"
            x: plan.renderCamera.x; y: plan.renderCamera.y
            scale: plan.renderCamera.zoom; rotation: plan.bearing
            transformOrigin: Item.TopLeft
            // R707 (study 55, 3.3): the drawing goes out while the site's mark comes in, and is not drawn under it
            opacity: 1-siteMark.shown
            visible: opacity>0
            property real settledScale: plan.settledZoom
            property real strokeScale: plan.strokeZoom
            // R706: what the image shows, and half a view more on every side, in the scene's metres (west, north,
            // east, south): the layers cut in squares draw and build only what touches it. The margin is what a
            // zoom out or a pan uncovers before the next redraw: built before it is seen.
            readonly property var viewBox: {
                const camera=plan.renderCamera, m=plan.motionMargin, w=plan.imageWidth, h=plan.imageHeight, ex=w/2, ey=h/2
                const a=plan.bearing*Math.PI/180, c=Math.cos(a), s=Math.sin(a)
                let x0=Infinity, y0=Infinity, x1=-Infinity, y1=-Infinity
                for (const p of [[-m-ex,-m-ey],[w+m+ex,-m-ey],[-m-ex,h+m+ey],[w+m+ex,h+m+ey]]) {
                    const u=(p[0]-camera.x)/camera.zoom, v=(p[1]-camera.y)/camera.zoom
                    const x=u*c+v*s, y=-u*s+v*c
                    x0=Math.min(x0,x); x1=Math.max(x1,x); y0=Math.min(y0,y); y1=Math.max(y1,y)
                }
                return [x0,y0,x1,y1]
            }
            // the hatches as wide on screen at every zoom and turn of the view
            readonly property matrix4x4 patternTransform: {
                var camera=plan.renderCamera,a=plan.bearing*Math.PI/180,c=Math.cos(a)/camera.zoom,s=Math.sin(a)/camera.zoom
                return Qt.matrix4x4(c,s,0,-c*camera.x-s*camera.y,-s,c,0,s*camera.x-c*camera.y,0,0,1,0,0,0,0,1)
            }
            // the sun map under the outlines, the obstacles and the modules (study 45, package 5)
            SunMapLayer { objectName: "sunMapLayer"; sun: plan.sun }
            PolygonLayer {
                objectName: "outlineLayer"
                objects: plan.polygons.filter(function(o){return o.kind!=="prop" && o.kind!=="prop_mark"}); halo: true
                hatchSource: backend.hatchSource
                patternTransform: worldLayer.patternTransform
                // over the sun map the roofs and the sub-fields keep their outlines, not their tint (its colours are read)
                grounds: !plan.sun || !plan.sun.on
            }
            Loader {
                active: GraphicsInfo.api === GraphicsInfo.Software && plan.polygons.some(o=>o.kind==="exclusion")
                sourceComponent: SoftwareHatch {
                    width: plan.width; height: plan.height
                    transform: Matrix4x4 { matrix: worldLayer.patternTransform }
                    polygons: plan.polygons.filter(o=>o.kind==="exclusion").map(o=>o.points.map(p=>{
                        const q=plan.screen(p.x,-p.y); return [q.x,q.y]
                    }))
                }
            }
            ModuleBatch {
                id: geometry
                objectName: "moduleGeometry"
                width: 1; height: 1
                curves: plan.renderer!=="triangles"
                visible: plan.renderer==="batched" || plan.renderer==="triangles" || plan.renderer==="geometry"
                modules: visible ? plan.modules : []
                // R707: a fill for each module from the scale of the fields; its outline fades out below the
                // strings' scale (2000 outlines, each with its halo, were most of the drawing from far)
                shown: plan.modulePixels>=plan.levels.field
                line: plan.seen(plan.levels.outlineGone, plan.levels.string)
                // R547: a layout that moves modules: they fade in at their place, no jump and no flash
                NumberAnimation on opacity { id: modulesFade; running: false; from: 0.35; to: 1; duration: Theme.motion.FAST; easing.type: Theme.motion.EASE }
                Connections { target: backend; function onModulesMoved() { if (!Theme.reducedMotion) modulesFade.restart() } }
            }
            // R707: from far, one fill for each row of modules instead of one for each module
            ModuleBatch {
                objectName: "moduleRows"; width: 1; height: 1
                preset: backend.rowPaths; line: 0
                visible: geometry.visible; shown: plan.modulePixels<plan.levels.field
            }
            PolygonLayer { objects: plan.renderer==="shapes" ? plan.modules : []; modules: true }
            // the modules laid coloured by the class of the sun map (decision 2), over their own drawing
            ModuleBatch {
                objectName: "sunMapModules"; width: 1; height: 1; sync: true
                visible: !!plan.sun && plan.sun.on
                preset: visible ? plan.sun.modulePaths : []
            }
            Repeater {
                model: backend.shadows
                delegate: Shape {
                id: strokeShape0
                    required property var modelData
                    preferredRendererType: Shape.CurveRenderer
                    Controls.ViewPath {
                    surface: strokeShape0
                    halo: true
                    viewScale: 1;
                        fillColor: "transparent";  fillRule: ShapePath.OddEvenFill
                        PathSvg { path: modelData.path }
                    }
                Controls.ViewPath {
                    surface: strokeShape0
                    viewScale: 1;
                        fillColor: Theme.colors.overlay.shade; strokeColor: "transparent"; fillRule: ShapePath.OddEvenFill
                        PathSvg { path: modelData.path }
                    }
                }
            }
            // R496: the finished strings, the modules in no string, the draft and the band to the pointer are layers of
            // their own, each made again only when it changes; the small ones are built at once, never in a thread
            // that leaves them blank for a few frames.
            // They stay built in every phase and are only shown in Plant (R483): no item made again on the way back.
            // R598: the large layers come as the paths already joined (a few strings, not a row for each module)
            ModuleBatch {
                objectName: "wireFills"; width: 1; height: 1; preset: backend.wireFillPaths; visible: backend.stringsVisible
                // R707: the strings' colours fade out below the scale of the fields
                shown: plan.modulePixels>plan.levels.colourGone
                opacity: plan.seen(plan.levels.colourGone, plan.levels.field)
            }
            ModuleBatch { objectName: "unwiredBatch"; width: 1; height: 1; preset: backend.unwiredJoined; sync: true; visible: backend.stringsVisible }
            ModuleBatch { objectName: "draftFills"; width: 1; height: 1; modules: backend.draftFills; sync: true; visible: backend.stringsVisible }
            // R707 (study 55, 3.6): obstacles and 3D objects over the modules and over the strings' colours too (they
            // were drawn before the colours)
            PolygonLayer { objectName: "propsLayer"; objects: plan.polygons.filter(function(o){return o.kind==="prop" || o.kind==="prop_mark"}); halo: true }
            // R580: the outlines of what is chosen or under the pointer lie over the strings' fills and under their lines
            // (they were drawn last, and a sub-field's outline cut the lines of its strings).
            // Widgets put hover at Z_SELECTION - 1: it must not erase the solid selection.
            PolygonLayer { objects: sweep.hoveredRidges }
            PolygonLayer { objects: sweep.hoveredOutline }
            PolygonLayer { objectName: "highlightLayer"; objects: backend.highlights }
            // R707: the strings' lines, their marks and the optimizers from the scale of the strings
            ModuleBatch {
                objectName: "wiresBatch"; preset: backend.wirePaths; visible: backend.stringsVisible
                shown: plan.modulePixels>=plan.levels.string*plan.levels.ease
                opacity: plan.seen(plan.levels.string*plan.levels.ease, plan.levels.string)
            }
            // R706: what follows the scale among the strings' lines (arrowheads, jumps with a lane), few and apart:
            // a new step of the scale draws these again and leaves the lines of every module as they are
            ModuleBatch {
                objectName: "wireMarks"; preset: backend.wireMarkPaths; visible: backend.stringsVisible
                shown: plan.modulePixels>=plan.levels.string*plan.levels.ease
                opacity: plan.seen(plan.levels.string*plan.levels.ease, plan.levels.string)
            }
            ModuleBatch {
                objectName: "optimizerBatch"; preset: backend.optimizerPaths; visible: backend.stringsVisible
                shown: plan.modulePixels>=plan.levels.string*plan.levels.ease
                opacity: plan.seen(plan.levels.string*plan.levels.ease, plan.levels.string)
            }
            ModuleBatch { objectName: "draftWires"; modules: backend.draftWires; sync: true; visible: backend.stringsVisible }
            Shape {
                id: band; objectName: "draftBand"
                readonly property var ends: backend.draftBand
                visible: ends.length===4 && backend.stringsVisible
                preferredRendererType: Shape.CurveRenderer
                Controls.ViewPath {
                    surface: band
                    halo: true
                    viewScale: 1;
                      cosmeticStroke: true
                    dashed: true;
                    fillColor: "transparent"
                    startX: band.visible ? band.ends[0] : 0; startY: band.visible ? band.ends[1] : 0
                    PathLine { x: band.visible ? band.ends[2] : 0; y: band.visible ? band.ends[3] : 0 }
                }
                Controls.ViewPath {
                    surface: band
                    viewScale: 1;
                    strokeColor: backend.draftColour || plan.ink;  cosmeticStroke: true
                    dashed: true;
                    fillColor: "transparent"
                    startX: band.visible ? band.ends[0] : 0; startY: band.visible ? band.ends[1] : 0
                    PathLine { x: band.visible ? band.ends[2] : 0; y: band.visible ? band.ends[3] : 0 }
                }
            }
            ModuleBatch { width: 1; height: 1; preset: backend.moduleHighlightPaths }
            PolygonLayer { objects: backend.draftObjects }
            // R706: the strings' dots, one layer of the drawing (a short stroke with round ends as wide as a dot):
            // they were an item each over the drawing, made again each time the view settled near the modules
            ModuleBatch {
                objectName: "dotsBatch"; width: 1; height: 1
                // kept at every scale (R706) and shown from the scale of the modules (R707): crossing it makes none again
                preset: backend.dotPaths; pen: Theme.annotation.POINT
                visible: backend.stringsVisible
                shown: plan.modulePixels>=plan.levels.module*plan.levels.ease
                opacity: plan.seen(plan.levels.module*plan.levels.ease, plan.levels.module)
            }
            // R707: between the scale of the strings and that of the modules, the dot of each string's first module
            ModuleBatch {
                objectName: "headsBatch"; width: 1; height: 1
                preset: backend.headPaths; pen: Theme.annotation.POINT
                visible: backend.stringsVisible
                shown: plan.modulePixels>=plan.levels.string*plan.levels.ease && plan.modulePixels<plan.levels.module
                opacity: plan.seen(plan.levels.string*plan.levels.ease, plan.levels.string)
            }
        }
    }
    ShaderEffectSource {
        // the geometry's one image (R706): drawn again only when what it shows or renderCamera changes
        id: motionSnapshot
        objectName: "motionSnapshot"
        sourceItem: geometrySurface
        sourceRect: Qt.rect(-plan.motionMargin,-plan.motionMargin,
                            plan.imageWidth+2*plan.motionMargin,plan.imageHeight+2*plan.motionMargin)
        width: plan.imageWidth+2*plan.motionMargin; height: plan.imageHeight+2*plan.motionMargin
        x: plan.panX-plan.motionRatio*(plan.renderCamera.x+plan.motionMargin)
        y: plan.panY-plan.motionRatio*(plan.renderCamera.y+plan.motionMargin)
        scale: plan.motionRatio
        transformOrigin: Item.TopLeft
        samples: Theme.annotation.SAMPLES
        smooth: true
        live: true
        hideSource: plan.retained
        visible: plan.retained
    }
    MouseArea {
        id: mouse
        objectName: "planMouse"
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        cursorShape: Controls.ToolCursor.shape(backend.tool !== "select", plan.spaceHeld)    // the 3D view's too
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
            // study 46, Daniel's choice 2 (as in AutoCAD): Shift + right button with Measure in hand opens the snaps'
            // menu for the point being placed, not the plan's menu
            if(event.button===Qt.RightButton && (event.modifiers & Qt.ShiftModifier) && backend.tool==="measure") {
                navigated=true; snapMenu.popup(event.x,event.y); return
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
        if(action[0]==="pan") plan.panBy(action[1],action[2])
        else plan.zoomBy(Math.pow(1.2,action[2]),event.x,event.y)
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
        onScaleChanged: function(delta) { plan.zoomBy(delta,centroid.position.x,centroid.position.y) }
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
    ToolOverlay { anchors.fill: parent; plan: plan; preview: backend.preview }
    Controls.LitSide {
        // R505, R617: the side «Align the view to a side» (and every command that waits for a side) would take: the
        // program's one lit side, in the drawing's colour
        objectName: "collectSide"
        readonly property var side: backend.collectSide
        visible: side.length === 2
        a: visible ? plan.screen(side[0][0], side[0][1]) : Qt.point(0, 0)
        b: visible ? plan.screen(side[1][0], side[1][1]) : Qt.point(0, 0)
        ink: backend.planColors.draw
    }
    Controls.PointerSign {
        // R497: the command's icon beside the pointer on a side «Align» takes, as SelectionOverlay's + and - (R535)
        objectName: "collectBadge"
        visible: backend.collectBadge!=="" && mouse.containsMouse && !plan.spaceHeld
        pointer: plan.pointer; colours: backend.planColors
        sign: ""; iconName: backend.collectBadge || "view_align"; iconColor: plan.ink
    }
    RowHandle { plan: plan; backend: plan.backend }
    readonly property var sidePillBoxes: sidePills.visible ? sidePills.pills.map(function(p) { return p.bounds || p }) : []
    SidePills { id: sidePills; plan: plan; backend: plan.backend; shown: plan.measuresShown }
    Shape {
        id: vertexPreview; visible: plan.vertexDragIndex>=0
        preferredRendererType: Shape.CurveRenderer
        property var points: backend.grips.map(function(p,i) {
            return plan.cornerAt(i,p.x,p.y)
        })
        Controls.ViewPath {
                surface: vertexPreview
                halo: true
                viewScale: 1;   dashed: true; fillColor: "transparent"
            PathPolyline { path: vertexPreview.points }
            PathLine { x: vertexPreview.points.length ? vertexPreview.points[0].x : 0; y: vertexPreview.points.length ? vertexPreview.points[0].y : 0 }
        }
            Controls.ViewPath {
                surface: vertexPreview
                viewScale: 1; strokeColor: backend.planColors.sel;  dashed: true; fillColor: "transparent"
            PathPolyline { path: vertexPreview.points }
            PathLine { x: vertexPreview.points.length ? vertexPreview.points[0].x : 0; y: vertexPreview.points.length ? vertexPreview.points[0].y : 0 }
        }
    }
    // R707 (study 55, 3.3): from far, where buildings and fields can no longer be told apart, one mark for the site,
    // the same size on screen at every zoom out: a drop in the site's colour with the project's name and power under
    // it (the drop alone from levels.siteNameless). A click frames the site again.
    Item {
        id: siteMark
        objectName: "planSiteMark"
        // read once from the backend: every read of a map or a list is a JavaScript copy to be collected later
        readonly property var box: backend.bounds
        readonly property var site: backend.site
        readonly property real span: box && box.length===4 ? Math.max(box[2],box[3])*plan.renderCamera.zoom : 1e9
        readonly property real shown: site.shown ?
            Math.max(0,Math.min(1,(plan.levels.siteIn-span)/(plan.levels.siteIn-plan.levels.siteAlone))) : 0
        // Daniel 21/11/2026: the camera in hand, as the map's image is moved to it at every frame of a drag or a zoom.
        // The camera the image was last drawn at (renderCamera) left the drop behind the map until the next redraw.
        readonly property point at: {
            if (!box || box.length!==4) return Qt.point(0,0)
            const a=plan.bearing*Math.PI/180, c=Math.cos(a), s=Math.sin(a)
            const x=box[0]+box[2]/2, y=box[1]+box[3]/2
            return Qt.point(plan.panX+plan.zoom*(x*c-y*s), plan.panY+plan.zoom*(x*s+y*c))
        }
        readonly property real size: Controls.ControlMetrics.planMarker*1.6
        visible: shown>0
        opacity: shown
        x: at.x; y: at.y
        Rectangle {
            objectName: "planSiteDrop"
            // a square with its corner at the site, turned to stand on its point
            width: siteMark.size; height: siteMark.size
            x: -width/2; y: -height*1.414
            radius: width/2; bottomRightRadius: 0
            rotation: 45
            color: Theme.colors.overlay.select
            border.width: Controls.ControlMetrics.planMarkerRing; border.color: Theme.colors.overlay.halo
            Rectangle {
                anchors.centerIn: parent
                width: parent.width*.38; height: width; radius: width/2
                color: Theme.colors.overlay.halo
            }
        }
        Rectangle {
            id: siteName
            objectName: "planSiteName"
            visible: siteMark.site.text!=="" && 1/plan.renderCamera.zoom<plan.levels.siteNameless
            x: -width/2; y: Theme.space.XS
            width: siteText.implicitWidth+2*Theme.space.S; height: siteText.implicitHeight+Theme.space.XS
            radius: height/2
            color: backend.planColors.label_bg
            border.width: 1; border.color: Theme.colors.overlay.select
            Text {
                id: siteText
                anchors.centerIn: parent
                text: siteMark.site.text
                color: backend.planColors.label_fg
                font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE
            }
        }
        // R714 (Daniel 21/11/2026): from far the checks' marks are not drawn one by one (the warning's triangle
        // stayed over the drop at every zoom out): the worst of them sits on the drop, with the number of checks
        PlanSymbol {
            objectName: "planSiteChecks"
            readonly property var summary: backend.marksSummary
            visible: summary.name !== undefined
            shape: summary; name: summary.name || "info"; count: summary.count || 1
            views: true
            size: Controls.ControlMetrics.viewMark*.8
            fontFamily: Theme.fontFamily
            x: siteMark.size*.2; y: -siteMark.size*2.05
        }
        MouseArea {
            objectName: "planSiteFrame"
            enabled: siteMark.shown>=.5
            x: -Math.max(siteMark.size,siteName.visible ? siteName.width : 0)/2; y: -siteMark.size*1.9
            width: -2*x; height: siteMark.size*1.9+(siteName.visible ? siteName.y+siteName.height : 0)
            cursorShape: Qt.PointingHandCursor
            onClicked: plan.fit()
        }
    }
    StringLabels { id: stringLabels; plan: plan; backend: plan.backend; avoid: sidePills.visible ? sidePills.pills : []; visible: backend.stringsVisible }
    Repeater {
        model: backend.marks
        delegate: PlanSymbol {
            required property var modelData
            shape: modelData; name: modelData.name; count: modelData.count
            views: true                                             // with the views' thin white edge, no disc
            // R714: one by one only while the drawing is near enough to read them; from far, on the site's drop
            opacity: plan.checkMarksShown
            visible: opacity>0
            fontFamily: Theme.fontFamily
            property point location: plan.screen(modelData.x,-modelData.y)
            x: location.x-width/2; y: location.y-height/2
            Controls.MarkArea {
                tip: modelData.tip || ""
                onHoveredChanged: plan.markHovered=hovered          // its words, not the module's under it
                Component.onDestruction: if (hovered) plan.markHovered=false
                onClicked: function(event) {
                    // R529: on the modules of its sub-field the click takes the module under it
                    var at=mapToItem(plan,event.x,event.y), p=plan.world(at.x,at.y)
                    plan.forceActiveFocus()
                    backend.markClick(modelData.target[0],modelData.target[1],p.x,p.y)
                }
            }
        }
    }
    // R701: anchors stay in world coordinates. Two shared transforms move every dot and keep its ink screen-sized,
    // without evaluating screen() once per module at every pan/zoom (including the hidden dots outside Plant).
    readonly property bool stringsShown: backend.stringsVisible
    Matrix4x4 {
        id: dotCamera
        matrix: {
            const camera=plan.annotationCamera,a=camera.bearing*Math.PI/180,c=Math.cos(a)*camera.zoom,s=Math.sin(a)*camera.zoom
            return Qt.matrix4x4(c,-s,0,camera.x,s,c,0,camera.y,0,0,1,0,0,0,0,1)
        }
    }
    Matrix4x4 {
        id: dotInk
        matrix: {
            const camera=plan.annotationCamera,a=camera.bearing*Math.PI/180,c=Math.cos(a)/camera.zoom,s=Math.sin(a)/camera.zoom
            return Qt.matrix4x4(c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1)
        }
    }
    component Dots: Repeater {
        delegate: Item {
            required property var modelData
            objectName: "stringDotAnchor"
            x: modelData.x; y: -modelData.y
            transform: dotInk
            visible: plan.stringsShown
            Controls.ViewPoint {
                objectName: "stringDot"
                x: -width/2; y: -height/2
                ink: parent.modelData.colour
            }
        }
    }
    Item {
        objectName: "stringDots"
        transform: dotCamera
        // Ink has no input. Skip the entire subtree when Qt searches for the recipient of a pointer event.
        enabled: false
        Dots { model: backend.draftDots }        // the few of the string in hand follow it at once
    }
    Repeater {
        model: backend.plainLabels.filter(function(p){return p.side===undefined && p.kind!=="name" && p.kind!=="number"})
        delegate: Controls.LengthPill {
            required property var modelData
            property point location: plan.screen(modelData.x,modelData.y)
            x: location.x-width/2+(modelData.offsetX || 0); y: location.y-height/2+(modelData.offsetY || 0)
            visible: plan.clearOfChrome(x, y, width, height)
            value: modelData.text
            ground: backend.planColors.label_bg; ink: backend.planColors.label_fg
            MouseArea { anchors.fill: parent; enabled: modelData.side!==undefined && backend.tool==="select"
                onClicked: backend.editSide(modelData.side) }
        }
    }
    Repeater {
        model: backend.grips
        delegate: Controls.ViewPoint {
            required property var modelData
            objectName: "vertexGrip"+modelData.index
            visible: plan.cornersShown
            property point location: plan.cornerAt(modelData.index,modelData.x,modelData.y)
            readonly property bool chosen: backend.chosenCorners.indexOf(modelData.index)>=0
            readonly property bool hot: chosen || plan.hotVertex===modelData.index || plan.vertexDragIndex===modelData.index
            x: location.x-width/2; y: location.y-height/2
            ink: hot ? backend.planColors.sel : backend.planColors.label_fg
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
    // With the sun map on, its figures under the pointer (of the tile, or of the module) on the line after them.
    Controls.ToolTip {
        id: moduleTip
        objectName: "moduleTip"
        readonly property var record: sweep.hovered && sweep.hovered.record && sweep.hovered.record.kind==="module" ? sweep.hovered.record : null
        readonly property int revision: backend.moduleTipsRevision !== undefined ? backend.moduleTipsRevision : 0
        readonly property string mapText: plan.sun && plan.sun.on ? plan.sun.pointerText : ""
        text: { const r=revision, words=record && backend.moduleTip ? backend.moduleTip(record.oid,record.key) : ""
            return words && mapText ? words+"\n"+mapText : words || mapText }
        visible: text!=="" && mouse.containsMouse && !mouse.pressed && !mouse.swept && !plan.markHovered
        placed: true
        shownAt: plan.pointer           // R550: beside it as every tooltip (ControlMetrics.besidePointer)
    }
    PlanLegend {
        id: optimizerLegend
        objectName: "optimizerLegend"
        z: Theme.stack.VIEW_BAR
        visible: backend.optimizerPaths !== undefined && backend.optimizerPaths.length>0
        x: Theme.space.M; y: plan.height-height-Theme.space.XXXL-Theme.space.L
        words: backend.optimizerLegendWords || []
    }
    Compass {
        id: compass
        z: Theme.stack.VIEW_BAR
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
        tooltipText: turned ? backend.compassText+"\n"+backend.compassTurned.replace("{heading}",headingText) : backend.compassUp
        onNorth: plan.rotateView(-plan.bearing)
        onRotate: function(degrees) { plan.rotateView(degrees) }
    }
    ScaleBar {
        id: scaleBar
        z: Theme.stack.VIEW_BAR
        objectName: "scaleBar"
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: Theme.space.M
        metresPerPixel: 1/plan.zoom; ink: plan.ink; ground: backend.planColors.label_bg
        visible: backend.maps===null || !backend.maps.equalEarth
    }
    // R552 (Daniel 08/11/2026: «questa scritta si nasconde dietro i pannelli»): the credit of the background stands
    // with the scale, the compass and the bars above the project's drawing, on a full dark ground; it was in MapLayer,
    // under the drawing, and the modules passed over it and through its half-clear ground. R555 (1): above the drawing,
    // on the one ground of the pills over a view (overlay.glass), as the scale and the coordinates beside it
    Rectangle {
        id: credit
        z: Theme.stack.VIEW_BAR
        objectName: "mapCredit"
        readonly property var maps: backend.maps
        visible: maps !== null && attribution.text.length > 0 && width >= 4 * Theme.space.M
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.space.M
        // the room left of it is the scale's and the coordinates' (their width kept while the pointer is away)
        readonly property real from: cursorPill.x + cursorPill.width + Theme.space.S
        width: Math.max(0, Math.min(plan.width - Theme.space.M - from, attribution.implicitWidth + 2*Theme.space.M))
        height: Theme.size.CONTROL
        radius: Theme.radius.CONTROL
        color: Theme.colors.overlay.glass
        Controls.CopyLabel {
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
        z: Theme.stack.VIEW_BAR
        variant: "view"
        objectName: "planCursor"
        visible: plan.cursorText !== ""
        anchors.bottom: parent.bottom; anchors.bottomMargin: Theme.space.M
        x: scaleBar.visible ? scaleBar.x + scaleBar.width + Theme.space.S : Theme.space.M
        width: Math.ceil(Math.max(cursorWords.implicitWidth, cursorLongest.advanceWidth(plan.cursorLongest))) + 2 * pad
        ground: backend.planColors.label_bg; ink: plan.ink
        FontMetrics { id: cursorLongest; font: cursorWords.font }
        Controls.CopyLabel {
            id: cursorWords; objectName: "planCursorText"
            x: cursorPill.pad; height: parent.height; verticalAlignment: Text.AlignVCenter
            text: plan.cursorText; color: cursorPill.ink
            font: cursorPill.font
        }
    }
    // the sun map's words over the plan (its labels, its legend over the scale) and its panel, opened from its button
    // in the bar (study 45, package 5); its figures under the pointer are in moduleTip
    SunMapOverlay {
        id: sunOverlay
        z: Theme.stack.VIEW_BAR
        plan: plan
        legendBottom: scaleBar.visible ? scaleBar.y : plan.height - Theme.space.M
    }
    SunMapPanel { id: sunPanel; objectName: "sunMapPopup"; sun: plan.sun }
    onPointerChanged: if (sun && sun.on) {
        const q=world(pointer.x,pointer.y), r=sweep.hovered && sweep.hovered.record && sweep.hovered.record.kind==="module" ? sweep.hovered.record : null
        sun.point(q.x,q.y,r ? String(r.oid) : "",r ? String(r.key) : "")
    }
    Connections { target: mouse; function onContainsMouseChanged() { if (!mouse.containsMouse && plan.sun) plan.sun.leave() } }
    ViewBar {
        id: viewbar; objectName: "planViewBar"
        z: Theme.stack.VIEW_BAR
        x: Theme.space.M; y: Theme.space.M
        plan: plan; backend: plan.backend; viewMode: plan.viewMode; backgroundMenu: backgroundMenu; sunPanel: sunPanel
        onWidthChanged: plan.toolbarBounds=Qt.rect(x,y,width,height)
        onHeightChanged: plan.toolbarBounds=Qt.rect(x,y,width,height)
        Component.onCompleted: plan.toolbarBounds=Qt.rect(x,y,width,height)
        onBackgroundRequested: backgroundMenu.popup(x,y+height)
    }
    MapNotice {
        id: mapNotice
        maps: backend.maps
        z: Theme.stack.VIEW_BAR
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
        id: imageValueDialog; objectName: "imageValueDialog"
        acceptText: backend.texts.apply; rejectText: backend.texts.cancel
        acceptCheck: () => backend.underlays.accept(imageValue.text)
        Column {
            width: parent.width; spacing: Theme.space.S
            Controls.ReadableText { id: imageValueLabel; width: parent.width; wrapMode: Text.Wrap }
            Controls.TextField { id: imageValue; width: parent.width
                onAccepted: imageValueDialog.tryAccept() }
        }
        onOpened: imageValue.forceActiveFocus()
        onClosed: plan.forceActiveFocus()
    }
    Controls.Menu {
        id: menu
        objectName: "planContextMenu"
        Controls.TextActions { id: objectCopy; readOnly: true; wholeText: backend.selectionName }
        onAboutToShow: objectCopy.begin()
        Controls.MenuItem { text: textEditing.labels.name; enabled: objectCopy.allowed("copy"); onTriggered: objectCopy.execute("copy") }
        // R533: what the menu acts on at the top, under muted titles; the levels above it (sub-field, roof) and the
        // point's coordinates in submenus, from the field «menu» of each entry
        Component {
            id: contextEntry
            // R564: the common entry (rule, title, command with the reason it is off), as the bar's and the 3D view's
            Controls.MenuEntry {
                required property var modelData
                objectName: modelData.header ? "planContextTitle" : "planContext-"+modelData.command
                entry: modelData
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
        onClosed: { objectCopy.end(); plan.forceActiveFocus() }
    }
    Measure.SnapMenu { id: snapMenu; measure: backend.measure; onClosed: plan.forceActiveFocus() }
    Controls.Dialog {
        id: renameDialog; title:backend.texts.rename
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
        implicitWidth: Controls.ControlMetrics.dialogSize.relayout.width
        acceptText: backend.texts.yes; rejectText: backend.texts.no          // R518: the window's buttons
        Controls.ReadableText { id: relayoutMessage; wrapMode: Text.Wrap }
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
        implicitWidth: Controls.ControlMetrics.dialogSize.placeOverlap.width
        function choose(value) { answer=value; close() }
        Column {
            width: parent.width; spacing: Theme.space.M
            Controls.ReadableText { id: overlapMessage; width: parent.width; wrapMode: Text.Wrap
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
        implicitWidth: Controls.ControlMetrics.dialogSize.placeCoordinates.width
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
                Controls.CopyLabel { text: coordinatesDialog.labels()[0] }
                Controls.TextField { id: coordA; textActions.identity: coordinatesDialog.system; textActions.numericPolicy: ({unit:coordinatesDialog.system === "latlon" ? "\u00b0" : "m", kind:"", minimum:coordinatesDialog.system === "latlon" ? -90 : -1e12, maximum:coordinatesDialog.system === "latlon" ? 90 : 1e12, decimals:12, locale:Qt.locale()}); objectName: "placeA"; width: 200; selectByMouse: true; onTextEdited: coordinatesDialog.refresh() }
                Controls.CopyLabel { text: coordinatesDialog.labels()[1] }
                Controls.TextField { id: coordB; textActions.identity: coordinatesDialog.system; textActions.numericPolicy: ({unit:coordinatesDialog.system === "latlon" ? "\u00b0" : "m", kind:"", minimum:coordinatesDialog.system === "latlon" ? -180 : -1e12, maximum:coordinatesDialog.system === "latlon" ? 180 : 1e12, decimals:12, locale:Qt.locale()}); objectName: "placeB"; width: 200; selectByMouse: true; onTextEdited: coordinatesDialog.refresh() }
                Controls.ReadableText { text: coordinatesDialog.info.texts ? coordinatesDialog.info.texts.turn : ""; width: parent.width - 200 - Theme.space.M
                    wrapMode: Text.Wrap }
                Controls.TextField { id: coordTurn; textActions.numericPolicy: ({unit:"\u00b0", kind:"", minimum:-1e12, maximum:1e12, decimals:12, locale:Qt.locale()}); objectName: "placeTurn"; width: 200; selectByMouse: true; onTextEdited: coordinatesDialog.refresh() }
            }
            Controls.ReadableText { width: parent.width; wrapMode: Text.Wrap; textStyle: "caption"
                text: coordinatesDialog.info.texts ? coordinatesDialog.info.texts.point : "" }
            Controls.ReadableText { objectName: "placeCheck"; width: parent.width; wrapMode: Text.Wrap
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
        id:sourcesDialog; title:backend.texts.sources
        implicitWidth: Controls.ControlMetrics.dialogSize.mapSources.width; implicitHeight: Controls.ControlMetrics.dialogSize.mapSources.height
        bodyScrolls: false
        rejectText: backend.texts.closeWindow
        // R518: «Applica» on the window's row of buttons, the window stays open
        acceptText: sourcesPage.item && sourcesPage.item.showApply ? sourcesPage.item.words.apply : ""
        acceptOnReturn: false
        acceptCheck: () => { sourcesPage.item.backend.apply(); return false }
        Loader { id: sourcesPage; active: sourcesDialog.opened && backend.sourceEditor!==null
            sourceComponent:MapSources { backend:plan.backend.sourceEditor; embedded: true } }
        onClosed:plan.forceActiveFocus()
    }
}
