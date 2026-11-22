import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme

// R21-F2: the one drop-down of the program (it was five: ComboBox, ResultChoice, PropertyChoice, PlantChoice,
// Selector). Two ways to feed it: Qt's (`model`, `textRole`, `valueRole`, `activated`, `currentValue`) or the pages'
// `options`, a list of {value (or key), label, enabled} with `value` the one chosen and `chosen(value)` when the
// person picks another; `emptyText` is shown when no option has the value (a mixed selection), `searchable` puts a
// search field over the entries (the properties' long lists), `tip` a tooltip. Up and Down step over the enabled
// options, Alt+Down opens, the wheel steps when the control has the focus. The list drops in an M.Popup, its entries
// are M.MenuItem (R525), the current one has its check.
// R598: the list is made at its first opening, then kept. Qt defers a ComboBox's `popup` until something reads it, and
// every form of the Properties and of the results has many drop-downs: nothing here reads `popup` before it opens
// (`listShown` is the list's own word on whether it is up), and the list is a file of its own (ComboList.qml): Qt
// makes a deferred object at once when it or one of its children has an id in this file.
T.ComboBox {
    id: root
    property var options: null
    property var value
    signal chosen(var value)
    property bool searchable: false
    property string searchHint: ""
    property string emptyText: ""
    property string accessibleName: ""
    property string tip: ""
    readonly property bool hasOptions: options !== null && options !== undefined
    function valueOf(option) { return option.value !== undefined ? option.value : option.key }
    function isEnabled(option) { return option.enabled !== false }
    function indexOfOption(wanted) {
        if (!hasOptions) return -1
        for (let i = 0; i < options.length; i++) if (valueOf(options[i]) === wanted) return i
        return -1
    }
    // whether the list is up: told by the list, so that reading it does not make the list
    property bool listShown: false
    function pick(wanted) { chosen(wanted); popup.close() }
    function step(direction) {
        if (!hasOptions) return
        let index = indexOfOption(value)
        for (index += direction; index >= 0 && index < options.length; index += direction)
            if (isEnabled(options[index])) { chosen(valueOf(options[index])); return }
    }
    model: hasOptions ? options : []
    textRole: hasOptions ? "label" : ""
    function follow() { if (hasOptions) currentIndex = indexOfOption(value) }
    onValueChanged: follow()
    onOptionsChanged: follow()
    Component.onCompleted: follow()
    displayText: hasOptions ? (currentIndex >= 0 && currentIndex < options.length ? options[currentIndex].label : emptyText) : currentText
    onActivated: index => { if (hasOptions && index >= 0 && index < options.length) chosen(valueOf(options[index])) }
    Accessible.name: accessibleName !== "" ? accessibleName : displayText
    implicitWidth: Theme.size.READING / 2
    implicitHeight: Math.max(Theme.size.CONTROL, contentItem.implicitHeight + 2 * Theme.space.XS)
    padding: Theme.space.M
    leftPadding: ControlMetrics.fieldInset
    // R582: the chosen label on the middle as a field's text (ControlMetrics.textBaseline)
    FontMetrics { id: metrics; font: root.font }
    topPadding: ControlMetrics.textBaseline(height, metrics, Screen.devicePixelRatio) - metrics.ascent
    bottomPadding: 0
    wheelEnabled: !hasOptions && activeFocus
    WheelHandler { enabled: root.hasOptions && root.activeFocus && !root.listShown
        onWheel: event => { root.step(event.angleDelta.y > 0 ? -1 : 1); event.accepted = true } }
    Keys.onPressed: event => {
        // only the arrows of `options` are ours; every other key goes on to the ComboBox (a handler accepts by default)
        event.accepted = hasOptions && (event.key === Qt.Key_Down || event.key === Qt.Key_Up)
        if (!event.accepted) return
        if (event.modifiers & Qt.AltModifier) popup.open()
        else step(event.key === Qt.Key_Down ? 1 : -1)
        event.accepted = true
    }
    focusPolicy: Qt.StrongFocus
    rightPadding: indicator.width + Theme.space.M * 2
    hoverEnabled: true
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    contentItem: Label { text: root.displayText; enabled: root.enabled; elide: Text.ElideRight; verticalAlignment: Text.AlignTop }
    indicator: Arrow { x: Math.round(root.width - Theme.size.COMPACT/2 - width/2); y: Math.round((root.height-height)/2)     // R592
        active: root.hovered || root.activeFocus || root.listShown }
    background: Rectangle { radius: Theme.radius.CONTROL; color: Theme.colors.field
        border.width: Theme.focusRing(root) ? Theme.line.FOCUS : Theme.line.HAIR
        border.color: !root.enabled ? "transparent" : Theme.focusRing(root) ? Theme.colors.focus : root.hovered ? Theme.colors.field_line : "transparent"
    }
    // R598: made only for a drop-down that has a tip (most have none)
    Loader { active: root.tip !== ""
        sourceComponent: Item { ToolTip { parent: root; visible: root.hovered && root.tip !== "" && !root.listShown; text: root.tip } } }
    // R525: the entry of every menu, as it is (its hover, its radius, its height); the current choice is its check
    delegate: MenuItem { required property int index; width: ListView.view ? ListView.view.width : root.width
        checkable: true; checked: index === root.currentIndex
        text: root.textAt(index); highlighted: root.enabled && root.highlightedIndex === index }
    popup: ComboList { combo: root }
}
