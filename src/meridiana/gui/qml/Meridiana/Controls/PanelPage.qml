import QtQuick

// R631 (Daniel 15/11/2026, the Plant panel beside Properties: «dove sarebbe l'armonizzazione e la centralizzazione
// richiesta?»): the one body of a side panel (Properties, Plant, the data of Production, Consumption and Balance,
// Deliverables). It is the panel's only scroll (R601: nothing scrolls inside it, no section has a bar of its own), its
// bar at the right of the card's body, outside the sections; the sections are its children (or a form's, laid as wide
// as it), with its gaps (ControlMetrics.panelGap), never margins of their own; a group inside a section is a nested
// M.Section (the title on its line, docs/design/sistema-grafico.md, «Gruppo dentro un gruppo»). Guards:
// tests/quick/shell/test_pannelli_r631.py.
// R637: no margins of its own either: the card keeps ControlMetrics.cardMargin round it on the four sides
// (Shell/DockPanel.qml), and the page's bar stands centred in the card's margin at its right (barInMargin).
// R633: the heads of its sections always in view while it scrolls (HeldHeads.qml). Guards:
// tests/quick/shell/test_testate_r633.py.
ScrollPage {
    // what the guard reads: this page is a panel's body
    readonly property bool panelBody: true
    leftMargin: 0
    rightMargin: 0
    air: 0
    barInMargin: true
    spacing: ControlMetrics.panelGap
    keepHeads: true
}
