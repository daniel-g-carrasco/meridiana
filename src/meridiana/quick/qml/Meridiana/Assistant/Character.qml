import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    property bool animated: true
    property bool awake: true
    property bool thinking: false
    property bool dragging: false
    property string style: "smooth"
    property string where: "local"
    property string expression: ""
    property bool blink: false
    property int gazeX: 0
    property int gazeY: 0
    property int pixelStep: 0
    property string state: thinking ? "thinking" : "idle"
    property real awakeUntil: Date.now() + 5000
    property real angle: 0
    property real breath: 0
    property real faceScale: 1
    property point lookedAt: Qt.point(0, 0)
    property bool following: false
    property real pointSince: 0
    property real pointMoved: 0
    property real nextBlink: Date.now() + randomBetween(4000, 8000)
    property real blinkUntil: 0
    property real nextGlance: Date.now() + randomBetween(7000, 16000)
    property point glance: Qt.point(0, 0)
    property real glanceUntil: 0
    property real nextExpression: Date.now() + 350
    property real expressionUntil: 0
    readonly property bool moving: animated && !Theme.reducedMotion && !dragging && visible
        && Window.window !== null && Window.window.active
    readonly property bool turning: moving && (awake || state !== "idle" || Date.now() < awakeUntil)
    function randomBetween(low, high) { return low + Math.random() * (high-low) }
    function touch() {
        awakeUntil = Date.now() + 5000
        if (Date.now() >= expressionUntil) nextExpression = Math.min(nextExpression, Date.now() + 350)
    }
    function lookAt(x, y) {
        const point = Qt.point(Math.abs(x) < 0.3 ? 0 : x > 0 ? 1 : -1, Math.abs(y) < 0.3 ? 0 : y > 0 ? 1 : -1)
        if (!following || point.x !== lookedAt.x || point.y !== lookedAt.y) { lookedAt = point; pointSince = Date.now() }
        following = true; pointMoved = Date.now()
    }
    onAwakeChanged: touch()
    onStateChanged: touch()
    onMovingChanged: {
        if (!moving) { blink = false; expression = ""; gazeX = 0; gazeY = 0; faceScale = 1 }
        else touch()
    }
    readonly property real inner: style === "pixel" ? Math.max(17, Math.floor(width * 0.74 / 17) * 17) : Math.floor(width * 0.74)
    implicitWidth: M.ControlMetrics.figure
    implicitHeight: M.ControlMetrics.figure
    radius: width / 2
    color: Theme.colors.panel
    border.color: Theme.colors.line
    function source(parts, closed, step) {
        return "image://assistant/" + [style, parts, encodeURIComponent(Theme.colors.text),
            encodeURIComponent(Theme.colors.assistant), thinking ? "1" : "0", closed ? "1" : "0", expression,
            step || 0, dragging ? 0 : gazeX, dragging ? 0 : gazeY].join("/")
    }
    Item {
        width: root.inner; height: root.inner * 16.4 / 24
        x: (root.width - width) / 2; y: (root.height - root.inner) / 2
        clip: true
        Image {
            id: rays
            visible: root.style !== "pixel"
            width: root.inner; height: width
            source: root.source("rays", false)
            sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)
            smooth: root.style !== "pixel"
            transform: Rotation {
                id: turn
                origin.x: rays.width / 2; origin.y: rays.height * 10.2 / 24
                angle: root.angle
            }
        }
        Repeater {
            model: root.style === "pixel" ? 8 : 0
            Image {
                required property int index
                width: root.inner; height: width
                source: root.source("rays", false, index)
                sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)
                smooth: false
                opacity: root.pixelStep === index ? 1 : 0
            }
        }
    }
    Image {
        id: face
        anchors.centerIn: parent
        width: root.inner; height: width
        source: root.source("face", root.blink)
        sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)
        smooth: root.style !== "pixel"
        scale: root.faceScale
    }
    Timer {
        interval: 50; running: root.moving; repeat: true
        property real last: Date.now()
        onRunningChanged: last = Date.now()
        onTriggered: {
            const now = Date.now(), dt = Math.max(0, (now-last)/1000)
            last = now
            const active = root.awake || root.state !== "idle" || now < root.awakeUntil
            if (active) root.angle = (root.angle + 6*dt) % 360
            root.pixelStep = Math.floor((root.angle % 30) / 3.75) % 8
            if (active || root.breath > 0) {
                const b = root.breath + dt
                root.breath = !active && (b >= 4 || b % 4 < root.breath % 4) ? 0 : b
            }
            root.faceScale = root.style === "pixel" ? 1 : 1 + 0.02*(1-Math.cos(2*Math.PI*root.breath/4))
            if (now >= root.nextBlink) { root.blinkUntil = now+120; root.nextBlink = now+root.randomBetween(4000,8000) }
            root.blink = now < root.blinkUntil
            if (now >= root.nextExpression) {
                root.expression = ["wink", "surprise", "grin", "hmm"][Math.floor(Math.random()*4)]
                root.expressionUntil = now+root.randomBetween(800,1300)
                root.nextExpression = now+root.randomBetween(60000,120000)
            }
            if (now >= root.expressionUntil) root.expression = ""
            if (now >= root.nextGlance) {
                const directions = [[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]]
                const p = directions[Math.floor(Math.random()*8)]
                root.glance = Qt.point(p[0],p[1]); root.glanceUntil = now+root.randomBetween(600,1300)
                root.nextGlance = now+root.randomBetween(7000,16000)
            }
            if (root.following && now-root.pointMoved >= 2000) root.following = false
            if (root.following) {
                if (now-root.pointSince >= 100) { root.gazeX=root.lookedAt.x; root.gazeY=root.lookedAt.y }
            } else {
                root.gazeX = now < root.glanceUntil ? root.glance.x : 0
                root.gazeY = now < root.glanceUntil ? root.glance.y : 0
            }
        }
    }
    Rectangle {
        width: 16; height: 16; radius: 8; anchors.right: parent.right; anchors.bottom: parent.bottom
        visible: root.where.length > 0
        color: Theme.colors.panel; border.color: Theme.colors.line
        M.Icon { anchors.centerIn: parent; width: 12; height: 12; iconName: root.where === "local" ? "house" : "cloud" }
    }
}
