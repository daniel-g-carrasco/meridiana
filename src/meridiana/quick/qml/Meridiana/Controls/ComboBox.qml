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
    topPadding: Theme.space.XS
    bottomPadding: Theme.space.XS
    wheelEnabled: !hasOptions && activeFocus
    WheelHandler { enabled: root.hasOptions && root.activeFocus && !root.popup.visible
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
    contentItem: Label { text: root.displayText; enabled: root.enabled; elide: Text.ElideRight }
    indicator: Icon { name: "field:open"; width: 9; height: 7; color: Theme.colors.muted; x: root.width - Theme.size.COMPACT/2 - width/2; y: (root.height-height)/2 }
    background: Rectangle { radius: Theme.radius.CONTROL; color: Theme.colors.field
        border.width: root.activeFocus ? Theme.line.FOCUS : Theme.line.HAIR
        border.color: !root.enabled ? "transparent" : root.activeFocus ? Theme.colors.accent : root.hovered ? Theme.colors.field_line : "transparent"
    }
    ToolTip { parent: root; visible: root.hovered && root.tip !== "" && !root.popup.visible; text: root.tip }
    // R525: the entry of every menu, as it is (its hover, its radius, its height); the current choice is its check
    delegate: MenuItem { required property int index; width: ListView.view ? ListView.view.width : root.width
        checkable: true; checked: index === root.currentIndex
        text: root.textAt(index); highlighted: root.enabled && root.highlightedIndex === index }
    // the entries shown: the indexes of the model (of `options`, only the ones whose label holds the search when there
    // is one). The list never takes the ComboBox's delegateModel: a delegate set on it from the list would be the
    // ComboBox's, and a null one leaves the ComboBox without entries (count 0).
    readonly property var shownIndexes: {
        if (!hasOptions) return Array.from({length: root.count}, (_, i) => i)
        const needle = searchable ? search.text.toLocaleLowerCase() : ""
        const out = []
        for (let i = 0; i < options.length; i++)
            if (!needle || String(options[i].label).toLocaleLowerCase().indexOf(needle) >= 0) out.push(i)
        return out
    }
    readonly property real naturalWidth: {
        const revision = Theme.revision
        let wanted = root.width
        if (hasOptions) { for (const option of options) wanted = Math.max(wanted, Theme.measureText(option.label).width + Theme.space.XXL + Theme.space.XL) }
        else wanted = Math.max(wanted, root.implicitContentWidth + 2 * root.padding)
        return wanted
    }
    popup: Popup {
        id: list
        enabled: root.enabled
        width: Math.min(root.naturalWidth, ControlMetrics.menuWide, root.Window.window ? root.Window.window.width - 2 * margins : ControlMetrics.menuWide)
        height: Math.min(ControlMetrics.menuTall, choices.contentHeight + (search.visible ? search.height + Theme.space.S : 0) + topPadding + bottomPadding)
        onOpened: {
            search.text = ""
            choices.currentIndex = root.hasOptions ? root.shownIndexes.indexOf(root.indexOfOption(root.value)) : root.highlightedIndex
            if (choices.currentIndex >= 0) choices.positionViewAtIndex(choices.currentIndex, ListView.Contain)
            if (root.searchable) search.forceActiveFocus(); else if (root.hasOptions) choices.forceActiveFocus()
        }
        contentItem: Column {
            spacing: Theme.space.S
            TextField { id: search; width: parent.width; height: visible ? implicitHeight : 0; visible: root.searchable
                placeholderText: root.searchHint
                Keys.onDownPressed: { choices.forceActiveFocus(); choices.currentIndex = 0 }
                onAccepted: if (choices.count === 1) choices.pickRow(0)
            }
            ListView {
                id: choices
                width: parent.width
                height: list.availableHeight - (search.visible ? search.height + Theme.space.S : 0)
                clip: true; highlightMoveDuration: 0; keyNavigationEnabled: root.hasOptions
                model: root.shownIndexes
                currentIndex: -1
                function pickRow(row) {
                    if (row < 0 || row >= root.shownIndexes.length) return
                    const option = root.options[root.shownIndexes[row]]
                    if (root.isEnabled(option)) root.pick(root.valueOf(option))
                }
                delegate: optionEntry
                Keys.onReturnPressed: pickRow(currentIndex)
                T.ScrollBar.vertical: ScrollBar { fades: false; visible: size < 1 }
            }
        }
        Component { id: optionEntry
            MenuItem { required property int modelData; required property int index
                readonly property var option: root.hasOptions ? root.options[modelData] : null
                width: ListView.view ? ListView.view.width : list.availableWidth
                text: option ? option.label : root.textAt(modelData); enabled: !option || root.isEnabled(option)
                checkable: true; checked: modelData === root.currentIndex
                highlighted: root.hasOptions ? choices.activeFocus && choices.currentIndex === index : root.highlightedIndex === modelData
                onClicked: { if (option) root.pick(root.valueOf(option)); else { root.currentIndex = modelData; root.activated(modelData); list.close() } } }
        }
    }
}
