import QtQuick
import Meridiana.Theme

Rectangle {
    id: root
    property color ink: Theme.colors.overlay.pill_ink
    width: Theme.annotation.POINT; height: width; radius: width/2
    color: ink
    antialiasing: true
    Rectangle {
        anchors.centerIn: parent
        width: root.width + Theme.annotation.HALO_EXTRA; height: width; radius: width/2
        color: Qt.rgba(0,0,0,Theme.annotation.HALO_ALPHA)
        z: -1
        antialiasing: true
    }
}
