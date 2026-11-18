// The look of Meridiana's report (R460, draft A5 of the study of 06/11/2026): square, thin rules, IBM Plex Sans Light,
// warm greys without blue. Everything it shows comes from data.json (compose.py), the values of the look from
// D.style (look.py, shared with the ODT and DOCX exports). No string of the data is ever evaluated as markup: the texts
// of the user are shown as text. The formulas are TeX composed by Typst (the mitex package, carried by the program and
// copied into the report's folder) in IBM Plex Math. Files are read only from the root of the compilation.

#import "mitex/lib.typ": mitex, mi, mitex-convert, mitex-scope

#let D = json("data.json")
#let T = D.texts
#let S = D.style
#let TEX = D.at("tex", default: (:))

#let accent = rgb(S.accent)
#let colours = {
  let c = (:)
  for (k, v) in S.colours { c.insert(k, rgb(v)) }
  c
}
#let ink = rgb(S.ink)
#let txt2 = rgb(S.txt2)
#let faint = rgb(S.faint)
#let tint = rgb(S.tint)
#let rule-colour = rgb(S.rule)
#let hair = 0.4pt + rule-colour
#let thin = 0.6pt + rule-colour
#let body-font = S.font.body
#let head-font = S.font.head
#let table-font = S.font.table
#let table-stretch = S.font.table_stretch * 1%
#let math-font = S.font.math
#let mono-font = S.font.mono
#let head-weight = S.font.head_weight
#let head-fill = rgb(S.head_fill)
#let grid-colour = rgb(S.grid)
// the vertical scale, in points: 6 pt is half a line of text
#let SP = S.spacing
#let sp(k) = SP.at(k) * 1pt
// the charts' colours: taupe and sand, the losses hatched, the lines anthracite
#let CH = S.chart
#let ch(k) = rgb(CH.at(k))
#let hatch(colour, bg) = {
  let s = CH.hatch * 1pt
  tiling(size: (s, s), {
    place(rect(width: s, height: s, fill: bg, stroke: none))
    place(line(start: (0pt, s), end: (s, 0pt), stroke: 0.5pt + colour))
  })
}
#let loss-fill() = hatch(ch("loss"), ch("loss_bg"))
#let line-width = CH.line_width * 1pt

#let shown(name) = name != none and name != "" and name not in D.missing

#set document(title: D.doc.title, author: D.doc.author)
#set text(font: (body-font, "IBM Plex Sans", "IBM Plex Math"), weight: S.font.weight, size: S.size * 1pt, lang: D.lang, fill: ink,
  hyphenate: S.hyphenate)
#set par(justify: S.justify, leading: 0.58em, spacing: sp("par"))
#set block(spacing: sp("par"))
#show math.equation: set text(font: math-font, weight: 400)

#let attachments-before(p) = {
  query(<meridiana-attachment>).filter(m => m.location().page() < p).map(m => m.value.pages).sum(default: 0)
}
#let shown-page(p) = p + attachments-before(p)
#let total-pages() = counter(page).final().first() + D.attachments.map(a => a.pages).sum(default: 0)

#let mark(level, size: 8.2pt) = {
  let svg = D.marks.at(level, default: D.marks.info).replace("@fill@", colours.at(level, default: colours.info).to-hex())
  box(width: size, height: size, baseline: 12%, image(bytes(svg), format: "svg", width: size))
}

#let fitted(name) = layout(size => context {
  let natural = measure(image(name))
  if natural.width > size.width { image(name, width: size.width) } else { image(name) }
})

// a symbol: from its TeX when there is one, else its image
#let symbol(c) = {
  let tex = TEX.at(c.formula, default: none)
  if tex != none { mi(tex) } else if shown(c.formula) { box(baseline: 20%, fitted(c.formula)) }
}

#let inline(c) = {
  if c == none { [] }
  else if type(c) == str { c }
  else if type(c) == array { c.map(inline).join() }
  else if "b" in c { text(weight: 600, c.b) }
  else if "bb" in c { text(weight: 700, c.bb) }
  else if "m" in c { text(fill: txt2, c.m) }
  else if "mark" in c { mark(c.mark) }
  else if "formula" in c { symbol(c) }
  else { [] }
}

// a number in two parts, the whole and the decimals with the unit: the digits aligned on the comma
#let num-parts(s) = {
  if type(s) != str { return none }
  let m = s.match(regex("^(-?[0-9][0-9.]*)(,[0-9]+)?( .*)?$"))
  if m == none { none } else {
    (int: m.captures.at(0),
     rest: (if m.captures.at(1) == none { "" } else { m.captures.at(1) }) + (if m.captures.at(2) == none { "" } else { m.captures.at(2) }))
  }
}
#let decimal-cell(c, share: 58%) = {
  let p = num-parts(c)
  if p == none { align(right, inline(c)) } else {
    box(width: share, align(right, p.int)) + box(width: 100% - share, align(left, p.rest))
  }
}

// the header and the footer: the logo on the left, the words on the right, the same thin rule
#let logo-box(height: 10mm, room: 40mm) = context {
  let size = measure(image(D.doc.logo))
  let w = size.width / size.height * height
  if w > room { image(D.doc.logo, width: room) } else { image(D.doc.logo, height: height) }
}
#let logo-placeholder(height: 9mm, width: 36mm) = box(width: width, height: height,
  stroke: (paint: rule-colour, thickness: 0.5pt, dash: "densely-dashed"),
  align(center + horizon, text(6.5pt, fill: faint, tracking: 0.12em, "LOGO")))
#let has-logo = D.doc.logo != none and shown(D.doc.logo)
#let page-header = context {
  set par(justify: false)
  set text(hyphenate: false)
  let p = here().page()
  let chapters = query(<meridiana-chapter>).filter(m => {
    let at = m.location()
    at.page() < p or (at.page() == p and (at.position().y < 50mm or m.value.id.starts-with("attachment")))
  })
  let short = D.doc.at("doc_short", default: T.report)
  let sub = D.doc.head_sub
  let sub = if chapters.len() > 0 { sub + (if sub != "" { " · " } else { "" }) + chapters.last().value.title } else { sub }
  let logo-side = if has-logo { logo-box() } else if D.doc.at("logo_placeholder", default: false) { logo-placeholder() } else { none }
  set text(font: head-font)
  block(width: 100%, inset: (bottom: 5pt), stroke: (bottom: S.hf_rule * 1pt + rgb(S.hf_colour)), breakable: false,
    grid(columns: (auto, 1fr), column-gutter: 8pt, align: (left + bottom, right + bottom),
      logo-side,
      align(right, stack(spacing: 2.4pt,
        text(8pt, weight: 600, short + " · " + D.doc.head_title),
        text(7pt, fill: txt2, sub),
        text(7pt, fill: txt2, D.doc.revision + (if D.doc.revision != "" { " · " } else { "" }) + D.doc.date)))))
}
#let page-footer = context {
  set par(justify: false)
  set text(hyphenate: false)
  let p = here().page()
  set text(7pt, fill: txt2, font: head-font)
  block(width: 100%, inset: (top: 5pt), stroke: (top: S.hf_rule * 1pt + rgb(S.hf_colour)), breakable: false,
    grid(columns: (1fr, auto, 1fr), column-gutter: 8pt,
      stack(spacing: 2.2pt, text(fill: ink, weight: 600, D.doc.foot_left), D.doc.foot_left2),
      align(center, stack(spacing: 2.2pt, D.doc.foot_centre, D.doc.foot_centre2)),
      align(right, stack(spacing: 2.2pt,
        T.page_of.replace("{n}", str(shown-page(p))).replace("{total}", str(total-pages())),
        D.doc.foot_right2))))
}

#set page(paper: "a4", margin: (left: S.margin_left * 1mm, right: 16mm, top: 25mm, bottom: 19mm),
  header-ascent: 4mm, footer-descent: 3mm, header: page-header, footer: page-footer)

// the headings: chapters and sections numbered by Typst (1, 1.1), the sub-headings not; never hyphenated
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  let num = if it.numbering != none { counter(heading).display(it.numbering) } else { none }
  set text(font: head-font, weight: head-weight, hyphenate: false)
  set par(justify: false)
  block(above: sp("h1a"), below: sp("h1b"), sticky: true, width: 100%, breakable: false,
    text(17pt, if num != none { num + h(0.55em) } + it.body))
}
#show heading.where(level: 2): it => {
  let num = if it.numbering != none { counter(heading).display(it.numbering) } else { none }
  set text(font: head-font, weight: head-weight, hyphenate: false)
  set par(justify: false)
  block(above: sp("h2a"), below: sp("h2b"), sticky: true, breakable: false,
    text(11pt, if num != none { text(fill: accent, num) + h(0.55em) } + it.body))
}
#show heading.where(level: 3): it => block(above: sp("h3a"), below: sp("h3b"), sticky: true, breakable: false, {
  set text(hyphenate: false)
  set par(justify: false)
  text(9.6pt, font: head-font, weight: 600, it.body)
})
#show heading.where(level: 4): it => block(above: sp("h4a"), below: sp("h4b"), sticky: true, breakable: false, {
  set text(hyphenate: false)
  set par(justify: false)
  text(8.8pt, font: head-font, weight: 600, fill: txt2, it.body)
})

// the results in boxes: cells of a grid with a thin rule, a rule in the result's colour on top, the number large
#let dash(b) = block(width: 100%, above: sp("dasha"), below: sp("dashb"), breakable: false, {
  let n = b.items.len()
  let cols = calc.max(1, calc.min(n, b.at("cols", default: 4)))
  set par(leading: 0.4em, justify: false)
  set text(hyphenate: false)
  grid(columns: (1fr,) * cols, column-gutter: 3mm, row-gutter: 3mm,
    ..b.items.map(t => grid.cell(
      stroke: (top: 2pt + colours.at(t.c, default: colours.slate), left: hair, right: hair, bottom: hair),
      inset: (x: 7pt, top: 7pt, bottom: 6pt),
      stack(spacing: 4.5pt,
        text(6.6pt, weight: 600, fill: txt2, tracking: 0.06em, font: head-font, upper(t.l)),
        box[#text(19pt, weight: 300, font: head-font, t.n)#if t.u != "" { h(2.5pt); text(8pt, weight: 500, fill: txt2, t.u) }],
        ..(if t.at("s", default: "") != "" { (text(6.8pt, fill: faint, t.s),) } else { () })))))
})

// the tables, «grid»: rules across and down in a light grey, the head on a grey ground, the numbers on the comma
#let grid-stroke = 0.4pt + grid-colour
#let head-text(h) = text(7.8pt, weight: 600, fill: rgb("#3a3a37"), h)
#let data-table(b) = {
  let n = b.widths.len()
  let columns = if b.source { b.widths.slice(0, n - 1).map(w => w * 1fr) + (15mm,) } else { b.widths.map(w => w * 1fr) }
  let has-head = b.head != none
  let decimal-col = range(n).map(i => i in b.right
    and b.rows.any(r => type(r) == array and r.len() > i and type(r.at(i)) == str and r.at(i).contains(",")))
  let cell-style(c, i, result) = {
    let body = if decimal-col.at(i) and type(c) == str { decimal-cell(c) } else { inline(c) }
    let body = if result { text(weight: 600, body) } else { body }
    if i == n - 1 and b.source { text(6.6pt, font: mono-font, fill: faint, inline(c)) } else { body }
  }
  let cells = ()
  if has-head {
    cells.push(table.header(..b.head.enumerate().map(((i, h)) => table.cell(
      align: (if i in b.right { right } else { left }) + bottom, fill: head-fill,
      head-text(inline(h))))))
  }
  for (r, row) in b.rows.enumerate() {
    if type(row) == dictionary {
      cells.push(table.header(level: 2, table.cell(colspan: n, fill: tint, text(weight: 600, inline(row.group)))))
    } else {
      let result = r == b.result
      for (i, c) in row.enumerate() {
        cells.push(table.cell(fill: if result { tint } else { none }, cell-style(c, i, result)))
      }
    }
  }
  set table.cell(breakable: false)
  set text(font: table-font, stretch: table-stretch, size: S.table_size * 1pt, weight: 400)
  set par(leading: 0.42em, justify: false)
  block(width: 100%, breakable: true, above: sp("taba"), below: sp("tabb"),
    table(columns: columns, inset: (x: 4pt, y: S.table_pad * 1pt),
      align: (x, y) => (if x in b.right { right } else { left }) + top,
      stroke: grid-stroke, ..cells))
}

#let facts(b) = {
  let with-source = b.rows.any(r => r.len() > 2)
  let cells = ()
  for row in b.rows {
    let value = if type(row.at(1)) == str and row.at(1).len() > 44 { left } else { right }
    cells.push(text(fill: txt2, inline(row.at(0))))
    cells.push(table.cell(align: value, if b.strong { text(weight: 600, inline(row.at(1))) } else { inline(row.at(1)) }))
    if with-source {
      cells.push(table.cell(align: right + horizon, text(6.6pt, font: mono-font, fill: faint, inline(row.at(2)))))
    }
  }
  block(width: 100%, breakable: false, above: sp("taba"), below: sp("tabb"), {
    set table.cell(breakable: false)
    set text(font: table-font, stretch: table-stretch, size: 8.5pt)
    set par(leading: 0.42em, justify: false)
    table(columns: if with-source { (b.ratio.at(0) * 1fr, b.ratio.at(1) * 1fr, auto) }
                   else { (b.ratio.at(0) * 1fr, b.ratio.at(1) * 1fr) },
      inset: (x: 3.6pt, y: 3.4pt), stroke: grid-stroke, ..cells)
  })
}

#let chips(items) = block(above: 5pt, below: 4pt, breakable: false, {
  set text(7.4pt, font: table-font)
  set par(justify: false)
  for c in items {
    box(stroke: hair, inset: (x: 5pt, y: 2.6pt), {
      if "fill" in c {
        let fill = if c.at("hatch", default: false) { loss-fill() } else { rgb(c.fill) }
        box(baseline: 0.5pt, rect(width: 6pt, height: 6pt, fill: fill,
          stroke: if c.at("edge", default: none) != none { (paint: rgb(c.edge), thickness: 0.6pt,
          dash: if c.at("dash", default: false) { "densely-dashed" } else { "solid" }) } else { none }))
        h(3pt)
      }
      c.t
    })
    h(3pt)
  }
})

// the figures: a thin frame for the drawings, none for the 3D views
#let is-view(name) = type(name) == str and name.starts-with("view_")
#let framed(b) = layout(size => context {
  let natural = measure(image(b.image))
  let w = size.width
  let ratio = natural.height / natural.width
  let top = if b.at("max_h", default: none) != none { b.max_h * 1mm } else { 120mm }
  let h = calc.min(w * ratio, top)
  block(width: w, height: h, breakable: false,
    fill: if b.at("tint", default: false) { tint } else { white },
    stroke: if is-view(b.image) { none } else { thin },
    inset: b.at("inset", default: 0) * 1mm,
    align(center + horizon, image(b.image, width: 100%, height: 100%, fit: "contain")))
})
#let caption-text(c) = { set par(leading: 0.42em, justify: false); text(7.6pt, fill: txt2, inline(c)) }
#let caption(c) = block(above: sp("capa"), below: sp("capb"), caption-text(c))
#let figure-block(b) = {
  if shown(b.image) {
    block(above: sp("figa"), below: sp("figb"), breakable: false, {
      framed(b)
      if b.at("chips", default: none) != none { chips(b.chips) }
      if b.at("caption", default: none) != none { block(above: sp("capa"), below: 0pt, caption-text(b.caption)) }
    })
  }
}
#let fill-figure(b) = if shown(b.image) {
  block(width: 100%, height: 1fr, above: sp("figa"), below: 4pt, stroke: if is-view(b.image) { none } else { thin },
    fill: white, align(center + horizon, image(b.image, width: 100%, height: 100%, fit: "contain")))
  if b.at("caption", default: none) != none { caption(b.caption) }
}

// the charts: flat, square, a light grid behind the bars
#let series-colour(s) = if s.color == "sun" { ch("calc") } else if s.color in ("slate", "acc") { ch("ref") } else if s.color in colours { colours.at(s.color) } else { rgb(s.color) }
#let grid-lines(h, n: 4) = { for k in range(1, n + 1) { place(dy: h - k * h / n, line(length: 100%, stroke: CH.grid_width * 1pt + ch("grid"))) } }
#let bars(b) = block(above: sp("figa"), below: sp("par"), breakable: false, width: 100%, {
  let h = b.h * 1mm
  let many = calc.max(1, b.series.len())
  let top = calc.max(..b.series.map(s => calc.max(0, ..s.values)), 1e-9)
  if b.series.len() > 1 { chips(b.series.map(s => (t: s.name, fill: series-colour(s).to-hex()))) }
  let bar-column(i) = {
    let group = b.series.map(s => {
      let v = s.values.at(i)
      let bar = rect(width: 100%, height: calc.max(v / top, 0.002) * h, fill: series-colour(s))
      if s.at("texts", default: none) != none {
        stack(spacing: 1.5pt, align(center, text(6.1pt, fill: txt2, font: table-font, s.texts.at(i))), bar)
      } else { bar }
    })
    grid(columns: (1fr,) * many, column-gutter: 0.6pt, align: bottom, ..group)
  }
  let n = calc.max(1, b.labels.len())
  box(width: 100%, {
    grid-lines(h)
    grid(columns: (1fr,) * n, column-gutter: if many > 1 { 2.4pt } else { 1.6pt }, row-gutter: 0pt, align: bottom,
      ..range(b.labels.len()).map(bar-column))
  })
  line(length: 100%, stroke: 0.6pt + ch("axis"))
  v(-0.55em)
  grid(columns: (1fr,) * n, column-gutter: if many > 1 { 2.4pt } else { 1.6pt },
    ..b.labels.map(l => align(center, text(6.8pt, fill: txt2, font: table-font, l))))
})

#let waterfall(b) = block(above: 8pt, below: 5pt, breakable: false, width: 100%, {
  let h = b.h * 1mm
  let colour(t) = if t == "total" { ch("total") } else if t == "gain" { ch("gain") } else if t == "zero" { ch("zero") } else { loss-fill() }
  let n = calc.max(1, b.items.len())
  grid(columns: (1fr,) * n, column-gutter: 3pt, align: bottom,
    ..b.items.map(i => stack(spacing: 1.5pt,
      align(center, text(6.3pt, weight: 600, font: table-font, i.text)),
      ..(if i.at("extra", default: "") != "" { (align(center, text(6pt, fill: ch("extra"), weight: 600, i.extra)),) } else { () }),
      rect(width: 100%, height: calc.max(i.h, 0.012) * h, fill: colour(i.t),
        stroke: if i.t == "loss" { 0.5pt + ch("loss") } else { none }))))
  line(length: 100%, stroke: 0.6pt + ch("axis"))
  v(-0.55em)
  set par(leading: 0.3em, justify: false)
  grid(columns: (1fr,) * n, column-gutter: 3pt,
    ..b.items.map(i => align(center, text(5.9pt, fill: txt2, font: table-font, i.label))))
})

#let balance(b) = block(above: 6pt, below: 5pt, breakable: false, width: 100%, {
  let h = b.h * 1mm
  chips(((t: b.names.at(0), fill: ch("produced").to-hex()), (t: b.names.at(1), fill: ch("consumed").to-hex()),
         (t: b.names.at(2), fill: "#ffffff", edge: ch("self").to-hex())))
  layout(size => {
    let n = calc.max(1, b.labels.len())
    let w = size.width / n
    let pad-x = 0.14 * w
    let bw = (w - 2 * pad-x) / 2
    box(width: size.width, height: h, {
      grid-lines(h)
      for i in range(b.labels.len()) {
        let x = i * w + pad-x
        let p = b.first.at(i) * h
        let c = b.second.at(i) * h
        place(dx: x, dy: h - p, rect(width: bw, height: p, fill: ch("produced")))
        place(dx: x + bw, dy: h - c, rect(width: bw, height: c, fill: ch("consumed")))
      }
      let points = range(b.labels.len()).map(i => ((i + 0.5) * w, h - b.line.at(i) * h))
      if points.len() > 1 {
        // a white halo under the line: it reads over the bars of the same grey
        place(curve(stroke: (paint: white, thickness: line-width + 2.2pt, join: "round"),
          curve.move(points.at(0)), ..points.slice(1).map(p => curve.line(p))))
        place(curve(stroke: (paint: ch("self"), thickness: line-width, join: "round"),
          curve.move(points.at(0)), ..points.slice(1).map(p => curve.line(p))))
      }
      for pt in points {
        place(dx: pt.at(0) - 1.6pt, dy: pt.at(1) - 1.6pt, rect(width: 3.2pt, height: 3.2pt, fill: ch("self"), stroke: 0.5pt + white))
      }
    })
    v(-0.55em)
    line(length: 100%, stroke: 0.6pt + ch("axis"))
    v(-0.55em)
    grid(columns: (1fr,) * n, ..b.labels.map(l => align(center, text(6.8pt, fill: txt2, font: table-font, l))))
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
      place(dx: 16mm, box(width: w, height: h, grid-lines(h)))
      if pts.len() > 1 {
        let first-x = pts.first().at(0)
        let last-x = pts.last().at(0)
        place(curve(fill: ch("cash").transparentize(82%), stroke: none,
          curve.move((first-x, zero)), ..pts.map(p => curve.line(p)), curve.line((last-x, zero)), curve.close()))
      }
      place(line(start: (16mm, zero), end: (size.width, zero), stroke: 0.6pt + ink))
      if pts.len() > 1 {
        place(curve(stroke: (paint: ch("cash_line"), thickness: line-width, join: "round"),
          curve.move(pts.at(0)), ..pts.slice(1).map(p => curve.line(p))))
      }
      for t in b.y {
        place(dy: h - t.at("at") * h - 3.5pt, box(width: 14.5mm, align(right, text(6.6pt, fill: txt2, font: table-font, t.t))))
      }
      for t in b.x {
        place(dx: 16mm + t.at("at") * w - 5mm, dy: h + 1.5pt, box(width: 10mm, align(center, text(6.6pt, fill: txt2, font: table-font, t.t))))
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
      place(dx: 7mm, block(width: w, height: h, stroke: hair,
        image(b.image, width: w, height: h, fit: "stretch", scaling: "pixelated")))
      for t in b.hours { place(dy: h - t.at("at") * h - 3.5pt, box(width: 5.6mm, align(right, text(6.5pt, fill: txt2, t.t)))) }
      for t in b.months { place(dx: 7mm + t.at("at") * w, dy: h + 1.5pt, text(6.5pt, fill: txt2, t.t)) }
      place(dx: size.width - 14mm, block(width: 3mm, height: h, fill: gradient.linear(white, accent, angle: -90deg), stroke: hair))
      place(dx: size.width - 10mm, text(6.5pt, fill: txt2, b.top))
      place(dx: size.width - 10mm, dy: h - 8pt, text(6.5pt, fill: txt2, "0 " + b.unit))
    })
  })
})

#let badge(b) = block(above: 4pt, below: 6pt, breakable: false,
  box(stroke: 0.6pt + colours.at(b.level), inset: (x: 7pt, y: 4pt), {
    box(baseline: 15%, mark(b.level, size: 10pt))
    h(4pt)
    text(8.6pt, weight: 600, fill: colours.at(b.level).darken(30%), b.t)
  }))

#let bullets(b) = block(above: sp("lista"), below: sp("listb"), {
  set text(9pt)
  list(tight: false, marker: text(fill: accent, "–"), indent: 2pt, spacing: sp("lista"), ..b.items.map(i => inline(i)))
})

// a step of a calculation: its title with its code, the explanation, the equation on a line of its own and numbered,
// «where:» with the symbols, their values on the comma and their sources, the hour of the example, the same equation
// with the numbers in place of the symbols ending in the result, in evidence (R479), the reference
// a line with the numbers (R479): mitex makes the comma of «30{,}0» a punctuation comma, spaced after; between two
// digits it is the decimal comma, set as an ordinary character
#let numbers-line(t) = {
  let res = mitex-convert(t)
  let tight = res.replace(regex("(\\d)\\s*\\\\,\\s*(\\d)"), m => m.captures.at(0) + "\",\"" + m.captures.at(1))
  math.equation(block: true, eval("$" + tight + "$", scope: mitex-scope))
}

#let step(b) = {
  let code = if b.code != "" { text(font: mono-font, size: 8pt, fill: accent, b.code) + h(6pt) } else { none }
  heading(level: 3, bookmarked: false, outlined: false, numbering: none, [#code#b.title])
  if b.explanation != "" { par(inline(b.explanation)) }
  let eq = if b.tex != "" { mitex(b.tex) } else { none }
  let number = text(8pt, font: table-font, fill: txt2, "(" + b.eq + ")")
  if eq != none {
    block(above: sp("eqa"), below: sp("eqb"), width: 100%, breakable: false,
      grid(columns: (1fr, auto), align: horizon, inset: (x: 0pt, y: 2pt), eq, number))
  }
  if b.inputs.len() > 0 or b.result != none {
    block(above: sp("par"), below: 2pt, text(8pt, fill: txt2, font: table-font, weight: 500, T.where))
    let rows = ()
    let cell(q, strong: false, fill: none) = {
      let sym = if q.symbol != "" { mi(q.symbol) } else { none }
      let w(x) = if strong { text(weight: 600, x) } else { x }
      (table.cell(align: left + horizon, fill: fill, sym),
       table.cell(fill: fill, w(q.label)),
       ..(if q.int == "" { (table.cell(colspan: 2, align: right, fill: fill, w(q.value)),) }
          else { (table.cell(align: right, inset: (right: 0pt), fill: fill, w(q.int)),
                  table.cell(align: left, inset: (left: 0pt), fill: fill, w(q.rest))) }),
       table.cell(fill: fill, text(fill: txt2, size: 7.4pt, inline(q.source))))
    }
    for q in b.inputs { rows += cell(q) }
    if b.result != none { rows += cell(b.result, strong: true, fill: tint) }
    set text(font: table-font, stretch: table-stretch, size: 8.4pt)
    set par(leading: 0.42em, justify: false)
    set table.cell(breakable: false)
    let header = (table.header(table.cell(fill: head-fill, head-text(T.symbol)), table.cell(fill: head-fill, head-text(T.quantity)),
      table.cell(fill: head-fill, colspan: 2, align: right, head-text(T.value)), table.cell(fill: head-fill, head-text(T.source))),)
    block(width: 100%, above: 2pt, below: sp("par"), breakable: true,
      table(columns: (13mm, 1fr, auto, auto, 0.9fr), inset: (x: 4pt, y: 3.4pt), align: top,
        stroke: (x, y) => {
          // the whole and the decimals are one column: no rule between the two
          if x == 2 { (top: grid-stroke, bottom: grid-stroke, left: grid-stroke, right: none) }
          else if x == 3 { (top: grid-stroke, bottom: grid-stroke, left: none, right: grid-stroke) }
          else { grid-stroke }
        },
        ..header, ..rows))
  }
  if b.at("worked", default: ()).len() > 0 {
    if b.example != "" {
      block(above: sp("par"), below: 3pt, text(8pt, fill: txt2, font: table-font, b.example))
    }
    block(above: 3pt, below: sp("par"), width: 100%, breakable: false,
      box(width: 100%, fill: tint, inset: (x: 8pt, y: 5pt), stroke: (left: 1.4pt + accent), {
        set text(9pt)
        stack(dir: ttb, spacing: 7pt, ..b.worked.map(t => align(left, numbers-line(t))))
      }))
  }
  if b.reference != "" {
    block(above: 2pt, below: sp("capb"), text(7.4pt, fill: faint, font: table-font, [#T.reference: #b.reference]))
  }
}

#let chapter-title(t) = t.replace(regex("^[0-9]+\.\s+"), "")

#let render(b) = {
  let k = b.k
  if k == "chapter" {
    pagebreak(weak: true)
    context [#metadata((title: b.title, id: b.id, page: here().page())) <meridiana-chapter>]
    let attachment = b.id.starts-with("attachment")
    heading(level: 1, outlined: true, bookmarked: true, numbering: if attachment { none } else { "1.1" },
      if attachment { b.title } else { chapter-title(b.title) })
  } else if k == "section" {
    heading(level: 2, bookmarked: true, b.t)
  } else if k == "sub" {
    heading(level: b.at("level", default: 3), bookmarked: false, outlined: false, numbering: none, inline(b.t))
  } else if k == "step" { step(b) }
  else if k == "p" {
    let style = b.at("style", default: "")
    if style == "caption" { caption(b.t) }
    else if style == "muted" { block(above: 4pt, below: 6pt, text(8.6pt, fill: txt2, inline(b.t))) }
    else if style == "source" { block(above: 3pt, below: 7pt, { set par(justify: false); text(7pt, fill: faint, font: table-font, stretch: table-stretch, inline(b.t)) }) }
    else if style == "lead" { block(above: 4pt, below: 8pt, text(10.5pt, inline(b.t))) }
    else { par(inline(b.t)) }
  } else if k == "tiles" or k == "dash" { dash(b) }
  else if k == "facts" { facts(b) }
  else if k == "table" { data-table(b) }
  else if k == "two" {
    let ratio = b.at("ratio", default: (1, 1))
    grid(columns: ratio.map(r => r * 1fr), column-gutter: 6mm, align: top,
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
    let tex = b.at("tex", default: TEX.at(b.image, default: none))
    if tex != none { block(above: sp("eqa"), below: sp("eqb"), mitex(tex)) }
    else if shown(b.image) { block(above: 5pt, below: 6pt, breakable: false, fitted(b.image)) }
  }
  else if k == "pagebreak" { pagebreak(weak: true) }
  else if k == "attachment" {
    pagebreak(weak: true)
    context [#metadata((k: b.n, pages: b.pages, page: here().page())) <meridiana-attachment>]
    [#metadata((title: b.title, id: b.id)) <meridiana-chapter>]
    v(55mm)
    block(width: 100%, stroke: (left: 2pt + accent), inset: (left: 9mm, y: 4mm), breakable: false, {
      text(7.4pt, weight: 600, fill: accent, tracking: 0.1em, upper(T.attachment))
      heading(level: 1, bookmarked: true, numbering: none, b.title)
      { for x in b.items { render(x) } }
    })
  }
}
#let render-all(items) = { for b in items { render(b) } }

// the contents: chapters and sections, the numbers in a column of their own, dots up to the page on the right
#let toc-entry(hd) = {
  let loc = hd.location()
  let page = str(shown-page(loc.page()))
  let num = if hd.numbering != none { numbering(if hd.level == 1 { "1." } else { "1.1" }, ..counter(heading).at(loc)) } else { "" }
  let lead = box(width: 1fr, repeat(text(fill: if hd.level == 1 { ink } else { faint }, "."), gap: 2.2pt))
  set par(leading: 0.45em, justify: false)
  set text(hyphenate: false)
  if hd.level == 1 {
    block(above: 11pt, below: 4pt, width: 100%, link(loc,
      [#box(width: 14mm, text(weight: 600, font: head-font, num))#text(weight: 600, font: head-font, hd.body)#h(3pt)#lead#h(3pt)#text(weight: 600, page)]))
  } else {
    block(above: 3.5pt, below: 3.5pt, width: 100%, link(loc,
      [#box(width: 14mm, num)#hd.body#h(3pt)#lead#h(3pt)#page]))
  }
}
#let contents-page() = context {
  let found = query(heading.where(outlined: true)).filter(h => h.level <= S.toc_levels)
  heading(level: 1, numbering: none, outlined: false, bookmarked: true, T.contents)
  for hd in found { toc-entry(hd) }
}

// the cover: the logo's row, the title of the document and the plant on the left, the data in a column on the right,
// the 3D view large and without a frame
#let doc-title = D.doc.at("doc_title", default: T.report)
#let doc-sub = D.doc.at("doc_sub", default: "")
#let cover-image(c, h) = if shown(c.image) {
  block(width: 100%, height: h, fill: if c.at("tint", default: false) { tint } else { white },
    stroke: if is-view(c.image) { none } else { thin }, inset: c.at("inset", default: 0) * 1mm,
    align(center + horizon, image(c.image, width: 100%, height: 100%, fit: "contain")))
}
#let cover-logo-row() = {
  block(width: 100%, stroke: (bottom: 0.5pt + ink), inset: (bottom: 5pt),
    grid(columns: (auto, 1fr), align: (left + bottom, right + bottom),
      if has-logo { logo-box(height: 14mm, room: 60mm) } else if D.doc.at("logo_placeholder", default: false) { logo-placeholder(height: 14mm, width: 56mm) } else { none },
      align(right, stack(spacing: 2.4pt, text(8pt, weight: 600, font: head-font, D.doc.foot_left), text(7.5pt, fill: txt2, D.doc.foot_left2)))))
}
#let cover(c) = page(header: none, footer: none, margin: (left: 20mm, right: 16mm, top: 20mm, bottom: 18mm), {
  set text(hyphenate: false)
  set par(justify: false)
  cover-logo-row()
  v(10mm)
  grid(columns: (1fr, 60mm), column-gutter: 10mm, align: top,
    {
      block({ set par(leading: 0.42em); text(24pt, weight: 300, font: head-font, doc-title) })
      v(2mm)
      text(11pt, fill: txt2, font: head-font, doc-sub)
      v(6mm)
      text(7.5pt, weight: 600, fill: accent, tracking: 0.16em, font: head-font, upper(T.plant))
      v(1.5mm)
      text(15pt, weight: 500, font: head-font, c.title)
      v(2mm)
      text(9.5pt, fill: txt2, c.sub)
    },
    block(width: 100%, stroke: (left: 1.2pt + accent), inset: (left: 5mm, y: 1mm), {
      set text(8.4pt)
      set par(leading: 0.45em)
      for m in c.meta {
        text(6.6pt, weight: 600, fill: txt2, tracking: 0.06em, upper(m.t))
        linebreak()
        m.lines.join(linebreak())
        v(3.5mm, weak: true)
      }
    }))
  v(8mm)
  cover-image(c, 112mm)
  v(1fr)
  block(width: 100%, stroke: (top: 0.5pt + ink), inset: (top: 5pt), align(right, text(7pt, fill: faint, c.made)))
})

#let compact-head(c) = block(above: 0pt, below: 8pt, breakable: false, {
  set par(justify: false)
  text(7.6pt, weight: 600, fill: accent, tracking: 0.14em, upper(c.kicker))
  block(above: 4pt, below: 8pt, text(21pt, weight: 300, font: head-font, c.title))
  if c.sub != "" { block(above: 3pt, below: 3pt, text(9.6pt, fill: txt2, c.sub)) }
  if c.lines.len() > 0 { block(above: 4pt, below: 0pt, { set text(8pt, fill: txt2); c.lines.join(" · ") }) }
  if c.made != "" { block(above: 3pt, below: 0pt, text(6.8pt, fill: faint, c.made)) }
})

// ---- the document ----
// (what is above is also the head of the pictures of the editable exports: report_typst/editable.py cuts here)

#if D.cover != none { cover(D.cover) }
#if D.cover != none or D.toc == "page" {
  contents-page()
  pagebreak()
}
#if D.head != none { compact-head(D.head) }
#render-all(D.body)
