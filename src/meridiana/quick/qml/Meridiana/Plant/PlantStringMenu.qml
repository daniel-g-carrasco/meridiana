import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// What every menu of a string has (ui/window._string_actions): reversed, drawn again, its optimizers, moved to another
// input, deleted. `open` it for an index: the string is brought into view first, as the window does.
M.Menu {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var strings: backend.strings
    readonly property var inputs: backend.inputs
    required property var actions
    property int index: -1
    readonly property var info: root.strings[index] || ({})
    readonly property string name: info.label || ""
    function popupFor(string, target, x, y) {
        index = string
        backend.selectString(string)
        if (target !== undefined) popup(target, x, y)
        else popup()
    }
    M.MenuItem { text: root.backend.tr("Reverse string {name}").replace("{name}", root.name); onTriggered: root.backend.reverseString(root.index) }
    M.MenuItem { text: root.backend.tr("Draw string {name} again (double click)").replace("{name}", root.name)
        onTriggered: root.backend.draw(root.info.inverter, root.info.mppt, root.index) }
    M.MenuItem { text: root.backend.tr("Modules on each optimizer…"); enabled: !!root.info.optimized; height: enabled ? implicitHeight : 0; visible: enabled
        onTriggered: root.actions.groups(root.index) }
    M.Menu {
        title: root.backend.tr("Move string {name} to").replace("{name}", root.name)
        Instantiator {
            model: root.inputs
            delegate: M.MenuItem {
                required property var modelData
                text: modelData.place
                enabled: !(root.info.inverter === modelData.unit && root.info.mppt === modelData.mppt)
                onTriggered: root.backend.moveString(root.index, modelData.unit, modelData.mppt)
            }
            onObjectAdded: (at, object) => moves.insertItem(at, object)
            onObjectRemoved: (at, object) => moves.removeItem(object)
        }
        id: moves
    }
    M.MenuSeparator { }
    M.MenuItem { text: root.backend.tr("Delete string {name} (Del)").replace("{name}", root.name); onTriggered: root.backend.deleteString(root.index) }
}
