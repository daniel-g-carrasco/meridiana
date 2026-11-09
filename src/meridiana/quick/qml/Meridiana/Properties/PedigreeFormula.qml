import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    property var backend: null
    property string formula: ""
    property bool active: false
    property real textSize: Theme.text.body.size
    property string ink: Theme.colors.text
    property string family: Theme.fontFamily
    property real ratio: Screen.devicePixelRatio
    property string requestKey: ""
    property var result: ({source: "", width: 0, height: 0, error: ""})
    implicitHeight: Math.max(Theme.size.CONTROL, result.source ? result.height : fallback.implicitHeight)
    function request() {
        if (active && visible && backend && formula.length)
            result = backend.requestFormula(formula, textSize, ink, family, ratio)
        requestKey = result.key || ""
    }
    onActiveChanged: Qt.callLater(request)
    onVisibleChanged: Qt.callLater(request)
    onFormulaChanged: { result = {source: "", height: 0, error: ""}; Qt.callLater(request) }
    onBackendChanged: Qt.callLater(request)
    onTextSizeChanged: Qt.callLater(request)
    onInkChanged: Qt.callLater(request)
    onFamilyChanged: Qt.callLater(request)
    onRatioChanged: Qt.callLater(request)
    Component.onCompleted: Qt.callLater(request)
    Connections {
        target: root.backend
        function onFormulaReady(key, value) {
            if (key === root.requestKey)
                root.result = value
        }
    }
    Image {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(root.width, root.result.width || 0)
        height: root.result.height || 0
        source: root.result.source || ""
        fillMode: Image.PreserveAspectFit
        visible: source.toString().length > 0
    }
    M.Label {
        id: fallback
        width: parent.width
        anchors.verticalCenter: parent.verticalCenter
        text: root.formula
        wrapMode: Text.WrapAnywhere
        visible: !root.result.source
    }
    HoverHandler { id: hover }
    M.ToolTip { visible: hover.hovered && !!root.result.error; text: root.result.error || "" }
    Accessible.role: Accessible.StaticText
    Accessible.name: formula
}
