import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// The summary of the Plant at the right of its bar, or above the plan when the bar has no room (R419): the modules and
// the inverters, and in a place of its own what is selected. Nothing moves when the selection changes: the place is
// kept empty with nothing selected. Narrow, the inverters, then the modules, give their place to the selection while
// there is one; the tooltip of a column says all of it.
Item {
    id: root
    objectName: "plant-strip"
    readonly property var totals: plantSummary.totals
    readonly property var chosen: plantSummary.selection
    readonly property real unit: Theme.type.BODY / 13
    readonly property bool wide: width >= 590 * unit
    readonly property bool two: width >= 300 * unit
    M.InfoGroup {
        objectName: "plant-summary"
        anchors.fill: parent
        shares: root.wide ? [.3, .42, .28] : root.two ? [.5, .5] : [1]
        columns: !root.totals.length ? [] : root.wide ? [root.totals[0], root.totals[1], root.chosen]
            : root.two ? [root.totals[0], root.chosen.key ? root.chosen : root.totals[1]]
            : [root.chosen.key ? root.chosen : root.totals[0]]
    }
}
