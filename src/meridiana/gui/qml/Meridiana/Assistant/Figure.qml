pragma Singleton
import QtQml

// Meridio's figure for Character.qml (gui/backend/assistant.FigureBridge, given as the context property
// `assistantFigure`): a singleton reads it in the engine's root context, so that a Character made by a Repeater with
// required properties (whose context does not reach the root's properties) still finds it.
QtObject {
    readonly property var bridge: typeof assistantFigure !== "undefined" ? assistantFigure : null
    readonly property var data: bridge ? bridge.data : null
    function eyes(values, small) { return bridge ? bridge.eyes(values, small) : [] }
}
