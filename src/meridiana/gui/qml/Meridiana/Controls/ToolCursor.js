.pragma library

// The pointer over a view of the drawing, the one rule of the plan and of the 3D view (Daniel 14/11/2026: «sul 2d il
// puntatore diventa una croce [...] ma sul 3d non vedo nessun cambio»): the open hand while Space is held (the view is
// dragged), the cross while a tool other than Select is in hand (Measure, a drawing tool, an object to place), the arrow
// with Select. Where the tool can do nothing (the 3D view's sky) the cross stays, without the snap's mark under it.

function shape(toolInHand, spaceHeld) {
    return spaceHeld ? Qt.OpenHandCursor : toolInHand ? Qt.CrossCursor : Qt.ArrowCursor
}
