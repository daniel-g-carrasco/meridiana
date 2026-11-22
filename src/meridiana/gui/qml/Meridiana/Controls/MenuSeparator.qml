import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.MenuSeparator {
    implicitHeight: 2*Theme.space.XS + Theme.line.HAIR
    padding: Theme.space.XS
    // R662: as far in as the entries' content (MenuItem's rule), on both sides
    leftPadding: ControlMetrics.menuItemPadH
    rightPadding: ControlMetrics.menuItemPadH
    contentItem: Rectangle { objectName: "menuRule"; implicitHeight: Theme.line.HAIR; color: Theme.colors.line }
}
