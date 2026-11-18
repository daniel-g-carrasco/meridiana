.pragma library

// What a click with Ctrl or Shift selects in a tree: more rows of one group (R439). Pure: the rows are
// {id, group, selectable}, `selected` and `anchor` are ids. It gives {selected, anchor}.
// Ctrl adds or takes off one row, Shift takes the rows of its group from the anchor to the click, a plain click
// one row; a row of another group starts again, and the last row selected cannot be taken off.
function click(rows, selected, anchor, id, ctrl, shift) {
    var row = rows.find(function(r) { return r.id === id; });
    if (!row || row.selectable === false)
        return {selected: selected, anchor: anchor};
    function sameGroup(other) {
        var found = rows.find(function(r) { return r.id === other; });
        return !!found && found.group === row.group;
    }
    if (shift && sameGroup(anchor)) {
        var from = rows.findIndex(function(r) { return r.id === anchor; });
        var to = rows.findIndex(function(r) { return r.id === id; });
        var range = rows.slice(Math.min(from, to), Math.max(from, to) + 1).filter(function(r) {
            return r.group === row.group && r.selectable !== false;
        }).map(function(r) { return r.id; });
        return {selected: range, anchor: anchor};
    }
    if (ctrl && selected.length && selected.every(sameGroup)) {
        var at = selected.indexOf(id);
        if (at < 0)
            return {selected: selected.concat([id]), anchor: id};
        if (selected.length === 1)
            return {selected: selected, anchor: id};
        var left = selected.slice();
        left.splice(at, 1);
        return {selected: left, anchor: left[left.length - 1]};
    }
    return {selected: [id], anchor: id};
}
