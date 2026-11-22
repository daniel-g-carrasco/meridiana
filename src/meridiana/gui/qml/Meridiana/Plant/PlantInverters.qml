import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import Meridiana.Controls as M
import Meridiana.Theme

// ui/plant_page.PlantInspector (R119, study 23): at the top the string chosen, only while one is (R298); the inverters
// one by one with their menus (R297), the totals over them and no group of their own; the Strings of the inverter
// shown with the commands at their foot; the conditions of the checks; the sub-field selected, for the proposal.
// R631: the body of the Inverter section of the Plant panel, whose page (M.PanelPage) scrolls the whole panel: no
// scroll of its own.
Column {
    id: root
    objectName: "plant-inverters"
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var units: backend.units
    readonly property var strings: backend.strings
    readonly property var plantData: backend.data
    required property var actions
    readonly property string view: actions.stringsView
    // R711: of the three views of the strings only the one shown is made, and kept once made (changing back is at
    // once, as before). The three made together were 1141 items at the first strings of 2000 modules (721 of the
    // table, which shows every row, R631), a second of the window's thread offscreen
    property var made: ({})
    function keepShown() { if (!made[view]) made = Object.assign({}, made, {[view]: true}) }
    onViewChanged: keepShown()
    Component.onCompleted: keepShown()
    readonly property var unitNow: root.units.find(u => u.number === backend.working) || ({})
    readonly property var chosen: backend.chosen
    property var sheet: ({})
    spacing: Theme.space.L

    function signed(level) {
        // The rich text of ui/plant_page.state_sign: the window's symbol in the line, the words wrap under it.
        const symbol = ({ok: "check", check: "warning", fail: "stop"})[level]
        return symbol ? '<img src="image://meridiana/symbol:' + symbol + '/' + encodeURIComponent(Theme.colors.text.toString()) + '/' + (Theme.dark ? "dark" : "light")
              + '/on" width="13" height="13" style="vertical-align: middle">' : ""
    }
    function esc(text) { return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") }

    // The string chosen (ui/plant_page.ChosenString)
    M.Section {
        id: stringGroup
        objectName: "plant-string-chosen"
        nested: true; collapsible: true
        width: parent.width; visible: root.backend.selected >= 0
        title: qsTr("String chosen"); helpId: "plant.string"
        M.ReadableText {
            objectName: "plant-string-identity"
            width: parent.width; wrapMode: Text.Wrap; textFormat: Text.RichText; textStyle: "body"
            text: "<b style='font-weight:600'>" + root.esc(root.chosen.label || "") + "</b> · " + root.esc(root.chosen.where || "") + " " + root.signed(root.chosen.state)
        }
        M.ReadableText { width: parent.width; text: root.chosen.detail || ""; wrapMode: Text.Wrap; textStyle: "secondary" }
        Repeater {
            model: root.chosen.bars || []
            PlantMargin { required property var modelData; width: parent.width; observation: modelData; colors: root.backend.statusColors }
        }
        Column {
            width: parent.width; spacing: Theme.space.XS
            Repeater {
                model: root.chosen.rows || []
                Column {
                    required property var modelData
                    required property int index
                    width: parent.width; spacing: Theme.space.XS
                    Rectangle { visible: index > 0; width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line }
                    M.ReadableText {
                        width: parent.width; wrapMode: Text.Wrap; textFormat: Text.RichText; textStyle: "secondary"
                        text: (modelData.level ? root.signed(modelData.level) + " " : "") + root.esc(modelData.text)
                    }
                }
            }
        }
        M.ReadableText { width: parent.width; visible: text !== ""; text: root.chosen.source || ""; wrapMode: Text.Wrap; textStyle: "caption" }
        Row {
            // Three on a row: they share the width and never widen the panel (the words are in the tooltips too).
            id: stringButtons
            width: parent.width; spacing: Theme.space.S
            readonly property real share: (width - 2 * spacing) / 3
            M.Button { objectName: "plant-string-redraw"; width: stringButtons.share; padding: Theme.space.XS; text: qsTr("Redraw")
                tip: qsTr("Draw this string again on the plan, from its modules")
                onClicked: root.backend.draw(root.chosen.inverter, root.chosen.mppt, root.backend.selected) }
            M.Button { id: moveTo; objectName: "plant-string-move"; width: stringButtons.share; padding: Theme.space.XS; text: qsTr("Move to…")
                tip: qsTr("The string's menu: the inputs it can go to, and the rest")
                onClicked: stringMenu.popupFor(root.backend.selected, moveTo, 0, moveTo.height) }
            M.Button { objectName: "plant-string-delete"; width: stringButtons.share; padding: Theme.space.XS; text: qsTr("Delete")
                tip: qsTr("This string deleted: its modules stay laid, in no string (Ctrl+Z brings it back)")
                onClicked: root.backend.deleteString(root.backend.selected) }
        }
    }

    // The inverters (R297): the totals, the cards, the commands, the DC/AC ratio on its scale
    Column {
        objectName: "plant-inverters-group"
        width: parent.width; spacing: Theme.space.S
        M.ReadableText {
            objectName: "plant-totals"
            width: parent.width; text: root.plantData.total; wrapMode: Text.Wrap; textStyle: "description"
            HoverHandler { id: totalsHover }
            M.ToolTip { visible: totalsHover.hovered && root.plantData.totalTip !== undefined; text: root.plantData.totalTip || "" }
        }
        Repeater {
            id: units
            property int focusNumber: -1
            model: root.units.filter(u => u.card)
            onItemAdded: (index, card) => {
                if (card.modelData.number === focusNumber) {
                    focusNumber = -1
                    Qt.callLater(() => card.forceActiveFocus(Qt.ShortcutFocusReason))
                }
            }
            PlantInverterCard { width: parent.width; backend: root.backend; actions: root.actions; list: units
                onDatasheet: record => { root.sheet = record; sheetDialog.open() } }
        }
        PlantCommand { width: parent.width; command: "inverter_catalog"; actions: root.actions; onClicked: root.actions.open("catalog") }
        PlantCommand { width: parent.width; command: "inverter_auto"; actions: root.actions; onClicked: root.actions.open("sizing") }
        // R522: the search for the modules in no string ends within its time limit; «Stop» gives the best one found,
        // «Cancel» throws it away
        Column {
            objectName: "plant-search"
            width: parent.width; spacing: Theme.space.S
            visible: root.backend.searchSeconds >= 0
            M.ProgressBar { objectName: "plant-search-progress"; width: parent.width
                value: Math.min(1, Math.max(0, root.backend.searchSeconds / root.backend.searchLimit)) }
            M.ReadableText { objectName: "plant-search-words"; width: parent.width; wrapMode: Text.Wrap; textStyle: "secondary"
                text: qsTr("Searching… {s} of {limit} s").replace("{s}", Math.min(root.backend.searchLimit, Math.floor(Math.max(0, root.backend.searchSeconds)))).replace("{limit}", root.backend.searchLimit) }
            Row {
                spacing: Theme.space.S
                M.Button { objectName: "plant-search-stop"; text: qsTr("Stop the search")
                    tip: qsTr("End the search now and take the best proposal found until then"); onClicked: root.backend.stopSearch() }
                M.Button { objectName: "plant-search-cancel"; flat: true; text: qsTr("Cancel"); onClicked: root.backend.cancelSearch() }
            }
        }
        // R522 r22-impianto: why the proposal for the modules in no string (the ratio of each inverter, the modules
        // left and why), and the other valid ones, each to take in its place
        Column {
            objectName: "plant-free-choice"
            width: parent.width; spacing: Theme.space.S
            visible: !!root.backend.sizingChoice.why && !root.backend.searching
            M.CopyLabel { width: parent.width; textStyle: "strong"; text: qsTr("Inverters sized") }
            M.ReadableText { objectName: "plant-free-why"; width: parent.width; wrapMode: Text.Wrap; textStyle: "secondary"
                text: root.backend.sizingChoice.why || "" }
            M.CopyLabel { width: parent.width; textStyle: "strong"; visible: (root.backend.sizingChoice.alternatives || []).length > 0
                text: qsTr("Other valid proposals") }
            Repeater {
                model: root.backend.sizingChoice.alternatives || []
                Row {
                    required property var modelData
                    width: parent.width; spacing: Theme.space.S
                    M.ReadableText { width: parent.width - useButton.width - Theme.space.S; wrapMode: Text.Wrap; textStyle: "secondary"
                        objectName: "plant-free-alternative" + modelData.index
                        text: modelData.line || (modelData.names + " · DC/AC " + modelData.ratio)
                        HoverHandler { id: alternativeHover }
                        M.ToolTip { visible: alternativeHover.hovered; text: modelData.why } }
                    M.Button { id: useButton; objectName: "plant-free-use" + modelData.index; text: qsTr("Use this")
                        onClicked: root.backend.useSizingAlternative(modelData.index) }
                }
            }
            M.Button { objectName: "plant-free-close"; flat: true; text: qsTr("Close"); onClicked: root.backend.dismissSizing() }
        }
        PlantFormRow {
            objectName: "plant-ratio-row"
            width: parent.width; label: qsTr("DC/AC ratio wanted")
            tip: qsTr("The modules' power over the inverters' AC power: «Choose automatically» picks the size closest to it. The energy cut shows on the scale once the year is computed")
            M.NumberField {
                width: parent.width; minimum: .5; maximum: 2; decimals: 2; stepSize: .05
                value: root.backend.settings.dc_ac
                onValueEdited: value => root.backend.setEnergy("dc_ac_ratio", value)
            }
        }
        PlantClipScale { width: parent.width; backend: root.backend }
    }

    // The strings (R115, R298): the view chosen from the menu beside the «?», the commands at the foot
    M.Section {
        id: stringsSection
        objectName: "plant-strings"
        nested: true; collapsible: true
        width: parent.width; title: qsTr("Strings")
        helpId: "plant.strings"
        M.Button {
            parent: stringsSection; x: parent.width - 16 - Theme.space.XS - width; y: 2; width: 20; height: 20; flat: true; padding: Theme.space.XXS
            objectName: "plant-strings-view"; iconName: root.view === "cards" ? "layout-grid" : root.view === "diagram" ? "rows-3" : "table"
            tip: qsTr("How the strings are shown: the inputs as cards, or a single-line diagram")
            onClicked: views.popup(this, 0, height)
            M.Menu { id: views
                M.MenuItem { objectName: "plant-view-cards"; text: qsTr("Inputs as cards"); checkable: true; checked: root.view === "cards"; onTriggered: root.actions.setStringsView("cards") }
                M.MenuItem { objectName: "plant-view-diagram"; text: qsTr("Single-line diagram in miniature"); checkable: true; checked: root.view === "diagram"; onTriggered: root.actions.setStringsView("diagram") }
                M.MenuItem { objectName: "plant-view-table"; text: qsTr("Table"); checkable: true; checked: root.view === "table"; onTriggered: root.actions.setStringsView("table") }
            }
        }
        M.ReadableText { objectName: "plant-strings-state"; width: parent.width; text: root.plantData.summary || ""; wrapMode: Text.Wrap; textStyle: "description"; visible: text !== "" }
        Row {
            width: parent.width; spacing: Theme.space.S
            M.ComboBox {
                objectName: "plant-working-inverter"
                width: (parent.width - parent.spacing) / 2
                enabled: root.units.length > 0
                value: root.backend.working
                tip: qsTr("The inverter whose inputs and strings are shown (a click on its card does the same)")
                Accessible.name: qsTr("Inverter shown")
                options: root.units.map(u => ({key: u.number, label: u.label}))
                onChosen: value => root.backend.selectUnit(value)
            }
            M.CopyLabel {
                objectName: "plant-working-summary"
                width: (parent.width - parent.spacing) / 2; height: Theme.size.CONTROL
                text: root.unitNow.summary || ""; textStyle: "secondary"; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                HoverHandler { id: summaryHover }
                M.ToolTip { visible: summaryHover.hovered && text !== ""; text: root.unitNow.summaryTip || "" }
            }
        }
        Loader { objectName: "plant-view-cards-part"; width: parent.width; active: root.made.cards === true; visible: root.view === "cards"
            sourceComponent: PlantInputCards { backend: root.backend; menu: stringMenu } }
        Loader { objectName: "plant-view-diagram-part"; width: parent.width; active: root.made.diagram === true; visible: root.view === "diagram"
            sourceComponent: PlantDiagram { backend: root.backend; menu: stringMenu } }
        // R631: every string shown, the panel scrolls (nothing scrolls inside it, R601)
        Loader { objectName: "plant-view-table-part"; width: parent.width; active: root.made.table === true; visible: root.view === "table"
            sourceComponent: PlantTable { id: stringsTable; height: stringsTable.wholeHeight; backend: root.backend } }
        PlantCommand { width: parent.width; command: "strings_auto"; actions: root.actions; onClicked: root.actions.proposal(true) }
        PlantCommand { width: parent.width; command: "strings_manual"; actions: root.actions; onClicked: root.actions.drawNew() }
        PlantCommand { width: parent.width; command: "strings_clear"; actions: root.actions; enabled: root.strings.length > 0; onClicked: root.actions.open("clear") }
    }

    // The conditions of the checks (study 23: what is left of «Proposal and checks»)
    M.Section {
        objectName: "plant-conditions"
        nested: true; collapsible: true
        width: parent.width; title: qsTr("Conditions of the checks")
        helpId: "plant.conditions"
        PlantFormRow {
            width: parent.width; label: qsTr("Lowest temperature of the site"); wrapLabel: true
            M.NumberField { width: parent.width; value: root.backend.settings.t_min; minimum: -40; maximum: 20; decimals: 1; unit: "°C"
                onValueEdited: value => root.backend.setEnergy("t_min", value) }
        }
        M.ReadableText { width: parent.width; wrapMode: Text.Wrap; text: root.plantData.conditionsText || ""; textStyle: "secondary"; visible: text !== "" }
    }

    // The sub-field selected, for the proposal
    M.Section {
        id: subfieldGroup
        objectName: "plant-subfield"
        nested: true; collapsible: true
        width: parent.width; title: qsTr("Sub-field selected")
        helpId: "plant.subfield"
        visible: root.actions.selectedSubfield !== ""
        readonly property var sf: root.backend.subfields.find(s => s.id === root.actions.selectedSubfield) || ({})
        readonly property var unit: root.units.find(u => u.number === sf.inverter)
        readonly property real labels: Math.max(inverterRow.words, inputRow.words)
        M.CopyLabel { width: parent.width; text: subfieldGroup.sf.name || ""; textStyle: "strong"; elide: Text.ElideRight }
        PlantFormRow {
            id: inverterRow
            readonly property real words: Theme.measureText(label, "body").width
            width: parent.width; label: qsTr("Inverter of the proposal"); labelWidth: subfieldGroup.labels
            M.ComboBox { width: parent.width; value: subfieldGroup.sf.inverter || 0
                tip: qsTr("Where «String automatically» sends the strings of this sub-field; the strings of now do not change")
                options: [{key: 0, label: qsTr("automatic")}].concat(root.units.map(u => ({key: u.number, label: u.label})))
                onChosen: value => root.backend.assignSubfield(root.actions.selectedSubfield, value, 0) }
        }
        PlantFormRow {
            id: inputRow
            readonly property real words: Theme.measureText(label, "body").width
            width: parent.width; label: qsTr("Input of the proposal"); labelWidth: subfieldGroup.labels
            M.ComboBox { width: parent.width; enabled: !!subfieldGroup.unit; value: subfieldGroup.sf.mppt || 0
                tip: qsTr("Where «String automatically» sends the strings of this sub-field; the strings of now do not change")
                options: [{key: 0, label: qsTr("automatic")}].concat(Array.from({length: subfieldGroup.unit ? subfieldGroup.unit.inputs : 0},
                    (_v, k) => ({key: k + 1, label: qsTr("Input {k}").replace("{k}", k + 1)})))
                onChosen: value => root.backend.assignSubfield(root.actions.selectedSubfield, subfieldGroup.sf.inverter, value) }
        }
    }

    PlantStringMenu { id: stringMenu; backend: root.backend; actions: root.actions; parent: root }
    M.Dialog {
        id: sheetDialog; objectName: "plant-datasheet-dialog"
        title: qsTr("Datasheet"); rejectText: qsTr("Close")
        implicitWidth: M.ControlMetrics.dialogSize.datasheet.width; implicitHeight: M.ControlMetrics.dialogSize.datasheet.height
        bodyScrolls: false
        ListView {
            clip: true; model: root.backend.recordDetails(root.sheet)
            C.ScrollBar.vertical: M.ScrollBar { id: sheetBar }
            delegate: M.ReadableText { required property var modelData; width: ListView.view.width - sheetBar.room; text: modelData.label + ": " + modelData.value; wrapMode: Text.Wrap; bottomPadding: Theme.space.S }
        }
    }
}
