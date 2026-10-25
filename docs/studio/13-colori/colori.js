// Theme from one seed colour, in OKLCH. Same code goes into Finestra.dc.html.
const toLin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
const fromLin = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
const hexRgb = (hex) => { const h = hex.replace('#', '').slice(0, 6); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255); };
const lab = (hex) => {
  const [r, g, b] = hexRgb(hex).map(toLin);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
};
const lch = (hex) => { const q = lab(hex); return [q[0], Math.hypot(q[1], q[2]), (Math.atan2(q[2], q[1]) * 180 / Math.PI + 360) % 360]; };
const linOf = (L, C, h) => {
  const a = C * Math.cos(h * Math.PI / 180), b = C * Math.sin(h * Math.PI / 180);
  const l = Math.pow(L + 0.3963377774 * a + 0.2158037573 * b, 3), m = Math.pow(L - 0.1055613458 * a - 0.0638541728 * b, 3), s = Math.pow(L - 0.0894841775 * a - 1.291485548 * b, 3);
  return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
};
const inGamut = (v) => v.every((x) => x >= -0.0005 && x <= 1.0005);
const hexOf = (L, C, h) => {
  let c = C;
  if (!inGamut(linOf(L, c, h))) {
    let lo = 0, hi = c;
    for (let i = 0; i < 18; i++) { const mid = (lo + hi) / 2; if (inGamut(linOf(L, mid, h))) lo = mid; else hi = mid; }
    c = lo;
  }
  return '#' + linOf(L, c, h).map((x) => Math.round(Math.max(0, Math.min(1, fromLin(Math.max(0, Math.min(1, x))))) * 255).toString(16).padStart(2, '0')).join('');
};
const lum = (hex) => { const [r, g, b] = hexRgb(hex).map(toLin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const contrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
const dE = (a, b) => { const p = lab(a), q = lab(b); return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]); };

const STATUS = { warning: '#fab219', critical: '#d03b3b', good: '#0ca30c' };
const NEAR = 0.15;
const nearest = (hex) => Object.keys(STATUS).reduce((best, k) => { const d = dE(hex, STATUS[k]); return d < best.d ? { k: k, d: d } : best; }, { k: '', d: 9 });
// Moves a colour away from the status colours: darker in the light theme, lighter in the dark one, and less vivid.
const protect = (hex, darker) => {
  let [L, C, h] = lch(hex), out = hex, n = 0;
  while (nearest(out).d < NEAR && n < 14) { if (darker) { L -= 0.03; C *= 0.94; } else { L = Math.min(0.97, L + 0.02); C *= 0.8; } out = hexOf(L, C, h); n++; }
  return { hex: out, moved: n > 0 };
};

// a towards b by t, in sRGB as Qt mixes the colours of a palette (theme_colors.mix)
const mix = (a, b, t) => { const p = hexRgb(a), q = hexRgb(b); return '#' + p.map((x, i) => Math.round((x + (q[i] - x) * t) * 255).toString(16).padStart(2, '0')).join(''); };

// Study 17 (A.5, C.5): card lifted over the panel in the dark theme (the view's white in the light one), field the
// tonal veil, field_line a border at 3:1 or more from the panel and the field, accent_hover, danger readable on a field.
const CARD_VEIL = 0.0, FIELD_VEIL = [0.06, 0.22], LINE_CONTRAST = 3.0;
const surfaces = (t, dark) => {
  if (dark) { t.card = mix(t.panel, '#ffffff', CARD_VEIL); t.field = mix(t.panel, '#000000', FIELD_VEIL[1]); }
  else { t.card = t.view; t.field = mix(t.panel, t.text, FIELD_VEIL[0]); }
  let [L, C, h] = lch(t.line);
  L = dark ? 0.54 : 0.58;
  let line = hexOf(L, C, h);
  while (Math.min(contrast(line, t.panel), contrast(line, t.field)) < LINE_CONTRAST + 0.05 && L > 0.2 && L < 0.9) { L += dark ? 0.01 : -0.01; line = hexOf(L, C, h); }
  t.field_line = line;
  t.accent_hover = mix(t.accent, dark ? '#ffffff' : t.text, 0.12);
  t.card_line = t.line;
  [L, C, h] = lch(STATUS.critical);
  L = dark ? 0.72 : L;
  let danger = hexOf(L, C, h);
  while (contrast(danger, t.field) < 4.5 && L > 0.2 && L < 0.95) { L += dark ? 0.01 : -0.01; danger = hexOf(L, C, h); }
  t.danger = danger;
};

// base: the direction's tokens for this mode; fondi: 'meridiana' | 'colore' | 'grigi'
const derive = (seed, dark, fondi, base) => {
  const [L0, C0, h] = lch(seed);
  const t = Object.assign({}, base, { plan: Object.assign({}, base.plan), d3: Object.assign({}, base.d3), chart: Object.assign({}, base.chart) });
  if (fondi === 'colore' || fondi === 'grigi') {
    const k = fondi === 'grigi' ? 0 : 1;
    const N = (L, C) => hexOf(L, C * k, h);
    if (!dark) {
      Object.assign(t, { window: N(0.957, 0.008), panel: N(0.978, 0.005), view: '#ffffff', header: N(0.957, 0.008), card: '#ffffff', line: N(0.872, 0.013), line_soft: N(0.926, 0.01),
        text: N(0.235, 0.012), text2: N(0.43, 0.016), muted: N(0.515, 0.016), tooltip_bg: N(0.235, 0.012), tooltip_fg: N(0.978, 0.005) });
      Object.assign(t.plan, { bg: N(0.988, 0.003), grid: N(0.935, 0.008), bld_stroke: N(0.32, 0.012), bld_fill: N(0.32, 0.012) + '0d', ink: N(0.32, 0.012), label_bg: t.text + 'e6', label_fg: t.panel, pitch: N(0.6, 0.014) });
      Object.assign(t.chart, { surface: '#ffffff', grid: N(0.93, 0.007), axis: N(0.83, 0.01) });
    } else {
      Object.assign(t, { window: N(0.196, 0.012), panel: N(0.265, 0.013), view: N(0.226, 0.011), header: N(0.196, 0.012), card: N(0.265, 0.013), line: N(0.372, 0.015), line_soft: N(0.321, 0.013),
        text: N(0.946, 0.008), text2: N(0.82, 0.012), muted: N(0.69, 0.014), tooltip_bg: N(0.946, 0.008), tooltip_fg: N(0.196, 0.012) });
      Object.assign(t.plan, { bg: t.view, grid: N(0.262, 0.012), bld_stroke: N(0.86, 0.01), bld_fill: N(0.86, 0.01) + '0d', ink: N(0.86, 0.01), label_bg: N(0.15, 0.01) + 'e6', label_fg: t.text, halo: N(0.13, 0.01), pitch: N(0.66, 0.014) });
      Object.assign(t.chart, { surface: t.view, grid: N(0.275, 0.01), axis: N(0.38, 0.012) });
    }
  }
  let L = dark ? Math.max(L0, 0.82) : Math.min(L0, 0.6);
  const C = dark ? Math.min(C0, 0.11) : Math.min(C0, 0.17);
  let acc = hexOf(L, C, h);
  if (!dark) { while (contrast(acc, '#ffffff') < 4.6 && L > 0.2) { L -= 0.01; acc = hexOf(L, C, h); } }
  else { while (contrast(acc, t.view) < 7 && L < 0.97) { L += 0.01; acc = hexOf(L, C, h); } }
  const near = nearest(acc);
  const pa = protect(acc, !dark);
  acc = pa.hex;
  const fg = dark ? t.window : '#ffffff';
  const selBg = dark ? hexOf(0.34, Math.min(0.05, C0 * 0.45 + 0.01), h) : hexOf(0.925, Math.min(0.055, C0 * 0.5 + 0.01), h);
  const modSel = dark ? acc : protect(hexOf(0.88, Math.min(0.09, C0), h), false).hex;
  Object.assign(t, { accent: acc, accent_fg: fg, accent_soft: acc + (dark ? '24' : '20'), select_bg: selBg, select_fg: t.text, assistant: acc });
  Object.assign(t.plan, { sub_stroke: acc, sub_fill: acc + (dark ? '12' : '14'), sel: acc });
  t.d3.module_sel = modSel;
  surfaces(t, dark);
  const report = { onAccent: contrast(acc, fg), onView: contrast(acc, t.view), onWindow: contrast(acc, t.window), near: pa.moved ? near.k : '', dStatus: nearest(acc).d,
    selText: contrast(t.text, selBg), muted: contrast(t.muted, t.panel), text2: contrast(t.text2, t.panel), modSelStatus: nearest(modSel).d };
  return { t: t, report: report };
};

module.exports = { lch, hexOf, contrast, dE, derive, nearest, mix, STATUS };
