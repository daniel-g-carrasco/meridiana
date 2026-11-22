import QtQuick

Menu {
    id: root
    objectName: "textContextMenu"
    required property var actions
    // Commit requests wait until the temporary menu focus has returned or left the editor.
    focus: true
    readonly property bool targetAvailable: !actions.target || (actions.target.visible && actions.target.enabled)
    onTargetAvailableChanged: if (!targetAvailable) close()
    onAboutToShow: { actions.popup = root; actions.begin(); textEditing.activateMenu(actions, root) }
    onClosed: { textEditing.deactivateMenu(root); actions.end(); actions.popup = null }
    MenuItem { text: textEditing.labels.undo; shortcutText: textEditing.shortcut("undo"); shown: !root.actions.readOnly; enabled: root.actions.allowed("undo"); onTriggered: root.actions.execute("undo") }
    MenuItem { text: textEditing.labels.redo; shortcutText: textEditing.shortcut("redo"); shown: !root.actions.readOnly; enabled: root.actions.allowed("redo"); onTriggered: root.actions.execute("redo") }
    MenuItem { rule: true; shown: !root.actions.readOnly }
    MenuItem { text: textEditing.labels.cut; shortcutText: textEditing.shortcut("cut"); shown: !root.actions.readOnly; enabled: root.actions.allowed("cut"); onTriggered: root.actions.execute("cut") }
    MenuItem { text: root.actions.copyLabel; shortcutText: textEditing.shortcut("copy"); enabled: root.actions.allowed("copy"); onTriggered: root.actions.execute("copy") }
    MenuItem { text: root.actions.wholeLabel; shown: root.actions.readOnly && root.actions.partialSelection; enabled: root.actions.allowed("whole"); onTriggered: root.actions.execute("whole") }
    MenuItem { text: textEditing.labels.markdown; shown: root.actions.hasMarkdown; enabled: root.actions.allowed("markdown"); onTriggered: root.actions.execute("markdown") }
    MenuItem { text: textEditing.labels.paste; shortcutText: textEditing.shortcut("paste"); shown: !root.actions.readOnly; enabled: root.actions.allowed("paste"); onTriggered: root.actions.execute("paste") }
    MenuItem { text: textEditing.labels.delete; shortcutText: textEditing.shortcut("delete"); shown: !root.actions.readOnly; enabled: root.actions.allowed("delete"); onTriggered: root.actions.execute("delete") }
    MenuSeparator { visible: !!root.actions.editor || !!root.actions.selectAllHandler || root.actions.hasDescription; height: visible ? implicitHeight : 0 }
    MenuItem { text: textEditing.labels.selectAll; shortcutText: textEditing.shortcut("selectAll"); shown: !!root.actions.editor || !!root.actions.selectAllHandler; enabled: root.actions.allowed("selectAll"); onTriggered: root.actions.execute("selectAll") }
    MenuItem { text: textEditing.labels.description; shown: root.actions.hasDescription; enabled: root.actions.allowed("description"); onTriggered: root.actions.execute("description") }
}
