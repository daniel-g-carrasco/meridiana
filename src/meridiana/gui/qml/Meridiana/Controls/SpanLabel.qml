import QtQuick
import QtQuick.Controls as C
import Meridiana.Theme
import "LabelPlace.js" as Place

// Compatibility adapter: all view words use the common length pill.
LengthPill {
    id: label
    TextActions { id: measureCopy; target: label; readOnly: true; wholeText: label.shown }
    C.ContextMenu.menu: TextMenu { actions: measureCopy }
    property point a: Qt.point(0, 0)
    property point b: Qt.point(0, 0)
    property color halo: Theme.colors.view
    property rect room: Qt.rect(0, 0, 0, 0)
    property real gap: ControlMetrics.measureTextGap
    property real pointGap: ControlMetrics.measureMark/2 + gap
    property bool along: true
    property var place: null
    readonly property var spot: along && place ? place
        : along ? Place.along(a, b, implicitWidth, implicitHeight, gap, pointGap, room, Theme.space.XS)
        : ({x: x + width/2, y: y + height/2, angle: 0, box: {x: x, y: y, width: width, height: height}})
    readonly property var box: spot.box
    x: along ? spot.x - implicitWidth/2 : 0
    y: along ? spot.y - implicitHeight/2 : 0
    direction: along ? spot.angle : 0
}
