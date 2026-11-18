import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    required property var backend
    spacing: Theme.space.S
    M.Section {
        width: parent.width; title: root.backend.text.mapBackground
        SettingField {
            width: parent.width; backend: root.backend
            field: root.backend.fields.find(f => f.key === "background")
            labelWidth: Theme.measureText(field.label).width
        }
        M.Label { width: parent.width; text: root.backend.text.mapBackgroundNote; textStyle: "description"; wrapMode: Text.WordWrap }
    }
    M.Section {
        width: parent.width; title: root.backend.text.atSite
        visible: root.backend.hasSite
        SourceRows { width: parent.width; rows: root.backend.siteSources }
    }
    M.Section {
        width: parent.width; title: root.backend.text.builtin
        SourceRows { width: parent.width; rows: root.backend.sourceRows }
        M.Label { width: parent.width; text: root.backend.text.mapLicences; textStyle: "description"; wrapMode: Text.WordWrap }
    }
    M.Section {
        width: parent.width; title: root.backend.text.sources
        SettingsRecords { width: parent.width; backend: root.backend; maps: true }
    }
    component SourceRows: Column {
        property var rows: []
        Repeater {
            model: rows
            delegate: Item {
                required property var modelData
                width: parent.width; height: Math.max(name.implicitHeight, licence.implicitHeight) + 2 * Theme.space.S + 1
                RowLayout {
                    anchors.fill: parent; spacing: Theme.space.L
                    M.Label { id: name; Layout.fillWidth: true; text: modelData.name; textStyle: "strong"; wrapMode: Text.WordWrap }
                    M.Label { id: licence; Layout.maximumWidth: parent.width * 0.6; text: modelData.licence; textStyle: "description"; wrapMode: Text.WordWrap }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line_soft }
                M.ToolTip { text: modelData.tip; visible: hover.hovered }
                HoverHandler { id: hover }
            }
        }
    }
}
