import QtQuick
import Meridiana.Theme

// R633 (Daniel 15/11/2026: «che la forma delle testate rimanga quella quando si scorre verso il basso»): the head of a
// section (M.Section) with the section's frame, one item for the section in its place and for its copy held at an edge
// of the panel's page (HeldHeads.qml), so that the two are one drawing: the band (R524), the arrow (R592), the title,
// the «?» (R597), the frame as tall as the section (the held copy is cut at the head's foot, or at the closed section's).
// `held`: the copy, outside the Tab chain and the reader's tree (the section's own head is the one they reach: Tab gets
// there as before), its parts named "held-" and their names; a click on it is the same click as on the section's own.
Item {
    id: root
    property Item section: null
    property bool held: false
    readonly property Item button: heading
    readonly property Item help: help
    width: section ? section.width : 0
    height: heading.height
    // the frame of the section, above its band as it always was (the section's body under it); in a panel's page the
    // page draws it over what scrolls instead, so that it never dissolves (HeldHeads.qml, R633)
    Rectangle { width: root.width; height: root.section ? root.section.height : 0; z: 1
        visible: root.section !== null && !root.section.nested && root.section.framed && !root.section.framedByPage; radius: root.section ? root.section.radius : 0
        color: "transparent"; border.width: Theme.line.HAIR; border.color: Theme.colors.line }
    Button {
        id: heading; objectName: (root.held ? "held-" : "") + (root.section ? root.section.headName : ""); width: parent.width
        height: root.section && root.section.headingVisible ? Math.ceil(Theme.measureText(root.section.title || "Hg", "body").height) + Theme.space.M : 0
        visible: height > 0; flat: true
        enabled: !root.held || root.section.enabled
        focusPolicy: root.section && root.section.collapsible && !root.held ? Qt.StrongFocus : Qt.NoFocus
        text: root.section ? root.section.title : ""; padding: 0
        Accessible.role: Accessible.Button
        Accessible.name: text
        Accessible.expandable: root.section ? root.section.collapsible : false
        Accessible.expanded: root.section ? root.section.expanded : false
        Accessible.ignored: root.held
        background: Item {
            SectionBand { anchors.fill: parent; anchors.margins: Theme.line.HAIR / 2; visible: !root.section.nested && root.section.framed     // R524
                radius: root.section.radius - Theme.line.HAIR / 2
                foot: root.section.foot; hovered: heading.hovered && root.section.collapsible; pressed: heading.down && root.section.collapsible }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.line.HAIR; visible: root.section.nested; color: Theme.colors.line }
        }
        contentItem: Item {
            Chevron { x: (root.section.nested ? 0 : Theme.line.TEXT_INSET) - 5; y: Math.round((parent.height-height)/2)     // R592
                visible: root.section.collapsible; progress: root.section.progress; active: root.section.nested && heading.hovered }
            Label { x: root.section.collapsible ? (root.section.nested ? 0 : Theme.line.TEXT_INSET) + 16 : 0
                width: parent.width-x-(help.visible ? help.width+Theme.space.M : Theme.line.TEXT_INSET)
                height: parent.height; text: root.section.title; textStyle: "strong"
                color: root.section.enabled ? Theme.colors.text : Theme.colors.muted; elide: Text.ElideRight }
        }
        onClicked: root.section.activate()
    }
    HelpMark { id: help; objectName: (root.held ? "held-" : "") + "section-help:" + (root.section ? root.section.helpId : "")
        visible: root.section !== null && root.section.headingVisible && root.section.helpId !== ""
        enabled: !root.held || root.section.enabled
        x: Math.round(parent.width-width-(root.section.nested ? 0 : root.section.density === "page" ? Theme.line.TEXT_INSET : Theme.space.S))
        y: Math.round((heading.height-height)/2)
        helpKey: root.section ? root.section.helpId : ""
        focusPolicy: root.held ? Qt.NoFocus : Qt.TabFocus
        Accessible.ignored: root.held
    }
}
