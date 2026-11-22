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
    // R644: one ground for the two halves, the common rule of the split buttons
    M.SplitGround {
        objectName: root.objectName+"Ground"; anchors.fill: parent; split: main.width
        on: main.active || root.stripActive; commandEnabled: main.enabled
        commandHovered: main.hovered; commandDown: main.down
        arrowHovered: arrow.hovered; arrowDown: arrow.down; menuOpen: popup.visible
    }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: arrow.openMenu() }
    // R614: the command is the plain button of the bar, with its icon and word in the same places and margins
    PhaseToolButton {
        id: main; width: parent.width-arrow.width; height: parent.height; focusPolicy: Qt.NoFocus
        onClicked: root.clicked()
        background: Item {}
    }
    M.Button {
        id: arrow; objectName: root.objectName+"Arrow"; x: main.width; width: root.stripWidth; height: parent.height
        padding: 0; flat: true; focusPolicy: Qt.NoFocus; tip: root.stripTip; Accessible.name: tip
        background: Item {}
        contentItem: Item { M.Arrow { anchors.fill: parent; active: arrow.hovered || arrow.down || popup.visible } }     // R592
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
            // R564: the common entry; «Fill» off on a sub-field already full says why in the column of the keys
            delegate: M.MenuEntry {
                required property var modelData
                required property int index
                objectName: "phaseMenu_"+modelData.command
                entry: ({text: modelData.title, icon: modelData.icon, keys: modelData.keys, tip: modelData.tip,
                         danger: modelData.danger, note: shell.commandNote[modelData.command] || "",
                         enabled: modelData.enabled && shell.commandEnabled[modelData.command]!==false})
                onTriggered: root.chosen(index)
            }
            onObjectAdded: (index, object) => popup.insertItem(index,object)
            onObjectRemoved: (index, object) => popup.removeItem(object)
        }
    }
    Keys.onDownPressed: arrow.openMenu()
}
