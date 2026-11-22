import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as T
import QtQuick.Dialogs
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Dialogs as D

Item {
    id: root
    property var words: shellTasks.labels
    Connections {
        target: shellTasks
        function onShowDialog(kind) { dialog.kind=kind; dialog.open() }
        function onExportRequested(kind) { chooser.kind=kind; chooser.open() }
        function onVariantDialog(action, name) { variant.action=action; variantName.text=name; variant.open() }
    }
    M.Dialog {
        id: variant; objectName: "variantDialog"
        property string action: "new"
        property var others: shell.variants.filter(v=>v.id!==shell.currentVariant)
        implicitWidth: M.ControlMetrics.dialogSize.variant.width
        title: root.words[action+"Variant"]
        acceptText: root.words.apply; rejectText: root.words.cancel
        onAccepted: shellTasks.commitVariant(action,action==="delete" ? others[variantChoice.currentIndex].id : variantName.text)
        Column { width: parent.width; spacing: Theme.space.M
            M.ReadableText { width: parent.width; text: variant.action==="delete" ? root.words.chooseVariant : root.words.name; wrapMode: Text.Wrap }
            M.TextField { id: variantName; objectName: "variantName"; visible: variant.action!=="delete"; width: parent.width
                onAccepted: variant.accept() }
            M.ComboBox { id: variantChoice; visible: variant.action==="delete"; width: parent.width; model: variant.others; textRole: "text" }
        }
        onOpened: if(action!=="delete") { variantName.forceActiveFocus(); variantName.selectAll() }
    }
    FileDialog {
        id: chooser; property string kind: "csv"
        fileMode: FileDialog.SaveFile
        title: kind==="dxf" ? root.words.dxfTitle : root.words[kind]
        nameFilters: kind==="csv" ? ["CSV (*.csv)"] : kind==="dxf" ? [root.words.dxfPlan]
                     : [root.words.ifcAll, root.words.ifcPlant, root.words.dxfPlan, root.words.ifcOriginal]  // R513, r22-ifc
        onAccepted: (kind==="dxf" || kind==="ifc" && selectedNameFilter.index===2)
            ? dxfChoice.show(selectedFile.toString(), shellTasks.dxfFrames(), shellTasks.dxfParts, root.words)
            : shellTasks.exportTo(kind, selectedFile, kind!=="ifc" ? "all" : ["all", "plant", "", "original"][selectedNameFilter.index])
    }
    D.DxfOptions {
        id: dxfChoice
        onChosen: (url, frame, parts) => shellTasks.exportDxf(url, frame, parts)
    }
    M.Dialog {
        id: dialog; objectName: "shellCommandDialog"
        property string kind: "message"
        implicitWidth: kind==="compare" ? M.ControlMetrics.dialogSize.compare.width : M.ControlMetrics.dialogSize.message.width
        // the words take what they need; only the comparison table fills a height of its own
        implicitHeight: kind==="about" || kind==="message" ? fitHeight : M.ControlMetrics.dialogSize.compare.height
        title: root.words[kind] || L.title
        // R607: one command stops the comparison under way, the window's own: «Cancel» while it runs (it stops and
        // closes), «Close» after; a report's draft is sent from the window's row of buttons, not from a row in the body
        rejectText: kind==="compare" && shellTasks.busy ? root.words.cancel : root.words.close
        actions: kind==="compare" ? [{text: root.words.copy, enabled: !shellTasks.busy}]
            : kind==="feedback" ? [{text: root.words.copyDraft},
                                   {text: root.words.openDraft, enabled: summary.text.trim().length>0 && description.text.trim().length>0}] : []
        onActionTriggered: index => kind==="compare" ? shellTasks.copyComparison()
            : shellTasks.shareDraft(summary.text,description.text,environment.checked,index===1)
        onClosed: if(kind==="compare") shellTasks.cancel()
        ColumnLayout {
            M.ReadableText { visible: dialog.kind==="about"; Layout.fillWidth: true; text: shellTasks.about(); wrapMode: Text.Wrap }
            M.ReadableText { visible: dialog.kind!=="feedback" && dialog.kind!=="about"; Layout.fillWidth: true; text: shellTasks.message; wrapMode: Text.Wrap }
            M.ProgressBar { visible: shellTasks.busy; Layout.fillWidth: true; indeterminate: true }
            M.Table { id: comparison; visible: dialog.kind==="compare"; Layout.fillWidth: true; Layout.fillHeight: true
                columns: shellTasks.columns; model: shellTasks.rows
                // the best of each figure drawn strong (r23-tabelle: in place of a delegate of its own)
                emphasis: (row, column) => row.best !== null && row.best !== undefined && String(row.best) === column.key }
            ColumnLayout {
                visible: dialog.kind==="feedback"; Layout.fillWidth: true; Layout.fillHeight: true
                M.ReadableText { Layout.fillWidth: true; text: root.words.intro; wrapMode: Text.Wrap }
                M.TextField { id: summary; objectName: "feedbackTitle"; Layout.fillWidth: true; placeholderText: root.words.title; maximumLength: 180 }
                M.ScrollPage { Layout.fillWidth: true; Layout.preferredHeight: 150; follow: description
                    M.TextArea { id: description; width: parent.width; objectName: "feedbackDescription"; placeholderText: root.words.description
                        color: Theme.colors.text; wrapMode: Text.Wrap; selectByMouse: true }
                }
                M.CheckBox { id: environment; checked: true; text: root.words.environment }
                M.CopyLabel { text: root.words.preview }
                M.ScrollPage { Layout.fillWidth: true; Layout.fillHeight: true
                    M.TextArea { bare: true; width: parent.width; readOnly: true; selectByMouse: true; wrapMode: Text.Wrap; color: Theme.colors.text
                        text: shellTasks.preview(summary.text,description.text,environment.checked) }
                }
            }
        }
    }
}
