import QtQuick
import QtQuick.Controls as C
import QtQuick.Templates as T
import Meridiana.Theme

// R636 (Daniel 15/11/2026: «darei la possibilità alla casella di input di testo di meridio di accettare anche il
// multiriga se gli si sta scrivendo un messaggio più lungo. Ovviamente con limiti in altezza e barra di scorrimento»):
// a field of text that is born one line tall, as M.TextField, and grows by whole lines with its text (the words that
// wrap and the lines one breaks) up to `maxLines` (ControlMetrics.growLines) and never past `maxHeight`; beyond that
// its text scrolls inside it with the common bar and soft ends (M.ScrollBar, M.EdgeFades), the cursor always in view.
// Return sends (`accepted`), Shift+Return breaks the line. The ground, the radius, the borders, the paddings, the
// colours and the hint are M.TextField's; with one line it stands as one. The wheel scrolls its text only when it has
// some to scroll, else it goes on to what is under it.
FocusScope {
    id: root
    property alias textActions: textCommands
    property alias text: area.text
    property alias placeholderText: area.placeholderText
    property alias area: area
    property bool invalid: false
    property int maxLines: ControlMetrics.growLines
    property real maxHeight: Infinity
    // the room at the field's right for what is drawn inside it (a button), as M.TextField's rightPadding
    property real rightRoom: ControlMetrics.fieldInset
    readonly property alias lineCount: area.lineCount
    // the height of a line as the text lays it out, not as the font's metrics say: on the laptop (and here with IBM
    // Plex at the small text) a written line is 1 px taller than FontMetrics.height, the text was 1 px taller than the
    // field and its bar showed with nothing to scroll (16/11/2026). The empty field has the metrics' line.
    readonly property real lineHeight: area.length > 0 && area.lineCount > 0 ? area.contentHeight / area.lineCount
                                                                             : metrics.height
    readonly property alias hovered: area.hovered
    // the line's box in one line, as M.TextField: its baseline on the field's middle by its capitals (R582)
    readonly property real oneLine: Theme.size.CONTROL
    readonly property real topRoom: ControlMetrics.textBaseline(oneLine, metrics, Screen.devicePixelRatio) - metrics.ascent
    readonly property real bottomRoom: oneLine - topRoom - lineHeight
    // whole lines, as many as `maxLines` and `maxHeight` allow, never less than one
    readonly property int capLines: Math.max(1, Math.min(maxLines, Math.floor((maxHeight - topRoom - bottomRoom) / lineHeight)))
    readonly property real capHeight: topRoom + bottomRoom + capLines * lineHeight
    readonly property real wantedHeight: topRoom + bottomRoom + Math.max(1, area.lineCount) * lineHeight
    readonly property bool scrolls: wantedHeight > capHeight + 0.5
    signal accepted()
    signal keyPressed(var event)       // before the field's own keys: accept it to keep it from them
    signal textEdited()
    implicitWidth: Theme.size.READING / 2
    implicitHeight: Math.max(oneLine, Math.min(capHeight, wantedHeight))
    activeFocusOnTab: true
    function insertLineBreak() { area.remove(area.selectionStart, area.selectionEnd); area.insert(area.cursorPosition, "\n") }
    FontMetrics { id: metrics; font: area.font }
    Rectangle {
        anchors.fill: parent
        color: Theme.colors.field; radius: Theme.radius.CONTROL
        border.width: Theme.focusRing(area) ? Theme.line.FOCUS : Theme.line.HAIR
        border.color: !root.enabled ? "transparent" : root.invalid ? Theme.colors.danger
            : Theme.focusRing(area) ? Theme.colors.focus : area.hovered ? Theme.colors.field_line : "transparent"
    }
    Flickable {
        id: view
        anchors.fill: parent
        // scrolling, the bar stands in the lane of the field's right, before what is drawn there (rightRoom); the text
        // ends where it ends in one line
        anchors.rightMargin: root.scrolls ? Math.max(0, root.rightRoom - Theme.size.SCROLLBAR) : 0
        contentWidth: width
        // within the cap nothing scrolls, whatever a fraction of a pixel of the layout says
        contentHeight: root.scrolls ? area.implicitHeight : height
        clip: true
        interactive: root.scrolls
        boundsBehavior: Flickable.StopAtBounds
        // the cursor in view, the line it is on whole
        function follow() {
            const r = area.cursorRectangle
            if (r.y < contentY + root.topRoom) contentY = Math.max(0, r.y - root.topRoom)
            else if (r.y + r.height > contentY + height - root.bottomRoom)
                contentY = Math.min(Math.max(0, contentHeight - height), r.y + r.height - height + root.bottomRoom)
        }
        T.TextArea {
            id: area
            property alias textActions: textCommands
            TextActions { id: textCommands; editor: area }

            TextKeys { id: textKeys; editor: area; actions: textCommands; enabled: area.textKeysEnabled }
            property bool textKeysEnabled: true
            function handleTextKey(event) { if (textKeys.handle(event)) C.ContextMenu.menu.popup(area, 0, area.height) }
            Keys.forwardTo: [textKeys]

            C.ContextMenu.menu: TextMenu { actions: textCommands }
            function openTextMenu(x, y) { const menu = C.ContextMenu.menu; if (!menu.visible) menu.popup(area, x, y) }
            onPressAndHold: event => area.openTextMenu(event.x, event.y)

            width: view.width
            implicitHeight: contentHeight + topPadding + bottomPadding
            height: implicitHeight
            focus: true
            leftPadding: ControlMetrics.fieldInset
            rightPadding: root.scrolls ? Theme.size.SCROLLBAR : root.rightRoom
            topPadding: root.topRoom
            bottomPadding: root.bottomRoom
            font.family: Theme.fontFamily
            font.pixelSize: Theme.text.body.size
            color: enabled ? Theme.colors.text : Theme.disabledText
            selectionColor: Theme.colors.select_bg
            selectedTextColor: Theme.colors.select_fg
            placeholderTextColor: Theme.colors.muted
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            persistentSelection: textCommands.menuActive
            hoverEnabled: true
            renderType: TextEdit.NativeRendering
            background: null
            onCursorRectangleChanged: view.follow()
            onTextChanged: Qt.callLater(view.follow)
            Label { x: area.leftPadding; y: area.topPadding; width: area.availableWidth
                text: area.placeholderText; color: area.placeholderTextColor; visible: !area.length && !area.preeditText
                elide: Text.ElideRight }
            Keys.onPressed: event => {
                if (textKeys.handle(event)) C.ContextMenu.menu.popup(area, 0, area.height)
                if (event.accepted) return
                root.keyPressed(event)
                if (event.accepted || (event.key !== Qt.Key_Return && event.key !== Qt.Key_Enter)) return
                event.accepted = true
                if (event.modifiers & Qt.ShiftModifier) root.insertLineBreak()
                else root.accepted()
            }
            // what the keyboard and the clipboard change, not what is set from outside (M.TextField's textEdited); told a
            // turn later, out of the change itself, so that a binding of `text` written back from it makes no loop
            Connections { target: area; enabled: area.activeFocus; function onTextChanged() { Qt.callLater(root.textEdited) } }
        }
        // the common bar, which brings the common soft ends (EdgeFades, R624)
        T.ScrollBar.vertical: ScrollBar { id: bar; visible: root.scrolls && size < 1 }
    }
}
