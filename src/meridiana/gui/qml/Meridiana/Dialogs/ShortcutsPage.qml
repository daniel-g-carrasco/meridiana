import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: root
    property var backend
    property string selected: ""
    spacing: Theme.space.S
    M.TextField {
        id: filter; objectName: "dialogShortcutSearch"
        Layout.fillWidth: true; placeholderText: root.backend.labels.shortcutsSearch
    }
    // R555: the one table (M.Table), in its own outline, with the commands found by the filter
    readonly property var shown: (root.backend && root.backend.kind === "shortcuts" ? root.backend.state.shortcuts : []).filter(row => !filter.text || (row.label + " " + row.keys + " " + row.defaults).toLowerCase().includes(filter.text.toLowerCase()))
    M.Table {
        id: rows
        objectName: "dialogShortcutTable"
        Layout.fillWidth: true; Layout.fillHeight: true
        // its heading and three rows at the least: in a low window the list gives way, not the fields
        Layout.minimumHeight: 4 * rowHeight
        framed: true; rowHeight: Theme.size.COMPACT; selectOnPress: false; cacheBuffer: 0
        columns: [{key: "label", title: root.backend.labels.command, weight: 2},
                  {key: "keys", title: root.backend.labels.keys, weight: 1},
                  {key: "defaults", title: root.backend.labels.defaults, weight: 1}]
        model: root.shown
        onRowActivated: index => { root.selected = root.shown[index].id; capture.clear() }
        Binding on currentIndex { value: root.shown.findIndex(row => row.id === root.selected) }
    }
    RowLayout {
        Layout.fillWidth: true
        M.CopyLabel { text: root.backend.labels.newKeys }
        M.TextField {
            textKeysEnabled: false
            id: capture; objectName: "dialogShortcutCapture"
            Layout.fillWidth: true; enabled: root.selected !== ""
            Keys.onPressed: event => {
                if ([Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta].includes(event.key)) return
                text = root.backend.captureKey(event.key, event.modifiers); event.accepted = true
            }
        }
        M.Button { text: root.backend.labels.use; enabled: root.selected !== "" && capture.text !== ""; onClicked: root.backend.assignShortcut(root.selected, capture.text) }
        M.Button { text: root.backend.labels.none; enabled: root.selected !== ""; onClicked: root.backend.assignShortcut(root.selected, "") }
        M.Button { text: root.backend.labels.defaults; enabled: root.selected !== ""; onClicked: root.backend.resetShortcut(root.selected) }
    }
    M.ReadableText {
        Layout.fillWidth: true; wrapMode: Text.WordWrap
        text: root.selected && capture.text ? root.backend.shortcutVerdict(root.selected, capture.text) : ""
    }
    RowLayout {
        Layout.fillWidth: true; Layout.topMargin: Theme.space.L
        M.ReadableText { Layout.fillWidth: true; text: root.backend.labels.keyboardNote; wrapMode: Text.WordWrap }
        M.Button { text: root.backend.labels.allDefaults; onClicked: root.backend.resetShortcut("") }
    }
}
