// The report of Meridiana, sketch V1 «Cornice» of study 24 (docs/studio/24-relazione): the look and nothing else.
// What it says comes from data.json, written by report_typst/compose.py: every text there is a JSON string, shown as
// text and never read as markup, so a name with #, $, * or [ prints as it is. This file evaluates no string.
// Files are read only from the root of the compilation, a temporary folder (report_typst/engine.py).

#let D = json("data.json")
#let T = D.texts

// the palette of the sketch; the accent comes from the signing profile
#let accent = rgb(D.accent)
#let colours = (
  acc: accent, sun: rgb("#e8a317"), leaf: rgb("#2e8b57"), slate: rgb("#2b3440"), red: rgb("#d9534f"),
  ok: rgb("#2e7d4f"), warn: rgb("#b7791f"), fail: rgb("#c0392b"), info: rgb("#2a7fc4"), grey: rgb("#9aa2ab"),
)
#let ink = rgb("#1a1a1a")
#let txt2 = rgb("#58616c")
#let faint = rgb("#7d8792")
#let card = rgb("#f3f3f0")
#let rule-colour = rgb("#d4d4ce")
#let radius-card = 8pt
#let radius-table = 5pt

#let shown(name) = name != none and name != "" and name not in D.missing

#set document(title: D.doc.title, author: D.doc.author)
#set text(font: ("Titillium Web", "Inter"), size: 9.5pt, lang: D.lang, fill: ink, hyphenate: false)
#set par(justify: false, leading: 0.52em, spacing: 0.75em)
#set block(spacing: 0.9em)

// page numbers: the attachments' pages come between the report's, in the PDF as merged (ui/report.py)
#let attachments-before(p) = {
  query(<meridiana-attachment>).filter(m => m.location().page() < p).map(m => m.value.pages).sum(default: 0)
}
#let shown-page(p) = p + attachments-before(p)
#let total-pages() = counter(page).final().first() + D.attachments.map(a => a.pages).sum(default: 0)

// the marks of the results, drawn: no font is asked for them
#let mark(level, size: 8.2pt) = {
  let c = colours.at(level, default: colours.info)
  let s = size
  let w = (paint: white, thickness: s * 0.14, cap: "round", join: "round")
  box(width: s, height: s, baseline: 12%, {
    if level == "warn" {
      place(polygon(fill: c, stroke: (paint: c, thickness: s * 0.1, join: "round"),
        (s * 0.5, s * 0.06), (s * 0.97, s * 0.92), (s * 0.03, s * 0.92)))
      place(line(start: (s * 0.5, s * 0.36), end: (s * 0.5, s * 0.62), stroke: w))
      place(dx: s * 0.5 - s * 0.05, dy: s * 0.72, circle(radius: s * 0.05, fill: white))
    } else {
      place(circle(radius: s * 0.5, fill: c))
      if level == "ok" {
        place(curve(stroke: w, curve.move((s * 0.27, s * 0.52)), curve.line((s * 0.44, s * 0.68)),
          curve.line((s * 0.73, s * 0.34))))
      } else if level == "fail" {
        place(line(start: (s * 0.32, s * 0.32), end: (s * 0.68, s * 0.68), stroke: w))
        place(line(start: (s * 0.68, s * 0.32), end: (s * 0.32, s * 0.68), stroke: w))
      } else {
        place(line(start: (s * 0.5, s * 0.44), end: (s * 0.5, s * 0.74), stroke: w))
        place(dx: s * 0.5 - s * 0.05, dy: s * 0.22, circle(radius: s * 0.05, fill: white))
      }
    }
  })
}

// an image no wider than the room it has
#let fitted(name) = layout(size => context {
  let natural = measure(image(name))
  if natural.width > size.width { image(name, width: size.width) } else { image(name) }
})

// a piece of text: a string, or a run (bold, muted, mark, formula), or a list of them
#let inline(c) = {
  if c == none { [] }
  else if type(c) == str { c }
  else if type(c) == array { c.map(inline).join() }
  else if "b" in c { text(weight: 600, c.b) }
  else if "bb" in c { text(weight: 700, c.bb) }
  else if "m" in c { text(fill: txt2, c.m) }
  else if "mark" in c { mark(c.mark) }
  else if "formula" in c { if shown(c.formula) { box(baseline: 20%, fitted(c.formula)) } }
  else { [] }
}

// the head of a page: the logo in the corner when there is one (the rest closes up when not), what and for whom, the
// revision and the date on the right, the sketch's thin rule under them
#let logo-box(height: 11.5mm, room: 44mm) = context {
  let size = measure(image(D.doc.logo))
  let w = size.width / size.height * height
  if w > room { image(D.doc.logo, width: room) } else { image(D.doc.logo, height: height) }
}
#let page-header = context {
  let p = here().page()
  let chapters = query(<meridiana-chapter>).filter(m => {
    let at = m.location()
    at.page() < p or (at.page() == p and at.position().y < 50mm)
  })
  let title = if p == 1 and D.cover != none { T.report } else { D.doc.head_title }
  let sub = D.doc.head_sub
  let sub = if chapters.len() > 0 and not (p == 1 and D.cover != none) {
    sub + (if sub != "" { " · " } else { "" }) + chapters.last().value.title
  } else { sub }
  let middle = stack(spacing: 2.4pt,
    text(8.6pt, weight: 700, title),
    text(7.2pt, fill: txt2, sub))
  let right-side = align(right, stack(spacing: 2.4pt,
    text(7.8pt, weight: 600, D.doc.revision),
    text(7.2pt, fill: txt2, D.doc.date)))
  let has-logo = D.doc.logo != none and shown(D.doc.logo)
  block(width: 100%, inset: (bottom: 5pt), stroke: (bottom: 1.1pt + accent), breakable: false,
    grid(columns: if has-logo { (auto, 1fr, auto) } else { (1fr, auto) }, column-gutter: 8pt, align: horizon,
      ..(if has-logo { (logo-box(),) } else { () }), middle, right-side))
}
#let page-footer = context {
  let p = here().page()
  set text(7.2pt, fill: txt2)
  block(width: 100%, inset: (top: 5pt), stroke: (top: 0.6pt + rule-colour), breakable: false,
    grid(columns: (1fr, auto, 1fr), column-gutter: 8pt,
      stack(spacing: 2.2pt, text(fill: ink, weight: 600, D.doc.foot_left), D.doc.foot_left2),
      align(center, stack(spacing: 2.2pt, D.doc.foot_centre, D.doc.foot_centre2)),
      align(right, stack(spacing: 2.2pt,
        T.page_of.replace("{n}", str(shown-page(p))).replace("{total}", str(total-pages())),
        D.doc.foot_right2))))
}

#set page(paper: "a4", margin: (x: 15mm, top: 26mm, bottom: 19mm), header-ascent: 3.5mm, footer-descent: 3mm,
  header: page-header, footer: page-footer)

// the headings: chapters, sections with their coloured square, the small ones
#show heading: it => it.body
#show heading.where(level: 1): it => block(above: 15pt, below: 8pt, sticky: true, width: 100%, breakable: false,
  text(15.5pt, weight: 700, it.body))
#show heading.where(level: 2): it => block(above: 12pt, below: 6pt, sticky: true, breakable: false,
  text(10.8pt, weight: 700, it.body))
#show heading.where(level: 3): it => block(above: 10pt, below: 4.5pt, sticky: true, breakable: false,
  text(9.5pt, weight: 700, it.body))
#show heading.where(level: 4): it => block(above: 8pt, below: 3.5pt, sticky: true, breakable: false,
  text(8.8pt, weight: 600, fill: txt2, it.body))

#let square-of(c) = box(baseline: 0.6pt, rect(width: 7pt, height: 7pt, radius: 2pt, fill: colours.at(c, default: colours.slate)))

// the four numbers: rounded tiles with a coloured edge on top, all as tall as the tallest
#let tile-inside(t) = block(width: 100%, radius: radius-card, clip: true, fill: card, breakable: false, stack(
  rect(width: 100%, height: 3.4pt, fill: colours.at(t.c, default: colours.slate)),
  pad(x: 8pt, top: 7pt, bottom: 7pt, {
    set par(leading: 0.4em)
    stack(spacing: 5pt,
      box[#text(19pt, weight: 700, t.n)#if t.u != "" { h(2pt); text(8.5pt, weight: 600, fill: txt2, t.u) }],
      text(6.8pt, weight: 600, fill: txt2, tracking: 0.05em, upper(t.l)),
      ..(if t.s != "" { (text(6.6pt, fill: faint, t.s),) } else { () }))
  })))
#let tiles(b) = layout(size => {
  let gap = 2.2mm
  let n = b.items.len()
  let w = (size.width - gap * (n - 1)) / n
  let inside(t) = block(width: w, radius: radius-card, clip: true, fill: card, breakable: false,
    tile-inside(t))
  let h = calc.max(..b.items.map(t => measure(inside(t)).height))
  grid(columns: (w,) * n, column-gutter: gap,
    ..b.items.map(t => block(width: w, height: h, radius: radius-card, clip: true, fill: card, tile-inside(t))))
})

// a table: outer corners rounded, a line between the rows and one between the columns, the head again on every page,
// a row never split between two pages
#let hair = 0.45pt + rule-colour
#let on-dark = 0.45pt + rgb("#59616d")
#let data-table(b) = {
  let n = b.widths.len()
  let columns = if b.source { b.widths.slice(0, n - 1).map(w => w * 1fr) + (15mm,) } else { b.widths.map(w => w * 1fr) }
  let has-head = b.head != none
  let cell-style(c, i, result) = {
    let body = inline(c)
    let body = if result { text(weight: 700, body) } else { body }
    if i == n - 1 and b.source { text(6.6pt, font: "Inter", fill: faint, body) } else { body }
  }
  let cells = ()
  if has-head {
    cells.push(table.header(..b.head.enumerate().map(((i, h)) => table.cell(fill: colours.slate,
      align: (if i in b.right { right } else { left }) + bottom,
      text(7.6pt, weight: 600, fill: white, inline(h))))))
  }
  for (r, row) in b.rows.enumerate() {
    if type(row) == dictionary {
      let group = table.cell(colspan: n, fill: card, text(weight: 700, inline(row.group)))
      cells.push(table.header(level: 2, group))
    } else {
      let result = r == b.result
      for (i, c) in row.enumerate() {
        cells.push(table.cell(fill: if result { card } else { none }, cell-style(c, i, result)))
      }
    }
  }
  set table.cell(breakable: false)
  set text(8.3pt)
  set par(leading: 0.42em)
  block(width: 100%, radius: radius-table, clip: true, stroke: 0.6pt + rule-colour, breakable: true, above: 5pt, below: 7pt,
    table(columns: columns, inset: (x: 4.2pt, y: 3.1pt),
      align: (x, y) => (if x in b.right { right } else { left }) + top,
      stroke: (x, y) => {
        let dark = has-head and y == 0
        (left: if x > 0 { if dark { on-dark } else { hair } } else { none },
         top: if y > 0 { if dark { on-dark } else { hair } } else { none })
      },
      ..cells))
}

// label and value in a rounded box: a filled card with a line between the rows and one between the columns; the code
// of the register in a third column when the report has the register
#let facts(b) = {
  let with-source = b.rows.any(r => r.len() > 2)
  let cells = ()
  for row in b.rows {
    let value = if type(row.at(1)) == str and row.at(1).len() > 44 { left } else { right }
    cells.push(text(fill: txt2, inline(row.at(0))))
    cells.push(table.cell(align: value, if b.strong { text(weight: 600, inline(row.at(1))) } else { inline(row.at(1)) }))
    if with-source {
      cells.push(table.cell(align: right + horizon, text(6.6pt, font: "Inter", fill: faint, inline(row.at(2)))))
    }
  }
  block(width: 100%, radius: radius-card, fill: card, inset: (x: 5pt, y: 2.2pt), breakable: false, above: 5pt, below: 7pt, {
    set table.cell(breakable: false)
    set text(8.4pt)
    set par(leading: 0.42em)
    table(columns: if with-source { (b.ratio.at(0) * 1fr, b.ratio.at(1) * 1fr, auto) }
                   else { (b.ratio.at(0) * 1fr, b.ratio.at(1) * 1fr) },
      inset: (x: 3.4pt, y: 2.9pt),
      stroke: (x, y) => (left: if x > 0 { hair } else { none }, top: if y > 0 { hair } else { none }),
      ..cells)
  })
}

#let chips(items) = block(above: 5pt, below: 3pt, breakable: false, {
  set text(7.4pt)
  for c in items {
    box(fill: card, radius: 8pt, inset: (x: 5pt, y: 2.6pt), outset: (y: 0pt), {
      if "fill" in c {
        box(baseline: 0.5pt, rect(width: 6.5pt, height: 6.5pt, radius: 1.5pt,
          fill: rgb(c.fill), stroke: if c.at("edge", default: none) != none { (paint: rgb(c.edge), thickness: 0.6pt,
          dash: if c.at("dash", default: false) { "densely-dashed" } else { "solid" }) } else { none }))
        h(3pt)
      }
      c.t
    })
    h(3pt)
  }
})

// the image of a figure in its rounded frame, as tall as the picture wants within `max`; the frame fills what the page
// leaves when `fill` is set (the closed page of the summary)
#let framed(b, width: 100%) = layout(size => context {
  let natural = measure(image(b.image))
  let w = size.width
  let ratio = natural.height / natural.width
  let top = if b.at("max_h", default: none) != none { b.max_h * 1mm } else { 120mm }
  let h = calc.min(w * ratio, top)
  block(width: w, height: h, radius: 10pt, clip: true, breakable: false,
    fill: if b.at("tint", default: false) { card } else { white },
    stroke: if b.at("tint", default: false) { none } else { 0.6pt + rule-colour },
    inset: b.at("inset", default: 0) * 1mm,
    align(center + horizon, image(b.image, width: 100%, height: 100%, fit: "contain")))
})
#let caption(c) = block(above: 4pt, below: 7pt, {
  set par(leading: 0.42em)
  text(7.4pt, fill: txt2, inline(c))
})

#let figure-block(b) = {
  if shown(b.image) {
    block(above: 5pt, below: 7pt, breakable: false, {
      framed(b)
      if b.at("chips", default: none) != none { chips(b.chips) }
      if b.at("caption", default: none) != none { caption(b.caption) }
    })
  }
}

// a filling figure: the rest of the page, for the closed page of the summary
#let fill-figure(b) = if shown(b.image) {
  block(width: 100%, height: 1fr, above: 6pt, below: 4pt, radius: 10pt, clip: true, stroke: 0.6pt + rule-colour, fill: white,
    align(center + horizon, image(b.image, width: 100%, height: 100%, fit: "contain")))
  if b.at("caption", default: none) != none { caption(b.caption) }
}

// charts drawn here in the document's style: full bars with rounded tops, their values on them, no axes
#let bar-top = (top-left: 1.8pt, top-right: 1.8pt)
#let bars(b) = block(above: 6pt, below: 5pt, breakable: false, width: 100%, {
  let h = b.h * 1mm
  let many = b.series.len()
  let top = calc.max(..b.series.map(s => calc.max(..s.values)), 1e-9)
  if many > 1 { chips(b.series.map(s => (t: s.name, fill: if s.color in colours { colours.at(s.color).to-hex() } else { s.color }))) }
  let colour(s) = colours.at(s.color, default: rgb("#999999"))
  let bar-column(i) = {
    let group = b.series.map(s => {
      let v = s.values.at(i)
      let bar = rect(width: 100%, height: calc.max(v / top, 0.002) * h, radius: bar-top, fill: colour(s))
      if s.at("texts", default: none) != none {
        stack(spacing: 1.5pt, align(center, text(6.1pt, fill: txt2, s.texts.at(i))), bar)
      } else { bar }
    })
    grid(columns: (1fr,) * many, column-gutter: 0.6pt, align: bottom, ..group)
  }
  grid(columns: (1fr,) * b.labels.len(), column-gutter: if many > 1 { 2.4pt } else { 1.6pt }, row-gutter: 0pt, align: bottom,
    ..range(b.labels.len()).map(bar-column))
  line(length: 100%, stroke: 0.6pt + rgb("#c9c9c4"))
  v(-0.55em)
  grid(columns: (1fr,) * b.labels.len(), column-gutter: if many > 1 { 2.4pt } else { 1.6pt },
    ..b.labels.map(l => align(center, text(6.8pt, fill: txt2, l))))
})

#let waterfall(b) = block(above: 8pt, below: 5pt, breakable: false, width: 100%, {
  let h = b.h * 1mm
  let colour(t) = if t == "total" { colours.sun } else if t == "gain" { colours.leaf } else if t == "zero" { colours.grey } else { colours.red }
  grid(columns: (1fr,) * b.items.len(), column-gutter: 3pt, align: bottom,
    ..b.items.map(i => stack(spacing: 1.5pt,
      align(center, text(6.3pt, weight: 600, i.text)),
      ..(if i.at("extra", default: "") != "" { (align(center, text(6pt, fill: colours.leaf.darken(20%), weight: 600, i.extra)),) } else { () }),
      rect(width: 100%, height: calc.max(i.h, 0.012) * h, radius: bar-top, fill: colour(i.t)))))
  line(length: 100%, stroke: 0.6pt + rgb("#c9c9c4"))
  v(-0.55em)
  set par(leading: 0.3em)
  grid(columns: (1fr,) * b.items.len(), column-gutter: 3pt,
    ..b.items.map(i => align(center, text(5.9pt, fill: txt2, i.label))))
})

// what a month's bars cannot say: the line of what is used on site over the produced and consumed bars
#let balance(b) = block(above: 6pt, below: 5pt, breakable: false, width: 100%, {
  let h = b.h * 1mm
  chips((
    (t: b.names.at(0), fill: colours.sun.to-hex()),
    (t: b.names.at(1), fill: colours.slate.to-hex()),
    (t: b.names.at(2), fill: colours.leaf.to-hex()),
  ))
  layout(size => {
    let n = b.labels.len()
    let w = size.width / n
    let pad-x = 0.14 * w
    let bw = (w - 2 * pad-x) / 2
    box(width: size.width, height: h, {
      for i in range(n) {
        let x = i * w + pad-x
        let p = b.first.at(i) * h
        let c = b.second.at(i) * h
        place(dx: x, dy: h - p, rect(width: bw, height: p, radius: bar-top, fill: colours.sun))
        place(dx: x + bw, dy: h - c, rect(width: bw, height: c, radius: bar-top, fill: colours.slate))
      }
      let points = range(n).map(i => ((i + 0.5) * w, h - b.line.at(i) * h))
      place(curve(stroke: (paint: colours.leaf, thickness: 1.3pt, join: "round"),
        curve.move(points.at(0)), ..points.slice(1).map(p => curve.line(p))))
      for pt in points {
        place(dx: pt.at(0) - 1.6pt, dy: pt.at(1) - 1.6pt, circle(radius: 1.6pt, fill: colours.leaf, stroke: 0.5pt + white))
      }
    })
    v(-0.55em)
    line(length: 100%, stroke: 0.6pt + rgb("#c9c9c4"))
    v(-0.55em)
    grid(columns: (1fr,) * n, ..b.labels.map(l => align(center, text(6.8pt, fill: txt2, l))))
  })
})

#let cash(b) = block(above: 6pt, below: 5pt, breakable: false, width: 100%, {
  let h = b.h * 1mm
  layout(size => {
    let w = size.width - 16mm
    let at(p) = (16mm + p.at(0) * w, h - p.at(1) * h)
    let zero = h - b.zero * h
    box(width: size.width, height: h, {
      let pts = b.points.map(at)
      let first-x = pts.first().at(0)
      let last-x = pts.last().at(0)
      place(curve(fill: accent.transparentize(84%), stroke: none,
        curve.move((first-x, zero)), ..pts.map(p => curve.line(p)), curve.line((last-x, zero)), curve.close()))
      place(line(start: (16mm, zero), end: (size.width, zero), stroke: 0.6pt + rgb("#9a9a94")))
      place(curve(stroke: (paint: accent, thickness: 1.5pt, join: "round"),
        curve.move(pts.at(0)), ..pts.slice(1).map(p => curve.line(p))))
      for t in b.y {
        place(dy: h - t.at("at") * h - 3.5pt, box(width: 14.5mm, align(right, text(6.6pt, fill: txt2, t.t))))
      }
      for t in b.x {
        place(dx: 16mm + t.at("at") * w - 5mm, dy: h + 1.5pt, box(width: 10mm, align(center, text(6.6pt, fill: txt2, t.t))))
      }
    })
    v(7pt)
  })
})

#let carpet(b) = block(above: 6pt, below: 5pt, breakable: false, width: 100%, {
  let h = b.h * 1mm
  layout(size => {
    let w = size.width - 26mm
    box(width: size.width, height: h + 9pt, {
      place(dx: 7mm, block(width: w, height: h, radius: 4pt, clip: true,
        image(b.image, width: w, height: h, fit: "stretch", scaling: "pixelated")))
      for t in b.hours {
        place(dy: h - t.at("at") * h - 3.5pt, box(width: 5.6mm, align(right, text(6.5pt, fill: txt2, t.t))))
      }
      for t in b.months {
        place(dx: 7mm + t.at("at") * w, dy: h + 1.5pt, text(6.5pt, fill: txt2, t.t))
      }
      // the scale of the colours
      place(dx: size.width - 14mm, block(width: 3mm, height: h, radius: 2pt,
        fill: gradient.linear(white, accent, angle: -90deg), stroke: 0.4pt + rule-colour))
      place(dx: size.width - 10mm, text(6.5pt, fill: txt2, b.top))
      place(dx: size.width - 10mm, dy: h - 8pt, text(6.5pt, fill: txt2, "0 " + b.unit))
    })
  })
})

#let badge(b) = block(above: 4pt, below: 5pt, breakable: false,
  box(fill: colours.at(b.level).lighten(84%), radius: 12pt, inset: (x: 7pt, y: 4.2pt), {
    box(baseline: 15%, mark(b.level, size: 10.5pt))
    h(4pt)
    text(8.6pt, weight: 600, fill: colours.at(b.level).darken(30%), b.t)
  }))

#let bullets(b) = block(above: 4pt, below: 7pt, {
  set text(8.8pt)
  list(tight: true, marker: text(fill: accent, "•"), indent: 2pt, ..b.items.map(i => inline(i)))
})

// the blocks of a chapter
#let render(b) = {
  let k = b.k
  if k == "chapter" {
    if b.at("break", default: false) { pagebreak(weak: true) }
    [#metadata((title: b.title, id: b.id)) <meridiana-chapter>]
    heading(level: 1, outlined: true, bookmarked: true, b.title)
  } else if k == "section" {
    heading(level: 2, bookmarked: true, [#square-of(b.c) #h(2.5pt) #b.t])
  } else if k == "sub" {
    heading(level: b.at("level", default: 3), bookmarked: false, inline(b.t))
  } else if k == "p" {
    let style = b.at("style", default: "")
    if style == "caption" { caption(b.t) }
    else if style == "muted" { block(above: 4pt, below: 6pt, text(8.6pt, fill: txt2, inline(b.t))) }
    else if style == "source" { block(above: 3pt, below: 7pt, text(6.8pt, fill: faint, inline(b.t))) }
    else if style == "lead" { block(above: 4pt, below: 7pt, text(10pt, inline(b.t))) }
    else { par(inline(b.t)) }
  } else if k == "tiles" { tiles(b); v(2pt) }
  else if k == "facts" { facts(b) }
  else if k == "table" { data-table(b) }
  else if k == "two" {
    let ratio = b.at("ratio", default: (1, 1))
    grid(columns: ratio.map(r => r * 1fr), column-gutter: 5mm, align: top,
      block(breakable: false, { for x in b.left { render(x) } }), block(breakable: false, { for x in b.right { render(x) } }))
  }
  else if k == "keep" { block(breakable: false, { for x in b.items { render(x) } }) }
  else if k == "float" { place(auto, float: true, clearance: 5mm, align(left, block(width: 100%, breakable: false, { for x in b.items { render(x) } }))) }
  else if k == "figure" { figure-block(b) }
  else if k == "fill_figure" { fill-figure(b) }
  else if k == "chips" { chips(b.items) }
  else if k == "bars" { bars(b) }
  else if k == "waterfall" { waterfall(b) }
  else if k == "balance" { balance(b) }
  else if k == "cash" { cash(b) }
  else if k == "carpet" { carpet(b) }
  else if k == "badge" { badge(b) }
  else if k == "list" { bullets(b) }
  else if k == "formula" {
    if shown(b.image) { block(above: 5pt, below: 6pt, breakable: false, fitted(b.image)) }
  }
  else if k == "pagebreak" { pagebreak(weak: true) }
  else if k == "attachment" {
    pagebreak(weak: true)
    context [#metadata((k: b.n, pages: b.pages, page: here().page())) <meridiana-attachment>]
    [#metadata((title: b.title, id: b.id)) <meridiana-chapter>]
    v(55mm)
    block(width: 100%, radius: 12pt, fill: card, inset: 9mm, breakable: false, {
      text(7.4pt, weight: 600, fill: accent, tracking: 0.1em, upper(T.attachment))
      heading(level: 1, bookmarked: true, b.title)
      { for x in b.items { render(x) } }
    })
  }
}

#let render-all(items) = { for b in items { render(b) } }

// the contents, with the pages of the PDF as merged
#let contents(columns) = context {
  let found = query(<meridiana-chapter>)
  let cell(m) = link(m.location(), grid(columns: (1fr, auto), column-gutter: 4pt,
    text(8.2pt, m.value.title),
    text(8.2pt, weight: 600, str(shown-page(m.location().page())))))
  block(width: 100%, radius: radius-card, fill: card, inset: (x: 8pt, y: 6pt), breakable: false, {
    text(7pt, weight: 600, fill: txt2, tracking: 0.08em, upper(T.contents))
    v(2pt, weak: true)
    let n = found.len()
    let half = calc.ceil(n / columns)
    let lists = range(columns).map(c => found.slice(calc.min(c * half, n), calc.min((c + 1) * half, n)))
    grid(columns: (1fr,) * columns, column-gutter: 7mm,
      ..lists.map(l => stack(spacing: 3.6pt, ..l.map(cell))))
  })
}

// the cover: the picture in its frame, the title, the four numbers, who and what, the contents
#let cover-page(c) = {
  if shown(c.image) {
    block(above: 0pt, below: 7mm, framed((image: c.image, max_h: c.max_h, tint: c.at("tint", default: false),
      inset: c.at("inset", default: 0))))
  }
  text(7.6pt, weight: 600, fill: accent, tracking: 0.14em, upper(c.kicker))
  v(3pt, weak: true)
  block(above: 4pt, below: 10pt, text(25pt, weight: 700, c.title))
  block(above: 0pt, below: 10pt, text(10.2pt, fill: txt2, c.sub))
  tiles((items: c.tiles))
  v(3mm)
  grid(columns: (1fr,) * c.meta.len(), column-gutter: 5mm,
    ..c.meta.map(m => {
      set par(leading: 0.42em)
      text(6.8pt, weight: 600, fill: txt2, tracking: 0.08em, upper(m.t))
      linebreak()
      set text(8.2pt)
      for (i, line) in m.lines.enumerate() { line; if i < m.lines.len() - 1 { linebreak() } }
    }))
  v(1fr)
  if D.toc == "cover" { contents(2) }
  v(2.5mm)
  text(6.8pt, fill: faint, c.made)
  pagebreak()
}

#let compact-head(c) = block(above: 0pt, below: 7pt, breakable: false, {
  text(7.6pt, weight: 600, fill: accent, tracking: 0.14em, upper(c.kicker))
  block(above: 4pt, below: 8pt, text(21pt, weight: 700, c.title))
  if c.sub != "" { block(above: 3pt, below: 3pt, text(9.6pt, fill: txt2, c.sub)) }
  if c.lines.len() > 0 {
    block(above: 4pt, below: 0pt, {
      set text(8pt, fill: txt2)
      c.lines.join(" · ")
    })
  }
  if c.made != "" { block(above: 3pt, below: 0pt, text(6.8pt, fill: faint, c.made)) }
})

#if D.cover != none { cover-page(D.cover) }
#if D.toc == "page" {
  heading(level: 2, bookmarked: false, T.contents)
  contents(1)
  pagebreak()
}
#if D.head != none { compact-head(D.head) }
#render-all(D.body)
