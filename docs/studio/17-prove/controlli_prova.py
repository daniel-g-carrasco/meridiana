"""Prova per lo studio 17, temi A, C ed E: quello che i bozzetti propongono si fa con Fusion e un foglio di stile?
E quanto costa? Offscreen, con i colori veri di theme_colors (bronzo), in chiaro e in scuro.

Che cosa prova:
1. tre livelli di superficie (finestra, pannelli, viste) e le intestazioni dei pannelli con QDockWidget::title,
   in una finestra con i pannelli veri (QMainWindow, due dock, una vista centrale);
2. i pulsanti nei tre stili (C1 Fusion ritoccato, C2 tonale alla GNOME, C3 contorni) e i campi con fondo e bordo,
   i gruppi come schede (QGroupBox con fondo, bordo e angoli) o con intestazione piena; i contrasti misurati
   con theme_colors.contrast (WCAG 1.4.11 chiede 3:1 per i bordi dei controlli);
3. il «?» accanto a un titolo con il riquadro d'aiuto (QToolButton e un QFrame a comparsa) e una frase sotto
   il campo;
4. il costo: applicare il foglio di stile a una finestra con circa 300 widget (il polish), misurato.

Le schermate finiscono accanto allo script (controlli_prova_*.png).

Lancio: QT_QPA_PLATFORM=offscreen python docs/studio/17-prove/controlli_prova.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDockWidget, QDoubleSpinBox, QFormLayout,  # noqa: E402
                               QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton,
                               QScrollArea, QStyleFactory, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

from meridiana import theme_colors as tc  # noqa: E402
from meridiana.ui.theme import qpalette  # noqa: E402

OUT = Path(__file__).resolve().parent


def tokens(dark: bool) -> dict:
    return tc.derive(tc.DEFAULT_SEED, dark, "meridiana").tokens


def alpha(hex_: str, a: float) -> str:
    """Un colore con trasparenza, nell'ordine di Qt (#aarrggbb)."""
    return f"#{int(a * 255):02x}{hex_.lstrip('#')[:6]}"


def sheet(t: dict, dark: bool, style: str, surfaces: str) -> str:
    """Il foglio di stile della prova: `style` C1, C2 o C3; `surfaces` A1 (tre livelli), A2 (un livello e
    intestazioni piene) o A3 (schede)."""
    sink = alpha("#000000" if dark else t["text"], 0.22 if dark else 0.06)
    raise_ = alpha("#ffffff", 0.045 if dark else 0.9)
    focus = alpha(t["accent"], 0.25)
    css = f"""
QMainWindow, QMenuBar, QToolBar, QStatusBar {{ background: {t['window']}; }}
QDockWidget {{ background: {t['panel']}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {t['panel']}; }}
QTreeWidget {{ background: {t['panel']}; border: none; }}
"""
    if surfaces == "A1":
        css += f"""
QDockWidget::title {{ background: {t['panel']}; color: {t['muted']}; padding: 7px 10px; border-bottom: 1px solid {t['line']};
                      font-size: 11px; text-transform: uppercase; }}
QMainWindow::separator {{ background: {t['line']}; width: 1px; height: 1px; }}
"""
    elif surfaces == "A2":
        css += f"""
QDockWidget {{ background: {t['window']}; }}
QScrollArea, QScrollArea > QWidget > QWidget, QTreeWidget {{ background: {t['window']}; }}
QDockWidget::title {{ background: {t['line_soft']}; color: {t['text']}; padding: 6px 10px; border-bottom: 1px solid {t['line']}; }}
QMainWindow::separator {{ background: {t['line']}; width: 1px; height: 1px; }}
"""
    else:
        css += f"""
QDockWidget {{ background: {t['window']}; }}
QDockWidget > QWidget {{ background: {t['panel']}; border: 1px solid {t['line_soft']}; border-radius: 8px; }}
QDockWidget::title {{ background: transparent; color: {t['text']}; padding: 8px 12px 4px; }}
QMainWindow::separator {{ background: {t['window']}; width: 8px; height: 8px; }}
"""
    if style == "C1":
        css += f"""
QPushButton {{ background: {raise_}; border: 1px solid {t['line']}; border-radius: 5px; padding: 4px 12px; color: {t['text']}; }}
QPushButton[primary="true"] {{ background: {t['accent']}; color: {t['accent_fg']}; border-color: {t['accent']}; font-weight: 600; }}
QLineEdit, QDoubleSpinBox, QComboBox {{ background: {t['view']}; border: 1px solid {t['line']}; border-radius: 4px; padding: 2px 6px; color: {t['text']}; }}
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {t['accent']}; }}
QGroupBox {{ border: none; border-top: 1px solid {t['line']}; margin-top: 18px; padding-top: 6px; font-weight: 600; color: {t['text2']}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 0; top: 2px; padding: 0 2px; }}
"""
    elif style == "C2":
        css += f"""
QPushButton {{ background: {sink}; border: 1px solid transparent; border-radius: 6px; padding: 4px 12px; color: {t['text']}; font-weight: 600; }}
QPushButton:hover {{ background: {alpha('#ffffff' if dark else t['text'], 0.09)}; }}
QPushButton[primary="true"] {{ background: {t['accent']}; color: {t['accent_fg']}; }}
QLineEdit, QDoubleSpinBox, QComboBox {{ background: {sink}; border: 1px solid transparent; border-radius: 5px; padding: 2px 6px; color: {t['text']}; }}
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {t['accent']}; background: {t['view']}; }}
QGroupBox {{ background: {t['card']}; border: 1px solid {t['line_soft']}; border-radius: 8px; margin-top: 12px; padding: 14px 8px 8px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; top: 4px; padding: 0 4px; background: {t['card']}; color: {t['text']}; }}
"""
    else:
        css += f"""
QPushButton {{ background: transparent; border: 1.5px solid {t['text2']}; border-radius: 5px; padding: 4px 12px; color: {t['text']}; font-weight: 600; }}
QPushButton[primary="true"] {{ background: {t['accent']}; color: {t['accent_fg']}; border-color: {t['accent']}; }}
QLineEdit, QDoubleSpinBox, QComboBox {{ background: {t['view']}; border: 1.5px solid {t['text2']}; border-radius: 3px; padding: 2px 6px; color: {t['text']}; }}
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {t['accent']}; }}
QGroupBox {{ border: 1px solid {t['line']}; border-radius: 4px; margin-top: 14px; padding-top: 10px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 0; padding: 3px 8px; background: {t['line_soft']}; color: {t['text']}; }}
"""
    css += f"""
QLabel[hint="true"] {{ color: {t['muted']}; font-size: 11px; }}
QToolButton[help="true"] {{ border: none; color: {t['muted']}; font-weight: 700; padding: 0 3px; }}
QFrame[pop="true"] {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px; }}
QLabel[focusring="true"] {{ border: 2px solid {focus}; border-radius: 6px; }}
"""
    return css


def properties_page(style: str, help_: bool) -> QWidget:
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(8, 6, 8, 6)
    groups = [("Sottocampo", [("Nome", "line", "Copertura Sud"), ("Montaggio", "combo", "Complanare alla falda"),
                              ("Orientamento", "combo", "Verticale"), ("Moduli per tavola, di traverso", "spin", 1)]),
              ("Distanze e margini", [("Tra i moduli", "spin", 0.02), ("Dal bordo dell'area", "spin", 0.5), ("Tra le file", "spin", 0.05),
                                      ("Fuori dalle ombre", "check", True)])]
    for title, fields in groups:
        g = QGroupBox(title)
        form = QFormLayout(g)
        form.setVerticalSpacing(6)
        if help_:
            head = QHBoxLayout()
            head.addWidget(QLabel("Che cosa sono"))
            h = QToolButton()
            h.setText("?")
            h.setProperty("help", True)
            h.setToolTip("Le distanze che la posa rispetta: tra i moduli, dal bordo, tra le file.")
            head.addWidget(h)
            head.addStretch(1)
            form.addRow(head)
        for label, kind, value in fields:
            if kind == "line":
                w = QLineEdit(value)
            elif kind == "combo":
                w = QComboBox()
                w.addItems([value, "Altro"])
            elif kind == "spin":
                w = QDoubleSpinBox()
                w.setRange(0, 100)
                w.setValue(value)
                w.setSuffix(" m" if value < 1 else "")
            else:
                w = QCheckBox()
                w.setChecked(value)
            form.addRow(label, w)
            if help_ and label == "Dal bordo dell'area":
                hint = QLabel("Fascia libera lungo il contorno; con le regole VVF almeno 1 m.")
                hint.setProperty("hint", True)
                hint.setWordWrap(True)
                form.addRow(hint)
        box.addWidget(g)
    row = QHBoxLayout()
    b = QPushButton("Posa i moduli")
    b.setProperty("primary", True)
    row.addWidget(b)
    row.addWidget(QPushButton("Svuota"))
    row.addStretch(1)
    box.addLayout(row)
    if help_:
        pop = QFrame(page)
        pop.setProperty("pop", True)
        pl = QVBoxLayout(pop)
        pl.addWidget(QLabel("<b>Dal bordo dell'area</b><br>Fascia libera lungo il contorno dell'area, dove i moduli non vanno: per "
                            "la manutenzione e per le regole dei Vigili del Fuoco.<br><a href='#'>Manuale ›</a> · <a href='#'>Come è calcolato ›</a>"))
        pl.itemAt(0).widget().setWordWrap(True)
        pop.setFixedWidth(240)
        pop.move(30, 300)
        pop.raise_()
    box.addStretch(1)
    return page


def build(t: dict, dark: bool, style: str, surfaces: str, help_: bool) -> QMainWindow:
    win = QMainWindow()
    win.resize(1100, 640)
    win.menuBar().addMenu("File")
    win.menuBar().addMenu("Modifica")
    win.menuBar().addMenu("Disegna")
    win.menuBar().addMenu("Vista")
    tb = win.addToolBar("Strumenti")
    for name in ("Seleziona", "Edificio", "Falda", "Sottocampo", "Esclusione", "Misura"):
        tb.addAction(name)
    centre = QLabel("pianta e 3D")
    centre.setAlignment(Qt.AlignmentFlag.AlignCenter)
    centre.setStyleSheet(f"background: {t['plan']['bg']}; color: {t['muted']};")
    win.setCentralWidget(centre)
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    root = QTreeWidgetItem(tree, ["Sito: Capannone Rho"])
    for name in ("Edificio 1", "Uffici", "Copertura Sud · 156", "Copertura Nord · 32", "Lucernario 1", "Camino 1"):
        QTreeWidgetItem(root, [name])
    tree.expandAll()
    left = QDockWidget("Progetto")
    left.setWidget(tree)
    win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left)
    right = QDockWidget("Proprietà")
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(properties_page(style, help_))
    scroll.setMinimumWidth(330)
    right.setWidget(scroll)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, right)
    bottom = QDockWidget("Verifiche")
    lst = QTreeWidget()
    lst.setHeaderLabels(["", "Che cosa", "Fonte"])
    QTreeWidgetItem(lst, ["✘", "Copertura Sud: 3 moduli nell'ombra del Camino 1", "DCPREV 14030/2025"])
    QTreeWidgetItem(lst, ["⚠", "Stringhe: 4 moduli non sono in nessuna stringa", "CEI 64-8/7:2024"])
    bottom.setWidget(lst)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, bottom)
    win.statusBar().showMessage("Sottocampo: disegna l'area dove possono andare i moduli.")
    return win


def count_widgets(w) -> int:
    return 1 + sum(count_widgets(c) for c in w.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly))


def contrasts(t: dict, dark: bool) -> list[str]:
    out = []
    pairs = [("campo C1: fondo vista su pannello", t["view"], t["panel"]), ("campo C1: bordo linea su pannello", t["line"], t["panel"]),
             ("campo C3: bordo testo2 su pannello", t["text2"], t["panel"]), ("pulsante primario: testo su accento", t["accent_fg"], t["accent"]),
             ("testo attenuato su pannello", t["muted"], t["panel"]), ("scheda C2: fondo card su pannello", t["card"], t["panel"]),
             ("scheda C2: bordo leggero su pannello", t["line_soft"], t["panel"]), ("finestra contro pannello (A1)", t["window"], t["panel"])]
    for name, a, b in pairs:
        out.append(f"  {name}: {tc.contrast(a, b):.2f}:1")
    # il velo tonale di C2 composto sul pannello
    base = QColor(t["panel"])
    veil = QColor("#000000" if dark else t["text"])
    k = 0.22 if dark else 0.06
    mixed = QColor(int(base.red() * (1 - k) + veil.red() * k), int(base.green() * (1 - k) + veil.green() * k), int(base.blue() * (1 - k) + veil.blue() * k))
    out.append(f"  campo C2: velo tonale ({mixed.name()}) su pannello: {tc.contrast(mixed.name(), t['panel']):.2f}:1")
    return out


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    folder = ROOT / "data" / "fonts" / "titillium-web"
    fid = QFontDatabase.addApplicationFont(str(folder / "TitilliumWeb-Regular.ttf"))
    fam = QFontDatabase.applicationFontFamilies(fid)
    if fam:
        app.setFont(QFont(fam[0], 10))
    for dark in (False, True):
        t = tokens(dark)
        app.setPalette(qpalette(tc.palette(t, dark)))
        print("tema", "scuro" if dark else "chiaro")
        for name in contrasts(t, dark):
            print(name)
        for style, surfaces in (("C1", "A1"), ("C2", "A3"), ("C3", "A2")):
            win = build(t, dark, style, surfaces, help_=style == "C2")
            win.show()
            app.processEvents()
            n = count_widgets(win)
            css = sheet(t, dark, style, surfaces)
            t0 = time.perf_counter()
            app.setStyleSheet(css)
            app.processEvents()
            polish = (time.perf_counter() - t0) * 1000
            t0 = time.perf_counter()
            img = win.grab()
            paint = (time.perf_counter() - t0) * 1000
            name = f"controlli_prova_{style}_{surfaces}_{'scuro' if dark else 'chiaro'}.png"
            img.save(str(OUT / name))
            print(f"  {style} + {surfaces}: {n} widget, foglio di stile applicato in {polish:.0f} ms, disegno {paint:.0f} ms, "
                  f"{len(css.splitlines())} regole -> {name}")
            app.setStyleSheet("")
            win.close()
            win.deleteLater()
            app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
