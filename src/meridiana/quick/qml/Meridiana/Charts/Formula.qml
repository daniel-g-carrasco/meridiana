import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Meridiana.Theme
import Meridiana.ChartBackend 1.0

Column {
    id: root
    property string tex: ""
    property real pointSize: 14
    property bool inViewport: true
    property string imageUrl: ""
    property string error: ""
    property string requestedKey: ""
    // R460: `fit` sizes the formula to its image (a symbol in a line of text); `centred` puts a wide line's image in
    // the middle, as the report sets an equation on a line of its own
    property bool fit: false
    property bool centred: false
    readonly property real renderScale: root.Window.window ? root.Window.window.devicePixelRatio : 1
    readonly property string appearanceKey: tex + "|" + Theme.colors.text + "|" + Theme.fontFamily
                                             + "|" + pointSize + "|" + renderScale
    readonly property bool ready: formulaImage.status === Image.Ready && imageUrl !== ""
    spacing: Theme.space.S
    visible: tex.length > 0

    function request() {
        if (!visible || !inViewport || !tex || requestedKey === appearanceKey) return
        requestedKey = appearanceKey
        services.requestFormula(requestedKey, tex, Theme.colors.text, Theme.fontFamily,
                                pointSize, renderScale)
    }
    onAppearanceKeyChanged: {
        imageUrl = ""
        error = ""
        requestedKey = ""
        pending.restart()
    }
    onVisibleChanged: pending.restart()
    onInViewportChanged: pending.restart()
    Component.onCompleted: pending.restart()
    // Wait for the containing Columns to settle before testing the viewport.
    Timer { id: pending; interval: 16; onTriggered: root.request() }
    ChartServices {
        id: services
        onFormulaReady: (key, url, message) => {
            if (key !== root.requestedKey || key !== root.appearanceKey) return
            root.error = message
            root.imageUrl = url
        }
    }
    // Wide equations keep their logical text size and can be panned horizontally.
    Flickable {
        width: root.fit ? formulaImage.width : root.width
        height: root.ready ? formulaImage.implicitHeight / root.renderScale : 0
        visible: root.ready
        contentWidth: Math.max(width, formulaImage.width)
        contentHeight: height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalFlick
        ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
        Image {
            id: formulaImage
            objectName: "formula-image"
            source: root.imageUrl
            asynchronous: true
            x: root.centred && !root.fit ? Math.max(0, (root.width - width) / 2) : 0
            width: implicitWidth / root.renderScale
            height: implicitHeight / root.renderScale
        }
    }
    Text {
        objectName: "formula-fallback"
        width: root.fit ? implicitWidth : root.width
        visible: !root.ready
        text: root.error ? root.tex : services.labels.preparing
        textFormat: Text.PlainText
        wrapMode: Text.WrapAnywhere
        color: Theme.colors.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.type.BODY
    }
    Text {
        objectName: "formula-error"
        width: root.fit ? implicitWidth : root.width
        visible: root.error.length > 0
        text: root.error
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: Theme.colors.text2
        font.family: Theme.fontFamily
        font.pixelSize: Theme.type.CAPTION
    }
}
