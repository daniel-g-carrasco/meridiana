import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.Button {
    id: root
    property string tip: ""
    TextActions { id: descriptionCopy; target: root; readOnly: true; wholeText: textEditing.plainHtml(root.tip); copyLabel: textEditing.labels.description }
    // the menu of the tip's words (R683): opened by the right button and by the Menu key, not by Qt's ContextMenu,
    // whose touch handling let a pinch or a drag over a popup reach the button behind it (R570)
    // made at its first use: a menu made at once for every button of a page held the page up (Production and the
    // report stayed blank on a real screen)
    Component { id: descriptionMenuMaker; TextMenu { actions: descriptionCopy } }
    property var descriptionMenu: null
    function openDescriptionMenu(x, y) {
        if (!descriptionMenu) descriptionMenu = descriptionMenuMaker.createObject(root)
        descriptionMenu.popup(root, x, y)
    }
    TapHandler { acceptedButtons: Qt.RightButton; acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onTapped: eventPoint => root.openDescriptionMenu(eventPoint.position.x, eventPoint.position.y) }
    Keys.onMenuPressed: event => { root.openDescriptionMenu(0, root.height); event.accepted = true }
    property string iconName: ""
    // Compact icon actions share the same square and all button states.
    property bool compact: false
    // R592: a button that opens a list of choices shows the full arrow (M.Arrow) after its text
    property bool menuArrow: false
    flat: false
    property bool groupHovered: false
    property bool groupMember: false
    property bool active: checked
    // R480 (Daniel 06/11/2026): a button that opens a menu. While the menu is open it stays pressed; a second click
    // closes it (the press closes the menu before the button hears it: Menu.closedAt says it was open); Esc and a
    // click outside close it as any menu. `menuBelow`: placed under the button, else where the menu says.
    property var menu: null
    property bool menuBelow: true
    // A shared popup can follow the whole split control, rather than its old owner.
    property Item menuAnchor: null
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
        if (menuAnchor) menu.parent = menuAnchor
        if (menuBelow && menu.parent) { const anchor = menuAnchor || root; const p = anchor.mapToItem(menu.parent, 0, anchor.height); menu.x = p.x; menu.y = p.y }
        if (menu.opener !== undefined) menu.opener = root
        menu.open()
    }
    // R555 (Daniel 13/11/2026: «il pulsante "Suggestions" ha la scritta che esce dai bordi»): the size follows the face
    // the button really has. `contentItem.implicitWidth` stayed bound to this file's own face, so a button that brings a
    // face of its own (Meridio's «Suggerimenti», a chevron and a word) kept the width of the plain text and let its
    // face out of the border; the control's implicitContent* follow whichever face is in place.
    implicitWidth: compact ? Theme.size.CHIP : Math.max(Theme.size.CONTROL, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: compact ? Theme.size.CHIP : Math.max(Theme.size.CONTROL, implicitContentHeight + 2 * Theme.space.XS)
    padding: compact ? Theme.space.XS : Theme.space.L
    topPadding: Math.min(padding, Theme.space.XS)
    bottomPadding: Math.min(padding, Theme.space.XS)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.strong.size
    font.weight: Theme.text.strong.weight
    Accessible.name: text
    Accessible.description: tip
    // R598: no id inside the face, or Qt makes it even for a button that brings a face of its own (a deferred
    // delegate with an id is made at once): the Steppers' arrows, the head of every M.Section
    contentItem: Item {
        implicitWidth: children[0].implicitWidth
        implicitHeight: children[0].implicitHeight
        Row { anchors.centerIn: parent; spacing: Theme.space.S
            Icon { visible: root.iconName !== ""; name: root.iconName; anchors.verticalCenter: parent.verticalCenter
                color: root.enabled ? Theme.colors.text : Theme.disabledText }
            Label { text: root.text; visible: text !== ""; font: root.font; enabled: root.enabled; anchors.verticalCenter: parent.verticalCenter }
            Arrow { visible: root.menuArrow; anchors.verticalCenter: parent.verticalCenter; active: root.hovered || root.menuShown }
        }
    }
    background: Rectangle {
        radius: Theme.radius.CONTROL
        color: root.flat || !root.enabled ? "transparent" : Theme.colors.field
        Rectangle { anchors.fill: parent; radius: parent.radius
            color: !root.enabled ? "transparent" : root.down || root.menuShown || (root.flat && root.active) || (root.groupMember && root.hovered) ? Theme.colors.press : root.hovered || root.groupHovered ? Theme.colors.hover : "transparent" }
        Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"
            border.width: Theme.focusRing(root) ? Theme.line.FOCUS : 0; border.color: Theme.colors.focus }
    }
    // R468: the tooltip only when it adds something to what the button shows (textShown: false for a face of its
    // own without the text; textCut: true when that face cuts the text).
    property bool textShown: true
    property bool textCut: false
    readonly property string shownTip: ControlMetrics.tipAdds(tip, textShown ? text : "", textCut) ? tip : ""
    // R598: made only for a button that has a tooltip to show (most have none: a section's head, a number's steps)
    Loader { active: root.shownTip !== ""
        sourceComponent: Item { ToolTip { objectName: "controlTip"; parent: root; text: root.shownTip; visible: root.hovered && root.shownTip !== "" && !root.menuShown } } }
}
