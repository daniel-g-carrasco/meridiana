import QtQuick
import Meridiana.Controls as M

M.ComboBox {
    textRole: "text"
    valueRole: "key"
    implicitWidth: M.ControlMetrics.choiceWidth
    wheelEnabled: activeFocus
}
