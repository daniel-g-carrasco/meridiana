import QtQuick

// Keep the cached inspector and its draft, without laying it out behind another phase.
// The shell's inspector loaders fill their parent whenever they are shown.
Binding {
    required property Item panel
    target: panel
    property: "anchors.fill"
    value: panel.visible ? panel.parent : null
    restoreMode: Binding.RestoreBindingOrValue
}
