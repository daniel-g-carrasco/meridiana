import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    required property var backend
    property var fields: []             // the page's (SettingsPage, R630)
    property var values: ({})
    spacing: Theme.space.S
    M.Section {
        width: parent.width; title: root.backend.text.mapBackground
        SettingField {
            width: parent.width; backend: root.backend
            section: "maps"; values: root.values
            field: root.fields.find(f => f.key === "background") || ({key: "background", label: "", kind: "choice", options: [], description: "", enabled: true})
            labelWidth: Theme.measureText(field.label).width
        }
        M.ReadableText { width: parent.width; text: root.backend.text.mapBackgroundNote; textStyle: "description"; wrapMode: Text.WordWrap }
    }
    M.Section {
        width: parent.width; title: root.backend.text.atSite
        visible: root.backend.hasSite
        SourceRows { width: parent.width; rows: root.backend.siteSources }
    }
    M.Section {
        width: parent.width; title: root.backend.text.builtin
        SourceRows { width: parent.width; rows: root.backend.sourceRows }
        M.ReadableText { width: parent.width; text: root.backend.text.mapLicences; textStyle: "description"; wrapMode: Text.WordWrap }
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
                    M.ReadableText { id: name; Layout.fillWidth: true; text: modelData.name; textStyle: "strong"; wrapMode: Text.WordWrap }
                    // its words or 60 % of the row, whichever is less: a text edit given its own implicit width does not
                    // wrap (the licence stood on one line 186 px past its box, test_allineamenti_pagine)
                    M.ReadableText { id: licence; Layout.maximumWidth: parent.width * 0.6
                        Layout.preferredWidth: Math.min(licenceWords.advanceWidth + 1, parent.width * 0.6)
                        text: modelData.licence; textStyle: "description"; wrapMode: Text.WordWrap
                        TextMetrics { id: licenceWords; font: licence.font; text: licence.text } }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line_soft }
                M.ToolTip { text: modelData.tip; visible: hover.hovered }
                HoverHandler { id: hover }
            }
        }
    }
}
