.pragma library
// The keys a view gives the measuring tool (study 46): their names as app/view/measure_tool.py MeasureTool.key reads
// them, "" for a key that is not the tool's (the view keeps it), and the modifiers as the bridge's bits
// (gui/backend/measure.py: 1 Ctrl, 2 Shift, 4 Alt; Ctrl with Alt is AltGr, not Ctrl).

function name(event) {
    var names = {}
    names[Qt.Key_Escape] = "Escape"; names[Qt.Key_Return] = "Enter"; names[Qt.Key_Enter] = "Enter"
    // F8 is not the tool's: it is the plan's Ortho, the window's shortcut, which the ruler's 15° guides follow
    names[Qt.Key_Backspace] = "Backspace"; names[Qt.Key_Delete] = "Delete"
    names[Qt.Key_Left] = "Left"; names[Qt.Key_Right] = "Right"; names[Qt.Key_Up] = "Up"; names[Qt.Key_Down] = "Down"
    names[Qt.Key_Shift] = "Shift"
    if (names[event.key]) return names[event.key]
    return /^[0-9,.-]$/.test(event.text) ? event.text : ""
}

function bits(flags) {
    return ((flags & Qt.ControlModifier) && !(flags & Qt.AltModifier) ? 1 : 0)
         | ((flags & Qt.ShiftModifier) ? 2 : 0) | ((flags & Qt.AltModifier) ? 4 : 0)
}

// the arrows, Enter, Backspace and a length typed are the tool's while a point is placed: the window's shortcuts
// must not take them first
function heldWhilePlaced(event) {
    var plain = !(event.modifiers & (Qt.ControlModifier | Qt.AltModifier))
    return [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down].indexOf(event.key) >= 0
        || (plain && ([Qt.Key_Return, Qt.Key_Enter, Qt.Key_Backspace].indexOf(event.key) >= 0
                      || /^[0-9,.-]+$/.test(event.text)))
}
