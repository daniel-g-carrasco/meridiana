import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme

// R21-F2: the field of many lines, on M.TextField's metrics (its ground, its radius, its focus and hover borders, its
// paddings, its colours and its placeholder); `bare` draws no ground, for a long text read in a page (a manual, a
// preview, a command to copy). It grows with its text; a page that must keep it in a given room puts it in an
// M.ScrollPage, with `follow` so the page keeps the cursor in view while one writes.
T.TextArea {
    id: root
    property bool invalid: false
    property bool bare: false
    implicitWidth: Theme.size.READING / 2
    implicitHeight: Math.max(bare ? 0 : Theme.size.CONTROL, contentHeight + topPadding + bottomPadding)
    padding: Theme.space.M
    leftPadding: bare ? 0 : padding + 2
    rightPadding: bare ? 0 : padding + 2
    topPadding: bare ? 0 : Theme.space.XS
    bottomPadding: bare ? 0 : Theme.space.XS
    font.family: Theme.fontFamily
    font.pixelSize: Theme.text.body.size
    color: enabled ? Theme.colors.text : Theme.disabledText
    selectionColor: Theme.colors.select_bg
    selectedTextColor: Theme.colors.select_fg
    placeholderTextColor: Theme.colors.muted
    wrapMode: TextEdit.Wrap
    selectByMouse: true
    persistentSelection: false
    hoverEnabled: true
    renderType: TextEdit.NativeRendering
    focusPolicy: readOnly ? Qt.ClickFocus : Qt.StrongFocus
    Label { x: root.leftPadding; y: root.topPadding; width: root.availableWidth
        text: root.placeholderText; color: root.placeholderTextColor; visible: !root.length && !root.preeditText; wrapMode: Text.Wrap }
    background: Rectangle { visible: !root.bare; color: Theme.colors.field; radius: Theme.radius.CONTROL
        border.width: root.activeFocus ? Theme.line.FOCUS : Theme.line.HAIR
        border.color: !root.enabled ? "transparent" : root.invalid ? Theme.colors.danger : root.activeFocus ? Theme.colors.accent : root.hovered ? Theme.colors.field_line : "transparent" }
}
