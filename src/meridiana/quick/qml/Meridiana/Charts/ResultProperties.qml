import QtQuick

// Explicit integration point: the Properties branch supplies persisted editors.
// This component does not duplicate settings or create a second editable state.
Loader {
    property var pageData: ({})
    property Component editorComponent: null
    signal actionRequested(string action)
    sourceComponent: editorComponent
}
