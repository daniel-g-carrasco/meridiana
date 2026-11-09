import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Properties

// ui/plant_page.PlantSide (R277): one page with three sections in the order of the work, one open at a time, as tall
// as what it holds and scrolling only when that does not fit (R337); what is left of the panel is below them, out of
// every frame. The space is shared here and nothing is laid under the sections: the backend's sentences go to the
// status bar, as the window's do (R406).
Item {
    id: root
    objectName: "plant-inspector"
    property var backend: plantBackend
    property var actions: plantActions
    property var sectionStates: ({})
    function closed(key) { return sectionStates[key] === true }
    function toggle(key) { const next = Object.assign({}, sectionStates); next[key] = !closed(key); sectionStates = next }
    readonly property real headHeight: Math.ceil(Theme.measureText("Hg", "body").height) + Theme.space.M
    // The room of the one open: the panel less the three heads, their lines and the two gaps (PlantSide.room_for).
    readonly property real room: Math.max(0, height - 3 * (headHeight + Theme.line.HAIR) - 2 * Theme.space.S)
    Column {
        anchors.fill: parent
        spacing: Theme.space.S
        Repeater {
            model: [{key: "panels", text: root.backend.tr("Panels"), help: ""},
                    {key: "inverter", text: root.backend.tr("Inverter"), help: "plant.inverters"},
                    {key: "storage", text: root.backend.tr("Storage"), help: ""}]
            // F5: the one section (M.Section), opened by its owner: one at a time, the panel's actions say which
            M.Section {
                id: section
                required property var modelData
                width: parent.width
                title: modelData.text
                headName: "plant-section-" + modelData.key
                density: "flush"
                expanded: root.actions.section === modelData.key
                helpId: modelData.help
                helpTip: modelData.help !== "" ? root.actions.helpTip(modelData.help) : ""
                onToggled: root.actions.toggleSection(modelData.key)
                onHelpRequested: id => root.actions.help(id)
                Loader {
                    id: body
                    width: parent.width
                    height: Math.min(item ? item.implicitHeight : 0, root.room)
                    sourceComponent: section.modelData.key === "panels" ? panels : section.modelData.key === "inverter" ? inverters : storageSummary
                }
            }
        }
    }
    Component {
        id: panels
        M.ScrollPage {
            // R523: what the form below changes, said first: the defaults of the next sub-fields when no sub-field
            // is selected, else the sub-field in hand
            M.Label {
                objectName: "plant-panels-heading"
                width: parent.width
                text: plantPanels.heading
                wrapMode: Text.Wrap; textStyle: "strong"; bottomPadding: Theme.space.S
            }
            // One form for each shape the panels backend has shown, built once and kept, as PropertiesPage does: a
            // selection changes the values of fields already built (06/11/2026, R465: the form of the sub-field was
            // made again at every selection anywhere in the program, 0.2-0.5 s each time).
            ListModel { id: plantForms }
            Connections { target: plantPanels; function onFormAdded(key) { plantForms.append({key: key}) } }
            Item {
                id: keptForms
                width: parent.width
                height: 0
                Component.onCompleted: { for (const key of plantPanels.formKeys) plantForms.append({key: key}) }
                Repeater {
                    model: plantForms
                    delegate: PropertyForm {
                        required property string key
                        readonly property bool shown: plantPanels.currentForm === key
                        visible: shown
                        interactive: shown
                        // Only the form on show follows the width: the kept ones would lay themselves out at every
                        // step of a resize (R470).
                        width: shown ? keptForms.width : 0; lent: true
                        sections: plantPanels.formSections(key); backend: plantPanels; stateOwner: root
                        function place() { if (shown) keptForms.height = height }
                        onShownChanged: place()
                        onHeightChanged: place()
                        Component.onCompleted: place()
                    }
                }
            }
        }
    }
    Component { id: inverters; PlantInverters { backend: root.backend; actions: root.actions } }
    Component {
        id: storageSummary
        M.ScrollPage {
            M.Label {
                width: parent.width; wrapMode: Text.Wrap; textStyle: "description"
                text: root.actions.storageSummary
                HoverHandler { id: summaryHover }
                M.ToolTip { visible: summaryHover.hovered; text: root.actions.storageSummary }
            }
            PlantCommand { width: parent.width; command: "battery_catalog"; actions: root.actions; onClicked: root.actions.open("storage") }
        }
    }
    PlantDialogs { backend: root.backend; actions: root.actions }
}
