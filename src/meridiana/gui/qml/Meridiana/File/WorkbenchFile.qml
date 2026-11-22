import QtQuick

FilePage {
    anchors.fill: parent
    backend: filesBackend
    settingsBackend: filesSettingsBackend
    dialogsBackend: filesDialogsBackend
    onClosed: filePart.closeFile()
    onVisibleChanged: if (visible) enter()
    Component.onCompleted: if (visible) enter()
}
