import QtQuick
import QtQuick.Shapes
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
    property alias menu: popup
    signal clicked()
    signal chosen(int index)
    implicitWidth: main.implicitWidth + Theme.bar.STRIP
    implicitHeight: main.implicitHeight
    Rectangle { x: main.enabled ? 0 : main.width; width: main.enabled ? root.width : arrow.width; height: root.height; radius: Theme.radius.CONTROL
        color: root.enabled && (main.hovered || arrow.hovered || popup.visible) ? Theme.colors.hover : "transparent" }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: popup.open() }
    ToolButton { id: main; width: parent.width - arrow.width; height: parent.height
        onClicked: root.clicked()
        background: Item { clip: true
            Rectangle { width: parent.width+Theme.radius.CONTROL; height: parent.height; radius: Theme.radius.CONTROL
                color: !main.enabled ? "transparent" : main.down || main.active ? Theme.colors.press : main.hovered ? Theme.colors.hover : "transparent" }
        }
    }
    Button { id: arrow; x: main.width; width: Theme.bar.STRIP; height: parent.height; padding: 0; flat: true
        Accessible.name: root.text
        background: Item { clip: true
            Rectangle { x: -Theme.radius.CONTROL; width: parent.width+Theme.radius.CONTROL; height: parent.height; radius: Theme.radius.CONTROL
                color: arrow.down || popup.visible ? Theme.colors.press : arrow.hovered ? Theme.colors.hover : "transparent" }
        }
        contentItem: Item { Shape { anchors.centerIn: parent; width: 8; height: 8
            ShapePath { strokeWidth: Theme.icon.STROKE; strokeColor: arrow.hovered || arrow.down ? Theme.colors.text : Theme.colors.text2
                fillColor: "transparent"; capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                startX: 1; startY: 2.5; PathLine { x: 4; y: 5.5 } PathLine { x: 7; y: 2.5 }
            }
        } }
        // R480: the arrow owns the menu: pressed while it is open, a second click closes it
        menu: popup; menuBelow: false; Keys.onDownPressed: openMenu() }
    Menu { id: popup; y: root.height
        Repeater { model: root.model
            MenuItem { required property var modelData; required property int index
                text: modelData.text; iconName: modelData.icon || ""; enabled: modelData.enabled !== false
                onTriggered: root.chosen(index) }
        }
    }
    Keys.onDownPressed: arrow.openMenu()
}
