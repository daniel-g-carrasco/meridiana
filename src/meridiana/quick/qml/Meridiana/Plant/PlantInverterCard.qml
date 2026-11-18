import QtQuick
import QtQuick.Layouts
import Meridiana.Controls as M
import Meridiana.Theme

// ui/plant_page.InverterCard (R297, study 23, A2): its disc with the number as the handle, its name (F2 or a double
// click to rename, the menu too), the model, its strings, the first reason to look at; the menu «⋯» at the right. The
// card of the inverter the Strings show is filled as a row chosen (R340). The optimizers on their row (task 22).
Rectangle {
    id: unit
    objectName: "inverter-card-" + modelData.number
    required property var modelData
    required property int index
    required property var backend
    required property var actions
    required property var list
    signal datasheet(var record)
    readonly property bool current: backend.working === modelData.number
    property bool renaming: false
    function rename() { renaming = true; nameEdit.text = modelData.name; nameEdit.forceActiveFocus(); nameEdit.selectAll() }
    function saveName() {
        if (!renaming) return
        renaming = false
        unit.forceActiveFocus()
        const text = nameEdit.text.trim()
        if (text && text !== modelData.name) backend.renameUnit(modelData.number, text)
    }
    function nudge(by) {
        const at = index + by
        if (at >= 0 && at < list.count) backend.moveUnit(modelData.number, at)
    }
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: modelData.accessible || ""
    Keys.onPressed: event => {
        if (event.key === Qt.Key_F2) { rename(); event.accepted = true }
        else if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Up) { nudge(-1); event.accepted = true }
        else if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Down) { nudge(1); event.accepted = true }
    }
    height: column.implicitHeight + 2 * Theme.space.M
    radius: Theme.radius.CARD
    color: current ? Theme.colors.select_bg : Theme.colors.field
    border.width: current ? Theme.line.HAIR : 0
    border.color: Theme.colors.accent
    HoverHandler { id: cardHover; cursorShape: Qt.PointingHandCursor }
    M.ToolTip { visible: cardHover.hovered && !disc.hot && !more.hovered; text: unit.modelData.tip || "" }
    TapHandler { onTapped: { unit.forceActiveFocus(); unit.backend.selectUnit(unit.modelData.number) } onDoubleTapped: unit.rename() }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: menu.popup() }

    // The disc: the handle of the card, under the pointer the number gives way to the dots of a grip.
    Item {
        id: disc
        x: Theme.space.M; y: Theme.space.M; width: Theme.size.CONTROL; height: Theme.size.CONTROL
        readonly property bool hot: discMouse.containsMouse
        Rectangle {
            x: 1; y: 1; width: parent.width - 2; height: width; radius: width / 2
            color: unit.current ? Theme.colors.accent : Theme.colors.line_soft
        }
        M.Label { anchors.centerIn: parent; visible: !disc.hot; text: String(unit.modelData.number); textStyle: "caption"; font.weight: Theme.text.strong.weight
            color: unit.current ? Theme.colors.accent_fg : Theme.colors.text }
        Repeater {
            model: 6
            Rectangle {
                required property int index
                visible: disc.hot
                width: 2.4; height: 2.4; radius: 1.2
                x: disc.width / 2 + (index % 2 ? 3 : -3) - 1.2
                y: disc.height / 2 + (Math.floor(index / 2) - 1) * 5 - 1.2
                color: unit.current ? Theme.colors.accent_fg : Theme.colors.text
            }
        }
        MouseArea {
            id: discMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            property point start
            onPressed: mouse => { start = mapToItem(unit.parent, mouse.x, mouse.y); unit.forceActiveFocus(); unit.backend.selectUnit(unit.modelData.number) }
            onReleased: mouse => {
                const end = mapToItem(unit.parent, mouse.x, mouse.y)
                if (Math.abs(end.y - start.y) < 10) return
                for (let i = 0; i < unit.list.count; i++) {
                    const other = unit.list.itemAt(i)
                    if (end.y >= other.y && end.y < other.y + other.height) { unit.backend.moveUnit(unit.modelData.number, i); break }
                }
            }
        }
        M.ToolTip { pressed: discMouse.pressed; visible: discMouse.containsMouse; text: unit.backend.tr("Drag to change the order of the inverters (Alt+Up and Alt+Down too). The number is the inverter's place: the strings are named after it.") }
    }

    Column {
        id: column
        x: disc.x + disc.width + Theme.space.M; y: Theme.space.M
        width: more.x - Theme.space.M - x
        spacing: Theme.space.XXS
        M.Label {
            width: parent.width; visible: !unit.renaming; text: unit.modelData.name; textStyle: "strong"; wrapMode: Text.Wrap
            HoverHandler { id: nameHover }
            M.ToolTip { visible: nameHover.hovered; text: unit.backend.tr("The inverter's name: F2 or a double click to change it") }
        }
        M.TextField {
            id: nameEdit; objectName: "inverter-name-" + unit.modelData.number; width: parent.width; visible: unit.renaming
            placeholderText: unit.backend.tr("Name of the inverter")
            onEditingFinished: unit.saveName()
            Keys.onEscapePressed: { text = unit.modelData.name; unit.saveName() }
        }
        Repeater {
            model: unit.modelData.lines || []
            M.Label { required property string modelData; width: parent.width; visible: text !== ""; text: modelData; wrapMode: Text.Wrap; textStyle: "secondary" }
        }
        // The power optimizers of an inverter at a fixed string voltage: which, how many modules on each.
        Column {
            visible: unit.modelData.optimized === true
            width: parent.width; spacing: Theme.space.XXS
            M.Label { width: parent.width; text: unit.modelData.optimizerText || ""; wrapMode: Text.Wrap; textStyle: "secondary"
                HoverHandler { id: optimizerHover }
                M.ToolTip { visible: optimizerHover.hovered; text: unit.modelData.optimizerText || "" } }
            Row {
                spacing: Theme.space.XS
                M.Button { text: unit.backend.tr("Optimizers…"); tip: unit.backend.tr("Choose the power optimizers of this inverter in the catalogue")
                    onClicked: unit.backend.catalogRequested("optimizers", unit.modelData.entry) }
                M.ComboBox {
                    width: 150; visible: !!unit.modelData.optimizer.model
                    value: unit.modelData.per; enabled: (unit.modelData.optimizer.modules_per_unit || 1) > 1
                    tip: unit.backend.tr("Maximum modules on each optimizer. Its model determines series or parallel wiring; edit individual groups from the string menu.")
                    options: [{key: 1, label: unit.backend.tr("one module each")}].concat((unit.modelData.optimizer.modules_per_unit || 1) > 1 ? [{key: 2, label: unit.backend.tr("two modules each")}] : [])
                    onChosen: value => unit.backend.setOptimizerPer(unit.modelData.entry, value)
                }
                M.Button { visible: !!unit.modelData.optimizer.model; flat: true; iconName: "symbol:back"; width: Theme.size.CONTROL; height: Theme.size.CONTROL; padding: 0
                    tip: unit.backend.tr("Back to the optimizers Meridiana proposes for the module")
                    onClicked: unit.backend.setOptimizer(unit.modelData.entry, {}, 1) }
            }
            M.Button {
                objectName: "optimizer-sheet-" + unit.modelData.number
                visible: !!unit.modelData.optimizer.model
                text: unit.backend.tr("Optimizer datasheet…")
                onClicked: unit.datasheet(unit.modelData.optimizer)
            }
        }
    }

    M.Button {
        id: more
        x: unit.width - width - Theme.space.S; y: Theme.space.M
        width: 27; height: 27; padding: 0; iconName: "ellipsis"; flat: true
        tip: unit.backend.tr("Rename, move, datasheet, string, empty, take out")
        Accessible.name: unit.backend.tr("Inverter's menu")
        menu: menu                                      // R480: under it, pressed while open
    }
    M.Menu {
        id: menu
        M.MenuItem { text: unit.backend.tr("Rename") + "\tF2"; onTriggered: unit.rename() }
        M.MenuItem { text: unit.backend.tr("Move up") + "\tAlt+Up"; enabled: unit.index > 0; onTriggered: unit.nudge(-1) }
        M.MenuItem { text: unit.backend.tr("Move down") + "\tAlt+Down"; enabled: unit.index < unit.list.count - 1; onTriggered: unit.nudge(1) }
        M.MenuSeparator { }
        M.MenuItem { text: unit.backend.tr("Datasheet…"); onTriggered: unit.datasheet(unit.modelData.record) }
        M.MenuItem { text: unit.backend.tr("String this inverter…"); onTriggered: { unit.backend.selectUnit(unit.modelData.number); unit.actions.proposalForUnit(unit.modelData.number) } }
        M.MenuItem { text: unit.backend.tr("Empty its strings"); onTriggered: unit.backend.emptyUnit(unit.modelData.number) }
        M.MenuSeparator { }
        M.MenuItem { text: unit.backend.tr("Take out of the plant"); onTriggered: unit.backend.removeUnit(unit.modelData.number, false) }
    }
}
