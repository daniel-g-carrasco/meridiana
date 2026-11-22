pragma Singleton
import QtQuick
// R628 (Daniel 15/11/2026: the windows «si ridimensionano»): the size a window was given by hand, one for each kind of
// window (M.Dialog's `sizeKey`: its objectName, the File's windows by their kind), as [width, height]. The window
// reads it at every opening and writes it when its grip is let go; a double click on a grip forgets it (the window
// goes back to the size it asks). Saved with the window's arrangement (Workbench.savedLayout, quick-shell.json:
// backend/shell_state.py), read back at the start (Workbench.restoreLayout).
QtObject {
    property var sizes: ({})
    function of(key) {
        const s = key ? sizes[key] : undefined
        return s && s.length === 2 && s[0] > 0 && s[1] > 0 ? Qt.size(s[0], s[1]) : Qt.size(0, 0)
    }
    function keep(key, width, height) {
        if (!key) return
        const next = Object.assign({}, sizes)
        next[key] = [Math.round(width), Math.round(height)]
        sizes = next
    }
    function forget(key) {
        if (!key || sizes[key] === undefined) return
        const next = Object.assign({}, sizes)
        delete next[key]
        sizes = next
    }
}
