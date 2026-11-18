import QtQuick
import QtQuick.Shapes
import Meridiana.Theme

Rectangle {
    id: chart
    objectName: "yearChart"
    color: D.view
    property var yearData: backend.year
    property bool retained: true
    property int pointCount: yearData.points ? yearData.points.length : 0
    Text {
        x: D.pad; y: D.pad
        text: L.year + (chart.yearData.total ? " · " + chart.yearData.total + " kWh" : "")
        font.family: Theme.fontFamily; font.pixelSize: D.heading; color: D.text
    }
    Text { x: D.pad; y: 48; text: L.daily; font.family: Theme.fontFamily; font.pixelSize: D.body; color: D.text2 }
    Item {
        id: plot
        anchors { left: parent.left; right: parent.right; top: parent.top; bottom: parent.bottom
            leftMargin: 64; rightMargin: D.pad; topMargin: 88; bottomMargin: 64 }
        Repeater {
            model: 5
            delegate: Item {
                required property int index
                y: index * plot.height / 4
                width: plot.width
                Rectangle { width: parent.width; height: D.hair; color: D.line_soft }
                Text { x: -60; y: -8; width: 52; horizontalAlignment: Text.AlignRight
                    text: chart.yearData.maximum ? Math.round(chart.yearData.maximum * (1-index/4)).toLocaleString(Qt.locale("it_IT"), 'f', 0) : ""
                    font.family: Theme.fontFamily; font.pixelSize: D.caption; color: D.muted }
            }
        }
        Shape {
            width: chart.retained ? 1000 : plot.width
            height: chart.retained ? 500 : plot.height
            transform: Scale {
                xScale: chart.retained ? plot.width / 1000 : 1
                yScale: chart.retained ? plot.height / 500 : 1
            }
            ShapePath {
                strokeColor: D.accent; strokeWidth: D.focus; fillColor: "transparent"
                PathPolyline {
                    path: chart.yearData.points ? chart.yearData.points.map(p =>
                        Qt.point(p.x*(chart.retained ? 1000 : plot.width), p.y*(chart.retained ? 500 : plot.height))) : []
                }
            }
        }
        Text { anchors.top: parent.bottom; anchors.topMargin: D.gap; text: L.jan; color: D.text2; font.family: Theme.fontFamily; font.pixelSize: D.body }
        Text { anchors.top: parent.bottom; anchors.right: parent.right; anchors.topMargin: D.gap
            text: L.dec; color: D.text2; font.family: Theme.fontFamily; font.pixelSize: D.body }
    }
    Text { anchors { left: parent.left; bottom: parent.bottom; margins: D.pad }
        text: chart.yearData.source || L.calculating; font.family: Theme.fontFamily; font.pixelSize: D.caption; color: D.muted }
}
