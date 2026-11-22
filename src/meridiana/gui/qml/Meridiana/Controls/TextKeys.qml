import QtQuick

Item {
    required property var editor
    required property var actions
    Keys.onPressed: event => editor.handleTextKey(event)
    function handle(event) {
        event.accepted = false
        if (actions.closingMenu && [Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Up, Qt.Key_Down].includes(event.key)) {
            event.accepted = true; return false
        }
        if (actions.menuActive && actions.popup) {
            const menu = actions.popup
            if (event.key === Qt.Key_Escape) { menu.close(); event.accepted = true; return false }
            if (event.key === Qt.Key_Down || event.key === Qt.Key_Up) {
                const direction = event.key === Qt.Key_Down ? 1 : -1
                let next = menu.currentIndex
                for (let i = 0; i < menu.count; ++i) {
                    next = (next + direction + menu.count) % menu.count
                    const item = menu.itemAt(next)
                    if (item && item.enabled && item.visible && !item.rule) { menu.currentIndex = next; break }
                }
                event.accepted = true; return false
            }
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                const item = menu.itemAt(menu.currentIndex)
                if (item && item.enabled && item.visible) item.triggered()
                menu.close(); event.accepted = true; return false
            }
        }
        if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) {
            event.accepted = true
            return true
        }
        const commands = [[StandardKey.Undo, "undo"], [StandardKey.Redo, "redo"], [StandardKey.Cut, "cut"],
                          [StandardKey.Copy, "copy"], [StandardKey.Paste, "paste"], [StandardKey.SelectAll, "selectAll"]]
        for (const pair of commands) if (event.matches(pair[0])) {
            actions.execute(pair[1]); event.accepted = true; return false
        }
        if ((event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace)
                && (!actions.writable || (!actions.selected && (event.key === Qt.Key_Delete
                    ? editor.cursorPosition >= editor.length : editor.cursorPosition <= 0)))) event.accepted = true
        return false
    }
}
