import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
import Meridiana.Controls as M
import Meridiana.Catalog
import QtQuick.Dialogs
import Meridiana.Theme

Item {
    id: root
    anchors.fill: parent
    z: 1000
    property var dialogsBackend: filesDialogsBackend
    M.Dialog {
        parent: root; anchors.centerIn: parent; popupType: C.Popup.Item
        objectName: "fileCatalogDialog"
        width: Math.min(M.ControlMetrics.dialogWidth.page, root.width - 2 * M.ControlMetrics.dialogEdge); height: Math.min(800, root.height - 2 * M.ControlMetrics.dialogEdge)
        title: fileCatalogBackend.texts.title || ""
        visible: filePart.catalogVisible
        rejectText: filesDialogsBackend.labels.cancel
        onClosed: filePart.closeCatalog()
        contentItem: Loader {
            active: filePart.catalogVisible
            sourceComponent: CatalogPage {
                backend: fileCatalogBackend
                // R23 F6: «Choose» hidden here, in QML (the backend looked it up by name and hid it)
                Component.onCompleted: {
                    const pending = [this]
                    while (pending.length) {
                        const item = pending.pop()
                        if (item.objectName === "catalogChoose") { item.visible = false; return }
                        const kids = item.children || []
                        for (let i = kids.length - 1; i >= 0; i--) pending.push(kids[i])
                    }
                }
            }
        }
    }
    Connections { target: fileCatalogBackend; function onImportRequested(kind) { productFile.nameFilters = kind === 'modules' ? ['PVsyst (*.pan *.PAN)'] : ['PVsyst (*.ond *.OND)']; productFile.open() } }
    FileDialog { id: productFile; onAccepted: fileCatalogBackend.readProduct(selectedFile.toString()) }
    // R21-F2: the frame of the file's windows is the common popup, centred and modal; the page inside draws its own bar
    M.Popup {
        id: dialog
        objectName: "fileDialogOverlay"
        parent: root
        centered: true
        modal: true; focus: true
        ground: Theme.colors.panel
        closePolicy: C.Popup.CloseOnEscape
        visible: filePart.dialogVisible
        // the dialogs whose content fills what it is given have a height of their own; the others take their content's
        readonly property var sizes: ({shortcuts:[640,560], update:[520,0], pvsyst:[720,0], ifc:[680,0], template:[344,590], canopy:[760,548], "canopy-layout":[440,0], site:[640,600], report_bug:[640,640], about:[560,0], registry:[720,640], new:[720,640]})
        readonly property var size: sizes[dialogsBackend.kind] || [720,0]
        width: Math.min(root.width - 24, size[0])
        height: Math.min(root.height - 24, size[1] || pageContent.implicitHeight)
        padding: 0
        contentItem: DialogsPage { id: pageContent; backend: dialogsBackend }
        onClosed: if (filePart.dialogVisible) { dialogsBackend.cancel(); filePart.dismissDialog() }
    }
    Connections {
        target: filePart
        function onLogoRequested() { logoFile.open() }
        function onExportRequested() { exportReport.open() }
    }
    Connections {
        target: filesActions
        function onExportIfcRequested() { exportIfc.open() }
        function onExportDxfRequested() { exportDxf.open() }
    }
    FileDialog {
        id: exportIfc; title: filesActions.labels.exporting; fileMode: FileDialog.SaveFile
        // R513: the plan as a DXF beside the two IFC
        // r22-ifc: the plant added to the architect's own IFC, fourth
        nameFilters: [filesActions.labels.ifcAll, filesActions.labels.ifcPlant, filesActions.labels.dxfPlan, filesActions.labels.ifcOriginal]; defaultSuffix: "ifc"
        onAccepted: selectedNameFilter.index === 2
            ? dxfOptions.show(selectedFile.toString(), filesActions.dxfFrames(), filesActions.dxfParts, filesActions.labels)
            : filesActions.exportIfc(selectedFile.toString(), ["all", "plant", "", "original"][selectedNameFilter.index])
    }
    FileDialog {
        id: exportDxf; title: filesActions.labels.dxfTitle; fileMode: FileDialog.SaveFile
        nameFilters: [filesActions.labels.dxfPlan]; defaultSuffix: "dxf"
        onAccepted: dxfOptions.show(selectedFile.toString(), filesActions.dxfFrames(), filesActions.dxfParts, filesActions.labels)
    }
    DxfOptions {
        id: dxfOptions
        onChosen: (url, frame, parts) => filesActions.exportDxf(url, frame, parts)
    }
    Rectangle {
        visible: filesActions.status !== "" && dialogsBackend.kind !== "report_bug"
        anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 40
        width: Math.min(parent.width - 40, exportRow.implicitWidth + 24); height: exportRow.implicitHeight + 16
        color: Theme.colors.panel; border.color: Theme.colors.line; radius: Theme.radius.CARD
        RowLayout {
            id: exportRow; anchors.fill: parent; anchors.margins: 8
            M.Label { Layout.fillWidth: true; text: filesActions.status; wrapMode: Text.Wrap }
            M.Button { visible: filesActions.busy; text: filesActions.labels.cancel; onClicked: filesActions.cancelExport() }
        }
    }
    FileDialog {
        id: logoFile; title: filesSettingsBackend.text.logo
        nameFilters: [filesSettingsBackend.text.logoFilter]
        onAccepted: filePart.putReportLogo(selectedFile.toString())
    }
    FileDialog {
        id: exportReport
        title: reportBackend.labels.export
        fileMode: FileDialog.SaveFile
        // R460: the PDF, or the same report editable as ODT (LibreOffice) or DOCX (Word)
        nameFilters: [reportBackend.labels.pdfFilter, reportBackend.labels.odtFilter, reportBackend.labels.docxFilter]
        defaultSuffix: ["pdf", "odt", "docx"][Math.max(0, selectedNameFilter.index)]
        onAccepted: reportBackend.exportReport(selectedFile.toString(), selectedNameFilter.index)
    }
}
