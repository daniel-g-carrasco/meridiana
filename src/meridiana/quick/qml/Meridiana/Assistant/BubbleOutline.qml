import QtQuick
import QtQuick.Shapes
import Meridiana.Theme

// ui.assistant.outline: one closed contour, including the tail (R293).
Shape {
    id: root
    property string tail: ""
    property real at: 23
    property real cornerRadius: 10
    readonly property real leftEdge: 0.5 + (tail === "left" ? 12 : 0)
    readonly property real rightEdge: width - 0.5 - (tail === "right" ? 12 : 0)
    readonly property real topEdge: 0.5 + (tail === "top" ? 12 : 0)
    readonly property real bottomEdge: height - 0.5 - (tail === "bottom" ? 12 : 0)
    function outline() {
        const l = leftEdge, r = rightEdge, t = topEdge, b = bottomEdge, c = cornerRadius
        const a = Math.max(23, Math.min(at, (tail === "left" || tail === "right" ? height : width) - 23))
        let d = "M " + (l+c) + " " + t
        if (tail === "top") d += " L " + (a-11) + " " + t + " L " + a + " " + (t-12) + " L " + (a+11) + " " + t
        d += " L " + (r-c) + " " + t + " A " + c + " " + c + " 0 0 1 " + r + " " + (t+c)
        if (tail === "right") d += " L " + r + " " + (a-11) + " L " + (r+12) + " " + a + " L " + r + " " + (a+11)
        d += " L " + r + " " + (b-c) + " A " + c + " " + c + " 0 0 1 " + (r-c) + " " + b
        if (tail === "bottom") d += " L " + (a+11) + " " + b + " L " + a + " " + (b+12) + " L " + (a-11) + " " + b
        d += " L " + (l+c) + " " + b + " A " + c + " " + c + " 0 0 1 " + l + " " + (b-c)
        if (tail === "left") d += " L " + l + " " + (a+11) + " L " + (l-12) + " " + a + " L " + l + " " + (a-11)
        return d + " L " + l + " " + (t+c) + " A " + c + " " + c + " 0 0 1 " + (l+c) + " " + t + " Z"
    }
    preferredRendererType: Shape.CurveRenderer
    ShapePath {
        strokeColor: Theme.colors.line; strokeWidth: 1
        fillColor: Theme.colors.panel
        joinStyle: ShapePath.MiterJoin
        PathSvg { path: root.outline() }
    }
}
