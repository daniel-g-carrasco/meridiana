import QtQuick
import Meridiana.Theme

Rectangle {
    id: root
    property int count: 0
    property string value: String(count)
    property color ink: Theme.colors.overlay.pill_ink
    color: Theme.colors.overlay.badge
    implicitHeight: Theme.annotation.COUNT_HEIGHT
    implicitWidth: value.length === 1 ? implicitHeight
                   : Math.max(implicitHeight, number.implicitWidth + 2 * Theme.annotation.COUNT_PAD)
    radius: height / 2
    antialiasing: true
    Text {
        id: number
        anchors.centerIn: parent; text: root.value; color: root.ink
        font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE
        font.weight: Theme.annotation.WEIGHT
        font.features: {"tnum": 1}
    }
}
