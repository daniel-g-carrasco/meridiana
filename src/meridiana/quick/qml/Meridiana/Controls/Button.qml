import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.Button {
    id: root
    property string tip: ""
    property string iconName: ""
    // an icon after the text (a menu's chevron-down: R21-F3, it was a «⌄» in the text)
    property string endIconName: ""
    flat: false
    property bool groupHovered: false
    property bool groupMember: false
    property bool active: checked
    // R480 (Daniel 06/11/2026): a button that opens a menu. While the menu is open it stays pressed; a second click
    // closes it (the press closes the menu before the button hears it: Menu.closedAt says it was open); Esc and a
    // click outside close it as any menu. `menuBelow`: placed under the button, else where the menu says.
    property var menu: null
    property bool menuBelow: true
    readonly property bool menuShown: !!menu && menu.visible
    property bool menuAtPress: false
    // `menuOnPress`: opened at the press, as QToolButton's menu arrow (the tools' strips, test_integration)
    property bool menuOnPress: false
    onPressed: {
        menuAtPress = !!menu && (menu.visible || Date.now() - (menu.closedAt || 0) < 400)
        if (menu && menuOnPress) { if (menu.visible) menu.close(); else if (!menuAtPress) openMenu() }
    }
    onClicked: if (menu && !menuOnPress) { if (menuAtPress) menu.close(); else openMenu() }
    function openMenu() {
        if (!menu) return
        if (menuBelow && menu.parent) { const p = root.mapToItem(menu.parent, 0, root.height); menu.x = p.x; menu.y = p.y }
        if (menu.opener !== undefined) menu.opener = root
        menu.open()
    }
    implicitWidth: Math.max(Theme.size.CONTROL, contentItem.implicitWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(Theme.size.CONTROL, contentItem.implicitHeight + 2 * Theme.space.XS)
    padding: Theme.space.L
    topPadding: Math.min(padding, Theme.space.XS)
    bottomPadding: Math.min(padding, Theme.space.XS)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.strong.size
    font.weight: Theme.text.strong.weight
    Accessible.name: text
    Accessible.description: tip
    contentItem: Item {
        implicitWidth: face.implicitWidth
        implicitHeight: face.implicitHeight
        Row { id: face; anchors.centerIn: parent; spacing: Theme.space.S
            Icon { visible: root.iconName !== ""; name: root.iconName; anchors.verticalCenter: parent.verticalCenter
                color: root.enabled ? Theme.colors.text : Theme.disabledText }
            Label { text: root.text; visible: text !== ""; font: root.font; enabled: root.enabled; anchors.verticalCenter: parent.verticalCenter }
            Icon { visible: root.endIconName !== ""; name: root.endIconName; anchors.verticalCenter: parent.verticalCenter
                color: root.enabled ? Theme.colors.text : Theme.disabledText }
        }
    }
    background: Rectangle {
        radius: Theme.radius.CONTROL
        color: root.flat || !root.enabled ? "transparent" : Theme.colors.field
        Rectangle { anchors.fill: parent; radius: parent.radius
            color: !root.enabled ? "transparent" : root.down || root.menuShown || (root.flat && root.active) || (root.groupMember && root.hovered) ? Theme.colors.press : root.hovered || root.groupHovered ? Theme.colors.hover : "transparent" }
        Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"
            border.width: root.enabled && root.activeFocus ? Theme.line.FOCUS : 0; border.color: Theme.colors.accent }
    }
    // R468: the tooltip only when it adds something to what the button shows (textShown: false for a face of its
    // own without the text; textCut: true when that face cuts the text).
    property bool textShown: true
    property bool textCut: false
    readonly property string shownTip: ControlMetrics.tipAdds(tip, textShown ? text : "", textCut) ? tip : ""
    ToolTip { objectName: "controlTip"; parent: root; text: root.shownTip; visible: root.hovered && root.shownTip !== "" && !root.menuShown }
}
