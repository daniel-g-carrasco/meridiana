import QtQuick
import QtQuick.Shapes
import Meridiana.Theme

// F5 (r23-f5): the one section of the program, its head on the band of R524 (SectionBand). It took in Properties'
// CollapsibleSection and the Plant's panel; what made them different is a property here:
//  - who opens it: by itself (a click turns it), or by its owner, who binds `collapsed` (or `expanded`) and answers
//    `toggled` (the forms of Properties and of the results keep the state of each group, the Plant one open at a time);
//  - `framed`: false for a group without a frame nor a fold (the title only);
//  - `nested` (found by itself inside another section): the title on a thin line, nothing behind it (R343);
//  - `density`: the padding of the body, "page" (Settings, File, the dialogs), "form" and "lead" (the forms of
//    Properties and of the results, ui/style as the Widgets: 10/9, and 9/4 for the first box), "flush" (no padding: a
//    body that lays itself out, the Plant's);
//  - `headName`: the objectName of the head ("section:<title>" unless said otherwise).
Item {
    id: root
    property string title: ""
    property bool collapsible: framed
    property bool framed: true
    property bool _open: true
    property bool collapsed: !_open
    property bool expanded: !collapsed
    property bool headingVisible: title !== ""
    property string density: "page"
    property string headName: "section:" + title
    // the key of its help (app/interface/help.py): the «?» at the end of the head opens its bubble (Help.show)
    property string helpId: ""
    property real radius: Theme.radius.CONTROL
    property bool nested: {
        let ancestor = parent
        while (ancestor) {
            if (ancestor.sectionControl === true) return true
            ancestor = ancestor.parent
        }
        return false
    }
    readonly property bool sectionControl: true
    // the help key and «What's this?» open the help of the section on its «?»
    readonly property Item helpAnchor: head.help
    readonly property real progress: contentClip.progress
    default property alias content: body.data
    signal toggled(bool expanded)
    readonly property real bodyX: nested || !framed ? 0 : density === "flush" ? Theme.line.HAIR : density === "lead" ? 9 : density === "form" ? 10 : Theme.space.M + 1
    readonly property real bodyY: nested ? Theme.space.S : !framed || density === "flush" ? 0 : density === "lead" ? 4 : density === "form" ? 9 : Theme.space.M + 1
    readonly property real bodyRoom: nested ? Theme.space.S : !framed || density === "flush" ? 0 : density === "lead" ? 13 : density === "form" ? 19 : 2 * Theme.space.M
    implicitHeight: head.height + contentClip.height + (nested || !framed || density === "form" || density === "lead" ? 0 : Theme.line.HAIR)
    height: implicitHeight
    implicitWidth: Theme.size.READING
    // R633: the head, and how tall its copy held at an edge of the page is: the head of an open section (its body goes
    // on under it), the whole of a closed one (its frame's foot with it)
    readonly property real headHeight: head.height
    readonly property real heldHeight: progress > 0 ? head.height : height
    // R633: the frame of a section of a panel's page is drawn by the page, over what scrolls (HeldHeads.qml), so that it
    // never dissolves; `foot` how far the head's band goes on under it before its rounded foot: square while the body
    // is seen under the head, rounded as the body seen goes under the radius (the frame closes there too)
    readonly property bool framedByPage: _keptBy !== null
    readonly property real foot: Math.max(0, Math.min(radius, _keptBy !== null ? _keptBy.bodyShown(root) : progress > 0 ? radius : 0))
    // a click on the head (its own or its held copy's) or the keyboard on it: open or close, then the page that holds
    // the head is told (it brings a held head's section into view)
    function activate() {
        if (!collapsible) return
        _open = !expanded
        toggled(_open)
        if (_keptBy) _keptBy.headActivated(root)
    }
    // R633: the page that keeps the head in view while it scrolls (M.PanelPage: ScrollPage.keepsHeads), the nearest one
    // above the section; only for a section of the page's own (framed, that opens and closes), never a group inside
    // another section (nested: its head scrolls with its section)
    readonly property Item headKeeper: {
        if (nested || !framed || !collapsible || !headingVisible) return null
        for (let ancestor = parent; ancestor; ancestor = ancestor.parent) {
            if (ancestor.sectionControl === true) return null
            if (ancestor.keepsHeads === true) return ancestor
        }
        return null
    }
    property Item _keptBy: null
    function _keep() {
        if (_keptBy === headKeeper) return
        if (_keptBy) _keptBy.dropHead(root)
        _keptBy = headKeeper
        if (_keptBy) _keptBy.keepHead(root)
    }
    onHeadKeeperChanged: _keep()
    Component.onCompleted: _keep()
    Component.onDestruction: if (_keptBy) _keptBy.dropHead(root)
    FoldBody {
        id: contentClip; y: head.height; width: parent.width
        expanded: root.expanded
        contentHeight: body.implicitHeight + root.bodyRoom
        Column { id: body; x: root.bodyX; y: root.bodyY
            width: parent.width-2*x; spacing: Theme.space.S }
    }
    // after the body, so that the section's frame (in the head) is drawn over it as before; what an owner lays on the
    // head (a button given `parent: section`, PlantInverters' view of the strings) comes later still, over the head
    SectionHead { id: head; section: root }
}
