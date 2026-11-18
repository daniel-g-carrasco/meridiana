"""Reproducible Italian result-page/table photographs, with actual pixel dimensions.

Example (PowerShell, from the repository root):
  $env:PYTHONPATH='tests;src'; $env:QT_QPA_PLATFORM='windows'; $env:QT_SCALE_FACTOR='2'
  python -m quick.grafici.photographs_pages --kind tables --theme light dark --output build/table-photos

Use a new output directory for each revision: existing photographs are never overwritten.
The environment selects the Qt platform and scale before QApplication is constructed.
"""
import argparse
import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QLocale, QPoint, QSize, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import _setup
from meridiana import i18n
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend import charts_bridge, charts_data
from quick.grafici.fixtures import build_results


QML = _setup.ROOT / "src/meridiana/quick/qml"


def dimensions(value):
    try:
        width, height = (int(part) for part in value.lower().split("x"))
        if min(width, height) < 200:
            raise ValueError
        return width, height
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use WIDTHxHEIGHT, at least 200x200") from error


def wait(app, predicate, seconds=15):
    end = time.monotonic() + seconds
    while not predicate() and time.monotonic() < end:
        app.processEvents()
        QTest.qWait(10)
        time.sleep(0.005)
    if not predicate():
        raise RuntimeError("The result did not become ready for a photograph")


def table_is_visible(subject):
    for child in subject.childItems():
        if not child.metaObject().className().startswith("QQuickLoader"):
            continue
        table = child.property("item")
        if table is not None and child.opacity() >= 0.999 and table.property("item") is not None:
            return True
    return False


def photograph(app, payload, component, width, height, theme, target):
    if target.exists():
        raise FileExistsError(target)
    engine = QQmlApplicationEngine()
    theme_tokens = install_controls(engine)
    theme_tokens.configure({"theme": theme})
    engine.addImportPath(str(QML))
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.rootContext().setContextProperty("payload", payload)
    field = "chartData" if component == "Chart" else "pageData"
    engine.loadData(f'''import QtQuick
import Meridiana.Theme
import Meridiana.Charts 1.0
Window {{ width: {width}; height: {height}; color: Theme.colors.view
    {component} {{ objectName: "subject"; anchors.fill: parent; {field}: payload }}
}}'''.encode(), QUrl.fromLocalFile(str(QML / "photograph-pages.qml")))
    if not engine.rootObjects():
        raise RuntimeError("\n".join(warnings))
    window = engine.rootObjects()[0]
    subject = window.findChild(QQuickItem, "subject")
    screens = app.screens()
    if len(screens) > 1:
        window.setScreen(screens[1])
        window.setPosition(screens[1].availableGeometry().topLeft() + QPoint(20, 20))
    # Windows otherwise caps a large requested window to the monitor's work area.
    window.setMinimumSize(QSize(width, height))
    window.resize(width, height)
    window.show()
    try:
        wait(app, window.isExposed)
        QTest.qWait(150)
        if component == "Chart":
            subject.setProperty("tableMode", True)
            wait(app, lambda: subject.property("readyForDisplay") and table_is_visible(subject))
        elif payload.get("tabs"):
            wait(app, lambda: subject.property("displayedPage") is not None)
        QTest.qWait(300)
        image = window.grabWindow()
        scale = window.devicePixelRatio()
        expected = (round(width * scale), round(height * scale))
        actual = (image.width(), image.height())
        if image.isNull() or actual != expected or (window.width(), window.height()) != (width, height):
            raise AssertionError(("Unexpected dimensions", expected, actual, window.size()))
        if warnings:
            raise AssertionError(warnings)
        if not image.save(str(target)):
            raise OSError(f"Could not save {target}")
        table = payload.get("table", {})
        return {"path": str(target), "theme": theme, "logical": [width, height],
                "pixels": list(actual), "dpr": scale, "title": payload.get("title", ""),
                "rows": len(table.get("rows", [])), "columns": len(table.get("headers", [])),
                "qml_warnings": warnings}
    finally:
        window.close()
        engine.deleteLater()
        app.processEvents()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("pages", "tables", "storage"), required=True)
    parser.add_argument("--theme", choices=("light", "dark"), nargs="+", default=["light", "dark"])
    parser.add_argument("--sizes", type=dimensions, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sizes = args.sizes or ([(1366, 900), (1600, 960), (1920, 1080)] if args.kind == "pages" else [(900, 620)])
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    i18n.setup("it")
    QLocale.setDefault(QLocale("it_IT"))
    app = QApplication.instance() or QApplication(["result-photographs"])
    charts_bridge.register()
    result = build_results()
    pages = {"produzione": charts_data.production(result.sim, result.pvgis),
             "consumi": charts_data.consumption(result.load),
             "economia": charts_data.economics(result.econ, sizing=result.sizing, storage=result.storage,
                                               p_stc_kw=result.sim.p_stc_kw, battery_kwh=5)}
    if args.kind == "storage":
        battery = dict(manufacturer="Fixture", model="B10", usable_energy_kwh=10,
                       max_charge_power_w=5000, max_discharge_power_w=5000,
                       round_trip_efficiency_pct=90, coupling="ac")
        payloads = {"accumulo-vuoto": charts_data.storage({}),
                    "accumulo-ac": charts_data.storage(dict(battery=battery, battery_units=1,
                                                            storage_coupling="ac"))}
        component = "ResultsPage"
    elif args.kind == "pages":
        payloads, component = pages, "ResultsPage"
    else:
        charts = {chart["id"]: chart for tab in pages["consumi"]["tabs"] for chart in tab["charts"]}
        payloads = {"monthly": charts["monthly"], "year_map": charts["year_map"],
                    "anno8760": charts_data.line(list(range(8760)), [("Consumo", result.load.hourly.tolist())],
                                                 "kWh", xlabel="Ora", decimals=2,
                                                 title="Consumi delle 8760 ore").to_dict()}
        component = "Chart"
    manifest = {"language": "it", "platform": app.platformName(), "qt_scale_factor": os.getenv("QT_SCALE_FACTOR", ""),
                "shared_table_available": (QML / "Meridiana/Controls/Table.qml").exists(), "images": []}
    for width, height in sizes:
        for theme in args.theme:
            for name, payload in payloads.items():
                target = args.output / f"{name}-{theme}-{width}x{height}.png"
                record = photograph(app, payload, component, width, height, theme, target)
                manifest["images"].append(record)
                print(target, record["pixels"], flush=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
