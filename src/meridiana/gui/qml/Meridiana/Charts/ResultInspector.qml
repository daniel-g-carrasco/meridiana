import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Properties

// R631: the body of every side panel (M.PanelPage), its margins, gaps and one scroll
M.PanelPage {
    implicitHeight: 0
    id: root
    required property var backend
    readonly property bool prepared: backend.ready
    property var sectionStates: ({})
    function closed(key) { return sectionStates[key] === true }
    function toggle(key) { const next = Object.assign({}, sectionStates); next[key] = !closed(key); sectionStates = next }
    Column {
        id: body
        width: root.pageWidth
        spacing: M.ControlMetrics.panelGap
        ResultForm { width: parent.width; backend: root.backend; sections: root.backend.sections; stateOwner: root }
        M.ReadableText { width: parent.width; visible: text.length > 0; text: root.backend.status; wrapMode: Text.Wrap }
        M.ReadableText { width: parent.width; visible: text.length > 0; text: root.backend.error; wrapMode: Text.Wrap; color: Theme.colors.danger }
    }
    // R598: the editor makes its fields again only while this page is on show; behind another phase or with the
    // panel closed a change costs nothing, and the fields are made when it is shown next
    Binding { target: root.backend; property: "shown"; value: root.parent && root.parent.shown !== undefined ? root.parent.shown && root.parent.visible : root.visible }
    Connections { target: root.backend; function onImportRequested() { curveDialog.open() } }
    Component.onCompleted: if (backend.importPending) curveDialog.open()
    FileDialog {
        id: curveDialog
        title: root.backend.labels.importTitle
        nameFilters: ["CSV (*.csv *.txt)"]
        onAccepted: root.backend.importCurve(selectedFile)
        onVisibleChanged: if (!visible) root.backend.dismissImport()
    }
}
