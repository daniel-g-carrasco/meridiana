import QtQuick
import Meridiana.Measure
import "CameraMath.js" as Cam

Item {
    id: overlay
    required property var viewport
    readonly property var cam: viewport.cameraState
    readonly property var clipData: viewport.sceneMeasure ? viewport.sceneMeasure.annotationData : ({segments:{},points:{}})
    property int turns: 0
    property int clipRevision: 0
    onCamChanged: {
        if(viewport && viewport.sceneMeasure) viewport.sceneMeasure.invalidateVisibility()
        turns++
    }
    onWidthChanged: turns++
    onHeightChanged: turns++
    // Camera motion only reprojects the last world-space answer. Coalesce clipping
    // requests until rest instead of serialising a job for every wheel/animation step.
    onTurnsChanged: visibilityRest.restart()
    Timer { id: visibilityRest; interval: 120; onTriggered: overlay.requestVisibility() }
    Connections {
        target: overlay.viewport.sceneBackend
        function onSceneChanged() { overlay.turns++ }
    }
    Connections {
        target: overlay.viewport.sceneMeasure
        function onAnnotationChanged() { overlay.clipRevision++ }
    }
    Connections {
        target: overlay.viewport.measureBridge
        function onChanged() { Qt.callLater(overlay.requestVisibility) }
        function onDoneChanged() { Qt.callLater(overlay.requestVisibility) }
        function onPlacedChanged() { Qt.callLater(overlay.requestVisibility) }
    }
    function project(p) { return Cam.project(cam,p,width,viewport.sceneHeight) }
    function worldAtScreen(screen,anchor) {
        const ray=Cam.ray(cam,screen.x,screen.y,width,viewport.sceneHeight), forward=Cam.forward(cam)
        const at=[anchor[0],anchor[2],-anchor[1]]
        const t=Cam.dot(Cam.sub(at,ray[0]),forward)/Cam.dot(ray[1],forward)
        const p=Cam.add(ray[0],Cam.scale(ray[1],Math.max(.01,t)))
        return [p[0],-p[2],p[1]]
    }
    function worldOnFollow(screen) {
        const f=layer.display.follow
        if(!f) return worldAtScreen(screen,layer.elastic ? layer.elastic.b : layer.placed.marks[layer.placed.marks.length-1].at)
        const ray=Cam.ray(cam,screen.x,screen.y,width,viewport.sceneHeight)
        const a=[f.a[0],f.a[2],-f.a[1]], b=[f.b[0],f.b[2],-f.b[1]], axis=Cam.unit(Cam.sub(b,a))
        const w=Cam.sub(a,ray[0]), k=Cam.dot(axis,ray[1]), den=1-k*k
        if(den<1e-10) return f.a
        const t=(k*Cam.dot(ray[1],w)-Cam.dot(axis,w))/den
        const p=Cam.add(a,Cam.scale(axis,t))
        return [p[0],-p[2],p[1]]
    }
    function portions(a,b) { return clipData.segments[JSON.stringify([a,b])] || [] }
    function isVisibleAt(p) { return clipData.points[JSON.stringify(p)] || false }
    function requestVisibility() {
        if (!viewport.sceneMeasure || !layer.measure || width<=0 || viewport.sceneHeight<=0) return
        const segments=[], points=[], known={}, knownPoints={}
        function point(p) {
            const key=JSON.stringify(p)
            if(!knownPoints[key]) { knownPoints[key]=true; points.push({key:key,at:p}) }
        }
        function span(s) {
            if(!s) return
            const key=JSON.stringify([s.a,s.b])
            if(!known[key]) {
                known[key]=true
                const record={key:key,a:s.a,b:s.b}
                if(s.ray) { record.ray=s.ray; record.rayAt=s.rayAt || "b" }
                segments.push(record)
                point(s.a); point(s.b)
            }
        }
        function measurement(m) {
            if(!m) return
            ;(m.segments || []).forEach(span)
            ;(m.sources || []).forEach(span)
            ;(m.marks || []).forEach(function(k){point(k.at)})
        }
        layer.done.forEach(measurement)
        measurement(layer.placed)
        const d=layer.display
        if(layer.following && layer.placed && layer.placed.marks.length) {
            const last=layer.placed.marks[layer.placed.marks.length-1].at
            const live={a:last,b:worldOnFollow(layer.followEnd)}
            if(!d.follow) live.ray=Cam.ray(cam,layer.followEnd.x,layer.followEnd.y,width,viewport.sceneHeight)
            span(live)
        } else span(layer.elastic)
        ;(d.guides || []).forEach(span)
        span(d.source); span(d.edge)
        if(layer.movingReference) span({a:layer.movingReference.a,b:layer.movingReference.b,
            ray:Cam.ray(cam,layer.pointerScreen.x,layer.pointerScreen.y,width,viewport.sceneHeight),rayAt:"a"})
        if(d.pointer) point(d.pointer.at)
        if(!segments.length && !points.length) return
        viewport.sceneMeasure.visibility({camera:{origin:cam.position,forward:Cam.forward(cam),right:Cam.right(cam),up:Cam.up(cam),
            ortho:cam.ortho,halfHeight:Cam.halfHeight(cam),tangent:Math.tan(cam.fov*Math.PI/360),
            aspect:width/viewport.sceneHeight,far:Cam.CLIP,ground:viewport.sceneBackend.contextModels.length===0},
                                          segments:segments,points:points})
    }
    Component.onCompleted: Qt.callLater(requestVisibility)
    MeasureLayer {
        id: layer
        objectName: "sceneMeasures"
        anchors.fill: parent
        measure: overlay.viewport.measureBridge
        view: "3d"
        visibleParts: overlay.portions
        pointVisible: overlay.isVisibleAt
        worldAtScreen: overlay.worldAtScreen
        worldOnFollow: overlay.worldOnFollow
        revision: overlay.turns + overlay.clipRevision
        colors: overlay.viewport.sceneBackend.overlayColors
        pointerScreen: overlay.viewport.measureFollows ? overlay.viewport.measurePointer : null
        picking: !overlay.viewport.measuring && !overlay.viewport.placing
        onPicked: overlay.viewport.forceActiveFocus()
        toScreen: function(p) {
            const s=overlay.viewport.projectPoint([p[0],p[2],-p[1]])
            return s ? Qt.point(s[0],s[1]) : Qt.point(-overlay.width,-overlay.height)
        }
    }
}
