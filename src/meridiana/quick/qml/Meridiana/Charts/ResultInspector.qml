import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Properties

M.ScrollPage {
    leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0; groundAbove: true
    id: root
    required property var backend
    property var sectionStates: ({})
    function closed(key) { return sectionStates[key] === true }
    function toggle(key) { const next = Object.assign({}, sectionStates); next[key] = !closed(key); sectionStates = next }
    Column {
        id: body
        width: root.width - Theme.size.SCROLLBAR
        spacing: Theme.space.S
        ResultForm { width: parent.width; backend: root.backend; sections: root.backend.sections; stateOwner: root }
        M.Label { x: Theme.space.L; width: parent.width-2*x; visible: text.length > 0; text: root.backend.status; wrapMode: Text.Wrap }
        M.Label { x: Theme.space.M; width: parent.width - 2*x; visible: text.length > 0; text: root.backend.error; wrapMode: Text.Wrap; color: Theme.colors.danger }
    }
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
