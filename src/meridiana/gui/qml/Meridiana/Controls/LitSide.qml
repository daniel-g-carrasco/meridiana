import QtQuick
import Meridiana.Theme

// The common side highlight, in screen pixels.
ViewStroke {
    id: root
    property point a: Qt.point(0, 0)
    property point b: Qt.point(0, 0)
    points: [a, b]
}
