import QtQuick
import QtQuick.Shapes
import QtQuick.Templates as T
import Meridiana.Theme
T.MenuItem {
    id: root
    property string iconName: ""
    property string shortcutText: text.indexOf("\t") >= 0 ? text.split("\t")[1] : action && action.shortcut ? action.shortcut.toString() : ""
    property string tip: ""
    // R564: what an entry made from data can be besides a command (MenuEntry), drawn here once for every menu: a rule
    // between groups (MenuSeparator's look), a title over the commands that follow (R533, the «label» text of the
    // sections), a command that deletes everything (the last of its menu, apart under a rule and in red)
    property bool rule: false
    property bool heading: false
    property bool danger: false
    // R662: an entry left out of its menu for now (the Checks' «Show» without a place): hidden, no height, and not
    // counted in the menu's width nor in its column of marks
    property bool shown: true
    visible: shown
    height: shown ? implicitHeight : 0
    // R662 (Daniel 15/11/2026: «guarda quanto spazio rimane a destra di "propose inverters..."... quando a sinistra ci
    // sono 5mm!!»): the column of the marks is there only when an entry of the menu has a mark (an icon, a check, or
    // a check it can take: checkable), as wide as an icon when one has an icon, as a check otherwise, and then for
    // every entry; a menu of words alone starts its words at the margin. Before: a slot of 12 px and a gap of 6,
    // empty, at the left of every menu without icons.
    readonly property var marks: {
        const mine = shown && !rule && !heading
        const out = {icons: mine && iconName !== "", checks: mine && (checkable || checked)}
        if (!menu) return out
        for (let i=0; i<menu.count; i++) {
            const entry = menu.itemAt(i)
            // a rule or a title shows no mark, whatever its `checked` (the snaps' rule matched the snap "")
            if (!entry || entry.shown === false || entry.rule || entry.heading) continue
            if (entry.iconName) out.icons = true
            if (entry.checkable || entry.checked) out.checks = true
        }
        return out
    }
    readonly property bool hasIcons: marks.icons
    readonly property bool hasMarks: marks.icons || marks.checks
    readonly property real markerWidth: hasIcons ? Theme.icon.CONTROL : hasMarks ? ControlMetrics.menuCheck : 0
    readonly property real markerGap: hasIcons ? Theme.space.M : hasMarks ? Theme.space.S : 0
    readonly property string caption: text.split("\t")[0].replace(/&(.)/g, "$1")
    readonly property color ink: !root.enabled && !root.heading ? Theme.disabledText : root.danger ? Theme.colors.danger : Theme.colors.text
    // R555, R662: an entry is the mirror of itself and so is its menu. ControlMetrics.menuInset from the menu's side
    // to the first ink at the left (the mark's column, or the text) and from the last ink of the widest entry to the
    // side at the right: its key, its submenu's arrow, or its text. The keys and the arrow are a column at the right,
    // menuColumnGap after the text, counted in the entry's width; the arrow's ink ends where the right padding starts.
    readonly property bool hasArrow: subMenu !== null
    readonly property real arrowRoom: hasArrow ? ControlMetrics.menuColumnGap + ControlMetrics.arrowDepth : 0
    implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
    implicitHeight: rule ? 2 * Theme.space.XS + Theme.line.HAIR
                         : Math.ceil(Theme.measureText(caption, heading ? "label" : "body").height) + topPadding + bottomPadding
    padding: rule ? Theme.space.XS : ControlMetrics.menuItemPadV
    topPadding: danger ? padding + Theme.space.S : padding
    // a rule as far in as the entries' content, on both sides
    leftPadding: ControlMetrics.menuItemPadH
    rightPadding: ControlMetrics.menuItemPadH
    hoverEnabled: true
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    Accessible.role: rule ? Accessible.Separator : heading ? Accessible.StaticText : Accessible.MenuItem
    contentItem: Item {
        implicitWidth: root.rule ? 0 : root.markerWidth + root.markerGap + word.implicitWidth + (keys.text ? ControlMetrics.menuColumnGap + keys.implicitWidth : 0) + root.arrowRoom
        implicitHeight: root.rule ? Theme.line.HAIR : word.implicitHeight
        Rectangle { objectName: "menuRule"; visible: root.rule; width: parent.width; height: Theme.line.HAIR; anchors.verticalCenter: parent.verticalCenter
            color: Theme.colors.line }
        Item { objectName: "menuMark"; width: root.markerWidth; height: width; anchors.verticalCenter: parent.verticalCenter
            visible: !root.rule && !root.heading && root.hasMarks
            Icon { anchors.fill: parent; name: root.iconName; visible: !root.checked; color: root.ink }
            CheckMark { anchors.fill: parent; visible: root.checked; color: root.ink }
        }
        Label { id: word; objectName: "menuText"; x: root.markerWidth + root.markerGap
            width: Math.max(0, parent.width-x-(keys.text ? keys.implicitWidth+ControlMetrics.menuColumnGap : 0)-root.arrowRoom)
            visible: !root.rule; text: root.caption; textStyle: root.heading ? "label" : "body"
            color: root.heading ? Theme.colors.muted : root.ink; height: parent.height; elide: Text.ElideRight }
        Label { id: keys; objectName: "menuKeys"; anchors.right: parent.right; anchors.rightMargin: root.arrowRoom; height: parent.height; text: root.rule || root.heading ? "" : root.shortcutText; enabled: root.enabled }
    }
    // R592: a submenu opens a list of choices: the full arrow (M.Arrow); R662: as wide as its ink, at the right padding
    arrow: Arrow { objectName: "menuArrow"; visible: root.hasArrow; direction: "right"
        x: root.width - root.rightPadding - width
        y: Math.round((root.height-height)/2); active: root.highlighted || root.hovered }
    background: Rectangle { objectName: "menuItemGround"; radius: ControlMetrics.menuItemRadius
        color: root.enabled && (root.highlighted || root.hovered) ? Theme.colors.hover : "transparent"
        Rectangle { visible: root.danger; x: ControlMetrics.menuItemPadH; y: Theme.space.XXS; width: parent.width-2*x; height: Theme.line.HAIR
            color: Theme.colors.line_soft }
    }
    // R555 (Daniel: «il suggerimento della voce si apre sopra il menu e ne copre il bordo»): an entry's tooltip stands
    // outside the menu, beside it at the entry's height (ControlMetrics.besideMenu), as a submenu does
    ToolTip { id: tipBox; parent: root; text: root.tip; visible: root.hovered && text !== ""
        readonly property Item frame: root.menu && root.menu.background ? root.menu.background : null
        // asked again when it shows and when the entry is laid out (the list places its entries after making them)
        readonly property point beside: frame && (visible || root.x + root.y + frame.height >= 0)
            ? ControlMetrics.besideMenu(root.mapFromItem(frame, 0, 0), frame.width, implicitWidth, implicitHeight,
                                        ControlMetrics.roomOf(root, false)) : spot
        x: beside.x
        y: beside.y }
}
