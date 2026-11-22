import QtQuick

// R564: one entry of a menu made from data, the same for the bar's menus, the plan's, the 3D view's and the project
// tree's: `entry` is {text, enabled, separator, header, icon, keys, note, tip, danger}; a separator without a header is
// a rule, with one a title (R533); `note` says why the entry is off, in the column of the keys. What it looks like is
// MenuItem's.
MenuItem {
    required property var entry
    rule: !!entry.separator && !entry.header
    heading: !!entry.header
    danger: !!entry.danger
    text: entry.text || ""
    iconName: entry.icon || ""
    tip: entry.tip || ""
    shortcutText: entry.note ? entry.note : entry.keys ? entry.keys.join(", ") : ""
    enabled: !rule && !heading && entry.enabled !== false
}
