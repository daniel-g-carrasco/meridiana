import QtQuick
import Meridiana.Theme
Item {
    id: root
    property alias text: main.text
    property alias tip: main.tip
    property alias iconName: main.iconName
    property alias mode: main.mode
    property var model: []
    property alias mainEnabled: main.enabled
    property alias active: main.active
    property alias checked: main.checked
    property bool compact: false
    property bool commandOpensMenu: false
    property var menu: popup
    readonly property bool menuShown: !!menu && menu.visible
    signal clicked()
    signal chosen(int index)
    implicitWidth: main.implicitWidth + (compact ? ControlMetrics.viewArrow : Theme.bar.STRIP)
    implicitHeight: main.implicitHeight
    // R644: one ground for the two halves (SplitGround, the common rule of the split buttons)
    SplitGround { objectName: root.objectName + "Ground"; anchors.fill: parent; split: main.width; on: main.active; commandEnabled: main.enabled
        commandHovered: main.hovered; commandDown: main.down
        arrowHovered: arrow.hovered; arrowDown: arrow.down; menuOpen: root.menuShown }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: arrow.openMenu() }
    ToolButton { id: main; width: parent.width - arrow.width; height: parent.height
        objectName: root.objectName + "Command"
        compact: root.compact
        menu: root.commandOpensMenu ? root.menu : null; menuBelow: root.compact; menuAnchor: root.compact ? root : null
        onClicked: root.clicked()
        background: Item {}
    }
    Button { id: arrow; objectName: root.objectName + "Arrow"; x: main.width
        width: root.compact ? ControlMetrics.viewArrow : Theme.bar.STRIP; height: parent.height; padding: 0; flat: true
        Accessible.name: root.text
        background: Item {}
        contentItem: Item { Arrow { anchors.fill: parent; active: arrow.hovered || arrow.down || root.menuShown } }     // R592
        // R480: the arrow owns the menu: pressed while it is open, a second click closes it
        menu: root.menu; menuBelow: root.compact; menuAnchor: root.compact ? root : null; Keys.onDownPressed: openMenu() }
    Menu { id: popup; y: root.height
        Repeater { model: root.model
            MenuItem { required property var modelData; required property int index
                text: modelData.text; iconName: modelData.icon || ""; enabled: modelData.enabled !== false
                onTriggered: root.chosen(index) }
        }
    }
    Keys.onDownPressed: arrow.openMenu()
}
