import QtQuick
import Meridiana.Theme

// R644 (Daniel 15/11/2026: «non mi piace che quando attivo una qualsiasi funzione di un pulsante strumenti che è
// suddiviso con il pulsante per richiamare il menù a comparsa, rimanga evidenziata solo la prima metà»; of three
// variants drawn, «ci sta la 2»): the ground of every split button (Controls/SplitButton, Shell/PhaseSplitButton), one
// rule. With its tool on the whole button is lit, rounded at its outer corners only, in two tones whose change, the
// whole height, is the divider (no hair): the tool's half in the theme's `press`, the arrow's half a step less, `hover`.
// Under the pointer the tool's half takes the hover's layer over its tone; the arrow's half rises over the tool's
// (`hover` and `press`), and with its menu open more (`press` twice), so the halves never meet in one tone. Off, as
// before: under the pointer the whole button in `hover`, the half under it with its layer (theme_colors, HOVER, PRESS).
Item {
    id: root
    property real split: width / 2          // where the arrow's half begins
    property bool on: false                 // the command's tool, or one of its menu's, is on
    property bool commandEnabled: true
    property bool commandHovered: false
    property bool commandDown: false
    property bool arrowHovered: false
    property bool arrowDown: false
    property bool menuOpen: false
    readonly property bool lit: enabled && (on || commandHovered || arrowHovered || menuOpen)
    readonly property bool arrowPressed: arrowDown || menuOpen
    function tone(down, hovered) { return !root.enabled ? "transparent" : down ? Theme.colors.press : hovered ? Theme.colors.hover : "transparent" }
    Rectangle {
        objectName: "splitGround"
        // off and under the pointer: the whole button (the command off: the arrow's half alone, its menu still open)
        x: root.commandEnabled ? 0 : root.split
        width: root.commandEnabled ? root.width : root.width - root.split
        height: root.height
        radius: Theme.radius.CONTROL
        color: root.enabled && !root.on && root.lit ? Theme.colors.hover : "transparent"
    }
    Item {
        width: root.split; height: root.height; clip: true
        Rectangle { objectName: "splitCommandBase"; width: parent.width + Theme.radius.CONTROL; height: parent.height
            radius: Theme.radius.CONTROL; color: root.enabled && root.on && root.commandEnabled ? Theme.colors.press : "transparent" }
        Rectangle { objectName: "splitCommandLayer"; width: parent.width + Theme.radius.CONTROL; height: parent.height
            radius: Theme.radius.CONTROL; color: root.commandEnabled ? root.tone(root.commandDown, root.commandHovered) : "transparent" }
    }
    Item {
        x: root.split; width: root.width - root.split; height: root.height; clip: true
        Rectangle { objectName: "splitArrowBase"; x: -Theme.radius.CONTROL; width: parent.width + Theme.radius.CONTROL
            height: parent.height; radius: Theme.radius.CONTROL
            color: !root.enabled || !root.on ? "transparent" : root.arrowPressed ? Theme.colors.press : Theme.colors.hover }
        Rectangle { objectName: "splitArrowLayer"; x: -Theme.radius.CONTROL; width: parent.width + Theme.radius.CONTROL
            height: parent.height; radius: Theme.radius.CONTROL
            color: !root.on ? root.tone(root.arrowPressed, root.arrowHovered)
                 : root.enabled && (root.arrowPressed || root.arrowHovered) ? Theme.colors.press : "transparent" }
    }
}
