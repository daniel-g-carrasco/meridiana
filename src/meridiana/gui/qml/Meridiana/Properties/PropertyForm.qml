import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    property var sections: []
    required property var backend
    required property var stateOwner
    property bool interactive: true
    // Inside a section of the Plant: ui/plant_page.PlantSide.lend, the groups nested. R631: no margins of its own, the
    // panel's page (M.PanelPage) gives them, and its gap between two sections
    property bool lent: false
    spacing: lent ? Theme.space.S : M.ControlMetrics.panelGap
    FontMetrics { id: formMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size; font.weight: Theme.text.body.weight }
    Repeater {
        model: root.sections
        delegate: M.Section {
            id: section
            required property var modelData
            width: root.width
            nested: root.lent
            title: modelData.title
            helpId: modelData.help
            framed: modelData.framed
            density: ["site", "building", "subfield", "exclusion"].includes(modelData.key) ? "lead" : "form"
            // R598: the label column reads each field's outline (label, kind, range), not its value: a value changed
            // lays out its own editor only
            readonly property var labelHints: {
                const revision = Theme.revision
                let hints = {}
                for (const field of modelData.fields) {
                    const outline = field.outline
                    const hint = field.labelHint(formMetrics.font)
                    hint.minimum = field.editorMinimum(formMetrics.font)
                    hint.measured = !["check", "action", "note", "heading"].includes(outline.kind) && !outline.inlineWith
                    hints[outline.id] = hint
                }
                return hints
            }
            readonly property real labelWidth: {
                let longest = 0
                for (const id in labelHints) {
                    const hint = labelHints[id]
                    if (hint.measured && hint.width + 86 < width - 18) longest = Math.max(longest, hint.width)
                }
                return longest
            }
            collapsed: root.stateOwner.closed(modelData.key)
            onToggled: if (root.interactive) root.stateOwner.toggle(modelData.key)
            Repeater {
                model: modelData.fields
                delegate: PropertyEditor {
                    required property var modelData
                    width: parent.width
                    field: modelData
                    visible: !spec.inlineWith && !(spec.kind === "note" && !spec.display)
                    labelWidth: section.labelWidth
                    labelHint: section.labelHints[spec.id]
                    companion: section.modelData.fields.find(f => f.outline.inlineWith === modelData.outline.id) || null
                    backend: root.backend
                    interactive: root.interactive
                }
            }
        }
    }
}
