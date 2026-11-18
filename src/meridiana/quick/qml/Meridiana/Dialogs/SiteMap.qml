import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    property var backend
    property var map: backend ? backend.mapBackend : null
    property var countries: map ? JSON.parse(map.countriesJson) : []
    property real cx: map ? map.center[0] : 0.53
    property real cy: map ? map.center[1] : 0.37
    property int zoom: map ? map.zoom : 6
    property real scale: 256 * Math.pow(2, zoom)
    property real metresPerPixel: 40075016.686 * Math.cos(Math.atan(Math.sinh(Math.PI * (1 - 2 * cy)))) / scale
    color: map ? map.colours.ocean : Theme.colors.card
    clip: true
    function refresh() {
        if (map)
            map.viewport(cx, cy, zoom, width, height);
        canvas.requestPaint();
    }
    onWidthChanged: fetch.restart()
    onHeightChanged: fetch.restart()
    Timer {
        id: fetch
        interval: 100
        onTriggered: root.refresh()
    }
    Connections {
        target: root.map
        function onChanged() {
            if (!drag.pressed) {
                root.cx = root.map.center[0];
                root.cy = root.map.center[1];
                root.zoom = root.map.zoom;
            }
            canvas.requestPaint();
        }
    }
    Component.onCompleted: fetch.restart()
    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            let c = getContext("2d");
            c.reset();
            c.fillStyle = root.color;
            c.fillRect(0, 0, width, height);
            if (!root.map)
                return;
            c.strokeStyle = root.map.colours.border;
            c.lineWidth = 0.8;
            let rings = root.countries;
            for (let country of rings) {
                let r = country.ring;
                c.fillStyle = country.color;
                c.beginPath();
                for (let i = 0; i < r.length; i++) {
                    let x = (r[i][0] - root.cx) * root.scale + width / 2;
                    let y = (r[i][1] - root.cy) * root.scale + height / 2;
                    if (i === 0)
                        c.moveTo(x, y);
                    else
                        c.lineTo(x, y);
                }
                c.closePath();
                c.fill();
                c.stroke();
            }
            if (root.metresPerPixel >= 1500) {
                let occupied = [];
                c.font = Theme.text.secondary.size + "px '" + Theme.fontFamily + "'";
                c.textAlign = "center"; c.textBaseline = "middle";
                c.fillStyle = root.map.colours.label;
                for (let label of root.map.labels) {
                    if (root.metresPerPixel >= 5000 && label.rank > 3) continue;
                    let x = (label.anchor[0] - root.cx) * root.scale + width / 2;
                    let y = (label.anchor[1] - root.cy) * root.scale + height / 2;
                    let w = c.measureText(label.text).width + 6, h = Theme.text.secondary.size + 4;
                    let box = {x:x-w/2, y:y-h/2, w:w, h:h};
                    if (occupied.some(o => box.x < o.x+o.w && box.x+box.w > o.x && box.y < o.y+o.h && box.y+box.h > o.y)) continue;
                    occupied.push(box);
                    c.fillText(label.text, x, y);
                }
            }
        }
    }
    Repeater {
        model: root.map && root.map.allowed ? root.map.tiles : []
        delegate: Image {
            required property var modelData
            x: (modelData.x / Math.pow(2, modelData.z) - root.cx) * root.scale + root.width / 2
            y: (modelData.y / Math.pow(2, modelData.z) - root.cy) * root.scale + root.height / 2
            width: M.ControlMetrics.mapTile
            height: M.ControlMetrics.mapTile
            source: modelData.url
            asynchronous: true
        }
    }
    Rectangle {
        visible: root.map && root.map.marker.length === 2
        x: root.map && root.map.marker.length ? (root.map.marker[0] - root.cx) * root.scale + root.width / 2 - M.ControlMetrics.siteMarker / 2 : 0
        y: root.map && root.map.marker.length ? (root.map.marker[1] - root.cy) * root.scale + root.height / 2 - M.ControlMetrics.siteMarker / 2 : 0
        width: M.ControlMetrics.siteMarker
        height: M.ControlMetrics.siteMarker
        radius: M.ControlMetrics.siteMarker / 2
        color: Theme.colors.accent
        border.color: Theme.colors.card
        border.width: Theme.line.FOCUS
    }
    MouseArea {
        id: drag
        anchors.fill: parent
        property real px
        property real py
        property real oldx
        property real oldy
        onPressed: event => {
            px = event.x;
            py = event.y;
            oldx = root.cx;
            oldy = root.cy;
        }
        onPositionChanged: event => {
            if (pressed) {
                root.cx = oldx - (event.x - px) / root.scale;
                root.cy = oldy - (event.y - py) / root.scale;
                canvas.requestPaint();
            }
        }
        onReleased: event => {
            if (Math.abs(event.x - px) + Math.abs(event.y - py) < 6) {
                let x = root.cx + (event.x - width / 2) / root.scale;
                let y = root.cy + (event.y - height / 2) / root.scale;
                root.backend.pickLocation(Math.atan(Math.sinh(Math.PI * (1 - 2 * y))) * 180 / Math.PI, x * 360 - 180);
            }
            root.refresh();
        }
        onWheel: event => {
            root.zoom = Math.max(2, Math.min(19, root.zoom + (event.angleDelta.y > 0 ? 1 : -1)));
            root.refresh();
        }
    }
    Row {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Theme.space.M
        spacing: Theme.space.S
        M.Button {
            iconName: "control:plus"
            tip: root.backend ? root.backend.labels.zoomIn : ""
            onClicked: {
                root.zoom = Math.min(19, root.zoom + 1);
                root.refresh();
            }
        }
        M.Button {
            iconName: "control:minus"
            tip: root.backend ? root.backend.labels.zoomOut : ""
            onClicked: {
                root.zoom = Math.max(2, root.zoom - 1);
                root.refresh();
            }
        }
    }
    M.Label {
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: Theme.space.S
        text: root.map && root.map.allowed ? "© OpenStreetMap contributors" : "Natural Earth"
        textStyle: "caption"; color: root.map ? root.map.colours.label : Theme.colors.text
    }
}
