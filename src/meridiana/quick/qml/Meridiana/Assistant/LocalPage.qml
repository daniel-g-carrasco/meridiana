import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: root
    property var backend: null
    property var texts: assistantText
    spacing: Theme.space.S
    M.Label { text: root.texts.local; textStyle: "strong"; Layout.fillWidth: true }
    Flow {
        Layout.fillWidth: true; spacing: Theme.space.XS
        M.Button { text: root.texts.discover; enabled: root.backend ? !root.backend.busy : false; onClicked: root.backend.start() }
        M.Button { text: root.texts.probe; enabled: root.backend ? !root.backend.testing : false; onClicked: root.backend.probe() }
        M.Button { text: root.texts.cancel; visible: root.backend ? root.backend.testing : false; onClicked: root.backend.cancelProbe() }
    }
    M.Label { text: root.backend ? root.backend.machine : ""; Layout.fillWidth: true; wrapMode: Text.Wrap }
    M.Label { text: root.backend ? root.backend.status : ""; Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "caption" }
    RowLayout {
        visible: root.backend ? root.backend.needsRam : false
        M.Label { text: root.texts.ram }
        M.NumberField { minimum: 1; maximum: 2048; value: 16; onValueEdited: value => root.backend.setRam(value) }
    }
    Repeater {
        model: root.backend ? root.backend.models : []
        ColumnLayout {
            required property var modelData
            required property int index
            Layout.fillWidth: true
            M.Button {
                text: modelData.name
                active: root.backend.selectedIndex === index
                enabled: modelData.enabled
                Layout.fillWidth: true
                onClicked: root.backend.select(index)
            }
            M.Label { text: modelData.reason; Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "caption" }
        }
    }
    M.Button { text: root.texts.useModel; enabled: root.backend ? root.backend.selectedIndex >= 0 : false; onClicked: root.backend.useSelected() }
    M.Label { text: root.backend ? root.backend.testStatus : ""; Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "caption" }
    Repeater {
        model: root.backend ? root.backend.guide : []
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            M.Label { text: modelData.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
            M.TextArea {
                text: modelData.command || ""; visible: text.length > 0
                Layout.fillWidth: true; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
                color: Theme.colors.text
            }
        }
    }
}
