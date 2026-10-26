#!/usr/bin/env python3
"""Render the three study mockups offscreen with Meridiana's real design tokens.

Run from the repository root:
    QT_QPA_PLATFORM=offscreen PYTHONPATH=src python docs/studio/20-inizio-progetto/genera_bozzetti.py

Every client, job, project, address and place in the drawings is invented.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QByteArray, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QImage, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from meridiana import theme_colors
from meridiana.ui import design, icons

W, H = 1600, 960
OUT = HERE / "bozzetti"
PHASES = ("Modello", "Impianto", "Producibilità", "Consumi", "Bilancio ed economia", "Relazione")


class Canvas:
    def __init__(self, image: QImage, tokens: dict):
        self.image = image
        self.t = tokens
        self.p = QPainter(image)
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.base = QFont("Inter")

    def colour(self, role: str, alpha: int | None = None) -> QColor:
        value = self.t.get(role, theme_colors.STATUS.get(role, role))
        c = QColor(value)
        if alpha is not None:
            c.setAlpha(alpha)
        return c

    def rect(self, x, y, w, h, fill="panel", line="", radius=design.Radius.CARD, width=1):
        self.p.setPen(QPen(self.colour(line), width) if line else Qt.PenStyle.NoPen)
        self.p.setBrush(self.colour(fill) if fill else Qt.BrushStyle.NoBrush)
        self.p.drawRoundedRect(QRectF(x, y, w, h), radius, radius)

    def rule(self, x1, y1, x2, y2, role="line_soft", width=1):
        self.p.setPen(QPen(self.colour(role), width))
        self.p.drawLine(QLineF(x1, y1, x2, y2))

    def text(self, x, y, w, h, value, style=design.Text.BODY, colour="", wrap=False, align="left"):
        font = design.text_font(style, self.base)
        self.p.setFont(font)
        self.p.setPen(self.colour(colour or style.tone))
        flags = Qt.AlignmentFlag.AlignTop
        flags |= {"left": Qt.AlignmentFlag.AlignLeft, "right": Qt.AlignmentFlag.AlignRight,
                  "center": Qt.AlignmentFlag.AlignHCenter}[align]
        if wrap:
            flags |= Qt.TextFlag.TextWordWrap
            shown = value
        else:
            flags |= Qt.TextFlag.TextSingleLine
            shown = QFontMetrics(font).elidedText(value, Qt.TextElideMode.ElideRight, max(1, int(w)))
        self.p.drawText(QRectF(x, y, w, h), flags, shown)

    def icon(self, name, x, y, size=design.Icon.LIST, colour="text2"):
        data = icons.svg(name).replace(b"currentColor", self.colour(colour).name().encode("ascii"))
        if not data:
            return
        renderer = QSvgRenderer(QByteArray(data))
        if renderer.isValid():
            renderer.render(self.p, QRectF(x, y, size, size))

    def pill(self, x, y, w, label, selected=False, colour=""):
        self.rect(x, y, w, design.Size.CHIP, "panel" if selected else "field", "line" if selected else "",
                  design.Radius.pill(design.Size.CHIP))
        self.text(x + design.Space.M, y + 4, w - 2 * design.Space.M, 16, label, design.Text.CONTROL,
                  colour or "text", align="center")

    def button(self, x, y, w, label, primary=False, icon=""):
        self.rect(x, y, w, design.Size.CONTROL, "accent" if primary else "field", "",
                  design.Radius.CONTROL)
        tx = x + design.Space.M
        if icon:
            self.icon(icon, x + design.Space.M, y + 6, design.Icon.CONTROL,
                      "accent_fg" if primary else "text2")
            tx += design.Icon.CONTROL + design.Space.S
        self.text(tx, y + 6, w - (tx - x) - design.Space.M, 17, label, design.Text.STRONG,
                  "accent_fg" if primary else "text", align="center")

    def field(self, x, y, w, label, value, note="", focus=False):
        self.text(x, y, w, 16, label, design.Text.SECONDARY)
        self.rect(x, y + 18, w, design.Size.CONTROL, "field", "accent" if focus else "",
                  design.Radius.CONTROL, design.Line.FOCUS if focus else design.Line.HAIR)
        self.text(x + design.Line.TEXT_INSET, y + 24, w - 2 * design.Line.TEXT_INSET, 17, value)
        if note:
            self.text(x, y + 50, w, 30, note, design.Text.SECONDARY, wrap=True)

    def card(self, x, y, w, h, title="", icon=""):
        self.rect(x, y, w, h, "panel", "card_line")
        if title:
            if icon:
                self.icon(icon, x + design.Space.L, y + design.Space.M, design.Icon.CONTROL)
            self.text(x + design.Space.L + (design.Icon.CONTROL + design.Space.M if icon else 0),
                      y + design.Space.M, w - 2 * design.Space.L - 28, 20, title, design.Text.TITLE)

    def label(self, x, y, w, value):
        self.text(x, y, w, 16, value.upper(), design.Text.LABEL)

    def checkbox(self, x, y, label, checked=False):
        self.rect(x, y + 2, 16, 16, "accent" if checked else "field", "accent" if checked else "field_line",
                  design.Radius.INNER)
        if checked:
            self.icon("check", x + 2, y + 4, 12, "accent_fg")
        self.text(x + 24, y + 2, 300, 18, label)

    def end(self):
        self.p.end()


def app_frame(c: Canvas, file_on=True, active=0):
    c.rect(0, 0, W, H, "window", "", 0)
    c.button(12, 12, 88, "File", file_on, "folder-open")
    x = 112
    widths = (100, 100, 126, 100, 156, 100)
    for i, (name, width) in enumerate(zip(PHASES, widths, strict=True)):
        selected = not file_on and i == active
        c.rect(x, 10, width, 38, "panel" if selected else "window", "line_soft" if selected else "",
               design.Radius.CARD)
        c.rect(x + 8, 17, 20, 20, "accent" if selected else "line_soft", "", 10)
        c.text(x + 8, 20, 20, 14, str(i + 1), design.Text.LABEL,
               "accent_fg" if selected else "muted", align="center")
        c.text(x + 34, 21, width - 40, 18, name,
               design.Text.STRONG if selected else design.Text.CONTROL)
        x += width + 2
    c.pill(1390, 16, 194, "Variante: Base  ⌄")
    c.rule(0, 934, W, 934)
    c.text(16, 940, 1100, 16, "Meridiana · bozzetto di studio, dati inventati", design.Text.SECONDARY)
    c.text(1180, 940, 404, 16, "Inter · token del tema · 1600 × 960", design.Text.CAPTION, align="right")


def file_nav(c: Canvas, selected="new"):
    c.card(12, 58, 240, 866)
    entries = [
        ("back", "Torna al progetto", "Esc"),
        None,
        ("new", "Nuovo", "Ctrl+N"),
        ("open", "Apri", "Ctrl+O"),
        ("save", "Salva", "Ctrl+S"),
        ("revision", "Salva una revisione", "_R01"),
        None,
        ("registry", "Clienti e commesse", ""),
        ("import", "Importa ed esporta", ""),
        None,
        ("catalogues", "Cataloghi", ""),
        ("preferences", "Preferenze", "Ctrl+,"),
        ("help", "Aiuto e manuale", "F1"),
    ]
    icon_names = {"back": "arrow-left", "new": "file-plus", "open": "folder-open", "save": "save",
                  "revision": "copy-plus", "registry": "users", "import": "download", "catalogues": "library",
                  "preferences": "settings", "help": "book-open"}
    y = 68
    for entry in entries:
        if entry is None:
            c.rule(24, y + 4, 240, y + 4)
            y += 12
            continue
        key, label, keys = entry
        if key == selected:
            c.rect(20, y, 224, design.Size.NAV, "select_bg", "", design.Radius.CONTROL)
        c.icon(icon_names[key], 32, y + 8, design.Icon.LIST)
        c.text(60, y + 9, 128, 18, label, design.Text.STRONG if key == selected else design.Text.BODY)
        if keys:
            c.text(174, y + 10, 58, 16, keys, design.Text.CAPTION, align="right")
        y += design.Size.NAV + 2
    c.icon("log-out", 32, 888, design.Icon.LIST)
    c.text(60, 896, 150, 18, "Esci")


def marker(c: Canvas, x, y, number, selected=False):
    colour = "accent" if selected else "text2"
    c.p.setBrush(c.colour(colour))
    c.p.setPen(QPen(c.colour("panel"), 2))
    c.p.drawEllipse(QPointF(x, y), 16, 16)
    c.p.drawLine(QLineF(x, y + 15, x, y + 25))
    c.text(x - 10, y - 8, 20, 16, str(number), design.Text.LABEL,
           "accent_fg" if selected else "panel", align="center")


def road(c: Canvas, points, width=7):
    path = QPainterPath()
    path.moveTo(points[0])
    for point in points[1:]:
        path.lineTo(point)
    c.p.setBrush(Qt.BrushStyle.NoBrush)
    c.p.setPen(QPen(c.colour("line"), width + 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    c.p.drawPath(path)
    c.p.setPen(QPen(c.colour("panel"), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    c.p.drawPath(path)


def draw_map(c: Canvas, x, y, w, h):
    c.rect(x, y, w, h, "view", "line", design.Radius.VIEW)
    c.p.save()
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(x, y, w, h), design.Radius.VIEW, design.Radius.VIEW)
    c.p.setClipPath(clip)
    c.p.fillRect(QRectF(x, y, w, h), c.colour("view"))
    c.p.setPen(Qt.PenStyle.NoPen)
    c.p.setBrush(c.colour("good", 15))
    c.p.drawRect(QRectF(x + w * 0.62, y, w * 0.38, h * 0.42))
    c.p.setBrush(c.colour("accent_soft"))
    c.p.drawEllipse(QRectF(x + w * 0.1, y + h * 0.58, w * 0.36, h * 0.42))
    for i in range(9):
        bx = x + 28 + (i % 3) * 178 + (i // 3) * 24
        by = y + 54 + (i // 3) * 154 + (i % 2) * 24
        c.p.setBrush(c.colour("plan", "bld_fill") if False else c.colour("field"))
        c.p.setPen(QPen(c.colour("line"), 1))
        c.p.drawRect(QRectF(bx, by, 104 + (i % 2) * 30, 62))
    road(c, [QPointF(x - 20, y + h * 0.68), QPointF(x + w * 0.35, y + h * 0.52),
             QPointF(x + w * 0.68, y + h * 0.57), QPointF(x + w + 20, y + h * 0.4)], 9)
    road(c, [QPointF(x + w * 0.28, y - 20), QPointF(x + w * 0.36, y + h * 0.32),
             QPointF(x + w * 0.35, y + h * 0.52), QPointF(x + w * 0.43, y + h + 20)], 7)
    road(c, [QPointF(x + w * 0.68, y - 20), QPointF(x + w * 0.65, y + h * 0.28),
             QPointF(x + w * 0.68, y + h * 0.57), QPointF(x + w * 0.78, y + h + 20)], 6)
    road(c, [QPointF(x - 20, y + h * 0.25), QPointF(x + w * 0.36, y + h * 0.32),
             QPointF(x + w * 0.65, y + h * 0.28), QPointF(x + w + 20, y + h * 0.3)], 5)
    c.text(x + 28, y + 18, 240, 18, "LOCALITÀ CAMPO CHIARO", design.Text.LABEL)
    c.text(x + w * 0.44, y + h * 0.46, 170, 18, "Via della Fonte", design.Text.SECONDARY)
    c.text(x + w * 0.69, y + h * 0.2, 160, 18, "Via dei Tigli", design.Text.SECONDARY)
    marker(c, x + w * 0.52, y + h * 0.43, 1, True)
    marker(c, x + w * 0.27, y + h * 0.23, 2)
    marker(c, x + w * 0.76, y + h * 0.68, 3)
    c.rect(x + 12, y + 12, 318, 32, "panel", "line_soft", design.Radius.CONTROL)
    c.icon("map", x + 20, y + 20, design.Icon.CONTROL)
    c.text(x + 44, y + 20, 276, 17, "Stradale  |  Ortofoto  |  Mondo con stati", design.Text.CONTROL)
    c.rect(x + 12, y + h - 48, w - 24, 36, "panel", "line_soft", design.Radius.CONTROL)
    c.text(x + 24, y + h - 39, w - 48, 18,
           "Stradale OSM · z16 · 2,4 m/pixel · schema inventato", design.Text.SECONDARY)
    c.p.restore()


def new_project(c: Canvas):
    app_frame(c)
    file_nav(c, "new")
    x0 = 268
    c.text(x0 + 16, 76, 900, 30, "Nuovo progetto", design.Text.DISPLAY)
    c.text(x0 + 16, 110, 1050, 22, "Prima il posto. Committente, commessa e dati di rete possono completare il passo dopo.",
           design.Text.DESCRIPTION)
    c.pill(x0 + 16, 144, 128, "1  Il luogo", True)
    c.pill(x0 + 152, 144, 212, "2  Committente e rete")
    c.pill(x0 + 372, 144, 142, "3  Conferma")
    c.card(x0 + 16, 182, 510, 654)
    c.label(x0 + 32, 198, 460, "Progetto")
    c.field(x0 + 32, 222, 478, "Nome breve", "26042 - Capannone Alfa")
    c.field(x0 + 32, 274, 478, "Commessa", "26042, cartella esistente collegata")
    c.label(x0 + 32, 338, 460, "Dove si trova")
    c.field(x0 + 32, 362, 478, "Stabilimento, indirizzo o coordinate", "Campo Chiaro", focus=True)
    c.rect(x0 + 32, 410, 478, 174, "card", "line", design.Radius.CONTROL)
    suggestions = [
        ("1", "Stabilimento Alfa", "Da clienti e progetti, su questo PC"),
        ("2", "Località Campo Chiaro, centro", "Elenco locale, senza rete"),
        ("3", "Campo Chiaro, zona produttiva", "Elenco locale, senza rete"),
    ]
    for i, (number, title, source) in enumerate(suggestions):
        yy = 420 + i * 54
        if i == 0:
            c.rect(x0 + 36, yy - 4, 470, 50, "select_bg", "", design.Radius.INNER)
        c.rect(x0 + 44, yy + 4, 24, 24, "accent" if i == 0 else "line_soft", "", 12)
        c.text(x0 + 44, yy + 8, 24, 15, number, design.Text.LABEL,
               "accent_fg" if i == 0 else "muted", align="center")
        c.text(x0 + 80, yy, 408, 20, title, design.Text.STRONG)
        c.text(x0 + 80, yy + 22, 408, 17, source, design.Text.SECONDARY)
    c.icon("shield-check", x0 + 34, 596, design.Icon.CONTROL, "good")
    c.text(x0 + 58, 596, 442, 34, "Solo suggerimenti locali. La ricerca online parte con il pulsante, non a ogni tasto.",
           design.Text.SECONDARY, wrap=True)
    c.button(x0 + 32, 638, 230, "Cerca online", False, "search")
    c.button(x0 + 270, 638, 240, "Coordinate o collegamento", False, "map-pin")
    c.text(x0 + 32, 680, 478, 42,
           "Il punto scelto resta da confermare sulla mappa. Per un progetto riservato non parte alcuna richiesta.",
           design.Text.SECONDARY, wrap=True)
    c.checkbox(x0 + 32, 734, "Progetto riservato: nessun dato del sito in rete", True)
    c.text(x0 + 32, 772, 478, 38, "Dopo «Crea e disegna»: sfondo automatico sull'ortofoto disponibile, con risoluzione e anno visibili.",
           design.Text.SECONDARY, wrap=True)
    draw_map(c, x0 + 542, 182, 774, 654)
    c.card(x0 + 16, 850, 1300, 74)
    c.icon("info", x0 + 32, 872, design.Icon.CONTROL)
    c.text(x0 + 60, 866, 780, 42,
           "Il segno 1 è sul tetto scelto. Gli altri segni restano visibili per confrontare i posti possibili prima di creare.",
           design.Text.DESCRIPTION, wrap=True)
    c.button(x0 + 1012, 872, 130, "Annulla")
    c.button(x0 + 1150, 872, 150, "Crea e disegna", True, "arrow-right")


def client_row(c: Canvas, x, y, w, name, kind, jobs, selected=False):
    if selected:
        c.rect(x, y, w, 64, "select_bg", "", design.Radius.INNER)
    c.icon("building", x + 10, y + 12, 22)
    c.text(x + 42, y + 8, w - 52, 20, name, design.Text.STRONG)
    c.text(x + 42, y + 32, w - 52, 18, f"{kind} · {jobs}", design.Text.SECONDARY)


def job_row(c: Canvas, x, y, w, code, name, meta, deadline, selected=False, reserved=False):
    if selected:
        c.rect(x, y, w, 82, "select_bg", "", design.Radius.INNER)
    c.text(x + 12, y + 8, 68, 20, code, design.Text.STRONG)
    c.text(x + 88, y + 8, w - 100, 20, name, design.Text.STRONG)
    if reserved:
        c.icon("lock-keyhole", x + w - 32, y + 10, design.Icon.CONTROL)
    c.text(x + 88, y + 32, w - 100, 18, meta, design.Text.SECONDARY)
    c.text(x + 88, y + 54, w - 100, 18, deadline, design.Text.SECONDARY)
    c.rule(x + 12, y + 80, x + w - 12, y + 80)


def registry(c: Canvas):
    app_frame(c)
    file_nav(c, "registry")
    x0 = 268
    c.text(x0 + 16, 76, 900, 30, "Clienti e commesse", design.Text.DISPLAY)
    c.text(x0 + 16, 110, 1050, 22,
           "Il registro resta sul PC. Ogni commessa può avere un piccolo manifesto nella sua cartella esistente.",
           design.Text.DESCRIPTION)
    c.button(x0 + 1010, 82, 142, "Importa / esporta")
    c.button(x0 + 1160, 82, 156, "Nuova commessa", True, "file-plus")
    c.rect(x0 + 16, 148, 1300, 44, "field", "", design.Radius.CONTROL)
    c.icon("search", x0 + 28, 160, design.Icon.CONTROL)
    c.text(x0 + 56, 160, 660, 18, "Cerca per codice, nome, cliente o progetto", design.Text.DESCRIPTION)
    c.pill(x0 + 872, 158, 130, "12 clienti")
    c.pill(x0 + 1010, 158, 136, "8 in corso")
    c.pill(x0 + 1154, 158, 146, "3 scadenze")
    left, centre, right = x0 + 16, x0 + 348, x0 + 934
    c.card(left, 206, 324, 718, "Clienti", "users")
    c.label(left + 16, 248, 288, "Anagrafica locale")
    client_row(c, left + 8, 274, 308, "Azienda Alfa S.p.A.", "Impresa generale", "3 commesse", True)
    client_row(c, left + 8, 344, 308, "Cooperativa Beta", "Sviluppatore", "2 commesse")
    client_row(c, left + 8, 414, 308, "Studio Gamma", "Architettura", "1 commessa")
    client_row(c, left + 8, 484, 308, "Privato Delta", "Persona", "1 commessa")
    c.rule(left + 16, 566, left + 308, 566)
    c.label(left + 16, 584, 288, "Cliente selezionato")
    c.text(left + 16, 610, 292, 24, "Azienda Alfa S.p.A.", design.Text.STRONG)
    c.text(left + 16, 640, 292, 56, "Contatti e dati fiscali solo quando servono agli elaborati. Nessuna fatturazione o campagna commerciale.",
           design.Text.SECONDARY, wrap=True)
    c.text(left + 16, 710, 292, 42, "Esportazione JSON completa o CSV per il foglio di calcolo.",
           design.Text.SECONDARY, wrap=True)
    c.button(left + 16, 866, 140, "Nuovo cliente", False, "file-plus")
    c.button(left + 164, 866, 144, "Modifica", False, "settings")

    c.card(centre, 206, 578, 718, "Commesse di Azienda Alfa", "folder-open")
    c.pill(centre + 16, 248, 116, "In corso", True)
    c.pill(centre + 140, 248, 112, "In attesa")
    c.pill(centre + 260, 248, 112, "Consegnate")
    c.pill(centre + 380, 248, 108, "Archivio")
    c.label(centre + 16, 292, 530, "Aperte")
    job_row(c, centre + 8, 316, 562, "26042", "Capannone Alfa", "Preliminare · 2 progetti Meridiana",
            "Scadenza: verifica rete, 28/10", True)
    job_row(c, centre + 8, 402, 562, "26037", "Insediamento Alfa sud", "Definitivo · 1 progetto Meridiana",
            "Scadenza: relazione, 04/11")
    job_row(c, centre + 8, 488, 562, "26018", "Capannone Beta", "Esecutivo · 4 progetti Meridiana",
            "Nessuna scadenza questa settimana", False, True)
    c.label(centre + 16, 598, 530, "Consegnate di recente")
    job_row(c, centre + 8, 622, 562, "25987", "Polo logistico Alfa", "Consegnata · 3 progetti Meridiana",
            "Archiviare dopo il saldo documentale")
    c.text(centre + 16, 730, 530, 56,
           "Il codice resta una parola di cinque cifre: anno e progressivo. I progetti si collegano con un id stabile, non con il nome del file.",
           design.Text.SECONDARY, wrap=True)
    c.rect(centre + 16, 804, 546, 88, "field", "", design.Radius.CONTROL)
    c.icon("database", centre + 28, 824, design.Icon.TILE)
    c.text(centre + 64, 816, 482, 60,
           "Indice locale aggiornato adesso. Se il server non risponde, le commesse note restano disponibili e la cartella è segnata come non raggiungibile.",
           design.Text.SECONDARY, wrap=True)

    c.card(right, 206, 382, 718, "26042 - Capannone Alfa", "building")
    c.pill(right + 16, 250, 104, "In corso", True)
    c.pill(right + 128, 250, 118, "Preliminare")
    c.text(right + 16, 292, 350, 20, "Azienda Alfa S.p.A.", design.Text.STRONG)
    c.text(right + 16, 318, 350, 38, "Cartella: \\\\studio\\commesse\\26042 - Capannone Alfa\npercorso inventato, fasi e discipline lasciate come sono",
           design.Text.SECONDARY, wrap=True)
    c.button(right + 16, 366, 166, "Apri la cartella", False, "folder-open")
    c.button(right + 190, 366, 176, "Nuovo progetto", False, "file-plus")
    c.label(right + 16, 420, 350, "Progetti collegati")
    c.rect(right + 16, 446, 350, 92, "card", "line_soft", design.Radius.CONTROL)
    c.icon("file-text", right + 28, 458, design.Icon.LIST)
    c.text(right + 56, 454, 296, 20, "26042_fotovoltaico_R03.meridiana", design.Text.STRONG)
    c.text(right + 56, 478, 296, 18, "Ultima revisione · 24/10/2026", design.Text.SECONDARY)
    c.text(right + 56, 502, 296, 18, "R02 e R01 restano nella stessa serie", design.Text.SECONDARY)
    c.rect(right + 16, 546, 350, 62, "card", "line_soft", design.Radius.CONTROL)
    c.text(right + 28, 556, 326, 20, "26042_connessione_R01.meridiana", design.Text.STRONG)
    c.text(right + 28, 580, 326, 18, "Progetto distinto, stessa commessa", design.Text.SECONDARY)
    c.label(right + 16, 634, 350, "Da fare")
    c.checkbox(right + 16, 662, "Controllare l'offerta di rete")
    c.text(right + 42, 684, 280, 16, "28/10 · attività personale su questo PC", design.Text.CAPTION)
    c.checkbox(right + 16, 716, "Inserire la curva del POD")
    c.text(right + 42, 738, 280, 16, "30/10 · collegata al progetto R03", design.Text.CAPTION)
    c.rect(right + 16, 788, 350, 104, "field", "", design.Radius.CONTROL)
    c.icon("shield-check", right + 28, 806, design.Icon.TILE, "good")
    c.text(right + 64, 800, 286, 76,
           "La commessa non è riservata. Per quelle riservate, il manifesto resta locale e Meridio non manda nemmeno l'esistenza al cloud.",
           design.Text.SECONDARY, wrap=True)


def roof_scene(c: Canvas, x, y, w, h):
    c.rect(x, y, w, h, "view", "line", design.Radius.VIEW)
    c.p.setPen(QPen(c.colour("line_soft"), 1))
    for i in range(1, 18):
        c.rule(x + i * w / 18, y, x + i * w / 18, y + h)
    for i in range(1, 12):
        c.rule(x, y + i * h / 12, x + w, y + i * h / 12)
    building = [QPointF(x + 130, y + 130), QPointF(x + w - 140, y + 86),
                QPointF(x + w - 90, y + h - 150), QPointF(x + 170, y + h - 96)]
    c.p.setBrush(c.colour("field"))
    c.p.setPen(QPen(c.colour("text2"), 2))
    c.p.drawPolygon(QPolygonF(building))
    for row in range(5):
        for col in range(8):
            xx = x + 196 + col * 68 + row * 8
            yy = y + 150 + row * 54 - col * 3
            c.p.setBrush(c.colour("accent_soft"))
            c.p.setPen(QPen(c.colour("accent"), 1))
            c.p.drawRect(QRectF(xx, yy, 56, 34))
    c.rect(x + 16, y + 16, 292, 34, "panel", "line_soft", design.Radius.CONTROL)
    c.text(x + 28, y + 24, 270, 18, "Pianta · progetto dimostrativo inventato", design.Text.SECONDARY)
    c.rect(x + 16, y + h - 52, w - 32, 38, "panel", "line_soft", design.Radius.CONTROL)
    c.text(x + 28, y + h - 43, w - 56, 20,
           "Ortofoto 2012 · 0,5 m/pixel · non è un rilievo", design.Text.SECONDARY)


def meridio_face(c: Canvas, x, y):
    c.p.setPen(QPen(c.colour("assistant"), 2))
    for i in range(8):
        import math
        angle = math.radians(i * 45)
        c.rule(x + 23 + math.cos(angle) * 29, y + 23 + math.sin(angle) * 29,
               x + 23 + math.cos(angle) * 35, y + 23 + math.sin(angle) * 35, "assistant", 2)
    c.p.setBrush(c.colour("assistant"))
    c.p.drawEllipse(QRectF(x, y, 46, 46))
    c.p.setBrush(c.colour("text"))
    c.p.drawEllipse(QRectF(x + 12, y + 17, 4, 5))
    c.p.drawEllipse(QRectF(x + 29, y + 17, 4, 5))
    c.p.setPen(QPen(c.colour("text"), 1.5))
    c.p.drawArc(QRectF(x + 15, y + 22, 16, 12), 200 * 16, 140 * 16)


def result_card(c: Canvas, x, y, w, code, name, file, facts, why, primary=False):
    c.rect(x, y, w, 142 if primary else 96, "card", "accent" if primary else "line_soft",
           design.Radius.CONTROL, design.Line.FOCUS if primary else design.Line.HAIR)
    c.text(x + 12, y + 10, w - 24, 20, f"{code} - {name}", design.Text.STRONG)
    c.text(x + 12, y + 34, w - 24, 18, file, design.Text.SECONDARY)
    c.text(x + 12, y + 56, w - 24, 18, facts, design.Text.SECONDARY)
    if primary:
        c.text(x + 12, y + 78, w - 24, 34, why, design.Text.SECONDARY, wrap=True)
        c.button(x + 12, y + 108, 116, "Apri", True, "folder-open")
        c.button(x + 136, y + 108, 168, "Mostra la commessa")
        c.pill(x + w - 126, y + 10, 114, "Più simile", True)


def meridio(c: Canvas):
    app_frame(c, False, 0)
    c.card(12, 58, 214, 866, "Progetto", "folder-open")
    c.label(28, 104, 180, "Sito")
    c.text(28, 130, 180, 22, "Capannone Alfa", design.Text.STRONG)
    c.text(28, 158, 180, 54, "Commessa 26042\nCliente Azienda Alfa\nProgetto non riservato", design.Text.SECONDARY, wrap=True)
    c.label(28, 240, 180, "Edifici")
    c.text(28, 268, 180, 22, "1  Corpo principale", design.Text.BODY)
    c.label(28, 320, 180, "Sottocampi")
    c.text(28, 348, 180, 22, "1  Falda sud", design.Text.BODY)
    c.card(234, 58, 876, 866, "Modello", "building")
    roof_scene(c, 246, 104, 852, 690)
    c.card(246, 806, 852, 104, "Verifiche", "shield-check")
    c.icon("check", 264, 836, design.Icon.LIST, "good")
    c.text(292, 830, 650, 22, "Nessun errore bloccante nel progetto dimostrativo", design.Text.STRONG)
    c.text(292, 858, 650, 20, "Il disegno e i dati sono inventati per questo bozzetto.", design.Text.SECONDARY)
    c.card(1118, 58, 470, 866, "Meridio", "sparkles")
    c.pill(1134, 102, 286, "Locale · ricerca solo su questo PC", True)
    c.icon("lock-keyhole", 1434, 106, design.Icon.CONTROL)
    c.text(1134, 142, 420, 44,
           "L'indice non va al cloud. Nomi, percorsi e commesse riservate non escono dal PC.",
           design.Text.SECONDARY, wrap=True)
    c.rect(1134, 202, 404, 62, "field", "", design.Radius.CONTROL)
    c.text(1148, 214, 376, 38, "Trovami l'ultimo capannone simile", design.Text.BODY, wrap=True)
    meridio_face(c, 1136, 282)
    c.text(1194, 286, 330, 60,
           "Ho trovato tre capannoni. Il più recente tra quelli davvero simili è questo.",
           design.Text.BODY, wrap=True)
    c.label(1134, 360, 390, "Risultati dall'indice locale")
    result_card(c, 1134, 386, 420, "26018", "Capannone Beta", "26018_fotovoltaico_R04.meridiana",
                "96 kWp · copertura · 12 km · 22/10/2026",
                "Stesso tipo, potenza vicina, stessa falda. Ultima revisione della serie.", True)
    result_card(c, 1134, 536, 420, "25987", "Polo logistico Alfa", "25987_fotovoltaico_R02.meridiana",
                "142 kWp · copertura · 18 km · 03/10/2026", "")
    result_card(c, 1134, 640, 420, "26102", "Polo Delta", "26102_fotovoltaico_R01.meridiana",
                "310 kWp · copertura · 46 km · 19/10/2026", "")
    c.rect(1134, 752, 420, 70, "field", "", design.Radius.CONTROL)
    c.icon("info", 1146, 768, design.Icon.CONTROL)
    c.text(1174, 762, 366, 50,
           "«Apri» mostra prima il percorso. Se il lavoro in mano non è salvato, Meridiana chiede che cosa farne.",
           design.Text.SECONDARY, wrap=True)
    c.field(1134, 840, 334, "Chiedi a Meridio", "Un nome, una commessa o un tipo di progetto")
    c.button(1476, 858, 78, "Invia", False, "arrow-right")


def render(name: str, draw, tokens: dict):
    image = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    canvas = Canvas(image, tokens)
    draw(canvas)
    canvas.end()
    path = OUT / name
    if not image.save(str(path), "PNG"):
        raise RuntimeError(f"Cannot write {path}")
    print(f"{path.relative_to(ROOT)}: {image.width()}x{image.height()}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([sys.argv[0], "-platform", "offscreen"])
    for name in ("Inter-Regular.ttf", "Inter-SemiBold.ttf"):
        if QFontDatabase.addApplicationFont(str(ROOT / "data" / "fonts" / "inter" / name)) < 0:
            raise RuntimeError(f"Cannot load {name}")
    if not QFont("Inter").exactMatch():
        raise RuntimeError("Inter is not available")
    tokens = theme_colors.derive(theme_colors.DEFAULT_SEED, False, "meridiana").tokens
    for name, draw in (("01-nuovo-progetto.png", new_project),
                       ("02-clienti-commesse.png", registry),
                       ("03-meridio-capannone-simile.png", meridio)):
        render(name, draw, tokens)
    app.processEvents()


if __name__ == "__main__":
    main()
