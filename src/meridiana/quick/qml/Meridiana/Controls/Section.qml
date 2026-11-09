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
    property string helpTip: ""
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
    property real progress: expanded ? 1 : 0
    Behavior on progress { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.NORMAL; easing.type: Theme.motion.EASE } }
    signal helpRequested(string helpId)
    default property alias content: body.data
    signal toggled(bool expanded)
    readonly property real bodyX: nested || !framed ? 0 : density === "flush" ? Theme.line.HAIR : density === "lead" ? 9 : density === "form" ? 10 : Theme.space.M + 1
    readonly property real bodyY: nested ? Theme.space.S : !framed || density === "flush" ? 0 : density === "lead" ? 4 : density === "form" ? 9 : Theme.space.M + 1
    readonly property real bodyRoom: nested ? Theme.space.S : !framed || density === "flush" ? 0 : density === "lead" ? 13 : density === "form" ? 19 : 2 * Theme.space.M
    implicitHeight: heading.height + contentClip.height + (nested || !framed || density === "form" || density === "lead" ? 0 : Theme.line.HAIR)
    height: implicitHeight
    implicitWidth: Theme.size.READING
    Rectangle { anchors.fill: parent; visible: !root.nested && root.framed; radius: root.radius; z: 1
        color: "transparent"; border.width: Theme.line.HAIR; border.color: Theme.colors.line }
    Button {
        id: heading; objectName: root.headName; width: parent.width
        height: root.headingVisible ? Math.ceil(Theme.measureText(root.title || "Hg", "body").height) + Theme.space.M : 0
        visible: height > 0; flat: true
        focusPolicy: root.collapsible ? Qt.StrongFocus : Qt.NoFocus
        text: root.title; padding: 0
        Accessible.role: Accessible.Button
        Accessible.name: root.title
        Accessible.expandable: root.collapsible
        Accessible.expanded: root.expanded
        background: Item {
            SectionBand { anchors.fill: parent; anchors.margins: Theme.line.HAIR / 2; visible: !root.nested && root.framed     // R524
                radius: root.radius - Theme.line.HAIR / 2
                open: root.progress > 0; hovered: heading.hovered && root.collapsible; pressed: heading.down && root.collapsible }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.line.HAIR; visible: root.nested; color: Theme.colors.line }
        }
        contentItem: Item {
            Item { x: root.nested ? 0 : Theme.line.TEXT_INSET; y: (parent.height-10)/2; width: 10; height: 10
                visible: root.collapsible; rotation: -90*(1-root.progress)
                Icon { anchors.centerIn: parent; anchors.verticalCenterOffset: -0.5; width: 20; height: 20
                    name: "control:chevron-down"; color: root.nested && heading.hovered ? Theme.colors.text : Theme.colors.muted }
            }
            Label { x: root.collapsible ? (root.nested ? 0 : Theme.line.TEXT_INSET) + 16 : 0
                width: parent.width-x-(help.visible ? help.width+Theme.space.M : Theme.line.TEXT_INSET)
                height: parent.height; text: root.title; textStyle: "strong"; color: root.enabled ? Theme.colors.text : Theme.colors.muted; elide: Text.ElideRight }
        }
        onClicked: if (root.collapsible) { root._open = !root.expanded; root.toggled(root._open) }
    }
    HelpMark { id: help; objectName: "section-help:" + root.helpId; visible: root.headingVisible && (root.helpId !== "" || root.helpTip !== "")
        x: parent.width-width-(root.nested ? 0 : root.density === "page" ? Theme.line.TEXT_INSET : Theme.space.S); y: (heading.height-height)/2
        tip: root.helpTip
        onClicked: root.helpRequested(root.helpId)
    }
    Item {
        id: contentClip; y: heading.height; width: parent.width
        height: Math.round((body.implicitHeight + root.bodyRoom) * root.progress)
        opacity: root.progress; visible: height > 0; enabled: root.expanded; clip: true
        Column { id: body; x: root.bodyX; y: root.bodyY
            width: parent.width-2*x; spacing: Theme.space.S }
    }
}
