// One page in the spirit of sketch B (numbers first) and the forty-row table: does Typst keep rows whole,
// repeat the header, number the pages, and embed Inter?
#set page(paper: "a4", margin: (x: 20mm, y: 20mm),
  header: context { if counter(page).get().first() > 1 [
    #set text(8pt, fill: luma(110))
    Studio di prova #h(1fr) Relazione tecnica, Rev. 0 ] },
  footer: context [ #set text(8pt, fill: luma(110))
    Impianto fotovoltaico 331,2 kWp, Rho (MI) #h(1fr) pagina #counter(page).display() di #counter(page).final().first() ])
#set text(font: "Inter", size: 10.5pt, lang: "it", hyphenate: true)
#set par(justify: true, leading: 0.6em)
#show heading.where(level: 1): it => block(above: 0pt, below: 10pt, text(23pt, weight: 600, it.body))
#show heading.where(level: 2): it => block(above: 16pt, below: 6pt, text(13pt, weight: 600, it.body))

#let big(n, u, l) = box(width: 100%)[
  #text(22pt, weight: 700, number-width: "tabular", n) #text(10pt, fill: luma(110), u) \
  #text(8.5pt, fill: luma(110), l) ]

= Prova Typst: numeri grandi e una tabella che si spezza fra le righe
#v(10pt)
#grid(columns: (1fr, 1fr, 1fr, 1fr), gutter: 10pt,
  big("331,2", "kWp", "potenza di picco, 736 moduli"),
  big("420.700", "kWh/anno", "energia nell'anno tipo"),
  big("1.270", "kWh/kWp", "producibilità specifica"),
  big("78,1", "%", "performance ratio"))

#v(8pt)
Un paragrafo giustificato con sillabazione italiana: l'impianto, posto sulla copertura di un capannone a Rho
(MI), è formato da 736 moduli da 450 Wp su due inverter da 100 kW; la producibilità è calcolata con pvlib
sull'anno tipo PVGIS-SARAH3 e ogni numero della relazione porta con sé la riga del registro da cui viene.

== Verifiche delle stringhe

#show table.cell.where(y: 0): set text(weight: 600)
// A row stays whole: its cells are unbreakable blocks (Typst breaks rows otherwise, seen on the first try).
#show table.cell: it => block(breakable: false, it)
#table(columns: (8%, 52%, 20%, 20%), stroke: (x, y) => (bottom: 0.5pt + luma(200)),
  fill: (x, y) => if y == 0 { rgb("#efede8") }, inset: (x: 6pt, y: 4pt),
  table.header([N.], [Verifica], [Valore], [Esito]),
//ROWS
)
