import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs as D
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    required property var backend
    property bool maps: false
    property var records: maps ? backend.values.map_sources : backend.values.report_profiles
    property var recordFields: maps ? backend.mapFields : backend.profileFields
    property int current: records.length ? 0 : -1
    property var record: current >= 0 && current < records.length ? records[current] : ({})
    spacing: Theme.space.M
    onRecordsChanged: {
        if (!records.length) current = -1
        else if (current < 0) current = 0
        else if (current >= records.length) current = records.length - 1
    }
    D.FileDialog {
        id: logoDialog
        title: root.backend.text.logo
        nameFilters: [root.backend.text.logoFilter]
        onAccepted: root.backend.editProfile(root.current, "logo", selectedFile.toString())
    }
    RowLayout {
        width: parent.width
        spacing: Theme.space.S
        M.ComboBox {
            Layout.fillWidth: true
            objectName: root.maps ? "settingsMapChoice" : "settingsProfileChoice"
            options: root.records.map((record, index) => ({value: index, label: record.name}))
            value: root.current
            enabled: root.records.length > 0
            onChosen: value => { root.backend.flushPending(); root.current = value }
        }
        M.Button {
            objectName: root.maps ? "settingsAddMap" : "settingsAddProfile"
            text: root.maps ? root.backend.text.addMap : root.backend.text.addProfile
            onClicked: {
                if (root.maps) root.backend.addMapSource(); else root.backend.addProfile()
                root.current = root.records.length - 1
            }
        }
        M.Button {
            objectName: root.maps ? "settingsRemoveMap" : "settingsRemoveProfile"
            text: root.backend.text.remove
            enabled: root.current >= 0
            onClicked: { if (root.maps) root.backend.removeMapSource(root.current); else root.backend.removeProfile(root.current) }
        }
    }
    Repeater {
        model: root.recordFields
        delegate: GridLayout {
            required property var modelData
            width: root.width
            enabled: root.current >= 0
            columns: root.width < 520 ? 1 : 2
            columnSpacing: Theme.space.S; rowSpacing: Theme.space.XS
            M.Label { Layout.preferredWidth: root.width < 520 ? -1 : Math.max(...root.recordFields.map(f => Theme.measureText(f.label).width)); text: modelData.label }
            RowLayout {
                Layout.fillWidth: true
                visible: !root.maps || (modelData.key !== "kind" && modelData.key !== "imagery" && modelData.key !== "max_zoom")
                M.TextField {
                    id: recordEdit; Layout.fillWidth: true
                    visible: root.maps || modelData.key !== "logo"
                    placeholderText: modelData.hint || ""
                    objectName: (root.maps ? "settingsMap_" : "settingsProfile_") + modelData.key + (parent.visible ? "" : "_hidden")
                    text: root.record[modelData.key] === undefined ? "" : String(root.record[modelData.key])
                    onEditingFinished: root.backend.flushPending()
                    onTextEdited: {
                        if (root.maps) root.backend.stageMapSource(root.current, modelData.key, text)
                        else root.backend.stageProfile(root.current, modelData.key, text)
                    }
                }
                M.Label {
                    Layout.fillWidth: true
                    visible: !root.maps && modelData.key === "logo"
                    text: root.record.logo ? String(root.record.logo).split(/[\\/]/).pop() : root.backend.text.noLogo
                    elide: Text.ElideMiddle
                }
                M.Button {
                    visible: !root.maps && modelData.key === "logo"
                    text: root.backend.text.choose
                    onClicked: logoDialog.open()
                }
                M.Button {
                    visible: !root.maps && modelData.key === "logo"
                    enabled: !!root.record.logo
                    text: root.backend.text.remove
                    onClicked: root.backend.editProfile(root.current, "logo", "")
                }
            }
            M.ComboBox {
                objectName: "settingsMap_" + modelData.key + (visible ? "" : "_hiddenChoice")
                Layout.fillWidth: true
                visible: root.maps && (modelData.key === "kind" || modelData.key === "imagery")
                options: modelData.key === "kind" ? [{value: "xyz", label: "XYZ"}, {value: "wms", label: "WMS"}, {value: "wmts", label: "WMTS"}] : root.backend.mapImageryOptions
                value: root.record[modelData.key]
                onChosen: value => root.backend.editMapSource(root.current, modelData.key, value)
            }
            M.NumberField {
                objectName: "settingsMap_" + modelData.key + (visible ? "" : "_hiddenNumber")
                Layout.fillWidth: true
                visible: root.maps && modelData.key === "max_zoom"
                value: Number(root.record.max_zoom || 19)
                minimum: 1
                maximum: root.backend.mapMaxZoom
                decimals: 0
                onValueEdited: value => root.backend.editMapSource(root.current, "max_zoom", value)
            }

        }
    }
    M.Label {
        width: parent.width
        visible: root.maps && root.current >= 0
        text: { let records = root.records; return root.maps ? root.backend.mapProblems(root.current) : "" }
        wrapMode: Text.WordWrap
        color: Theme.colors.danger
    }
    Column {
        width: parent.width
        visible: root.maps && root.current >= 0
        spacing: Theme.space.S
        M.Button {
            objectName: "settingsReadCapabilities"
            text: root.backend.text.capabilities
            enabled: !root.backend.services.mapBusy && root.record.kind !== "xyz"
            onClicked: root.backend.services.readCapabilities(root.current)
        }
        M.Label { width: parent.width; text: root.backend.services.mapStatus; wrapMode: Text.WordWrap }
        M.ComboBox {
            width: parent.width
            objectName: "settingsMapLayer"
            options: root.backend.services.layers[root.record.key] || []
            value: root.record.layer
            visible: options.length > 0
            onChosen: value => root.backend.services.chooseLayer(root.current, value)
        }
        M.TextField { id: mapSecret; width: parent.width; echoMode: TextInput.Password; placeholderText: root.backend.text.key }
        Flow {
            width: parent.width
            spacing: Theme.space.S
            M.Button { text: root.backend.text.key; onClicked: { root.backend.setSecret(root.record.key, mapSecret.text, "meridiana-maps"); mapSecret.clear() } }
            M.Button { text: root.backend.text.forget; onClicked: root.backend.setSecret(root.record.key, "", "meridiana-maps") }
        }
    }
}
