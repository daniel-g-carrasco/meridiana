import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme

// R598: the list of M.ComboBox (its only user), made at the list's first opening and then kept: in a file of its own
// because Qt makes a ComboBox's deferred `popup` at once when it or one of its children has an id in the ComboBox's
// file. What is here was M.ComboBox's popup as it was, `combo` in place of the ComboBox's `root`.
Popup {
    id: list
    required property T.ComboBox combo
    enabled: combo.enabled
    onVisibleChanged: combo.listShown = visible
    // the entries shown: the indexes of the model (of `options`, only the ones whose label holds the search when
    // there is one). The list never takes the ComboBox's delegateModel: a delegate set on it from the list would be
    // the ComboBox's, and a null one leaves the ComboBox without entries (count 0).
    readonly property var shownIndexes: {
        if (!combo.hasOptions) return Array.from({length: combo.count}, (_, i) => i)
        const needle = combo.searchable ? search.text.toLocaleLowerCase() : ""
        const out = []
        for (let i = 0; i < combo.options.length; i++)
            if (!needle || String(combo.options[i].label).toLocaleLowerCase().indexOf(needle) >= 0) out.push(i)
        return out
    }
    readonly property real naturalWidth: {
        const revision = Theme.revision
        let wanted = combo.width
        if (combo.hasOptions) { for (const option of combo.options) wanted = Math.max(wanted, Theme.measureText(option.label).width + Theme.space.XXL + Theme.space.XL) }
        else wanted = Math.max(wanted, combo.implicitContentWidth + 2 * combo.padding)
        return wanted
    }
    width: Math.min(naturalWidth, ControlMetrics.menuWide, combo.Window.window ? combo.Window.window.width - 2 * margins : ControlMetrics.menuWide)
    height: Math.min(ControlMetrics.menuTall, choices.contentHeight + (search.visible ? search.height + Theme.space.S : 0) + topPadding + bottomPadding)
    onOpened: {
        search.text = ""
        choices.currentIndex = combo.hasOptions ? list.shownIndexes.indexOf(combo.indexOfOption(combo.value)) : combo.highlightedIndex
        if (choices.currentIndex >= 0) choices.positionViewAtIndex(choices.currentIndex, ListView.Contain)
        if (combo.searchable) search.forceActiveFocus(); else if (combo.hasOptions) choices.forceActiveFocus()
    }
    contentItem: Column {
        spacing: Theme.space.S
        TextField { id: search; width: parent.width; height: visible ? implicitHeight : 0; visible: combo.searchable
            placeholderText: combo.searchHint
            Keys.onDownPressed: { choices.forceActiveFocus(); choices.currentIndex = 0 }
            onAccepted: if (choices.count === 1) choices.pickRow(0)
        }
        ListView {
            id: choices
            width: parent.width
            height: list.availableHeight - (search.visible ? search.height + Theme.space.S : 0)
            clip: true; highlightMoveDuration: 0; keyNavigationEnabled: combo.hasOptions
            model: list.shownIndexes
            currentIndex: -1
            function pickRow(row) {
                if (row < 0 || row >= list.shownIndexes.length) return
                const option = combo.options[list.shownIndexes[row]]
                if (combo.isEnabled(option)) combo.pick(combo.valueOf(option))
            }
            delegate: optionEntry
            Keys.onReturnPressed: pickRow(currentIndex)
            T.ScrollBar.vertical: ScrollBar { fades: false; visible: size < 1 }
        }
    }
    Component { id: optionEntry
        MenuItem { required property int modelData; required property int index
            readonly property var option: combo.hasOptions ? combo.options[modelData] : null
            width: ListView.view ? ListView.view.width : list.availableWidth
            text: option ? option.label : combo.textAt(modelData); enabled: !option || combo.isEnabled(option)
            checkable: true; checked: modelData === combo.currentIndex
            highlighted: combo.hasOptions ? choices.activeFocus && choices.currentIndex === index : combo.highlightedIndex === modelData
            onClicked: { if (option) combo.pick(combo.valueOf(option)); else { combo.currentIndex = modelData; combo.activated(modelData); list.close() } } }
    }
}
