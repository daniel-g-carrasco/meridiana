import QtQuick
import Meridiana.Theme

// F5 (r23-f5): one check mark for the whole program. Without a level it is the tick of the boxes and the menus
// (partial: the stop sign). With a level (fail, warn, info, ok) it is the symbol of a check (it was Checks/CheckMark):
// drawn by the icon provider at the pixels it covers (R464, symbols.paint, never a data-URL SVG scaled by the scene
// graph), its sign white; on the views (the 3D) with the thin white edge of the views' marks (symbols.paint_view, the
// same as the plan's PlanSymbol), with the count over it when the same place has more than one.
Icon {
    id: root
    property bool partial: false
    property string level: ""
    property int count: 1
    property bool views: false
    // kept for the callers of the checks: the symbols come from the icon provider
    property var symbols: null
    readonly property bool levelMark: level !== ""
    name: levelMark ? (views ? "mark:" : "symbol:") + level : partial ? "sign:stop" : "sign:check"
    color: levelMark ? "black" : enabled ? Theme.colors.text : Theme.disabledText
    dimDisabled: !levelMark
    implicitWidth: levelMark ? (views ? ControlMetrics.viewMark : 18) : Theme.icon.CONTROL
    CountBadge {
        visible: root.levelMark && root.count > 1
        x: root.width * .725
        y: -height / 4
        count: root.count
    }
}
