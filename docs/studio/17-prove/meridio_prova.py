"""Prova per lo studio 17, tema G: quanto costa animare Meridio in Qt Widgets (PySide6 6.12, offscreen).

1. respiro: la pixmap in cache (ui/assistant.picture) disegnata scalata tra 1,00 e 1,04 con QPainter, ms a fotogramma;
2. sguardo: nove pixmap pre-disegnate dall'SVG con gli occhi spostati di -1, 0, +1 px, costo del rendering una volta
   e del disegno a fotogramma;
3. «pensa»: la pixmap con gli occhi in su e i tre puntini, alternata a quella ferma;
4. per confronto, l'SVG reso di nuovo a ogni fotogramma (senza cache);
5. l'apertura della chat: un QFrame di 320 x 400 px con la conversazione, QPropertyAnimation sulla geometria (220 ms)
   e QGraphicsOpacityEffect sull'opacità, contati i fotogrammi disegnati offscreen e i ms per fotogramma.

Lancio:
    QT_QPA_PLATFORM=offscreen python docs/studio/17-prove/meridio_prova.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QByteArray, QEasingCurve, QPropertyAnimation, QRect, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsOpacityEffect, QLabel, QLineEdit, QPushButton,  # noqa: E402
                               QTextBrowser, QVBoxLayout, QWidget)

from meridiana import assistant, theme_colors as tc  # noqa: E402
from meridiana.ui.assistant import picture  # noqa: E402

OUT = Path(__file__).resolve().parent
SIZE = 46
FRAMES = 60


def timed(fn, n: int = FRAMES) -> float:
    t = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t) * 1000 / n


def eyes_svg(text: str, colour: str, dx: float, dy: float) -> str:
    """Meridio's SVG with the eyes moved by (dx, dy) in the 24-unit grid: the gaze."""
    s = assistant.svg(text, colour)
    return (s.replace('cx="10.1" cy="9.5"', f'cx="{10.1 + dx:g}" cy="{9.5 + dy:g}"')
             .replace('cx="13.9" cy="9.5"', f'cx="{13.9 + dx:g}" cy="{9.5 + dy:g}"'))


def render(svg: str, size: int) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    r = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, size, size))
    p.end()
    return pix


class Face(QWidget):
    """The closed character: the circle and the cached pixmap, scaled by `scale` (the breath)."""

    def __init__(self, t: dict):
        super().__init__()
        self.t = t
        self.setFixedSize(SIZE, SIZE)
        self.scale = 1.0
        self.pix = picture(t["text"], t["assistant"], int(SIZE * 0.74))
        self.gaze = {(dx, dy): render(eyes_svg(t["text"], t["assistant"], dx * 0.5, dy * 0.5), int(SIZE * 0.74))
                     for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        self.look = (0, 0)
        self.uncached = False

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setPen(QPen(QColor(self.t["line"]), 1.0))
        p.setBrush(QColor(self.t["panel"]))
        p.drawEllipse(QRectF(0.5, 0.5, SIZE - 1, SIZE - 1))
        inner = int(SIZE * 0.74)
        if self.uncached:
            pix = render(eyes_svg(self.t["text"], self.t["assistant"], 0, 0), inner)
        else:
            pix = self.gaze[self.look]
        side = inner * self.scale
        off = (SIZE - side) / 2
        p.drawPixmap(QRectF(off, off, side, side), pix, QRectF(0, 0, inner, inner))


def chat(t: dict) -> QFrame:
    f = QFrame()
    f.setStyleSheet(f"QFrame {{ background: {t['panel']}; border: 1px solid {t['line']}; border-radius: 8px; }}")
    box = QVBoxLayout(f)
    head = QLabel("Meridio")
    view = QTextBrowser()
    view.setHtml("<p>Che ne pensi di questa disposizione?</p><p>Buona: 156 moduli complanari a sud, 19° di falda. "
                 "Tre moduli finiscono nell'ombra del camino tra le 10 e le 14 del 21 dicembre.</p>")
    box.addWidget(head)
    box.addWidget(view, 1)
    for q in ("Le distanze dai bordi vanno bene per i Vigili del Fuoco?", "Dove recupero potenza senza ombre?",
              "Quante stringhe servono con questo inverter?"):
        box.addWidget(QPushButton("› " + q))
    box.addWidget(QLineEdit("Chiedi a Meridio… (Ctrl+L)"))
    return f


def measure(app, dark: bool) -> str:
    t = tc.derive(tc.DEFAULT_SEED, dark, "meridiana").tokens
    name = "scuro" if dark else "chiaro"
    face = Face(t)
    face.show()
    face.grab()
    # 1. the breath: the cached pixmap drawn scaled
    k = [0]

    def breath():
        k[0] += 1
        face.scale = 1.0 + 0.04 * ((k[0] % 20) / 20)
        face.grab()
    breath_ms = timed(breath)
    face.scale = 1.0
    # 2. the gaze: nine cached pixmaps
    t0 = time.perf_counter()
    gaze_pix = {(dx, dy): render(eyes_svg(t["text"], t["assistant"], dx * 0.5, dy * 0.5), int(SIZE * 0.74))
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    gaze_render_ms = (time.perf_counter() - t0) * 1000
    looks = list(gaze_pix)

    def gaze():
        k[0] += 1
        face.look = looks[k[0] % 9]
        face.grab()
    gaze_ms = timed(gaze)
    face.look = (0, 0)
    # 3. thinking: the two pixmaps alternated
    think = picture(t["text"], t["assistant"], int(SIZE * 0.74), True)

    def thinking():
        k[0] += 1
        face.gaze[(0, 0)] = think if k[0] % 2 else face.pix
        face.grab()
    think_ms = timed(thinking)
    face.gaze[(0, 0)] = face.pix
    # 4. the SVG rendered again at every frame, for comparison
    face.uncached = True
    uncached_ms = timed(lambda: face.grab())
    face.uncached = False
    face.grab().save(str(OUT / f"meridio_prova_{name}_chiuso.png"))
    # 5. the chat opening: geometry and opacity animated, 220 ms
    stage = QWidget()
    stage.resize(600, 500)
    stage.setStyleSheet(f"background: {t['window']}")
    stage.show()
    panel = chat(t)
    panel.setParent(stage)
    effect = QGraphicsOpacityEffect(panel)
    panel.setGraphicsEffect(effect)
    geom = QPropertyAnimation(panel, b"geometry")
    geom.setDuration(220)
    geom.setEasingCurve(QEasingCurve.Type.OutCubic)
    geom.setStartValue(QRect(560, 460, 46, 46))
    geom.setEndValue(QRect(268, 88, 320, 400))
    fade = QPropertyAnimation(effect, b"opacity")
    fade.setDuration(220)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    panel.show()
    frames = [0]
    costs = []

    def frame():
        frames[0] += 1
        t1 = time.perf_counter()
        stage.grab()
        costs.append((time.perf_counter() - t1) * 1000)
    geom.valueChanged.connect(lambda _v: frame())
    t0 = time.perf_counter()
    geom.start()
    fade.start()
    while geom.state() == QPropertyAnimation.State.Running:
        app.processEvents()
    open_ms = (time.perf_counter() - t0) * 1000
    panel.setGraphicsEffect(None)
    stage.grab().save(str(OUT / f"meridio_prova_{name}_aperto.png"))
    plain_ms = timed(lambda: stage.grab(), 20)
    return (f"tema {name}: respiro {breath_ms:.2f} ms/fotogramma, sguardo {gaze_ms:.2f} ms/fotogramma "
                 f"(nove pixmap disegnate una volta in {gaze_render_ms:.1f} ms), pensa {think_ms:.2f} ms/fotogramma, "
                 f"SVG reso a ogni fotogramma {uncached_ms:.2f} ms; apertura della chat {open_ms:.0f} ms per "
                 f"{frames[0]} fotogrammi, {sum(costs) / max(1, len(costs)):.1f} ms di disegno a fotogramma con "
                 f"l'opacità (QGraphicsOpacityEffect), {plain_ms:.1f} ms senza")


def main() -> None:
    app = QApplication(sys.argv)
    lines = [measure(app, dark) for dark in (False, True)]
    print(f"Meridio di {SIZE} px, {FRAMES} fotogrammi per misura, offscreen, PySide6 6.12")
    for line in lines:
        print(line)
    print("Il personaggio a 20 fotogrammi al secondo costa respiro x 20 ms al secondo di CPU del thread della finestra; "
          "con «meno movimento» non si anima e costa 0.")


if __name__ == "__main__":
    main()
