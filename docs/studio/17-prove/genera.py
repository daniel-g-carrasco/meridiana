"""Genera i bozzetti dello studio 17 (pagine HTML che si aprono da sole nel browser, in questa cartella):

    python docs/studio/17-prove/genera.py

Ogni tema ha la sua pagina con almeno tre direzioni una accanto all'altra, sul layout vero di Meridiana, in chiaro e
in scuro (interruttore in cima, ricordato dal browser). Le parti comuni sono in parti.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import parti as P  # noqa: E402
from parti import direction, icon, page, window, write  # noqa: E402

INDEX = []


def save(name: str, title: str, content: str, summary: str) -> None:
    write(name, content)
    INDEX.append((name, title, summary))


# ============================================================ A. le parti dell'interfaccia

A_CSS = """
/* A1: tre livelli di superficie. finestra (scura) < pannelli (media) < viste e campi (chiara) */
.mock.a1 .menubar, .mock.a1 .tabs, .mock.a1 .toolbar, .mock.a1 .status { background: var(--window); }
.mock.a1 .side, .mock.a1 .checks { background: var(--panel); }
.mock.a1 .body { gap: 1px; background: var(--line); }
.mock.a1 .ptitle { background: var(--panel); border-bottom: 1px solid var(--line); font-size: 12px; letter-spacing: 0.04em;
                   text-transform: uppercase; color: var(--muted); padding: 7px 10px; }
.mock.a1 .view { background: var(--plan-bg); }
/* A2: un livello solo, separatori e intestazioni piene */
.mock.a2 .side, .mock.a2 .checks, .mock.a2 .menubar, .mock.a2 .tabs, .mock.a2 .toolbar, .mock.a2 .status { background: var(--window); }
.mock.a2 .side.left { border-right: 1px solid var(--line); } .mock.a2 .side.right { border-left: 1px solid var(--line); }
.mock.a2 .ptitle { background: var(--line-soft); color: var(--text); border-bottom: 1px solid var(--line); padding: 6px 10px; }
.mock.a2 .toolbar { border-bottom: 1px solid var(--line); }
.mock.a2 .checks .chead { background: var(--line-soft); border-bottom: 1px solid var(--line); }
/* A3: pannelli come schede che galleggiano sulla finestra, con angoli e spazi (libadwaita, Fluent) */
.mock.a3 .body { gap: 8px; padding: 0 8px 8px; background: var(--window); }
.mock.a3 .side, .mock.a3 .checks { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 8px; overflow: hidden;
                                   box-shadow: 0 1px 3px var(--shadow); }
.mock.a3 .checks { border-top: 1px solid var(--line-soft); }
.mock.a3 .ptitle { background: transparent; border-bottom: none; font-size: 13px; color: var(--text); padding: 8px 12px 4px; }
.mock.a3 .centre { border-radius: 8px; overflow: hidden; border: 1px solid var(--line-soft); box-shadow: 0 1px 3px var(--shadow); }
.mock.a3 .toolbar { background: var(--window); padding: 4px 8px 6px; }
.mock.a3 .status { border-top: none; }
"""

TREE_CSS = """
.treebox { width: 250px; height: 330px; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden;
           font-size: 13px; }
.treebox .ptitle { padding: 6px 10px; font-weight: 600; font-size: 12px; color: var(--text2); border-bottom: 1px solid var(--line-soft); }
.treebox .tree { padding: 6px 4px; line-height: 1.7; }
.treebox .tree div { display: flex; align-items: center; gap: 6px; padding: 0 6px; border-radius: 4px; white-space: nowrap; }
.treebox .tree div.sel { background: var(--select-bg); color: var(--select-fg); }
.treebox .tree svg { width: 15px; height: 15px; color: var(--text2); flex: none; }
.treebox .tree .mark { margin-left: auto; font-size: 11px; padding: 0 6px; border-radius: 8px; color: #fff; }
.treebox .tree .mark.warn { background: var(--warning-ink); } .treebox .tree .mark.info { background: var(--muted); }
.treebox .tree .lvl1 { padding-left: 22px; } .treebox .tree .lvl2 { padding-left: 40px; }
.treebox .sec { margin-top: 8px; padding: 2px 8px 0; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.treebox .sec .n { margin-left: 6px; font-weight: 400; letter-spacing: 0; text-transform: none; }
.treebox.t3 .tree { padding: 6px; }
.treebox.t3 .card { background: var(--card); border: 1px solid var(--line-soft); border-radius: 6px; margin: 6px 0; padding: 4px 2px; }
.treebox.t3 .card .sec { margin-top: 0; }
.treebox .cnt { color: var(--muted); font-size: 12px; }
.treebox .chev { color: var(--muted); width: 12px; }
.treerow { display: flex; gap: 22px; flex-wrap: wrap; }
.treerow .dir .note { max-width: 250px; }
"""


def tree_sections(cards: bool = False) -> str:
    def sec(title, n):
        return f'<div class="sec">{title}<span class="n">{n}</span></div>'

    def row(lvl, ic, text, cls="", mark=None, chev=""):
        m = f'<span class="mark {mark[0]}">{mark[1]}</span>' if mark else ""
        c = f'<span class="chev">{chev}</span>' if chev else ""
        return f'<div class="lvl{lvl} {cls}">{c}{icon(ic, 15)}<span>{text}</span>{m}</div>'

    site = row(0, "site", "Capannone Rho", "sel", ("info", 3))
    b = (sec("Edifici", 2) + row(0, "building", "Edificio 1", "", None, "⌄") + row(1, "pitch", "Falda 1 · Sud 19°") +
         row(1, "pitch", "Falda 2 · Nord 19°") + row(0, "building", "Uffici", "", None, "›"))
    s = (sec("Sottocampi", "2 · 188 moduli") + row(0, "subfield", "Copertura Sud <span class=cnt>156</span>", "", ("warn", 1)) +
         row(0, "subfield", "Copertura Nord <span class=cnt>32</span>"))
    e = (sec("Esclusioni", 3) + row(0, "exclusion", "Lucernario 1") + row(0, "exclusion", "Lucernario 2") + row(0, "exclusion", "Camino 1"))
    if cards:
        body = site + "".join(f'<div class="card">{x}</div>' for x in (b, s, e))
    else:
        body = site + b + s + e
    return f'<div class="tree">{body}</div>'


def page_a() -> str:
    intro = ("<p>R18 e R30. Daniel: «Non c'è grande distinzione tra menu e sottomenu (strumenti, proprietà, barre laterali, verifiche)»; "
             "l'albero è «senza spaziatura tra le sezioni, il tutto poco chiaro». Tre direzioni per i livelli di superficie, poi tre per "
             "l'albero del progetto. La barra degli strumenti qui è quella di oggi: dove metterla è il tema B.</p>")
    a0 = direction("A0. Oggi", window("a0"), "Com'è adesso: stessi fondi quasi ovunque, titoli dei pannelli uguali al testo normale, "
                   "nessuno stacco tra le barre e i pannelli.")
    a1 = direction("A1. Tre livelli di superficie",
                   window("a1"),
                   "<b>Finestra</b> (menu, schede, strumenti, stato) sul fondo più scuro, <b>pannelli</b> sul fondo medio, "
                   "<b>viste e campi</b> sul fondo più chiaro; un filo di linea tra le parti; titoli in maiuscoletto attenuato. "
                   "È la regola di libadwaita (window, sidebar, view) e di VS Code (sideBar, editor). In scuro i tre livelli sono "
                   "#14181e, #1a1f26, #101318, già nel tema.")
    a2 = direction("A2. Un livello e intestazioni piene",
                   window("a2"),
                   "Un fondo solo, separatori di 1 px e <b>intestazioni piene</b> (una striscia appena più scura con il titolo) "
                   "per i pannelli e per le Verifiche: il modello di Revit e di Blender (header delle regioni). Meno «disegno», "
                   "ma le intestazioni fanno il lavoro.")
    a3 = direction("A3. Pannelli come schede",
                   window("a3"),
                   "I pannelli e le viste sono <b>schede arrotondate</b> che galleggiano sulla finestra con 8 px di spazio e un'ombra "
                   "leggera; i titoli dentro la scheda. È il «layering» di Fluent 2 e le «cards» di libadwaita. Costa spazio "
                   "(8 px per lato) e in Qt richiede un contenitore per ogni dock.")
    trees = (direction("T1. Oggi", f'<div class="treebox"><div class="ptitle">Progetto</div>{P.tree_plain()}</div>',
                       "Una lista indentata: il sito, poi edifici, sottocampi ed esclusioni di seguito, il segno delle verifiche piccolo.") +
             direction("T2. Sezioni con intestazioni", f'<div class="treebox t2"><div class="ptitle">Progetto</div>{tree_sections()}</div>',
                       "<b>Intestazioni di sezione</b> in maiuscoletto con il conteggio (VS Code, Explorer), 8 px di aria sopra ognuna, "
                       "le freccine per aprire e chiudere, i conteggi dei moduli attenuati, i segni delle verifiche come pillole leggibili.") +
             direction("T3. Sezioni come schede", f'<div class="treebox t3"><div class="ptitle">Progetto</div>{tree_sections(True)}</div>',
                       "Ogni sezione in una <b>scheda</b> sul fondo del pannello (boxed list di libadwaita). Più chiara da lontano, "
                       "più alta: con molti oggetti si scorre prima."))
    body = (f'<h2>I livelli di superficie</h2><div class="row">{a0}{a1}{a2}{a3}</div>'
            f'<h2>L\'albero del progetto</h2><div class="treerow">{trees}</div>')
    return page("A. Distinguere le parti dell'interfaccia", intro, body, A_CSS + TREE_CSS)


# ============================================================ B. dove stanno gli strumenti

B_CSS = """
.mock.b1 .toolbar { background: var(--panel); border-bottom: 1px solid var(--line); padding-left: 14px; }
.mock.b1 .tabs { border-bottom: none; }
.mock.b1 .toolbar .lab { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-right: 8px; }
.mock.b2 { grid-template-rows: 28px 34px 1fr 24px; }
.mock.b2 .body { grid-template-columns: 44px 220px 1fr 300px; }
.mock.b2 .rail { background: var(--panel); border-right: 1px solid var(--line); display: flex; flex-direction: column; align-items: center;
                 padding: 6px 0; gap: 4px; }
.mock.b2 .rail .tb { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 6px; color: var(--text2); }
.mock.b2 .rail .tb.on { background: var(--select-bg); color: var(--select-fg); box-shadow: inset 2px 0 0 var(--accent); }
.mock.b2 .rail .sep { width: 20px; height: 1px; background: var(--line); margin: 4px 0; }
.mock.b3 { grid-template-rows: 28px 34px 1fr 24px; }
.mock.b3 .floatbar { position: absolute; left: 50%; top: 10px; transform: translateX(-50%); display: flex; gap: 2px; padding: 3px;
                     background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 2px 8px var(--shadow); }
.mock.b3 .floatbar .tb { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 6px; color: var(--text2); }
.mock.b3 .floatbar .tb.on { background: var(--select-bg); color: var(--select-fg); }
.mock.b3 .viewbar { top: auto; bottom: 8px; }
.mock.b4 .tabs { padding: 0 10px; gap: 0; }
.mock.b4 .tabs span { padding: 6px 14px 5px; border-bottom: none; position: relative; }
.mock.b4 .tabs span.on::before { display: none; }
.mock.b4 .tabs span.on { background: var(--panel); border: 1px solid var(--line); border-bottom: 1px solid var(--panel); border-radius: 6px 6px 0 0; margin-bottom: -1px; }
.mock.b4 .tabs span.num { color: var(--muted); font-size: 11px; padding: 6px 2px 5px 10px; }
.mock.b4 .toolbar { background: var(--panel); border-bottom: 1px solid var(--line); padding: 4px 12px; gap: 8px; }
.mock.b4 .toolbar .tb { flex-direction: column; gap: 2px; padding: 3px 8px; font-size: 11px; }
.mock.b4 .toolbar .tb svg { width: 20px; height: 20px; }
.mock.b4 .toolbar .grp { display: flex; flex-direction: column; align-items: center; }
.mock.b4 .toolbar .grp .gl { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.mock.b4 .toolbar .grp .gi { display: flex; }
"""


def page_b() -> str:
    intro = ("<p>R19, seconda parte. Daniel: «mi chiedo se inoltre non debbano stare loro sotto il menù con scritto \"modello, producibilità, "
             "consumi, ecc.\" essendo che loro sono controlli della modellazione». I comandi delle viste (Pianta, 3D, Affiancate, Inquadra, "
             "F3, F8) sono già decisi dentro le viste (ritocchi, passo 2) e qui compaiono così. La barra mostra solo le icone, come deciso "
             "(ritocchi, passo 3); i nomi stanno nei suggerimenti.</p>")
    b1 = direction("B1. Barra sotto le schede, legata a Modello",
                   window("b1", toolbar_html=P.toolbar(extra_left='<span class="lab">Disegna</span>')),
                   "La barra sta <b>sotto la scheda Modello</b> e appartiene a lei: nelle altre schede sparisce (Producibilità ha i suoi "
                   "comandi, Calcola e PVGIS). Un'etichetta «Disegna» dice cos'è. È il modello della ribbon di Revit e dei «tool settings» "
                   "di Blender: gli strumenti sono contestuali alla scheda.")
    rail = "".join(f'<span class="tb {"on" if k == "subfield" else ""}" title="{n} ({key})">{icon(k, 20)}</span>' for k, n, key in P.TOOLS)
    rail += f'<span class="sep"></span><span class="tb">{icon("sun", 20)}</span>'
    b2_centre = (f'<div class="rail">{rail}</div>'
                 f'<div class="side left"><div class="ptitle">Progetto<span class="x">✕</span></div>{P.tree_plain()}</div>'
                 f'<div class="centre"><div class="views"><div class="view plan">{P.plan_svg()}{P.viewbar("plan")}</div>'
                 f'<div class="view d3">{P.view3d_svg()}{P.viewbar("3d")}</div></div>{P.sunbar()}</div>')
    b2 = direction("B2. Barra laterale a icone",
                   window("b2", toolbar_html="", left="", centre=b2_centre),
                   "Una <b>colonna di icone</b> di 44 px sul fianco sinistro, prima del pannello Progetto, come la toolbar «T» di Blender "
                   "e l'activity bar di VS Code; lo strumento attivo ha la riga d'accento. Libera una riga in alto; sulle altre schede "
                   "la colonna resta ma cambia contenuto (o sparisce).")
    fbar = "".join(f'<span class="tb {"on" if k == "subfield" else ""}" title="{n} ({key})">{icon(k, 18)}</span>' for k, n, key in P.TOOLS)
    b3_centre = (f'<div class="centre"><div class="views"><div class="view plan">{P.plan_svg()}{P.viewbar("plan")}'
                 f'<div class="floatbar">{fbar}</div></div><div class="view d3">{P.view3d_svg()}{P.viewbar("3d")}</div></div>{P.sunbar()}</div>')
    b3 = direction("B3. Barra dentro la vista",
                   window("b3", toolbar_html="", centre=b3_centre),
                   "Gli strumenti <b>galleggiano sopra la pianta</b>, in alto al centro, come in Aurora, OpenSolar e nelle app di disegno; "
                   "i comandi di vista restano nell'angolo in basso. Vicino a dove si lavora, ma copre una striscia di disegno e nel 3D "
                   "non c'è (lì gli strumenti di disegno non servono).")
    phases = ('<div class="tabs"><span class="num">1</span><span class="on">Modello</span><span class="num">2</span><span>Impianto</span>'
              '<span class="num">3</span><span>Producibilità</span><span class="num">4</span><span>Consumi</span>'
              '<span class="num">5</span><span>Bilancio ed economia</span><span class="num">6</span><span>Relazione</span></div>')
    groups = [("Disegna", ("building", "pitch", "subfield", "exclusion")), ("Modifica", ("select", "move", "measure")),
              ("Sole", ("sun",)), ("Sfondo", ("layers", "eye"))]
    names = {k: n for k, n, _x in P.TOOLS}
    names.update({"move": "Sposta", "sun": "Sole", "layers": "Livelli", "eye": "Ortofoto"})
    tb = ""
    for gl, keys in groups:
        gi = "".join(f'<span class="tb {"on" if k == "subfield" else ""}">{icon(k, 20)}<span>{names[k]}</span></span>' for k in keys)
        tb += f'<div class="grp"><div class="gi">{gi}</div><div class="gl">{gl}</div></div><span class="sep"></span>'
    b4 = direction("B4. Fasi alla DIALux, con i gruppi",
                   window("b4", tabs_html=phases, toolbar_html=f'<div class="toolbar">{tb}</div>'),
                   "Le schede diventano <b>fasi numerate</b> (Modello, Impianto, Producibilità, Consumi, Bilancio, Relazione), come i modi "
                   "di DIALux evo e i passi di HelioScope; sotto, una barra alla ribbon con i gruppi etichettati (Disegna, Modifica, Sole, "
                   "Sfondo). Chiarissima, ma più alta (76 px) e con il testo sotto le icone, che Daniel ha detto di non volere.")
    body = f'<div class="row">{b1}{b2}{b3}{b4}</div>'
    return page("B. Dove stanno gli strumenti", intro, body, B_CSS)


# ============================================================ C. pulsanti, campi e gruppi

C_CSS = """
.ctl { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; }
.ctl .box { background: var(--window); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
.ctl h3 { margin: 0 0 10px; font-size: 16px; }
.ctl .samples { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 8px 0 14px; }
.ctl .side { width: 310px; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; font-size: 13px; }
.ctl .side .ptitle { padding: 6px 10px; font-weight: 600; font-size: 12px; color: var(--text2); border-bottom: 1px solid var(--line-soft); }
.ctl .props { padding: 6px 8px; }
.ctl .group { margin: 8px 0; }
.ctl .group .gt { font-weight: 600; font-size: 12px; color: var(--text2); padding: 2px 0; }
.ctl .form { display: grid; grid-template-columns: 1fr 128px; gap: 5px 8px; align-items: center; }
.ctl .form label { color: var(--text2); }
.ctl .hbox { display: flex; gap: 6px; }
.ctl .value { font-weight: 600; text-align: right; }
.ctl .note { grid-column: 1 / -1; color: var(--muted); font-size: 12px; }
.ctl .check { display: flex; gap: 6px; align-items: center; }
.ctl .check i { width: 14px; height: 14px; border: 1px solid var(--line); border-radius: 3px; background: var(--view); }
.ctl .check i.on { background: var(--accent); border-color: var(--accent); }
.ctl .field { display: flex; align-items: center; justify-content: space-between; height: 26px; padding: 0 7px; border-radius: 4px; }
.ctl .field .arr { color: var(--muted); font-size: 10px; letter-spacing: -2px; }
.ctl .field.combo::after { content: "⌄"; color: var(--muted); }
.ctl .btn { display: inline-flex; align-items: center; justify-content: center; height: 28px; padding: 0 14px; border-radius: 6px; font-weight: 600; }
.ctl .help { display: none; }
/* C1: Fusion ritoccato: pulsante con fondo leggero e bordo, campo con fondo vista e bordo; gruppo con titolo e riga */
.c1 .btn { background: var(--raise); border: 1px solid var(--line); color: var(--text); box-shadow: 0 1px 0 var(--sink); }
.c1 .btn.primary { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.c1 .btn.flat { background: transparent; border-color: transparent; box-shadow: none; color: var(--accent); }
.c1 .field { background: var(--view); border: 1px solid var(--line); color: var(--text); }
.c1 .field.focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
.c1 .group .gt { border-bottom: 1px solid var(--line); margin-bottom: 6px; }
/* C2: alla GNOME: pulsanti tonali pieni senza bordo, campi pieni, gruppi come schede piene con angoli */
.c2 .btn { background: var(--sink); border: 1px solid transparent; color: var(--text); }
.c2 .btn.primary { background: var(--accent); color: var(--accent-fg); }
.c2 .btn.flat { background: transparent; color: var(--accent); }
.c2 .field { background: var(--sink); border: 1px solid transparent; color: var(--text); }
.c2 .field.focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
.c2 .group { background: var(--card); border: 1px solid var(--line-soft); border-radius: 8px; padding: 8px 10px 10px; }
.c2 .group .gt { color: var(--text); font-size: 13px; margin-bottom: 6px; }
.c2 .check i { background: var(--sink); border-color: transparent; }
.c2 .check i.on { background: var(--accent); }
/* C3: contorni forti: pulsanti a contorno, campi con bordo da 1,5 px, gruppi con cornice e intestazione piena */
.c3 .btn { background: transparent; border: 1.5px solid var(--text2); color: var(--text); }
.c3 .btn.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.c3 .btn.flat { border-color: transparent; color: var(--accent); }
.c3 .field { background: var(--view); border: 1.5px solid var(--text2); color: var(--text); border-radius: 3px; }
.c3 .field.focus { border-color: var(--accent); }
.c3 .group { border: 1px solid var(--line); border-radius: 4px; overflow: hidden; }
.c3 .group .gt { background: var(--line-soft); color: var(--text); padding: 4px 8px; margin: 0 0 6px; }
.c3 .group .form { padding: 0 8px 8px; }
/* i riquadri dei risultati */
.res { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; margin-top: 10px; }
.res .box { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
.res h3 { margin: 0 0 10px; font-size: 16px; }
.res .cards { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.res .card { border-radius: 6px; padding: 8px 10px; }
.res .card .k { font-size: 12px; color: var(--text2); }
.res .card .v { font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums; }
.res .card .u { font-size: 12px; color: var(--muted); margin-left: 3px; font-weight: 400; }
.res .card .s { font-size: 11px; color: var(--muted); }
.res .card .s a { color: var(--accent); text-decoration: none; }
.r1 .card { background: var(--card); border: 1px solid var(--line-soft); }
.r2 .card { background: var(--sink); }
.r2 .card.key { background: var(--accent-soft); }
.r3 .card { border-bottom: 1px solid var(--line); border-radius: 0; padding-left: 0; }
.r3 .card .v { color: var(--accent); }
.contrast { font-size: 13px; color: var(--text2); margin-top: 8px; }
"""


def props_block(variant: str) -> str:
    return f'<div class="side {variant}"><div class="ptitle">Proprietà</div>{P.props(variant)}</div>'


def samples(variant: str) -> str:
    return (f'<div class="samples {variant}"><span class="btn primary">Calcola</span><span class="btn">Catalogo…</span>'
            f'<span class="btn flat">Come è calcolato</span><div class="field" style="width:120px">12,36 m</div>'
            f'<div class="field focus" style="width:120px">10 m + 50 cm</div><div class="field combo" style="width:150px">Complanare alla falda</div>'
            f'<div class="check"><i class="on"></i>Fuori dalle ombre</div></div>')


RESULTS = [("Produzione annua", "92.410", "kWh", "da PVGIS, anno tipo 2005-2023"), ("Resa specifica", "1.247", "kWh/kWp", "calcolata"),
           ("Performance ratio", "82,6", "%", "calcolato"), ("Autoconsumo", "61", "%", "con i consumi stimati"),
           ("Perdita per ombre vicine", "3,4", "%", "ostacoli della scena"), ("VAN a 20 anni", "48.300", "€", "prezzi indicativi")]


def results_block(variant: str, title: str, note: str) -> str:
    cards = "".join(f'<div class="card {"key" if i == 0 else ""}"><div class="k">{k}</div><div class="v">{v}<span class="u">{u}</span></div>'
                    f'<div class="s">{s} · <a href="#">come è calcolato</a></div></div>' for i, (k, v, u, s) in enumerate(RESULTS))
    return f'<div class="box {variant}"><h3>{title}</h3><div class="cards">{cards}</div><p class="contrast">{note}</p></div>'


def page_c() -> str:
    intro = ("<p>R22. Daniel: «il design di tasti e bottoni non è il massimo. […] Le caselle di input non si distinguono bene dallo sfondo "
             "(almeno in modalità scura) e sarebbe buono dare alle varie sottosezioni un contorno più evidente […]. Anche i contorni all'interno "
             "dei risultati di consumi, bilancio ed economia, producibilità, non si leggono. […] non è possibile usare un approccio alla gnome "
             "nel quale sottosezioni e tasti non solo hanno contorno ma riempimento come il contorno?». Tre direzioni per pulsanti, campi e "
             "gruppi, poi tre per i riquadri dei risultati. Il colore d'accento è il bronzo in chiaro e il sole pallido in scuro.</p>")
    c = ""
    for variant, title, note in (
        ("c1", "C1. Fusion ritoccato", "Pulsanti con <b>fondo leggero e bordo</b> (come Fusion, ma con il bordo del tema e un'ombra di 1 px), "
         "campi con il fondo della vista e il bordo, gruppi con titolo e riga sotto. Il più vicino a oggi: cambia solo il foglio di stile. "
         "In scuro il campo (#101318) si stacca dal pannello (#1a1f26) per 1,5:1 più il bordo #2b323c."),
        ("c2", "C2. Alla GNOME, tonale", "Pulsanti <b>pieni senza bordo</b> (un velo del testo al 6-10 %, come i «button» di Adwaita), "
         "il pulsante principale pieno d'accento, campi pieni dello stesso velo, <b>gruppi come schede</b> arrotondate con fondo proprio "
         "(preferences groups, boxed lists). Il riempimento «come il contorno» che chiede Daniel. In scuro i campi hanno un velo nero al 22 %."),
        ("c3", "C3. Contorni forti", "Pulsanti <b>a contorno</b> di 1,5 px nel colore del testo secondario, campi con bordo di 1,5 px, "
         "gruppi con cornice e <b>intestazione piena</b>. Si legge sempre (WCAG 1.4.11: bordi a 3:1 garantiti), ma è la più «disegnata» "
         "e i contorni si sommano a quelli dei pannelli.")):
        c += f'<div class="box"><h3>{title}</h3>{samples(variant)}{props_block(variant)}<p class="contrast">{note}</p></div>'
    r = (results_block("r1", "R1. Schede dei risultati", "Ogni numero in una <b>scheda</b> con fondo e bordo leggero, l'unità piccola, la fonte e il "
                       "collegamento a «Come è calcolato». Legge bene in griglia; i contorni si vedono anche in scuro (#1a1f26 su #14181e più il bordo).") +
         results_block("r2", "R2. Schede piene, il risultato chiave in evidenza", "Schede <b>piene senza bordo</b> (velo del testo), la prima "
                       "nel velo d'accento: il numero che conta si trova a colpo d'occhio. Stile tonale, coerente con C2.") +
         results_block("r3", "R3. Righe con il numero d'accento", "Niente riquadri: <b>righe separate da una linea</b>, il numero nel colore "
                       "d'accento. La più leggera; meno «contorno», che è ciò che Daniel lamenta."))
    body = f'<div class="ctl">{c}</div><h2>I riquadri dei risultati (Producibilità, Consumi, Bilancio)</h2><div class="res">{r}</div>'
    return page("C. Pulsanti, campi e gruppi", intro, body, C_CSS)


# ============================================================ indice

def index(pages: list[tuple[str, str, str]]) -> str:
    items = "".join(f'<li><a href="{n}" style="color:var(--accent);font-weight:600">{t}</a> · {s}</li>' for n, t, s in pages)
    body = f'<ul style="line-height:1.8;font-size:16px">{items}</ul>'
    return page("Studio 17: i bozzetti", "<p>Una pagina per tema, con le direzioni una accanto all'altra; in cima a ogni pagina il tema "
                "chiaro o scuro e la scala. Lo studio è <code>docs/studio/17-interfaccia.md</code>.</p>", body)


def main() -> None:
    from pagine_defg import page_d, page_e, page_f, page_g
    save("A-parti.html", "A. Distinguere le parti dell'interfaccia", page_a(), "livelli di superficie, intestazioni, separatori, albero del progetto")
    save("B-strumenti.html", "B. Dove stanno gli strumenti", page_b(), "sotto le schede, barra laterale, dentro la vista, fasi")
    save("C-controlli.html", "C. Pulsanti, campi e gruppi", page_c(), "Fusion ritoccato, alla GNOME, contorni forti; i riquadri dei risultati")
    save("D-grafici.html", "D. Grafici interattivi", page_d(), "valori al passaggio, zoom, serie, su un anno di valori orari")
    save("E-aiuti.html", "E. Aiuti accanto alle cose", page_e(), "il «?», i suggerimenti estesi, le frasi sotto i campi, il pannello d'aiuto")
    save("F-verifiche.html", "F. Il pannello Verifiche", page_f(), "per oggetto, per livello, per area; frasi brevi, Correggi, legame con le viste")
    save("G-meridio.html", "G. Meridio e la sua chat", page_g(), "personaggio animato, apertura e chiusura, risposta in corso, ridimensionamento, domande pronte")
    write("index.html", index(INDEX))
    print("scritte", len(INDEX) + 1, "pagine in", Path(__file__).resolve().parent)


if __name__ == "__main__":
    main()
