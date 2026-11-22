import QtQuick
import QtQuick.Shapes
import QtQuick.Window
import Meridiana.Theme

// The shared path style, also used inside batched Shapes (no Item per segment).
ShapePath {
    property bool dashed: false
    property real viewScale: 1
    property bool halo: false
    property color ink: Theme.colors.overlay.pill_ink
    property Item surface: null
    // Software cosmetic pens use physical pixels; CurveRenderer uses logical pixels.
    readonly property bool software: surface && surface.GraphicsInfo.api === GraphicsInfo.Software
    readonly property real pixelRatio: software ? surface.Screen.devicePixelRatio : 1
    // CurveRenderer keeps the pen cosmetic, but still transforms its dash distances. GeometryRenderer does not:
    // its dashes are already on the screen's scale, and divided again by the view's they were dashes of a
    // fraction of a pixel, as many as the zoom squared (seconds to build near the modules, R706).
    readonly property bool screenDashes: software || (surface && surface.preferredRendererType === Shape.GeometryRenderer)
    readonly property real dashScale: screenDashes ? 1 : Math.max(.00002, Math.abs(viewScale))
    // R706: above 0, the pen is in the item's own units, as wide on screen as the drawing's line at this scale of
    // the item. A cosmetic pen (0, the rule) is as wide at every scale, but the curve renderer builds the whole
    // path again whenever the scale passes a step: 100 ms for 2000 modules at each step of a zoom. The layers of
    // the modules and of the strings give the scale they were last built for, and change it in steps.
    property real worldScale: 0
    readonly property bool world: worldScale > 0 && !software
    // the drawing's line, or another width of the theme's (the strings' dots: POINT)
    property real pen: Theme.annotation.STROKE
    readonly property real inkWidth: (pen + (halo ? Theme.annotation.HALO_EXTRA : 0)) * pixelRatio
    strokeWidth: world ? inkWidth / worldScale : inkWidth
    strokeColor: halo ? Qt.rgba(0, 0, 0, ink.a > 0 ? Theme.annotation.HALO_ALPHA : 0) : ink
    fillColor: "transparent"
    cosmeticStroke: !world
    capStyle: dashed ? ShapePath.FlatCap : ShapePath.RoundCap
    joinStyle: ShapePath.RoundJoin
    strokeStyle: dashed ? ShapePath.DashLine : ShapePath.SolidLine
    // Only a dashed path follows the scale: a new pattern makes Qt build the stroke again, and on a solid path
    // that was every module's outline built again at each settled zoom (R706).
    // (a pattern counts in pen widths: a pen in the item's units already carries the scale)
    dashPattern: !dashed ? [Theme.annotation.DASH_ON, Theme.annotation.DASH_OFF]
                 : world ? [Theme.annotation.DASH_ON / inkWidth, Theme.annotation.DASH_OFF / inkWidth]
                 : [Theme.annotation.DASH_ON * pixelRatio / (strokeWidth * dashScale),
                    Theme.annotation.DASH_OFF * pixelRatio / (strokeWidth * dashScale)]
}
