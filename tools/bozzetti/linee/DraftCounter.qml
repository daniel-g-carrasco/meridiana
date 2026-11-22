import QtQuick
import Meridiana.Theme

Rectangle {
    id: root
    required property int count
    property bool current: false
    height: current ? 12.4 : 16
    width: current ? 14.4 : Math.max(height, number.implicitWidth + 8)
    radius: current ? Theme.radius.INNER : height/2
    color: Theme.colors.overlay.badge
    antialiasing: true
    Text {
        id: number
        anchors.centerIn: parent; text: root.count; color: "white"
        font.family: Theme.fontFamily; font.pixelSize: root.current ? 9 : Theme.type.CAPTION
        font.weight: root.current ? Font.Bold : Font.Normal
        font.features: {"tnum": 1}
    }
}
