import QtQuick
import QtQuick.Shapes
import QtQuick.Templates as T
import Meridiana.Theme
T.MenuItem {
    id: root
    property string iconName: ""
    property string shortcutText: text.indexOf("\t") >= 0 ? text.split("\t")[1] : action && action.shortcut ? action.shortcut.toString() : ""
    property string tip: ""
    readonly property bool hasIcons: {
        if (!menu) return iconName !== ""
        for (let i=0; i<menu.count; i++) {
            const entry = menu.itemAt(i)
            if (entry && entry.iconName) return true
        }
        return false
    }
    readonly property real markerWidth: hasIcons ? Theme.icon.CONTROL : 12
    readonly property real markerGap: hasIcons ? Theme.space.M : Theme.space.S
    readonly property string caption: text.split("\t")[0].replace(/&(.)/g, "$1")
    implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
    implicitHeight: Math.ceil(Theme.measureText(caption, "body").height) + 2 * ControlMetrics.menuItemPadV
    padding: ControlMetrics.menuItemPadV
    leftPadding: Theme.space.XS
    rightPadding: Theme.space.XXL + Theme.space.XS
    hoverEnabled: true
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    contentItem: Item {
        implicitWidth: root.markerWidth + root.markerGap + word.implicitWidth + (keys.text ? Theme.space.XXL + keys.implicitWidth : 0)
        implicitHeight: word.implicitHeight
        Item { width: root.markerWidth; height: width; anchors.verticalCenter: parent.verticalCenter
            Icon { anchors.fill: parent; name: root.iconName; visible: !root.checked; color: root.enabled ? Theme.colors.text : Theme.disabledText }
            CheckMark { anchors.fill: parent; visible: root.checked; color: root.enabled ? Theme.colors.text : Theme.disabledText }
        }
        Label { id: word; x: root.markerWidth + root.markerGap; width: Math.max(0, parent.width-x-(keys.text ? keys.implicitWidth+Theme.space.XXL : 0))
            text: root.caption; enabled: root.enabled; height: parent.height; elide: Text.ElideRight }
        Label { id: keys; anchors.right: parent.right; height: parent.height; text: root.shortcutText; enabled: root.enabled }
    }
    // R21-F3: the submenu's arrow is the sections' chevron, drawn once by the provider (it was a triangle in a Shape)
    arrow: Icon { visible: root.subMenu !== null; width: 14; height: 14
        x: root.width-width-Theme.space.M+5; y: (root.height-height)/2
        name: "control:chevron-right"; color: root.enabled ? Theme.colors.muted : Theme.disabledText }
    background: Rectangle { objectName: "menuItemGround"; radius: ControlMetrics.menuItemRadius
        color: root.enabled && (root.highlighted || root.hovered) ? Theme.colors.hover : "transparent"
    }
    ToolTip { parent: root; text: root.tip; visible: root.hovered && text !== "" }
}
