import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as Controls

// A viewport-sized layer. Its scene transform is shared with the plan above it.
Item {
    id: root
    property var backend: null
    property real viewScale: 1
    property real offsetX: width / 2
    property real offsetY: height / 2
    property real viewRotation: 0
    property string fontFamily: Qt.application.font.family
    property real textSize: 13
    property bool showOverlays: true
    property bool showSite: true
    readonly property var world: backend ? backend.world : ({})
    readonly property bool worldActive: backend && backend.worldVisible
    clip: true

    function matrix(values) {
        return Qt.matrix4x4(values[0], values[1], values[2], values[3],
                           values[4], values[5], values[6], values[7],
                           values[8], values[9], values[10], values[11],
                           values[12], values[13], values[14], values[15]);
    }
    function screenPoint(x, y) {
        const angle = viewRotation * Math.PI / 180;
        return Qt.point(offsetX + viewScale * (x * Math.cos(angle) - y * Math.sin(angle)),
                        offsetY + viewScale * (x * Math.sin(angle) + y * Math.cos(angle)));
    }
    function placeLabels() {
        const occupied = [];
        for (let i = 0; i < labels.count; ++i) {
            const label = labels.itemAt(i);
            if (!label) continue;
            let show = root.backend && root.backend.worldVisible &&
                    (root.backend.equalEarth || 1 / root.viewScale >= 1500) &&
                    label.modelData.rank <= (1 / root.viewScale >= 5000 ? 3 : 6);
            if (show) {
                for (let j = 0; j < occupied.length; ++j) {
                    const previous = occupied[j];
                    if (label.x < previous.x + previous.width + 6 && label.x + label.width + 6 > previous.x &&
                            label.y < previous.y + previous.height + 4 && label.y + label.height + 4 > previous.y) {
                        show = false;
                        break;
                    }
                }
            }
            label.unobstructed = show;
            if (show) occupied.push({x: label.x, y: label.y, width: label.width, height: label.height});
        }
    }
    // A single ordered pass avoids a chain of visible bindings between hundreds of labels.
    onViewScaleChanged: labelLayout.restart()
    onOffsetXChanged: labelLayout.restart()
    onOffsetYChanged: labelLayout.restart()
    onViewRotationChanged: labelLayout.restart()
    onWorldChanged: labelLayout.restart()
    onTextSizeChanged: labelLayout.restart()
    onFontFamilyChanged: labelLayout.restart()
    Timer { id: labelLayout; interval: 0; onTriggered: root.placeLabels() }
    Connections {
        target: root.backend
        function onChanged() { labelLayout.restart() }
    }

    Rectangle {
        anchors.fill: parent
        color: root.backend && root.backend.worldVisible ? root.world.ocean || Theme.colors.overlay.ocean : Theme.colors.overlay.blank
    }
    Item {
        id: scene
        x: root.offsetX
        y: root.offsetY
        scale: root.viewScale
        rotation: root.viewRotation
        transformOrigin: Item.TopLeft
        Item {
            visible: root.backend && root.backend.worldVisible
            scale: 1000
            transformOrigin: Item.TopLeft
            Repeater {
                objectName: "mapCountryPaths"
                model: root.worldActive ? root.world.countries || [] : []
                delegate: Shape {
                    required property var modelData
                    preferredRendererType: Shape.GeometryRenderer
                    ShapePath {
                        strokeWidth: 0.0008 / root.viewScale
                        strokeColor: root.world.border || Theme.colors.overlay.border
                        fillColor: modelData.colour
                        fillRule: ShapePath.OddEvenFill
                        PathSvg { path: modelData.path }
                    }
                }
            }
            Shape {
                preferredRendererType: Shape.GeometryRenderer
                ShapePath {
                    strokeWidth: 0.0006 / root.viewScale
                    strokeColor: Theme.colors.overlay.graticule
                    fillColor: "transparent"
                    PathSvg { path: root.worldActive ? root.world.graticule || "" : "" }
                }
            }
        }
        Item {
            visible: root.backend && !root.backend.equalEarth
            Repeater {
                // A model that adds and removes parts one by one (R466): the Images that stay are not made again.
                // The sharper tiles draw over the coarser ones still on show while the new ones arrive.
                model: root.backend ? root.backend.tileModel : null
                delegate: Image {
                    required property string url
                    required property var clipRect
                    required property var quad
                    required property int zoom
                    width: 1
                    height: 1
                    z: zoom
                    source: url
                    sourceClipRect: Qt.rect(clipRect[0], clipRect[1], clipRect[2], clipRect[3])
                    smooth: true
                    // r24-fasi (studio 41, S3): not asynchronous. Qt's loader thread would call the provider's Python
                    // (it needs the GIL) while the window's thread, holding the GIL, removes a loading Image in the
                    // model's endRemoveRows and waits for that thread: test_integration stopped for good. The images
                    // come decoded and in the scene graph's format from the decoders' threads, so the provider only
                    // hands them over.
                    asynchronous: false
                    transform: Matrix4x4 { matrix: root.matrix(quad) }
                }
            }
        }
    }
    Rectangle {
        anchors.fill: parent
        color: "black"
        opacity: root.backend ? root.backend.veil : 0
    }
    Item {
        x: root.offsetX
        y: root.offsetY
        scale: root.viewScale
        rotation: root.viewRotation
        transformOrigin: Item.TopLeft
        visible: root.backend && !root.backend.equalEarth
        Repeater {
            model: root.backend ? root.backend.underlays : []
            delegate: Image {
                required property var modelData
                width: 1
                height: 1
                source: modelData.source
                visible: modelData.visible
                opacity: modelData.opacity
                smooth: true
                transform: Matrix4x4 { matrix: root.matrix(modelData.matrix) }
            }
        }
    }
    // Names stay screen-sized and upright while the geographic anchors move.
    Repeater {
        id: labels
        objectName: "mapCountryLabels"
        model: root.worldActive && (root.backend.equalEarth || 1/root.viewScale >= 1500) ? root.world.labels || [] : []
        onCountChanged: labelLayout.restart()
        delegate: Text {
            objectName: "mapCountryLabel"
            required property var modelData
            required property int index
            property point anchor: root.screenPoint(modelData.x, modelData.y)
            property bool unobstructed: false
            x: anchor.x - width / 2
            y: anchor.y - height / 2
            text: modelData.name
            color: Theme.colors.overlay.ink
            style: Text.Outline
            styleColor: Theme.colors.overlay.glass_solid
            font.family: root.fontFamily
            font.pixelSize: root.textSize
            visible: root.backend && root.backend.worldVisible &&
                     (root.backend.equalEarth || 1 / root.viewScale >= 1500) &&
                     modelData.rank <= (1 / root.viewScale >= 5000 ? 3 : 6) && unobstructed
        }
    }
    Rectangle {
        objectName: "mapSiteMark"
        visible: root.showSite && 1 / root.viewScale >= 100
        x: root.offsetX - Controls.ControlMetrics.planMarker / 2
        y: root.offsetY - Controls.ControlMetrics.planMarker / 2
        width: Controls.ControlMetrics.planMarker
        height: Controls.ControlMetrics.planMarker
        radius: Controls.ControlMetrics.planMarker / 2
        border.width: Controls.ControlMetrics.planMarkerRing
        border.color: Theme.colors.overlay.halo
        color: Theme.colors.overlay.select
    }
    // R552: the credit of the background is drawn by Plan.qml (mapCredit), above the project's drawing
    // The notice of a background that fell back on another source is MapNotice, above the plan (R463).
}
