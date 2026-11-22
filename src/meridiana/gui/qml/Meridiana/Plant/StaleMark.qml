import QtQuick
import Meridiana.Theme

Rectangle {
    required property var backend
    required property string command
    objectName: "stale-" + command
    x: parent ? parent.width-(parent.stripWidth || 0)-width-4 : 0     // R564: on a split button, before its strip
    y: 4; width: 5; height: 5; radius: 2.5
    visible: command === "compute" ? backend.calculateDirty : backend.layoutDirty
    color: Theme.colors.muted
    Accessible.ignored: true
}
