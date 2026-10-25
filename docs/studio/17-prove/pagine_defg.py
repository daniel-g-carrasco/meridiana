"""Le pagine D (grafici), E (aiuti), F (verifiche) e G (Meridio) dei bozzetti dello studio 17; genera.py le scrive."""

from __future__ import annotations

import html
import json

import parti as P
from parti import direction, icon, page, window

MONTHS = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
PROD = [3.9, 5.4, 8.1, 9.6, 11.2, 11.9, 12.6, 11.4, 8.7, 6.1, 3.8, 3.2]        # MWh
CONS = [7.8, 7.1, 7.4, 6.6, 6.9, 7.6, 8.4, 6.2, 6.8, 7.0, 7.5, 8.1]
SELF = [2.9, 3.7, 4.6, 4.5, 4.7, 4.9, 5.4, 4.3, 4.3, 3.9, 2.8, 2.5]

# ============================================================ D. grafici

D_CSS = """
.charts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; }
.charts .box { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; min-width: 0; }
.charts h3 { margin: 0 0 4px; font-size: 16px; }
.charts .sub { font-size: 13px; color: var(--text2); margin: 0 0 8px; }
.chart { position: relative; background: var(--chart-surface); border-radius: 6px; border: 1px solid var(--line-soft); margin: 8px 0; }
.chart svg { width: 100%; display: block; font-family: inherit; }
.chart .tip { position: absolute; pointer-events: none; display: none; background: var(--tooltip-bg); color: var(--tooltip-fg);
              font-size: 12px; padding: 4px 8px; border-radius: 4px; white-space: nowrap; z-index: 2; }
.chart .tip b { font-variant-numeric: tabular-nums; }
.chart .legend { display: flex; gap: 12px; padding: 4px 10px 6px; font-size: 12px; color: var(--text2); flex-wrap: wrap; }
.chart .legend span { display: inline-flex; align-items: center; gap: 5px; cursor: pointer; user-select: none; }
.chart .legend i { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }
.chart .legend span.off { opacity: 0.4; text-decoration: line-through; }
.chart .tools { position: absolute; top: 6px; right: 8px; display: flex; gap: 4px; }
.chart .tools span { font-size: 11px; padding: 1px 7px; border: 1px solid var(--line); border-radius: 4px; background: var(--panel); color: var(--text2); cursor: pointer; }
.chart .crossv, .chart .crossh { stroke: var(--text2); stroke-width: 1; stroke-dasharray: 3 3; pointer-events: none; }
.chart .readout { position: absolute; left: 10px; top: 6px; font-size: 12px; color: var(--text2); font-variant-numeric: tabular-nums; pointer-events: none; }
.chart .mpl { font-family: "DejaVu Sans", "Titillium Web", sans-serif; }
.chart .brush { fill: var(--accent); opacity: 0.15; }
.chart .ov { height: 44px; border-top: 1px solid var(--line-soft); }
.charts .meta { font-size: 12px; color: var(--muted); margin: 4px 0 0; }
.charts .note { font-size: 13.5px; color: var(--text2); line-height: 1.35; margin: 8px 0 0; }
.charts .note b { color: var(--text); }
"""

D_JS = r"""
<script>
const YEAR = %(year)s;
const SERIES = [{k:'Produzione', c:'#2e6fb0', data:YEAR}, {k:'Autoconsumo', c:'#0ca30c', data:YEAR.map((v,i)=>Math.min(v, 6+4*Math.sin(i/24*Math.PI)+(i%%24>7&&i%%24<19?6:0)))}];
const MONTHS = %(months)s, PROD = %(prod)s, CONS = %(cons)s, SELF = %(self)s;
function fmt(v, d=1) { return v.toLocaleString('it-IT', {minimumFractionDigits:d, maximumFractionDigits:d}); }
function hourLabel(i) { const d = Math.floor(i/24), h = i%%24; const dt = new Date(2025,0,1+d); return dt.getDate()+' '+MONTHS[dt.getMonth()].toLowerCase()+', '+h+':00'; }

// ---- grafici a barre mensili (uguali nelle tre direzioni, con il comportamento diverso) ----
function bars(host, style) {
  const W = 520, H = 220, L = 46, R = 12, T = 18, B = 28, w = W-L-R, h = H-T-B, vmax = 14;
  let s = `<svg viewBox="0 0 ${W} ${H}" class="${style==='mpl'?'mpl':''}">`;
  for (let g=0; g<=vmax; g+=2) { const y = T + h - h*g/vmax; s += `<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="var(--chart-grid)"/><text x="${L-6}" y="${y+4}" font-size="11" text-anchor="end" fill="var(--text2)">${g}</text>`; }
  const bw = w/12;
  MONTHS.forEach((m,i) => {
    const x = L + i*bw;
    const hp = h*PROD[i]/vmax, hc = h*CONS[i]/vmax, hs = h*SELF[i]/vmax;
    s += `<g class="bar" data-i="${i}"><rect x="${x+4}" y="${T+h-hc}" width="${bw/2-5}" height="${hc}" fill="#7b7f87" opacity="0.55"/>`;
    s += `<rect x="${x+bw/2+1}" y="${T+h-hp}" width="${bw/2-5}" height="${hp}" fill="#2e6fb0"/>`;
    s += `<rect x="${x+bw/2+1}" y="${T+h-hs}" width="${bw/2-5}" height="${hs}" fill="#0ca30c"/>`;
    s += `<rect class="hit" x="${x}" y="${T}" width="${bw}" height="${h}" fill="transparent"/></g>`;
    s += `<text x="${x+bw/2}" y="${H-10}" font-size="11" text-anchor="middle" fill="var(--text2)">${m}</text>`;
  });
  s += `<line x1="${L}" x2="${W-R}" y1="${T+h}" y2="${T+h}" stroke="var(--chart-axis)"/><text x="${L}" y="11" font-size="11" fill="var(--muted)">MWh</text></svg>`;
  s += `<div class="tip"></div><div class="legend"><span data-k="c"><i style="background:#7b7f87"></i>Consumo</span><span data-k="p"><i style="background:#2e6fb0"></i>Produzione</span><span data-k="s"><i style="background:#0ca30c"></i>di cui autoconsumata</span></div>`;
  host.innerHTML = s;
  const tip = host.querySelector('.tip');
  host.querySelectorAll('.bar').forEach(g => {
    g.addEventListener('mousemove', e => { const i = +g.dataset.i; tip.style.display='block'; tip.style.left=(e.offsetX+14)+'px'; tip.style.top=(e.offsetY-10)+'px';
      tip.innerHTML = style==='mpl' ? `${MONTHS[i]}: <b>${fmt(PROD[i])}</b> MWh` : `<b>${MONTHS[i]}</b><br>Produzione <b>${fmt(PROD[i])}</b> MWh<br>Autoconsumo <b>${fmt(SELF[i])}</b> MWh (${Math.round(100*SELF[i]/PROD[i])} %%)<br>Consumo <b>${fmt(CONS[i])}</b> MWh`;
      g.querySelectorAll('rect:not(.hit)').forEach(r => r.setAttribute('stroke', 'var(--text)')); });
    g.addEventListener('mouseleave', () => { tip.style.display='none'; g.querySelectorAll('rect').forEach(r => r.removeAttribute('stroke')); });
  });
  if (style !== 'mpl') host.querySelectorAll('.legend span').forEach(sp => sp.addEventListener('click', () => { sp.classList.toggle('off');
    const k = sp.dataset.k, off = sp.classList.contains('off'); host.querySelectorAll('.bar').forEach(g => { const rs = g.querySelectorAll('rect:not(.hit)'); const r = {c:rs[0], p:rs[1], s:rs[2]}[k]; r.style.display = off ? 'none' : ''; }); }));
}

// ---- la linea oraria: 8.760 punti ----
function lines(host, style, from=0, to=8760) {
  const t0 = performance.now();
  const W = 520, H = 230, L = 46, R = 12, T = 18, B = 28 + (style==='web'?44:0), w = W-L-R, h = H-T-B, vmax = 80;
  const n = to - from;
  let s = `<svg viewBox="0 0 ${W} ${H}" class="${style==='mpl'?'mpl':''}">`;
  for (let g=0; g<=vmax; g+=20) { const y = T + h - h*g/vmax; s += `<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="var(--chart-grid)"/><text x="${L-6}" y="${y+4}" font-size="11" text-anchor="end" fill="var(--text2)">${g}</text>`; }
  SERIES.forEach((se, si) => { let d = ''; const step = Math.max(1, Math.floor(n/2000));
    for (let i=from; i<to; i+=step) { const x = L + w*(i-from)/n, y = T + h - h*Math.min(vmax, se.data[i])/vmax; d += (d?'L':'M')+x.toFixed(1)+' '+y.toFixed(1); }
    s += `<path class="ser" data-s="${si}" d="${d}" fill="none" stroke="${se.c}" stroke-width="${si?1:0.8}" opacity="${si?0.9:0.85}"/>`; });
  for (let m=0; m<12; m++) { const d0 = new Date(2025,m,1), i = (d0 - new Date(2025,0,1))/36e5; if (i>=from && i<to) { const x = L + w*(i-from)/n; s += `<text x="${x+2}" y="${T+h+14}" font-size="11" fill="var(--text2)">${MONTHS[m]}</text>`; } }
  s += `<line x1="${L}" x2="${W-R}" y1="${T+h}" y2="${T+h}" stroke="var(--chart-axis)"/><text x="${L}" y="11" font-size="11" fill="var(--muted)">kW</text>`;
  s += `<line class="crossv" x1="0" x2="0" y1="${T}" y2="${T+h}" style="display:none"/><line class="crossh" x1="${L}" x2="${W-R}" y1="0" y2="0" style="display:none"/>`;
  s += `<rect class="brush" x="0" y="${T}" width="0" height="${h}" style="display:none"/>`;
  s += `<rect class="hit" x="${L}" y="${T}" width="${w}" height="${h}" fill="transparent" style="cursor:${style==='mpl'?'default':'crosshair'}"/>`;
  if (style === 'web') { // la striscia di panoramica
    const oy = H-40, oh = 34; let d=''; for (let i=0;i<8760;i+=6){ const x=L+w*i/8760, y=oy+oh-oh*Math.min(vmax,YEAR[i])/vmax; d+=(d?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);}
    s += `<line x1="${L}" x2="${W-R}" y1="${oy-4}" y2="${oy-4}" stroke="var(--line-soft)"/><path d="${d}" fill="none" stroke="var(--muted)" stroke-width="0.6"/><rect class="win" x="${L+w*from/8760}" y="${oy}" width="${w*(to-from)/8760}" height="${oh}" fill="var(--accent)" opacity="0.18" stroke="var(--accent)"/>`;
  }
  s += `</svg><div class="tip"></div>`;
  if (style !== 'mpl') s += `<div class="readout"></div>`;
  s += `<div class="legend">` + SERIES.map((se,i)=>`<span data-s="${i}"><i style="background:${se.c}"></i>${se.k}</span>`).join('') + `</div>`;
  if (style !== 'mpl') s += `<div class="tools"><span class="reset">Tutto l'anno</span>${style==='web'?'<span>PNG</span><span>SVG</span>':''}</div>`;
  host.innerHTML = s;
  const ms = performance.now() - t0;
  const meta = host.parentElement.querySelector('.meta'); if (meta) meta.textContent = `${n.toLocaleString('it-IT')} valori orari disegnati in ${ms.toFixed(1)} ms (browser)`;
  const svg = host.querySelector('svg'), hit = host.querySelector('.hit'), tip = host.querySelector('.tip'), cv = host.querySelector('.crossv'), ch = host.querySelector('.crossh'), ro = host.querySelector('.readout'), brush = host.querySelector('.brush');
  let drag = null;
  function pos(e) { const r = svg.getBoundingClientRect(); return [(e.clientX - r.left) * W / r.width, (e.clientY - r.top) * H / r.height]; }
  hit.addEventListener('mousemove', e => { const [x, y] = pos(e); const i = Math.max(from, Math.min(to-1, Math.round(from + (x-L)/w*n)));
    const v = YEAR[i], a = SERIES[1].data[i];
    if (style === 'mpl') { tip.style.display='block'; tip.style.left=(e.offsetX+14)+'px'; tip.style.top=(e.offsetY-10)+'px'; tip.innerHTML = `${hourLabel(i)}: <b>${fmt(v)}</b> kW`; }
    else { cv.style.display=''; cv.setAttribute('x1', x); cv.setAttribute('x2', x); ch.style.display=''; ch.setAttribute('y1', y); ch.setAttribute('y2', y);
      ro.innerHTML = `${hourLabel(i)} · Produzione <b>${fmt(v)}</b> kW · Autoconsumo <b>${fmt(a)}</b> kW`;
      if (style === 'web') { tip.style.display='block'; tip.style.left=(e.offsetX+14)+'px'; tip.style.top=(e.offsetY-30)+'px'; tip.innerHTML = `<b>${hourLabel(i)}</b><br><span style="color:#8ab4f8">●</span> Produzione <b>${fmt(v)}</b> kW<br><span style="color:#7ddc7d">●</span> Autoconsumo <b>${fmt(a)}</b> kW`; }
      if (drag !== null) { brush.style.display=''; brush.setAttribute('x', Math.min(drag, x)); brush.setAttribute('width', Math.abs(x-drag)); } }
  });
  hit.addEventListener('mouseleave', () => { tip.style.display='none'; cv.style.display='none'; ch.style.display='none'; if (ro) ro.textContent=''; });
  if (style !== 'mpl') {
    hit.addEventListener('mousedown', e => { drag = pos(e)[0]; });
    window.addEventListener('mouseup', e => { if (drag === null) return; const [x] = pos(e); const a = from + (Math.min(drag,x)-L)/w*n, b = from + (Math.max(drag,x)-L)/w*n; drag = null; brush.style.display='none';
      if (b - a > 24) lines(host, style, Math.max(0, Math.floor(a)), Math.min(8760, Math.ceil(b))); });
    host.querySelector('.reset').addEventListener('click', () => lines(host, style));
    host.querySelectorAll('.legend span').forEach(sp => sp.addEventListener('click', () => { sp.classList.toggle('off'); host.querySelector(`.ser[data-s="${sp.dataset.s}"]`).style.display = sp.classList.contains('off') ? 'none' : ''; }));
  }
}
document.querySelectorAll('[data-bars]').forEach(h => bars(h, h.dataset.bars));
document.querySelectorAll('[data-lines]').forEach(h => lines(h, h.dataset.lines));
</script>
"""


def page_d() -> str:
    intro = ("<p>R23. Daniel: «i grafici non sono dinamici, non visualizzano nulla al passaggio del mouse, non è possibile controllarli. "
             "Negli sketch negli artefatti era possibile far più cose e il tutto era più carino. come mai qua non è così?». Perché oggi i "
             "grafici sono <b>immagini</b> disegnate da matplotlib in un widget (<code>ui/charts.py</code>): rispondono al passaggio solo "
             "con il suggerimento del widget, mentre la tela degli artefatti usava HTML e SVG nel browser. Qui tre direzioni, con lo "
             "stesso grafico mensile e lo stesso anno di valori orari (8.760 punti, sintetici): passaci sopra, trascina, clicca la legenda. "
             "Le misure in Qt (matplotlib, pyqtgraph, Qt Charts, Qt Graphs, vista web) sono in <code>grafici_prova.py</code>.</p>")
    year = P.synthetic_year()
    boxes = ""
    for style, title, sub, note in (
        ("mpl", "D1. matplotlib con gli eventi", "Quello di oggi più gli eventi del mouse",
         "Resta matplotlib (già nel programma, stesse immagini nella relazione PDF): si aggiungono <b>il valore al passaggio</b> con un'annotazione, "
         "la barra evidenziata, lo zoom con la barra di navigazione di matplotlib (lente e frecce) e il clic sulla legenda. Costo zero in dipendenze; "
         "la risposta al mouse passa dal ridisegno del canvas (10-40 ms per grafico, da misurare) e la grafica resta quella «da stampa»."),
        ("pg", "D2. pyqtgraph", "Mirino, lettura in alto, zoom con il trascinamento, legenda che accende e spegne",
         "Una libreria fatta per i dati vivi in Qt (MIT, numpy): <b>mirino</b> che segue il mouse con la lettura dei valori, <b>zoom</b> trascinando "
         "e rotella, serie accese e spente dalla legenda, 8.760 punti senza fatica. Una dipendenza in più (da proporre), stile da regolare con il "
         "tema (è fatto per il nero), esportazione in SVG o immagine per la relazione."),
        ("web", "D3. Vista web", "Come nella tela: tooltip con tutte le serie, pennello sulla panoramica, esportazione",
         "I grafici in una <b>vista web</b> (QtWebEngine, già nel pacchetto PySide6 ma 180 MB in più nell'installazione): HTML e SVG come negli "
         "artefatti, con una libreria JavaScript (uPlot, Chart.js, Plotly) o SVG scritto a mano come qui. La resa più ricca, al prezzo di un "
         "processo del browser per finestra, del ponte Python-JavaScript e di un secondo modo di disegnare per il PDF.")):
        boxes += (f'<div class="box"><h3>{title}</h3><p class="sub">{sub}</p>'
                  f'<div class="chart" data-bars="{style}"></div>'
                  f'<div class="chart" data-lines="{style}"></div><p class="meta"></p><p class="note">{note}</p></div>')
    js = D_JS % {"year": json.dumps(year), "months": json.dumps(MONTHS), "prod": json.dumps(PROD), "cons": json.dumps(CONS), "self": json.dumps(SELF)}
    return page("D. Grafici interattivi", intro, f'<div class="charts">{boxes}</div>', D_CSS, js)


# ============================================================ E. aiuti

E_CSS = """
.mock .help { display: inline-grid; place-items: center; width: 16px; height: 16px; border-radius: 50%; color: var(--muted); margin-left: 4px;
              vertical-align: middle; cursor: help; }
.mock .help:hover { color: var(--accent); }
.mock .gt .help { margin-left: 6px; }
.mock .pop { position: absolute; width: 260px; background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px;
             box-shadow: 0 4px 14px var(--shadow); font-size: 12.5px; line-height: 1.4; z-index: 5; }
.mock .pop b { display: block; margin-bottom: 3px; }
.mock .pop a { color: var(--accent); text-decoration: none; }
.mock .pop .links { margin-top: 6px; display: flex; gap: 10px; }
.mock .hint { grid-column: 1 / -1; font-size: 11.5px; color: var(--muted); margin: -2px 0 4px; line-height: 1.3; }
.mock .ttip { position: absolute; background: var(--tooltip-bg); color: var(--tooltip-fg); font-size: 12px; padding: 6px 9px; border-radius: 5px;
              width: 250px; line-height: 1.35; z-index: 5; }
.mock .ttip b { display: block; }
.mock .ttip .k { opacity: 0.7; margin-top: 4px; display: block; }
.mock .helpdock { border-top: 1px solid var(--line); background: var(--panel); padding: 8px 10px; font-size: 12.5px; line-height: 1.4; }
.mock .helpdock h5 { margin: 0 0 4px; font-size: 12px; color: var(--text2); display: flex; gap: 6px; align-items: center; }
.mock .helpdock a { color: var(--accent); text-decoration: none; }
.mock .helpdock .links { display: flex; gap: 10px; margin-top: 6px; }
.mock .e3 .props { max-height: 380px; }
.mock .statushelp { color: var(--text2); }
.mock .hbox { display: flex; gap: 6px; }
.mock .value { font-weight: 600; text-align: right; }
.mock .note { grid-column: 1 / -1; color: var(--muted); font-size: 12px; }
.mock .flagbar { position: absolute; left: 230px; top: 72px; background: var(--card); border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; font-size: 12px; box-shadow: 0 2px 8px var(--shadow); display: flex; gap: 8px; align-items: center; }
.mock .flagbar b { color: var(--accent); }
.examples { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; max-width: 1500px; }
.examples .ex { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; font-size: 14px; }
.examples h4 { margin: 0 0 6px; font-size: 15px; }
.examples dl { margin: 0; display: grid; grid-template-columns: 180px 1fr; gap: 4px 10px; }
.examples dt { color: var(--text2); } .examples dd { margin: 0; line-height: 1.35; }
"""


def props_with_help(mode: str) -> str:
    """Le Proprietà con gli aiuti: «?» accanto ai titoli e ai campi (e1), frasi sotto i campi (e2), niente (e3: l'aiuto è nel pannello)."""
    out = []
    hints = {"Dal bordo dell'area": "Fascia libera lungo il contorno dell'area. Con le regole VVF vale almeno 1 m.",
             "Tra le file": "Spazio tra una fila e l'altra sulla falda; a terra lo dà il sole.",
             "Fuori dalle ombre": "Toglie i moduli in ombra nel giorno di progetto tra le ore della finestra."}
    for title, fields in P.PROPS:
        rows = []
        for label, value, kind in fields:
            h = f'<span class="help">{icon("help", 13)}</span>' if mode == "e1" and kind in ("spin", "combo", "check") else ""
            if kind in ("text", "combo"):
                w = f'<div class="field {"combo" if kind == "combo" else ""}">{value}</div>'
            elif kind == "spin":
                w = f'<div class="field">{value}<span class="arr">▴▾</span></div>'
            elif kind == "btn":
                w = f'<div class="hbox"><div class="field" style="flex:1;min-width:0;overflow:hidden">{value}</div><span class="btn" style="padding:0 7px">…</span></div>'
            elif kind == "check":
                w = f'<div class="check"><i class="on"></i>{"Automatico" if label == "Azimut" else ""}</div>'
            elif kind == "value":
                w = f'<div class="value">{value}</div>'
            else:
                w = f'<div class="note">{value}</div>'
            rows.append(f'<label>{label}{h}</label>{w}')
            if mode == "e2" and label in hints:
                rows.append(f'<div class="hint">{hints[label]}</div>')
        head = f'<div class="gt">{title}{"<span class=\"help\">" + icon("help", 13) + "</span>" if mode == "e1" else ""}</div>'
        out.append(f'<div class="group">{head}<div class="form">{"".join(rows)}</div></div>')
    buttons = '<div class="hbox" style="margin-top:8px"><span class="btn primary">Posa i moduli</span><span class="btn">Svuota</span></div>'
    return f'<div class="props">{"".join(out)}{buttons}</div>'


def page_e() -> str:
    intro = ("<p>R24. Daniel: «non ci sono helper di fianco ai risultati o nelle varie sezioni che li spiegano, che spiegano come utilizzare i "
             "comandi, cosa vogliano dire determinate cose». Tre direzioni sullo stesso pannello Proprietà del sottocampo; la barra di stato "
             "spiega già lo strumento, e «Come è calcolato» esiste già per i risultati: qui si collegano. Sotto, gli esempi di testo per le "
             "sezioni principali.</p>")
    pop = ('<div class="pop" style="right:200px;top:300px"><b>Dal bordo dell\'area</b>Fascia libera lungo il contorno dell\'area, dove i moduli '
           'non vanno: per la manutenzione e per le regole dei Vigili del Fuoco (1 m se l\'attività è soggetta, DCPREV 14030/2025, 3.3.5.1).'
           '<div class="links"><a href="#">Manuale ›</a><a href="#">Come è calcolato ›</a></div></div>')
    e1 = direction("E1. Il «?» accanto ai titoli e ai campi",
                   window("e1", right=f'<div class="side right"><div class="ptitle">Proprietà<span class="x">✕</span></div>{props_with_help("e1")}</div>',
                          extra=pop),
                   "Un <b>«?»</b> discreto accanto a ogni titolo di gruppo e ai campi che lo meritano; un clic apre un <b>riquadro</b> di tre righe con "
                   "la fonte e i collegamenti al manuale e a «Come è calcolato». È la convenzione di macOS (help button), di JetBrains (help tooltip) "
                   "e il «?» dei dialoghi GTK. Non ingombra finché non si chiede.")
    ttip = ('<div class="ttip" style="right:330px;top:356px"><b>Tra le file</b>Lo spazio tra una fila e l\'altra. Sulle falde è un valore; a terra e '
            'sui tetti piani lo calcola il sole del giorno di progetto, così la fila davanti non fa ombra tra le ore scelte.'
            '<span class="k">Maiusc+F1: di più nel manuale</span></div>')
    e2 = direction("E2. Frasi sotto i campi e suggerimenti estesi",
                   window("e2", right=f'<div class="side right"><div class="ptitle">Proprietà<span class="x">✕</span></div>{props_with_help("e2")}</div>',
                          extra=ttip),
                   "Una <b>frase d'aiuto sotto il campo</b>, attenuata, per i campi che non si spiegano da soli (GNOME: subtitle delle righe; "
                   "VS Code: le descrizioni delle impostazioni), e i <b>suggerimenti estesi</b> dopo un attimo di sosta (Revit: tooltip "
                   "assistance, AutoCAD: rollover). Sempre visibile, quindi più lungo il pannello: va dosata.")
    helpdock = ('<div class="helpdock"><h5>' + icon("book", 14) + ' Aiuto · Dal bordo dell\'area</h5>Fascia libera lungo il contorno dell\'area. '
                'Serve per la manutenzione e per le regole dei Vigili del Fuoco: con l\'attività soggetta vale almeno 1 m e Meridiana la impone '
                'da sola.<div class="links"><a href="#">Manuale: la posa ›</a><a href="#">Come è calcolato ›</a><a href="#">Chiedi a Meridio ›</a></div></div>')
    e3 = direction("E3. Un pannello d'aiuto che segue il fuoco",
                   window("e3", right=f'<div class="side right e3"><div class="ptitle">Proprietà<span class="x">✕</span></div>{props_with_help("e3")}{helpdock}</div>'),
                   "Un <b>riquadro d'aiuto</b> in fondo alle Proprietà (o un pannello Ctrl+?) che spiega <b>il campo che ha il fuoco</b> o il risultato "
                   "sotto il mouse, con i collegamenti al manuale, a «Come è calcolato» e a Meridio. È il «Dynamic Help» di Visual Studio e il pannello "
                   "info di Blender. Sempre lì, mai sopra; costa 70-90 px di altezza.")
    examples = """
<div class="examples">
<div class="ex"><h4>Proprietà del sottocampo</h4><dl>
<dt>Montaggio</dt><dd>Come i moduli stanno sulla superficie: complanari alla falda, su file inclinate (ancorate o zavorrate), est-ovest, a terra, in pensilina. Decide pendenza e passo.</dd>
<dt>Moduli per tavola, di traverso</dt><dd>Quanti moduli uno sopra l'altro in una tavola: 2 è la «2V» dei montaggi a terra.</dd>
<dt>Tra le file</dt><dd>Sulle falde è un valore; a terra lo dà il sole: nessuna ombra tra le file nel giorno di progetto, tra le ore della finestra.</dd>
<dt>Fuori dalle ombre</dt><dd>Toglie i moduli che gli ostacoli ombreggiano nel giorno di progetto. Dice quanti moduli costa.</dd>
</dl></div>
<div class="ex"><h4>Producibilità</h4><dl>
<dt>Resa specifica</dt><dd>I kWh prodotti in un anno per ogni kWp installato. In Italia tra 1.000 e 1.500: sotto, cerca le ombre e l'orientamento.</dd>
<dt>Performance ratio</dt><dd>Quanto dell'energia che arriva sui moduli diventa energia al contatore. Tra 0,75 e 0,85 è normale.</dd>
<dt>Perdite</dt><dd>Ogni voce è un passo della catena, dal sole al contatore: ombre, temperatura, sporco, cavi, inverter. «Come è calcolato» mostra la formula e la fonte di ogni numero.</dd>
<dt>PVGIS</dt><dd>L'anno tipo e l'orizzonte del sito, dal servizio europeo. Scaricati una volta, poi in cache.</dd>
</dl></div>
<div class="ex"><h4>Bilancio ed economia</h4><dl>
<dt>Autoconsumo</dt><dd>La parte della produzione usata sul posto, ora per ora. Il resto va in rete.</dd>
<dt>Autosufficienza</dt><dd>La parte dei consumi coperta dall'impianto. Con l'accumulo sale.</dd>
<dt>VAN</dt><dd>Il valore attuale netto a 20 anni: quanto rende l'impianto oltre il costo, scontato al tasso scelto. Positivo conviene.</dd>
<dt>Prezzi</dt><dd>Valori indicativi finché non scrivi quelli della bolletta e del preventivo; la relazione lo dice.</dd>
</dl></div>
<div class="ex"><h4>Verifiche</h4><dl>
<dt>Da correggere</dt><dd>Qualcosa che la norma o la posa non ammette: il progetto non va consegnato così. «Correggi» fa la cosa proposta, annullabile.</dd>
<dt>Da controllare</dt><dd>Una perdita o un rischio, non un divieto: decidi tu.</dd>
<dt>Da sapere</dt><dd>Un fatto che la relazione citerà: una soglia superata, un valore predefinito ancora in uso.</dd>
<dt>Fonte</dt><dd>La norma con l'articolo e la pagina, o il modello di calcolo. Un clic la apre nel pedigree.</dd>
</dl></div>
</div>"""
    body = f'<div class="row">{e1}{e2}{e3}</div><h2>Esempi di testo (chi li scrive: Daniel, con una bozza della sessione; dove stanno: un file di testi tradotti, uno per campo)</h2>{examples}'
    return page("E. Aiuti accanto alle cose", intro, body, E_CSS)


# ============================================================ F. verifiche

F_CSS = """
.vrow { display: flex; gap: 22px; align-items: flex-start; overflow-x: auto; }
.vbox { flex: 0 0 auto; width: 760px; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; font-size: 13px; }
.vbox .ptitle { padding: 6px 10px; font-weight: 600; font-size: 12px; color: var(--text2); border-bottom: 1px solid var(--line-soft); display: flex; gap: 8px; align-items: center; }
.vbox .ptitle .x { margin-left: auto; color: var(--muted); font-weight: 400; }
.vbox .chead { display: flex; gap: 6px; align-items: center; padding: 6px 10px; font-size: 12px; border-bottom: 1px solid var(--line-soft); }
.vbox .chead .f { padding: 1px 8px; border: 1px solid var(--line); border-radius: 12px; background: var(--view); display: inline-flex; gap: 4px; align-items: center; }
.vbox .chead .f.on { background: var(--select-bg); }
.vbox .chead .f b { font-size: 11px; }
.vbox .chead .sp { flex: 1; }
.vbox .m { width: 18px; text-align: center; font-weight: 700; flex: none; }
.vbox .m.fail { color: var(--critical); } .vbox .m.warn { color: var(--warning-ink); } .vbox .m.ok { color: var(--good); } .vbox .m.info { color: var(--muted); }
.vbox .it { display: flex; gap: 8px; align-items: center; padding: 5px 10px; border-bottom: 1px solid var(--line-soft); }
.vbox .it:hover { background: var(--sink); }
.vbox .it .t { flex: 1; }
.vbox .it .src { color: var(--muted); font-size: 11.5px; white-space: nowrap; }
.vbox .it .act { display: inline-flex; gap: 6px; }
.vbox .it .b { font-size: 11.5px; padding: 1px 8px; border-radius: 4px; border: 1px solid var(--line); background: var(--view); color: var(--text); white-space: nowrap; }
.vbox .it .b.fix { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.vbox .it .b.ico { padding: 1px 5px; color: var(--text2); }
.vbox .it .chev { color: var(--muted); font-size: 11px; width: 10px; }
.vbox .detail { padding: 4px 10px 8px 46px; color: var(--text2); font-size: 12.5px; line-height: 1.4; border-bottom: 1px solid var(--line-soft); background: var(--sink); }
.vbox .detail b { color: var(--text); }
.vbox .obj { display: flex; gap: 8px; align-items: center; padding: 6px 10px; font-weight: 600; background: var(--line-soft); }
.vbox .obj svg { width: 15px; height: 15px; color: var(--text2); }
.vbox .obj .cnt { margin-left: auto; font-weight: 400; color: var(--muted); font-size: 12px; }
.vbox .it.sub { padding-left: 34px; }
.vbox .lvlhead { display: flex; gap: 8px; align-items: center; padding: 8px 10px 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 600; }
.vbox .lvlhead .m { font-size: 13px; text-transform: none; }
.vbox .card { margin: 0 10px 8px; background: var(--card); border: 1px solid var(--line-soft); border-radius: 6px; overflow: hidden; }
.vbox .card .it { border-bottom: 1px solid var(--line-soft); } .vbox .card .it:last-child { border-bottom: none; }
.vbox table { border-collapse: collapse; width: 100%; }
.vbox th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); padding: 5px 10px; border-bottom: 1px solid var(--line); font-weight: 600; }
.vbox td { padding: 5px 10px; border-bottom: 1px solid var(--line-soft); vertical-align: top; }
.vbox td.src { color: var(--muted); font-size: 11.5px; }
.vbox .areahead td { background: var(--line-soft); font-weight: 600; }
.vdir .note { max-width: 760px; font-size: 14px; color: var(--text2); line-height: 1.35; margin: 6px 0 0; }
.vdir .note b { color: var(--text); }
.vdir h3 { margin: 0 0 6px; font-size: 17px; }
"""

MARK = {"fail": "✘", "warn": "⚠", "info": "ℹ", "ok": "✔"}
ITEMS = [
    ("fail", "3 moduli nell'ombra del Camino 1 nel giorno di progetto", "Copertura Sud", "Posa", "DCPREV 14030/2025, 3.3.5.1",
     "Tra le 10 e le 14 del 21 dicembre l'ombra del camino copre i moduli 3:4, 3:5 e 4:4. «Correggi» li toglie dalla posa (−1,4 kWp); "
     "oppure abbassa il camino, o sposta la fila."),
    ("warn", "4 moduli non sono in nessuna stringa", "Copertura Sud", "Stringhe", "CEI 64-8/7:2024",
     "156 moduli con 12 in serie fanno 13 stringhe: ne restano 4. Cambia i moduli in serie, le stringhe per ingresso o l'inverter."),
    ("warn", "1 fila tolta per il corridoio dei Vigili del Fuoco", "Copertura Sud", "Posa", "DCPREV 14030/2025",
     "L'attività è soggetta: gruppi di 20 m al massimo con corridoi di 2 m. La seconda fila sarebbe caduta nel corridoio."),
    ("info", "74,1 kW: connessione trifase; sopra 11,08 kW la protezione di interfaccia è un relè dedicato", "Sito", "Connessione", "CEI 0-21, tab. 4", ""),
    ("info", "Prezzi e costi sono valori indicativi: inserisci quelli della bolletta e del preventivo", "Sito", "Economia", "", ""),
    ("ok", "12 moduli in serie, tutte le verifiche superate", "Copertura Sud", "Stringhe", "CEI 64-8/7:2024", ""),
    ("ok", "Uoc massima 587 V sotto i 1.000 V dell'inverter", "Copertura Nord", "Stringhe", "CEI 64-8/7:2024, B.1", ""),
]


def chead(filters: str = "") -> str:
    return (f'<div class="chead">{filters}<span class="sp"></span><span class="f on"><b style="color:var(--critical)">✘</b> 1</span>'
            f'<span class="f on"><b style="color:var(--warning-ink)">⚠</b> 2</span><span class="f on"><b style="color:var(--muted)">ℹ</b> 2</span>'
            f'<span class="f"><b style="color:var(--good)">✔</b> 2</span></div>')


def item(lv, text, src, actions: bool = True, sub: bool = False, chev: str = "›") -> str:
    act = ('<span class="act">' + ('<span class="b fix">Correggi</span>' if lv == "fail" else "") +
           f'<span class="b ico" title="Mostra nelle viste">{icon("eye", 13)}</span></span>') if actions else ""
    return (f'<div class="it {"sub" if sub else ""}"><span class="chev">{chev}</span><span class="m {lv}">{MARK[lv]}</span>'
            f'<span class="t">{html.escape(text)}</span><span class="src">{html.escape(src)}</span>{act}</div>')


def page_f() -> str:
    intro = ("<p>R13. Daniel: «è di sicuro da migliorarne il modo in cui vengono esposti tutti gli elementi perché siano più comprensibili». "
             "Il pannello Verifiche di oggi è una lista per area con il segno, la frase e la fonte; i filtri sono quattro pulsanti con i soli "
             "segni (il difetto dei filtri è nei ritocchi, passo 9). Tre direzioni, il pannello largo come nella finestra; la prima voce di ognuna "
             "è aperta per mostrare il dettaglio a richiesta.</p>")
    # F1 per oggetto
    f1 = (f'<div class="vbox"><div class="ptitle">Verifiche · 1 da correggere, 2 da controllare<span class="x">✕</span></div>'
          f'{chead("<span class=f>Per oggetto ⌄</span>")}'
          f'<div class="obj">{icon("subfield", 15)}Copertura Sud<span class="cnt">1 ✘ · 2 ⚠ · 1 ✔</span></div>'
          + item(*ITEMS[0][:2], ITEMS[0][4], sub=True, chev="⌄")
          + f'<div class="detail">{ITEMS[0][5]}</div>'
          + item(ITEMS[1][0], ITEMS[1][1], ITEMS[1][4], sub=True) + item(ITEMS[2][0], ITEMS[2][1], ITEMS[2][4], sub=True)
          + f'<div class="obj">{icon("site", 15)}Sito: Capannone Rho<span class="cnt">2 ℹ</span></div>'
          + item(ITEMS[3][0], ITEMS[3][1], ITEMS[3][4], sub=True) + item(ITEMS[4][0], ITEMS[4][1], ITEMS[4][4], sub=True)
          + f'<div class="obj">{icon("subfield", 15)}Copertura Nord<span class="cnt">1 ✔</span></div></div>')
    # F2 per livello, schede
    def lvl(lv, title, rows):
        return (f'<div class="lvlhead"><span class="m {lv}">{MARK[lv]}</span>{title}</div><div class="card">{rows}</div>')
    f2 = (f'<div class="vbox"><div class="ptitle">Verifiche<span class="x">✕</span></div>{chead("<span class=f>Per livello ⌄</span>")}'
          + lvl("fail", "Da correggere · 1", item(ITEMS[0][0], f"{ITEMS[0][2]}: {ITEMS[0][1]}", ITEMS[0][4], chev="⌄") + f'<div class="detail">{ITEMS[0][5]}</div>')
          + lvl("warn", "Da controllare · 2", item(ITEMS[1][0], f"{ITEMS[1][2]}: {ITEMS[1][1]}", ITEMS[1][4]) + item(ITEMS[2][0], f"{ITEMS[2][2]}: {ITEMS[2][1]}", ITEMS[2][4]))
          + lvl("info", "Da sapere · 2", item(ITEMS[3][0], ITEMS[3][1], ITEMS[3][4]) + item(ITEMS[4][0], ITEMS[4][1], ITEMS[4][4])) + '</div>')
    # F3 per area, tabella
    rows = ""
    for area in ("Posa", "Stringhe", "Connessione", "Economia"):
        rows += f'<tr class="areahead"><td colspan="5">{area}</td></tr>'
        for lv, text, obj, a, src, _det in ITEMS:
            if a != area:
                continue
            act = '<span class="b fix">Correggi</span>' if lv == "fail" else f'<span class="b ico">{icon("eye", 13)}</span>'
            rows += (f'<tr><td class="m {lv}">{MARK[lv]}</td><td>{html.escape(text)}</td><td>{obj}</td><td class="src">{src}</td><td>{act}</td></tr>')
    f3 = (f'<div class="vbox"><div class="ptitle">Verifiche<span class="x">✕</span></div>{chead("<span class=f>Per area ⌄</span>")}'
          f'<table><tr><th></th><th>Che cosa</th><th>Dove</th><th>Fonte</th><th></th></tr>{rows}</table></div>')
    dirs = (f'<div class="vdir"><h3>F1. Per oggetto</h3>{f1}<p class="note">Le voci <b>raggruppate per oggetto</b> (sottocampo, edificio, sito), con i '
            'conteggi nell\'intestazione; una freccia apre il <b>dettaglio</b> (che cosa, perché, che cosa fare) sotto la frase breve; a destra la fonte, '
            '«Correggi» solo dove c\'è una correzione, e l\'occhio che mostra l\'oggetto nelle viste. È il pannello Problemi di VS Code (per file) '
            'e la selezione già collegata alle viste (fase 2).</p></div>'
            f'<div class="vdir"><h3>F2. Per livello, in schede</h3>{f2}<p class="note">Prima <b>ciò che va corretto</b>, poi da controllare, da sapere, '
            'superate (chiuse per impostazione): ogni livello una scheda con il titolo in maiuscoletto. La frase porta l\'oggetto davanti. È il Review '
            'Warnings di Revit e l\'Accessibility Checker di Office (errori, avvisi, consigli). Chiaro per chi deve consegnare: si parte dall\'alto.</p></div>'
            f'<div class="vdir"><h3>F3. Per area, in tabella</h3>{f3}<p class="note">Una <b>tabella</b> con le colonne (segno, che cosa, dove, fonte, '
            'azione) e le aree come righe di intestazione (Posa, Ombre, Stringhe, Connessione…): l\'ordine di oggi, ma leggibile e ordinabile per '
            'colonna; «Vista a tabella» di VS Code. Densa, adatta alla relazione; il dettaglio a richiesta ci sta meno bene.</p></div>')
    return page("F. Il pannello Verifiche", intro, f'<div class="vrow">{dirs}</div>', F_CSS)


# ============================================================ G. Meridio

G_CSS = """
.grow { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; max-width: 1700px; }
.gbox { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
.gbox h3 { margin: 0 0 6px; font-size: 16px; }
.gbox .note { font-size: 13.5px; color: var(--text2); line-height: 1.35; margin: 8px 0 0; }
.gbox .note b { color: var(--text); }
.stage { position: relative; height: 420px; border-radius: 6px; overflow: hidden; background: linear-gradient(var(--sky-top), var(--sky-bottom)); border: 1px solid var(--line-soft); }
.stage > svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.stage .meridio { position: absolute; right: 16px; bottom: 16px; width: 46px; height: 46px; border-radius: 50%; background: var(--panel); border: 1px solid var(--line);
                  display: grid; place-items: center; box-shadow: 0 1px 4px var(--shadow); cursor: pointer; }
.stage .meridio svg { width: 34px; height: 34px; overflow: visible; }
.stage .meridio .dot { position: absolute; right: 2px; top: 2px; width: 9px; height: 9px; border-radius: 50%; background: var(--assistant); border: 1.5px solid var(--panel); }
/* G1 respiro e sguardo */
.g1 .meridio svg { animation: breathe 4s ease-in-out infinite; transform-origin: 50% 50%; }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.04); } }
.g1 .meridio .eye { transition: transform 0.25s ease-out; }
/* G2 i raggi girano piano, il disco respira */
.g2 .meridio .rays { animation: rays 60s linear infinite; transform-origin: 12px 10.2px; }
@keyframes rays { to { transform: rotate(360deg); } }
.g2 .meridio .disc { animation: glow 3s ease-in-out infinite; }
@keyframes glow { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.12); } }
/* G3 fermo, cambia solo di stato */
.g3 .meridio.think .eye { transform: translateY(-0.8px); }
.g3 .meridio .dots { display: none; } .g3 .meridio.think .dots { display: block; }
/* la chat */
.chat { position: absolute; right: 16px; bottom: 16px; width: 320px; height: 300px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
        box-shadow: 0 6px 24px var(--shadow); display: flex; flex-direction: column; overflow: hidden; transform-origin: 100% 100%; resize: both; min-width: 240px; min-height: 180px; }
.chat .head { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-bottom: 1px solid var(--line-soft); font-weight: 600; }
.chat .head svg { width: 22px; height: 22px; }
.chat .head .ctx { font-weight: 400; font-size: 11.5px; color: var(--muted); margin-left: auto; }
.chat .head .x { color: var(--muted); font-weight: 400; margin-left: 8px; cursor: pointer; }
.chat .msgs { flex: 1; padding: 8px 10px; overflow: auto; font-size: 12.5px; display: flex; flex-direction: column; gap: 6px; }
.chat .me { align-self: flex-end; background: var(--select-bg); color: var(--select-fg); padding: 5px 9px; border-radius: 10px 10px 2px 10px; max-width: 85%; }
.chat .him { align-self: flex-start; background: var(--sink); padding: 5px 9px; border-radius: 10px 10px 10px 2px; max-width: 90%; line-height: 1.35; }
.chat .him .cur { display: inline-block; width: 7px; height: 13px; background: var(--text); vertical-align: -2px; animation: blink 1s steps(2) infinite; margin-left: 1px; }
@keyframes blink { to { opacity: 0; } }
.chat .typing { display: inline-flex; gap: 4px; padding: 7px 10px; background: var(--sink); border-radius: 10px; align-self: flex-start; }
.chat .typing i { width: 6px; height: 6px; border-radius: 50%; background: var(--text2); animation: bounce 1.2s infinite; }
.chat .typing i:nth-child(2) { animation-delay: 0.2s; } .chat .typing i:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.5; } 30% { transform: translateY(-4px); opacity: 1; } }
.chat .sugg { padding: 4px 10px 6px; font-size: 12px; }
.chat .sugg .tt { color: var(--muted); font-size: 11px; margin-bottom: 3px; }
.chat .chips { display: flex; flex-wrap: wrap; gap: 5px; }
.chat .chips span { border: 1px solid var(--line); background: var(--view); border-radius: 12px; padding: 2px 9px; cursor: pointer; }
.chat .list div { display: flex; gap: 6px; align-items: center; padding: 3px 4px; border-radius: 4px; cursor: pointer; }
.chat .list div:hover { background: var(--sink); }
.chat .list div span.n { color: var(--muted); width: 14px; }
.chat .list div svg { margin-left: auto; width: 13px; height: 13px; color: var(--muted); }
.chat .in { display: flex; gap: 6px; padding: 6px 10px 8px; border-top: 1px solid var(--line-soft); align-items: center; }
.chat .in .field { flex: 1; height: 28px; border-radius: 14px; background: var(--view); border: 1px solid var(--line); padding: 0 10px; display: flex; align-items: center; color: var(--muted); }
.chat .in .send { width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: var(--accent-fg); display: grid; place-items: center; }
.chat .grip { position: absolute; left: 2px; top: 2px; color: var(--muted); font-size: 10px; cursor: nwse-resize; }
.chat.closed { display: none; }
.chat.opening { animation: pop 0.22s cubic-bezier(0.2, 0.8, 0.2, 1); }
@keyframes pop { from { transform: scale(0.15); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.chat.slide { animation: slide 0.26s cubic-bezier(0.2, 0.8, 0.2, 1); }
@keyframes slide { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.chat.closing { animation: pop 0.18s ease-in reverse; }
.chat .head .think svg { animation: spin 1.4s linear infinite; transform-origin: 50% 50%; }
@keyframes spin { to { transform: rotate(360deg); } }
.stage .meridio.hidden { display: none; }
.stage .say { position: absolute; right: 72px; bottom: 24px; background: var(--card); border: 1px solid var(--line); padding: 4px 9px; border-radius: 8px; font-size: 12px; box-shadow: 0 2px 8px var(--shadow); }
"""

G_JS = """
<script>
document.querySelectorAll('.stage').forEach(st => {
  const chat = st.querySelector('.chat'), face = st.querySelector('.meridio'), mode = st.dataset.open || 'pop';
  if (face && chat) {
    face.addEventListener('click', () => { face.classList.add('hidden'); chat.classList.remove('closed', 'closing'); chat.classList.add(mode === 'slide' ? 'slide' : 'opening'); });
    chat.querySelector('.x').addEventListener('click', () => { if (mode === 'none') { chat.classList.add('closed'); face.classList.remove('hidden'); return; }
      chat.classList.remove('opening', 'slide'); chat.classList.add('closing'); setTimeout(() => { chat.classList.add('closed'); chat.classList.remove('closing'); face.classList.remove('hidden'); }, 180); });
  }
  if (st.classList.contains('g1')) st.addEventListener('mousemove', e => { const r = face.getBoundingClientRect(); const dx = e.clientX - (r.left + r.width/2), dy = e.clientY - (r.top + r.height/2);
    const d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 300) * 0.9; st.querySelectorAll('.eye').forEach(el => el.style.transform = `translate(${k*dx/d}px, ${k*dy/d}px)`); });
  if (st.classList.contains('g3')) { let t = false; setInterval(() => { t = !t; face.classList.toggle('think', t); }, 2500); }
});
</script>
"""


def chat(sugg: str, responding: str, closed: bool = True, ctx: str = "Scheda: Modello · Selezione: Copertura Sud") -> str:
    msgs = ('<div class="me">Che ne pensi di questa disposizione?</div>'
            '<div class="him">Buona: 156 moduli complanari a sud, 19° di falda. Tre moduli finiscono nell\'ombra del camino tra le 10 e le 14 '
            'del 21 dicembre: toglierli costa 1,4 kWp e guadagna il 2 % di resa' + ('<span class="cur"></span>' if responding == "stream" else ".") + '</div>')
    if responding == "dots":
        msgs = '<div class="me">Che ne pensi di questa disposizione?</div><div class="typing"><i></i><i></i><i></i></div>'
    if sugg == "chips":
        s = '<div class="sugg"><div class="tt">Domande pronte</div><div class="chips"><span>Le distanze dai bordi vanno bene per i VVF?</span><span>Dove recupero potenza senza ombre?</span><span>Quante stringhe servono?</span></div></div>'
    elif sugg == "list":
        s = ('<div class="sugg"><div class="tt">Domande pronte</div><div class="list">' + "".join(
            f'<div>{icon("chevron", 12)}<span>{q}</span></div>' for q in ("Le distanze dai bordi vanno bene per i Vigili del Fuoco?",
                                                                          "Dove recupero potenza senza ombre?", "Quante stringhe servono con questo inverter?")) + '</div></div>')
    else:
        s = ('<div class="sugg"><div class="tt">Domande pronte · premi 1, 2, 3</div><div class="list">' + "".join(
            f'<div><span class="n">{i + 1}</span><span>{q}</span>{icon("send", 12)}</div>' for i, q in enumerate(("Le distanze dai bordi vanno bene per i VVF?",
                                                                                                                 "Dove recupero potenza senza ombre?", "Quante stringhe servono?"))) + '</div></div>')
    head_face = P.meridio_svg(22, thinking=responding == "dots", cls="")
    think = f'<span class="think">{head_face}</span>' if responding == "dots" else head_face
    return (f'<div class="chat {"closed" if closed else ""}"><span class="grip">{icon("resize", 10)}</span><div class="head">{think}Meridio'
            f'<span class="ctx">{ctx}</span><span class="x">✕</span></div><div class="msgs">{msgs}</div>{s}'
            f'<div class="in"><div class="field">Chiedi a Meridio… (Ctrl+L)</div><span class="send">{icon("send", 14)}</span></div></div>')


def page_g() -> str:
    intro = ("<p>R15. Daniel: «sarà da migliorarne l'estetica, renderlo magari dinamico, e migliorare anche l'estetica della chat con qualche "
             "animazione in apertura / chiusura, mentre sta parlando l'assistenza, possibilità di ridimensionare la chat, vista delle risposte "
             "consigliate più chiara con elenco». Tre scene: <b>clicca Meridio</b> per aprire la chat (ogni scena con la sua animazione), "
             "<b>trascina l'angolo in basso a destra</b> della chat per ridimensionarla, muovi il mouse nella prima scena per lo sguardo. "
             "Con «meno movimento» del sistema tutto resta fermo (<code>prefers-reduced-motion</code> qui, la preferenza letta dal portale in Meridiana).</p>")
    def face(cls=""):
        return f'<div class="meridio {cls}">{P.meridio_svg(34)}<span class="dot"></span></div>'
    g1 = (f'<div class="gbox"><h3>G1. Respiro e sguardo · apertura dall\'angolo · puntini · domande come elenco</h3>'
          f'<div class="stage g1" data-open="pop">{P.view3d_svg(False)}{face("hidden")}{chat("list", "dots", closed=False)}</div>'
          '<p class="note">Il personaggio <b>respira</b> (scala 1 → 1,04 in 4 s) e gli <b>occhi seguono il mouse</b> di un pixel; «pensa» alza gli '
          'occhi e mostra i tre puntini. La chat si <b>apre dall\'angolo</b> del personaggio in 220 ms (scala e dissolvenza) e si chiude al contrario; '
          'mentre risponde, <b>tre puntini</b> nel fumetto e il personaggio in testa che gira piano. Le domande pronte come <b>elenco</b> con la freccia. '
          'Il bordo in basso a destra ridimensiona.</p></div>')
    g2 = (f'<div class="gbox"><h3>G2. I raggi girano · scivola dal basso · testo che scorre · domande come pastiglie</h3>'
          f'<div class="stage g2" data-open="slide">{P.view3d_svg(False)}{face()}{chat("chips", "stream")}</div>'
          '<p class="note">I <b>raggi girano</b> in un minuto e il disco pulsa appena: si vede che è vivo senza muoversi. La chat <b>scivola dal basso</b> '
          'in 260 ms; mentre risponde il testo <b>arriva parola per parola</b> con il cursore (come le chat dei modelli). Le domande pronte come '
          '<b>pastiglie</b> (chips): compatte, ma con frasi lunghe vanno a capo.</p></div>')
    g3 = (f'<div class="gbox"><h3>G3. Fermo, cambia solo di stato · nessuna animazione · numerate</h3>'
          f'<div class="stage g3" data-open="none">{P.view3d_svg(False)}{face()}{chat("numbered", "none")}</div>'
          '<p class="note">Il personaggio <b>non si muove</b>: cambia espressione per stato (ogni 2,5 s qui «pensa»), il puntino nel suo colore dice '
          'che ha un parere. La chat appare e sparisce <b>senza animazione</b>; le domande pronte <b>numerate</b> si scelgono con 1, 2, 3. '
          'È quello che resta quando il sistema chiede meno movimento: la base su cui G1 e G2 aggiungono.</p></div>')
    return page("G. Meridio e la sua chat", intro, f'<div class="grow">{g1}{g2}{g3}</div>', G_CSS, G_JS)
