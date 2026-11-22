import QtQuick

// A phase never finishes incubation on the click. Keep the same item after it is ready;
// the common progress thread covers its preparation, including WholeLoader's retry.
WholeLoader {
    id: root
    // The software render loop does not reliably finish nested incubation.
    // Preserve its existing completion on show; GPU windows stay asynchronous.
    asynchronous: !shown || GraphicsInfo.api !== GraphicsInfo.Software
    readonly property bool contentReady: status === Loader.Ready && item && (item.prepared === undefined || item.prepared)
    // Qt can lose a Repeater delegate during incubation without putting its
    // enclosing Loader in Error. Check once after preparation, then recover the
    // whole body through the same bounded retry as WholeLoader.
    function integrity() {
        if (!shown || status !== Loader.Ready || !item || _tries >= 2) return
        const pending = [item]
        let missing = false
        while (pending.length) {
            const node = pending.pop()
            if (node instanceof Loader && node.status === Loader.Loading) { check.restart(); return }
            if (node instanceof Repeater)
                for (let i = 0; i < node.count; i++) missing = missing || !node.itemAt(i)
            for (const child of node.children || []) pending.push(child)
        }
        if (!missing) return
        _tries += 1; remade += 1
        console.warn("PhaseLoader: rebuilding incomplete delegates", String(_lastSource))
        _remaking = true
        Qt.callLater(_resume)
    }
    Timer { id: check; interval: 50; onTriggered: root.integrity() }
    Connections {
        target: root
        function onShownChanged() { if (root.shown) check.restart(); else check.stop() }
        function onStatusChanged() { if (root.shown && root.status === Loader.Ready) check.restart() }
    }
    Component.onCompleted: if (shown) check.start()
    Binding {
        target: root.item; property: "visible"; value: root.contentReady
        when: root.item !== null && root.item.prepared !== undefined
        restoreMode: Binding.RestoreNone
    }
    ProgressBar {
        objectName: "phasePreparation"
        anchors.centerIn: parent
        width: Math.min(160, root.width)
        indeterminate: true
        visible: root.shown && (root.status === Loader.Loading || root._remaking || (root.status === Loader.Ready && !root.contentReady))
    }
}
