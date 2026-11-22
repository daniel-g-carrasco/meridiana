import QtQuick
import QtQuick.Controls as C
import QtQuick.Templates as T
import Meridiana.Theme

// R21-F2: the field of many lines, on M.TextField's metrics (its ground, its radius, its focus and hover borders, its
// paddings, its colours and its placeholder); `bare` draws no ground, for a long text read in a page (a manual, a
// preview, a command to copy). It grows with its text; a page that must keep it in a given room puts it in an
// M.ScrollPage, with `follow` so the page keeps the cursor in view while one writes.
T.TextArea {
    id: root
    property alias textActions: textCommands
    TextActions { id: textCommands; editor: root }
    function handleTextKey(event) { if (textKeys.handle(event)) C.ContextMenu.menu.popup(root, 0, root.height) }
    TextKeys { id: textKeys; editor: root; actions: textCommands; enabled: root.textKeysEnabled }
    property bool textKeysEnabled: true
    Keys.forwardTo: [textKeys]

    C.ContextMenu.menu: TextMenu { actions: textCommands }
    function openTextMenu(x, y) { const menu = C.ContextMenu.menu; if (!menu.visible) menu.popup(root, x, y) }
    onPressAndHold: event => root.openTextMenu(event.x, event.y)

    Loader { active: textCommands.pasteError !== ""
        sourceComponent: ToolTip { parent: root; text: textCommands.pasteError; visible: root.hovered } }
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
    selectByKeyboard: true
    persistentSelection: textCommands.menuActive
    hoverEnabled: true
    renderType: TextEdit.NativeRendering
    focusPolicy: readOnly ? Qt.ClickFocus : Qt.StrongFocus
    Label { x: root.leftPadding; y: root.topPadding; width: root.availableWidth
        text: root.placeholderText; color: root.placeholderTextColor; visible: !root.length && !root.preeditText; wrapMode: Text.Wrap }
    background: Rectangle { visible: !root.bare; color: Theme.colors.field; radius: Theme.radius.CONTROL
        border.width: Theme.focusRing(root) ? Theme.line.FOCUS : Theme.line.HAIR
        border.color: !root.enabled ? "transparent" : (root.invalid || textCommands.pasteError !== "") ? Theme.colors.danger : Theme.focusRing(root) ? Theme.colors.focus : root.hovered ? Theme.colors.field_line : "transparent" }
}
