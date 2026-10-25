"""Prova per lo studio 16, tema F: quanto costano gli indicatori di attesa in Qt, nella configurazione di
Meridiana (Qt Widgets, pianta in QGraphicsView con molti oggetti, 3D in un QQuickWidget), offscreen.

Che cosa prova:
1. un indicatore «sta lavorando» disegnato sopra la pianta (un widget figlio del viewport con un arco che
   gira a 60 Hz): il costo di un suo fotogramma, e se ridisegna anche la pianta sotto (si contano i paint
   del viewport);
2. lo stesso con QProgressBar in modo «occupato» (minimo e massimo a 0) nella barra di stato;
3. un segnaposto a scheletro al posto di una pagina di proprietà: il costo di disegnare il segnaposto contro
   quello di costruire la pagina vera, e il costo di una fotografia della pagina (QWidget.grab) da mostrare
   mentre la si ricostruisce;
4. la prima accensione di un QQuickWidget con una scena Qt Quick 3D, che è l'attesa all'avvio misurata nello
   studio 12.

Lancio, dalla radice del repository:
    QT_QPA_PLATFORM=offscreen python docs/studio/16-prove/attese.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QRectF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPen  # noqa: E402
from PySide6.QtWidgets import (QApplication, QFormLayout, QGraphicsScene, QGraphicsView, QGroupBox,  # noqa: E402
                               QLabel, QProgressBar, QSpinBox, QStatusBar, QVBoxLayout, QWidget)


class Spinner(QWidget):
    """An arc that turns, 48 px, over the widget it is given; transparent around it."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.angle = 0
        self.paints = 0
        self.cost = []
        self.timer = QTimer(self, interval=16)
        self.timer.timeout.connect(self._tick)

    def _tick(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, _event):
        t = time.perf_counter()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(4, 4, -4, -4)
        p.setPen(QPen(QColor("#888"), 3))
        p.drawEllipse(r)
        p.setPen(QPen(QColor("#1f3352"), 4))
        p.drawArc(r, self.angle * 16, 90 * 16)
        p.end()
        self.paints += 1
        self.cost.append(time.perf_counter() - t)


class CountingView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.viewport_paints = 0
        self.viewport_cost = []

    def paintEvent(self, event):
        t = time.perf_counter()
        super().paintEvent(event)
        self.viewport_paints += 1
        self.viewport_cost.append(time.perf_counter() - t)


def spin(app, widget, ms: int):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        app.processEvents()


def ms(values) -> str:
    if not values:
        return "nessuno"
    values = sorted(values)
    return f"mediana {values[len(values) // 2] * 1000:.2f} ms, massimo {values[-1] * 1000:.2f} ms"


def skeleton_page() -> QWidget:
    """Grey bars where the fields of a properties page will be."""
    w = QWidget()
    box = QVBoxLayout(w)
    for _g in range(3):
        group = QGroupBox(" ")
        form = QFormLayout(group)
        for _i in range(6):
            bar = QLabel()
            bar.setFixedHeight(18)
            bar.setStyleSheet("background: #d8d8d8; border-radius: 4px;")
            name = QLabel()
            name.setFixedSize(80, 18)
            name.setStyleSheet("background: #e4e4e4; border-radius: 4px;")
            form.addRow(name, bar)
        box.addWidget(group)
    return w


def real_page() -> QWidget:
    w = QWidget()
    box = QVBoxLayout(w)
    for g in range(3):
        group = QGroupBox(f"Gruppo {g + 1}")
        form = QFormLayout(group)
        for i in range(6):
            s = QSpinBox()
            s.setRange(0, 10000)
            s.setValue(i)
            s.setSuffix(" m")
            form.addRow(f"Campo {i + 1}", s)
        box.addWidget(group)
    return w


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. a spinner over a plan with 5.000 modules
    scene = QGraphicsScene()
    for i in range(5000):
        x, y = (i % 100) * 12, (i // 100) * 24
        scene.addRect(QRectF(x, y, 11, 23), QPen(QColor("#1f3352")), QColor("#2a4a7a"))
    view = CountingView(scene)
    view.resize(1200, 800)
    view.show()
    spin(app, view, 200)
    view.viewport_paints, view.viewport_cost = 0, []
    spinner = Spinner(view.viewport())
    spinner.setGeometry(view.viewport().width() - 64, 16, 48, 48)
    spinner.show()
    spinner.timer.start()
    spin(app, view, 1000)
    spinner.timer.stop()
    print(f"1. arco sopra la pianta, 1 s: {spinner.paints} fotogrammi dell'arco ({ms(spinner.cost)} ciascuno); "
          f"la pianta sotto si è ridisegnata {view.viewport_paints} volte ({ms(view.viewport_cost)})")

    # 2. a busy QProgressBar in a status bar
    bar_host = QWidget()
    bar_host.resize(1200, 60)
    status = QStatusBar(bar_host)
    status.resize(1200, 24)
    progress = QProgressBar()
    progress.setRange(0, 0)
    progress.setFixedWidth(160)
    status.addPermanentWidget(progress)
    bar_host.show()
    paints = []
    original = progress.paintEvent

    def counted(event):
        t = time.perf_counter()
        original(event)
        paints.append(time.perf_counter() - t)
    progress.paintEvent = counted
    spin(app, bar_host, 1000)
    print(f"2. QProgressBar occupata nella barra di stato, 1 s: {len(paints)} ridisegni ({ms(paints)})")

    # 3. skeleton vs real page, and a snapshot of the real page
    t = time.perf_counter()
    sk = skeleton_page()
    sk.resize(360, 600)
    sk.show()
    spin(app, sk, 50)
    t_sk = time.perf_counter() - t
    t = time.perf_counter()
    page = real_page()
    page.resize(360, 600)
    page.show()
    spin(app, page, 50)
    t_page = time.perf_counter() - t
    t = time.perf_counter()
    shot = page.grab()
    t_grab = time.perf_counter() - t
    print(f"3. segnaposto a scheletro: costruito e mostrato in {t_sk * 1000:.0f} ms (compresi 50 ms di attesa); "
          f"pagina vera con 18 campi: {t_page * 1000:.0f} ms; fotografia della pagina (grab, "
          f"{shot.width()}x{shot.height()}): {t_grab * 1000:.1f} ms")

    # 4. the first QQuickWidget with a 3D scene
    from PySide6.QtCore import QUrl
    from PySide6.QtQuickWidgets import QQuickWidget
    qml = Path(__file__).with_name("attese_scena.qml")
    qml.write_text("import QtQuick\nimport QtQuick3D\nItem { View3D { anchors.fill: parent; PerspectiveCamera { z: 300 }"
                   " DirectionalLight {} Model { source: \"#Cube\"; materials: PrincipledMaterial {} } } }\n")
    t = time.perf_counter()
    q = QQuickWidget()
    q.setSource(QUrl.fromLocalFile(str(qml)))
    t_source = time.perf_counter() - t
    q.resize(800, 600)
    q.show()
    spin(app, q, 100)
    t_show = time.perf_counter() - t
    qml.unlink()
    print(f"4. QQuickWidget con una scena 3D: setSource {t_source * 1000:.0f} ms, mostrato dopo {t_show * 1000:.0f} ms "
          "(offscreen, senza GPU: sul PC lo studio 12 misura circa 1 s)")
    print(f"   {math.ceil(t_show * 1000 / 16)} fotogrammi a 60 Hz: tempo in cui un segnaposto della 3D sarebbe visibile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
