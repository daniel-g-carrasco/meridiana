"""Study 29: writes bozzetti.html next to it: the photographs of foto/ side by side (bars, panel, windows), the
width chart of the measures (misure.json) and the proofs of the width axis. From the study's folder: python genera.py
The photographs are made by the study's probe (see README, section 6); nothing of the program is changed."""

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / "misure.json").read_text(encoding="utf-8"))["fonts"]

# variant -> (label, what it is)
VARIANTS = {
    "inter": ("Inter 4.1 (oggi)", "riferimento: i tre file statici del programma"),
    "inter-tnum": ("Inter + cifre tabellari", "stesso Inter, feature tnum su tutto il testo"),
    "inter-ls": ("Inter, spaziatura -0,2 px", "stesso Inter, 3 % più stretto"),
    "intertight": ("Inter Tight", "stesso disegno di Inter, spaziatura e sagome più strette (-9 %)"),
    "adwaita": ("Adwaita Sans", "il carattere di Lucciola: derivato da Inter"),
    "intercond": ("Inter + Plex Condensed", "Inter ovunque; IBM Plex Sans Condensed solo nei bottoni delle barre, nelle linguette, nei titoli dei pannelli e nelle etichette del pannello Proprietà"),
    "intertight-narrow": ("Inter + Inter Tight", "Inter ovunque; Inter Tight solo negli stessi posti del condensato"),
    "plex": ("IBM Plex Sans", "IBM Plex Sans, asse wdth 100"),
    "plexcond": ("Plex + Plex Condensed", "Plex Sans ovunque; Plex Condensed negli stessi posti"),
    "fira": ("Fira Sans", "Fira Sans"),
    "firacond": ("Fira + Fira Condensed", "Fira Sans ovunque; Fira Sans Condensed negli stessi posti"),
    "notowdth": ("Noto Sans + asse wdth 75", "Noto Sans variabile; asse wdth 75 (e wght come asse) negli stessi posti"),
    "jball": ("JetBrains Mono ovunque", "tutta l'interfaccia a spaziatura fissa"),
    "jbnum": ("Inter + JetBrains Mono per i valori", "campi, caselle numeriche, tabelle e liste in JetBrains Mono; il resto in Inter"),
}
MAIN = ["inter", "intertight", "intercond", "intertight-narrow", "plexcond", "firacond", "notowdth", "jball", "jbnum"]
EXTRA = ["inter-tnum", "inter-ls", "adwaita", "plex", "fira"]

CSS = """
:root{--bg:#f4f2ee;--fg:#1e1c19;--mut:#5a554c;--card:#fff;--line:#d6d1c6;--acc:#4b3fa8}
@media (prefers-color-scheme: dark){:root{--bg:#1d1c1a;--fg:#ece8df;--mut:#a39e92;--card:#26241f;--line:#3d3a33;--acc:#a79cf0}}
html{background:var(--bg)}
body{margin:0;padding:20px 24px 60px;font:14px/1.45 Inter,"Segoe UI",system-ui,sans-serif;color:var(--fg)}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:34px 0 4px;border-top:1px solid var(--line);padding-top:14px}
h3{font-size:14px;margin:16px 0 4px}p{margin:0 0 8px;color:var(--mut);max-width:980px}
.row{margin:0 0 14px}.cap{font-size:12px;color:var(--mut);margin:0 0 2px}.cap b{color:var(--fg)}
.row img{display:block;border:1px solid var(--line);max-width:100%;height:auto}
.panels{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start}
.panels figure{margin:0}.panels img{display:block;border:1px solid var(--line)}
figcaption{font-size:12px;color:var(--mut);margin-top:3px;max-width:340px}
.chart{max-width:900px}.chart div{display:flex;align-items:center;gap:8px;height:20px;font-size:12px}
.chart span.n{width:250px;flex:none;text-align:right;color:var(--mut)}.chart i{display:block;height:12px;background:var(--acc);border-radius:2px}
.chart i.ref{background:#8a867c}.chart em{font-style:normal;color:var(--mut);font-size:11px}
details{margin:6px 0}summary{cursor:pointer;color:var(--acc)}
.note{border-left:3px solid var(--acc);padding:2px 10px;margin:8px 0;color:var(--fg)}
"""


def img(name, scale, w=None):
    """An image of foto/, shown at its logical size (the 200 % photographs at half their pixels)."""
    p = HERE / "foto" / name
    if not p.exists():
        return f'<p class="cap">(manca {html.escape(name)})</p>'
    from struct import unpack
    data = p.read_bytes()
    width = unpack(">I", data[16:20])[0]
    shown = w or width / scale
    return f'<img src="foto/{name}" width="{shown:.0f}" alt="{html.escape(name)}">'


def bars_section(scale, theme):
    out = [f'<h3>Barra degli strumenti, fase Impianto, {100 * scale} %, tema {"chiaro" if theme == "light" else "scuro"}</h3>']
    for v in MAIN:
        lab, what = VARIANTS[v]
        out.append(f'<div class="row"><p class="cap"><b>{html.escape(lab)}</b>: {html.escape(what)}</p>'
                   f'{img(f"{v}-{scale}x-{theme}-bar.png", scale)}</div>')
    return "\n".join(out)


def panel_section(scale, theme, variants):
    out = [f'<h3>Pannello Impianto stretto, {100 * scale} %, tema {"chiaro" if theme == "light" else "scuro"}</h3>',
           '<div class="panels">']
    for v in variants:
        lab, what = VARIANTS[v]
        out.append(f'<figure>{img(f"{v}-{scale}x-{theme}-panel.png", scale)}<figcaption><b>{html.escape(lab)}</b><br>{html.escape(what)}</figcaption></figure>')
    out.append("</div>")
    return "\n".join(out)


def chart():
    base = M["inter"]["corpus"]
    rows = []
    order = ["inter", "inter-ls1", "inter-ls2", "inter-tnum", "intertight", "adwaita", "noto", "noto75", "opensans75", "roboto",
             "robotocond", "robotoflex", "plex", "plex85", "plexcond", "source", "fira", "firacond", "barlow", "barlowsc",
             "archivo", "archivo75", "nerdubuntu", "nerdubuntucond", "jbmono"]
    for k in order:
        f = M[k]
        pct = 100 * f["corpus"] / base
        rows.append(f'<div><span class="n">{html.escape(f["label"])}</span><i class="{"ref" if k == "inter" else ""}" style="width:{pct * 4:.0f}px"></i>'
                    f'<em>{pct:.0f} %</em></div>')
    return '<div class="chart">' + "\n".join(rows) + "</div>"


def main():
    parts = [f"<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>Studio 29: font</title><style>{CSS}</style></head><body>",
             "<h1>Studio 29: il carattere di Meridiana</h1>",
             "<p>Finestra vera di Meridiana, offscreen su Windows (Qt 6.12, DirectWrite), con il carattere cambiato senza toccare il sorgente. "
             "Nelle varianti «condensato» il carattere stretto è usato solo nei bottoni delle barre, nelle linguette, nei titoli dei pannelli e nelle etichette del pannello Proprietà. "
             "La resa su uno schermo vero (ClearType, spaziatura dei pixel) non si vede offscreen: <b>non verificata</b>. "
             "Il 100 % è mostrato a grandezza naturale, il 200 % ridotto a metà (la foto ha il doppio dei pixel: si ingrandisce con il pulsante destro, apri immagine).</p>",
             "<h2>1. Larghezza dei testi veri, in percentuale di Inter</h2>",
             "<p>Somma della larghezza di 3181 stringhe italiane del programma (po/it.po) a 13 px, hinting predefinito di Windows. 100 % = Inter.</p>",
             chart(),
             "<h2>2. Barre</h2>"]
    for scale, theme in ((1, "light"), (2, "dark")):
        parts.append(bars_section(scale, theme))
    parts.append("<h2>3. Pannello Impianto stretto</h2>")
    parts.append("<p>Il pannello delle proprietà con il sottocampo selezionato, tirato a 276 px (si ferma al minimo del contenuto).</p>")
    for scale, theme in ((1, "light"), (2, "light"), (2, "dark")):
        parts.append(panel_section(scale, theme, MAIN))
    parts.append("<h2>4. Le altre prove di Inter, di Plex e di Fira senza condensato</h2>")
    parts.append(panel_section(1, "light", EXTRA))
    parts.append("<h2>5. Finestre intere (100 %)</h2>")
    for theme in ("light", "dark"):
        for v in MAIN:
            lab, _w = VARIANTS[v]
            parts.append(f'<details><summary>{html.escape(lab)}, {"chiaro" if theme == "light" else "scuro"}</summary>'
                         f'{img(f"{v}-1x-{theme}-window.png", 1)}</details>')
    parts.append("<h2>6. L'asse wdth in Qt</h2>")
    parts.append("<p>Lo stesso testo a 13 px con <code>QFont.setVariableAxis(wdth)</code>, con <code>setStretch(75)</code>, con il nome dello stile e con un condensato statico. "
                 "Windows (DirectWrite) e Linux (FreeType) danno risultati diversi: vedi il README.</p>")
    parts.append(f'<div class="row"><p class="cap"><b>Windows 11, Qt 6.12</b></p>{img("axis-win.png", 1)}</div>')
    parts.append(f'<div class="row"><p class="cap"><b>Fedora (Lucciola), Qt 6.12</b></p>{img("axis-linux.png", 1)}</div>')
    parts.append("</body></html>")
    (HERE / "bozzetti.html").write_text("\n".join(parts), encoding="utf-8")
    print("bozzetti.html written")


if __name__ == "__main__":
    main()
