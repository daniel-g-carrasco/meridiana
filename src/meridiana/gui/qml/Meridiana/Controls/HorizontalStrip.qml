import QtQuick

// A row of tools that scrolls sideways when the room is too narrow for it, and only then (the 3D view's bar; the phase
// toolbar is the same strip): no bar, no bounce past its ends, cut at its edges. Its height is its content's.
Flickable {
    contentHeight: height
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.HorizontalFlick
}
