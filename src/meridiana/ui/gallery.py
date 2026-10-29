"""The gallery of the design system (Daniel, 24/10/2026: «l'obiettivo è avere un template facilmente riutilizzabile per
altri programmi»): every token, scale and component on one page, in the theme asked, as a program built on it would
show them. It is the check of the harmony (a measure off the scale shows here first) and the showcase of the
template (docs/design/sistema-grafico.md).

    python -m meridiana.ui.gallery [light|dark] [--shot file.png]

The sections: the colours (the theme's tokens), the catalogue of the texts (design.Text), the spacing and the
radii, the kinds of buttons (design.Button: push, primary, destructive, tools, chips, tabs and the segmented
control, the small ones of a row), fields and a group, the tiles and a strip, a list with sections and marks, a
page that scrolls with its soft end and its scroll bar, a view with its rounded corners and its bar, the cards."""

from __future__ import annotations

import sys

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QPainter
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateEdit, QDoubleSpinBox, QFormLayout, QFrame,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QScrollArea,
                               QTabBar, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import design
from .design import Layout, Radius, Size, Space, Text, set_text, text_font

TOKENS = ("window", "panel", "card", "view", "field", "line", "line_soft", "text", "text2", "muted", "accent",
          "accent_soft", "accent_fg", "select_bg", "select_fg", "danger", "tooltip_bg")


def card(title: str, body: QWidget | None = None) -> QFrame:
    """A card of the gallery: the panels' colour, its line, its title as a card's."""
    frame = QFrame()
    frame.setObjectName("card")
    frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    box = QVBoxLayout(frame)
    box.setContentsMargins(Layout.TITLE_X, Space.M + 1, Layout.TITLE_X, Space.L)
    box.setSpacing(Space.M)
    box.addWidget(set_text(QLabel(title), Text.TITLE))
    if body is not None:
        box.addWidget(body)
    box.addStretch(1)
    return frame


def row(*widgets, spacing: int = Space.M) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for x in widgets:
        lay.addWidget(x)
    lay.addStretch(1)
    return w


class Swatch(QWidget):
    def __init__(self, name: str, colour: str):
        super().__init__()
        self.name, self.colour = name, colour
        self.setFixedSize(132, 64)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(self.palette().color(self.foregroundRole())).darker(100))
        from .. import theme_colors
        p.setBrush(QColor(theme_colors.qt_hex(self.colour)))
        p.drawRoundedRect(1, 1, self.width() - 2, 32, Radius.MARK, Radius.MARK)       # a swatch (the rules)
        p.setFont(text_font(Text.SECONDARY))
        p.drawText(2, 46, self.name)
        p.setFont(text_font(Text.CAPTION))
        p.drawText(2, 60, self.colour)


class Boxes(QWidget):
    """The spacing scale as bars, the radii as rounded squares."""

    def __init__(self, tokens: dict):
        super().__init__()
        self.t = tokens
        self.setMinimumHeight(150)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(text_font(Text.CAPTION))
        x = 0
        for s in Space.SCALE[1:]:
            p.fillRect(x, 10, s, 40, QColor(self.t["accent"]))
            p.setPen(QColor(self.t["text2"]))
            p.drawText(x, 66, str(s))
            x += max(s, 18) + Space.L
        x = 0
        for name, r in ((f"card {Radius.CARD}", Radius.CARD), (f"view {Radius.VIEW}", Radius.VIEW),
                        (f"control {Radius.CONTROL}", Radius.CONTROL), (f"inner {Radius.INNER}", Radius.INNER),
                        (f"mark {Radius.MARK}", Radius.MARK), ("pill", Size.CHIP / 2)):
            p.setPen(QColor(self.t["line"]))
            p.setBrush(QColor(self.t["field"]))
            p.drawRoundedRect(x, 84, 64 if name != "pill" else 80, Size.CHIP if name == "pill" else 40, r, r)
            p.setPen(QColor(self.t["text2"]))
            p.drawText(x, 144, name)
            x += 96


def gallery(theme) -> QMainWindow:
    t = theme.tokens
    win = QMainWindow()
    win.setWindowTitle("Meridiana: sistema grafico")
    page = QWidget()
    grid = QGridLayout(page)
    grid.setContentsMargins(Layout.EDGE, Layout.GAP, Layout.EDGE, Layout.GAP)
    grid.setSpacing(Layout.GAP)

    # the colours
    colours = QWidget()
    cg = QGridLayout(colours)
    cg.setContentsMargins(0, 0, 0, 0)
    cg.setSpacing(Space.M)
    for i, name in enumerate(TOKENS):
        cg.addWidget(Swatch(name, t[name]), i // 9, i % 9)
    cg.setColumnStretch(9, 1)
    grid.addWidget(card("Colori (i gettoni del tema)", colours), 0, 0, 1, 2)

    # the type
    types = QWidget()
    tb = QVBoxLayout(types)
    tb.setContentsMargins(0, 0, 0, 0)
    tb.setSpacing(Space.XS)
    for style, words in ((Text.DISPLAY, "107.130 kWh"), (Text.HEADING, "Un titolo dentro la pagina"),
                         (Text.TITLE, "Progetto, Proprietà, Aiuto"),
                         (Text.STRONG, "Sito, Inverter 1, Calcola, la fase in mano"),
                         (Text.BODY, "Il testo: campi, elenchi, menu, aiuto"),
                         (Text.DESCRIPTION, "Una frase che spiega che cosa fa"),
                         (Text.CONTROL, "Mesi · Perdite · Questa fase · Base"),
                         (Text.SECONDARY, "Note, barra di stato, parole sotto gli strumenti"),
                         (Text.CAPTION, "Tacche dei grafici, formati, fonti"),
                         (Text.LABEL, "Sezioni, gruppi della barra")):
        weight = "semigrassetto" if style.weight == design.Type.SEMIBOLD else "normale"
        tb.addWidget(set_text(QLabel(f"{style.name} · {style.size} px {weight} · {words}"), style))
    grid.addWidget(card("Testo: il catalogo (design.Text)", types), 1, 0)
    grid.addWidget(card("Spaziature e raggi", Boxes(t)), 1, 1)

    # the controls
    controls = QWidget()
    cb = QVBoxLayout(controls)
    cb.setContentsMargins(0, 0, 0, 0)
    cb.setSpacing(Space.L)
    primary = QPushButton("Calcola")
    primary.setProperty("primary", True)
    danger = QPushButton("Togli i moduli")
    danger.setProperty("destructive", True)
    off = QPushButton("Non ora")
    off.setEnabled(False)
    cb.addWidget(row(QPushButton("Pulsante"), primary, danger, off))
    from . import icons
    tools = []
    for name, text, checked in (("select", "Seleziona", True), ("move", "Sposta", False), ("measure", "Misura", False)):
        b = QToolButton()
        b.setIcon(icons.icon(name))
        b.setIconSize(QSize(design.Icon.BAR, design.Icon.BAR))
        b.setText(text)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        b.setCheckable(True)
        b.setChecked(checked)
        tools.append(b)
    cb.addWidget(row(*tools, spacing=Space.XXS))
    states = []
    for name, text in (("state-done", "Fatto"), ("state-stale", "Da aggiornare"), ("state-todo", "Da fare"),
                       ("state-planned", "Previsto")):
        s = QLabel(text)
        s.setObjectName(name)
        states.append(s)
    for s in states:
        s.setFont(text_font(Text.CONTROL))
    cb.addWidget(row(*states))
    # the chips: filters and counts (Button.CHIP), as the Checks' head
    from .marks import icon as mark_icon
    chips = []
    for text, checked in (("Per livello", False), ("Questa fase", True), ("Questo oggetto", False)):
        c = QToolButton()
        c.setObjectName("filter")
        c.setText(text)
        c.setCheckable(True)
        c.setChecked(checked)
        chips.append(c)
    for level, n in (("fail", 0), ("warn", 1), ("info", 12)):
        c = QToolButton()
        c.setObjectName("count")
        c.setIcon(mark_icon(level))
        c.setText(str(n))
        c.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        chips.append(c)
    cb.addWidget(row(*chips, spacing=Space.XS))
    # the tabs and the segmented control: one look (R109, R121)
    tabs = QTabBar()
    tabs.setDrawBase(False)
    for text in ("Mesi", "Perdite", "Giorno tipo", "Come è calcolato"):
        tabs.addTab(text)
    from .variant_bar import VariantBar
    bar = VariantBar(QAction("Nuova", win), [])
    bar.set_variants([("a", "Base"), ("b", "Senza batteria"), ("c", "Inclinati 30°")], "a")
    cb.addWidget(row(tabs, bar, spacing=Space.L))
    # the small buttons of a row and of a title, the «?»
    fix = QToolButton()
    fix.setObjectName("rowfix")
    fix.setText("Correggi")
    from .help_box import HelpButton, RowHelpButton
    small = [fix]
    try:
        small.append(HelpButton("site"))
        small.append(RowHelpButton("site"))
    except ValueError:
        pass
    cb.addWidget(row(*small))
    grid.addWidget(card("Pulsanti: 28 px, pillole 24 px, piccoli 20 px", controls), 2, 0)

    # the fields and a group
    fields = QWidget()
    fb = QVBoxLayout(fields)
    fb.setContentsMargins(0, 0, 0, 0)
    fb.setSpacing(Space.L)
    from .style import Group, pad_fields
    group = Group("Distanze e margini")
    form = QFormLayout(group)
    form.setContentsMargins(Space.M, Space.M, Space.M, Space.M)
    form.setSpacing(Space.M)
    edit = QLineEdit("Copertura")
    spin = QDoubleSpinBox()
    spin.setSuffix(" m")
    spin.setValue(0.5)
    combo = QComboBox()
    combo.addItems(["Verticale", "Orizzontale"])
    date = QDateEdit()
    form.addRow("Nome", edit)
    form.addRow("Dal bordo", spin)
    form.addRow("Disposizione", combo)
    form.addRow("Giorno", date)
    form.addRow("", QCheckBox("Edificio pubblico (+10%)"))
    pad_fields(group)
    fb.addWidget(group)
    grid.addWidget(card("Campi e gruppi", fields), 2, 1)

    # the tiles and a strip
    tiles = QWidget()
    tg = QHBoxLayout(tiles)
    tg.setContentsMargins(0, 0, 0, 0)
    tg.setSpacing(Layout.GAP)
    from .energy_pages import Tile
    for key, (label, value, unit, note) in enumerate((("Energia all'anno", "107.130", "kWh", "anno tipo"),
                                                       ("Producibilità specifica", "1.151", "kWh/kWp", ""),
                                                       ("Indice di prestazione", "69,9", "%", "IEC 61724-1"))):
        tile = Tile(label, key == 0)
        tile.set(f"{value} {unit}", note)
        tile.setMinimumWidth(200)
        tg.addWidget(tile)
    strip = QFrame()
    strip.setObjectName("strip")
    sl = QHBoxLayout(strip)
    sl.setContentsMargins(Space.L, Space.M, Space.L, Space.M)
    sl.addWidget(QLabel("PVGIS 5.3, anno tipo 2005-2023"))
    sl.addStretch(1)
    sl.addWidget(QPushButton("Scarica"))
    box = QWidget()
    bl = QVBoxLayout(box)
    bl.setContentsMargins(0, 0, 0, 0)
    bl.setSpacing(Layout.GAP)
    bl.addWidget(tiles)
    bl.addWidget(strip)
    grid.addWidget(card("Riquadri e striscia", box), 3, 0, 1, 2)

    # a list with sections and a page that goes on: its soft end
    tree = QTreeWidget()
    tree.setObjectName("project-tree")
    tree.setHeaderHidden(True)
    tree.setRootIsDecorated(False)
    from .sections import SectionDelegate, section
    tree.setItemDelegate(SectionDelegate(tree, pills=True))
    for title, items in (("Edifici", ("Capannone", "Uffici")), ("Sottocampi", ("Copertura",)),
                         ("Esclusioni", ("Camino 1", "Albero 1", "Impianto in copertura 1"))):
        section(tree, title, len(items), columns=1)
        for it in items:
            QTreeWidgetItem(tree, [it])
    tree.setMinimumHeight(220)
    long_text = QLabel(" ".join(["Il sito dà latitudine e longitudine dell'origine del disegno: il sole, il meteo "
                                 "da PVGIS e le regole della regione partono da lì."] * 6))
    long_text.setWordWrap(True)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(long_text)
    scroll.setFixedHeight(120)
    from . import fades
    fades.set_colour(t["panel"])
    fades.attach(scroll)
    fades.attach(tree)
    lists = QWidget()
    ll = QHBoxLayout(lists)
    ll.setContentsMargins(0, 0, 0, 0)
    ll.setSpacing(Layout.GAP)
    ll.addWidget(tree, 1)
    ll.addWidget(scroll, 2)
    grid.addWidget(card("Elenco a sezioni e fine morbida di ciò che scorre", lists), 4, 0)

    # a view: its rounded corners and its bar
    view = QFrame()
    view.setStyleSheet("background: #7f9a6a;")
    view.setMinimumHeight(220)
    from .cards import round_corners, set_corner_colour
    set_corner_colour(t["panel"])
    round_corners(view)
    from .viewbar import ViewBar
    acts = [QAction(icons.icon(n), n, win) for n in ("plan", "3d", "both")]
    for a in acts:
        a.setCheckable(True)
    acts[2].setChecked(True)
    vb = ViewBar(view, [acts, [QAction(icons.icon("fit"), "Inquadra", win)]])
    vb.set_colours(t)
    QTimer.singleShot(0, lambda: vb.place(view.rect()))
    grid.addWidget(card("Vista: angoli arrotondati, barra a soli simboli", view), 4, 1)

    grid.setRowStretch(5, 1)
    outer = QScrollArea()
    outer.setWidgetResizable(True)
    outer.setWidget(page)
    win.setCentralWidget(outer)
    win.resize(1500, 1400)
    return win


def main(argv: list[str]) -> int:
    from .. import config
    from .theme import Theme
    app = QApplication.instance() or QApplication(argv)
    which = next((a for a in argv[1:] if a in ("light", "dark")), "light")
    theme = Theme(config.Config(theme=which, check_updates=False), app=app)
    theme.apply()
    win = gallery(theme)
    win.show()
    if "--shot" in argv:
        out = argv[argv.index("--shot") + 1]

        def shoot():
            win.grab().save(out)
            app.quit()
        QTimer.singleShot(1200, shoot)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
