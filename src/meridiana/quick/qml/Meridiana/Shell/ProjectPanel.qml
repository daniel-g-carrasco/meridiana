import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as T
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: tree
    spacing: Theme.space.XS
    M.Button { Layout.fillWidth: true; text: shell.site.name; iconName: "site"; flat: true
        onClicked: backend.select("site","","") }
    ListView {
        objectName: "projectList"; Layout.fillWidth: true; Layout.fillHeight: true
        clip: true; model: backend.objects
        section.property: "kind"; section.criteria: ViewSection.FullString
        section.delegate: M.Label {
            required property string section
            text: (section === "building" ? L.buildings : L.subfields)
            textStyle: "label"; height: Theme.size.NAV
        }
        T.ScrollBar.vertical: M.ScrollBar { }
        delegate: M.Button {
            id: projectRow
            required property var modelData
            width: ListView.view.width; height: Theme.size.NAV
            text: modelData.name; iconName: modelData.kind === "building" ? "building" : "subfield"
            flat: true; checked: modelData.oid === backend.selection.oid
            contentItem: Row { spacing: Theme.space.S
                M.Icon { iconName: projectRow.iconName }
                M.Label { text: projectRow.text; textStyle: "body" }
            }
            onClicked: backend.select(modelData.kind, modelData.oid, "")
        }
    }
}
