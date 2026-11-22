import QtQuick
import Meridiana.Theme

TextArea {
    id: root
    property string textStyle: "body"
    readonly property var spec: Theme.text[textStyle] || Theme.text.body
    font.pixelSize: spec.size
    font.weight: spec.weight
    color: Theme.colors[spec.tone]
    property string markdownSource: ""
    textActions.markdown: markdownSource
    bare: true
    readOnly: true
    selectByKeyboard: true
    activeFocusOnTab: true
    // R570: a drag over the words selects them and goes no further. The text's own selection by the mouse is an item's
    // grab, and a DragHandler behind (the plan's, the 3D view's, under a help bubble or Meridio's) had a passive grab
    // of the same press and took the drag over at its threshold (Qt hands the moves to the passive grabbers first):
    // the words were not selected and the plan moved. This handler, above, takes the drag first and selects. Only on
    // the surfaces that float over the plan (`dragSelects`: the help's bubble, Meridio's words): elsewhere a click on
    // a control under the text's box (the catalogue's «Choose») went to it no more.
    property bool dragSelects: false
    DragHandler {
        enabled: root.dragSelects
        target: null
        acceptedButtons: Qt.LeftButton
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onActiveChanged: if (active) root.cursorPosition = root.positionAt(centroid.pressPosition.x, centroid.pressPosition.y)
        onCentroidChanged: if (active) root.moveCursorSelection(root.positionAt(centroid.position.x, centroid.position.y), TextEdit.SelectCharacters)
    }
}
