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
    readonly property bool failed: modelData.level === "fail"
    // Local view state only. Selecting another inverter restores the default folds.
    property int foldOverride: -1
    // R687 (Daniel 16/11/2026): an error does not keep a card open; the red mark says it, a click opens it
    readonly property bool expanded: renaming || (foldOverride < 0 ? current : foldOverride === 1)
    onCurrentChanged: if (!discMouse.pressed) foldOverride = -1
    function toggle() {
        foldOverride = expanded ? 0 : 1
        if (foldOverride === 1) backend.selectUnit(modelData.number)
    }
    property int dropIndex: -1
    readonly property bool dragging: discMouse.pressed && dropIndex >= 0
    function moveTo(at) {
        if (at < 0 || at >= list.count || at === index) return
        list.focusNumber = at + 1
        backend.moveUnit(modelData.number, at)
    }
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
        moveTo(at)
    }
    activeFocusOnTab: true
    // the card is not a Control: it declares how its focus came, for the one rule of the ring (Theme.focusRing);
    // a press or a tap takes it with the mouse, anything else (Tab, a shortcut, the end of a rename) the keyboard
    property int focusReason: Qt.TabFocusReason
    function takeFocus() { focusReason = Qt.MouseFocusReason; forceActiveFocus(Qt.MouseFocusReason) }
    onActiveFocusChanged: if (!activeFocus) focusReason = Qt.TabFocusReason
    Accessible.role: Accessible.ListItem
    Accessible.name: modelData.accessible || ""
    Keys.onPressed: event => {
        if (event.key === Qt.Key_F2) { rename(); event.accepted = true }
        else if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Up) { nudge(-1); event.accepted = true }
        else if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Down) { nudge(1); event.accepted = true }
    }
    height: header.height + body.height
    radius: Theme.radius.CARD
    color: current ? Theme.colors.select_bg : Theme.colors.field
    border.width: Theme.focusRing(unit) ? Theme.line.FOCUS : 0
    border.color: Theme.colors.focus
    HoverHandler { id: cardHover; cursorShape: Qt.PointingHandCursor }
    M.ToolTip {
        visible: cardHover.hovered && !disc.hot && !more.hovered
        text: (unit.modelData.tip || "") + "\n" + qsTr("Click the heading to expand or collapse. Counts: strings / used inputs.")
    }
    TapHandler { onTapped: { unit.takeFocus(); unit.backend.selectUnit(unit.modelData.number) } onDoubleTapped: unit.rename() }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: menu.popup() }

    Item {
        id: header
        objectName: "inverter-header-" + unit.modelData.number
        width: parent.width
        height: Math.max(Theme.size.CONTROL, Math.ceil(Theme.measureText("Hg", "body").height)) + 2 * Theme.space.S
        Accessible.role: Accessible.Button
        Accessible.name: unit.modelData.accessible || ""
        Accessible.expandable: true
        Accessible.expanded: unit.expanded
        TapHandler { onTapped: { unit.takeFocus(); unit.toggle() } onDoubleTapped: unit.rename() }
        M.CopyLabel {
            x: disc.x + disc.width + Theme.space.S; width: compact.x - Theme.space.S - x
            height: parent.height; text: unit.modelData.name; textStyle: "strong"; elide: Text.ElideRight
            visible: !unit.renaming
        }
        M.Label {
            id: compact
            x: stateMark.x - width - Theme.space.S; height: parent.height
            width: unit.expanded ? 0 : implicitWidth
            visible: !unit.expanded
            text: unit.modelData.power + " kW · " + unit.modelData.strings + "/" + (unit.modelData.usedInputs || 0)
            textStyle: "caption"
        }
        M.CheckMark {
            id: stateMark
            x: fold.x - width - Theme.space.XS; y: (parent.height-height)/2
            width: Theme.icon.CONTROL; height: width
            level: unit.modelData.level === "check" ? "warn" : unit.modelData.level || "info"
        }
        M.Chevron {
            id: fold; x: more.x - width; y: (parent.height-height)/2
            progress: body.progress
        }
    }

    Rectangle {
        objectName: "inverter-drop-preview-" + unit.modelData.number
        visible: unit.dragging && unit.dropIndex !== unit.index
        z: 10
        x: 0; width: unit.width; height: Theme.line.FOCUS
        y: {
            const target = unit.dropIndex >= 0 ? unit.list.itemAt(unit.dropIndex) : null
            return target ? target.y - unit.y + (unit.dropIndex > unit.index ? target.height : 0) : 0
        }
        color: Theme.colors.accent
    }

    // The disc: the handle of the card, under the pointer the number gives way to the dots of a grip.
    Item {
        id: disc
        x: Theme.space.M; y: (header.height-height)/2; width: Theme.size.CONTROL; height: Theme.size.CONTROL
        readonly property bool hot: discMouse.containsMouse
        Rectangle {
            x: 1; y: 1; width: parent.width - 2; height: width; radius: width / 2
            color: unit.current ? Theme.colors.accent : Theme.colors.line_soft
        }
        M.CopyLabel { anchors.centerIn: parent; visible: !disc.hot; text: String(unit.modelData.number); textStyle: "caption"; font.weight: Theme.text.strong.weight
            color: unit.current ? Theme.colors.accent_fg : Theme.colors.text }
        M.Icon {
            anchors.centerIn: parent; visible: disc.hot
            name: "control:grip"
            color: unit.current ? Theme.colors.accent_fg : Theme.colors.text
        }
        MouseArea {
            id: discMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            // The panel scrolls around the cards, but must not steal a handle's press.
            preventStealing: true
            property point start
            onPressed: mouse => { start = mapToItem(unit.parent, mouse.x, mouse.y); unit.takeFocus() }
            onPositionChanged: mouse => {
                if (!pressed) return
                const end = mapToItem(unit.parent, mouse.x, mouse.y)
                if (Math.abs(end.y - start.y) < 10) return
                unit.dropIndex = -1
                for (let i = 0; i < unit.list.count; i++) {
                    const other = unit.list.itemAt(i)
                    if (end.y >= other.y && end.y < other.y + other.height) { unit.dropIndex = i; break }
                }
            }
            onReleased: {
                const at = unit.dropIndex
                unit.dropIndex = -1
                unit.backend.selectUnit(unit.modelData.number)
                unit.moveTo(at)
            }
            onCanceled: unit.dropIndex = -1
        }
        M.ToolTip { pressed: discMouse.pressed; visible: discMouse.containsMouse; text: qsTr("Drag to change the order of the inverters (Alt+Up and Alt+Down too). The number is the inverter's place: the strings are named after it.") }
    }

    M.FoldBody {
        id: body
        y: header.height; width: parent.width
        expanded: unit.expanded
        contentHeight: column.implicitHeight + Theme.space.M
    Column {
        id: column
        x: disc.x + disc.width + Theme.space.M
        width: more.x - Theme.space.M - x
        spacing: Theme.space.XXS
        M.TextField {
            id: nameEdit; objectName: "inverter-name-" + unit.modelData.number; width: parent.width; visible: unit.renaming
            placeholderText: qsTr("Name of the inverter")
            onCommitRequested: unit.saveName()
            Keys.onEscapePressed: { text = unit.modelData.name; unit.saveName() }
        }
        Repeater {
            model: unit.modelData.lines || []
            M.ReadableText { required property string modelData; width: parent.width; visible: text !== ""; text: modelData; wrapMode: Text.Wrap; textStyle: "secondary" }
        }
        // The power optimizers of an inverter at a fixed string voltage: which, how many modules on each.
        Column {
            visible: unit.modelData.optimized === true
            width: parent.width; spacing: Theme.space.XXS
            M.ReadableText { width: parent.width; text: unit.modelData.optimizerText || ""; wrapMode: Text.Wrap; textStyle: "secondary"
                HoverHandler { id: optimizerHover }
                M.ToolTip { visible: optimizerHover.hovered; text: unit.modelData.optimizerText || "" } }
            Row {
                spacing: Theme.space.XS
                M.Button { text: qsTr("Optimizers…"); tip: qsTr("Choose the power optimizers of this inverter in the catalogue")
                    onClicked: unit.backend.catalogRequested("optimizers", unit.modelData.entry) }
                M.ComboBox {
                    width: 150; visible: !!unit.modelData.optimizer.model
                    value: unit.modelData.per; enabled: (unit.modelData.optimizer.modules_per_unit || 1) > 1
                    tip: qsTr("Maximum modules on each optimizer. Its model determines series or parallel wiring; edit individual groups from the string menu.")
                    options: [{key: 1, label: qsTr("one module each")}].concat((unit.modelData.optimizer.modules_per_unit || 1) > 1 ? [{key: 2, label: qsTr("two modules each")}] : [])
                    onChosen: value => unit.backend.setOptimizerPer(unit.modelData.entry, value)
                }
                M.Button { visible: !!unit.modelData.optimizer.model; flat: true; iconName: "symbol:back"; width: Theme.size.CONTROL; height: Theme.size.CONTROL; padding: 0
                    tip: qsTr("Back to the optimizers Meridiana proposes for the module")
                    onClicked: unit.backend.setOptimizer(unit.modelData.entry, {}, 1) }
            }
            M.Button {
                objectName: "optimizer-sheet-" + unit.modelData.number
                visible: !!unit.modelData.optimizer.model
                text: qsTr("Optimizer datasheet…")
                onClicked: unit.datasheet(unit.modelData.optimizer)
            }
        }
    }
    }

    M.Button {
        id: more
        x: unit.width - width - Theme.space.S; y: (header.height-height)/2
        width: 27; height: 27; padding: 0; iconName: "ellipsis"; flat: true
        tip: qsTr("Rename, move, datasheet, string, empty, take out")
        Accessible.name: qsTr("Inverter's menu")
        menu: menu                                      // R480: under it, pressed while open
    }
    M.Menu {
        id: menu
        M.TextActions { id: summaryCopy; readOnly: true; wholeText: (unit.modelData.label || unit.modelData.name || "") + "\n" + (unit.modelData.tip || "") }
        onAboutToShow: summaryCopy.begin()
        onClosed: summaryCopy.end()
        M.MenuItem { text: textEditing.labels.whole; enabled: summaryCopy.allowed("copy"); onTriggered: summaryCopy.execute("copy") }
        M.MenuItem { text: qsTr("Rename") + "\tF2"; onTriggered: unit.rename() }
        M.MenuItem { text: qsTr("Move up") + "\tAlt+Up"; enabled: unit.index > 0; onTriggered: unit.nudge(-1) }
        M.MenuItem { text: qsTr("Move down") + "\tAlt+Down"; enabled: unit.index < unit.list.count - 1; onTriggered: unit.nudge(1) }
        M.MenuSeparator { }
        M.MenuItem { text: qsTr("Datasheet…"); onTriggered: unit.datasheet(unit.modelData.record) }
        M.MenuItem { text: qsTr("String this inverter…"); onTriggered: { unit.backend.selectUnit(unit.modelData.number); unit.actions.proposalForUnit(unit.modelData.number) } }
        M.MenuItem { text: qsTr("Empty its strings"); onTriggered: unit.backend.emptyUnit(unit.modelData.number) }
        M.MenuSeparator { }
        M.MenuItem { text: qsTr("Take out of the plant"); onTriggered: unit.backend.removeUnit(unit.modelData.number, false) }
    }
}
