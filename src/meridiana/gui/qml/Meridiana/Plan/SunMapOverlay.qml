import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// What the sun map writes over the plan (study 45, package 5), in the screen's pixels: under each surface its
// irradiance without the shadows (decision 1; under it as on sheet 7, so that it never hides an obstacle of the roof)
// and «to be updated» while it shows an old map, in the plan's pills; the legend in classes at the bottom left, over
// the scale. The figures under the pointer are in the plan's tooltip of the pointer (Plan.qml, moduleTip). The state
// is the backend's (backend/plan_map.py over app/sun_map.SunMap): this only draws it.
Item {
    id: overlay
    required property var plan
    property var sun: plan.sun
    // where the legend stands on: the scale's top
    property real legendBottom: height
    // the legend is chrome of the plan (Plan.clearOfChrome): its words give way to it
    readonly property alias legend: legend
    anchors.fill: parent
    visible: !!sun && sun.on
    Repeater {
        model: overlay.sun ? overlay.sun.surfaces : null
        // a row is born with the plan, before its figures: its pill (and the box on screen it reads) only once it has
        // words, so that the row's birth costs the window an Item (a pill in every row, with its button and its
        // tooltip, was most of SurfaceModel.insert: 5,6 ms on screen, model A, 14/11/2026)
        delegate: Item {
            id: row
            required property string sid
            required property string label
            required property var ring
            Loader {
                active: row.label !== ""
                sourceComponent: M.Pill {
                    id: tag
                    // the surface's box on the screen, at every move of the view (plan.screen: pan, zoom and turn)
                    readonly property rect box: {
                        const ring = row.ring
                        let x0 = Infinity, x1 = -Infinity, y1 = -Infinity
                        for (let i = 0; i < ring.length; i++) {
                            const p = overlay.plan.screen(ring[i].x, -ring[i].y)
                            x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y)
                        }
                        return ring.length ? Qt.rect(x0, y1, x1 - x0, 0) : Qt.rect(0, 0, 0, 0)
                    }
                    objectName: "sunMapLabel-" + row.sid
                    variant: "view"
                    ground: overlay.plan.backend.planColors.label_bg; ink: overlay.plan.ink
                    // only where the surface on screen is about as wide as its words: a small roof keeps its colours
                    // clear; never under the plan's chrome (R555 (1), D4: Plan.clearOfChrome; the row and its
                    // loader stand at the overlay's origin, so these are the overlay's coordinates)
                    visible: box.width > width / 2 && overlay.plan.clearOfChrome(x, y, width, height)
                    width: Math.ceil(words.implicitWidth) + 2 * pad
                    height: Math.max(implicitHeight, Math.ceil(words.implicitHeight) + 2 * Theme.space.XS)
                    x: Math.round(box.x + box.width / 2 - width / 2); y: Math.round(box.y + Theme.space.S)
                    M.CopyLabel {
                        id: words
                        anchors.centerIn: parent
                        text: row.label; color: tag.ink; font: tag.font
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
    M.MapLegend {
        id: legend
        objectName: "sunMapLegend"
        readonly property var data: overlay.sun ? overlay.sun.legend : ({})
        visible: !!data.visible
        x: Theme.space.M; y: overlay.legendBottom - height - Theme.space.S
        title: data.title || ""
        limits: data.limits || []
        notes: data.notes || []
        colors: (data.tones || []).map(t => Theme.colors.sun_map[data.scale + "_" + t])
    }
}
