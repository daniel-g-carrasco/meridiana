import QtQuick
import Meridiana.Theme

Canvas {
    id: root
    property var backend
    // R400: the plan's frame of the last drawing, so that a rectangle dragged on it is a zone of the model
    property var frame: null
    property point dragFrom: Qt.point(-1, -1)
    property point dragTo: Qt.point(-1, -1)
    function planOf(p) { return frame ? [frame.xmin+(p.x-frame.ox)/frame.k, frame.ymin+(height-frame.oy-p.y)/frame.k] : [0, 0] }
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Connections { target: root.backend; function onChanged() { root.requestPaint() } }
    Connections { target: Theme; function onColorsChanged() { root.requestPaint() } }
    onPaint: {
        const c = getContext("2d")
        c.reset()
        if (!backend) return
        const rings = backend.state.ifcDrawing || []
        if (!rings.length) return
        const points = [].concat.apply([], rings.filter(r => r.kind !== "roof" && r.kind !== "zone").map(r => r.ring)).concat([[0, 0]])
        const xs = points.map(p => p[0]), ys = points.map(p => p[1])
        const xmin = Math.min(...xs), ymin = Math.min(...ys)
        const w = Math.max(...xs)-xmin || 1, h = Math.max(...ys)-ymin || 1
        const k = Math.min((width-2*Theme.space.XL)/w, (height-2*Theme.space.XL)/h)
        const ox = (width-w*k)/2, oy = (height-h*k)/2
        root.frame = { xmin: xmin, ymin: ymin, k: k, ox: ox, oy: oy }
        function x(p) { return ox+(p[0]-xmin)*k }
        function y(p) { return height-oy-(p[1]-ymin)*k }
        for (const row of rings) {
            c.globalAlpha = ["roof", "exclusion"].includes(row.kind) ? 0.45 : row.kind === "left" ? 0.2 : 1
            c.strokeStyle = row.kind === "support" || row.kind === "zone" ? Theme.colors.accent : Theme.colors.text
            c.lineWidth = row.kind === "building" || row.kind === "support" ? 1.6 : row.kind === "exclusion" ? 1.2 : 1
            c.setLineDash(row.kind === "support" || row.kind === "zone" ? [4, 2] : [])
            c.beginPath()
            row.ring.forEach((p, i) => { if (i) c.lineTo(x(p), y(p)); else c.moveTo(x(p), y(p)) })
            c.closePath(); c.stroke()
        }
        c.globalAlpha = 1; c.lineWidth = 1; c.setLineDash([]); c.strokeStyle = Theme.colors.text
        const cx = x([0, 0]), cy = y([0, 0])
        c.beginPath(); c.moveTo(cx-6,cy); c.lineTo(cx+6,cy); c.moveTo(cx,cy-6); c.lineTo(cx,cy+6); c.stroke()
        if (dragFrom.x >= 0) {
            c.strokeStyle = Theme.colors.accent; c.setLineDash([4, 2])
            c.strokeRect(Math.min(dragFrom.x, dragTo.x), Math.min(dragFrom.y, dragTo.y),
                         Math.abs(dragTo.x-dragFrom.x), Math.abs(dragTo.y-dragFrom.y))
        }
    }
    // a rectangle dragged on the preview: the zone of the model that comes in (only when the model has solids)
    MouseArea {
        anchors.fill: parent
        objectName: "ifcZoneArea"
        enabled: !!(root.backend && root.backend.state.solids !== undefined && root.backend.state.solids !== null)
        cursorShape: enabled ? Qt.CrossCursor : Qt.ArrowCursor
        onPressed: (e) => { root.dragFrom = Qt.point(e.x, e.y); root.dragTo = root.dragFrom }
        onPositionChanged: (e) => { root.dragTo = Qt.point(e.x, e.y); root.requestPaint() }
        onReleased: (e) => {
            const a = root.planOf(root.dragFrom), b = root.planOf(Qt.point(e.x, e.y))
            const big = Math.abs(e.x-root.dragFrom.x) > 4 && Math.abs(e.y-root.dragFrom.y) > 4
            root.dragFrom = Qt.point(-1, -1)
            root.backend.setValue("zoneBox", big ? [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])] : null)
        }
    }
}
