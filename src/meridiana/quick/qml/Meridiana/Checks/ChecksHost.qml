import QtQuick
import Meridiana.Checks

ChecksPage {
    backend: checksBackend
    readonly property string panelTitle: backend.title
    Component.onCompleted: {
        let candidate = parent
        while (candidate && candidate.panelId !== "checks") candidate = candidate.parent
        if (candidate) {
            titlePanel = candidate
            candidate.title = Qt.binding(function() { return checksBackend.title })
            for (const child of candidate.children)
                if (child.objectName === "checksTitleDrag")
                    child.width = Qt.binding(function() { return titleWidth })
        }
    }
}
