import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme

// F5 (r23-f5): one pill for the whole program, one ground and one radius (Theme.radius.CONTROL), three variants that
// were three components:
//  - "badge" (was Badge): a word or a number in a chip, state "done" / "stale" / "todo" or a tone of Theme.colors;
//  - "count" (was CountPill, and Checks' StatusPill over it): the count of a check level with its symbol, a button
//    (checkable unless said otherwise), the paint of themeTokens.countPill (R485: minText keeps it as wide as "99");
//  - "view" (was Plan/ViewPill, R511): the ground of what the plan writes over itself (the scale, the coordinates,
//    the sides' pills): the children go inside, `pad` and `font` are for them.
// Only "count" takes the pointer: the other two let the clicks through to the plan under them.
Rectangle {
    id: root
    property string variant: "badge"
    property string text: ""
    property string tone: "muted"
    property string level: "info"
    property string tip: ""
    // the text it is at least as wide as (R485, the status bar: "99"), so that a count of one more digit moves nothing
    property string minText: ""
    property alias checkable: button.checkable
    property alias checked: button.checked
    property alias focusPolicy: button.focusPolicy
    readonly property alias hovered: button.hovered
    readonly property alias down: button.down
    readonly property alias visualFocus: button.visualFocus
    signal clicked()
    signal toggled()
    // "view": the plan's ground and ink, the margin and the type of the status bar in digits of one width
    property color ground: Theme.colors.overlay.pill
    property color ink: Theme.colors.overlay.pill_ink
    readonly property real pad: Theme.space.M
    readonly property font font: Qt.font({family: Theme.fontFamily, pixelSize: Theme.text.secondary.size,
                                          weight: Theme.text.secondary.weight, features: {"tnum": 1}})
    readonly property bool counting: variant === "count"
    readonly property var paint: { const revision = Theme.revision; return counting ? themeTokens.countPill(level, text) : null }
    readonly property real minWidth: { const revision = Theme.revision; return counting && minText ? themeTokens.countPill(level, minText).width : 0 }
    readonly property string paintState: !counting ? "" : checked ? "on" : hovered || down ? "hover" : "rest"
    implicitWidth: counting ? Math.max(paint.width, minWidth) : variant === "badge" ? badgeText.implicitWidth + 2*Theme.space.M + 2 : 0
    implicitHeight: variant === "view" ? Theme.size.CONTROL : Theme.size.CHIP
    radius: Theme.radius.CONTROL
    opacity: counting && text === "0" ? .55 : 1
    color: counting ? paint[paintState][0] : variant === "view" ? ground
         : state === "done" ? Theme.colors.select_bg : state === "stale" ? "transparent" : Theme.colors.line_soft
    border.width: variant === "view" ? 0 : Theme.line.HAIR
    border.color: counting ? paint[paintState][1] : state === "stale" ? Theme.colors.field_line : "transparent"
    Label { id: badgeText; visible: root.variant === "badge"; anchors.centerIn: parent; textStyle: "control"; text: root.text
        color: root.state === "done" ? Theme.colors.select_fg : root.state === "stale" ? Theme.colors.text : root.state === "todo" ? Theme.colors.text2 : Theme.colors[root.tone] || Theme.colors.muted }
    // r23-unita: the symbol asked only when shown (a view pill, as the plan's scale, asked it hidden: an image for
    // nothing, and a warning in an engine without the icon provider, pianta/test_aids)
    Icon { visible: root.counting; name: root.counting ? "symbol:" + root.level : ""; dimDisabled: false; x: 6; y: (parent.height-height)/2; width: 12; height: 12 }
    Label { visible: root.counting; text: root.text; textStyle: "label"; color: Theme.colors.text
        x: parent.width-8-width; anchors.verticalCenter: parent.verticalCenter }
    Rectangle { visible: root.counting; anchors.fill: parent; radius: parent.radius; color: "transparent"
        border.width: button.visualFocus ? Theme.line.FOCUS : 0; border.color: Theme.colors.accent }
    T.AbstractButton {
        id: button
        anchors.fill: parent
        enabled: root.counting
        visible: root.counting
        checkable: true
        hoverEnabled: true
        focusPolicy: Qt.TabFocus
        Accessible.role: Accessible.Button
        Accessible.name: root.text
        Accessible.description: root.tip
        onClicked: root.clicked()
        onToggled: root.toggled()
    }
    ToolTip { parent: root; text: root.tip; visible: button.hovered && text !== "" }
}
