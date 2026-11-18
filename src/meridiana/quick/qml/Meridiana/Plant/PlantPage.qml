import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Catalog

Rectangle {
    id: root
    property var backend: plantBackend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var units: backend.units
    readonly property var strings: backend.strings
    readonly property var inputs: backend.inputs
    readonly property var plantData: backend.data
    readonly property var chosen: backend.chosen
    property var catalogController: typeof catalogBackend !== "undefined" ? catalogBackend : null
    property Component planComponent: null
    property var selectedModules: []
    property string section: "strings"
    property string stringsView: "cards"
    property int catalogEntry: -1
    property string catalogPurpose: ""
    property string subfieldId: ""
    readonly property var subfield: backend.subfields.find(sf => sf.id === subfieldId) || ({})
    property var sheet: ({})
    property string confirmation: ""
    property var confirmedAction: null
    implicitWidth: M.ControlMetrics.pageSize.wide.width
    implicitHeight: M.ControlMetrics.pageSize.wide.height
    color: Theme.colors.window
    focus: true

    function ask(text, action) { confirmation = text; confirmedAction = action }
    function showCatalog(kind, entry) {
        catalogEntry = entry
        catalogPurpose = kind
        if (catalogController) { catalogController.setKind(kind); catalogue.visible = true }
    }
    function submitProposal(options) {
        const go = () => backend.proposeConfigured(options)
        if (options.replace && root.strings.length) ask(backend.tr("The existing strings will be replaced. Undo restores the previous wiring."), go)
        else go()
    }
    Connections { target: root.backend; function onCatalogRequested(kind, entry) { root.showCatalog(kind, entry) } }
    Connections {
        target: root.catalogController
        function onChosen(kind, record) {
            if (kind === "inverters") root.backend.addInverter(record)
            else if (kind === "optimizers") root.backend.setOptimizer(root.catalogEntry, record, (record.modules_per_unit || 1) >= 2 ? 2 : 1)
            else if (kind === "batteries") storage.battery = record
            catalogue.visible = false
        }
    }
    Keys.onDeletePressed: event => { if (backend.selected >= 0) backend.deleteString(backend.selected) }
    // Undo and redo come from the command catalogue. A second Esc would be ambiguous with the window's, which then
    // fires neither: this one exists only while this page has something of its own to close.
    Shortcut { sequence: "Esc"; enabled: root.visible && (proposal.visible || catalogue.visible || root.confirmation !== "" || Object.keys(root.sheet).length > 0)
        onActivated: { proposal.visible = false; catalogue.visible = false; root.confirmation = ""; root.sheet = ({}) } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.M
        spacing: Theme.space.M
        RowLayout {
            Layout.fillWidth: true
            M.Label { text: root.backend.tr("Plant"); textStyle: "heading" }
            M.Label { Layout.fillWidth: true; text: root.plantData.total; textStyle: "description"; elide: Text.ElideRight }
            M.ToolButton { objectName: "layout"; text: root.backend.tr("Lay out"); mode: "beside"; iconName: "fill"
                onClicked: root.backend.layoutRequested()
                Rectangle { objectName: "layoutDot"; visible: root.backend.layoutDirty; width: 5; height: 5; radius: 3; color: Theme.colors.accent; anchors.right: parent.right; anchors.top: parent.top } }
            M.ToolButton { objectName: "calculate"; text: root.backend.tr("Compute"); mode: "beside"; iconName: "compute"
                onClicked: root.backend.calculateRequested()
                Rectangle { objectName: "calculateDot"; visible: root.backend.calculateDirty; width: 5; height: 5; radius: 3; color: Theme.colors.accent; anchors.right: parent.right; anchors.top: parent.top } }
            M.Button { iconName: "undo"; flat: true; enabled: root.backend.canUndo; tip: root.backend.tr("Undo"); onClicked: root.backend.undo() }
            M.Button { iconName: "redo"; flat: true; enabled: root.backend.canRedo; tip: root.backend.tr("Redo"); onClicked: root.backend.redo() }
        }
        RowLayout {
            Layout.fillWidth: true
            M.Button { objectName: "stringsTab"; text: root.backend.tr("Inverters and strings"); flat: true; active: root.section === "strings"; onClicked: root.section = "strings" }
            M.Button { objectName: "storageTab"; text: root.backend.tr("Storage"); flat: true; active: root.section === "storage"; onClicked: root.section = "storage" }
            Item { Layout.fillWidth: true }
            M.Label { text: root.backend.searching ? root.backend.tr("Searching…") : root.backend.busy ? root.backend.tr("The inverters are being checked…") : ""; textStyle: "secondary" }
            M.Button { visible: root.backend.searching; text: root.backend.tr("Cancel"); onClicked: root.backend.cancelSearch() }
        }
        RowLayout {
            visible: root.section === "strings"
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: Theme.space.M
            M.Card {
                Layout.preferredWidth: Math.max(250, Math.min(340, root.width * 0.24))
                Layout.fillHeight: true
                title: root.backend.tr("Active inverters")
                ColumnLayout {
                    anchors.fill: parent
                    spacing: Theme.space.S
                    ListView {
                        id: units
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; spacing: Theme.space.S; reuseItems: true
                        model: root.units
                        C.ScrollBar.vertical: M.ScrollBar { }
                        delegate: Rectangle {
                            id: unit
                            required property var modelData
                            required property int index
                            width: units.width
                            height: unitContents.implicitHeight + 2 * Theme.space.S
                            color: root.backend.working === modelData.number ? Theme.colors.press : Theme.colors.panel
                            radius: Theme.radius.CONTROL
                            ColumnLayout {
                                id: unitContents
                                x: Theme.space.S; y: Theme.space.S; width: parent.width - 2 * x
                                spacing: Theme.space.XS
                                RowLayout {
                                    Layout.fillWidth: true
                                    M.Button { text: String(unit.modelData.number); active: root.backend.working === unit.modelData.number; flat: true; onClicked: root.backend.selectUnit(unit.modelData.number)
                                        DragHandler { target: null; xAxis.enabled: false
                                            onActiveChanged: if (!active && Math.abs(translation.y) > 10) {
                                                const targetIndex = Math.max(0, Math.min(root.units.length - 1, unit.index + Math.round(translation.y / unit.height)))
                                                root.backend.moveUnit(unit.modelData.number, targetIndex)
                                            } }
                                    }
                                    M.TextField { Layout.fillWidth: true; text: unit.modelData.name; selectByMouse: true
                                        onEditingFinished: root.backend.renameUnit(unit.modelData.number, text) }
                                    M.Button { iconName: "control:more"; flat: true; menu: unitMenu }
                                }
                                M.Label { Layout.fillWidth: true; text: unit.modelData.model; wrapMode: Text.Wrap; textStyle: "secondary" }
                                M.Label { Layout.fillWidth: true; text: unit.modelData.power + " kW · " + unit.modelData.inputs + " MPPT"; textStyle: "secondary" }
                                M.Label { Layout.fillWidth: true; text: unit.modelData.strings + " " + root.backend.tr("Strings") + " · " + unit.modelData.modules + " " + root.backend.tr("Modules"); textStyle: "secondary" }
                                M.Label { Layout.fillWidth: true; text: "DC/AC " + unit.modelData.ratio; visible: unit.modelData.ratio !== ""; textStyle: "secondary" }
                                RowLayout {
                                    visible: unit.modelData.optimized
                                    M.Button { text: root.backend.tr("Optimizers"); onClicked: root.showCatalog("optimizers", unit.modelData.entry) }
                                    M.NumberField { Layout.preferredWidth: 60; minimum: 1; maximum: 2; decimals: 0; value: unit.modelData.per
                                        onValueEdited: value => root.backend.setOptimizerPer(unit.modelData.entry, value) }
                                }
                                M.Label { visible: unit.modelData.optimized; Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "caption"
                                    text: (unit.modelData.optimizer.model || root.backend.tr("suggested")) }
                            }
                            M.Menu {
                                id: unitMenu
                                M.MenuItem { text: root.backend.tr("Datasheet"); onTriggered: root.sheet = unit.modelData.record }
                                M.MenuItem { text: root.backend.tr("Move up"); enabled: unit.index > 0; onTriggered: root.backend.moveUnit(unit.modelData.number, unit.index - 1) }
                                M.MenuItem { text: root.backend.tr("Move down"); enabled: unit.index < root.units.length - 1; onTriggered: root.backend.moveUnit(unit.modelData.number, unit.index + 1) }
                                M.MenuItem { text: root.backend.tr("String automatically"); onTriggered: { proposal.scope = unit.modelData.number; proposal.visible = true } }
                                M.MenuItem { text: root.backend.tr("Empty its strings"); onTriggered: root.ask(text, () => root.backend.emptyUnit(unit.modelData.number)) }
                                M.MenuItem { text: root.backend.tr("Take out of the plant"); onTriggered: root.ask(text, () => root.backend.removeUnit(unit.modelData.number, false)) }
                                M.MenuItem { text: root.backend.tr("Back to the optimizers Meridiana proposes"); visible: unit.modelData.optimized; onTriggered: root.backend.setOptimizer(unit.modelData.entry, {}, 1) }
                            }
                        }
                    }
                    M.Button { Layout.fillWidth: true; text: root.backend.tr("Choose from the catalogue…"); iconName: "inverter_catalog"; onClicked: root.showCatalog("inverters", -1) }
                    M.Button { Layout.fillWidth: true; text: root.backend.tr("Choose automatically…"); iconName: "inverter_auto"; onClicked: { sizing.visible = true; root.backend.loadMakers() } }
                    M.Label { text: root.backend.tr("DC/AC ratio wanted") }
                    M.NumberField { Layout.fillWidth: true; value: root.backend.settings.dc_ac; minimum: 0.5; maximum: 2; decimals: 2; stepSize: 0.05
                        onValueEdited: value => root.backend.setEnergy("dc_ac_ratio", value) }
                    M.Label { text: "DC/AC " + (root.plantData.ratio || ""); textStyle: "secondary" }
                    M.Label { text: root.plantData.clipping ? root.backend.tr("Energy cut") + ": " + root.plantData.clipping : root.backend.tr("Compute production to see the energy cut."); textStyle: "caption"; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    M.Label { text: root.backend.tr("Sub-field selected"); textStyle: "strong"; visible: root.backend.subfields.length > 0 }
                    M.ComboBox { Layout.fillWidth: true; visible: root.backend.subfields.length > 0; value: root.subfieldId
                        options: [{key: "", label: root.backend.tr("Select a sub-field")}].concat(root.backend.subfields.map(sf => ({key: sf.id, label: sf.name})))
                        onChosen: value => root.subfieldId = value }
                    M.ComboBox { Layout.fillWidth: true; visible: root.subfieldId !== ""; value: root.subfield.inverter || 0
                        options: [{key: 0, label: root.backend.tr("Automatic")}].concat(root.units.map(u => ({key: u.number, label: u.number + " · " + u.name})))
                        onChosen: value => root.backend.assignSubfield(root.subfieldId, value, 0) }
                    M.ComboBox { Layout.fillWidth: true; visible: !!root.subfield.inverter; value: root.subfield.mppt || 0
                        options: [{key: 0, label: root.backend.tr("Automatic")}].concat(root.inputs.filter(i => i.unit === root.subfield.inverter).map(i => ({key: i.mppt, label: i.label})))
                        onChosen: value => root.backend.assignSubfield(root.subfieldId, root.subfield.inverter, value) }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                spacing: Theme.space.S
                Flow {
                    Layout.fillWidth: true; Layout.preferredHeight: implicitHeight
                    spacing: Theme.space.XS
                    M.Button { objectName: "drawString"; text: root.backend.tr("Draw"); iconName: "strings_manual"; flat: true; enabled: root.backend.working > 0
                        onClicked: root.backend.draw(root.backend.working, 1, -1) }
                    M.Button { objectName: "proposalOptions"; text: root.backend.tr("Propose"); iconName: "strings_auto"; flat: true; onClicked: proposal.visible = true }
                    M.Button { text: root.backend.tr("Complete"); iconName: "strings_complete"; flat: true; onClicked: root.backend.propose({replace: false}) }
                    M.Button { text: root.backend.tr("Clear"); iconName: "strings_clear"; flat: true; enabled: root.strings.length > 0; onClicked: root.ask(root.backend.tr("Delete all the strings"), () => root.backend.clearStrings()) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    M.Label { text: root.backend.tr("Strings"); textStyle: "title"; Layout.fillWidth: true }
                    M.Button { objectName: "viewCards"; text: root.backend.tr("Cards"); flat: true; active: root.stringsView === "cards"; onClicked: root.stringsView = "cards" }
                    M.Button { objectName: "viewDiagram"; text: root.backend.tr("Diagram"); flat: true; active: root.stringsView === "diagram"; onClicked: root.stringsView = "diagram" }
                    M.Button { objectName: "viewTable"; text: root.backend.tr("Table"); flat: true; active: root.stringsView === "table"; onClicked: root.stringsView = "table" }
                }
                Loader { Layout.fillWidth: true; Layout.preferredHeight: active ? 240 : 0; active: root.planComponent !== null; sourceComponent: root.planComponent }
                M.Label { objectName: "stringsEmpty"; visible: root.strings.length === 0; Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "description"
                    text: root.backend.tr("No strings yet. Draw a string on an input, or ask Meridiana to propose them.") }
                PlantTable { Layout.fillWidth: true; Layout.fillHeight: true; backend: root.backend; visible: root.stringsView === "table" && root.strings.length > 0 }
                PlantInputs { Layout.fillWidth: true; Layout.fillHeight: true; backend: root.backend; visible: root.stringsView !== "table" || root.strings.length === 0; diagram: root.stringsView === "diagram" }
                M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "secondary"; visible: text !== ""; text: root.plantData.notes.join("\n") }
                M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "caption"; text: (root.plantData.conditions || "") + " · " + (root.plantData.temperatures || "") }
            }
            M.Card {
                visible: root.backend.selected >= 0
                Layout.preferredWidth: Math.max(270, Math.min(360, root.width * 0.26)); Layout.fillHeight: true
                title: root.backend.tr("String") + " " + (root.chosen.label || "")
                closable: true; onClosed: root.backend.selectString(-1)
                M.ScrollPage {
                    leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0; groundAbove: true
                    anchors.fill: parent
                    ColumnLayout {
                        id: details; width: parent.width; spacing: Theme.space.S
                        M.Label { text: root.chosen.stateText || ""; textStyle: "strong"; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        M.Label { text: root.chosen.voltages || ""; textStyle: "secondary"; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        Repeater {
                            model: root.chosen.bars || []
                            ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                M.Label { text: modelData.label + " · " + modelData.text; textStyle: "secondary" }
                                Rectangle { Layout.fillWidth: true; height: 4; color: Theme.colors.line
                                    Rectangle { x: parent.width * modelData.low; width: parent.width * Math.max(0.015, modelData.high - modelData.low); height: parent.height; color: root.backend.statusColors[modelData.state] } }
                            }
                        }
                        PlantChecks { Layout.fillWidth: true; backend: root.backend; rows: root.chosen.checks || [] }
                        M.Label { text: root.backend.tr("Move to input"); textStyle: "strong" }
                        M.ComboBox {
                            Layout.fillWidth: true; value: (root.chosen.inverter || 0) + ":" + (root.chosen.mppt || 0)
                            options: root.inputs.map(i => ({key: i.unit + ":" + i.mppt, label: i.unit + " · " + i.label}))
                            onChosen: value => { const parts = value.split(":"); root.backend.moveString(root.backend.selected, Number(parts[0]), Number(parts[1])) }
                        }
                        M.Button { text: root.backend.tr("Draw again"); onClicked: root.backend.draw(root.chosen.inverter, root.chosen.mppt, root.backend.selected) }
                        M.Button { text: root.backend.tr("Reverse the string"); onClicked: root.backend.reverseString(root.backend.selected) }
                        M.Button { text: root.backend.tr("Optimizer groups"); visible: (root.chosen.groups || []).length > 0
                            onClicked: {
                                const unit = root.units.find(u => u.number === root.chosen.inverter)
                                grouping.prepare(root.chosen.keys, unit ? unit.per : 1, root.chosen.groups, root.backend.selected)
                            } }
                        M.Button { text: root.backend.tr("Delete string"); onClicked: root.backend.deleteString(root.backend.selected) }
                    }
                }
            }
        }
        PlantStorage { id: storage; objectName: "storagePanel"; backend: root.backend; visible: root.section === "storage"; Layout.fillWidth: true; Layout.fillHeight: true }
        M.Label { Layout.fillWidth: true; text: root.backend.message; wrapMode: Text.Wrap; textStyle: "secondary"; maximumLineCount: 4; elide: Text.ElideRight }
    }

    PlantProposal { id: proposal; objectName: "proposalPanel"; backend: root.backend; selectedModules: root.selectedModules
        visible: false; z: 10; width: Math.min(root.width - 40, 520); height: implicitHeight; anchors.centerIn: parent; onSubmitted: options => root.submitProposal(options) }
    PlantOptimizerGroups {
        id: grouping; objectName: "optimizerGroups"; backend: root.backend
        visible: false; z: 12; width: 560; height: Math.min(root.height - 100, 540); anchors.centerIn: parent
    }
    M.Card {
        id: sizingResult
        objectName: "sizingResult"
        visible: !!root.backend.sizingChoice.why; z: 11
        width: Math.min(root.width - 40, 620); height: sizingBody.implicitHeight + 80; anchors.centerIn: parent
        title: root.backend.tr("Inverters sized"); closable: true; onClosed: root.backend.dismissSizing()
        ColumnLayout {
            id: sizingBody
            width: parent.width
            spacing: Theme.space.S
            M.Label { objectName: "sizingWhy"; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.backend.sizingChoice.why || "" }
            M.Label { Layout.fillWidth: true; textStyle: "strong"; visible: (root.backend.sizingChoice.alternatives || []).length > 0
                text: root.backend.tr("Other valid combinations") }
            Repeater {
                model: root.backend.sizingChoice.alternatives || []
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: Theme.space.M
                    M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap
                        text: modelData.names + " · DC/AC " + modelData.ratio + (modelData.units > 1 ? " (" + modelData.byUnit + ")" : "") + " · " + modelData.ac + " kW AC · " + root.backend.tr("DC max") + " " + modelData.dc + " kW"
                              + (modelData.oversized ? " · " + root.backend.tr("oversized") : "")
                        M.ToolTip { visible: altHover.hovered; text: modelData.why }
                        HoverHandler { id: altHover } }
                    M.Button { objectName: "sizingUse" + modelData.index; text: root.backend.tr("Use this"); onClicked: root.backend.useSizingAlternative(modelData.index) }
                }
            }
        }
    }
    M.Card {
        id: sizing; visible: false; z: 11; width: 500; height: Math.min(root.height - 80, 560); anchors.centerIn: parent
        title: root.backend.tr("Size the inverter by itself"); closable: true; onClosed: visible = false
        ColumnLayout { anchors.fill: parent
            M.TextField { id: makerSearch; Layout.fillWidth: true; placeholderText: root.backend.tr("Search a manufacturer") }
            ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; reuseItems: true
                // r23-f1: the program's bar (lane, fades, rebound); the rows end before its lane (R520)
                C.ScrollBar.vertical: M.ScrollBar { id: makersBar }
                model: root.backend.makers.filter(m => m.label.toLowerCase().includes(makerSearch.text.toLowerCase()))
                delegate: RowLayout { required property var modelData; width: ListView.view.width - makersBar.room
                    M.Button { iconName: modelData.favourite ? "control:star-full" : "control:star"; flat: true; tip: root.backend.tr("Favourites"); onClicked: root.backend.toggleFavourite(modelData.label) }
                    M.Button { Layout.fillWidth: true; text: modelData.label; tip: modelData.reason
                        active: modelData.label === root.backend.settings.maker; opacity: modelData.sizable ? 1 : 0.5
                        onClicked: { root.backend.sizeInverters(modelData.label); sizing.visible = false } }
                }
            }
        }
    }
    M.Card {
        visible: root.confirmation !== ""; z: 20; width: Math.min(500, root.width - 40); height: confirmBody.implicitHeight + 80; anchors.centerIn: parent
        title: root.backend.tr("Plant"); closable: true; onClosed: root.confirmation = ""
        ColumnLayout { id: confirmBody; width: parent.width
            M.Label { text: root.confirmation; Layout.fillWidth: true; wrapMode: Text.Wrap }
            RowLayout {
                M.Button { text: root.backend.tr("Continue"); onClicked: { const action = root.confirmedAction; root.confirmation = ""; if (action) action() } }
                M.Button { text: root.backend.tr("Cancel"); onClicked: root.confirmation = "" }
            }
        }
    }
    M.Card {
        visible: Object.keys(root.sheet).length > 0; z: 15; width: Math.min(660, root.width - 40); height: root.height - 100; anchors.centerIn: parent
        title: root.backend.tr("Datasheet"); closable: true; onClosed: root.sheet = ({})
        ListView { anchors.fill: parent; clip: true; model: root.backend.recordDetails(root.sheet)
            C.ScrollBar.vertical: M.ScrollBar { }
            delegate: M.Label { required property var modelData; width: ListView.view.width; wrapMode: Text.Wrap
                text: modelData.label + ": " + modelData.value; textStyle: "secondary"; bottomPadding: Theme.space.S }
        }
    }
    Rectangle {
        id: catalogue; visible: false; z: 30; anchors.fill: parent; color: Theme.colors.window
        CatalogPage { anchors.fill: parent; anchors.topMargin: 40; backend: root.catalogController }
        M.Button { anchors.right: parent.right; text: root.backend.tr("Close"); onClicked: catalogue.visible = false }
    }
}
