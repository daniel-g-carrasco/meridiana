import QtQuick
import QtQuick.Templates as T
// R628 (Daniel 15/11/2026: «non mi piace il fatto che non sia utilizzabile meridio» with a window open): a place in
// Qt's overlay for what stays usable over the windows (Meridio: Shell/Workbench.qml). Qt keeps the windows, modal
// popups, in its overlay over all of the window's content, and a modal one takes every press, hover and wheel on what
// is not inside it or inside a popup stacked over it: what stands here is inside such a popup, at the step its user
// gives it (`z`, Theme.stack). Open for as long as the window, not modal, without veil, focus or frame, closed by
// nothing. It is 0 x 0 at the window's corner: what it holds is drawn and takes the pointer outside its box (it does not
// clip), so the popup's own item, which would take every press over its box, takes none; only the surfaces it holds
// take theirs. What it holds goes in `contentItem` (`parent: stage.contentItem`), placed in the window's coordinates.
T.Popup {
    x: 0; y: 0; width: 0; height: 0; padding: 0
    modal: false; dim: false; focus: false
    closePolicy: T.Popup.NoAutoClose
    popupType: T.Popup.Item
    background: null; enter: null; exit: null
    contentItem: Item { }
    visible: true
}
