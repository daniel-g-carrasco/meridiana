import QtQml
import QtQml.Models

// A list of plain rows as a model that keeps its delegates: a row with the same key stays where it is, with its hover and
// its state, and only what came or went is added or taken away. A delegate reads its row by its key, as
// `byKey[rowKey]` (`rowKey` is the model's role): during a sync the indices move one step at a time, and a delegate
// that read `current[index]` showed, for a turn or for good, the row of another index; a heading took the height of a
// row and was drawn over it, a row showed twice (R450). `current` stays, for who reads the rows in order.
QtObject {
    id: root
    property var rows: []
    property var keyOf: row => row.key
    property var current: []
    property var byKey: ({})
    signal synced()
    readonly property ListModel model: ListModel {}
    // At the end of this turn: delegates made during the binding's own update would read it back, a binding loop.
    onRowsChanged: Qt.callLater(sync)
    function sync() {
        const seen = {}, wanted = rows.map(row => {
            const key = String(keyOf(row)); seen[key] = (seen[key] || 0) + 1
            return key + "#" + seen[key]
        })
        const keep = new Set(wanted), list = model, map = {}
        for (let i = 0; i < wanted.length; i++) map[wanted[i]] = rows[i]
        byKey = map
        for (let i = list.count - 1; i >= 0; i--) if (!keep.has(list.get(i).rowKey)) list.remove(i)
        current = rows      // after the removals and before the rest: no delegate ever reads past the end
        for (let i = 0; i < wanted.length; i++) {
            if (i < list.count && list.get(i).rowKey === wanted[i]) continue
            let found = -1
            for (let j = i + 1; j < list.count; j++) if (list.get(j).rowKey === wanted[i]) { found = j; break }
            if (found >= 0) list.move(found, i, 1)
            else list.insert(i, {rowKey: wanted[i]})
        }
    }
}
