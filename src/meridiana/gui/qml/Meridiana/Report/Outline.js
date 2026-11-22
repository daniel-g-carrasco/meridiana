.pragma library
// The report's chapters (level 1) and paragraphs (level 2) as the tree's nodes, each with a key that survives a new
// preview (its chapter, its title, its level and how many came before with the same), shared by the contents
// (ReportContents.qml) and the preview that keeps its place across a new preview (ReportPage.qml).
function rowsOf(outline) {
    return (outline || []).filter(row => row.level <= 2 && row.page > 0)
}
function nodesOf(rows) {
    const nodes = [], occurrences = {}
    let chapter = null
    for (let i = 0; i < rows.length; ++i) {
        const row = rows[i]
        const parentKey = row.level === 2 && chapter ? chapter.key : ""
        const name = JSON.stringify([parentKey, row.title, row.level])
        occurrences[name] = (occurrences[name] || 0) + 1
        const node = {id: String(i), key: name + "/" + occurrences[name], parentKey: parentKey,
                      text: row.title, page: row.page, children: []}
        if (row.level === 2 && chapter) chapter.children.push(node)
        else { nodes.push(node); chapter = node }
    }
    return nodes
}
// every node in order, chapters and paragraphs
function flat(nodes) {
    let out = []
    for (const node of nodes) out = out.concat([node], flat(node.children || []))
    return out
}
