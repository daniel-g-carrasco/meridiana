import QtQuick
import Meridiana.Theme

// The legend of a map in classes (study 45, package 5: the sun map of the plan, the 3D's to come): its title with the
// unit, one swatch per class side by side, each limit under the edge it belongs to, and one or two lines of notes
// («plane of the pitch», «plane of the modules»). Over a view, on the plan's legend glass with the overlay's ink, as the
// plan's other signs. The colours come from the caller, out of Theme (Theme.colors.sun_map for the sun map): the
// component draws them, it does not choose them. Clicks pass through to the view under it.
Rectangle {
    id: root
    property string title: ""
    property var colors: []             // one per class, in the order of the limits
    property var limits: []             // one more than the colours: the edges of the classes, already worded
    property var notes: []
    // the classes the items are made for with the legend, before any figure comes: the first legend shown changes
    // their words and colours and makes none (made on the map's first figures they held the window's thread 5,5-6,8 ms,
    // sun_map.legend, 14/11/2026); more classes than these are made when they come
    property int slots: 6
    readonly property real swatch: Theme.size.SWATCH
    readonly property real bandWidth: colors.length * swatch
    radius: Theme.radius.INNER
    color: Theme.colors.overlay.glass
    implicitWidth: Math.max(heading.implicitWidth, bandWidth + limitRoom, noteColumn.implicitWidth) + 2 * Theme.space.M
    implicitHeight: column.implicitHeight + 2 * Theme.space.S
    width: implicitWidth; height: implicitHeight
    // the first and the last limit stand half outside the band: room for them
    readonly property real limitRoom: limits.length ? Math.max(first.implicitWidth, last.implicitWidth) : 0
    CopyLabel { id: first; visible: false; textStyle: "caption"; text: root.limits.length ? root.limits[0] : "" }
    CopyLabel { id: last; visible: false; textStyle: "caption"; text: root.limits.length ? root.limits[root.limits.length - 1] : "" }
    Column {
        id: column
        x: Theme.space.M; y: Theme.space.S
        spacing: Theme.space.XS
        CopyLabel { id: heading; objectName: "mapLegendTitle"; text: root.title; textStyle: "strong"; color: Theme.colors.overlay.white }
        Item {
            objectName: "mapLegendBand"
            width: root.bandWidth + root.limitRoom
            height: Theme.space.L + Theme.space.XXS + ticks.implicitHeight
            Row {
                x: root.limitRoom / 2
                // by count, not by the list: new limits or shades as the figures come change the words and the
                // colours, the items stay (with the list as model every change made them all again: 4,5-5,3 ms of
                // the window's thread on screen, model A, 14/11/2026)
                Repeater {
                    model: Math.max(root.slots, root.colors.length)
                    Rectangle {
                        required property int index
                        visible: index < root.colors.length
                        objectName: "mapLegendSwatch-" + index
                        width: root.swatch; height: Theme.space.L
                        color: root.colors[index] || "transparent"
                        border.width: Theme.line.HAIR; border.color: Theme.colors.overlay.legend_line
                    }
                }
            }
            CopyLabel {
                id: ticks; visible: false; textStyle: "caption"; text: "0"
            }
            Repeater {
                model: Math.max(root.slots + 1, root.limits.length)
                CopyLabel {
                    required property int index
                    visible: index < root.limits.length
                    objectName: "mapLegendLimit-" + index
                    text: root.limits[index] || ""; textStyle: "caption"; color: Theme.colors.overlay.ink
                    x: root.limitRoom / 2 + index * root.swatch - implicitWidth / 2
                    y: Theme.space.L + Theme.space.XXS
                }
            }
        }
        Column {
            id: noteColumn
            spacing: Theme.space.XXS
            Repeater {
                model: Math.max(2, root.notes.length)
                CopyLabel { required property int index; visible: index < root.notes.length; text: root.notes[index] || ""; textStyle: "caption"; color: Theme.colors.overlay.ink }
            }
        }
    }
}
