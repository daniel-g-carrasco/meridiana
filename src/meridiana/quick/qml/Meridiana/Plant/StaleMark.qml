import QtQuick
import Meridiana.Theme

Rectangle {
    required property var backend
    required property string command
    objectName: "stale-" + command
    x: parent ? parent.width-width-4 : 0
    y: 4; width: 5; height: 5; radius: 2.5
    visible: command === "compute" ? backend.calculateDirty : backend.layoutDirty
    color: Theme.colors.muted
    Accessible.ignored: true
}
