"""Drafts of the other phases (Daniel, 24/10/2026: «fai dei draft anche delle altre fasi di progettazione»), in the
language of the target (bersaglio.py): the same frame, cards, tiles (R2), groups (C3), fields (C2), checks (F2).
One idea for every phase: the results in front, in the card in the middle; what is typed in the right column, as
the Properties of the model; the charts in a card of their own with their tabs (D2). The figures are those of the
sample project (the shed in Rho, 188 modules, 93 kWp) as the program computes them on 24/10/2026.

    python docs/studio/19-grafica/fasi.py          -> fasi-<phase>-chiaro.html, fasi-<phase>-scuro.html"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "17-prove"))

import bersaglio as B  # noqa: E402
import genera as G  # noqa: E402
import parti as P  # noqa: E402

P.ICONS.update({
    "zap": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "wand": '<path d="M15 4V2M15 10V8M11 6h2M17 6h2M4 20L14 10"/><path d="M19 13v2M18 14h2"/>',
    "spline": '<circle cx="5" cy="19" r="2"/><circle cx="19" cy="5" r="2"/><path d="M5 17C5 9 19 15 19 7"/>',
    "route": '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H17a3.5 3.5 0 000-7H7a3.5 3.5 0 010-7h8.5"/>',
    "refresh": '<path d="M20 11a8 8 0 10-2.3 5.7M20 4v7h-7"/>',
    "play": '<path d="M7 4l13 8-13 8z"/>',
    "cloud": '<path d="M7 18a5 5 0 01-.6-10A6 6 0 0118 9a4 4 0 01-1 9"/><path d="M12 12v8M9 17l3 3 3-3"/>',
    "compare": '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M6 8.5V15a3 3 0 003 3h6.5M18 15.5V9a3 3 0 00-3-3H8.5"/>',
    "file-in": '<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4M8 14h7M12 11l3 3-3 3"/>',
    "sliders": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "battery": '<rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 11v2M10 9l-2 3h4l-2 3"/>',
    "doc": '<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    "copy-plus": '<rect x="8" y="8" width="12" height="13" rx="1"/><path d="M4 16V4h12M14 12v5M11.5 14.5h5"/>',
    "clip": '<rect x="6" y="4" width="12" height="17" rx="1"/><path d="M9 4V3h6v1M9 11h6M9 15h4"/>',
})

PHASE_CSS = """
.mock .pane.page { display: block; padding: 14px 16px; overflow: hidden; }
.mock .tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.mock .tiles.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.mock .tile { background: var(--sink); border-radius: 8px; padding: 10px 14px 11px; min-width: 0; }
.mock .tile.key { background: var(--accent-soft); }
.mock .tile .l { font-size: 12.5px; color: var(--text2); display: flex; justify-content: space-between; }
.mock .tile .l i { font-style: normal; color: var(--muted); border: 1px solid var(--line); border-radius: 50%;
                   width: 15px; height: 15px; display: inline-grid; place-items: center; font-size: 10px; }
.mock .tile .v { font-size: 24px; font-weight: 600; line-height: 1.25; margin-top: 2px; }
.mock .tile .v small { font-size: 12.5px; font-weight: 400; color: var(--muted); margin-left: 3px; }
.mock .tile .d { font-size: 12px; color: var(--muted); margin-top: 1px; }
.mock .tile .bar3 { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin: 8px 0 4px; gap: 2px; }
.mock .tile .bar3 b { display: block; }
.mock .sect { margin: 14px 0 6px; font-size: 11px; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted);
              font-weight: 600; display: flex; gap: 10px; align-items: baseline; }
.mock .sect span { text-transform: none; letter-spacing: 0; font-weight: 400; }
.mock .chartcard { border: 1px solid var(--line-soft); border-radius: 8px; margin-top: 10px; overflow: hidden; }
.mock .chartcard .ct { display: flex; align-items: center; gap: 2px; padding: 6px 8px; border-bottom: 1px solid var(--line-soft); }
.mock .chartcard .ct span { padding: 3px 10px; border-radius: 6px; color: var(--text2); font-size: 13px; }
.mock .chartcard .ct span.on { background: var(--select-bg); color: var(--select-fg); font-weight: 600; }
.mock .chartcard .ct .sp { flex: 1; }
.mock .chartcard .ct a { color: var(--accent); font-size: 12.5px; font-weight: 600; padding: 0 6px; }
.mock .chartcard .cb { padding: 10px 14px 8px; }
.mock .chartcard .cb h5 { margin: 0 0 4px; font-size: 13px; font-weight: 600; }
.mock .chartcard svg { display: block; width: 100%; }
.mock .strip { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 12.5px; color: var(--text2);
               background: var(--sink); border-radius: 8px; padding: 7px 12px; margin-top: 10px; }
.mock .strip b { color: var(--text); }
.mock .strip .sp { flex: 1; }
.mock .strip a { color: var(--accent); font-weight: 600; }
.mock .chip { display: inline-flex; align-items: center; gap: 5px; padding: 2px 10px; border-radius: 11px; font-size: 12px;
              border: 1px solid var(--line); color: var(--text2); background: var(--panel); white-space: nowrap; }
.mock .chip.on { background: var(--select-bg); color: var(--select-fg); border-color: var(--line); }
.mock .chip.warn { border-color: transparent; background: var(--warning-ink); color: #fff; }
.mock .chip.ok { border-color: transparent; background: var(--good); color: #fff; }
.mock .chip.muted { border-color: transparent; background: var(--line-soft); color: var(--muted); }
.mock .rlist { padding: 0 12px 10px; font-size: 13px; }
.mock .rlist .r { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 10px; padding: 5px 0;
                  border-bottom: 1px solid var(--line-soft); align-items: center; }
.mock .rlist .r:last-child { border-bottom: none; }
.mock .rlist .r .n { color: var(--text2); }
.mock .rlist .r .q { font-weight: 600; text-align: right; }
.mock .rlist .r .bar { grid-column: 1 / -1; height: 5px; border-radius: 3px; background: var(--line-soft); overflow: hidden; }
.mock .rlist .r .bar b { display: block; height: 100%; background: var(--muted); border-radius: 3px; }
.mock .rlist .r.warn .q { color: var(--warning-ink); }
.mock .rlist .r.warn .bar b { background: var(--warning-ink); }
.mock .rlist .r.total { border-top: 1px solid var(--line); }
.mock .side-tiles { padding: 2px 12px 10px; display: grid; gap: 8px; }
.mock .inv { background: var(--sink); border-radius: 8px; padding: 10px 12px; display: grid; grid-template-columns: 1fr auto;
             gap: 2px 8px; font-size: 13px; }
.mock .inv b { font-size: 14px; }
.mock .inv .s { color: var(--muted); font-size: 12px; grid-column: 1; }
.mock .inv .qty { grid-row: 1 / 3; grid-column: 2; display: flex; align-items: center; gap: 6px; }
.mock .inv .qty .field { width: 64px; background: var(--panel); }
.mock .gauge { position: relative; height: 10px; border-radius: 5px; background: var(--line-soft); margin: 6px 0 2px; }
.mock .gauge .band { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--good) 35%, transparent); border-radius: 5px; }
.mock .gauge .pin { position: absolute; top: -4px; width: 4px; height: 18px; border-radius: 2px; background: var(--warning-ink); }
.mock .gl { display: flex; justify-content: space-between; font-size: 11.5px; color: var(--muted); }
.mock .mppt { display: grid; grid-template-columns: 62px minmax(0, 1fr); gap: 4px 8px; padding: 6px 0; border-bottom: 1px solid var(--line-soft);
              font-size: 12.5px; align-items: center; }
.mock .mppt:last-child { border-bottom: none; }
.mock .mppt .k { font-weight: 600; }
.mock .mppt .ss { display: flex; gap: 4px; flex-wrap: wrap; }
.mock .mppt .note { grid-column: 2; color: var(--muted); font-size: 11.5px; }
.mock .sc { display: inline-flex; align-items: center; gap: 4px; padding: 1px 8px 1px 5px; border-radius: 10px; font-size: 12px;
            background: var(--sink); }
.mock .sc i { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.mock .sc .okm { color: var(--good); font-weight: 700; }
.mock .planbox { position: relative; height: 520px; border-radius: 6px; overflow: hidden; margin-top: 10px; background: var(--plan-bg); }
.mock .planbox svg { width: 100%; height: 100%; display: block; }
.mock .twocol { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 16px; }
.mock .outline { border: 1px solid var(--line-soft); border-radius: 8px; overflow: hidden; }
.mock .outline .o { display: flex; align-items: center; gap: 10px; padding: 7px 12px; border-bottom: 1px solid var(--line-soft); font-size: 13px; }
.mock .outline .o:last-child { border-bottom: none; }
.mock .outline .o .num { color: var(--muted); width: 18px; }
.mock .outline .o .t { flex: 1; }
.mock .outline .o .p { color: var(--muted); font-size: 12px; }
.mock .paper { background: #ffffff; border: 1px solid var(--line); border-radius: 4px; aspect-ratio: 210 / 297; padding: 16px 18px;
               box-shadow: 0 2px 8px var(--shadow); color: #1e1c19; font-size: 7px; line-height: 1.5; }
.mock .paper .hb { height: 6px; background: #8b5a12; border-radius: 2px; width: 40%; margin-bottom: 10px; }
.mock .paper h6 { font-size: 11px; margin: 0 0 6px; }
.mock .paper .ln { height: 4px; background: #e8e5de; border-radius: 2px; margin: 4px 0; }
.mock .paper .ln.s { width: 70%; }
.mock .paper .fig { height: 60px; background: #f2f1ed; border-radius: 3px; margin: 8px 0; display: grid; place-items: center; color: #8a857c; }
.mock .deliv { padding: 2px 12px 10px; display: grid; gap: 8px; }
.mock .deliv .d { background: var(--sink); border-radius: 8px; padding: 9px 12px; display: grid; grid-template-columns: 1fr auto; gap: 2px 8px;
                  font-size: 13px; align-items: center; }
.mock .deliv .d b { font-size: 13.5px; }
.mock .deliv .d .s { color: var(--muted); font-size: 12px; }
.mock .heat { display: grid; grid-template-columns: 34px repeat(24, minmax(0, 1fr)); gap: 2px; font-size: 10px; color: var(--muted); }
.mock .heat i { display: block; height: 12px; border-radius: 2px; }
.mock .heat .m { line-height: 12px; }
.mock .head-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.mock .head-row h3 { margin: 0; font-size: 16px; font-weight: 600; }
.mock .head-row .sp { flex: 1; }
.mock .prim { display: inline-flex; align-items: center; height: 30px; padding: 0 16px; border-radius: 6px; font-weight: 600;
              background: var(--accent); color: var(--accent-fg); }
.mock .form2 { display: grid; grid-template-columns: 1fr 150px; gap: 5px 8px; align-items: center; padding: 0 8px 8px; font-size: 13px; }
.mock .form2 label { color: var(--text2); }
"""

PHASES = ["model", "plant", "production", "consumption", "economics", "report"]


def tools_html(groups, on: str = "", primary: str = "") -> str:
    out = []
    for label, items in groups:
        tbs = "".join(f'<div class="tb {"on" if name == on else ""} {"prim-tb" if name == primary else ""}">{P.icon(key, 22)}'
                      f'<span>{name}</span></div>' for key, name in items)
        out.append(f'<div class="grp"><div class="gi">{tbs}</div><div class="gl">{label}</div></div>')
    return '<div class="tools">' + '<div class="sep"></div>'.join(out) + "</div>"


TOOLS_EXTRA_CSS = """
.mock .tools .tb.prim-tb { background: var(--accent); color: var(--accent-fg); }
"""


def card(title: str, body: str, icon: str = "", cls: str = "") -> str:
    ic = P.icon(icon, 15) if icon else ""
    return f'<div class="pane {cls}"><div class="ptitle">{ic}{title}<span class="x">✕</span></div>{body}</div>'


def group(title: str, body: str) -> str:
    return f'<div class="group"><div class="gt">{title}</div>{body}</div>'


def tile(label, value, unit="", detail="", key=False, extra="") -> str:
    u = f"<small>{unit}</small>" if unit else ""
    d = f'<div class="d">{detail}</div>' if detail else ""
    return (f'<div class="tile {"key" if key else ""}"><div class="l"><span>{label}</span><i>?</i></div>'
            f'<div class="v">{value}{u}</div>{extra}{d}</div>')


def help_card(title: str, text: str, how: bool = True) -> str:
    links = '<a>Manuale ›</a>' + ('<a>Come è calcolato ›</a>' if how else "") + '<a>Chiedi a Meridio ›</a>'
    return (f'<div class="pane help-card"><div class="ptitle">{P.icon("book", 15)}Aiuto<span class="x">✕</span></div>'
            f'<div class="hb"><b>{title}</b>{text}<div class="links">{links}</div></div></div>')


def window(active: int, tools: str, centre: str, right: str) -> str:
    left = f'<div class="pane left"><div class="ptitle">Progetto<span class="x">✕</span></div>{G.tree_sections()}</div>'
    return (f'<div class="frame"><div class="mock">{B.tabs(active)}{tools}'
            f'<div class="body">{left}<div class="pane centre page">{centre}</div><div class="rcol">{right}</div>{B.checks()}</div>'
            f'{P.statusbar()}{P.meridio_badge()}</div></div>')


# ---- charts, drawn as SVG on the theme's variables

MONTHS = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
PROD = [3.9, 5.6, 8.6, 10.7, 12.6, 13.1, 13.4, 12.0, 9.4, 7.0, 4.4, 3.4]      # MWh, 107 MWh a year
# the series in the charts' slot 1, blue as D2 (study 17) and the program: the accent is for the interface
CONS = [9.6, 8.8, 9.1, 8.6, 8.9, 9.0, 9.4, 7.1, 8.8, 9.2, 9.3, 9.3]


def bars(values, other=None, w=1060, h=230, unit="MWh", hover=6, name="Produzione", other_name="Consumi") -> str:
    top = max(max(values), max(other or [0])) * 1.15
    left, base = 44, h - 26
    step = (w - left - 10) / len(values)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{name} mese per mese">']
    for k in range(0, 5):
        y = base - (base - 10) * k / 4
        out.append(f'<line x1="{left}" x2="{w - 10}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--line-soft)"/>'
                   f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{top * k / 4:.0f}</text>')
    bw = step * (0.34 if other else 0.56)
    for i, v in enumerate(values):
        x = left + step * i + step * (0.14 if other else 0.22)
        hgt = (base - 10) * v / top
        out.append(f'<rect x="{x:.1f}" y="{base - hgt:.1f}" width="{bw:.1f}" height="{hgt:.1f}" rx="3" fill="#2e6fb0"'
                   f'{" opacity=\"0.55\"" if hover is not None and i != hover else ""}/>')
        if other:
            o = (base - 10) * other[i] / top
            out.append(f'<rect x="{x + bw + 2:.1f}" y="{base - o:.1f}" width="{bw:.1f}" height="{o:.1f}" rx="3" fill="var(--muted)" opacity="0.6"/>')
        out.append(f'<text x="{left + step * i + step / 2:.1f}" y="{h - 8}" text-anchor="middle" font-size="11" fill="var(--muted)">{MONTHS[i]}</text>')
    if hover is not None:
        x = left + step * hover + step / 2
        v = values[hover]
        lines = [f"{name}: {v * 1000:,.0f} kWh".replace(",", ".")]
        if other:
            lines.append(f"{other_name}: {other[hover] * 1000:,.0f} kWh".replace(",", "."))
        tw = 190
        out.append(f'<g><rect x="{x + 14:.1f}" y="18" width="{tw}" height="{22 + 17 * len(lines)}" rx="6" fill="var(--tooltip-bg)"/>'
                   f'<text x="{x + 26:.1f}" y="36" font-size="12" font-weight="600" fill="var(--tooltip-fg)">luglio</text>'
                   + "".join(f'<text x="{x + 26:.1f}" y="{53 + 17 * j}" font-size="12" fill="var(--tooltip-fg)">{t}</text>'
                             for j, t in enumerate(lines)) + "</g>")
    out.append(f'<text x="{left}" y="10" font-size="11" fill="var(--muted)">{unit}</text></svg>')
    return "".join(out)


def cashflow(w=1060, h=230) -> str:
    # cumulative cash flow, 20 years: -121 k€ at year 0, payback at 6.6
    years = list(range(0, 21))
    cum = [-121.0 + 18.3 * y - 0.12 * y * y for y in years]
    lo, hi = -130, 260
    left, base_top, base_bot = 50, 12, h - 26

    def Y(v):
        return base_bot - (base_bot - base_top) * (v - lo) / (hi - lo)

    def X(y):
        return left + (w - left - 14) * y / 20
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Flusso di cassa cumulato">']
    for v in (-100, 0, 100, 200):
        out.append(f'<line x1="{left}" x2="{w - 14}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{"var(--line)" if v == 0 else "var(--line-soft)"}"/>'
                   f'<text x="{left - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)">{v}</text>')
    for y in years:
        v = cum[y]
        top, bot = (Y(v), Y(0)) if v >= 0 else (Y(0), Y(v))
        out.append(f'<rect x="{X(y) - 9:.1f}" y="{top:.1f}" width="18" height="{max(1, bot - top):.1f}" rx="2" '
                   f'fill="{"var(--accent)" if v >= 0 else "var(--critical)"}" opacity="{0.85 if v >= 0 else 0.55}"/>')
        if y % 2 == 0:
            out.append(f'<text x="{X(y):.1f}" y="{h - 8}" text-anchor="middle" font-size="11" fill="var(--muted)">{y}</text>')
    px = X(6.6)
    out.append(f'<line x1="{px:.1f}" x2="{px:.1f}" y1="{base_top}" y2="{base_bot}" stroke="var(--text2)" stroke-dasharray="4 3"/>'
               f'<text x="{px + 6:.1f}" y="{base_top + 12}" font-size="12" fill="var(--text)">rientro: 6,6 anni</text>'
               f'<text x="{left}" y="10" font-size="11" fill="var(--muted)">k€</text></svg>')
    return "".join(out)


def heatmap() -> str:
    import math
    cells = ['<div class="heat"><span></span>' + "".join(f'<span style="text-align:center">{h if h % 3 == 0 else ""}</span>' for h in range(24))]
    for m, name in enumerate(MONTHS):
        row = [f'<span class="m">{name}</span>']
        for h in range(24):
            work = 1.0 if 7 <= h <= 18 else 0.25
            v = work * (0.75 + 0.25 * math.sin((h - 6) / 12 * math.pi)) * (0.55 if m == 7 else 1.0)
            v = max(0.08, min(1.0, v))
            row.append(f'<i style="background: color-mix(in srgb, var(--accent) {round(v * 90)}%, var(--sink))"></i>')
        cells.append("".join(row))
    return "".join(cells) + "</div>"


# ---- the phases

def plant() -> str:
    tools = tools_html([("Inverter", (("zap", "Catalogo"), ("wand", "Dimensiona"))),
                        ("Stringhe", (("spline", "Automatico"), ("route", "A mano"), ("refresh", "Ripeti")))])
    colours = ["#c0392b", "#2e6fb0", "#1f9e6e", "#8e44ad", "#d35400", "#16a085", "#7f8c8d", "#b03a2e"]
    legend = "".join(f'<i style="background:{c};width:9px;height:9px;border-radius:50%;display:inline-block"></i>' for c in colours[:5])
    centre = (f'<div class="head-row"><span class="chip">{P.icon("route", 14)} Stringatura a mano</span>'
              f'<span><b>1 × Huawei SUN2000-50KTL-M3</b> · 50,0 kW AC · 8 stringhe su 4 ingressi</span><span class="sp"></span>'
              f'<span class="chip warn">⚠ 52 moduli fuori stringa</span></div>'
              f'<div class="strip" style="margin-top:0">{legend} un colore per stringa<span class="sp"></span>'
              f'<span class="okm" style="color:var(--good);font-weight:700">✓</span> corretta '
              f'<span style="color:var(--warning-ink);font-weight:700">⚠</span> da verificare '
              f'<span style="color:var(--critical);font-weight:700">✘</span> fuori finestra · ▢ modulo fuori stringa</div>'
              f'<div class="planbox">{P.plan_svg()}{P.viewbar("plan")}</div>')

    def mppt(n, strings):
        chips = "".join(f'<span class="sc"><i style="background:{colours[(n - 1) * 2 + j]}"></i>{s} <span class="okm">✓</span></span>'
                        for j, s in enumerate(strings))
        return (f'<div class="mppt"><span class="k">Ingresso {n}</span><span class="ss">{chips}</span>'
                f'<span class="note">2 stringhe da 7 a 25 moduli · 12 in serie, Uoc 587 V</span></div>')
    right = card("Inverter", '<div class="side-tiles">'
                 '<div class="inv"><b>Huawei SUN2000-50KTL-M3</b><span class="s">50,0 kW AC · 4 MPPT · 1.100 V · rendimento 98,7 %</span>'
                 '<span class="qty"><span class="field">× 1<span class="arr">▴▾</span></span></span></div>'
                 '<div class="hbox"><span class="btn">Dal catalogo…</span><span class="btn">Dimensiona da solo</span></div>'
                 '</div><div class="props">'
                 + group("Rapporto DC/AC", '<div class="form2"><label>Obiettivo</label><div class="field">1,10 – 1,30<span class="arr">▴▾</span></div>'
                         '<div style="grid-column:1/-1"><div class="gauge"><span class="band" style="left:12%;width:20%"></span>'
                         '<span class="pin" style="left:76%"></span></div><div class="gl"><span>0,8</span><span>1,86 ora</span><span>2,0</span></div>'
                         '<div class="note" style="color:var(--warning-ink)">Sopra 1,30 l\'inverter taglia il 12,4 % dell\'energia: un secondo inverter o uno più grande.</div></div></div>')
                 + group("Ingressi e stringhe", '<div style="padding:0 8px 6px">' + mppt(1, ["1.1.1", "1.1.2"]) + mppt(2, ["1.2.1", "1.2.2"])
                         + mppt(3, ["1.3.1", "1.3.2"]) + mppt(4, ["1.4.1", "1.4.2"]) + "</div>")
                 + "</div>", cls="props-card")
    right += help_card("Impianto", "Gli inverter, scelti dal catalogo o dimensionati da Meridiana, e le stringhe, verificate con la "
                       "CEI 64-8/7: la tensione alla cella più fredda e la corrente alla più calda, entro ciò che inverter e moduli accettano.",
                       how=False)
    return window(1, tools, centre, right)


def production() -> str:
    tools = tools_html([("Calcolo", (("play", "Calcola"), ("cloud", "Da PVGIS"))), ("Confronto", (("compare", "Varianti"),))],
                       primary="Calcola")
    tiles = ('<div class="tiles">'
             + tile("Energia all'anno", "107.130", "kWh", "anno tipo, dopo tutte le perdite", key=True)
             + tile("Producibilità specifica", "1.151", "kWh/kWp", "in Lombardia di solito 1.100-1.300")
             + tile("Indice di prestazione", "69,9", "%", "IEC 61724-1 · basso per il taglio")
             + tile("Potenza", "93,06", "kWp", "50,0 kW AC · DC/AC 1,86") + "</div>")
    chart = ('<div class="chartcard"><div class="ct"><span class="on">Mesi</span><span>Perdite</span><span>Giorno tipo</span>'
             '<span>Come è calcolato</span><span class="sp"></span><a>Tabella</a><a>Copia</a></div>'
             f'<div class="cb"><h5>Produzione mese per mese</h5>{bars(PROD)}</div></div>')
    strip = ('<div class="strip">' + P.icon("cloud", 15) + '<span>Meteo: <b>PVGIS 5.3</b>, anno tipo SARAH3 + ERA5 2005-2023, scaricato il '
             '21/10/2026 · <b>1.450 kWh/m²</b> sull\'orizzontale · 13,1 °C di media</span><span class="sp"></span>'
             '<span class="chip on">✓ Orizzonte lontano</span><span class="chip on">✓ Ostacoli della scena</span><a>Scarica di nuovo</a></div>')
    centre = tiles + chart + strip + '<div class="sect">PVGIS, secondo parere<span>non disponibile senza rete: si calcola quando c\'è</span></div>'

    def loss(name, value, pct, warn=False, total=False):
        return (f'<div class="r {"warn" if warn else ""} {"total" if total else ""}"><span class="n">{name}</span>'
                f'<span class="q">{value}</span><span class="bar"><b style="width:{pct}%"></b></span></div>')
    right = card("Perdite, dal sole al contatore", '<div class="props" style="padding-bottom:0"><div class="form2" style="padding:0 0 6px">'
                 '<label>Variante</label><div class="field combo">Base</div></div></div><div class="rlist">'
                 + loss("Irraggiamento sul piano", "1.512 kWh/m²", 100)
                 + loss("Ombre vicine (effetto elettrico)", "−8,0 %", 40)
                 + loss("Angolo e riflessione", "−2,6 %", 13)
                 + loss("Temperatura dei moduli", "−5,1 %", 26)
                 + loss("Sporco e neve", "−2,0 %", 10)
                 + loss("Mismatch e cavi DC", "−2,2 %", 11)
                 + loss("Taglio dell'inverter", "−12,4 %", 62, warn=True)
                 + loss("Rendimento dell'inverter", "−1,6 %", 8)
                 + loss("Cavi AC e trasformatore", "−0,9 %", 5)
                 + loss("Al contatore", "107.130 kWh", 70, total=True) + "</div>", cls="props-card")
    right += help_card("Producibilità", "Meridiana calcola l'anno ora per ora, dal sole sui moduli al contatore, con il meteo del sito "
                       "da PVGIS. Ogni riquadro ha il suo «?», e «Come è calcolato» mostra formula e fonte di ogni numero.")
    return window(2, tools, centre, right)


def consumption() -> str:
    tools = tools_html([("Dati", (("file-in", "Curva"), ("sliders", "Base")))])
    f = ('<div class="bar3"><b style="width:69%;background:var(--accent)"></b><b style="width:14%;background:var(--muted)"></b>'
         '<b style="width:17%;background:var(--line)"></b></div>')
    tiles = ('<div class="tiles">'
             + tile("Consumo all'anno", "107.100", "kWh", "stima dal progetto: altri usi, bassa tensione", key=True)
             + tile("Fasce", "69 · 14 · 17", "%", "F1 74.429 · F2 14.525 · F3 18.146 kWh", extra=f)
             + tile("Tra le 8 e le 18", "72", "%", "dei consumi: quando l'impianto produce di più")
             + tile("Carico di base", "2,83", "kW", "mai sotto nel 95 % delle ore") + "</div>"
             + '<div class="tiles" style="margin-top:8px">'
             + tile("Ora di punta", "32,11", "kWh", "in un'ora")
             + tile("Fattore di carico", "38", "%", "carico medio sul massimo")
             + tile("Fine settimana e festivi", "10", "%", "dei consumi")
             + '<div class="tile" style="background:transparent;border:1px dashed var(--line)"><div class="l"><span>Da dove vengono</span></div>'
             '<div class="d" style="margin-top:6px">Stima dal progetto. Per numeri veri, la curva misurata o le bollette:</div>'
             '<div class="hbox" style="margin-top:6px"><span class="btn" style="white-space:nowrap">Curva…</span>'
             '<span class="btn" style="white-space:nowrap">Bollette…</span></div></div>'
             + "</div>")
    chart = ('<div class="chartcard"><div class="ct"><span>Mesi</span><span>Giorno tipo</span><span class="on">Mappa oraria</span>'
             '<span>Come è calcolato</span><span class="sp"></span><a>Tabella</a></div>'
             f'<div class="cb"><h5>Consumi ora per ora, mese per mese</h5>{heatmap()}'
             '<div class="gl" style="margin-top:6px"><span>ore 0-23</span><span>più chiaro: meno consumo · più pieno: di più</span></div></div></div>')
    centre = tiles + chart
    right = card("Punto di prelievo", '<div class="props">'
                 + group("Fornitura", '<div class="form2"><label>Codice POD</label><div class="field">IT001E12345678</div>'
                         '<label>Tipo</label><div class="field combo">Altri usi, BT</div>'
                         '<label>Potenza impegnata</label><div class="field">93,0 kW<span class="arr">▴▾</span></div>'
                         '<div class="note">Automatica dalla potenza dell\'impianto finché non scrivi quella del contratto.</div></div>')
                 + group("Profilo", '<div class="form2"><label>Attività</label><div class="field combo">Uffici e laboratorio</div>'
                         '<label>Giorni di lavoro</label><div class="field combo">Lun-Ven</div>'
                         '<label>Chiusura estiva</label><div class="field combo">2 settimane di agosto</div></div>')
                 + "</div>", cls="props-card")
    right += help_card("Consumi", "I consumi decidono quanta produzione si usa sul posto. Inserisci un anno, le fasce F1, F2, F3, le "
                       "bollette mese per mese o una curva misurata; senza, Meridiana li stima dal progetto e lo dice nelle Verifiche.")
    return window(3, tools, centre, right)


def economics() -> str:
    tools = tools_html([("Componenti", (("battery", "Batteria"),)), ("Calcolo", (("play", "Calcola"),)),
                        ("Confronto", (("compare", "Varianti"),))], primary="Calcola")
    centre = ('<div class="sect" style="margin-top:0">Energia<span>quanto si usa sul posto</span></div><div class="tiles">'
              + tile("Autoconsumo", "53", "%", "della produzione · 56.743 kWh", key=True)
              + tile("Autosufficienza", "53", "%", "dei consumi")
              + tile("Ceduta alla rete", "50.387", "kWh", "all'anno")
              + tile("Bolletta, primo anno", "12.589", "€", "quota energia, era 26.775 €") + "</div>"
              + '<div class="sect">Economia<span>20 anni, tasso 5 %, degrado 0,5 % l\'anno</span></div><div class="tiles">'
              + tile("Valore attuale netto", "198.853", "€", "positivo: conviene", key=True)
              + tile("Tempo di ritorno", "6,6", "anni", "attualizzato 7,8")
              + tile("Tasso interno di rendimento", "15,3", "%")
              + tile("Costo livellato", "0,100", "€/kWh", "contro 0,25 €/kWh comprati") + "</div>"
              + '<div class="chartcard"><div class="ct"><span>Bilancio</span><span>Bolletta</span><span class="on">Flusso di cassa</span>'
              '<span>Anno per anno</span><span>Taglia</span><span>Accumulo</span><span>Come è calcolato</span><span class="sp"></span><a>Tabella</a></div>'
              f'<div class="cb"><h5>Flusso di cassa cumulato</h5>{cashflow()}</div></div>')
    right = card("Prezzi e ipotesi", '<div class="props">'
                 + group("Energia acquistata", '<div class="form2"><label>F1</label><div class="field">0,250 €/kWh<span class="arr">▴▾</span></div>'
                         '<label>F2</label><div class="field">0,250 €/kWh<span class="arr">▴▾</span></div>'
                         '<label>F3</label><div class="field">0,250 €/kWh<span class="arr">▴▾</span></div>'
                         '<div class="note">Tutti i costi variabili, imposte comprese: dalla bolletta.</div></div>')
                 + group("Energia immessa", '<div class="form2"><label>Ritiro dedicato</label><div class="field">0,100 €/kWh<span class="arr">▴▾</span></div>'
                         '<label>Incentivo CER</label><div class="field combo">Nessuno</div></div>')
                 + group("Investimento", '<div class="form2"><label>Costo dell\'impianto</label><div class="field">1.300 €/kWp<span class="arr">▴▾</span></div>'
                         '<label>Detrazione</label><div class="field combo">Nessuna</div>'
                         '<label>Anni dell\'analisi</label><div class="field">20<span class="arr">▴▾</span></div></div>')
                 + "</div>", cls="props-card")
    right += help_card("Bilancio ed economia", "Produzione e consumi si incontrano ora per ora: ciò che si usa sul posto fa risparmiare "
                       "in bolletta, il resto si vende. I flussi di cassa negli anni danno poi il valore attuale netto e il tempo di ritorno.")
    return window(4, tools, centre, right)


def report() -> str:
    tools = tools_html([("Esporta", (("doc", "Relazione"),)), ("Varianti", (("compare", "Confronta"), ("copy-plus", "Revisione"))),
                        ("Note", (("clip", "Copia le note"),))], primary="Relazione")
    chapters = [("Dati generali e sito", "2 pagine"), ("Edifici, coperture e posa", "3"), ("Impianto: moduli, inverter e stringhe", "4"),
                ("Producibilità con le perdite", "3"), ("Consumi e bilancio", "2"), ("Economia", "2"),
                ("Verifiche e norme applicate", "3"), ("Allegati: tabelle orarie, schede", "6")]
    outline = '<div class="outline">' + "".join(
        f'<div class="o"><span class="check"><i class="on"></i></span><span class="num">{i + 1}</span><span class="t">{t}</span>'
        f'<span class="p">{p}{" pagine" if p.isdigit() else ""}</span></div>' for i, (t, p) in enumerate(chapters)) + "</div>"
    paper = ('<div class="paper"><div class="hb"></div><h6>Impianto fotovoltaico, capannone di Rho</h6>'
             '<div class="ln"></div><div class="ln s"></div><div class="ln"></div><div class="fig">pianta con i moduli</div>'
             '<div class="ln"></div><div class="ln"></div><div class="ln s"></div><div class="fig">produzione mese per mese</div>'
             '<div class="ln"></div><div class="ln s"></div></div>')
    centre = ('<div class="head-row"><h3>Relazione tecnica</h3><span class="chip muted">da fare</span><span class="sp"></span>'
              '<span class="btn">Anteprima</span><span class="prim">Esporta la relazione (PDF)…</span></div>'
              '<div class="twocol"><div>'
              + group("Intestazione", '<div class="form2" style="grid-template-columns:1fr 1fr 1fr;gap:5px 8px">'
                      '<div><label>Committente</label><div class="field">Logistica Rho S.r.l.</div></div>'
                      '<div><label>Progettista</label><div class="field">Ing. …</div></div>'
                      '<div><label>Revisione</label><div class="field combo">R00, 24/10/2026</div></div></div>')
              + '<div class="sect">Capitoli<span>25 pagine circa, ogni calcolo con la sua fonte</span></div>' + outline
              + f'</div><div>{paper}<div class="gl" style="margin-top:6px"><span>pagina 1 di 25</span><span>A4</span></div></div></div>')

    def d(name, state, cls, note, button=""):
        b = f'<span class="btn" style="grid-column:1/-1;justify-self:start;margin-top:4px">{button}</span>' if button else ""
        return f'<div class="d"><b>{name}</b><span class="chip {cls}">{state}</span><span class="s">{note}</span>{b}</div>'
    right = card("Elaborati", '<div class="deliv">'
                 + d("Relazione tecnica (PDF)", "da fare", "muted", "Non ancora esportata", "Esporta…")
                 + d("Confronto delle varianti (PDF)", "fatto", "ok", "23/10/2026 · 2 varianti")
                 + d("Pianta con i moduli (DXF)", "non ancora", "muted", "Arriva con il compito relazione")
                 + d("Modello (IFC4)", "non ancora", "muted", "Arriva con il compito relazione")
                 + d("Serie orarie (CSV)", "non ancora", "muted", "Arriva con il compito relazione")
                 + d("Elenco moduli e stringhe", "non ancora", "muted", "Arriva con il compito relazione")
                 + "</div>", cls="props-card")
    right += help_card("Relazione", "Il pannello Elaborati elenca ciò che esce dal progetto con il suo stato: fatto, da rifare perché "
                       "il progetto è cambiato, da fare, o non ancora disponibile. La relazione porta ogni calcolo con la sua fonte.",
                       how=False)
    return window(5, tools, centre, right)


PAGES = {"impianto": (plant, "2. Impianto"), "producibilita": (production, "3. Producibilità"),
         "consumi": (consumption, "4. Consumi"), "bilancio": (economics, "5. Bilancio ed economia"),
         "relazione": (report, "6. Relazione")}


def main() -> None:
    css = (G.TREE_CSS.replace(".treebox", ".mock") + B.CONTROLS_CSS + B.CHECKS_CSS + B.TABS_CSS + B.TOOLS_CSS + B.BODY_CSS
           + TOOLS_EXTRA_CSS + PHASE_CSS + B.FRAME_CSS)
    for name, (make, title) in PAGES.items():
        html = P.page(f"Bozzetto: {title}", "", make(), css).replace(f"<h1>Bozzetto: {title}</h1>", "")
        html = html.replace(P.controls(), "").replace(P.FONT_DIR, "../../../data/fonts/titillium-web")
        for theme in ("chiaro", "scuro"):
            out = html if theme == "chiaro" else html.replace('<html lang="it">', '<html lang="it" class="dark">').replace(
                "try { setTheme(localStorage.getItem('m17-dark') === '1'); } catch (e) { setTheme(false); }", "setTheme(true);")
            (HERE / f"fasi-{name}-{theme}.html").write_text(out, encoding="utf-8")
        print("scritto", name)


if __name__ == "__main__":
    main()
