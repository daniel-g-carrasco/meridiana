import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Catalog

Item {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var units: backend.units
    readonly property var chosen: backend.chosen
    required property var actions
    FileDialog {
        title: root.backend.tr("Import from PVsyst…")
        nameFilters: root.actions.importKind === "modules" ? ["PVsyst (*.pan *.PAN)"] : ["PVsyst (*.ond *.OND)"]
        visible: root.actions.dialog === "pvsyst_file"
        onAccepted: root.actions.readPvsyst(selectedFile)
        onRejected: root.actions.dismiss()
    }
    M.Dialog {
        parent: C.Overlay.overlay; anchors.centerIn: parent
        width: Math.min(600, parent.width-32)
        title: root.backend.tr("Import from PVsyst…")
        visible: root.actions.dialog === "pvsyst_review"
        acceptText: root.backend.tr("Yes"); rejectText: root.backend.tr("No")
        onAccepted: root.actions.acceptPvsyst()
        onRejected: root.actions.dismiss()
        contentItem: M.Label { text: root.actions ? root.actions.importText || "" : ""; wrapMode: Text.Wrap }
    }
    M.Dialog {
        id: catalogue
        objectName: "plant-catalog-dialog"
        parent: C.Overlay.overlay; anchors.centerIn: parent
        title: root.backend.tr("Catalogue: {what}").replace("{what}", catalogBackend.choices.kinds.find(k=>k.key===catalogBackend.kind).text)
        width: Math.min(1280, parent.width - 32); height: Math.min(820, parent.height - 32)
        visible: root.actions.dialog === "catalog"
        onClosed: if (root.actions.dialog === "catalog") root.actions.dismiss()
        rejectText: root.backend.tr("Close")
        acceptText: catalogBackend.texts.choose; acceptEnabled: catalogBackend.canChoose; acceptOnReturn: false
        acceptCheck: () => { catalogBackend.choose(); return false }
        actions: catalogPage.windowActions
        onActionTriggered: index => catalogPage.windowAction(index)
        contentItem: CatalogPage { id: catalogPage; backend: catalogBackend; embedded: true; windowButtons: true }
    }
    M.Dialog {
        id: storageDialog
        objectName: "plant-storage-dialog"
        parent: C.Overlay.overlay; anchors.centerIn: parent
        title: root.backend.tr("Storage"); rejectText: root.backend.tr("Close")
        width: Math.min(620, parent.width - 32); height: Math.min(720, parent.height - 32)
        visible: root.actions.dialog === "storage"
        onClosed: if (root.actions.dialog === "storage") root.actions.dismiss()
        // R518: apply and remove on the window's row of buttons
        acceptText: root.backend.tr("Apply storage configuration"); acceptEnabled: storage.check.valid; acceptOnReturn: false
        acceptCheck: () => { root.backend.applyStorage(storage.patch); return false }
        actions: [{text: root.backend.tr("Remove storage")}]
        onActionTriggered: { root.backend.removeStorage(); storage.battery = ({}) }
        contentItem: PlantStorage { id: storage; windowButtons: true; backend: root.backend; battery: root.actions.battery; revision: root.actions.storageRevision }
    }
    M.Dialog {
        id: proposalDialog
        objectName: "plant-proposal-dialog"
        // ui/window.py _stringing_popup: the modules are chosen on the plan while it is open.
        // Not CloseOnEscape: Qt would then block every shortcut of the window while it is open.
        parent: C.Overlay.overlay; modal: false; closePolicy: C.Popup.NoAutoClose
        width: Math.min(M.ControlMetrics.dialogWidth.normal, parent.width - 2 * M.ControlMetrics.dialogEdge); margins: M.ControlMetrics.dialogEdge
        title: root.backend.tr("String automatically")
        acceptText: root.backend.tr("String"); rejectText: root.backend.tr("Cancel"); acceptEnabled: !root.backend.searching
        onAccepted: contentItem.submit()
        onRejected: root.actions.dismiss()
        x: Math.max(16, parent.width - width - (parent.Window.window && parent.Window.window.rightWidth !== undefined ? parent.Window.window.rightWidth : 0) - 2*Theme.layout.GAP - Theme.layout.EDGE)
        y: Math.min(120, Math.max(16, parent.height - height - 16))
        visible: root.actions.dialog === "proposal"
        onAboutToShow: { contentItem.scope = root.actions.proposalScope; contentItem.replace = root.actions.replace; contentItem.visible = true }
        Shortcut { sequence: "Esc"; enabled: proposalDialog.visible; onActivated: root.actions.dismiss() }
        Binding { target: proposalDialog.parent ? proposalDialog.parent.Window.window : null; property: "escTaken"; value: proposalDialog.visible }
        onClosed: if (root.actions.dialog === "proposal") root.actions.dismiss()
        contentItem: PlantProposal {
            backend: root.backend; selectedModules: root.actions.dialog === "proposal" ? root.actions.selectedModules : []; replace: root.actions.replace
            visible: true
            onClosed: root.actions.dismiss()
            onSubmitted: options => { root.backend.proposeConfigured(options); root.actions.dismiss() }
        }
    }
    M.Dialog {
        id: clearDialog
        objectName: "plant-clear-dialog"
        parent: C.Overlay.overlay; anchors.centerIn: parent
        visible: root.actions.dialog === "clear"
        title: root.backend.tr("Delete all the strings")
        rejectText: root.backend.tr("Cancel"); acceptText: root.backend.tr("Continue")
        onAccepted: { root.backend.clearStrings(); root.actions.dismiss() }
        onRejected: root.actions.dismiss()
        onClosed: if (root.actions.dialog === "clear") root.actions.dismiss()
        contentItem: M.Label { text: root.backend.tr("The existing strings will be replaced. Undo restores the previous wiring."); wrapMode: Text.Wrap }
    }
    M.Dialog {
        id: makerDialog
        objectName: "plant-maker-dialog"
        parent: C.Overlay.overlay; anchors.centerIn: parent
        title: root.backend.tr("Size the inverter by itself")
        rejectText: root.backend.tr("Cancel"); acceptText: root.backend.tr("Choose")
        width: Math.min(420, parent.width - 32)
        visible: root.actions.dialog === "sizing"
        onOpened: makerSearch.forceActiveFocus()
        onClosed: if (root.actions.dialog === "sizing") root.actions.dismiss()
        onAccepted: choose()
        readonly property bool freeOnly: onlyFree.visible && onlyFree.checked
        function choose() { if (makers.currentItem) { root.backend.sizeInvertersFor(makers.currentItem.modelData.label, freeOnly); root.actions.dismiss() } }
        function star() { if (makers.currentItem) root.backend.toggleFavourite(makers.currentItem.modelData.label) }
        function fold(text) { return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase() }
        contentItem: ColumnLayout {
            spacing: Theme.space.M
            // R522: the modules in no string only, the strings and inverters there are kept (on by itself when some are left)
            M.CheckBox {
                id: onlyFree; objectName: "sizing-only-free"; Layout.fillWidth: true
                visible: root.backend.freeModules > 0
                checked: root.actions.onlyFree
                text: root.backend.freeModules === 1 ? root.backend.tr("Only the module in no string")
                    : root.backend.tr("Only the {n} modules in no string").replace("{n}", root.backend.freeModules)
            }
            // R522 (Daniel 07/11/2026 «solo marche preferite»): for the modules in no string the preferred manufacturers
            // only (catalog/data/preferred_makers.json and the stars); with none, said here
            M.Label {
                objectName: "sizing-free-preferred"; Layout.fillWidth: true; wrapMode: Text.WordWrap; textStyle: "secondary"
                visible: makerDialog.freeOnly
                text: root.backend.makers.some(m => m.preferred)
                    ? root.backend.tr("Only the preferred manufacturers, within {s} seconds: the best proposal found is given.").replace("{s}", root.backend.searchLimit)
                    : root.backend.tr("No preferred manufacturer is in the catalogue: switch off the box above, mark one with its star and switch it on again.")
            }
            M.TextField {
                id: makerSearch; objectName: "maker-search"; Layout.fillWidth: true
                placeholderText: root.backend.tr("Search a manufacturer")
                Keys.onDownPressed: makers.currentIndex = Math.min(makers.count - 1, makers.currentIndex + 1)
                Keys.onUpPressed: makers.currentIndex = Math.max(0, makers.currentIndex - 1)
                Keys.onReturnPressed: makerDialog.choose()
                Keys.onEscapePressed: event => { if (text) { text = ""; event.accepted = true } else root.actions.dismiss() }
                Keys.onPressed: event => {
                    if (event.key === Qt.Key_PageDown) { makers.currentIndex = Math.min(makers.count-1, makers.currentIndex+7); event.accepted = true }
                    if (event.key === Qt.Key_PageUp) { makers.currentIndex = Math.max(0, makers.currentIndex-7); event.accepted = true }
                    if (event.key === Qt.Key_D && (event.modifiers & Qt.ControlModifier)) { makerDialog.star(); event.accepted = true }
                }
            }
            // The list of the Widgets window (ui/brand_picker.py, R458 voce 9): the favourites under their heading, then
            // every manufacturer in alphabetical order, those that cannot be sized dimmed and last, each with its star;
            // rows as those of the other lists of the program (select_bg on the current one), not buttons.
            ListView {
                id: makers; objectName: "maker-list"; Layout.fillWidth: true
                Layout.preferredHeight: Math.min(9, Math.max(1, count + (makers.hasFavourites ? 2 : 0))) * Theme.size.CONTROL
                clip: true; reuseItems: true; currentIndex: 0
                readonly property string favouritesTitle: root.backend.tr("Favourites")
                readonly property string othersTitle: root.backend.tr("All manufacturers")
                readonly property bool hasFavourites: model.some(m => m.favourite)
                model: root.backend.makers.filter(m => (!makerDialog.freeOnly || m.preferred) && makerDialog.fold(m.label).includes(makerDialog.fold(makerSearch.text)))
                    .map(m => Object.assign({group: m.favourite ? makers.favouritesTitle : makers.othersTitle}, m))
                onModelChanged: currentIndex = Math.max(0, model.findIndex(m => m.label === root.backend.settings.maker))
                onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
                C.ScrollBar.vertical: M.ScrollBar { id: makersBar }
                section.property: makers.hasFavourites ? "group" : ""
                section.delegate: M.Label {
                    required property string section
                    width: makers.width - makersBar.room; height: Theme.size.CONTROL; verticalAlignment: Text.AlignVCenter
                    leftPadding: Theme.space.S; text: section; textStyle: "caption"; color: Theme.colors.text2
                }
                delegate: Rectangle {
                    id: makerRow
                    required property var modelData
                    required property int index
                    objectName: "maker-row-" + modelData.label
                    width: makers.width - makersBar.room; height: Theme.size.CONTROL; radius: Theme.radius.INNER
                    color: index === makers.currentIndex ? Theme.colors.select_bg : rowMouse.containsMouse ? Theme.colors.hover : "transparent"
                    MouseArea {
                        id: rowMouse; anchors.fill: parent; hoverEnabled: true
                        onClicked: makers.currentIndex = makerRow.index
                        onDoubleClicked: { makers.currentIndex = makerRow.index; makerDialog.choose() }
                    }
                    M.Label {
                        anchors.left: parent.left; anchors.leftMargin: Theme.space.S; anchors.right: star.left
                        anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight
                        text: makerRow.modelData.label
                        color: makerRow.modelData.sizable ? Theme.colors.text : Theme.colors.muted
                    }
                    M.ToolTip { visible: rowMouse.containsMouse && !!makerRow.modelData.reason; text: makerRow.modelData.reason || "" }
                    M.Button { id: star; anchors.right: parent.right; width: Theme.size.CONTROL; height: parent.height
                        flat: true; iconName: makerRow.modelData.favourite ? "control:star-full" : "control:star"; Accessible.name: tip; tip: root.backend.tr("Favourites")
                        onClicked: root.backend.toggleFavourite(makerRow.modelData.label) }
                }
            }
        }
    }
    M.Dialog {
        id: groupsDialog
        parent: C.Overlay.overlay; anchors.centerIn: parent
        objectName: "plant-groups-dialog"
        width: Math.min(M.ControlMetrics.dialogWidth.normal, parent.width - 2 * M.ControlMetrics.dialogEdge); height: Math.min(540, parent.height - 2 * M.ControlMetrics.dialogEdge)
        title: root.backend.tr("Modules on each optimizer")
        acceptText: root.backend.tr("Apply"); rejectText: root.backend.tr("Cancel"); acceptEnabled: grouping.valid
        onAccepted: grouping.apply()
        onRejected: root.actions.dismiss()
        visible: root.actions.dialog === "groups"
        onOpened: {
            const unit = root.units.find(u => u.number === root.chosen.inverter)
            grouping.prepare(root.chosen.keys || [], unit ? unit.per : 1, root.chosen.groups || [], root.backend.selected)
        }
        onClosed: if (root.actions.dialog === "groups") root.actions.dismiss()
        contentItem: PlantOptimizerGroups {
            id: grouping; backend: root.backend
            onVisibleChanged: if (!visible && root.actions && root.actions.dialog === "groups") root.actions.dismiss()
        }
    }
}
