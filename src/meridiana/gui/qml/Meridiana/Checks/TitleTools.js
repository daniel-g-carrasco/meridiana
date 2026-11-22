.pragma library

// ui/title_tools.TitleTools.plan: full groups wrap; the tail stays beside Close.
function plan(width, indent, first, items, tail, gap, rowGap) {
    const firstRight = Math.max(0, width - tail - gap)
    let rows = [[]], x = indent
    for (const item of items) {
        let right = rows.length === 1 ? firstRight : width
        if (x + item.preferred > right && (rows[rows.length-1].length || rows.length === 1)) {
            rows.push([]); x = 0; right = width
        }
        const size = x + item.preferred <= right ? item.preferred : Math.max(item.minimum, right - x)
        rows[rows.length-1].push({item: item, width: size})
        x += size + gap
    }
    let rectangles = {}, y = 0
    for (let i = 0; i < rows.length; i++) {
        let height = i === 0 ? first : 0
        for (const entry of rows[i]) height = Math.max(height, entry.item.height)
        const right = i === 0 ? firstRight : width
        x = i === 0 ? indent : 0
        for (const entry of rows[i]) {
            const item = entry.item
            const left = item.align === "end" ? Math.max(x, right - entry.width) : x
            rectangles[item.key] = {x: left, y: y + Math.floor((height-item.height)/2), width: entry.width}
            x = left + entry.width + gap
        }
        if (i === 0) rectangles.copy = {x: width-tail, y: Math.floor((height-tail)/2), width: tail}
        y += height + rowGap
    }
    return {rectangles: rectangles, height: y-rowGap}
}
