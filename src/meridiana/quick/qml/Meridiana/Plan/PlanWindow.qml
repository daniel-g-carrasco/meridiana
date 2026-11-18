import QtQuick
import QtQuick.Controls

ApplicationWindow {
    width: 1366; height: 900
    visible: true
    title: "Meridiana"
    Plan { anchors.fill: parent; backend: planBackend }
}
