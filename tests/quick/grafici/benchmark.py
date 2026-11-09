"""Reproducible D3D11 comparison; run each renderer/form in a fresh process."""
import argparse
import base64
import json
import math
import os
from pathlib import Path
import statistics
import time

os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")
os.environ.setdefault("QSG_RENDER_LOOP", "basic")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPointF, QTimer, QUrl
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("renderer", choices=("graphs", "retained", "production"))
    parser.add_argument("form", choices=("line", "map"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app = QGuiApplication([])
    engine = QQmlApplicationEngine()
    points = [QPointF(i / 8759 * 1000, 450 - 390 * max(0, math.sin((i % 24 - 6) * math.pi / 12))
                     * (0.65 + 0.35 * math.sin(i / 8760 * math.pi))) for i in range(8760)]
    matrix = QImage(365, 24, QImage.Format.Format_RGB32)
    for d in range(365):
        for h in range(24):
            value = (500 - points[d * 24 + h].y()) / 500
            matrix.setPixelColor(d, h, QColor.fromRgbF(0.8 - value * 0.75, 0.9 - value * 0.7, 1 - value * 0.6))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    matrix.save(buffer, "PNG")
    engine.rootContext().setContextProperty("points", points)
    engine.rootContext().setContextProperty("mapUrl", "data:image/png;base64," + base64.b64encode(bytes(data)).decode())
    engine.rootContext().setContextProperty("useGraphs", args.renderer == "graphs")
    engine.rootContext().setContextProperty("useMap", args.form == "map")
    preparations = []
    if args.renderer == "production":
        from meridiana.quick.backend import charts_bridge, charts_data, charts_scene
        from meridiana.quick.backend.tokens import install_theme
        charts_bridge.register()
        _theme = install_theme(engine)  # Keep the context provider alive.
        original_prepare = charts_scene.prepare
        def prepare(data):
            begin = time.perf_counter()
            prepared = original_prepare(data)
            preparations.append((time.perf_counter()-begin)*1000)
            return prepared
        charts_scene.prepare = prepare
        chart = (charts_data.heatmap([[500-points[d*24+h].y() for d in range(365)] for h in range(24)],
                                    [str(h) for h in range(24)], [str(d) for d in range(365)], "kW")
                 if args.form == "map" else charts_data.line(list(range(8760)),
                                     [("Power", [500-p.y() for p in points])], "kW"))
        engine.rootContext().setContextProperty("benchmarkData", chart.to_dict())
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    qml = '''import QtQuick
import QtQuick.Shapes
import QtGraphs
Window {
 id: win; width: 1366; height: 900; visible: true; color: "#fcfcfb"
 property int step: -1
 property bool running: false
 property int builds: 0
 signal done()
 Item { id: plot; anchors.fill: parent; anchors.margins: 70
 Loader { anchors.fill: parent; sourceComponent: useGraphs ? graphs : retained }
 }
 Component { id: retained
 Item {
 Loader { active: !useMap; sourceComponent: Shape { width: 1000; height: 500
 transform: Scale { xScale: plot.width/1000; yScale: plot.height/500 }
 ShapePath { strokeColor: "#2a78d6"; strokeWidth: 1; cosmeticStroke: true; fillColor: "transparent"
 PathPolyline { path: points; onPathChanged: win.builds++ }
 } }
 }
 Image { visible: useMap; anchors.fill: parent; source: mapUrl; smooth: false }
 }
 }
 Component { id: graphs
 GraphsView { id: graph; anchors.fill: parent; shadowVisible: false
 axisX: ValueAxis { min: 0; max: useMap ? 365 : 1000 }
 axisY: ValueAxis { min: 0; max: useMap ? 24 : 500 }
 LineSeries { id: line; objectName: "line"; visible: !useMap; color: "#2a78d6"; width: 1 }
 ScatterSeries { id: map; objectName: "map"; visible: useMap
 pointDelegate: Rectangle {
 required property int index
 width: graph.plotArea.width/365 + 0.2; height: graph.plotArea.height/24 + 0.2
 property real v: (500-points[index].y)/500
 color: Qt.rgba(0.8-v*0.75, 0.9-v*0.7, 1-v*0.6, 1)
 }
 }
 }
 }
 Timer { interval: 25; running: win.running; repeat: true
 onTriggered: {
 win.step++;
 if (win.step >= 40) { win.running=false; win.done(); return }
 win.width=1371+win.step*5; win.height=902+win.step*2;
 }
 }
}'''
    if args.renderer == "production":
        # Measure the actual component without loading unused Qt Graphs types.
        qml = '''import QtQuick
import Meridiana.Charts
Window {
 id: win; width: 1366; height: 900; visible: true; color: "#fcfcfb"
 property int step: -1
 property bool running: false
 signal done()
 Chart { anchors.fill: parent; chartData: benchmarkData }
 Timer { interval: 25; running: win.running; repeat: true
 onTriggered: {
 win.step++;
 if (win.step >= 40) { win.running=false; win.done(); return }
 win.width=1371+win.step*5; win.height=902+win.step*2;
 }
 }
}'''
    started = time.perf_counter()
    engine.loadData(qml.encode(), QUrl("file:///benchmark.qml"))
    if not engine.rootObjects():
        raise RuntimeError(warnings)
    window = engine.rootObjects()[0]
    if args.renderer == "graphs":
        from PySide6.QtGraphs import QLineSeries, QScatterSeries
        series = window.findChild(QScatterSeries if args.form == "map" else QLineSeries, args.form)
        values = [QPointF(i // 24 + 0.5, 23.5 - i % 24) for i in range(8760)] if args.form == "map" else points
        series.replace(values)
    populated = time.perf_counter()
    frames = []
    render_times = []
    render_start = [None]
    first = []
    resize_start = [None]

    def resized():
        if window.property("running"):
            resize_start[0] = time.perf_counter()

    def swapped():
        now = time.perf_counter()
        if not first:
            first.append((now - started) * 1000)
        if resize_start[0] is not None:
            frames.append((now - resize_start[0]) * 1000)
            resize_start[0] = None

    window.widthChanged.connect(resized)
    window.frameSwapped.connect(swapped)
    window.beforeSynchronizing.connect(lambda: render_start.__setitem__(0, time.perf_counter()))

    def rendered():
        if window.property("running") and render_start[0] is not None:
            render_times.append((time.perf_counter() - render_start[0]) * 1000)

    window.afterRendering.connect(rendered)

    def done():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shot = args.output.with_suffix(".png")
        window.grabWindow().save(str(shot))
        result = {"renderer": args.renderer, "form": args.form, "api": str(window.rendererInterface().graphicsApi()),
                  "platform": app.platformName(), "dpr": window.devicePixelRatio(), "points": 8760,
                  "populate_ms": (populated-started)*1000, "first_frame_ms": first,
                  "steps": 40, "resize_frames": len(frames), "resize_ms": frames,
                  "median_ms": statistics.median(frames) if frames else None,
                  "max_ms": max(frames) if frames else None, "path_builds": len(preparations) if preparations else window.property("builds"),
                  "prepare_ms": preparations,
                  "render_ms": render_times, "render_median_ms": statistics.median(render_times) if render_times else None,
                  "render_max_ms": max(render_times) if render_times else None,
                  "warnings": warnings, "screenshot": str(shot)}
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k not in ("resize_ms", "render_ms")}))
        app.quit()

    window.done.connect(done)
    QTimer.singleShot(700, lambda: window.setProperty("running", True))
    QTimer.singleShot(90000, app.quit)
    app.exec()
    window.close()


if __name__ == "__main__":
    main()
