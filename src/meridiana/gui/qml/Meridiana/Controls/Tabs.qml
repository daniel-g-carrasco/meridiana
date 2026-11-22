import QtQuick
import Meridiana.Theme
Segments {
    dimDisabled: false
    segmentExtra: 0
    padding: Theme.space.XS
    leftPadding: Theme.space.XXS
    rightPadding: Theme.space.XXS
    implicitHeight: Theme.size.CHIP + 2*Theme.space.XS
    background: Rectangle { y: Theme.space.XXS; height: parent.height-2*y
        radius: Theme.radius.CONTROL; color: Theme.colors.field }
}
