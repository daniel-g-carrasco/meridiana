import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M

M.ScrollPage {
    leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0
    id: root
    objectName: "plant-storage-form"
    required property var backend
    property var battery: backend.storage.battery || ({})
    property string coupling: backend.storage.storage_coupling || "ac"
    property var inverter: backend.storage.storage_inverter || ({})
    property int units: backend.storage.battery_units || 1
    property real efficiency: backend.storage.storage_efficiency_pct || 0
    property int revision: 0
    property bool windowButtons: false          // R518: apply and remove on the window's row (PlantDialogs)
    function resetDraft() {
        coupling = backend.storage.storage_coupling || "ac"
        inverter = backend.storage.storage_inverter || ({})
        units = backend.storage.battery_units || 1
        efficiency = backend.storage.storage_efficiency_pct || 0
    }
    onRevisionChanged: resetDraft()
    readonly property var inverterRecords: {
        const records = []
        for (const unit of backend.units) if (!records.some(r => r.model === unit.record.model && r.manufacturer === unit.record.manufacturer)) records.push(unit.record)
        if (inverter.model && !records.some(r => r.model === inverter.model && r.manufacturer === inverter.manufacturer)) records.push(inverter)
        return [{}].concat(records)
    }
    readonly property var patch: ({battery: battery, battery_units: units, storage_coupling: coupling,
                                   storage_inverter: coupling === "dc" ? inverter : ({}),
                                   storage_efficiency_pct: efficiency || null})
    readonly property var check: backend.checkStorage(patch)
    ColumnLayout {
        id: body
        width: Math.min(root.pageWidth, 700)
        spacing: Theme.space.M
        M.CopyLabel { text: qsTr("Storage") }
        M.ReadableText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: ((root.battery.manufacturer || "") + " " + (root.battery.model || "")).trim() || qsTr("No battery") }
        M.Button { Layout.fillWidth: true; text: qsTr("Choose battery…"); onClicked: root.backend.catalogRequested("batteries", -1) }
        M.CopyLabel { text: qsTr("Connection") }
        M.ComboBox { Layout.fillWidth: true; value: root.coupling
            options: [{key: "ac", label: qsTr("AC: independent storage converter")},
                      {key: "dc", label: qsTr("DC: hybrid inverter")}]
            onChosen: value => root.coupling = value }
        M.CopyLabel { text: qsTr("Storage inverter") }
        M.ComboBox { Layout.fillWidth: true; enabled: root.coupling === "dc"
            value: (root.inverter.manufacturer || "") + " " + (root.inverter.model || "")
            options: root.inverterRecords.map(r => ({key: (r.manufacturer || "") + " " + (r.model || ""), label: r.model ? ((r.manufacturer || "") + " " + r.model).trim() : qsTr("No inverter selected")}))
            onChosen: value => { for (const r of root.inverterRecords) if ((r.manufacturer || "") + " " + (r.model || "") === value) root.inverter = r } }
        M.ReadableText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("Complete battery systems in parallel") }
        M.NumberField { Layout.fillWidth: true; value: root.units; minimum: 1; maximum: 1000; decimals: 0; onValueEdited: value => root.units = value }
        M.ReadableText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: qsTr("AC round-trip efficiency (designer input)") }
        M.NumberField {
            id: efficiencyField
            Layout.fillWidth: true; value: root.efficiency; minimum: 0; maximum: 100; decimals: 1
            readonly property bool unspecified: value === 0 && !activeFocus
            color: unspecified ? "transparent" : Theme.colors.text
            unit: unspecified ? "" : "%"
            M.CopyLabel { anchors.fill: parent; anchors.margins: Theme.space.S; visible: efficiencyField.unspecified; text: qsTr("Not supplied"); horizontalAlignment: Text.AlignRight }
            onValueEdited: value => root.efficiency = value
        }
        M.ReadableText { Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "secondary"
            text: qsTr("Hourly balance uses AC production and an equivalent AC round-trip efficiency once. DC coupling does not recover clipped PV energy. Unknown compatibility is not approval.") }
        M.ReadableText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.check.text || "" }
        M.Button { Layout.fillWidth: true; visible: !root.windowButtons; text: qsTr("Apply storage configuration"); enabled: root.check.valid; onClicked: root.backend.applyStorage(root.patch) }
        M.Button { Layout.fillWidth: true; visible: !root.windowButtons; text: qsTr("Remove storage"); onClicked: { root.backend.removeStorage(); root.battery = ({}) } }
    }
}
