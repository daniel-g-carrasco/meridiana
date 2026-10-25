"""Le parti comuni dei bozzetti dello studio 17: i colori del tema (da theme_colors.py, bronzo, chiaro e scuro) come
variabili CSS, il carattere Titillium Web dai file del repository, e la finestra di Meridiana disegnata in HTML
(barra dei menu, schede, barra degli strumenti, Progetto, pianta e 3D affiancate, Proprietà, Verifiche, barra di
stato). Le pagine (genera.py) compongono queste parti in tre o più direzioni per tema.

Niente librerie, niente rete: ogni pagina si apre da sola nel browser."""

from __future__ import annotations

import html
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from meridiana import theme_colors as tc  # noqa: E402

FONT_DIR = "../../../data/fonts/titillium-web"
STATUS = {"warning": "#fab219", "critical": "#d03b3b", "good": "#0ca30c", "warning_ink": tc.WARNING_INK}


def css_variables() -> str:
    """Le variabili CSS per i due temi, dai token di theme_colors.derive (bronzo, fondi «Meridiana»)."""
    out = []
    for dark in (False, True):
        t = tc.derive(tc.DEFAULT_SEED, dark, "meridiana").tokens
        names = {
            "window": t["window"], "panel": t["panel"], "view": t["view"], "header": t["header"], "card": t["card"],
            "line": t["line"], "line-soft": t["line_soft"], "text": t["text"], "text2": t["text2"], "muted": t["muted"],
            "tooltip-bg": t["tooltip_bg"], "tooltip-fg": t["tooltip_fg"], "accent": t["accent"],
            "accent-fg": t["accent_fg"], "accent-soft": t["accent_soft"], "select-bg": t["select_bg"],
            "select-fg": t["select_fg"], "assistant": t["assistant"],
            "plan-bg": t["plan"]["bg"], "plan-bld": t["plan"]["bld_stroke"], "plan-bld-fill": t["plan"]["bld_fill"],
            "plan-module": t["plan"]["module"], "plan-sub": t["plan"]["sub_stroke"], "plan-sub-fill": t["plan"]["sub_fill"],
            "plan-sel": t["plan"]["sel"], "plan-guide": t["plan"]["guide"], "plan-pitch": t["plan"]["pitch"],
            "sky-top": t["d3"]["sky_top"], "sky-bottom": t["d3"]["sky_bottom"], "ground": t["d3"]["ground"],
            "wall": t["d3"]["wall"], "roof": t["d3"]["roof"], "d3-module": t["d3"]["module"],
            "chart-surface": t["chart"]["surface"], "chart-grid": t["chart"]["grid"], "chart-axis": t["chart"]["axis"],
            "warning": STATUS["warning"], "critical": STATUS["critical"], "good": STATUS["good"],
            "warning-ink": STATUS["warning_ink"] if not dark else STATUS["warning"],
            # i fondi «dal colore» e «grigi» sono scelte di Daniel: qui solo Meridiana
            "shadow": "rgba(20, 24, 30, 0.14)" if not dark else "rgba(0, 0, 0, 0.5)",
            "raise": "rgba(255, 255, 255, 0.9)" if not dark else "rgba(255, 255, 255, 0.045)",
            "sink": "rgba(30, 28, 25, 0.06)" if not dark else "rgba(0, 0, 0, 0.22)",
        }
        sel = "html.dark" if dark else ":root"
        out.append(sel + " {\n" + "".join(f"  --{k}: {v};\n" for k, v in names.items()) + "}\n")
    return "".join(out)


def base_css(zoom: float = 0.62) -> str:
    return css_variables() + f"""
@font-face {{ font-family: "Titillium Web"; src: url("{FONT_DIR}/TitilliumWeb-Regular.ttf"); font-weight: 400; }}
@font-face {{ font-family: "Titillium Web"; src: url("{FONT_DIR}/TitilliumWeb-SemiBold.ttf"); font-weight: 600; }}
@font-face {{ font-family: "Titillium Web"; src: url("{FONT_DIR}/TitilliumWeb-Bold.ttf"); font-weight: 700; }}
* {{ box-sizing: border-box; }}
html {{ --zoom: {zoom}; }}
body {{ margin: 0; font-family: "Titillium Web", "Segoe UI", sans-serif; font-size: 15px; color: var(--text);
       background: var(--window); }}
.page {{ padding: 20px 28px 60px; max-width: 2400px; }}
.page h1 {{ font-size: 26px; margin: 0 0 4px; font-weight: 600; }}
.page h2 {{ font-size: 20px; margin: 28px 0 6px; font-weight: 600; }}
.page p {{ max-width: 920px; line-height: 1.4; color: var(--text2); margin: 4px 0; }}
.controls {{ display: flex; gap: 14px; align-items: center; margin: 10px 0 18px; flex-wrap: wrap; }}
.controls label {{ display: flex; gap: 6px; align-items: center; color: var(--text2); }}
.controls button, .controls select {{ font: inherit; padding: 4px 12px; border-radius: 6px; border: 1px solid var(--line);
       background: var(--panel); color: var(--text); cursor: pointer; }}
.controls button.on {{ background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }}
.row {{ display: flex; gap: 22px; align-items: flex-start; flex-wrap: wrap; padding-bottom: 12px; }}
.dir {{ flex: 0 0 auto; }}
.dir h3 {{ margin: 0 0 6px; font-size: 17px; font-weight: 600; }}
.dir .note {{ max-width: calc(1180px * var(--zoom)); font-size: 14px; color: var(--text2); line-height: 1.35; margin: 6px 0 0; }}
.dir .note b {{ color: var(--text); }}
.frame {{ width: calc(1180px * var(--zoom)); height: calc(720px * var(--zoom)); overflow: hidden; border-radius: 6px;
          box-shadow: 0 2px 10px var(--shadow); border: 1px solid var(--line); }}
.mock {{ width: 1180px; height: 720px; transform: scale(var(--zoom)); transform-origin: 0 0; display: grid;
         grid-template-rows: 28px 34px auto 1fr 24px; grid-template-columns: 1fr; background: var(--window);
         color: var(--text); font-size: 13px; position: relative; }}
.mock .menubar {{ display: flex; align-items: center; gap: 2px; padding: 0 8px; background: var(--window); }}
.mock .menubar span {{ padding: 4px 8px; border-radius: 4px; }}
.mock .menubar span.on {{ background: var(--select-bg); color: var(--select-fg); }}
.mock .menubar .sp {{ flex: 1; }}
.mock .menubar .chip {{ border: 1px solid var(--line); background: var(--panel); font-size: 12px; padding: 2px 8px; }}
.mock .tabs {{ display: flex; align-items: flex-end; gap: 2px; padding: 0 10px; background: var(--window);
               border-bottom: 1px solid var(--line); }}
.mock .tabs span {{ padding: 7px 12px 6px; color: var(--text2); border-bottom: 2px solid transparent; }}
.mock .tabs span.on {{ color: var(--text); border-bottom-color: var(--accent); }}
.mock .tabs span.on::before {{ content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%;
                               background: var(--accent); margin-right: 7px; vertical-align: 1px; }}
.mock .toolbar {{ display: flex; align-items: center; gap: 4px; padding: 3px 8px; background: var(--window); min-height: 34px; }}
.mock .toolbar .tb {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 5px;
                      color: var(--text2); border: 1px solid transparent; }}
.mock .toolbar .tb svg {{ width: 18px; height: 18px; }}
.mock .toolbar .tb.on {{ background: var(--select-bg); color: var(--select-fg); border-color: var(--line); }}
.mock .toolbar .sep {{ width: 1px; height: 20px; background: var(--line); margin: 0 6px; }}
.mock .body {{ display: grid; grid-template-columns: 220px 1fr 300px; min-height: 0; }}
.mock .side {{ display: flex; flex-direction: column; min-height: 0; background: var(--panel); }}
.mock .ptitle {{ padding: 5px 10px; font-weight: 600; font-size: 12px; color: var(--text2); background: var(--header);
                 border-bottom: 1px solid var(--line-soft); display: flex; align-items: center; gap: 6px; }}
.mock .ptitle .x {{ margin-left: auto; color: var(--muted); font-weight: 400; }}
.mock .centre {{ display: grid; grid-template-rows: 1fr auto; min-height: 0; background: var(--window); }}
.mock .views {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--line); min-height: 0; }}
.mock .view {{ position: relative; overflow: hidden; background: var(--plan-bg); }}
.mock .view svg {{ width: 100%; height: 100%; display: block; }}
.mock .view.d3 {{ background: linear-gradient(var(--sky-top), var(--sky-bottom)); }}
.mock .viewbar {{ position: absolute; top: 8px; left: 8px; display: flex; gap: 2px; background: var(--panel);
                  border: 1px solid var(--line); border-radius: 6px; padding: 2px; font-size: 12px;
                  box-shadow: 0 1px 4px var(--shadow); }}
.mock .viewbar span {{ padding: 2px 8px; border-radius: 4px; color: var(--text2); }}
.mock .viewbar span.on {{ background: var(--select-bg); color: var(--select-fg); }}
.mock .checks {{ grid-column: 1 / -1; background: var(--panel); border-top: 1px solid var(--line); min-height: 0;
                 display: flex; flex-direction: column; }}
.mock .status {{ display: flex; align-items: center; gap: 14px; padding: 0 10px; border-top: 1px solid var(--line);
                 font-size: 12px; color: var(--text2); background: var(--window); }}
.mock .status .sp {{ flex: 1; }}
.mock .status .cnt {{ display: inline-flex; gap: 4px; align-items: center; }}
.mock .tree {{ padding: 6px 4px; overflow: hidden; line-height: 1.6; font-size: 13px; }}
.mock .tree div {{ display: flex; align-items: center; gap: 6px; padding: 0 6px; border-radius: 4px; white-space: nowrap; }}
.mock .tree div.sel {{ background: var(--select-bg); color: var(--select-fg); }}
.mock .tree svg {{ width: 15px; height: 15px; flex: none; color: var(--text2); }}
.mock .tree .mark {{ margin-left: auto; font-size: 11px; padding: 0 5px; border-radius: 8px; color: #fff; }}
.mock .tree .mark.warn {{ background: var(--warning-ink); }}
.mock .tree .mark.info {{ background: var(--muted); }}
.mock .tree .mark.fail {{ background: var(--critical); }}
.mock .tree .lvl1 {{ padding-left: 20px; }}
.mock .tree .lvl2 {{ padding-left: 36px; }}
.mock .tree .lvl3 {{ padding-left: 52px; }}
.mock .props {{ padding: 6px 8px; overflow: hidden; font-size: 13px; }}
.mock .props h4 {{ margin: 6px 0 4px; font-size: 13px; font-weight: 600; }}
.mock .group {{ margin: 8px 0; }}
.mock .group .gt {{ font-weight: 600; font-size: 12px; color: var(--text2); padding: 2px 0; }}
.mock .form {{ display: grid; grid-template-columns: 1fr 128px; gap: 4px 8px; align-items: center; }}
.mock .form label {{ color: var(--text2); }}
.mock .field {{ display: flex; align-items: center; justify-content: space-between; height: 24px; padding: 0 6px;
                border-radius: 4px; background: var(--view); border: 1px solid var(--line); color: var(--text); }}
.mock .field .arr {{ color: var(--muted); font-size: 10px; letter-spacing: -2px; }}
.mock .field.combo::after {{ content: "⌄"; color: var(--muted); }}
.mock .btn {{ display: inline-flex; align-items: center; justify-content: center; height: 26px; padding: 0 12px;
              border-radius: 5px; border: 1px solid var(--line); background: var(--view); color: var(--text); }}
.mock .btn.primary {{ background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }}
.mock .check {{ display: flex; gap: 6px; align-items: center; }}
.mock .check i {{ width: 14px; height: 14px; border: 1px solid var(--line); border-radius: 3px; background: var(--view); }}
.mock .check i.on {{ background: var(--accent); border-color: var(--accent); }}
.mock .clist {{ overflow: hidden; font-size: 12.5px; padding: 2px 6px; }}
.mock .clist div {{ display: flex; gap: 8px; align-items: baseline; padding: 2px 4px; }}
.mock .clist .m {{ width: 16px; text-align: center; font-weight: 700; }}
.mock .clist .m.fail {{ color: var(--critical); }} .mock .clist .m.warn {{ color: var(--warning-ink); }}
.mock .clist .m.ok {{ color: var(--good); }} .mock .clist .m.info {{ color: var(--muted); }}
.mock .clist .src {{ margin-left: auto; color: var(--muted); font-size: 11.5px; white-space: nowrap; }}
.mock .chead {{ display: flex; gap: 6px; align-items: center; padding: 4px 8px; font-size: 12px; }}
.mock .chead .f {{ padding: 1px 7px; border: 1px solid var(--line); border-radius: 4px; background: var(--view); }}
.mock .chead .f.on {{ background: var(--select-bg); }}
.mock .sunbar {{ display: flex; align-items: center; gap: 10px; padding: 3px 10px; font-size: 12px; color: var(--text2);
                 background: var(--panel); border-top: 1px solid var(--line); }}
.mock .sunbar .track {{ flex: 1; height: 4px; background: var(--line); border-radius: 2px; position: relative; }}
.mock .sunbar .track i {{ position: absolute; left: 46%; top: -4px; width: 12px; height: 12px; border-radius: 50%;
                          background: var(--accent); }}
.mock .meridio {{ position: absolute; right: 318px; bottom: 60px; width: 46px; height: 46px; border-radius: 50%;
                  background: var(--panel); border: 1px solid var(--line); display: grid; place-items: center;
                  box-shadow: 0 1px 4px var(--shadow); }}
.mock .meridio svg {{ width: 34px; height: 34px; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
"""


CONTROLS_JS = """
<script>
const root = document.documentElement;
function setTheme(dark) {
  root.classList.toggle('dark', dark);
  document.querySelectorAll('[data-theme]').forEach(b => b.classList.toggle('on', (b.dataset.theme === 'dark') === dark));
  try { localStorage.setItem('m17-dark', dark ? '1' : '0'); } catch (e) {}
}
function setZoom(z) { root.style.setProperty('--zoom', z); const o = document.getElementById('zoomv'); if (o) o.textContent = Math.round(z * 100) + '%'; }
try { setTheme(localStorage.getItem('m17-dark') === '1'); } catch (e) { setTheme(false); }
</script>
"""


def controls() -> str:
    return """
<div class="controls">
  <label>Tema:
    <button data-theme="light" class="on" onclick="setTheme(false)">Chiaro</button>
    <button data-theme="dark" onclick="setTheme(true)">Scuro</button></label>
  <label>Scala: <input type="range" min="0.35" max="1" step="0.01" value="0.62" oninput="setZoom(this.value)"> <span id="zoomv">62%</span></label>
</div>"""


# ---- icone (tratti alla Lucide, su una griglia di 24) ----

ICONS = {
    "select": '<path d="M5 3l14 8-6 2-3 6z"/>',
    "building": '<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M8 7h2M14 7h2M8 11h2M14 11h2M8 15h2M14 15h2M10 21v-4h4v4"/>',
    "pitch": '<path d="M3 11l9-7 9 7M5 10v10h14V10"/>',
    "subfield": '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h18M3 14h18M9 4v16M15 4v16"/>',
    "exclusion": '<circle cx="12" cy="12" r="8"/><path d="M6.5 6.5l11 11"/>',
    "measure": '<path d="M3 17L17 3l4 4L7 21zM7 13l2 2M10 10l2 2M13 7l2 2"/>',
    "strings": '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="7" cy="6" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="17" cy="18" r="1.6"/>',
    "site": '<path d="M12 21s-6-5.5-6-10a6 6 0 0112 0c0 4.5-6 10-6 10z"/><circle cx="12" cy="11" r="2.2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 015 0c0 1.6-2.5 2-2.5 3.5M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "move": '<path d="M12 2v20M2 12h20M12 2l-3 3M12 2l3 3M12 22l-3-3M12 22l3-3M2 12l3-3M2 12l3 3M22 12l-3-3M22 12l-3 3"/>',
    "fix": '<path d="M14 7l3 3M4 20l4-1 10-10-3-3L5 16z"/>',
    "chevron": '<path d="M9 6l6 6-6 6"/>',
    "chevdown": '<path d="M6 9l6 6 6-6"/>',
    "grid": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5M3 17l9 5 9-5"/>',
    "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "send": '<path d="M3 11l18-8-8 18-2-8z"/>',
    "resize": '<path d="M21 15l-6 6M21 9L9 21M21 21l-1 0"/>',
    "book": '<path d="M4 4h6a3 3 0 013 3v13a2 2 0 00-2-2H4zM20 4h-6a3 3 0 00-3 3v13a2 2 0 012-2h7z"/>',
    "calc": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 12h3M13 12h3M8 16h3M13 16h3"/>',
    "filter": '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "palette": '<circle cx="12" cy="12" r="9"/><circle cx="8" cy="10" r="1.3"/><circle cx="12" cy="7" r="1.3"/><circle cx="16" cy="10" r="1.3"/><path d="M12 21c-2 0-2-3 0-3h2a3 3 0 000-6"/>',
}


def icon(name: str, size: int = 16, extra: str = "") -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra}>{ICONS[name]}</svg>')


TOOLS = (("select", "Seleziona", "V"), ("building", "Edificio", "B"), ("pitch", "Falda", "P"),
         ("subfield", "Sottocampo", "S"), ("exclusion", "Esclusione", "X"), ("measure", "Misura", "D"),
         ("strings", "Stringhe", "W"))
MENUS = ("File", "Modifica", "Disegna", "Vista", "Cataloghi", "Sito", "Varianti", "Aiuto")
TABS = ("Modello", "Producibilità", "Consumi", "Bilancio ed economia")


def menubar(extra: str = "") -> str:
    items = "".join(f"<span>{m}</span>" for m in MENUS)
    return (f'<div class="menubar">{items}<span class="sp"></span>{extra}'
            f'<span class="chip">Variante: Base ⌄</span><span class="chip">Tema ⌄</span><span class="chip">Colore ⌄</span></div>')


def tabs(active: int = 0, cls: str = "") -> str:
    items = "".join(f'<span class="{"on" if i == active else ""}">{t}</span>' for i, t in enumerate(TABS))
    return f'<div class="tabs {cls}">{items}</div>'


def toolbar(active: str = "subfield", text: bool = False, cls: str = "", extra_left: str = "", extra_right: str = "") -> str:
    items = []
    for key, name, k in TOOLS:
        label = f"<span>{name}</span>" if text else ""
        items.append(f'<span class="tb {"on" if key == active else ""}" title="{name} ({k})">{icon(key, 18)}{label}</span>')
    return (f'<div class="toolbar {cls}">{extra_left}{"".join(items)}<span class="sep"></span>'
            f'<span class="tb">{icon("sun", 18)}{"<span>Sole</span>" if text else ""}</span>{extra_right}</div>')


TREE = [
    (0, "site", "Sito: Capannone Rho", "sel", ("info", 3)),
    (1, "building", "Edificio 1", "", None),
    (2, "pitch", "Falda 1 (Sud, 19°)", "", None),
    (2, "pitch", "Falda 2 (Nord, 19°)", "", None),
    (1, "building", "Uffici", "", None),
    (1, "subfield", "Copertura Sud · 156", "", ("warn", 1)),
    (1, "subfield", "Copertura Nord · 32", "", None),
    (1, "exclusion", "Lucernario 1", "", None),
    (1, "exclusion", "Lucernario 2", "", None),
    (1, "exclusion", "Camino 1", "", None),
]


def tree_plain() -> str:
    """L'albero come è oggi: una lista indentata, nessuno spazio tra le sezioni."""
    out = []
    for lvl, ic, text, cls, mark in TREE:
        m = f'<span class="mark {mark[0]}">{mark[1]}</span>' if mark else ""
        out.append(f'<div class="lvl{lvl} {cls}">{icon(ic, 15)}<span>{text}</span>{m}</div>')
    return f'<div class="tree">{"".join(out)}</div>'


# ---- la pianta e il 3D ----

def plan_svg(selected: bool = True, halo: bool = False, sel_colour: str = "var(--plan-sel)") -> str:
    """Una pianta a L con due falde, un sottocampo di moduli, due lucernari, nord e scala."""
    mods = []
    for r in range(5):
        for c in range(11):
            x, y = 86 + c * 22, 80 + r * 44
            if (r, c) in ((1, 4), (1, 5), (2, 4), (2, 5)):
                continue
            mods.append(f'<rect x="{x}" y="{y}" width="20" height="40" fill="var(--plan-module)" stroke="var(--plan-bg)" stroke-width="0.8"/>')
    for r in range(2):
        for c in range(4):
            mods.append(f'<rect x="{406 + c * 22}" y="{310 + r * 44}" width="20" height="40" fill="var(--plan-module)" stroke="var(--plan-bg)" stroke-width="0.8"/>')
    glow = f'<path d="M70 60h270v255h-270z" fill="none" stroke="{sel_colour}" stroke-width="6" opacity="0.25"/>' if halo and selected else ""
    sel = f'<path d="M70 60h270v255h-270z" fill="var(--plan-sub-fill)" stroke="{sel_colour}" stroke-width="2"/>' if selected else ""
    return f'''<svg viewBox="0 0 560 420" preserveAspectRatio="xMidYMid meet">
<rect width="560" height="420" fill="var(--plan-bg)"/>
<path d="M50 40h300v300h150v50H50z" fill="var(--plan-bld-fill)" stroke="var(--plan-bld)" stroke-width="2.2"/>
<path d="M50 190h300M350 40v300" stroke="var(--plan-pitch)" stroke-width="1" stroke-dasharray="6 4"/>
<path d="M200 230v40m0 0l-6-8m6 8l6-8" stroke="var(--plan-pitch)" stroke-width="1.2" fill="none"/>
{glow}{sel}
{"".join(mods)}
<rect x="174" y="124" width="44" height="84" fill="none" stroke="var(--critical)" stroke-width="1.5" stroke-dasharray="4 3"/>
<rect x="420" y="360" width="30" height="20" fill="none" stroke="var(--critical)" stroke-width="1.5" stroke-dasharray="4 3"/>
<text x="196" y="172" font-size="10" text-anchor="middle" fill="var(--plan-bld)">Luc. 1</text>
<g transform="translate(520 34)"><path d="M0 18L6 -2l6 20-6-5z" fill="var(--plan-bld)"/><text x="6" y="34" font-size="11" text-anchor="middle" fill="var(--plan-bld)">N</text></g>
<g transform="translate(20 398)"><path d="M0 0h100" stroke="var(--plan-bld)" stroke-width="2"/><path d="M0 -4v8M50 -4v8M100 -4v8" stroke="var(--plan-bld)" stroke-width="1.5"/><text x="50" y="-6" font-size="10" text-anchor="middle" fill="var(--plan-bld)">10 m</text></g>
</svg>'''


def view3d_svg(selected: bool = True) -> str:
    """Un capannone con il tetto a due falde e i moduli sulla falda sud, in assonometria semplice."""
    mods = []
    for r in range(3):
        for c in range(9):
            x = 150 + c * 28 + r * 18
            y = 212 - r * 22
            mods.append(f'<path d="M{x} {y}l22 -8 10 6 -22 8z" fill="var(--d3-module)" stroke="#ffffff22" stroke-width="0.6"/>')
    sel = '<path d="M140 220l250-92 32 20-250 92z" fill="none" stroke="var(--plan-sel)" stroke-width="2.5"/>' if selected else ""
    return f'''<svg viewBox="0 0 560 420" preserveAspectRatio="xMidYMid meet">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--sky-top)"/><stop offset="1" stop-color="var(--sky-bottom)"/></linearGradient></defs>
<rect width="560" height="420" fill="url(#sky)"/>
<path d="M0 290L560 290L560 420L0 420z" fill="var(--ground)"/>
<path d="M110 300l300-110 0-90-300 110z" fill="var(--wall)"/>
<path d="M410 190l80 40 0-90-80-40z" fill="var(--wall)" opacity="0.8"/>
<path d="M110 300l300-110 80 40-300 110z" fill="var(--wall)" opacity="0.55"/>
<path d="M110 100l300-110 80 40-300 110z" fill="var(--roof)"/>
<path d="M110 100l300-110-30 -25-300 110z" fill="var(--roof)" opacity="0.7"/>
{"".join(mods)}{sel}
<path d="M110 300l300-110" stroke="var(--plan-bld)" stroke-width="1" opacity="0.4"/>
<circle cx="470" cy="60" r="12" fill="#f6e3a4" opacity="0.9"/>
</svg>'''


def viewbar(kind: str = "plan") -> str:
    if kind == "plan":
        return ('<div class="viewbar"><span class="on">Pianta</span><span>3D</span><span>Affiancate</span>'
                '<span style="border-left:1px solid var(--line)">Inquadra</span><span class="on">F3</span><span>F8</span></div>')
    return '<div class="viewbar"><span>Pianta</span><span class="on">3D</span><span>Affiancate</span><span style="border-left:1px solid var(--line)">Inquadra</span></div>'


def sunbar() -> str:
    return ('<div class="sunbar"><span>21 dic</span><div class="track"><i></i></div><span>12:00 <b>XII</b></span>'
            '<span>h 21° · az 180°</span></div>')


def meridio_svg(size: int = 34, thinking: bool = False, cls: str = "") -> str:
    rays = ("M5.1 10.2H3.4M6.02 6.75L4.55 5.9M8.55 4.22L7.7 2.75M12 3.3V1.6M15.45 4.22L16.3 2.75M17.98 6.75L19.45 5.9"
            "M18.9 10.2H20.6M3 19.4H21M12 16.9V21.8")
    eye = 8.7 if thinking else 9.5
    dots = "".join(f'<circle cx="{x}" cy="3.6" r="0.75" fill="var(--text)"/>' for x in (19.2, 21.2, 23.2)) if thinking else ""
    return (f'<svg class="{cls}" viewBox="0 0 24 24" width="{size}" height="{size}">'
            f'<path class="rays" d="{rays}" fill="none" stroke="var(--text)" stroke-width="1.3" stroke-linecap="round"/>'
            f'<circle class="disc" cx="12" cy="10.2" r="5.3" fill="var(--assistant)" stroke="#24211d" stroke-width="1.3"/>'
            f'<path class="smile" d="M10.2 12.1Q12 13.5 13.8 12.1" fill="none" stroke="#24211d" stroke-width="1.2" stroke-linecap="round"/>'
            f'<circle class="eye l" cx="10.1" cy="{eye}" r="0.9" fill="#24211d"/><circle class="eye r" cx="13.9" cy="{eye}" r="0.9" fill="#24211d"/>{dots}</svg>')


def meridio_badge() -> str:
    return f'<div class="meridio">{meridio_svg(34)}</div>'


# ---- Proprietà del sottocampo ----

PROPS = [
    ("Sottocampo", [("Nome", "Copertura Sud", "text"), ("Montaggio", "Complanare", "combo"),
                    ("Modulo", "JKM475N", "btn"), ("Orientamento", "Verticale", "combo"),
                    ("Moduli per tavola, di traverso", "1", "spin"), ("Azimut", "Automatico", "check")]),
    ("Distanze e margini", [("Tra i moduli", "0,02 m", "spin"), ("Dal bordo dell'area", "0,50 m", "spin"),
                            ("Tra le file", "0,05 m", "spin"), ("Moduli per tavola, lungo", "file continue", "spin"),
                            ("Fuori dalle ombre", "", "check")]),
    ("Risultato della posa", [("Moduli", "156", "value"), ("Potenza", "74,1 kWp", "value"), ("Passo", "1,18 m", "value"),
                              ("Nota", "1 fila tolta per il corridoio VVF", "note")]),
]


def props(variant: str = "plain", help_: bool = False, summary: bool = False) -> str:
    """Le Proprietà di un sottocampo: `variant` decide come sono disegnati gruppi, campi e pulsanti (classi CSS)."""
    out = []
    for title, fields in PROPS:
        rows = []
        for label, value, kind in fields:
            h = f'<span class="help">{icon("help", 13)}</span>' if help_ and kind in ("spin", "combo") else ""
            if kind == "text":
                w = f'<div class="field">{value}</div>'
            elif kind == "combo":
                w = f'<div class="field combo">{value}</div>'
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
        head = f'<div class="gt">{title}{"<span class=\"help\">" + icon("help", 13) + "</span>" if help_ else ""}</div>'
        out.append(f'<div class="group g-{variant}">{head}<div class="form">{"".join(rows)}</div></div>')
    buttons = '<div class="hbox" style="margin-top:8px"><span class="btn primary">Posa i moduli</span><span class="btn">Svuota</span></div>'
    return f'<div class="props">{"".join(out)}{buttons}</div>'


CHECKS = [
    ("fail", "Copertura Sud: 3 moduli nell'ombra del Camino 1 nel giorno di progetto", "Posa", "DCPREV 14030/2025, 3.3.5.1"),
    ("warn", "Stringhe: 4 moduli non sono in nessuna stringa", "Stringhe", "CEI 64-8/7:2024"),
    ("warn", "Copertura Sud: 1 fila tolta per il corridoio dei Vigili del Fuoco", "Posa", "DCPREV 14030/2025"),
    ("info", "74,1 kW: connessione trifase; sopra 11,08 kW la protezione di interfaccia è un relè dedicato", "Connessione", "CEI 0-21, tab. 4"),
    ("info", "Prezzi e costi sono valori indicativi: inserisci quelli della bolletta", "Economia", ""),
    ("ok", "12 moduli in serie, tutte le verifiche superate", "Stringhe", "CEI 64-8/7:2024"),
]


def checks_panel() -> str:
    head = ('<div class="chead"><b>Verifiche</b> · 1 da correggere, 2 da controllare, 2 da sapere, 1 superata'
            '<span class="sp" style="flex:1"></span><span class="f on">✘</span><span class="f on">⚠</span><span class="f on">ℹ</span><span class="f on">✔</span></div>')
    rows = "".join(f'<div><span class="m {lv}">{ {"fail": "✘", "warn": "⚠", "info": "ℹ", "ok": "✔"}[lv]}</span><span>{html.escape(t)}</span>'
                   f'<span class="src">{html.escape(src)}</span></div>' for lv, t, _area, src in CHECKS[:4])
    return f'<div class="checks">{head}<div class="clist">{rows}</div></div>'


def statusbar() -> str:
    return ('<div class="status"><span>Sottocampo: disegna l\'area dove possono andare i moduli, sul tetto o a terra.</span>'
            '<span class="sp"></span><span class="cnt"><b style="color:var(--critical)">✘</b> 1</span>'
            '<span class="cnt"><b style="color:var(--warning-ink)">⚠</b> 2</span><span>12,4 × 8,6 m</span>'
            '<span>E 12,36  N 8,40 m</span><span>' + meridio_svg(14) + ' Meridio</span></div>')


def window(cls: str = "", menubar_html: str | None = None, tabs_html: str | None = None, toolbar_html: str | None = None,
           left: str | None = None, centre: str | None = None, right: str | None = None, checks: str | None = None,
           status: str | None = None, extra: str = "", rows: str = "") -> str:
    """La finestra intera; ogni parte si può sostituire. `rows` cambia le righe della griglia (per esempio senza barra)."""
    centre = centre if centre is not None else (
        f'<div class="centre"><div class="views"><div class="view plan">{plan_svg()}{viewbar("plan")}</div>'
        f'<div class="view d3">{view3d_svg()}{viewbar("3d")}</div></div>{sunbar()}</div>')
    left = left if left is not None else f'<div class="side left"><div class="ptitle">Progetto<span class="x">✕</span></div>{tree_plain()}</div>'
    right = right if right is not None else f'<div class="side right"><div class="ptitle">Proprietà<span class="x">✕</span></div>{props()}</div>'
    style = f' style="grid-template-rows:{rows}"' if rows else ""
    return (f'<div class="frame"><div class="mock {cls}"{style}>'
            f'{menubar_html if menubar_html is not None else menubar()}'
            f'{tabs_html if tabs_html is not None else tabs(0)}'
            f'{toolbar_html if toolbar_html is not None else toolbar()}'
            f'<div class="body">{left}{centre}{right}{checks if checks is not None else checks_panel()}</div>'
            f'{status if status is not None else statusbar()}{meridio_badge()}{extra}</div></div>')


def page(title: str, intro: str, body: str, extra_css: str = "", extra_js: str = "") -> str:
    return f'''<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{base_css()}{extra_css}</style>{CONTROLS_JS}</head>
<body><div class="page"><h1>{html.escape(title)}</h1>{intro}{controls()}{body}
<p style="margin-top:30px;font-size:13px">Studio 17, Meridiana. Colori da <code>theme_colors.py</code> (bronzo, fondi Meridiana); carattere Titillium Web dai file del repository; nessuna libreria, nessuna rete. <a href="index.html" style="color:var(--accent)">Indice dei bozzetti</a>.</p>
</div>{extra_js}</body></html>'''


def direction(title: str, mock: str, note: str) -> str:
    return f'<div class="dir"><h3>{title}</h3>{mock}<p class="note">{note}</p></div>'


def write(name: str, content: str) -> Path:
    out = Path(__file__).resolve().parent / name
    out.write_text(content, encoding="utf-8")
    return out


def lerp_hex(a: str, b: str, t: float) -> str:
    return tc.mix(a, b, t)


def polyline(values: list[float], x0: float, y0: float, w: float, h: float, vmax: float) -> str:
    n = len(values)
    pts = " ".join(f"{x0 + w * i / (n - 1):.1f},{y0 + h - h * v / vmax:.1f}" for i, v in enumerate(values))
    return pts


def synthetic_year(seed: int = 3) -> list[float]:
    """8.760 valori orari di produzione (kW) con una stagione e un giorno, deterministici."""
    out = []
    for hour in range(8760):
        d = hour // 24
        h = hour % 24
        season = 0.55 + 0.45 * math.cos((d - 172) / 365 * 2 * math.pi)
        day = max(0.0, math.sin((h - 6) / 13 * math.pi)) if 6 <= h <= 19 else 0.0
        cloud = 0.6 + 0.4 * abs(math.sin(d * 0.37 + seed) * math.cos(d * 0.11))
        out.append(round(74.1 * season * day * cloud, 2))
    return out
