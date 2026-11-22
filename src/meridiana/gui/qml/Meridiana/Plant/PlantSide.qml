import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Properties

// ui/plant_page.PlantSide (R277): one page with three sections in the order of the work, one open at a time. R631
// (Daniel 15/11/2026: «come mai i margini della scheda destra ... sono molto diversi da quella in Impianto?»): the
// panel's body is the one of every side panel, M.PanelPage, the only scroll of the panel; the open section is as tall
// as what it holds, nothing scrolls inside it (R601), and its groups are nested sections (the title on its line). The
// backend's sentences go to the status bar, as the window's do (R406).
Item {
    id: root
    objectName: "plant-inspector"
    property var backend: plantBackend
    property var actions: plantActions
    property var sectionStates: ({})
    function closed(key) { return sectionStates[key] === true }
    function toggle(key) { const next = Object.assign({}, sectionStates); next[key] = !closed(key); sectionStates = next }
    // another section opened: the page from its top, where the three heads are
    readonly property string openSection: actions.section
    onOpenSectionChanged: page.contentY = 0
    M.PanelPage {
        id: page
        objectName: "plant-page"
        anchors.fill: parent
        Repeater {
            model: [{key: "panels", text: qsTr("Modules"), help: ""},
                    {key: "inverter", text: qsTr("Inverter"), help: "plant.inverters"},
                    {key: "storage", text: qsTr("Storage"), help: ""}]
            // F5: the one section (M.Section), opened by its owner: one at a time, the panel's actions say which
            M.Section {
                id: section
                required property var modelData
                width: parent.width
                title: modelData.text
                headName: "plant-section-" + modelData.key
                density: "form"
                expanded: root.actions.section === modelData.key
                helpId: modelData.help
                onToggled: root.actions.toggleSection(modelData.key)
                // R625 (Daniel 15/11/2026, «NON SI APRE LA SCHEDA INVERTER»): made inside the panel warmed in the
                // background, Qt could throw it away half made and the section opened on nothing; made again whole
                // when the section is opened (M.WholeLoader)
                M.WholeLoader {
                    id: body
                    objectName: "plant-section-body-" + section.modelData.key
                    // an empty body has no height, and its section stays shut on nothing: seen when its section is open
                    shown: section.expanded && root.visible
                    width: parent.width
                    height: item ? item.implicitHeight : 0
                    sourceComponent: section.modelData.key === "panels" ? panels : section.modelData.key === "inverter" ? inverters : storageSummary
                }
            }
        }
    }
    Component {
        id: panels
        Column {
            spacing: Theme.space.S
            // R523: what the form below changes, said first: the defaults of the next sub-fields when no sub-field
            // is selected, else the sub-field in hand
            M.ReadableText {
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
                // R598: a new form made a slice at a time (an asynchronous Loader), the one on show kept meanwhile,
                // as PropertiesPage does
                property string shownForm: ""
                property var readyForms: ({})
                function formMade(key) {
                    let ready = Object.assign({}, readyForms)
                    ready[key] = true
                    readyForms = ready
                    follow()
                }
                function follow() { if (readyForms[plantPanels.currentForm] === true) shownForm = plantPanels.currentForm }
                Connections { target: plantPanels; function onFormChanged() { keptForms.follow() } }
                Repeater {
                    model: plantForms
                    delegate: Item {
                        id: kept
                        required property string key
                        readonly property bool shown: keptForms.shownForm === key
                        visible: shown
                        // Only the form on show follows the width: the kept ones would lay themselves out at every
                        // step of a resize (R470).
                        width: shown ? keptForms.width : 0
                        height: made.item ? made.item.height : 0
                        function place() { if (shown) keptForms.height = height }
                        onShownChanged: place()
                        onHeightChanged: place()
                        Loader {
                            id: made
                            asynchronous: GraphicsInfo.api !== GraphicsInfo.Software
                            sourceComponent: PropertyForm {
                                width: kept.width; lent: true; interactive: kept.shown
                                sections: plantPanels.formSections(kept.key); backend: plantPanels; stateOwner: root
                            }
                            onLoaded: { kept.place(); keptForms.formMade(kept.key) }
                        }
                    }
                }
            }
        }
    }
    Component { id: inverters; PlantInverters { backend: root.backend; actions: root.actions } }
    Component {
        id: storageSummary
        Column {
            spacing: Theme.space.S
            M.ReadableText {
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
