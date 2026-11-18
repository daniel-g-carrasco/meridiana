"""The sketches of study 22 (phases, bars, tools, 3D previews) as SVG, and their PNG through Qt offscreen.

Run from the repository root with the venv's Python and QT_QPA_PLATFORM=offscreen:
    python docs/studio/22-fase-modellazione/bozzetti.py
Only drawings: nothing of the program is imported."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "Segoe UI"
INK, DIM, LINE, BG, CARD = "#2b2622", "#7a6f66", "#b8ada3", "#f4f1ec", "#ffffff"
ACCENT, ACCENT_BG, OLD, NEW = "#8a5a1e", "#f0e3d1", "#c9bfb4", "#3f7d4a"
RIDGE, EAVE, VALLEY = "#b7791f", "#3f7d4a", "#3b6ea5"


class Svg:
    def __init__(self, w: int, h: int):
        self.w, self.h, self.parts = w, h, []
        self.rect(0, 0, w, h, BG, "none", 0)

    def rect(self, x, y, w, h, fill=CARD, stroke=LINE, sw=1, r=6, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight="normal", italic=False):
        st = ' font-style="italic"' if italic else ""
        self.parts.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
                          f'text-anchor="{anchor}" font-weight="{weight}"{st}>{s}</text>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.5, dash="", arrow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                          f'stroke-width="{sw}"{d}{m} stroke-linecap="round"/>')

    def poly(self, pts, fill="none", stroke=INK, sw=1.5, closed=True, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        tag = "polygon" if closed else "polyline"
        s = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.parts.append(f'<{tag} points="{s}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} '
                          f'stroke-linejoin="round"/>')

    def circle(self, x, y, r, fill=CARD, stroke=INK, sw=1.5):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def pill(self, x, y, s, size=11, fill=CARD, ink=INK, stroke=LINE):
        w = len(s) * size * 0.58 + 12
        self.rect(x - w / 2, y - size * 0.8, w, size * 1.5, fill, stroke, 1, size * 0.75)
        self.text(x, y + size * 0.3, s, size, ink, "middle")
        return w

    def save(self, name: str) -> Path:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}"><defs><marker id="arrow" markerWidth="8" markerHeight="8" '
                f'refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{INK}"/></marker></defs>')
        path = HERE / name
        path.write_text(head + "\n".join(self.parts) + "</svg>", encoding="utf-8")
        return path


# ---- the bar of a phase: groups of tools -------------------------------------------------------------------

def bar(s: Svg, x, y, groups, primary=None, new=(), gone=()):
    """groups: [(title, [(label, key), ...])]; returns the width used."""
    cx = x
    for title, tools in groups:
        gx = cx
        for label, key in tools:
            w = max(58, len(label) * 7 + 14)
            fill = ACCENT_BG if label == primary else CARD
            stroke = NEW if label in new else (OLD if label in gone else LINE)
            s.rect(cx, y, w, 44, fill, stroke, 2 if label in new or label in gone else 1, 5,
                   "4,3" if label in gone else "")
            s.text(cx + w / 2, y + 18, "⬚", 12, DIM, "middle")
            s.text(cx + w / 2, y + 35, label, 11, OLD if label in gone else INK, "middle")
            if key:
                s.text(cx + w - 4, y + 11, key, 8, DIM, "end")
            cx += w + 4
        s.text((gx + cx - 4) / 2, y + 60, title, 10, DIM, "middle")
        s.line(cx + 4, y + 4, cx + 4, y + 40, LINE, 1)
        cx += 14
    return cx - x


def phase_row(s: Svg, x, y, names, active=0):
    cx = x
    for i, n in enumerate(names):
        w = len(n) * 7.2 + 30
        if i == active:
            s.rect(cx, y, w, 28, ACCENT_BG, ACCENT, 1, 5)
        s.text(cx + 10, y + 19, str(i + 1), 11, ACCENT, "start", "bold")
        s.text(cx + 24, y + 19, n, 12, INK if i == active else DIM)
        cx += w + 6
    return cx - x


def fig_fasi():
    s = Svg(1240, 700)
    s.text(20, 30, "Prima e dopo: le fasi e le barre di Modello/Modellazione e di Impianto", 16, INK, "start", "bold")
    # today
    s.text(20, 66, "OGGI (phases.py, R205)", 12, DIM, "start", "bold")
    phase_row(s, 20, 76, ["Modello", "Impianto", "Producibilità", "Consumi", "Bilancio ed economia", "Relazione"])
    s.text(20, 130, "1 Modello", 11, DIM)
    bar(s, 20, 138, [
        ("Modifica", [("Seleziona", "V"), ("Sposta", "M"), ("Ruota", "")]),
        ("Disegna", [("Edificio", "B"), ("Modello", ""), ("Pensilina", ""), ("Falda", "P"), ("Esclusione", "X")]),
        ("Posa", [("Sottocampo", "S"), ("Fila", "L"), ("Est-ovest", ""), ("Posa", ""), ("Svuota", "")]),
        ("Precisione", [("Misura", "D"), ("Squadra", "Q"), ("Rettangolo", "R")])], primary="Posa",
        gone=("Sottocampo", "Fila", "Est-ovest", "Posa", "Svuota"))
    s.text(20, 230, "2 Impianto", 11, DIM)
    bar(s, 20, 238, [
        ("Inverter", [("Catalogo", ""), ("Dimensiona", "")]),
        ("Accumulo", [("Configura", "")]),
        ("Stringhe", [("Proponi", ""), ("Completa", ""), ("Disegna", ""), ("Ricomincia", "")])])
    s.text(640, 262, "la posa dei moduli sta in Modello; l'impianto parte dagli inverter", 11, DIM, "start", "normal",
           True)
    s.line(20, 330, 1220, 330, LINE, 1, "6,4")
    # proposal
    s.text(20, 362, "PROPOSTA (R277)", 12, NEW, "start", "bold")
    phase_row(s, 20, 372, ["Modellazione", "Impianto", "Producibilità", "Consumi", "Bilancio ed economia",
                           "Relazione"])
    s.text(20, 426, "1 Modellazione: solo il sito e i volumi", 11, DIM)
    bar(s, 20, 434, [
        ("Modifica", [("Seleziona", "V"), ("Sposta", "M"), ("Ruota", "")]),
        ("Edifici", [("Edificio", "B"), ("Da modello", "E"), ("Pensilina", "T")]),
        ("Tetto", [("Falda", "P"), ("Colmo", "C"), ("Tipo…", "")]),
        ("Ostacoli", [("Esclusione", "X"), ("Oggetto 3D", "O")]),
        ("Precisione", [("Misura", "D"), ("Squadra", "Q"), ("Rettangolo", "R")])],
        new=("Pensilina", "Colmo", "Tipo…", "Oggetto 3D"))
    s.text(20, 526, "2 Impianto: pannelli, poi inverter, poi accumulo; le stringhe chiudono", 11, DIM)
    bar(s, 20, 534, [
        ("Pannelli", [("Sottocampo", "S"), ("Fila", "L"), ("Est-ovest", ""), ("Su pensilina", ""), ("Posa", ""),
                      ("Svuota", "")]),
        ("Inverter", [("Catalogo", ""), ("Dimensiona", "")]),
        ("Accumulo", [("Configura", "")]),
        ("Stringhe", [("Proponi", ""), ("Completa", ""), ("Disegna", ""), ("Ricomincia", "")])],
        primary="Posa", new=("Su pensilina",))
    s.text(20, 630, "Legenda: bordo verde = comando nuovo; tratteggio grigio = comando che lascia questa barra; "
                    "fondo ambra = pulsante principale della fase.", 10, DIM)
    s.text(20, 648, "I tasti C, E, O, T oggi sono liberi (shortcuts.py); «Tipo…» apre il gruppo Tetto nelle "
                    "proprietà.", 10, DIM)
    s.text(20, 666, "Le fasi restano sei e sono luoghi, non tappe (design 2.1): i tasti Ctrl+1…6 non cambiano.",
           10, DIM)
    return s.save("fasi-e-barre.svg")


# ---- the hand-drawn pitch (R274) ---------------------------------------------------------------------------

def plan_building(s: Svg, x, y, scale=9):
    pts = [(0, 0), (20, 0), (20, 14), (0, 14)]
    P = [(x + px * scale, y + (14 - py) * scale) for px, py in pts]
    s.poly(P, "#fbf9f6", INK, 1.5)
    return P


def fig_falda():
    s = Svg(1240, 560)
    s.text(20, 30, "Falda disegnata a mano (R274): la gronda, poi la profondità; angolo, colmo e punto di arrivo "
                   "nella scheda che segue il puntatore", 15, INK, "start", "bold")
    # step 1
    x0, y0 = 20, 70
    s.text(x0, y0 - 8, "1. Due clic: la linea di gronda", 12, INK, "start", "bold")
    P = plan_building(s, x0, y0)
    gx1, gy = P[0][0] + 18, P[0][1] - 18
    gx2 = P[1][0] - 18
    s.line(gx1, gy, gx2, gy, EAVE, 3)
    s.circle(gx1, gy, 4, EAVE, EAVE)
    s.circle(gx2, gy, 4, EAVE, EAVE)
    s.text((gx1 + gx2) / 2, gy + 16, "gronda · 16,00 m · quota 6,00 m (gronda edificio)", 10, EAVE, "middle")
    # step 2
    x1 = 400
    s.text(x1, y0 - 8, "2. Il puntatore sale: la falda si forma; un numero digitato è la profondità", 12, INK,
           "start", "bold")
    P = plan_building(s, x1, y0)
    gx1, gy = P[0][0] + 18, P[0][1] - 18
    gx2 = P[1][0] - 18
    ry = gy - 7 * 9
    s.poly([(gx1, gy), (gx2, gy), (gx2, ry), (gx1, ry)], "#e6efe7", INK, 1.2)
    s.line(gx1, gy, gx2, gy, EAVE, 3)
    s.line(gx1, ry, gx2, ry, RIDGE, 3)
    mx = (gx1 + gx2) / 2
    s.line(mx, ry + 6, mx, gy - 8, INK, 1.2, "", True)
    s.text(mx + 6, (ry + gy) / 2, "pendenza", 9, DIM)
    s.text((gx1 + gx2) / 2, ry - 8, "colmo", 10, RIDGE, "middle")
    # the floating card
    cx, cy = x1 + 215, y0 + 10
    s.rect(cx, cy, 160, 118, CARD, LINE, 1, 8)
    s.text(cx + 10, cy + 18, "Falda", 11, INK, "start", "bold")
    rows = [("Profondità", "7,00 m"), ("Inclinazione", "20,0°  ◂ 36 %"), ("Quota colmo", "8,55 m"),
            ("Gronda", "6,00 m")]
    for i, (k, v) in enumerate(rows):
        s.text(cx + 10, cy + 40 + i * 19, k, 10, DIM)
        s.text(cx + 150, cy + 40 + i * 19, v, 10, INK, "end")
    s.rect(cx + 76, cy + 46, 78, 16, ACCENT_BG, ACCENT, 1, 4)
    s.text(cx + 10, cy + 112, "Tab: gronda ⇄ colmo   Invio: fatto", 9, DIM)
    # step 3: swap
    x2 = 820
    s.text(x2, y0 - 8, "3. Tab scambia gronda e colmo (R274), senza ridisegnare", 12, INK, "start", "bold")
    P = plan_building(s, x2, y0)
    gx1, gy = P[0][0] + 18, P[0][1] - 18
    gx2 = P[1][0] - 18
    ry = gy - 7 * 9
    s.poly([(gx1, gy), (gx2, gy), (gx2, ry), (gx1, ry)], "#e6efe7", INK, 1.2)
    s.line(gx1, gy, gx2, gy, RIDGE, 3)
    s.line(gx1, ry, gx2, ry, EAVE, 3)
    mx = (gx1 + gx2) / 2
    s.line(mx, gy - 6, mx, ry + 8, INK, 1.2, "", True)
    s.text((gx1 + gx2) / 2, gy + 16, "colmo", 10, RIDGE, "middle")
    s.text((gx1 + gx2) / 2, ry - 8, "gronda (quota 6,00 m)", 10, EAVE, "middle")
    # legend of the ways to fix the third value
    yy = 250
    s.text(20, yy, "Tre modi di chiudere la falda, uno solo per volta (gli altri due si ricalcolano):", 12, INK,
           "start", "bold")
    items = [
        ("Inclinazione", "digita «20» nella scheda o ruota il campo: la profondità resta, la quota del colmo "
                         "segue (gronda + profondità × tan α)"),
        ("Quota del colmo", "digita la quota in metri: l'inclinazione segue; rifiutata sotto la gronda (come oggi "
                            "ridge_written)"),
        ("Punto di arrivo", "clic su un punto della pianta (un altro colmo, un muro, un aggancio): la profondità "
                            "diventa la distanza dalla gronda; Maiusc tiene l'ortogonale come oggi"),
    ]
    for i, (k, v) in enumerate(items):
        s.text(30, yy + 24 + i * 22, "•  " + k, 11, INK, "start", "bold")
        s.text(170, yy + 24 + i * 22, v, 11, INK)
    s.text(20, yy + 100, "Valori iniziali: inclinazione proposta dal manto dell'edificio (roofs.proposed_tilt, "
                         "35 % tegole), gronda = quota di gronda dell'edificio.", 11, DIM)
    s.text(20, yy + 120, "La scheda è la stessa «misura accanto al puntatore» di oggi (plan._draw_labels) con tre "
                         "campi scrivibili; non una finestra modale.", 11, DIM)
    s.text(20, yy + 150, "Dopo il disegno: la falda ha le proprietà Gronda (lato, quota), Inclinazione, Quota colmo, "
                         "Profondità, e il pulsante «Scambia gronda e colmo»; i lati si tirano come gli altri (R276).",
           11, DIM)
    s.text(20, yy + 180, "Dati: nessun formato nuovo per la falda libera (anello + eave_side + eave + tilt bastano); "
                         "la quota del colmo è derivata.", 11, DIM)
    s.text(20, yy + 230, "Il tasto Tab durante il disegno va verificato contro gli usi di Tab nella pianta "
                         "(ciclo dei campi? nessuno oggi in plan.py: da confermare).", 10, DIM, "start", "normal", True)
    return s.save("falda-a-mano.svg")


# ---- the ridge that makes the roof (R275) ------------------------------------------------------------------

def fig_colmo():
    s = Svg(1240, 580)
    s.text(20, 30, "Solo il colmo (R275): si disegna il colmo, il tetto ipotetico viene da sé", 15, INK, "start",
           "bold")
    sc = 8

    def plan(x, y, pts):
        P = [(x + px * sc, y + (20 - py) * sc) for px, py in pts]
        s.poly(P, "#fbf9f6", INK, 1.5)
        return P

    # rectangle
    x0, y0 = 20, 70
    s.text(x0, y0 - 8, "a. Rettangolo: un segmento di colmo", 12, INK, "start", "bold")
    rect = [(0, 0), (24, 0), (24, 12), (0, 12)]
    P = plan(x0, y0 + 40, rect)
    cy = y0 + 40 + (20 - 6) * sc
    s.line(x0 + 3 * sc, cy, x0 + 21 * sc, cy, RIDGE, 3.5)
    s.circle(x0 + 3 * sc, cy, 4, RIDGE, RIDGE)
    s.circle(x0 + 21 * sc, cy, 4, RIDGE, RIDGE)
    s.text(x0 + 12 * sc, cy - 10, "colmo disegnato (2 clic) · quota 9,00 m", 10, RIDGE, "middle")
    # result beside
    x1 = x0 + 260
    P = plan(x1, y0 + 40, rect)
    s.line(x1, cy, x1 + 24 * sc, cy, RIDGE, 3)
    s.line(x1, P[0][1], x1 + 24 * sc, P[0][1], EAVE, 3)
    s.line(x1, P[2][1], x1 + 24 * sc, P[2][1], EAVE, 3)
    s.line(P[0][0], P[0][1], P[3][0], P[3][1], "#888", 3)
    s.line(P[1][0], P[1][1], P[2][0], P[2][1], "#888", 3)
    s.text(x1 + 12 * sc, cy + 36, "due falde, testate ai lati toccati dai capi", 10, DIM, "middle")
    s.text(x1 + 12 * sc, cy - 30, "il colmo si allunga fino ai lati", 10, DIM, "middle")
    s.line(x0 + 24 * sc + 12, cy, x1 - 12, cy, INK, 1.5, "", True)
    # L
    x2 = 620
    s.text(x2, y0 - 8, "b. Pianta a L: una spezzata di colmo", 12, INK, "start", "bold")
    L = [(0, 0), (24, 0), (24, 10), (10, 10), (10, 20), (0, 20)]
    P = plan(x2, y0 + 40, L)
    top = y0 + 40
    a = (x2 + 5 * sc, top + (20 - 5) * sc)
    b = (x2 + 20 * sc, top + (20 - 5) * sc)
    c = (x2 + 5 * sc, top + (20 - 17) * sc)
    s.poly([c, a, b], "none", RIDGE, 3.5, False)
    for p in (a, b, c):
        s.circle(*p, 4, RIDGE, RIDGE)
    s.text(a[0] - 8, a[1] + 14, "3 clic, Invio", 10, RIDGE, "end")
    x3 = x2 + 260
    P = plan(x3, y0 + 40, L)
    a3, b3, c3 = (a[0] + 260, a[1]), (b[0] + 260 + 4 * sc, b[1]), (c[0] + 260, c[1] - 3 * sc)
    s.poly([c3, a3, b3], "none", RIDGE, 3, False)
    # hip/valley from the inner corner
    inner = (x3 + 10 * sc, top + (20 - 10) * sc)
    s.line(inner[0], inner[1], a3[0], a3[1], VALLEY, 2.5)
    s.text(inner[0] + 6, inner[1] + 14, "compluvio", 9, VALLEY)
    s.text(x3 + 12 * sc, top + 20 * sc + 18, "scheletro dritto (skeleton.py) con il colmo come vincolo", 10, DIM,
           "middle")
    s.line(x2 + 24 * sc + 12, top + 10 * sc, x3 - 12, top + 10 * sc, INK, 1.5, "", True)
    # explanation
    yy = 300
    s.text(20, yy, "Che cosa fa il programma", 12, INK, "start", "bold")
    lines = [
        "1. Il colmo si disegna dentro un edificio (come la falda oggi, _host). Ogni segmento è parallelo a un lato:",
        "    si aggancia all'asse del rettangolo o ai lati vicini (snapping.py); fuori asse, avviso.",
        "2. I lati toccati (o quasi) dai capi del colmo diventano testate, gli altri gronde: è roof.edges di oggi",
        "    (formato 9), scritto dal gesto invece che lato per lato.",
        "3. La quota del colmo, chiesta a fine disegno (campo accanto al puntatore, prevalore = gronda + metà larghezza",
        "    × tan 35 %), dà la pendenza con roofs.slope_from_heights: è il ridge_height di oggi.",
        "4. Il tetto è «gable» sullo scheletro dritto (roofs.pitched): sulla L i compluvi vengono da soli. Il colmo",
        "    disegnato è conservato (roof.ridge_line) per poterlo spostare o riquotare.",
        "5. Colmo fuori asse (falde di larghezza diversa) = due pendenze diverse: scheletro pesato, oggi non c'è.",
        "    Primo lotto: il colmo si aggancia all'asse e lo dice; secondo lotto: asimmetrico.",
    ]
    for i, t in enumerate(lines):
        s.text(30, yy + 20 + i * 16, t, 11, INK)
    s.text(20, yy + 190, "Dati: formato 21, Roof.ridge_line: list | None (punti in metri). Migrazione 20 → 21: None "
                         "per tutti i tetti di prima; chi ha ridge_height e edges resta com'è.", 11, DIM)
    s.text(20, yy + 210, "Prova dove decide: 306 piante di 16-prove/scheletro-riferimento.json, colmo centrato: le "
                         "falde devono coincidere con quelle del gable con le stesse testate.", 11, DIM)
    return s.save("colmo-tetto.svg")


# ---- sides clickable on the plan and the 3D preview (R276, R282) -------------------------------------------

def axo(x, y, z, ox, oy, k=9.0):
    """A cabinet-like axonometry: x to the right-down, y to the right-up, z up."""
    ax, ay = math.radians(25), math.radians(-25)
    px = ox + k * (x * math.cos(ax) + y * math.cos(ay) * 0.9)
    py = oy - k * (-x * math.sin(ax) + y * math.sin(-ay) * 0.9 + z)
    return px, py


def canopy_axo(s: Svg, ox, oy, hover=None, k=9.0, W=10.0, D=5.0, H=2.7, tilt=8.0, pillars=3):
    rise = D * math.tan(math.radians(tilt))
    # pillars along the back edge (y = D)
    for i in range(pillars):
        px = W * i / (pillars - 1) if pillars > 1 else W / 2
        a = axo(px, D * 0.5, 0, ox, oy, k)
        b = axo(px, D * 0.5, H + rise * 0.5, ox, oy, k)
        s.line(a[0], a[1], b[0], b[1], INK, 3)
    # beam
    a = axo(0, D * 0.5, H + rise * 0.5, ox, oy, k)
    b = axo(W, D * 0.5, H + rise * 0.5, ox, oy, k)
    s.line(a[0], a[1], b[0], b[1], INK, 3)
    # roof plane
    roof = [axo(0, 0, H, ox, oy, k), axo(W, 0, H, ox, oy, k), axo(W, D, H + rise, ox, oy, k),
            axo(0, D, H + rise, ox, oy, k)]
    s.poly(roof, "#e6efe7", INK, 1.5)
    # purlins
    for j in (1, 2, 3):
        t = j / 4
        a, b = axo(0, D * t, H + rise * t, ox, oy, k), axo(W, D * t, H + rise * t, ox, oy, k)
        s.line(a[0], a[1], b[0], b[1], "#999", 1)
    # clickable sides
    sides = {
        "larghezza": (roof[0], roof[1], f"{W:g} m"),
        "profondita": (roof[1], roof[2], f"{D:g} m"),
        "altezza": (axo(W, 0, 0, ox, oy, k), axo(W, 0, H, ox, oy, k), f"{H:g} m"),
        "pendenza": (roof[3], roof[2], f"{tilt:g}°"),
    }
    for name, (a, b, label) in sides.items():
        hot = name == hover
        col = ACCENT if hot else INK
        s.line(a[0], a[1], b[0], b[1], col, 3 if hot else 1.5)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        s.pill(mx + (14 if name != "pendenza" else -30), my + (14 if name == "larghezza" else -6), label, 10,
               ACCENT_BG if hot else CARD, ACCENT if hot else INK, ACCENT if hot else LINE)
    # ground shadow of the pillars' feet
    base = [axo(0, 0, 0, ox, oy, k), axo(W, 0, 0, ox, oy, k), axo(W, D, 0, ox, oy, k), axo(0, D, 0, ox, oy, k)]
    s.poly(base, "none", LINE, 1, True, "3,3")


def fig_lati_anteprima():
    s = Svg(1240, 620)
    s.text(20, 30, "Lati cliccabili in pianta (R276) e anteprima 3D cliccabile nelle finestrelle (R282)", 15, INK,
           "start", "bold")
    # plan with side numbers and lengths
    s.text(20, 66, "Pianta, edificio selezionato: numero del lato e misura nella stessa pillola; un clic apre il "
                   "campo lì", 12, INK, "start", "bold")
    sc = 9
    x0, y0 = 60, 110
    L = [(0, 0), (20, 0), (20, 8), (8, 8), (8, 18), (0, 18)]
    P = [(x0 + px * sc, y0 + (18 - py) * sc) for px, py in L]
    s.poly(P, "#fbf9f6", ACCENT, 2)
    lengths = [20, 8, 12, 10, 8, 18]
    offs = [(0, 18), (16, 0), (0, -14), (16, 0), (0, -14), (-18, 0)]
    for i in range(6):
        a, b = P[i], P[(i + 1) % 6]
        mx, my = (a[0] + b[0]) / 2 + offs[i][0], (a[1] + b[1]) / 2 + offs[i][1]
        if i == 2:
            s.rect(mx - 40, my - 12, 80, 24, CARD, ACCENT, 1.5, 6)
            s.text(mx - 32, my + 4, "③", 11, ACCENT)
            s.text(mx - 14, my + 4, "12,00", 11, INK)
            s.rect(mx - 18, my - 8, 42, 16, "none", ACCENT, 1, 3)
            s.text(mx + 30, my + 4, "m", 10, DIM)
        else:
            s.pill(mx, my, f"{'①②③④⑤⑥'[i]} {lengths[i]:g} m", 10)
    s.text(20, y0 + 18 * sc + 40, "Oggi: misure sì (plan._draw_sides, doppio clic → QInputDialog), numeri no;", 10, DIM)
    s.text(20, y0 + 18 * sc + 54, "le Proprietà dicono «Lato 3» senza mostrarlo in pianta.", 10, DIM)
    s.text(20, y0 + 18 * sc + 72, "Dopo: pillola «③ 12,00 m», un clic (non doppio) apre il campo nella "
                                             "pillola; Invio tira il lato (sides.stretch).", 10, DIM)
    s.text(20, y0 + 18 * sc + 88, "Passando sul campo «Lato 3» delle Proprietà il lato 3 si accende in "
                                             "pianta (e viceversa).", 10, DIM)
    # dialog with 3D preview
    dx, dy = 560, 60
    s.rect(dx, dy, 640, 470, CARD, LINE, 1, 10)
    s.text(dx + 16, dy + 26, "Pensilina (struttura)", 13, INK, "start", "bold")
    rows = [("Posti per fila", "4"), ("File", "una, falda unica"), ("Larghezza posto", "2,50 m"),
            ("Profondità", "5,00 m"), ("Altezza libera", "2,70 m"), ("Pendenza", "8,0°"), ("Pilastri", "3, in asse"),
            ("Rotazione", "0°")]
    for i, (k, v) in enumerate(rows):
        yy = dy + 56 + i * 30
        s.text(dx + 16, yy, k, 11, DIM)
        hot = k == "Profondità"
        s.rect(dx + 130, yy - 14, 120, 22, ACCENT_BG if hot else "#f3f0eb", ACCENT if hot else LINE, 1.5 if hot else 1, 4)
        s.text(dx + 138, yy + 1, v, 11, INK)
    s.rect(dx + 270, dy + 44, 354, 300, "#faf8f5", LINE, 1, 8)
    canopy_axo(s, dx + 320, dy + 270, hover="profondita", k=13)
    s.text(dx + 447, dy + 334, "trascina per girare · clic su un lato per scriverlo", 9, DIM, "middle")
    s.text(dx + 16, dy + 318, "Anteprima 3D: assonometria", 10, DIM)
    s.text(dx + 16, dy + 332, "QPainter, niente Qt Quick 3D;", 10, DIM)
    s.text(dx + 16, dy + 346, "si aggiorna a ogni valore.", 10, DIM)
    s.text(dx + 16, dy + 380, "Crea solo la struttura: pilastri, travi, piano di copertura. I moduli si posano nella fase "
                              "Impianto (Pannelli › Su pensilina).", 10, DIM)
    s.rect(dx + 380, dy + 420, 130, 30, ACCENT_BG, ACCENT, 1, 6)
    s.text(dx + 445, dy + 440, "Mettila in pianta", 11, INK, "middle")
    s.rect(dx + 520, dy + 420, 100, 30, CARD, LINE, 1, 6)
    s.text(dx + 570, dy + 440, "Annulla", 11, INK, "middle")
    s.text(20, 590, "Lo stesso widget di anteprima serve a «Da modello» (prisma della pianta con tetto piano, lati "
                    "numerati cliccabili), alla falda (scheda) e alla pensilina. Clic su un lato = il campo del "
                    "modulo prende il fuoco e si accende; la misura si scrive lì o in una pillola sul lato.", 10, DIM)
    return s.save("lati-e-anteprima-3d.svg")


# ---- the canopy: structure then modules (R281) -------------------------------------------------------------

def fig_pensilina():
    s = Svg(1240, 520)
    s.text(20, 30, "Pensilina (R281): oggi due piani di posa con i moduli; dopo, la struttura in Modellazione e la "
                   "posa semplificata in Impianto", 15, INK, "start", "bold")
    s.text(20, 66, "OGGI (canopies.py): «Crea superfici di posa e moduli»", 12, DIM, "start", "bold")
    # today: two subfields with modules, axo
    ox, oy = 90, 290
    k = 11
    W, D, H, rise = 10.0, 5.0, 2.7, 5 * math.tan(math.radians(8))
    for row, sign in ((0, 1), (1, -1)):
        y0 = D if row == 1 else 0
        base_h = H + (rise if row == 1 else 0)
        pts = [axo(0, y0, base_h, ox, oy, k), axo(W, y0, base_h, ox, oy, k),
               axo(W, y0 + D, base_h + sign * rise, ox, oy, k), axo(0, y0 + D, base_h + sign * rise, ox, oy, k)]
        s.poly(pts, "#dde5f2", INK, 1.2)
        for i in range(8):
            for j in range(3):
                x1, x2 = i * W / 8 + 0.1, (i + 1) * W / 8 - 0.1
                t1, t2 = j / 3 + 0.03, (j + 1) / 3 - 0.03
                q = [axo(x1, y0 + D * t1, base_h + sign * rise * t1, ox, oy, k),
                     axo(x2, y0 + D * t1, base_h + sign * rise * t1, ox, oy, k),
                     axo(x2, y0 + D * t2, base_h + sign * rise * t2, ox, oy, k),
                     axo(x1, y0 + D * t2, base_h + sign * rise * t2, ox, oy, k)]
                s.poly(q, "#2f4f7f", "none", 0)
    s.text(20, oy + 60, "piani sospesi a 2,70 m, nessun pilastro né trave: in 3D e in IFC galleggiano", 10, DIM)
    s.text(20, oy + 76, "le due file opposte si incontrano sul colmo in mezzo; otto opzioni nella finestra", 10, DIM)
    # after
    s.text(560, 66, "DOPO: 1 Modellazione › Pensilina (struttura)", 12, NEW, "start", "bold")
    canopy_axo(s, 620, 290, None, 11, pillars=3)
    s.text(560, 350, "pilastri, trave, piano di copertura (falda unica o due falde)", 10, DIM)
    s.text(560, 376, "DOPO: 2 Impianto › Pannelli › Su pensilina", 12, NEW, "start", "bold")
    # simplified module laying card
    cx, cy = 560, 386
    s.rect(cx, cy, 300, 112, CARD, LINE, 1, 8)
    rows = [("Orientamento", "lungo la falda ▾"), ("File di moduli", "2 (riempie la profondità)"),
            ("Sporto oltre la struttura", "0,20 m"), ("Bordo", "0,10 m")]
    for i, (kk, v) in enumerate(rows):
        s.text(cx + 10, cy + 22 + i * 22, kk, 10, DIM)
        s.text(cx + 290, cy + 22 + i * 22, v, 10, INK, "end")
    s.text(880, 410, "Una sola falda = un sottocampo; i moduli", 10, DIM)
    s.text(880, 426, "coprono tutta la falda, senza file né", 10, DIM)
    s.text(880, 442, "corridoi: niente «passo», niente «altezza", 10, DIM)
    s.text(880, 458, "dal piano». La pendenza è quella della struttura.", 10, DIM)
    s.text(880, 486, "Nessun modulo appare in Modellazione.", 10, NEW, "start", "bold")
    return s.save("pensilina-struttura-posa.svg")


def render_pngs(paths):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    app = QGuiApplication.instance() or QGuiApplication([])
    for p in paths:
        r = QSvgRenderer(str(p))
        size = r.defaultSize()
        img = QImage(size.width(), size.height(), QImage.Format.Format_ARGB32)
        img.fill(0xFFFFFFFF)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        r.render(painter, QRectF(0, 0, size.width(), size.height()))
        painter.end()
        out = p.with_suffix(".png")
        img.save(str(out))
        print(out.name, size.width(), size.height())
    del app


if __name__ == "__main__":
    made = [fig_fasi(), fig_falda(), fig_colmo(), fig_lati_anteprima(), fig_pensilina()]
    if "--svg-only" not in sys.argv:
        render_pngs(made)
