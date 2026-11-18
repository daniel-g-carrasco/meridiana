import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.TextField {
    id: root
    clip: true
    property bool invalid: false
    implicitWidth: Theme.size.READING / 2
    implicitHeight: Math.max(Theme.size.CONTROL, contentHeight + 2 * Theme.space.XS)
    padding: Theme.space.M
    leftPadding: padding + 2
    rightPadding: padding + 2
    topPadding: Theme.space.XS
    bottomPadding: Theme.space.XS
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    color: enabled ? Theme.colors.text : Theme.disabledText
    selectionColor: Theme.colors.select_bg
    selectedTextColor: Theme.colors.select_fg
    placeholderTextColor: Theme.colors.muted
    verticalAlignment: TextInput.AlignVCenter
    Label { x: root.leftPadding; y: root.topPadding; width: root.availableWidth; height: root.availableHeight
        text: root.placeholderText; color: root.placeholderTextColor; visible: !root.length && !root.preeditText; elide: Text.ElideRight }
    selectByMouse: true
    autoScroll: activeFocus
    focusPolicy: Qt.StrongFocus
    onActiveFocusChanged: if (activeFocus && (focusReason === Qt.TabFocusReason || focusReason === Qt.BacktabFocusReason)) selectAll()
    hoverEnabled: true
    renderType: TextInput.NativeRendering
    persistentSelection: false
    background: Rectangle { color: Theme.colors.field; radius: Theme.radius.CONTROL
        border.width: root.activeFocus ? Theme.line.FOCUS : Theme.line.HAIR
        border.color: !root.enabled ? "transparent" : root.invalid ? Theme.colors.danger : root.activeFocus ? Theme.colors.accent : root.hovered ? Theme.colors.field_line : "transparent" }
}
