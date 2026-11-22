import QtQuick
import Meridiana.Theme

Rectangle {
    id: root
    required property string value
    property string badge: ""
    property real direction: 0
    // Use the same QColor conversion as the real view (source alpha is last).
    property color ink: viewPaint.label_fg
    property color ground: viewPaint.label_bg
    property bool smaller: true
    readonly property real oldHeight: oldMetrics.height + 2 * Theme.space.XXS
    height: oldHeight - (smaller ? 1 : 0)
    width: words.implicitWidth + (badge ? height + Theme.space.XS : 2 * Theme.space.S)
    radius: height / 2
    color: ground
    rotation: direction >= 90 ? direction-180 : direction < -90 ? direction+180 : direction
    antialiasing: true
    FontMetrics { id: oldMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
    Rectangle {
        visible: root.badge !== ""
        x: Theme.space.XXS; y: Theme.space.XXS
        height: parent.height - 2*Theme.space.XXS; width: height; radius: height/2
        color: root.ink
        Text {
            anchors.centerIn: parent; text: root.badge; color: root.ground
            font.family: Theme.fontFamily; font.pixelSize: Theme.type.CAPTION - (root.smaller ? 1 : 0)
            font.weight: Font.Normal
        }
    }
    Text {
        id: words
        x: root.badge ? root.height : Theme.space.S
        anchors.verticalCenter: parent.verticalCenter
        text: root.value; color: root.ink
        font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL - (root.smaller ? 1 : 0)
        font.weight: Font.Normal
        font.features: {"tnum": 1}
    }
}
