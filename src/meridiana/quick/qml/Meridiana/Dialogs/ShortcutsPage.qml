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
    Rectangle {
        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 220
        color: Theme.colors.card; radius: Theme.radius.CONTROL; border.color: Theme.colors.line
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 1; spacing: 0
            Rectangle {
                Layout.fillWidth: true; implicitHeight: Theme.size.CONTROL
                color: Theme.colors.window
                Row {
                    id: headings
                    anchors.fill: parent
                    Repeater {
                        model: [root.backend.labels.command, root.backend.labels.keys, root.backend.labels.defaults]
                        M.Label {
                            required property string modelData; required property int index
                            width: headings.width * (index === 0 ? 0.5 : 0.25)
                            height: headings.height; leftPadding: Theme.space.M
                            text: modelData; textStyle: "secondary"
                        }
                    }
                }
            }
            M.ScrollPage {
                leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0; groundAbove: true
                id: rows
                objectName: "dialogShortcutTable"
                Layout.fillWidth: true; Layout.fillHeight: true
                Column { id: table; width: rows.pageWidth
                Repeater {
                model: (root.backend && root.backend.kind === "shortcuts" ? root.backend.state.shortcuts : []).filter(row => !filter.text || (row.label + " " + row.keys + " " + row.defaults).toLowerCase().includes(filter.text.toLowerCase()))
                delegate: Rectangle {
                    required property var modelData
                    width: rows.pageWidth; height: Theme.size.COMPACT
                    color: root.selected === modelData.id ? Theme.colors.select_bg : "transparent"
                    Row {
                        anchors.fill: parent
                        Repeater {
                            model: [modelData.label, modelData.keys, modelData.defaults]
                            M.Label {
                                required property string modelData; required property int index
                                width: parent.width * (index === 0 ? 0.5 : 0.25); height: parent.height
                                leftPadding: Theme.space.XS; text: modelData; elide: Text.ElideRight
                            }
                        }
                    }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.colors.line_soft }
                    MouseArea { anchors.fill: parent; onClicked: { root.selected = modelData.id; capture.clear() } }
                }
                }
                }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        M.Label { text: root.backend.labels.newKeys }
        M.TextField {
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
    M.Label {
        Layout.fillWidth: true; wrapMode: Text.WordWrap
        text: root.selected && capture.text ? root.backend.shortcutVerdict(root.selected, capture.text) : ""
    }
    RowLayout {
        Layout.fillWidth: true; Layout.topMargin: Theme.space.L
        M.Label { Layout.fillWidth: true; text: root.backend.labels.keyboardNote; wrapMode: Text.WordWrap }
        M.Button { text: root.backend.labels.allDefaults; onClicked: root.backend.resetShortcut("") }
    }
}
