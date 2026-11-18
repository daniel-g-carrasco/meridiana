"""Study 27: writes bozzetti.html (self-contained): whole windows of the proposal at their real size in CSS pixels, with
the bars of study 26 (real words and icons). From the study's folder: python genera.py (needs ../26-barra/barre.json)."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "26-barra"))
import barra_html as H  # noqa: E402

CSS = H.CSS + """
html{background:#e6e3dc}
body{margin:0;font:13px/1.35 Inter,"Segoe UI",system-ui,sans-serif;color:#1e1c19;padding:20px 24px}
h1{font-size:22px;font-weight:600;margin:0 0 4px}
h2{font-size:16px;font-weight:600;margin:0 0 4px}
p{margin:0 0 6px;color:#514c44;max-width:1180px}
section{margin:0 0 28px;padding:14px 0 0;border-top:1px solid #cfcbc2}
table{border-collapse:collapse;background:#fff;font-size:12px;margin:6px 0}
th,td{border:1px solid #d9d5cc;padding:4px 8px;text-align:left;vertical-align:top}
th{background:#f2f1ed;font-weight:600}
.shot{display:inline-block;vertical-align:top;margin:0 16px 16px 0}
.shot .cap{font-size:12px;color:#514c44;margin:0 0 4px;max-width:900px}
.scale{transform-origin:0 0}
.win{position:relative;display:flex;flex-direction:column;overflow:hidden;background:var(--window);color:var(--text);border:1px solid #aaa59a;font-size:13px;line-height:1.3}
.tabs{display:flex;align-items:flex-end;height:36px;padding:0 12px;flex:none;position:relative;z-index:2}
.file{display:flex;align-items:center;gap:4px;height:28px;margin:0 12px 4px 0;padding:0 8px;font-weight:600;border-radius:6px}
.file .ic{width:15px;height:15px}
.tab{display:flex;align-items:center;gap:8px;height:32px;padding:0 12px;color:var(--text2);white-space:nowrap;border-radius:8px 8px 0 0}
.tab .disc{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:10px;background:var(--line-soft);color:var(--muted);font-size:11px;font-weight:600}
.tab.on{background:var(--panel);color:var(--text);font-weight:600;border:1px solid var(--line);border-bottom:0;height:33px;margin-bottom:-1px}
.tab.on .disc{background:var(--accent);color:var(--accent-fg)}
.tab.c{padding:0 4px}
.tab.c.on{padding:0 10px 0 6px}
.spacer{flex:1 1 auto}
.vari{display:flex;align-items:center;height:28px;margin-bottom:4px;background:var(--field);border-radius:6px;padding:2px;font-size:13px}
.vari i{font-style:normal;background:var(--panel);border:1px solid var(--line);border-radius:4px;height:24px;display:flex;align-items:center;padding:0 8px}
.vari u{text-decoration:none;padding:0 8px;color:var(--text2)}
.head{padding:0 12px;flex:none}
.head .card{position:relative;z-index:1}
.bodyw{flex:1 1 auto;min-height:0;display:flex;gap:8px;padding:8px 12px}
.col{display:flex;flex-direction:column;gap:8px;min-height:0;min-width:0}
.fill{flex:1 1 0;min-width:0;min-height:0}
.pcard{background:var(--panel);border:1px solid var(--line);border-radius:8px;display:flex;flex-direction:column;min-height:0;overflow:hidden}
.pt{display:flex;align-items:center;justify-content:space-between;font-size:14px;font-weight:600;padding:8px 12px 4px;flex:none}
.pt .x{color:var(--muted);font-weight:400}
.tree{padding:0 12px;font-size:13px}
.tree div{display:flex;align-items:center;gap:8px;height:26px;white-space:nowrap}
.tree .sec{font-size:11px;font-weight:600;letter-spacing:.04em;color:var(--muted);margin-top:8px}
.tree .ic{width:15px;height:15px}
.gr{border:1px solid var(--line);border-radius:6px;margin:0 6px 6px;overflow:hidden;flex:none}
.gr .gh{background:var(--line-soft);font-weight:600;padding:4px 8px;display:flex;gap:6px;align-items:center;white-space:nowrap}
.gr .gb{padding:6px 8px;display:grid;grid-template-columns:96px 1fr;gap:4px 8px;align-items:center}
.gr .gb.one{display:block;color:var(--text2);font-size:12px}
.fld{height:24px;background:var(--field);border-radius:6px;display:flex;align-items:center;padding:0 8px;white-space:nowrap;overflow:hidden}
.ch{display:inline-block;width:6px;height:6px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);transform:rotate(45deg);margin:0 3px 2px 1px}
.ch.cl{transform:rotate(-45deg);margin:0 3px 0 0}
.view{position:relative;background:#2b2f36;border-radius:6px;overflow:hidden;min-height:0;min-width:0}
.vb{position:absolute;left:8px;top:8px;display:flex;gap:2px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:2px;color:var(--text)}
.vb span{display:block}
.vb .ic{width:18px!important;height:18px!important;margin:3px}
.vb .on{background:var(--press);border-radius:4px}
.north{position:absolute;right:10px;top:10px;width:44px;height:44px;border-radius:22px;background:#1c1f24;color:#eee;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600}
.scale10{position:absolute;left:10px;bottom:10px;color:#eee;font-size:11px;background:#1c1f24;border-radius:6px;padding:3px 8px}
.ctr{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.cube{width:64px;height:64px;position:absolute;right:16px;top:16px;opacity:.9}
.sun{display:flex;align-items:center;gap:8px;height:28px;font-size:12px;flex:none;color:var(--text2)}
.sun i{flex:1;height:3px;background:var(--line);border-radius:2px;position:relative;font-style:normal}
.sun i::after{content:"";position:absolute;left:30%;top:-5px;width:13px;height:13px;border-radius:7px;background:var(--panel);border:1px solid var(--muted)}
.chk{padding:0 12px;flex:none}
.pista{display:inline-flex;background:var(--field);border-radius:6px;padding:2px;height:28px;font-size:13px;color:var(--text2);white-space:nowrap}
.pista span{display:flex;align-items:center;padding:0 10px;border-radius:4px;border:1px solid transparent}
.pista span.sel{background:var(--panel);border-color:var(--line);color:var(--text)}
.ln{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:13px;white-space:nowrap;overflow:hidden}
.tri2{display:inline-block;width:0;height:0;border:6px solid transparent;border-bottom:10px solid #e8a30c;border-top:0;flex:none}
.status{display:flex;align-items:center;gap:12px;height:36px;padding:0 12px;flex:none;font-size:12px;color:var(--text2);white-space:nowrap}
.status .sp{flex:1}
.status b{font-weight:600;color:var(--text)}
.status .btn{display:flex;align-items:center;gap:6px;height:26px;padding:0 8px;border-radius:6px;background:var(--hover);color:var(--text)}
.rail{width:44px;flex:none;background:var(--panel);border:1px solid var(--line);border-radius:8px;display:flex;flex-direction:column;align-items:center;padding:6px 0;gap:4px}
.rail .r{position:relative;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:6px;color:var(--text)}
.rail .r .ic{width:20px;height:20px}
.rail .r.on{background:var(--press)}
.rail .n{position:absolute;right:0;bottom:0;font-size:9px;font-weight:600;color:var(--muted);background:var(--panel);border-radius:3px;padding:0 2px;line-height:11px}
.overlay{position:absolute;z-index:5;background:var(--panel);border:1px solid var(--line);border-radius:8px;display:flex;flex-direction:column;overflow:hidden}
.pin{font-size:11px;color:var(--muted);font-weight:400;margin-left:auto;margin-right:10px}
.sheet{flex:none;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden;min-height:0}
.grab{width:40px;height:4px;border-radius:2px;background:var(--line);margin:5px auto 3px;flex:none}
.sheet .st{display:flex;align-items:center;gap:8px;padding:0 8px 6px;flex:none}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0 2px;padding-top:2px;min-height:0;overflow:hidden}
.thres td:first-child,.thres th:first-child{white-space:nowrap}
.ok{font-weight:600}
"""

PLAN = ('<svg viewBox="0 0 400 210" style="width:{w};max-height:90%"><rect x="1" y="1" width="398" height="208" fill="#4b5b6b" stroke="#f7f1de" stroke-width="2"/>'
        '<rect x="8" y="8" width="384" height="194" fill="none" stroke="#3aa0e8" stroke-width="2" stroke-dasharray="6 4"/>'
        + "".join(f'<rect x="16" y="{y}" width="368" height="22" fill="#1d2f5e" stroke="#d13b3b" stroke-width="1.5"/>' for y in (40, 80, 120, 160))
        + "</svg>")
BOX = ('<svg class="cube" viewBox="0 0 64 64"><path d="M32 6 58 20V46L32 60 6 46V20Z" fill="#8e8e8e" stroke="#333"/><path d="M6 20 32 34 58 20M32 34V60" fill="none" stroke="#333"/></svg>')
BUILD3D = ('<svg viewBox="0 0 400 220" style="width:70%;max-height:80%"><path d="M40 110 240 40 370 110 170 190Z" fill="#6c7886"/><path d="M40 110V150L170 220V190Z" fill="#4a535e"/><path d="M170 190V220L370 150V110Z" fill="#59636f"/>'
           + "".join(f'<path d="M{70 + i * 34} {108 - i * 12} {190 + i * 34} {174 - i * 12}" stroke="#1d2f5e" stroke-width="12"/>' for i in range(5))
           + "</svg>")


def vb(three: bool = False) -> str:
    icons = ("plan", "3d", "both", "fit", "zoom_in", "zoom_out")
    on = {"both"}
    if three:
        icons = ("fit", "zoom_in", "zoom_out")
        on = set()
    return '<div class="vb">' + "".join(f'<span class="{"on" if i in on else ""}">{H.ic(i)}</span>' for i in icons) + "</div>"


def plan_view(style: str = "", w: str = "70%", bar: bool = True) -> str:
    return (f'<div class="view fill" style="{style}">{vb() if bar else ""}<div class="ctr">{PLAN.format(w=w)}</div>'
            '<div class="north">N</div><div class="scale10">10 m</div></div>')


def d3_view(style: str = "") -> str:
    return f'<div class="view fill" style="{style}">{vb(True)}<div class="ctr">{BUILD3D}</div>{BOX}</div>'


def tree_body() -> str:
    return ('<div class="tree"><div>' + H.ic("site") + 'Prova<span style="margin-left:auto;color:var(--muted);font-size:12px">16</span></div>'
            '<div class="sec">EDIFICI 1</div><div>' + H.ic("building") + 'Capannone</div><div class="sec">SOTTOCAMPI 1</div><div>'
            + H.ic("subfield") + 'Sud <span class="mut">· 128</span></div><div class="sec">ESCLUSIONI 0</div></div>')


def tree(width: int) -> str:
    return f'<div class="pcard" style="width:{width}px;flex:none"><div class="pt">Progetto<span class="x">×</span></div>{tree_body()}</div>'


def sito() -> str:
    rows = (("Progetto", "Prova"), ("Latitudine", "45,522600"), ("Longitudine", "9,030000"), ("Indirizzo", "Rho (MI)"))
    body = "".join(f'<span>{a}</span><span class="fld">{b}</span>' for a, b in rows)
    return f'<div class="gr"><div class="gh"><i class="ch"></i>Sito</div><div class="gb">{body}</div></div>'


def rete() -> str:
    rows = (("Distributore", "&nbsp;"), ("POD", "&nbsp;"), ("Tensione", "non indicata"), ("Fasi", "non indicata"), ("Connessione", "non indicata"))
    body = "".join(f'<span>{a}</span><span class="fld">{b}</span>' for a, b in rows)
    return f'<div class="gr"><div class="gh"><i class="ch"></i>Connessione alla rete (facoltativa)</div><div class="gb">{body}</div></div>'


def obblighi() -> str:
    return '<div class="gr"><div class="gh"><i class="ch cl"></i>Connessione e obblighi</div></div>'


def props_body() -> str:
    return sito() + rete() + obblighi()


def plant_body() -> str:
    return ('<div class="gr"><div class="gh"><i class="ch"></i>Pannelli</div><div class="gb one">Sud: 128 moduli, 57,60 kWp. '
            'Seleziona un sottocampo in pianta per vederne qui la posa, oppure disegnane uno con «Sottocampo».</div></div>'
            '<div class="gr"><div class="gh"><i class="ch cl"></i>Inverter</div></div><div class="gr"><div class="gh"><i class="ch cl"></i>Accumulo</div></div>')


def help_card(h: int = 110) -> str:
    return (f'<div class="pcard" style="height:{h}px;flex:none"><div class="pt">Aiuto<span class="x">×</span></div>'
            '<div style="padding:0 12px;font-size:12px;color:var(--text2)">Il sito dà latitudine e longitudine dell\'origine del disegno: il sole, il meteo da PVGIS e le regole della regione.</div></div>')


def panel(title: str, body: str, width: int) -> str:
    return (f'<div class="col" style="width:{width}px;flex:none"><div class="pcard fill"><div class="pt">{title}<span class="x">×</span></div>'
            f'{body}</div>{help_card()}</div>')


def checks_body() -> str:
    return ('<div class="chk"><span class="pista"><span class="sel">Per livello</span><span>Per oggetto</span><span>Per area</span><span>Pronto per la consegna</span></span>'
            '<div class="ln"><i class="tri2"></i><b style="font-weight:600">Da controllare · 1</b></div>'
            '<div class="ln mut" style="color:var(--text)">128 moduli fuori stringa e senza inverter</div></div>')


def checks_card(h: int = 150) -> str:
    return f'<div class="pcard" style="height:{h}px;flex:none"><div class="pt">Verifiche (1)<span class="x">×</span></div>{checks_body()}</div>'


def status(note: str = "128 moduli posati in 9 ms", checks_word: bool = False) -> str:
    word = "<b>Verifiche: 1 da controllare</b>" if checks_word else "1"
    tag = "btn" if checks_word else ""
    return (f'<div class="status"><span>{note}</span><span class="sp"></span><span class="{tag}"><i class="tri2" style="transform:scale(.8)"></i>{word}</span>'
            '<span>Meridio</span></div>')


def row(phase: str, compact: bool) -> str:
    tabs = []
    for pid in ("model", "plant", "production", "consumption", "economics", "report"):
        p = H.PHASES[pid]
        on = pid == phase
        name = p["title"] if not compact or on else ""
        cls = "tab" + (" on" if on else "") + (" c" if compact else "")
        tabs.append(f'<div class="{cls}" title="{p["title"]}"><span class="disc">{p["n"]}</span>{name}</div>')
    file = f'<div class="file">{H.ic("folder-open")}File</div>'
    return (f'<div class="tabs">{file}{"".join(tabs)}<span class="spacer"></span><div class="vari"><i>Base</i><u>+</u></div></div>')


def header(phase: str, compact: bool, mode: str, titles: bool, strip: bool = True, faces=None) -> str:
    return (f'{row(phase, compact)}<div class="head"><div class="card">'
            f'{H.bar(phase, "g2", mode, measure=False, titles=titles, strip=strip, faces=faces)}</div></div>')


def window(w: int, h: int, inner: str, zoom: float, cap: str, name: str, stat: str | None = None) -> str:
    frame = f'<div class="win light" style="width:{w}px;height:{h}px">{inner}{stat or status()}</div>'
    return (f'<div class="shot" id="{name}"><div class="cap">{cap}</div>'
            f'<div style="width:{w * zoom + 2:.0f}px;height:{h * zoom + 2:.0f}px"><div class="scale" style="transform:scale({zoom})">{frame}</div></div></div>')


def sheet(tabs: tuple, body: str, h: int, two: bool = False) -> str:
    pista = "".join(f'<span class="{"sel" if i == 0 else ""}">{t}</span>' for i, t in enumerate(tabs))
    inner = f'<div class="two">{body}</div>' if two else f'<div style="padding-top:2px">{body}</div>'
    return (f'<div class="sheet" style="height:{h}px"><div class="grab"></div><div class="st"><span class="pista">{pista}</span>'
            f'<span class="spacer"></span><span class="mut" style="font-size:12px">Trascina la maniglia: chiuso, metà, tutto</span></div>{inner}</div>')


def shots(zoom: float) -> list[str]:
    out = []
    # 1366 x 768: the words beside, no titles, the checks in the status bar
    body = (f'<div class="bodyw">{tree(240)}<div class="pcard fill" style="padding:6px"><div class="col fill"><div class="fill" style="display:flex;gap:6px;min-height:0">{plan_view()}'
            f'{d3_view()}</div><div class="sun"><span>21 dic</span><i></i><span>12:20</span></div></div></div>{panel("Proprietà", props_body(), 300)}</div>')
    out.append(window(1366, 768, header("model", False, "beside", False) + body, zoom,
                      "<b>1366 x 768, Modellazione.</b> Tre colonne come oggi, parole accanto alle icone (la larghezza c'è), Verifiche chiuse nella barra di stato: la pianta passa da 363 a circa 590 px di altezza.",
                      "m1366", status(checks_word=True)))
    body = (f'<div class="bodyw">{tree(240)}<div class="pcard fill" style="padding:6px">{plan_view(w="62%")}</div>{panel("Impianto", plant_body(), 300)}</div>')
    out.append(window(1366, 768, header("plant", False, "beside", False) + body, zoom,
                      "<b>1366 x 768, Impianto.</b> Le parole ci stanno senza la striscia di stato, che passa nella barra di stato.",
                      "p1366", status(note="Non scelto: dimensionato da solo al rapporto DC/AC 1,10 · 0 stringhe su 0 ingressi · 128 moduli fuori stringa", checks_word=True)))
    # 1080 x 1920: portrait, the panels at the foot, plan over 3D
    tabs = ("Proprietà", "Progetto", "Verifiche (1)", "Aiuto")
    views = f'<div class="pcard" style="flex:1 1 0;padding:6px;min-height:0"><div class="col fill" style="gap:6px">{plan_view(w="55%")}{d3_view()}<div class="sun"><span>21 dic</span><i></i><span>12:20</span></div></div></div>'
    body = f'<div class="bodyw" style="flex-direction:column">{views}{sheet(tabs, sito() + obblighi() + rete(), 560, two=True)}</div>'
    out.append(window(1080, 1920, header("model", False, "tall", True) + body, zoom,
                      "<b>1080 x 1920, Modellazione.</b> Oggi la pianta è larga 186 px e alta 1493. Qui una sopra l'altra, larghe 1044 px; i pannelli in basso a linguette, nell'ordine di sempre, con la maniglia.",
                      "m1080"))
    tabs2 = ("Impianto", "Progetto", "Verifiche (1)", "Aiuto")
    views = f'<div class="pcard" style="flex:1 1 0;padding:6px;min-height:0">{plan_view(w="72%")}</div>'
    body = f'<div class="bodyw" style="flex-direction:column">{views}{sheet(tabs2, plant_body(), 560)}</div>'
    out.append(window(1080, 1920, header("plant", False, "tall", True, strip=False) + body, zoom,
                      "<b>1080 x 1920, Impianto.</b> Pianta larga tutta la finestra; la striscia di stato della fase passa in cima al foglio o nella barra di stato.",
                      "p1080", status(note="0 stringhe su 0 ingressi · 128 moduli fuori stringa")))
    # 800 x 1280: compact row, icons with titles, sheet
    views = f'<div class="pcard" style="flex:1 1 0;padding:6px;min-height:0"><div class="col fill" style="gap:6px">{plan_view(w="48%")}{d3_view()}<div class="sun"><span>21 dic</span><i></i><span>12:20</span></div></div></div>'
    body = f'<div class="bodyw" style="flex-direction:column">{views}{sheet(tabs, sito() + rete(), 400)}</div>'
    out.append(window(800, 1280, header("model", True, "low", True) + body, zoom,
                      "<b>800 x 1280, Modellazione.</b> Numeri nella riga delle fasi, il titolo solo della corrente (oggi: «Modella…», «Im…»). Barra a sole icone con i titolini: Precisione torna visibile. Stesso foglio in basso.",
                      "m800"))
    views = f'<div class="pcard" style="flex:1 1 0;padding:6px;min-height:0">{plan_view(w="78%")}</div>'
    body = f'<div class="bodyw" style="flex-direction:column">{views}{sheet(tabs2, plant_body(), 400)}</div>'
    out.append(window(800, 1280, header("plant", True, "low", True) + body, zoom,
                      "<b>800 x 1280, Impianto.</b> Le icone di tutti i gruppi ci stanno (522 px su 756): Stringhe non sparisce più.",
                      "p800", status(note="128 moduli fuori stringa")))
    # 960 x 1040: half a screen, the rail
    rail = ('<div class="rail">' + "".join(f'<div class="r{" on" if on else ""}">{H.ic(i)}<span class="n">{n}</span></div>'
            for i, n, on in (("site", "", False), ("building", "1", False), ("subfield", "1", False), ("exclusion", "0", False))) + "</div>")
    views = f'<div class="pcard fill" style="padding:6px"><div class="col fill" style="gap:6px">{plan_view(w="72%")}{d3_view()}<div class="sun"><span>21 dic</span><i></i><span>12:20</span></div></div></div>'
    body = f'<div class="bodyw">{rail}{views}{panel("Proprietà", props_body(), 300)}</div>'
    out.append(window(960, 1040, header("model", True, "tall", True) + body, zoom,
                      "<b>960 x 1040 (metà di uno schermo), a riposo.</b> A sinistra la striscia dei simboli: una voce per sezione dell'albero, con il conteggio. La vista guadagna 196 px.",
                      "m960", status(checks_word=True)))
    rail_on = rail.replace('class="r"', 'class="r"', 1)
    over = (f'<div class="overlay" style="left:68px;top:106px;width:260px;height:400px"><div class="pt">Progetto<span class="pin">Tieni aperta</span><span class="x">×</span></div>{tree_body()}</div>')
    views = f'<div class="pcard fill" style="padding:6px">{plan_view(w="72%")}</div>'
    body = f'<div class="bodyw">{rail_on}{views}{panel("Impianto", plant_body(), 300)}</div>{over}'
    out.append(window(960, 1040, header("plant", True, "low", True, strip=False) + body, zoom,
                      "<b>960 x 1040, Impianto, scheda aperta.</b> Le parole non ci stanno (988 px su 916): sole icone con i titolini. Un clic su un simbolo apre la scheda sopra la vista, senza spostare nulla; Esc o un clic fuori la chiude; «Tieni aperta» la rimette colonna (e la scelta si ricorda).",
                      "p960", status(checks_word=True)))
    return out


THRESHOLDS = """
<table class="thres">
<tr><th>Cosa decide</th><th>Quando (pixel logici della finestra, con 40 px di isteresi)</th><th>Che succede</th><th>Oggi</th></tr>
<tr><td>Riga delle fasi</td><td>L &lt; 1000</td><td>Dischi con i numeri, il titolo solo della corrente, nome intero nel suggerimento</td><td>Nomi tagliati a caso («Im…»), variante «B…»</td></tr>
<tr><td>Parole sotto le icone</td><td>A ≥ 900 e L ≥ larghezza che la fase chiede (802, Impianto 988, senza striscia)</td><td>Barra alta 69 px</td><td>Solo l'altezza decide: a 800 x 1280 le parole restano e i gruppi spariscono</td></tr>
<tr><td>Parole accanto, senza titolini</td><td>A &lt; 900 e L ≥ 1049 (Impianto 1249)</td><td>Barra alta 31 px: restano le parole, meno altezza</td><td>Non esiste: a 1366 x 768 sole icone con 880 px liberi a destra</td></tr>
<tr><td>Sole icone con titolini</td><td>L ≥ 429 (Impianto 522)</td><td>Barra alta 47 px</td><td>Solo sotto i 900 di altezza</td></tr>
<tr><td>Gruppi in tendina</td><td>L &lt; 429 (Impianto 522)</td><td>L'ultimo gruppo diventa un pulsante col suo titolo e chevron, poi il penultimo; ordine fisso, da destra</td><td>Il troppo-pieno di Qt, un puntino quasi invisibile</td></tr>
<tr><td>Verifiche</td><td>A &lt; 900</td><td>Chiuse nella barra di stato con il conteggio; un clic le apre sopra</td><td>247 px fissi anche su 768</td></tr>
<tr><td>Pianta e 3D</td><td>Area centrale con L/A &lt; 1</td><td>Una sopra l'altra</td><td>Sempre affiancate: 186 px di larghezza a 1080 x 1920</td></tr>
<tr><td>Colonna Progetto</td><td>L &lt; 1100</td><td>Striscia di simboli da 44 px, scheda sopra al clic</td><td>Sotto 1000 diventa linguetta di Proprietà e la pianta resta sola</td></tr>
<tr><td>Colonna Proprietà</td><td>L &lt; 800 (non in verticale)</td><td>Anche lei striscia, scheda sopra da 300 px</td><td>Sempre colonna; minimo 284</td></tr>
<tr><td>Foglio in basso</td><td>Area centrale alta almeno 1,25 volte la sua larghezza e L &lt; 1200</td><td>I pannelli a linguette in basso, tre altezze (chiuso, metà, tutto)</td><td>Non esiste</td></tr>
<tr><td>Griglie di riquadri</td><td>Larghezza della scheda (già così)</td><td>Colonne da 5 a 2, uguali</td><td>Già fatto (<code>Tiles</code>, R309)</td></tr>
<tr><td>Testo</td><td>Mai</td><td>Le dimensioni non cambiano con la finestra; solo la preferenza dell'utente (R133)</td><td>Già così</td></tr>
</table>
"""

CASES = """
<table>
<tr><th>Caso</th><th>Riga fasi</th><th>Barra</th><th>Colonne</th><th>Pianta e 3D</th><th>Verifiche</th></tr>
<tr><td>1920 x 1080</td><td>intera</td><td>parole sotto</td><td>320, 380</td><td>affiancate</td><td>in basso</td></tr>
<tr><td>1366 x 768</td><td>intera</td><td>parole accanto</td><td>240, 300</td><td>affiancate</td><td>chiuse</td></tr>
<tr><td>1280 x 800</td><td>intera</td><td>parole accanto (Impianto: icone)</td><td>240, 300</td><td>affiancate</td><td>chiuse</td></tr>
<tr><td>1080 x 1920</td><td>intera</td><td>parole sotto</td><td>foglio in basso</td><td>una sopra l'altra</td><td>nel foglio</td></tr>
<tr><td>960 x 1040</td><td>numeri</td><td>parole sotto (Impianto: icone)</td><td>simboli, 300</td><td>una sopra l'altra</td><td>in basso, o chiuse a scelta</td></tr>
<tr><td>800 x 1280</td><td>numeri</td><td>icone e titolini</td><td>foglio in basso</td><td>una sopra l'altra</td><td>nel foglio</td></tr>
<tr><td>683 x 728</td><td>numeri</td><td>icone e titolini</td><td>simboli, simboli</td><td>una alla volta</td><td>chiuse</td></tr>
</table>
"""

TEMPLATE = """<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Schermi stretti</title>
<style>{tokens}{css}</style></head>
<body>{sprite}
<h1>Schermi stretti: le schermate della proposta</h1>
<p>Studio 27 (R334), 02/11/2026. Finestre intere alle misure vere, ridotte a scala nella pagina (con <code>?z=1</code> al 100 %, con <code>?only=m800</code> una sola). Parole, icone e colori veri; barra secondo lo studio 26 (G2).
Il contenuto delle schede è di esempio, la pianta e il 3D sono disegni schematici. Le foto di come è oggi sono in <code>foto/</code>, i ragionamenti e le misure nel <code>README.md</code>.</p>
<section id="soglie"><h2>Le soglie</h2>{thresholds}<h2 style="margin-top:12px">Cosa ne viene, caso per caso</h2>{cases}</section>
<section id="windows">{shots}</section>
<script>
const q=new URLSearchParams(location.search);const only=q.get('only');const z=q.get('z');
if(only){{document.querySelectorAll('section').forEach(s=>{{if(s.id!=='windows')s.style.display='none'}});document.querySelectorAll('.shot').forEach(s=>{{if(s.id!==only)s.style.display='none'}});}}
if(z){{document.querySelectorAll('.shot').forEach(s=>{{const sc=s.querySelector('.scale');const w=sc.firstChild;sc.style.transform='scale('+z+')';sc.parentNode.style.width=(w.offsetWidth*z+2)+'px';sc.parentNode.style.height=(w.offsetHeight*z+2)+'px';}});}}
</script></body></html>
"""

if __name__ == "__main__":
    html = TEMPLATE.format(tokens=H.tokens_css(), css=CSS, sprite=H.sprite(), thresholds=THRESHOLDS, cases=CASES,
                           shots="".join(shots(0.5)))
    (HERE / "bozzetti.html").write_text(html, encoding="utf-8", newline="\n")
    print(len(html))
