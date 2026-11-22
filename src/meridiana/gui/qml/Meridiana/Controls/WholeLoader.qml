import QtQuick

// R625 (Daniel 15/11/2026: the Balance page empty, the Inverter section that opened on nothing): what is made in the
// background (a phase's page or panel warmed while hidden, Workbench.qml, and the Loaders inside it, which Qt then
// makes a slice at a time too) can be thrown away by Qt half made, when something it had made is destroyed between
// two slices («Object or context destroyed during incubation»): the Loader stays in Error, with no item, for good,
// and the page or the section shows nothing. This Loader makes its item again, whole, when it is seen in that state
// (shown, or failing while shown). `wanted` is what `active` would be; `shown` says when it is seen: its visibility,
// unless a holder that hides an empty body says better (a section open, PlantSide.qml). At most twice each time it is
// shown: an item that cannot be made at all (a fault in its QML) is said in the log, not made again in a loop.
Loader {
    id: root
    property bool wanted: true
    property bool shown: visible
    property bool _remaking: false
    property int _tries: 0
    // how many times it was made again (the tests read it)
    property int remade: 0
    // Qt may empty the source (or the component) of a Loader whose making failed, and the holder's binding is not asked
    // again: the last one given is kept here and given back
    property url _lastSource
    property Component _lastComponent: null
    onSourceChanged: if (String(source) !== "") _lastSource = source
    onSourceComponentChanged: if (sourceComponent) _lastComponent = sourceComponent
    active: wanted && !_remaking
    function remake() {
        if (status !== Loader.Error || !wanted || !shown || _tries >= 2) return
        _tries += 1
        remade += 1
        console.warn("WholeLoader: made again after a failed making:", String(_lastSource) || String(_lastComponent))
        // the broken making let go of first, a new one at the next turn
        _remaking = true
        Qt.callLater(_resume)
    }
    function _resume() {
        _remaking = false
        if (String(source) === "" && String(_lastSource) !== "") source = _lastSource
        else if (!sourceComponent && _lastComponent) sourceComponent = _lastComponent
    }
    onStatusChanged: if (status === Loader.Error) Qt.callLater(remake)
    onShownChanged: { if (!shown) _tries = 0; else Qt.callLater(remake) }
}
