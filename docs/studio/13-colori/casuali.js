const { lch, hexOf, contrast, nearest, derive } = require('./colori.js');
const protect = (hex, darker) => { const q = lch(hex); let L = q[0], C = q[1], out = hex, n = 0;
  while (nearest(out).d < 0.15 && n < 14) { if (darker) { L -= 0.03; C *= 0.94; } else { L = Math.min(0.97, L + 0.02); C *= 0.8; } out = hexOf(L, C, q[2]); n++; } return out; };
// theme_colors.MERIDIANA_LIGHT and MERIDIANA_DARK (the floors of study 17, A.5)
const MER = { light: { window: '#f2f1ed', panel: '#f8f7f4', view: '#ffffff', line: '#d9d5cc', text: '#1e1c19', text2: '#514c44', muted: '#6f685d', plan: {}, d3: {}, chart: {} },
  dark: { window: '#151515', panel: '#252525', view: '#1c1c1c', line: '#404040', text: '#ededed', text2: '#c4c4c4', muted: '#9b9b9b', plan: {}, d3: {}, chart: {} } };
let seedX = 12345; const rnd = () => { seedX = (seedX * 1103515245 + 12345) % 2147483648; return seedX / 2147483648; };
const fails = {}; const worst = {};
const note = (k, v, s) => { if (worst[k] === undefined || v < worst[k][0]) worst[k] = [v, s]; };
for (let i = 0; i < 2000; i++) {
  const s = '#' + [0, 1, 2].map(() => Math.floor(rnd() * 256).toString(16).padStart(2, '0')).join('');
  for (const fondi of ['meridiana', 'colore', 'grigi']) for (const dark of [false, true]) {
    const r = derive(s, dark, fondi, dark ? MER.dark : MER.light); const t = r.t;
    const asst = protect(hexOf(dark ? 0.8 : 0.42, 0.06, (lch(s)[2] + 180) % 360), !dark);
    const m = dark ? 'scuro' : 'chiaro';
    const checks = [['testo sull accento ' + m, contrast(t.accent, t.accent_fg), 4.5], ['accento sulla vista ' + m, contrast(t.accent, t.view), 4.5],
      ['attenuato sui pannelli ' + m, contrast(t.muted, t.panel), 4.5], ['testo sulla selezione ' + m, contrast(t.text, t.select_bg), 7],
      ['distanza accento-stati ' + m, nearest(t.accent).d, 0.15], ['distanza assistente-stati ' + m, nearest(asst).d, 0.15],
      ['assistente sul fondo ' + m, contrast(asst, dark ? t.window : '#ffffff'), 4.5], ['distanza modulo sel.-stati ' + m, nearest(t.d3.module_sel).d, 0.15],
      // studio 17 (compito 17a, passo 1): i piani e i controlli
      [dark ? 'scheda sulla finestra scuro' : 'finestra sui pannelli chiaro', dark ? contrast(t.card, t.window) : contrast(t.window, t.panel), 1.12],
      ['scheda sul pannello ' + m, contrast(t.card, t.panel), 1.10], ['bordo del campo sul pannello ' + m, contrast(t.field_line, t.panel), 3.0],
      ['bordo del campo sul campo ' + m, contrast(t.field_line, t.field), 3.0], ['attenuato sulla finestra ' + m, contrast(t.muted, t.window), 4.5],
      ['attenuato sulla scheda ' + m, contrast(t.muted, t.card), 4.5], ['errore sul campo ' + m, contrast(t.danger, t.field), 4.5]];
    for (const [k, v, min] of checks) { note(k, v, s + ' ' + fondi); if (v < min) fails[k] = (fails[k] || 0) + 1; }
  }
}
console.log('fallimenti su 2000 semi x 3 fondi x 2 temi:', JSON.stringify(fails));
for (const k of Object.keys(worst).sort()) console.log(k.padEnd(34), 'peggiore', worst[k][0].toFixed(3), worst[k][1]);
for (const s of ['#c88800', '#ffc057', '#e5a50a']) {
  const a = derive(s, false, 'meridiana', MER.light), b = derive(s, true, 'meridiana', MER.dark);
  console.log('seme', s, 'chiaro', a.t.accent, contrast(a.t.accent, '#ffffff').toFixed(1), 'vicino:', a.report.near || '-', '| scuro', b.t.accent, contrast(b.t.accent, '#101318').toFixed(1), 'vicino:', b.report.near || '-', 'dStat', nearest(b.t.accent).d.toFixed(2));
}
