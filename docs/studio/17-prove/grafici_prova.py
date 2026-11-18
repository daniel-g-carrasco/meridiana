"""Prova per lo studio 17, tema D: quanto costano i grafici interattivi in Qt, su un anno di valori orari (8.760
punti) e sul grafico mensile, con le strade possibili nella configurazione di Meridiana (PySide6 6.12, offscreen):

1. matplotlib con il canvas QtAgg di oggi: disegno intero, risposta al passaggio del mouse con il ridisegno, e con
   il blitting (si ridisegna solo l'annotazione);
2. pyqtgraph (MIT, da proporre): disegno, mirino al passaggio, zoom; con e senza antialiasing;
3. Qt Charts (nel pacchetto, deprecato dalla 6.10): QChartView con 8.760 punti e il segnale hovered;
4. Qt Graphs 2D (nel pacchetto, solo QML, dentro un QQuickWidget): disegno; offscreen senza GPU non si disegna
   (come la vista 3D), quindi qui si misura solo il costo di caricamento;
5. una vista web (QtWebEngine, nel pacchetto PySide6 ma 111-126 MiB di ruota): un grafico SVG scritto a mano,
   e il tempo del primo disegno; offscreen il processo del browser può non partire: la prova lo dice.

Lancio (pyqtgraph solo se installato; il resto è nel pacchetto):
    QT_QPA_PLATFORM=offscreen python docs/studio/17-prove/grafici_prova.py
"""

from __future__ import annotations

import gc
import os
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

HOURS = 8760
OUT = Path(__file__).resolve().parent


def year() -> np.ndarray:
    import parti
    return np.array(parti.synthetic_year(), dtype=float)


def rss_mb() -> float:
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return float("nan")


def spin(app, ms=50):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        app.processEvents()


def timed(fn, repeat=5):
    best = float("inf")
    for _i in range(repeat):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best * 1000


def report(name: str, **values) -> None:
    print(f"{name:34s} " + "  ".join(f"{k} {v}" for k, v in values.items()))


# ------------------------------------------------------------------ 1. matplotlib

def prova_matplotlib(app, data):
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    r0 = rss_mb()
    fig = Figure(figsize=(6, 3), dpi=100, layout="constrained")
    canvas = FigureCanvasQTAgg(fig)
    canvas.resize(600, 300)
    canvas.show()
    ax = fig.add_subplot()
    xs = np.arange(HOURS)
    t = time.perf_counter()
    line, = ax.plot(xs, data, linewidth=0.6)
    ax.plot(xs, np.minimum(data, 6 + 4 * np.sin(xs / 24 * np.pi)), linewidth=0.6)
    ax.set_xlim(0, HOURS)
    canvas.draw()
    first = (time.perf_counter() - t) * 1000
    redraw = timed(canvas.draw)
    # hover with a full redraw: an annotation moved and the canvas drawn again
    ann = ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points", bbox={"boxstyle": "round", "fc": "w"})
    ann.set_visible(True)
    step = [0]

    def hover_full():
        i = step[0] = (step[0] + 97) % HOURS
        ann.xy = (i, data[i])
        ann.set_text(f"{i} h: {data[i]:.1f} kW")
        canvas.draw()
    hover1 = timed(hover_full, 10)
    # hover with blitting: the background kept, only the annotation drawn
    ann.set_animated(True)
    canvas.draw()
    background = canvas.copy_from_bbox(fig.bbox)

    def hover_blit():
        i = step[0] = (step[0] + 97) % HOURS
        ann.xy = (i, data[i])
        ann.set_text(f"{i} h: {data[i]:.1f} kW")
        canvas.restore_region(background)
        ax.draw_artist(ann)
        canvas.blit(fig.bbox)
    hover2 = timed(hover_blit, 10)
    # the monthly bar chart
    fig2 = Figure(figsize=(6, 3), dpi=100, layout="constrained")
    c2 = FigureCanvasQTAgg(fig2)
    c2.resize(600, 300)
    ax2 = fig2.add_subplot()
    ax2.bar(range(12), [3.9, 5.4, 8.1, 9.6, 11.2, 11.9, 12.6, 11.4, 8.7, 6.1, 3.8, 3.2])
    bars = timed(c2.draw)
    # the PDF
    t = time.perf_counter()
    fig.savefig(OUT / "grafici_prova_matplotlib.pdf")
    pdf = (time.perf_counter() - t) * 1000
    size = os.path.getsize(OUT / "grafici_prova_matplotlib.pdf") // 1024
    report("1. matplotlib QtAgg", primo_disegno=f"{first:.0f} ms", ridisegno=f"{redraw:.0f} ms",
           passaggio_ridisegno=f"{hover1:.0f} ms", passaggio_blit=f"{hover2:.1f} ms", mensile=f"{bars:.0f} ms",
           pdf=f"{pdf:.0f} ms ({size} KB, vettoriale)", memoria=f"+{rss_mb() - r0:.0f} MB")
    (OUT / "grafici_prova_matplotlib.pdf").unlink()
    canvas.grab().save(str(OUT / "grafici_prova_matplotlib.png"))
    return canvas, c2


# ------------------------------------------------------------------ 2. pyqtgraph

def prova_pyqtgraph(app, data):
    try:
        import pyqtgraph as pg
    except ImportError:
        report("2. pyqtgraph", stato="non installato (pip install pyqtgraph in un ambiente a parte)")
        return None
    from PySide6.QtCore import QPointF
    r0 = rss_mb()
    pg.setConfigOptions(background="w", foreground="k")
    out = {}
    def run(aa):
        pg.setConfigOptions(antialias=aa)
        w = pg.PlotWidget()
        w.resize(600, 300)
        w.show()
        xs = np.arange(HOURS, dtype=float)
        t = time.perf_counter()
        item = w.plot(xs, data, pen=pg.mkPen("#2e6fb0", width=1))
        w.plot(xs, np.minimum(data, 6 + 4 * np.sin(xs / 24 * np.pi)), pen=pg.mkPen("#0ca30c", width=1))
        item.setClipToView(True)
        w.grab()
        first = (time.perf_counter() - t) * 1000
        redraw = timed(lambda: w.grab())
        v = pg.InfiniteLine(angle=90, movable=False)
        h = pg.InfiniteLine(angle=0, movable=False)
        label = pg.TextItem("", anchor=(0, 1))
        w.addItem(v)
        w.addItem(h)
        w.addItem(label)
        vb = w.getPlotItem().vb
        step = [0]

        def hover():
            i = step[0] = (step[0] + 97) % HOURS
            p = vb.mapViewToScene(QPointF(float(i), float(data[i])))
            m = vb.mapSceneToView(p)
            v.setPos(m.x())
            h.setPos(m.y())
            label.setText(f"{int(m.x())} h: {m.y():.1f} kW")
            label.setPos(m.x(), m.y())
            w.grab()
        hov = timed(hover, 10)
        scale = [1.0]

        def zoom():
            scale[0] = 0.9 if scale[0] == 1.0 else 1.0
            vb.setXRange(2000 * scale[0], 3000, padding=0)
            w.grab()
        z = timed(zoom, 6)
        if aa:
            w.grab().save(str(OUT / "grafici_prova_pyqtgraph.png"))
        widgets.append(w)
        return first, redraw, hov, z

    widgets = []
    for aa in (False, True):
        out[aa] = run(aa)
    a, b = out[False], out[True]
    report("2. pyqtgraph 0.14 (MIT)", primo_disegno=f"{a[0]:.0f}/{b[0]:.0f} ms", ridisegno=f"{a[1]:.0f}/{b[1]:.0f} ms",
           passaggio_mirino=f"{a[2]:.0f}/{b[2]:.0f} ms", zoom=f"{a[3]:.0f}/{b[3]:.0f} ms (senza/con antialiasing)",
           memoria=f"+{rss_mb() - r0:.0f} MB", pdf="SVG o QPdfWriter, nessun esportatore PDF")
    return widgets


# ------------------------------------------------------------------ 3. Qt Charts

def prova_qtcharts(app, data):
    try:
        from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
    except ImportError:
        report("3. Qt Charts", stato="modulo assente")
        return None
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QPainter
    r0 = rss_mb()
    chart = QChart()
    s = QLineSeries()
    t = time.perf_counter()
    s.replace([QPointF(float(i), float(v)) for i, v in enumerate(data)])
    chart.addSeries(s)
    ax = QValueAxis()
    ay = QValueAxis()
    chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
    s.attachAxis(ax)
    s.attachAxis(ay)
    chart.legend().hide()
    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.resize(600, 300)
    view.show()
    view.grab()
    first = (time.perf_counter() - t) * 1000
    redraw = timed(lambda: view.grab())
    hovered = []
    s.hovered.connect(lambda p, st: hovered.append((p, st)))
    view.setRubberBand(QChartView.RubberBand.RectangleRubberBand)

    toggled = [0]

    def zoom():
        toggled[0] ^= 1
        chart.zoomIn() if toggled[0] else chart.zoomReset()
        view.grab()
    z = timed(zoom, 6)
    view.grab().save(str(OUT / "grafici_prova_qtcharts.png"))
    report("3. Qt Charts (deprecato 6.10)", primo_disegno=f"{first:.0f} ms", ridisegno=f"{redraw:.0f} ms", zoom=f"{z:.0f} ms",
           passaggio="segnale hovered per punto (non misurabile senza mouse)", memoria=f"+{rss_mb() - r0:.0f} MB",
           pdf="QChartView.render su QPdfWriter, vettoriale")
    return view


# ------------------------------------------------------------------ 4. Qt Graphs 2D (QML)

def prova_qtgraphs(app, data):
    from PySide6.QtCore import QUrl
    from PySide6.QtQuickWidgets import QQuickWidget
    r0 = rss_mb()
    pts = ", ".join(f"Qt.point({i}, {v:.1f})" for i, v in enumerate(data[::1]))
    qml = OUT / "grafici_prova_graphs.qml"
    qml.write_text(f"""import QtQuick
import QtGraphs
Item {{ width: 600; height: 300
  GraphsView {{ anchors.fill: parent; id: g
    axisX: ValueAxis {{ min: 0; max: {HOURS} }}
    axisY: ValueAxis {{ min: 0; max: 80 }}
    LineSeries {{ id: s; hoverable: true; width: 1 }}
  }}
  Component.onCompleted: {{ s.replace([{pts}]) }}
}}
""")
    t = time.perf_counter()
    w = QQuickWidget()
    w.setSource(QUrl.fromLocalFile(str(qml)))
    ok = w.status() == QQuickWidget.Status.Ready
    errors = "; ".join(e.toString() for e in w.errors())
    w.resize(600, 300)
    w.show()
    spin(app, 100)
    first = (time.perf_counter() - t) * 1000
    img = w.grab()
    img.save(str(OUT / "grafici_prova_qtgraphs.png"))
    qml.unlink()
    note = "offscreen senza GPU la scena non si disegna (come la vista 3D): il tempo è il caricamento" if ok else f"errore: {errors[:120]}"
    report("4. Qt Graphs 2D (QML, GPL-3)", caricamento_e_primo_fotogramma=f"{first:.0f} ms", stato=note,
           memoria=f"+{rss_mb() - r0:.0f} MB", passaggio="segnale hover(serie, posizione, valore)", pdf="grabToImage, raster")
    return w


# ------------------------------------------------------------------ 5. vista web

def prova_web(app, data):
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        report("5. vista web (QtWebEngine)", stato="modulo assente")
        return None
    r0 = rss_mb()
    n = len(data)
    pts = " ".join(f"{560 * i / n:.1f},{280 - 260 * v / 80:.1f}" for i, v in enumerate(data))
    page = (f"<html><body style='margin:0'><svg width='600' height='300' viewBox='0 0 600 300'>"
            f"<polyline points='{pts}' fill='none' stroke='#2e6fb0' stroke-width='0.8'/></svg></body></html>")
    html = OUT / "grafici_prova_web.html"
    html.write_text(page)
    from PySide6.QtCore import QUrl
    t = time.perf_counter()
    view = QWebEngineView()
    view.resize(600, 300)
    done = []
    view.loadFinished.connect(lambda ok: done.append(ok))
    view.load(QUrl.fromLocalFile(str(html)))
    view.show()
    end = time.perf_counter() + 15
    while not done and time.perf_counter() < end:
        app.processEvents()
    first = (time.perf_counter() - t) * 1000
    spin(app, 300)
    img = view.grab()
    img.save(str(OUT / "grafici_prova_web.png"))
    html.unlink()
    report("5. vista web (QtWebEngine)", avvio_e_pagina=f"{first:.0f} ms" if done else "non ha finito in 15 s",
           caricata=str(bool(done and done[0])), memoria=f"+{rss_mb() - r0:.0f} MB nel processo principale (più il processo del browser)",
           ruota="111 MiB Linux, 126 MiB Windows", pdf="printToPdf asincrono o SVG dalla libreria")
    return view


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    data = year()
    print(f"{HOURS} valori orari, finestra 600 x 300 px, offscreen, Python {sys.version.split()[0]}")
    keep = []
    for prova in (prova_matplotlib, prova_pyqtgraph, prova_qtcharts, prova_qtgraphs, prova_web):
        gc.collect()
        try:
            keep.append(prova(app, data))
        except Exception as error:      # noqa: BLE001 (la prova dice che cosa è andato storto)
            report(prova.__name__, errore=f"{type(error).__name__}: {error}")
    return 0


if __name__ == "__main__":
    tracemalloc.start()
    sys.exit(main())
