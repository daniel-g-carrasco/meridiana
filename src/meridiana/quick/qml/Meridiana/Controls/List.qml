import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
Item {
    id: root
    property bool framed: true
    property real rowHeight: Math.ceil(Theme.measureText("Ag", "body").height)
    property alias model: view.model
    property alias currentIndex: view.currentIndex
    readonly property alias count: view.count
    property string textRole: "text"
    property string iconRole: "icon"
    property alias view: view
    signal activated(int index)
    implicitHeight: root.rowHeight * Math.min(6, view.count)+2
    implicitWidth: Theme.size.READING / 2
    activeFocusOnTab: true
    Accessible.role: Accessible.List
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Home) { view.currentIndex = 0; root.activated(0); event.accepted = true }
        else if (event.key === Qt.Key_End) { view.currentIndex = view.count - 1; root.activated(view.currentIndex); event.accepted = true }
    }
    Keys.onDownPressed: { view.incrementCurrentIndex(); root.activated(view.currentIndex) }
    Keys.onUpPressed: { view.decrementCurrentIndex(); root.activated(view.currentIndex) }
    Keys.onReturnPressed: root.activated(view.currentIndex)
    Rectangle { anchors.fill: parent; visible: root.framed; color: Theme.colors.card; radius: Theme.radius.CONTROL; border.width: 1; border.color: Theme.colors.card_line }
    ListView { id: view; anchors.fill: parent; anchors.margins: root.framed ? 1 : 0
        anchors.rightMargin: (root.framed ? 1 : 0) + Theme.size.SCROLLBAR; clip: true; currentIndex: -1; boundsBehavior: Flickable.StopAtBounds
        onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Contain)
        delegate: MenuItem { required property var model; required property int index
            readonly property var rowData: model.modelData !== undefined ? model.modelData : model
            width: view.width; height: root.rowHeight; leftPadding: 2; rightPadding: 2; topPadding: 0; bottomPadding: 0
            contentItem: Item {
                Icon { id: rowIcon; visible: parent.parent.iconName !== ""; name: parent.parent.iconName; width: Theme.icon.LIST; height: width; anchors.verticalCenter: parent.verticalCenter }
                Label { x: rowIcon.visible ? rowIcon.width+Theme.space.S : 0; width: parent.width-x; height: parent.height; text: parent.parent.text; elide: Text.ElideRight; enabled: root.enabled }
            }
            background: Rectangle { color: parent.highlighted ? Theme.colors.select_bg : "transparent" }
            text: typeof rowData === "string" ? rowData : rowData[root.textRole] || ""
            iconName: typeof rowData === "string" ? "" : rowData[root.iconRole] || ""
            highlighted: view.currentIndex === index
            onPressed: { root.forceActiveFocus(Qt.MouseFocusReason); view.currentIndex = index }
            onClicked: root.activated(index)
        }
        T.ScrollBar.vertical: ScrollBar { fades: false; parent: root; flickable: view; x: root.width-width-(root.framed ? 1 : 0)
            y: root.framed ? 1 : 0; height: root.height-2*y }
    }
    EdgeFades { flickable: view }
}
