"""The target of the graphic work (24/10/2026): one window with every choice Daniel made on the mockups of study 17,
drawn by the same HTML parts, at the size of the real window (1600 x 960 logical pixels, zoom 1), light and dark.
The real window is compared with these pictures side by side, part by part.

    python docs/studio/19-grafica/bersaglio.py          -> bersaglio-*.html next to this file

Choices (docs/richieste.md, 23/10/2026): A3 panels as cards; T2 tree with sections; B4 phases with the groups and the
text under the icons; C2 buttons and fields; C3 groups; R2 results; E3 help that follows the focus; F2 checks by level;
Meridio with the rays. Daniel's notes on the first target (24/10/2026): the help as a card of its own under the
properties; the same gap between every two cards, the bar of the tools included, and a wider margin at the window's
edge; the number of each phase inside its tab; the dark theme in neutral greys with clearer steps. Proposal on the
same day, to be decided: the menu bar hidden (Alt shows it) and a File page for what was in the menus."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "17-prove"))

import genera as G  # noqa: E402
import pagine_defg as D  # noqa: E402
import parti as P  # noqa: E402

W, H = 1600, 960
OUTER = 12          # the margin between the cards and the window's edge
GAP = 8             # between two cards, everywhere: the bar of the tools and the panels alike
RIGHT = 380         # the right column: Properties and Help
CHECKS = 214        # the height of the Checks card
BS = chr(92)

P.ICONS.update({
    "file-new": '<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4M12 11v6M9 14h6"/>',
    "folder": '<path d="M3 6h6l2 2h10v11H3z"/>',
    "save": '<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v5h7V3M8 21v-7h8v7"/>',
    "copy": '<rect x="8" y="8" width="12" height="13" rx="1"/><path d="M4 16V4h12"/>',
    "import": '<path d="M12 3v12M7 10l5 5 5-5M4 19h16"/>',
    "export": '<path d="M12 15V3M7 8l5-5 5 5M4 19h16"/>',
    "catalog": '<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M4 9h16M9 9v11"/>',
    "settings": ('<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1'
                 'M4.9 19.1L7 17M17 7l2.1-2.1"/>'),
    "curve": '<path d="M3 20h18M5 16l4-5 4 3 6-8"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="1"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-6-6-9 9"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/>',
    "inverter": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 14q2-4 4 0t4 0"/>',
    "back": '<path d="M15 6l-6 6 6 6"/>',
})

FRAME_CSS = f"""
.frame {{ width: {W}px; height: {H}px; border-radius: 0; box-shadow: none; border: none; }}
.mock {{ width: {W}px; height: {H}px; transform: none; grid-template-rows: 44px auto 1fr 30px; }}
.mock.filepage {{ grid-template-rows: 44px 1fr 30px; }}
.page {{ padding: 0; }}
.label {{ font: 600 15px "Titillium Web"; padding: 10px 0 6px; }}
"""

# the phases: tabs on the window, the number inside each tab; the tab in hand joins the card of its tools (B4)
TABS_CSS = f"""
.mock .tabs {{ display: flex; align-items: flex-end; gap: 2px; padding: 0 {OUTER}px; background: var(--window); border: none;
               position: relative; z-index: 2; }}
.mock .tabs .file {{ align-self: center; display: inline-flex; align-items: center; gap: 6px; height: 28px; margin: 6px 12px 0 0;
                     padding: 0 13px 0 10px; border-radius: 6px; background: var(--accent); color: var(--accent-fg); font-weight: 600;
                     font-size: 13.5px; }}
.mock .tabs .file svg {{ width: 15px; height: 15px; }}
.mock .tabs .file.on {{ box-shadow: 0 0 0 2px var(--window), 0 0 0 4px var(--accent); }}
.mock .tabs .tab {{ display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 16px 0 10px; color: var(--text2);
                    border: 1px solid transparent; border-bottom: none; border-radius: 8px 8px 0 0; font-size: 14px; }}
.mock .tabs .tab i {{ font-style: normal; display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 50%;
                      background: var(--line-soft); color: var(--muted); font-size: 11.5px; font-weight: 600; }}
.mock .tabs .tab.on {{ background: var(--panel); border-color: var(--line-soft); color: var(--text); font-weight: 600;
                       height: 37px; margin-bottom: -1px; }}
.mock .tabs .tab.on i {{ background: var(--accent); color: var(--accent-fg); }}
.mock .tabs .sp {{ flex: 1; }}
.mock .tabs .chip {{ align-self: center; margin-top: 6px; font-size: 12.5px; padding: 3px 10px; border-radius: 6px;
                     background: var(--sink); color: var(--text); }}
"""

TOOLS_CSS = f"""
.mock .tools {{ margin: 0 {OUTER}px; display: flex; align-items: stretch; gap: 2px; padding: 6px 10px 5px; background: var(--panel);
                border: 1px solid var(--line-soft); border-radius: 8px; box-shadow: 0 1px 3px var(--shadow); position: relative;
                z-index: 1; }}
.mock .tools .grp {{ display: flex; flex-direction: column; align-items: center; gap: 3px; }}
.mock .tools .gi {{ display: flex; gap: 2px; }}
.mock .tools .tb {{ display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 64px; padding: 5px 8px 4px;
                    border-radius: 6px; color: var(--text2); font-size: 12px; border: 1px solid transparent; }}
.mock .tools .tb svg {{ width: 22px; height: 22px; }}
.mock .tools .tb.on {{ background: var(--select-bg); color: var(--select-fg); border-color: var(--line); }}
.mock .tools .gl {{ font-size: 10px; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
.mock .tools .sep {{ width: 1px; background: var(--line-soft); margin: 4px 8px; }}
"""

BODY_CSS = f"""
.mock .body {{ display: grid; grid-template-columns: 320px 1fr {RIGHT}px; grid-template-rows: 1fr {CHECKS}px; gap: {GAP}px;
               padding: {GAP}px {OUTER}px 0; min-height: 0; background: var(--window); }}
.mock .pane {{ background: var(--panel); border: 1px solid var(--line-soft); border-radius: 8px; box-shadow: 0 1px 3px var(--shadow);
               overflow: hidden; display: flex; flex-direction: column; min-height: 0; }}
.mock .pane > .ptitle, .mock .checks .vbox > .ptitle {{ background: transparent; border: none; padding: 9px 12px 5px;
               font-size: 13.5px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 7px; }}
.mock .pane > .ptitle svg {{ width: 15px; height: 15px; color: var(--text2); }}
.mock .pane > .ptitle .x, .mock .checks .vbox > .ptitle .x {{ margin-left: auto; color: var(--muted); font-weight: 400; }}
.mock .left {{ grid-column: 1; grid-row: 1; }}
.mock .centre {{ grid-column: 2; grid-row: 1; display: grid; grid-template-rows: 1fr auto; background: var(--panel); }}
.mock .checks {{ grid-column: 1 / 3; grid-row: 2; border-top: 1px solid var(--line-soft); }}
.mock .rcol {{ grid-column: 3; grid-row: 1 / 3; display: flex; flex-direction: column; gap: {GAP}px; min-height: 0; }}
.mock .rcol .props-card {{ flex: 1; }}
.mock .help-card {{ flex: none; }}
.mock .help-card .hb {{ padding: 0 12px 12px; font-size: 13px; line-height: 1.45; color: var(--text2); }}
.mock .help-card .hb b {{ display: block; color: var(--text); margin-bottom: 2px; }}
.mock .help-card .links {{ display: flex; gap: 16px; margin-top: 8px; }}
.mock .help-card a {{ color: var(--accent); text-decoration: none; font-weight: 600; font-size: 12.5px; }}
.mock .props .focus {{ box-shadow: 0 0 0 2px var(--accent); }}
.mock .status {{ display: flex; align-items: center; gap: 14px; padding: 0 {OUTER + 4}px; border: none; font-size: 12px;
                 color: var(--text2); background: var(--window); }}
.mock .meridio {{ right: {OUTER + RIGHT + GAP + 14}px; bottom: {30 + CHECKS + GAP + 40}px; }}
"""

# C2 buttons and fields inside the window, C3 groups: the rules of genera.C_CSS moved from `.ctl .cN` to `.mock`
CONTROLS_CSS = """
.mock .field { height: 26px; padding: 0 7px; background: var(--sink); border: 1px solid transparent; color: var(--text); }
.mock .btn { height: 28px; padding: 0 14px; border-radius: 6px; font-weight: 600; background: var(--sink);
             border: 1px solid transparent; color: var(--text); }
.mock .btn.primary { background: var(--accent); color: var(--accent-fg); }
.mock .check i { background: var(--sink); border-color: transparent; }
.mock .check i.on { background: var(--accent); }
.mock .props { padding: 2px 12px 10px; }
.mock .group { border: 1px solid var(--line); border-radius: 4px; overflow: hidden; margin: 8px 0; }
.mock .group .gt { background: var(--line-soft); color: var(--text); padding: 4px 8px; margin: 0 0 6px; font-size: 13px; }
.mock .group .form { padding: 0 8px 8px; grid-template-columns: 1fr 150px; gap: 5px 8px; }
.mock .group .form label { color: var(--text2); }
.mock .value { font-weight: 600; text-align: right; }
.mock .note { grid-column: 1 / -1; color: var(--muted); font-size: 12px; }
.mock .hbox { display: flex; gap: 6px; }
"""

# F2 in the window: the rules of pagine_defg.F_CSS, scoped to the checks card
CHECKS_CSS = D.F_CSS.replace(".vbox {", ".vbox-x {").replace(".vrow", ".vrow-x") + """
.mock .checks .vbox { width: auto; border: none; border-radius: 0; background: transparent; height: 100%; overflow: hidden; }
"""

# the File page (proposal): what was in the menus, as a page of its own, like Office's and Revit's File
FILE_CSS = f"""
.mock .fcard {{ margin: 0 {OUTER}px; display: grid; grid-template-columns: 250px 1fr; min-height: 0; }}
.mock .fnav {{ border-right: 1px solid var(--line-soft); padding: 10px 8px; display: flex; flex-direction: column; gap: 2px;
               background: var(--panel); }}
.mock .fnav .it {{ display: flex; align-items: center; gap: 10px; height: 34px; padding: 0 10px; border-radius: 6px; color: var(--text);
                   font-size: 14px; }}
.mock .fnav .it svg {{ width: 18px; height: 18px; color: var(--text2); flex: none; }}
.mock .fnav .it .k {{ margin-left: auto; color: var(--muted); font-size: 12px; }}
.mock .fnav .it.on {{ background: var(--select-bg); color: var(--select-fg); font-weight: 600; }}
.mock .fnav .it.back {{ color: var(--text2); margin-bottom: 6px; }}
.mock .fnav .rule {{ height: 1px; background: var(--line-soft); margin: 6px 8px; }}
.mock .fbody {{ padding: 22px 28px; overflow: hidden; background: var(--panel); }}
.mock .fbody h2 {{ margin: 0 0 4px; font-size: 22px; font-weight: 600; }}
.mock .fbody .lead {{ margin: 0 0 18px; color: var(--text2); font-size: 14px; max-width: 760px; }}
.mock .fbody .sec {{ margin: 18px 0 8px; font-size: 11px; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted);
                     font-weight: 600; }}
.mock .fgrid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: {GAP}px; }}
.mock .ftile {{ background: var(--sink); border-radius: 8px; padding: 14px 16px; display: grid; grid-template-columns: 26px 1fr;
                gap: 2px 12px; }}
.mock .ftile svg {{ width: 24px; height: 24px; color: var(--text2); grid-row: 1 / 3; }}
.mock .ftile b {{ font-size: 14.5px; }}
.mock .ftile p {{ margin: 0; color: var(--text2); font-size: 13px; line-height: 1.4; }}
.mock .ftile .foot {{ grid-column: 2; display: flex; align-items: center; gap: 6px; margin-top: 10px; }}
.mock .ftile .fmt {{ font-size: 11.5px; padding: 1px 7px; border-radius: 10px; border: 1px solid var(--line); color: var(--text2); }}
.mock .ftile .btn {{ margin-left: auto; height: 28px; background: var(--panel); }}
.mock .recent {{ display: grid; grid-template-columns: 1fr auto; font-size: 13px; }}
.mock .recent div:nth-child(odd) {{ padding-right: 16px; }}
.mock .recent div {{ padding: 7px 0; border-bottom: 1px solid var(--line-soft); }}
.mock .recent .p {{ color: var(--muted); font-size: 12px; }}
"""

PHASES = ("Modello", "Impianto", "Producibilità", "Consumi", "Bilancio ed economia", "Relazione")


def tabs(active: int | None = 0, file_on: bool = False) -> str:
    items = "".join(f'<div class="tab {"on" if i == active else ""}"><i>{i + 1}</i>{name}</div>'
                    for i, name in enumerate(PHASES))
    return (f'<div class="tabs"><div class="file {"on" if file_on else ""}">{P.icon("folder", 15)}File</div>{items}'
            '<div class="sp"></div><div class="chip">Variante: Base ⌄</div></div>')


GROUPS = [("Disegna", (("building", "Edificio"), ("pitch", "Falda"), ("subfield", "Sottocampo"), ("exclusion", "Esclusione"),
                       ("strings", "Fila"))),
          ("Modifica", (("select", "Seleziona"), ("move", "Sposta"), ("measure", "Misura"))),
          ("Posa", (("subfield", "Posa i moduli"),))]


def tools() -> str:
    out = []
    for label, items in GROUPS:
        tbs = "".join(f'<div class="tb {"on" if name == "Sottocampo" else ""}">{P.icon(key, 22)}<span>{name}</span></div>'
                      for key, name in items)
        out.append(f'<div class="grp"><div class="gi">{tbs}</div><div class="gl">{label}</div></div>')
    return '<div class="tools">' + '<div class="sep"></div>'.join(out) + "</div>"


def checks() -> str:
    it = D.ITEMS

    def lvl(lv, title, rows):
        return f'<div class="lvlhead"><span class="m {lv}">{D.MARK[lv]}</span>{title}</div><div class="card">{rows}</div>'
    body = (lvl("fail", "Da correggere · 1", D.item(it[0][0], f"{it[0][2]}: {it[0][1]}", it[0][4], chev="⌄")
                + f'<div class="detail">{it[0][5]}</div>')
            + lvl("warn", "Da controllare · 2", D.item(it[1][0], f"{it[1][2]}: {it[1][1]}", it[1][4])
                  + D.item(it[2][0], f"{it[2][2]}: {it[2][1]}", it[2][4])))
    return (f'<div class="pane checks"><div class="vbox"><div class="ptitle">Verifiche<span class="x">✕</span></div>'
            f'{D.chead("<span class=f>Per livello ⌄</span>")}{body}</div></div>')


def help_card() -> str:
    text = ("Fascia libera lungo il contorno dell'area, dove i moduli non vanno: serve per la manutenzione e per le regole "
            "dei Vigili del Fuoco. Con l'attività soggetta vale almeno 1 m e Meridiana la impone da sola "
            "(DCPREV 14030/2025, 3.3.5.1).")
    return (f'<div class="pane help-card"><div class="ptitle">{P.icon("book", 15)}Aiuto<span class="x">✕</span></div>'
            f"<div class=\"hb\"><b>Dal bordo dell'area</b>{text}"
            '<div class="links"><a>Manuale ›</a><a>Come è calcolato ›</a><a>Chiedi a Meridio ›</a></div></div></div>')


def props_card() -> str:
    body = P.props("x").replace('<div class="field">0,50 m', '<div class="field focus">0,50 m', 1)
    return f'<div class="pane props-card"><div class="ptitle">Proprietà<span class="x">✕</span></div>{body}</div>'


def window() -> str:
    left = f'<div class="pane left"><div class="ptitle">Progetto<span class="x">✕</span></div>{G.tree_sections()}</div>'
    centre = (f'<div class="pane centre"><div class="views"><div class="view plan">{P.plan_svg()}{P.viewbar("plan")}</div>'
              f'<div class="view d3">{P.view3d_svg()}{P.viewbar("3d")}</div></div>{P.sunbar()}</div>')
    right = f'<div class="rcol">{props_card()}{help_card()}</div>'
    return (f'<div class="frame"><div class="mock">{tabs(0)}{tools()}'
            f'<div class="body">{left}{centre}{right}{checks()}</div>{P.statusbar()}{P.meridio_badge()}</div></div>')


IMPORTS = (
    ("Progetto", (
        ("folder", "Progetto PVsyst",
         "Il progetto e le varianti accanto, come progetto nuovo: Meridiana dice cosa ha approssimato.", (".PRJ",),
         "Scegli il file…"),
        ("image", "Immagine sotto il disegno", "Una planimetria o una foto aerea, da mettere in scala sulla pianta.",
         ("PNG", "JPEG", "PDF"), "Scegli il file…"),
        ("globe", "Anno tipo e orizzonte", "Dal servizio europeo PVGIS per il sito del progetto; poi restano nella cache.",
         ("PVGIS",), "Scarica"))),
    ("Cataloghi e consumi", (
        ("subfield", "Modulo da PVsyst", "Nel catalogo dei moduli, con i parametri del modello a un diodo.", (".PAN",),
         "Scegli il file…"),
        ("inverter", "Inverter da PVsyst", "Nel catalogo degli inverter, con la curva di rendimento.", (".OND",),
         "Scegli il file…"),
        ("curve", "Curva di carico", "I consumi misurati ogni 15 minuti o ogni ora, al posto del profilo.", ("CSV",),
         "Scegli il file…"))),
)
NAV = (("back", "Torna al progetto", "Esc"), None, ("file-new", "Nuovo", "Ctrl+N"), ("folder", "Apri", "Ctrl+O"),
       ("save", "Salva", "Ctrl+S"), ("copy", "Salva una revisione", "_R01"), None, ("import", "Importa", ""),
       ("export", "Esporta", ""), None, ("catalog", "Cataloghi", ""), ("settings", "Impostazioni", "Ctrl+,"),
       ("help", "Aiuto e manuale", "F1"), ("info", "Informazioni", ""))


def file_page() -> str:
    nav = []
    for entry in NAV:
        if entry is None:
            nav.append('<div class="rule"></div>')
            continue
        key, name, k = entry
        cls = "on" if name == "Importa" else ("back" if key == "back" else "")
        nav.append(f'<div class="it {cls}">{P.icon(key, 18)}<span>{name}</span><span class="k">{k}</span></div>')
    sections = []
    for title, tiles in IMPORTS:
        cells = "".join(f'<div class="ftile">{P.icon(ic, 24)}<b>{name}</b><p>{desc}</p><div class="foot">'
                        + "".join(f'<span class="fmt">{f}</span>' for f in fmts)
                        + f'<span class="btn">{btn}</span></div></div>'
                        for ic, name, desc, fmts, btn in tiles)
        sections.append(f'<div class="sec">{title}</div><div class="fgrid">{cells}</div>')
    where = BS.join(("D:", "Progetti", "Capannone", "PVsyst"))
    recent = ('<div class="sec">Importati di recente</div><div class="recent">'
              f'<div>Capannone Rho.PRJ <span class="p">{where}</span></div><div class="p">ieri</div>'
              '<div>JKM475N-60HL4-V.PAN <span class="p">Download</span></div><div class="p">22/10/2026</div></div>')
    body = ('<div class="fbody"><h2>Importa</h2><p class="lead">Quello che viene da altri programmi o da un file. Meridiana lo '
            'legge, ti dice cosa ha preso e cosa ha approssimato, e lo puoi annullare.</p>'
            f'{"".join(sections)}{recent}</div>')
    card = f'<div class="pane fcard"><div class="fnav">{"".join(nav)}</div>{body}</div>'
    return f'<div class="frame"><div class="mock filepage">{tabs(None, file_on=True)}{card}{P.statusbar()}</div></div>'


def render(body: str, title: str) -> str:
    css = (G.TREE_CSS.replace(".treebox", ".mock") + CONTROLS_CSS + CHECKS_CSS + TABS_CSS + TOOLS_CSS + BODY_CSS + FILE_CSS
           + FRAME_CSS)
    html = P.page(title, "", body, css).replace(f"<h1>{title}</h1>", "")
    html = html.replace(P.controls(), "")
    return html.replace(P.FONT_DIR, "../../../data/fonts/titillium-web")


def main() -> None:
    pages = {"bersaglio": (window(), "Bersaglio della grafica"),
             "bersaglio-file": (file_page(), "Bersaglio: la pagina File (proposta)")}
    for name, (body, title) in pages.items():
        html = render(body, title)
        for theme in ("chiaro", "scuro"):
            out = html if theme == "chiaro" else html.replace('<html lang="it">', '<html lang="it" class="dark">').replace(
                "try { setTheme(localStorage.getItem('m17-dark') === '1'); } catch (e) { setTheme(false); }", "setTheme(true);")
            (HERE / f"{name}-{theme}.html").write_text(out, encoding="utf-8")
            print("scritto", HERE / f"{name}-{theme}.html")


if __name__ == "__main__":
    main()
