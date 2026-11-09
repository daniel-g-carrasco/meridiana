import QtQuick
import Meridiana.Theme
// The one «?» of the program (R21-F3, Daniel 07/11/2026: in Impianto «due ? d'aiuto diversi», the round one beside the
// card's title and a grey square in the section «Inverter»). The house's form is the round one of the cards' header:
// Lucide's circle-question-mark drawn by the provider (M.Icon), 12 px in a flat button of 20 px, a flat button's hover
// and press. Every help mark is this component, in a card's header, a section's heading, a tile: guard in
// tests/quick/sistema/test_simboli.py (no other «?» button, no other circle-question-mark). It was R469's 16 px square
// with a «?» character and a hair line round it.
Button {
    id: root
    flat: true
    readonly property bool helpMark: true     // how a test finds every help mark of a window
    padding: (implicitWidth - 12) / 2       // the icon's 12 px in the middle of the 20
    topPadding: padding; bottomPadding: padding
    focusPolicy: Qt.NoFocus
    implicitWidth: ControlMetrics.helpMark
    implicitHeight: ControlMetrics.helpMark
    Accessible.name: tip !== "" ? tip : "?"
    contentItem: Item {
        Icon { anchors.centerIn: parent; name: "circle-question-mark"; width: 12; height: 12
            color: root.enabled ? Theme.colors.text : Theme.disabledText }
    }
}
