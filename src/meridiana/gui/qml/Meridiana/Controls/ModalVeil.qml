import QtQuick
import Meridiana.Theme
// R586 (c) (Daniel 11/11/2026: «quando compaiono scuriscono correttamente tutto, ma lasciano non scurita la barra del
// titolo. Questo è un bug generalizzato con tutte le finestre»): the one veil under every modal window of the program
// (M.Dialog, a modal M.Popup). While it is shown it tells the theme, which veils the title bar too where the program
// colours it (backend/window_frame.py: Windows 11's DWM colours, Wayland's decoration drawn by Qt).
Rectangle {
    id: root
    objectName: "modalVeil"
    color: Theme.colors.press
    readonly property bool showing: visible && opacity > 0
    property bool _told: false
    function tell(on) { if (on !== _told) { _told = on; Theme.veil(on, root.color) } }
    onShowingChanged: tell(showing)
    Component.onCompleted: tell(showing)
    Component.onDestruction: tell(false)
}
