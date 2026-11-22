import QtQuick

QtObject {
    id: root
    property var editor: null
    property var target: editor
    property var identity: null
    property var frozenIdentity: null
    property bool invalidTarget: menuActive && identity !== frozenIdentity
    property var popup: null
    property var focusExit: null
    property bool pendingExit: false
    property bool readOnly: !editor || editor.readOnly
    property string wholeText: editor ? editor.getText(0, editor.length) : ""
    property string wholeLabel: textEditing.labels.whole
    property string copyLabel: textEditing.labels.copy
    property string markdown: ""
    property string description: ""
    property string frozenDescription: ""
    property var pasteHandler: null
    property var selectAllHandler: null
    property var canSelectAllOverride: null
    property var canPasteOverride: null
    property var numericPolicy: null
    property string pasteError: ""
    property Connections editWatch: Connections {
        target: root.editor
        function onTextChanged() { root.pasteError = "" }
    }
    function paste() {
        if (pasteHandler && pasteHandler()) return
        if (!numericPolicy) { editor.paste(); return }
        const start = editor.selectionStart, end = editor.selectionEnd
        const before = editor.text.slice(0, start), after = editor.text.slice(end)
        const raw = before + textEditing.clipboardText() + after
        const p = numericPolicy
        const result = textEditing.numeric(raw, p.unit || "", p.kind || "", p.minimum, p.maximum, p.decimals)
        pasteError = result.ok ? "" : result.error
        if (!result.ok) return
        let normalized = result.text
        if (p.locale && p.locale.decimalPoint !== ".") normalized = normalized.replace(".", p.locale.decimalPoint)   // the field's locale
        // Preserve the surrounding characters and one native paste undo operation whenever possible.
        let replacement = normalized
        let left = 0, right = editor.length
        if (normalized.startsWith(before) && normalized.endsWith(after)) {
            replacement = normalized.slice(before.length, normalized.length - after.length || undefined)
            left = start; right = end
        }
        editor.select(left, right)
        textEditing.replaceSelection(editor, replacement)
    }
    property bool menuActive: false
    property bool closingMenu: false
    property string frozenWhole: ""
    property string frozenSelection: ""
    property string frozenMarkdown: ""
    property bool frozenPartial: false
    readonly property bool safe: !editor || editor.echoMode === undefined || editor.echoMode === TextInput.Normal
    readonly property bool available: !invalidTarget && (!target || (target.enabled && target.visible))
    readonly property bool writable: available && !!editor && !readOnly
    readonly property bool selected: !!editor && editor.selectionStart !== editor.selectionEnd
    readonly property bool partialSelection: menuActive ? frozenPartial : selected && Math.abs(editor.selectionEnd - editor.selectionStart) < editor.length
    readonly property bool hasMarkdown: (menuActive ? frozenMarkdown : markdown).length > 0
    readonly property bool hasDescription: (menuActive ? frozenDescription : description).length > 0
    readonly property bool canPaste: writable && (canPasteOverride === null ? editor.canPaste : canPasteOverride)
    function begin() {
        frozenWhole = wholeText; frozenSelection = editor && safe ? editor.getText(editor.selectionStart, editor.selectionEnd) : ""
        frozenPartial = selected && Math.abs(editor.selectionEnd - editor.selectionStart) < editor.length
        frozenIdentity = identity; frozenMarkdown = markdown; frozenDescription = description; menuActive = true
    }
    function end() {
        const valid = !invalidTarget && available
        menuActive = false; closingMenu = true
        Qt.callLater(() => {
            if (valid && identity === frozenIdentity && pendingExit && editor && !editor.activeFocus && available && focusExit) focusExit()
            pendingExit = false; closingMenu = false
        })
    }
    function allowed(command) {
        if (!available) return false
        switch (command) {
        case "undo": return writable && editor.canUndo
        case "redo": return writable && editor.canRedo
        case "cut": return writable && safe && selected
        case "copy": return safe && (menuActive ? frozenSelection.length > 0 || (readOnly && frozenWhole.length > 0) : selected || (readOnly && wholeText.length > 0))
        case "whole": return safe && (menuActive ? frozenWhole : wholeText).length > 0
        case "markdown": return safe && hasMarkdown
        case "description": return safe && hasDescription
        case "paste": return canPaste
        case "delete": return writable && selected
        case "selectAll": return canSelectAllOverride === null ? !!editor && editor.length > 0 && Math.abs(editor.selectionEnd-editor.selectionStart) !== editor.length : canSelectAllOverride
        }
        return false
    }
    function execute(command) {
        if (!allowed(command)) return
        switch (command) {
        case "copy":
            textEditing.copy(menuActive ? (frozenSelection || frozenWhole) : selected ? editor.getText(editor.selectionStart, editor.selectionEnd) : wholeText); break
        case "whole": textEditing.copy(menuActive ? frozenWhole : wholeText); break
        case "markdown": textEditing.copy(menuActive ? frozenMarkdown : markdown); break
        case "description": textEditing.copy(textEditing.plainHtml(menuActive ? frozenDescription : description)); break
        case "paste": paste(); break
        case "delete": editor.remove(editor.selectionStart, editor.selectionEnd); break
        case "selectAll": if (selectAllHandler) selectAllHandler(); else editor.selectAll(); break
        case "undo": editor.undo(); break
        case "redo": editor.redo(); break
        case "cut": editor.cut(); break
        }
    }
}
