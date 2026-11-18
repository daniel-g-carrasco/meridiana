"""Widgets/Quick pairs for each form, theme, viewport and scale on Windows D3D11."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")
os.environ.setdefault("QSG_RENDER_LOOP", "basic")

from PySide6.QtCore import QObject, QSize, QUrl, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from meridiana import config, i18n
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend import charts_bridge, charts_data
from meridiana.ui import charts, theme
from quick.grafici.fixtures import build_results

ROOT = Path(__file__).resolve().parents[3]


def specimens(results):
    pages = [charts_data.production(results.sim, results.pvgis), charts_data.consumption(results.load),
             charts_data.economics(results.econ, sizing=results.sizing, storage=results.storage,
                                   p_stc_kw=results.sim.p_stc_kw)]
    all_charts = {c["id"]: c for page in pages for tab in page["tabs"] for c in tab["charts"]}
    production = pages[0]["tabs"][0]["charts"][0]
    annual = charts_data.line(list(range(len(results.sim.hourly))),
                             [("Meridiana", (results.sim.hourly.p_ac/1000).tolist())], "kW",
                             title="Produzione oraria, 8.760 ore", source="PVGIS 5.3, meteo registrato Rho").to_dict()
    return dict(barre=production, impilate=all_charts["monthly"], perdite=all_charts["losses_chart"],
                giorno=all_charts["day"], mappa=all_charts["year_map"], settimana=all_charts["week"],
                anno=annual, cassa=all_charts["cash"], confronti=all_charts["size_share"], flussi=all_charts["flows"])


def draw_widget(widget, data):
    kind = data["kind"]
    if kind == "bars":
        widget.bars(data["categories"], data["series"], data["unit"], data["stacked"], data["decimals"])
    elif kind == "changes":
        widget.changes(data["categories"], data["series"][0][1], data["unit"])
    elif kind == "heatmap":
        widget.heatmap(data["matrix"], data["rows"], data["cols"], data["unit"], data["decimals"],
                       ticks=data["ticks"], row_ticks=data["row_ticks"])
    elif kind == "line":
        widget.line(data["xs"], data["series"], data["unit"], **{k: data[k] for k in
                    ("xlabel", "decimals", "area", "mark_zero", "mark", "markers", "ticks", "names")})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=("light", "dark"), required=True)
    parser.add_argument("--size", default="1366x900")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    app = QApplication([])
    i18n.setup("it")
    charts_bridge.register()
    width, height = [int(v) for v in args.size.split("x")]
    engine = QQmlApplicationEngine()
    provider = install_controls(engine, {"theme": args.theme})
    font = QFont(provider.fontFamily)
    font.setPixelSize(13)
    app.setFont(font)
    old_theme = theme.Theme(config.Config(theme=args.theme, accent='indigo', backgrounds='grey', font='plex'), app=app)
    old_theme.apply()
    t = old_theme.tokens
    charts.set_theme(t, args.theme == "dark", provider.fontFamily)
    samples = specimens(build_results())
    engine.rootContext().setContextProperty("specimen", next(iter(samples.values())))
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.loadData(b'''import QtQuick
import Meridiana.Charts
import Meridiana.Theme
Window { width: 1366; height: 900; visible: true; color: Theme.colors.card
 Chart { objectName: "chart"; anchors.fill: parent; chartData: specimen }
}''', QUrl.fromLocalFile(str(ROOT / "build/photos.qml")))
    if not engine.rootObjects():
        raise RuntimeError(warnings)
    window = engine.rootObjects()[0]
    window.setMinimumSize(QSize(width, height))
    window.resize(width, height)
    chart = window.findChild(QObject, "chart")
    dpr = window.devicePixelRatio()
    out = (args.output or ROOT / "build/quick-foto/grafici" / f"{args.theme}-{args.size}-scala{dpr:g}").resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)
    summaries = []
    images = []
    for name, data in samples.items():
        engine.rootContext().setContextProperty("specimen", data)
        widget = charts.Chart(data["title"])
        widget.setMinimumSize(width, height)
        widget.resize(width, height)
        widget.show()
        app.processEvents()
        draw_widget(widget, data)
        QTest.qWait(160)
        app.processEvents()
        quick = window.grabWindow()
        old = widget.grab().toImage()
        assert (quick.width(),quick.height()) == (int(width*dpr),int(height*dpr)), (quick.size(),dpr)
        assert quick.size() == old.size(), (quick.size(),old.size())
        pair = QImage(quick.width()+old.width(), max(quick.height(), old.height())+int(32*dpr), QImage.Format.Format_RGB32)
        pair.fill(QColor("#dedede"))
        painter = QPainter(pair)
        heading_font = QFont(provider.fontFamily)
        heading_font.setPixelSize(int(16*dpr))
        painter.setFont(heading_font)
        painter.setPen(QColor("#171717"))
        painter.drawText(12, int(23*dpr), "Widgets | "+name)
        painter.drawText(old.width()+12, int(23*dpr), "Quick | "+name)
        # Clear DPR before painting physical pixels side by side.
        old.setDevicePixelRatio(1)
        quick.setDevicePixelRatio(1)
        painter.drawImage(0, int(32*dpr), old)
        painter.drawImage(old.width(), int(32*dpr), quick)
        painter.end()
        path = out / (name+".png")
        pair.save(str(path))
        images.append(pair.scaledToWidth(1600, Qt.TransformationMode.SmoothTransformation))
        summaries.append(dict(form=name, file=str(path.relative_to(ROOT)), kind=data["kind"],
                              rows=len(data["table"]["rows"]), series=len(data["series"]),
                              quick_pixels=[quick.width(),quick.height()], widget_pixels=[old.width(),old.height()]))
        widget.close()
        widget.deleteLater()
        app.processEvents()
    for group in range(2):
        subset = images[group*5:(group+1)*5]
        contact = QImage(1600, sum(im.height() for im in subset), QImage.Format.Format_RGB32)
        contact.fill(QColor("white"))
        painter = QPainter(contact)
        y = 0
        for im in subset:
            painter.drawImage(0, y, im)
            y += im.height()
        painter.end()
        contact.save(str(out / f"contact-{group+1}.png"))
    manifest = dict(theme=args.theme, viewport=[width,height], dpr=dpr, graphics=str(window.rendererInterface().graphicsApi()),
                    warnings=warnings, specimens=summaries, chart_geometry=chart.property("geometry"))
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("specimens","chart_geometry")}, ensure_ascii=False))
    window.close()
    engine.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    main()
