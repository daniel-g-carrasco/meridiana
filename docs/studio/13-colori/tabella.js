// Markdown table of the ready-made colours for docs/studio/13, fondi "meridiana".
const { lch, hexOf, contrast, nearest, derive } = require('./colori.js');
const protect = (hex, darker) => { const q = lch(hex); let L = q[0], C = q[1], out = hex, n = 0;
  while (nearest(out).d < 0.15 && n < 14) { if (darker) { L -= 0.03; C *= 0.94; } else { L = Math.min(0.97, L + 0.02); C *= 0.8; } out = hexOf(L, C, q[2]); n++; } return out; };
const base = (dark) => (dark ? { window: '#151515', panel: '#252525', view: '#1c1c1c', line: '#404040', text: '#ededed', text2: '#c4c4c4', muted: '#9b9b9b', plan: {}, d3: {}, chart: {} }
  : { window: '#f2f1ed', panel: '#f8f7f4', view: '#ffffff', line: '#d9d5cc', text: '#1e1c19', text2: '#514c44', muted: '#6f685d', plan: {}, d3: {}, chart: {} });
const NEAR = { warning: 'avviso', critical: 'errore', good: 'superata' };
const P = [['Sistema (Windows)', '#0078d4'], ['Sistema (Lucciola, GNOME giallo)', '#c88800'], ['Bronzo, di partenza', '#8b5a12'], ['Cotto', '#a4482b'], ['Oliva', '#5f6b1f'], ['Bosco', '#2f6b4f'],
  ['Petrolio', '#1f6a7a'], ['Blu', '#2a5ea8'], ['Indaco', '#5b4bb0'], ['Prugna', '#8a3a6e'], ['Grafite', '#4a4f57']];
const f = (x) => x.toFixed(1).replace('.', ',');
console.log('| Colore | Scelto | Accento chiaro (bianco sopra) | Accento scuro (sul fondo) | Assistente chiaro / scuro | Ritoccato |');
console.log('|---|---|---|---|---|---|');
for (const [n, s] of P) {
  const a = derive(s, false, 'meridiana', base(false)), b = derive(s, true, 'meridiana', base(true));
  const h = (lch(s)[2] + 180) % 360, al = protect(hexOf(0.42, 0.06, h), true), ad = protect(hexOf(0.8, 0.06, h), false);
  const r = [a.report.near ? 'chiaro, dall\'' + NEAR[a.report.near] : '', b.report.near ? 'scuro, dall\'' + NEAR[b.report.near] : ''].filter(Boolean).join('; ') || '-';
  console.log('| ' + n + ' | ' + s + ' | ' + a.t.accent + ' (' + f(contrast(a.t.accent, '#ffffff')) + ':1) | ' + b.t.accent + ' (' + f(contrast(b.t.accent, '#101318')) + ':1) | ' + al + ' / ' + ad + ' | ' + r + ' |');
}
