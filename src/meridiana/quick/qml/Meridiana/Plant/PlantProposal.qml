import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

M.Card {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var units: backend.units
    property var selectedModules: []
    property int scope: 0
    property string strategy: backend.settings.strategy
    property bool replace: true
    property bool across: backend.settings.across
    signal submitted(var options)
    title: backend.tr("String automatically")
    closable: true
    implicitHeight: bare ? form.implicitHeight : form.implicitHeight + Theme.size.CONTROL + Theme.space.M * 3
    // R518: in a window the buttons are the window's (M.Dialog), which calls submit()
    function submit() {
        root.submitted({strategy: root.strategy, replace: root.replace, unit: root.scope > 0 ? root.scope : 0,
                        only: root.scope === -1 ? root.selectedModules : [], n_series: series.value || null, dc_ac: ratio.value,
                        across: root.across})
    }
    GridLayout {
        // As the form of ui/plant_page.py StringingPopup: each name beside its field.
        id: form
        width: parent.width
        columns: 2; columnSpacing: Theme.space.M; rowSpacing: Theme.space.S
        M.Label { Layout.fillWidth: true; Layout.columnSpan: 2; wrapMode: Text.Wrap; textStyle: "description"
            text: root.backend.tr("Meridiana lays strings on the inputs of the inverters, valid for their voltage window and their currents. The modules can also be chosen on the plan while this window is open.") }
        M.Label { text: root.backend.tr("On what") }
        M.ComboBox {
            Layout.fillWidth: true; value: root.scope
            options: [{key: 0, label: root.backend.tr("the whole plant")}]
                .concat(root.selectedModules.length ? [{key: -1, label: root.backend.tr("Modules selected")}] : [])
                .concat(root.units.filter(u => u.entry >= 0).map(u => ({key: u.number, label: u.number + ": " + u.name})))
            onChosen: value => root.scope = value
        }
        M.Label { text: root.backend.tr("Strings there are") }
        M.ComboBox { Layout.fillWidth: true; value: root.replace
            options: [{key: true, label: root.backend.tr("replace the strings there are")},
                      {key: false, label: root.backend.freeModules > 0
                          ? (root.backend.freeModules === 1 ? root.backend.tr("only the module in no string")
                             : root.backend.tr("only the {n} modules in no string").replace("{n}", root.backend.freeModules))
                          : root.backend.tr("add strings for the modules in no string only")}]
            onChosen: value => root.replace = value }
        M.Label { text: root.backend.tr("Path of the strings") }
        M.ComboBox { Layout.fillWidth: true; options: root.backend.strategies; value: root.strategy; onChosen: value => root.strategy = value }
        // R433: without optimizers the strings go on over another face of the building only when asked
        M.Label { text: root.backend.tr("Roof faces") }
        M.ComboBox { Layout.fillWidth: true; value: root.across
            options: [{key: false, label: root.backend.tr("a string on one face (with optimizers it goes on only when needed)")},
                      {key: true, label: root.backend.tr("a string may go on over another face of the same building")}]
            onChosen: value => root.across = value }
        M.Label { text: root.backend.tr("Modules in series") }
        // 0: Meridiana chooses from the voltage window, said «proposto» as in the Widgets form (never «0»).
        M.NumberField { id: series; objectName: "plant-propose-series"; Layout.fillWidth: true; value: root.backend.settings.n_series
            decimals: 0; minimum: 0; maximum: 80; specialValueText: root.backend.tr("suggested") }
        M.Label { text: root.backend.tr("DC/AC ratio wanted") }
        M.NumberField { id: ratio; Layout.fillWidth: true; value: root.backend.settings.dc_ac; decimals: 2; minimum: 0.5; maximum: 2; stepSize: 0.05 }
        M.Label { Layout.fillWidth: true; Layout.columnSpan: 2; wrapMode: Text.Wrap; textStyle: "secondary"
            text: root.backend.tr("The modules' power (kWp) over the inverters' AC power. «Choose automatically» picks the size closest to it; the energy the inverters cut shows once the production is computed. Your choice: no judgement here.") }
        RowLayout {
            Layout.columnSpan: 2
            visible: !root.bare
            M.Button { objectName: "plant-propose-accept"; text: root.backend.tr("String"); enabled: !root.backend.searching
                onClicked: {
                    root.submitted({strategy: root.strategy, replace: root.replace, unit: root.scope > 0 ? root.scope : 0,
                                    only: root.scope === -1 ? root.selectedModules : [], n_series: series.value || null, dc_ac: ratio.value,
                                    across: root.across})
                } }
            M.Button { text: root.backend.tr("Cancel"); onClicked: root.closed() }
        }
    }
}
