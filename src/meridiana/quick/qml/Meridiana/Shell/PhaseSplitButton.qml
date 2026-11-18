import QtQuick
import QtQuick.Shapes
import QtQml.Models
import Meridiana.Theme
import Meridiana.Controls as M

// Ribbon-specific adapter: the shared split control does not expose action
// tips, destructive separators or the opening-on-press behaviour of R364.
Item {
    id: root
    property alias text: main.text
    property alias tip: main.tip
    property alias iconName: main.iconName
    property alias mode: main.mode
    property alias mainEnabled: main.enabled
    property alias active: main.active
    property var model: []
    property string stripTip: ""
    property bool stripActive: false
    property real stripWidth: Theme.bar.STRIP
    property alias menu: popup
    readonly property bool menuOpened: popup.visible
    function dismissMenu() { popup.close() }
    signal clicked()
    signal chosen(int index)
    implicitWidth: main.implicitWidth+stripWidth
    implicitHeight: main.implicitHeight
    Rectangle { anchors.fill: parent; radius: Theme.radius.CONTROL
        color: root.enabled && (main.hovered || arrow.hovered || popup.visible) ? Theme.colors.hover : "transparent" }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: arrow.openMenu() }
    M.ToolButton {
        id: main; width: parent.width-arrow.width; height: parent.height; focusPolicy: Qt.NoFocus
        onClicked: root.clicked()
        background: Item { clip: true
            Rectangle { width: parent.width+Theme.radius.CONTROL; height: parent.height; radius: Theme.radius.CONTROL
                color: !main.enabled ? "transparent" : main.down || main.active ? Theme.colors.press : main.hovered ? Theme.colors.hover : "transparent" }
        }
    }
    M.Button {
        id: arrow; objectName: root.objectName+"Arrow"; x: main.width; width: root.stripWidth; height: parent.height
        padding: 0; flat: true; focusPolicy: Qt.NoFocus; tip: root.stripTip; Accessible.name: tip
        background: Item { clip: true
            Rectangle { x: -Theme.radius.CONTROL; width: parent.width+Theme.radius.CONTROL; height: parent.height; radius: Theme.radius.CONTROL
                color: arrow.down || popup.visible || root.stripActive ? Theme.colors.press : arrow.hovered ? Theme.colors.hover : "transparent" }
        }
        contentItem: Item { Shape { anchors.centerIn: parent; width: 8; height: 8; preferredRendererType: Shape.CurveRenderer
            ShapePath { strokeWidth: Theme.icon.STROKE; strokeColor: arrow.hovered || arrow.down || popup.visible ? Theme.colors.text : Theme.colors.text2
                fillColor: "transparent"; capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                startX: 1; startY: 2.5; PathLine { x: 4; y: 5.5 } PathLine { x: 7; y: 2.5 }
            }
        } }
        // R476, R480: the menu is the arrow's (M.Button `menu`), opened at the press as QToolButton's arrow; the arrow
        // stays pressed while it is open and a second press closes it. The flicker at the press (Daniel: «il flicker
        // c'è nel momento in cui preme il pulsante») was the arrow's tooltip coming back for three frames (ToolTip.held).
        menu: popup; menuBelow: false; menuOnPress: true
        Keys.onDownPressed: openMenu()
    }
    M.Menu {
        id: popup; objectName: root.objectName+"Menu"; y: root.height
        Instantiator {
            model: root.model
            delegate: M.MenuItem {
                required property var modelData
                required property int index
                objectName: "phaseMenu_"+modelData.command
                text: modelData.title; iconName: modelData.icon; enabled: modelData.enabled && shell.commandEnabled[modelData.command]!==false
                shortcutText: modelData.keys.join(", "); tip: modelData.tip
                topPadding: modelData.danger ? Theme.space.S*2 : Theme.space.S
                implicitHeight: Math.ceil(Theme.measureText(caption,"body").height)+topPadding+bottomPadding
                Rectangle { visible: modelData.danger; x: Theme.space.S; y: 1; width: parent.width-2*x; height: Theme.line.HAIR; color: Theme.colors.line_soft }
                contentItem: Item {
                    implicitWidth: label.implicitWidth+keys.implicitWidth+Theme.icon.CONTROL+Theme.space.M+Theme.space.XXL
                    M.Icon { width: Theme.icon.CONTROL; height: width; anchors.verticalCenter: parent.verticalCenter; iconName: modelData.icon
                        color: !parent.parent.enabled ? Theme.disabledText : modelData.danger ? Theme.colors.danger : Theme.colors.text }
                    M.Label { id: label; x: Theme.icon.CONTROL+Theme.space.M; height: parent.height; text: modelData.title
                        color: !parent.parent.enabled ? Theme.disabledText : modelData.danger ? Theme.colors.danger : Theme.colors.text }
                    M.Label { id: keys; anchors.right: parent.right; height: parent.height; text: modelData.keys.join(", "); enabled: parent.parent.enabled }
                }
                onTriggered: root.chosen(index)
            }
            onObjectAdded: (index, object) => popup.insertItem(index,object)
            onObjectRemoved: (index, object) => popup.removeItem(object)
        }
    }
    Keys.onDownPressed: arrow.openMenu()
}
