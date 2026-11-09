import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    property var sections: []
    required property var backend
    required property var stateOwner
    property bool interactive: true
    // Inside a section of the Plant: ui/plant_page.PlantSide.lend, the page margins of the section, the groups nested.
    property bool lent: false
    spacing: Theme.space.S
    topPadding: lent ? 0 : 15
    bottomPadding: lent ? 0 : 9
    FontMetrics { id: formMetrics; font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size; font.weight: Theme.text.body.weight }
    Repeater {
        model: root.sections
        delegate: M.Section {
            id: section
            required property var modelData
            width: root.lent ? root.width : root.width - 18
            x: root.lent ? 0 : 9
            nested: root.lent
            title: modelData.title
            helpId: modelData.help
            helpTip: modelData.helpTip
            framed: modelData.framed
            density: ["site", "building", "subfield", "exclusion"].includes(modelData.key) ? "lead" : "form"
            readonly property var labelHints: {
                const revision = Theme.revision
                let hints = {}
                for (const field of modelData.fields) {
                    const hint = field.labelHint(formMetrics.font)
                    hint.minimum = field.editorMinimum(formMetrics.font)
                    hints[field.data.id] = hint
                }
                return hints
            }
            readonly property real labelWidth: {
                let longest = 0
                for (const field of modelData.fields) {
                    const spec = field.data
                    if (["check", "action", "note", "heading"].includes(spec.kind) || spec.inlineWith) continue
                    const measured = labelHints[spec.id].width
                    if (measured + 86 < width - 18) longest = Math.max(longest, measured)
                }
                return longest
            }
            collapsed: root.stateOwner.closed(modelData.key)
            onToggled: if (root.interactive) root.stateOwner.toggle(modelData.key)
            onHelpRequested: if (root.interactive) root.backend.help(helpId)
            Repeater {
                model: modelData.fields
                delegate: PropertyEditor {
                    required property var modelData
                    width: parent.width
                    field: modelData
                    visible: !spec.inlineWith && !(spec.kind === "note" && !spec.display)
                    labelWidth: section.labelWidth
                    labelHint: section.labelHints[spec.id]
                    companion: section.modelData.fields.find(f => f.data.inlineWith === spec.id) || null
                    backend: root.backend
                    interactive: root.interactive
                }
            }
        }
    }
}
