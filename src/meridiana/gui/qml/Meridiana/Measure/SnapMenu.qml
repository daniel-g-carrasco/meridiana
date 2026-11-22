import QtQuick
import Meridiana.Controls as M

// The snaps' menu of the measuring tool (Daniel's choice 2, as in AutoCAD: Shift + right button while a point is being
// placed): vertex, midpoint, edge, intersection, perpendicular, none. The choice holds for the point being placed, then
// the snaps are all back (app/view/measure_tool.py set_snap). The program's menu (M.Menu) with the common entries
// (M.MenuEntry), the same in the plan (Plan/Plan.qml) and in the 3D view (View3D/Viewport.qml); the snap asked is
// checked. `measure` is the window's MeasureBridge; the host opens it with popup(x, y) and takes the focus back when
// it closes.
M.Menu {
    id: menu
    objectName: "measureSnapMenu"
    property var measure: null
    Instantiator {
        model: menu.measure ? menu.measure.snapChoices : []
        delegate: M.MenuEntry {
            required property var modelData
            objectName: modelData.separator ? "measureSnapRule" : "measureSnap-" + modelData.kind
            entry: modelData
            checked: !!menu.measure && menu.measure.snap === modelData.kind
            onTriggered: menu.measure.setSnap(modelData.kind)
        }
        onObjectAdded: function(index, object) { menu.insertItem(index, object) }
        onObjectRemoved: function(index, object) { menu.removeItem(object) }
    }
}
