import QtQuick
import Meridiana.Controls as M

M.ComboBox {
    id: root
    property var selectedValue: ""
    currentIndex: model ? model.findIndex(item => item.id === selectedValue) : -1
    textRole: "name"
    valueRole: "id"
    wheelEnabled: activeFocus
}
