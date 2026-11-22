import QtQuick
import QtQuick.Controls as C
import Meridiana.Theme

// R534: the field written over a view, one for all of them: the length of a plan's side (SideEditor, R336), the
// height of a corner in the 3D view. The ground and the ink of the plan's pills (label_bg, label_fg), the outline
// of the selection (sel) as wide as a focus, the radius of the plan's labels, the size of their text with digits all
// as wide as each other (as ViewPill), Theme.space.XXS above and below, the unit after the value. Before it, a
// number in a disc (the side's, as its pill) or a short word saying what the value is (the corner's «Quota da
// terra»). The 3D view's field was a white box with an accent border, three times as wide as its number, without a
// word or a unit (Daniel 07/11/2026: «non c'entra nulla a livello grafico con quanto c'è altrove»).
Rectangle {
    id: root
    // view_colours.PHOTO, as the plan and the scene give it (planColors, overlayColors)
    property var colours: ({label_bg: Theme.colors.overlay.glass, label_fg: Theme.colors.overlay.ink, sel: Theme.colors.overlay.pick})
    readonly property color ink: colours.label_fg
    readonly property color ground: colours.label_bg
    property string badge: ""
    property string label: ""
    property string unit: "m"
    property string sample: "0,00"
    property alias text: field.text
    property alias input: field
    readonly property real disc: height-2*Theme.space.XXS
    readonly property font textFont: Qt.font({family: Theme.fontFamily, pixelSize: Theme.annotation.LABEL_SIZE, features: {"tnum": 1}})
    signal accepted()
    signal canceled()
    signal focusLost()
    height: metrics.height+2*Theme.annotation.LABEL_PAD
    width: unitText.x+unitText.implicitWidth+Theme.space.S
    radius: Theme.radius.PLAN_LABEL
    color: Qt.rgba(ground.r,ground.g,ground.b,1)
    border.width: Theme.line.FOCUS
    border.color: colours.sel
    function edit(value, select) {
        field.text=value; field.forceActiveFocus()
        if (select !== false) field.selectAll()
    }
    FontMetrics { id: metrics; font: root.textFont }
    Rectangle {
        objectName: "overlayFieldBadge"
        visible: root.badge !== ""
        x: Theme.space.XXS; y: Theme.space.XXS; width: root.disc; height: width; radius: width/2
        color: root.ink
        Text { anchors.fill: parent; text: root.badge; color: root.ground
            font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE; font.weight: Theme.annotation.WEIGHT
            verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter }
    }
    Text {
        id: labelText
        objectName: "overlayFieldLabel"
        visible: root.label !== ""
        x: Theme.space.S
        anchors.baseline: field.baseline
        text: root.label; font: root.textFont; color: root.ink; opacity: .72
    }
    TextInput {
        id: field
        objectName: "overlayFieldInput"
        property alias textActions: textCommands
        TextActions { id: textCommands; editor: field; focusExit: () => root.focusLost(); numericPolicy: ({unit: root.unit, kind: root.unit === "m" ? "length" : "", minimum: -1e12, maximum: 1e12, decimals: 8}) }
        C.ContextMenu.menu: TextMenu { actions: textCommands }
        function openTextMenu(x, y) { const menu = C.ContextMenu.menu; if (!menu.visible) menu.popup(field, x, y) }
        TapHandler { acceptedButtons: Qt.LeftButton; gesturePolicy: TapHandler.DragThreshold; onLongPressed: field.openTextMenu(point.position.x, point.position.y) }

        TextKeys { id: textKeys; editor: field; actions: textCommands; enabled: field.textKeysEnabled }
        property bool textKeysEnabled: true
        function handleTextKey(event) { if (textKeys.handle(event)) C.ContextMenu.menu.popup(field, 0, field.height) }
        Keys.forwardTo: [textKeys]

        x: root.badge !== "" ? Theme.space.XXS+root.disc+Theme.space.XS
           : root.label !== "" ? labelText.x+labelText.implicitWidth+Theme.space.XS : Theme.space.S
        width: Math.max(metrics.advanceWidth(text),metrics.advanceWidth(root.sample))+Theme.space.XXS
        height: root.height; verticalAlignment: TextInput.AlignTop
        topPadding: ControlMetrics.textBaseline(height, metrics, Screen.devicePixelRatio) - metrics.ascent       // R582: as every field's
        color: root.ink; font: root.textFont; selectByMouse: true
        selectionColor: Qt.rgba(root.ink.r,root.ink.g,root.ink.b,64/255)
        selectedTextColor: root.ink
        // the paste's error said while the field has the focus: a tooltip, not a ring (the loader holds the condition)
        Loader { active: textCommands.pasteError !== "" && field.activeFocus
            sourceComponent: ToolTip { parent: root; text: textCommands.pasteError; visible: root.visible } }
        Keys.onReturnPressed: function(event) { root.accepted(); event.accepted=true }
        Keys.onEnterPressed: function(event) { root.accepted(); event.accepted=true }
        Keys.onEscapePressed: function(event) { root.canceled(); event.accepted=true }
        onActiveFocusChanged: if (!activeFocus && root.visible) {
            if (textCommands.menuActive) textCommands.pendingExit = true
            else { textCommands.pendingExit = false; root.focusLost() }
        }
    }
    Text {
        id: unitText
        x: field.x+field.width+Theme.space.XS
        anchors.baseline: field.baseline
        text: root.unit; font: root.textFont; color: root.ink
    }
}
