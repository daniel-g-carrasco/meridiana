import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.MenuSeparator {
    implicitHeight: 2*Theme.space.XS + Theme.line.HAIR
    padding: Theme.space.XS
    leftPadding: Theme.space.M
    rightPadding: Theme.space.M
    contentItem: Rectangle { implicitHeight: Theme.line.HAIR; color: Theme.colors.line }
}
