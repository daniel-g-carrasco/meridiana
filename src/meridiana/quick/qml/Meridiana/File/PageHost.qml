import QtQuick
import Meridiana.Theme

Window {
    id: window
    objectName: "pageWindow"
    property string activePage: pageName
    width: pageWidth; height: pageHeight; visible: true
    title: "Meridiana"; color: Theme.colors.window
    FilePage {
        id: filePage
        anchors.fill: parent; anchors.margins: Theme.space.M
        backend: filesPageBackend
        settingsBackend: settingsPageBackend
        dialogsBackend: dialogsPageBackend
        visible: window.activePage === "file" || window.activePage.indexOf("settings") === 0
        onClosed: window.close()
    }
    Loader {
        id: standalone
        anchors.fill: parent; anchors.margins: Theme.space.M
        active: !filePage.visible
        property string requestedSource: !active ? "" : window.activePage === "report" ? "../Report/ReportPage.qml" : "../Dialogs/DialogsPage.qml"
        onRequestedSourceChanged: setSource(requestedSource, {backend: window.activePage === "report" ? reportPageBackend : dialogsPageBackend})
        Component.onCompleted: setSource(requestedSource, {backend: window.activePage === "report" ? reportPageBackend : dialogsPageBackend})
    }
}
