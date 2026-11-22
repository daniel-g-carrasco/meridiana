import QtQuick

// Preserve the render buffer at its natural size; the animated host clips it.
Loader {
    property bool frozen: false
}
