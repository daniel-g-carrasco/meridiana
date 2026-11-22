"""Regenerate README photographs: python tools/readme_screenshots.py.

Real Qt Quick window, offscreen, temporary profile, fictional geometry, recorded
test weather. No model server, credentials, real projects or network required.
The three existing README images are intentionally replaced.

--live: the same captures on a real screen (full screen, the GPU's rendering, the
orthophoto from the network), for a session the user hands over: run it on the
desktop where the window may appear, e.g. from the Flatpak on Linux. The weather
stays the recorded one; only the map tiles come from the network.
"""
from __future__ import annotations

import argparse
import contextlib
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def demo():
    from _fixtures import capannone, inverter_record
    from meridiana.core.model import model

    project = capannone("Solar workshop: demonstration")
    project.site.address = "Demonstration site (recorded test weather)"
    project.buildings[0].name = "Workshop"
    project.subfields[0].name = "South roof"
    project.buildings.append(model.Building(
        id="b2", name="Store", height=5.5,
        footprint=[[44, 3], [55, 3], [55, 16], [44, 16]],
        roof=model.Roof(type="gable", tilt=25)))
    project.exclusions.append(model.ExclusionItem(
        id="e1", kind="skylight", building="b1",
        ring=[[17, 8], [20, 8], [20, 10], [17, 10]]))
    project.energy = {
        "inverters": [{"record": inverter_record(), "count": 3, "name": "Demo inverter"}],
        "strings": {"auto": True},
    }
    project.consumption = {"annual_kwh": 40000., "profile": "office"}
    project.economics = {"capex_total": 45000.}
    from meridiana.app import jobs
    layouts, _, _ = jobs.layout_of(project)
    modules = [f"s1/{m.key}" for m in layouts["s1"].modules]
    project.energy["strings"] = {"auto": False, "runs": [
        {"inverter": 1 + i // 2, "mppt": 1 + i % 2, "modules": modules[start:start + 25]}
        for i, start in enumerate(range(0, len(modules), 25))]}
    return project


def capture(folder, out, live=False):
    import _setup
    from PIL import Image
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtQml import QQmlEngine, QQmlExpression
    from meridiana import i18n
    from meridiana.app import jobs, pipeline
    from meridiana.core.energy import meteo
    from meridiana.gui.application import QuickWindow, create_app
    from _fixtures import FakePvgis
    from quick.gestures import item, pump, wait_for

    i18n.setup("en")
    app = create_app(language="en")
    if not live:
        assert app.platformName() == "offscreen", "Never show the capture window on the desktop"
    project = demo()
    cache = folder / "weather"
    with FakePvgis():
        meteo.typical_year(project.site.lat, project.site.lon, cache)
        meteo.horizon(project.site.lat, project.site.lon, cache)
    # From this point requests fail rather than falling back to a live service.
    offline = patch("requests.sessions.Session.request", side_effect=RuntimeError("Offline capture"))
    with (contextlib.nullcontext() if live else offline):
        host = QuickWindow(project, cache, real_views=True,
                           theme={"theme": "light", "reducedMotion": True})
        try:
            host.bridge.configure_background(enabled=False)
            host.cfg.network_tiles = live
            host.cfg.network_geocoding = host.cfg.network_pvgis = False
            host.cfg.assistant_voice = False
            if not live:
                host.plan.configureMaps({"offline": True})
            host.keep_on_screen = lambda: None
            host._placement.timeout.disconnect()
            win = host.window
            win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            if live:
                win.showFullScreen()
            else:
                win.resize(1600, 1000)
                win.show()
            frame_timer = QTimer(win)
            frame_timer.timeout.connect(win.requestUpdate)
            frame_timer.start(16)

            def settle():
                controller = host.engine.incubationController()
                end = time.monotonic() + 30
                while time.monotonic() < end:
                    if controller is not None:
                        controller.incubateFor(20)
                    pump(50)
                    if controller is None or controller.incubatingObjectCount() == 0:
                        pump(300)
                        if controller is None or controller.incubatingObjectCount() == 0:
                            return
                raise RuntimeError("QML did not finish loading")

            settle()
            wait_for(lambda: not host.bridge.busy and host.bridge._layout is None
                     and not host.bridge.session.telling(), 60)
            project = host.bridge.session.project
            layouts, keys, _ = jobs.layout_of(project)
            energy = pipeline.compute(project, layouts, cache, fetch=False).as_dict()
            assert energy["sim"] is not None and energy["sim"].energy_kwh > 0
            assert len(energy["sim"].hourly) == 8760
            print(f"Computed recorded year: {energy['sim'].energy_kwh:.1f} kWh", flush=True)
            host.bridge.session.take_year(layouts, keys, energy)
            wait_for(lambda: not host.bridge.session.telling()
                     and not host.parts.controllers["results"].busy, 60)
            item(win, "plan").fit()
            host.bridge.select("building", "b1", "")
            host.shell.trigger("panel_checks")
            settle()

            def save(name):
                pump(6000 if live else 1000)   # live: the map tiles arrive from the network
                settle()
                target = out / (name + ".png")
                result = win.contentItem().grabToImage()
                ready = []
                result.ready.connect(lambda: ready.append(True))
                wait_for(lambda: bool(ready), 15)
                image = result.image()
                if not live:
                    assert (image.width(), image.height()) == (1600, 1000)
                image.save(str(target))
                with Image.open(target) as source:
                    assert len(source.getcolors(source.width * source.height) or []) > 100, "Empty capture"
                    background = Image.new("RGBA", source.size, win.color().name())
                    background.alpha_composite(source.convert("RGBA"))
                    picture = background.convert("RGB")
                    if live:   # the screen's pixels, brought to the README's width
                        picture = picture.resize((1600, round(1600 * picture.height / picture.width)),
                                                 Image.Resampling.LANCZOS)
                        picture.save(target, optimize=True)
                    else:
                        picture.quantize(colors=256).save(target, optimize=True)
                assert target.stat().st_size < (1_500_000 if live else 400_000), target
                print(f"{target.name}: {target.stat().st_size} bytes", flush=True)

            save("modelling")
            win.showPhase("plant")
            settle()
            host.parts.controllers["plantActions"].openSection("inverter")
            settle()
            item(win, "plan").fit()
            save("plant")
            for phase, name in (("production", "production"), ("economics", "economics")):
                win.showPhase(phase)
                settle()
                wait_for(lambda: not host.parts.controllers["results"].busy, 60)
                save(name)
            win.showPhase("report")
            settle()
            report = host.parts.controllers["report"]
            wait_for(lambda: not report.busy and report.pages and report.outline, 180)
            assert not report.error, report.error
            settle()
            preview = item(win, "reportPreview")
            preview.zoomTo(0.6)
            settle()
            first_page = item(win, "reportPreviewPage")
            expression = QQmlExpression(QQmlEngine.contextForObject(preview), preview,
                                       f"contentItem.contentY = {first_page.height() + 32}")
            expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            def report_images():
                pending, found = [win.contentItem()], []
                while pending:
                    node = pending.pop()
                    if node.objectName() == "reportPreviewImage":
                        found.append(node)
                    pending.extend(node.childItems())
                return found

            def pages_loaded():
                visible = [node for node in report_images() if node.property("want")]
                return visible and all(not node.property("source").isEmpty() for node in visible)

            wait_for(pages_loaded, 60)
            print("Report page images loaded", flush=True)
            save("report")
            win.showPhase("model")
            settle()
            item(win, "plan").fit()
            chat = host.parts.controllers["assistant"]
            host.shell.trigger("assistant")
            pump(300)
            chat.ask("Show navigation controls")
            chat._dismiss_setup()  # the same action as the card's Not now button
            save("meridio")
            host.theme.configure({"theme": "dark"})
            host.shell.trigger("assistant")
            win.showPhase("model")
            save("modelling-dark")
            # Qt can warn when a hidden, prefetched delegate is discarded.
            # Keep those diagnostics visible; the captures must also be reviewed.
            for warning in host.warnings:
                print("Qt diagnostic: " + warning, file=sys.stderr)
        finally:
            host.close()
            app.processEvents()
        assert not _setup.profile_written(), "The capture changed the user's profile"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "images")
    parser.add_argument("--live", action="store_true",
                        help="capture on the real screen, full screen, with the map from the network")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.update(QT_QUICK_BACKEND="rhi", MERIDIANA_PRELOAD="0", MERIDIANA_WORKERS="2",
                      PYTHON_KEYRING_BACKEND="keyring.backends.null.Keyring", LANGUAGE="en")
    if not args.live:
        os.environ.update(QT_QPA_PLATFORM="offscreen", QSG_RENDER_LOOP="basic", QT_SCALE_FACTOR="1")
    if sys.platform == "win32" and not args.live:
        os.environ["QSG_RHI_BACKEND"] = "d3d11"
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
    os.environ["PYTHONPATH"] = str(ROOT / "src")
    with tempfile.TemporaryDirectory(prefix="meridiana-readme-", ignore_cleanup_errors=True) as temporary:
        folder = Path(temporary)
        # Profile paths are isolated before any application or test helper import.
        for key in ("APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
            os.environ[key] = str(folder / key.lower())
        capture(folder, args.out, args.live)


if __name__ == "__main__":
    main()
