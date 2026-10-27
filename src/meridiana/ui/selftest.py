"""`meridiana --self-test [REPORT]`: the program checks itself, without a screen and without touching the settings of
whoever runs it (task 18f). It is the smoke test of the packages (the PyInstaller bundle, the Flatpak) and of the CI:
a frozen program has no console, so every line also goes to REPORT when one is named, written as it comes (a crash
leaves what was done).

What it checks, one line each with its time: the files a build must carry (Meridiana's catalogue of Italian and Qt's
own, the fonts, the icons, the manual, the product catalogue, the 3D scene, the voice's worker as a script another
Python can run, pvlib's tables); the libraries the program loads late (matplotlib, pyqtgraph, scipy); then the window,
offscreen, with a sample project (a shed at Rho with a sub-field on its roof): opened, laid, drawn in 3D, its year
computed on a synthetic weather year put in the cache (no network: every service is off in its settings), its report
written to PDF, the window grabbed. The exit code is 0 when everything passed, 1 when something failed, 2 when the
test itself broke (the traceback is in the report).

Everything happens in a temporary folder that the XDG variables point to (Windows honours them too, paths.py) and
the platform is Qt's offscreen one, unless MERIDIANA_SELF_TEST_PLATFORM names another: a test never opens a window
on a screen, nor reads or writes the real settings."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

from .. import ENV_PREFIX, SLUG, __version__

# the sample's site: Rho (MI), as the tests' shed
LAT, LON, ELEVATION = 45.5226, 9.03, 150.0
LIMIT_S = 240.0                     # the whole test, at most: a step that never ends is a failure, not a hang


class Report:
    """The lines of the test: PASS, FAIL or INFO (an optional part missing), a name, what was seen, the time."""

    def __init__(self, path: str | None):
        self.path = Path(path).resolve() if path else None
        self.start = time.perf_counter()
        self.failed = 0
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")

    def line(self, text: str) -> None:
        if sys.stdout is not None:
            try:
                print(text, flush=True)
            except OSError:
                pass
        if self.path is not None:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(text + "\n")

    def add(self, state: str, name: str, detail: str = "", since: float | None = None) -> None:
        if state == "FAIL":
            self.failed += 1
        spent = time.perf_counter() - (self.start if since is None else since)
        self.line(f"{state} {name}: {detail} [{spent:.2f} s]")

    def check(self, name: str, ok: bool, detail: str = "", since: float | None = None) -> bool:
        self.add("PASS" if ok else "FAIL", name, detail, since)
        return ok


def isolate(folder: Path, environ=os.environ) -> None:
    """Nothing of the test in the user's folders: Meridiana's settings, state, data and cache in `folder` (paths.py
    honours the XDG variables on Windows too); Qt's caches of compiled QML and shaders, which Qt keeps in the user's
    cache folder of the application (%LOCALAPPDATA%\\Meridiana\\cache on Windows, whatever XDG says), not written;
    matplotlib's font cache in `folder` too. Qt on the offscreen platform: no window on a screen."""
    for var, sub in (("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state"), ("XDG_DATA_HOME", "data"),
                     ("XDG_CACHE_HOME", "cache")):
        environ[var] = str(folder / sub)
    environ["MPLCONFIGDIR"] = str(folder / "matplotlib")
    environ["QML_DISABLE_DISK_CACHE"] = "1"
    environ["QT_DISABLE_SHADER_DISK_CACHE"] = "1"
    environ["QT_QPA_PLATFORM"] = environ.get(f"{ENV_PREFIX}_SELF_TEST_PLATFORM") or "offscreen"


def sample_project():
    """A shed of 40 x 20 m, 9,5 m high, at Rho, with a sub-field «Sud» on its flat roof, tilted rows at 15°."""
    from .. import model
    p = model.Project(name="Self-test")
    p.site = model.Site(lat=LAT, lon=LON, address="Rho (MI)")
    b = model.Building(id=p.new_id("b"), name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
    p.buildings.append(b)
    p.subfields.append(model.SubField(id=p.new_id("s"), name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]],
                                      building=b.id, params={"tilt": 15.0}, filled=True))
    return p


def synthetic_weather(cache: Path) -> None:
    """A weather year for the sample, made without the network and put in the cache as PVGIS's would be: pvlib's
    simplified Solis clear sky dimmed to a cloudy year, a seasonal temperature, a light wind (as the tests do)."""
    import numpy as np
    import pandas as pd
    import pvlib

    from .. import atomic
    from ..energy import meteo
    index = pd.date_range("1990-01-01 00:00", periods=8760, freq="h", tz="UTC")
    sky = pvlib.location.Location(LAT, LON, altitude=ELEVATION).get_clearsky(index + pd.Timedelta(minutes=10),
                                                                             model="simplified_solis")
    day, hour = index.dayofyear.to_numpy(), index.hour.to_numpy()
    k = 0.72
    columns = {"ghi": sky.ghi.to_numpy() * k, "dni": sky.dni.to_numpy() * k, "dhi": sky.dhi.to_numpy(),
               "temp_air": 13.0 - 10.0 * np.cos(2 * np.pi * (day - 15) / 365.0) + 4.0 * np.sin(2 * np.pi * (hour - 9) / 24.0),
               "wind_speed": np.full(8760, 1.5), "pressure": np.full(8760, 101325.0 * np.exp(-ELEVATION / 8434.0)),
               "relative_humidity": np.full(8760, 65.0)}
    raw = {"fetched": "2026-10-25",
           "meta": {"inputs": {"location": {"latitude": LAT, "longitude": LON, "elevation": ELEVATION,
                                            "irradiance_time_offset": 0.1767},
                               "meteo_data": {"radiation_db": "synthetic", "meteo_db": "synthetic",
                                              "year_min": 2026, "year_max": 2026}}},
           "columns": {c: [round(float(v), 3) for v in np.nan_to_num(columns[c])] for c in meteo.COLUMNS}}
    atomic.write_json(meteo._cache_file(cache, "tmy", LAT, LON), raw, keep_backup=False)


def files(report: Report) -> None:
    """What a build must carry, before any window."""
    from .. import help as helps
    from .. import i18n, paths
    t = time.perf_counter()
    report.check("catalogue it", i18n.translation_for("it").gettext("Settings") != "Settings",
                 "Meridiana's words in Italian", t)
    t = time.perf_counter()
    from .theme import FONT_DIR
    fonts = paths.shipped("fonts", FONT_DIR)
    report.check("fonts", fonts is not None and any(fonts.glob("*.ttf")), str(fonts), t)
    t = time.perf_counter()
    icons = [paths.shipped("icons", "lucide", "map.svg"), paths.shipped("icons", "hicolor", "scalable", "apps")]
    report.check("icons", all(icons), ", ".join(str(i) for i in icons), t)
    t = time.perf_counter()
    manual = helps.manual_dir()
    missing = [c for c in helps.CHAPTERS if manual is None or not (manual / c).is_file()]
    report.check("manual", manual is not None and not missing, f"{manual}" + (f", missing {missing}" if missing else ""), t)
    t = time.perf_counter()
    from .. import catalog
    counted = catalog.counts()
    total = sum(n for kind in counted.values() for n in kind.values())
    report.check("product catalogue", counted["modules"]["cec"] > 0 and total > 0, f"{total} records", t)
    t = time.perf_counter()
    from .view3d import QML_FILE
    report.check("3D scene file", QML_FILE.is_file(), str(QML_FILE), t)
    t = time.perf_counter()
    from ..assistant import speech
    worker = speech.worker_script()
    report.check("voice worker script", worker.is_file() and worker.suffix == ".py", str(worker), t)
    t = time.perf_counter()
    try:
        import pvlib.location
        altitude = float(pvlib.location.lookup_altitude(LAT, LON))
        report.check("pvlib tables", 0.0 < altitude < 1000.0, f"altitude of the site {altitude:.0f} m", t)
    except (OSError, ImportError, ValueError) as error:
        report.add("FAIL", "pvlib tables", f"{type(error).__name__}: {error}", t)
    t = time.perf_counter()
    from .. import updates
    authorities = updates.ssl_context().cert_store_stats().get("x509_ca", 0)
    # HTTPS for PVGIS, the maps and the updates: the system's authorities (on Linux OpenSSL may read a folder of
    # them only when it needs one, and count none here)
    report.add("PASS" if authorities else ("FAIL" if sys.platform == "win32" else "INFO"), "TLS authorities",
               f"{authorities} in the system's store", t)
    for module in ("matplotlib.backends.backend_agg", "pyqtgraph", "scipy.optimize", "shapely", "requests"):
        t = time.perf_counter()
        try:
            __import__(module)
            report.add("PASS", f"import {module}", "", t)
        except ImportError as error:
            report.add("FAIL", f"import {module}", str(error), t)
    for module, what in (("anthropic", "Meridio's cloud model"), ("keyring", "the key in the system's keyring")):
        t = time.perf_counter()
        try:
            __import__(module)
            report.add("PASS", f"import {module}", what, t)
        except ImportError as error:
            report.add("INFO", f"import {module}", f"{what}, not available: {error}", t)


def window(report: Report, folder: Path) -> None:
    """The window offscreen with the sample project, laid, in 3D, computed, reported, grabbed."""
    from PySide6.QtCore import QLocale
    from PySide6.QtWidgets import QApplication

    from .. import APP_ID, APP_NAME, config, i18n, log
    from ..paths import Paths
    from . import qt_translations

    def wait(condition, seconds: float) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return bool(condition())

    t = time.perf_counter()
    QApplication.setApplicationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication.instance() or QApplication([sys.argv[0]])
    paths = Paths.from_env()
    report.check("isolated folders", str(paths.config).startswith(str(folder)), str(paths.config), t)
    log.setup(paths.log_file)
    cfg = config.load(paths.config_file)
    # nothing leaves the PC during the test: no map, no PVGIS, no address, no update
    cfg.network_tiles = cfg.network_pvgis = cfg.network_geocoding = cfg.check_updates = False
    cfg.language = "it"
    i18n.setup("it")
    QLocale.setDefault(QLocale("it"))
    t = time.perf_counter()
    report.check("Qt's words in Italian", qt_translations.install(app, "it"), ", ".join(qt_translations.folders()), t)
    t = time.perf_counter()
    try:            # Meridio's voices: the system's engines (SAPI and WinRT on Windows) and the sound's outputs
        from PySide6.QtMultimedia import QMediaDevices
        from PySide6.QtTextToSpeech import QTextToSpeech
        engines = [e for e in QTextToSpeech.availableEngines() if e != "mock"]
        report.add("PASS" if engines else ("FAIL" if sys.platform == "win32" else "INFO"), "system voices",
                   ", ".join(engines) or "no engine", t)
        t = time.perf_counter()
        outputs = QMediaDevices.audioOutputs()
        report.add("PASS" if outputs else "INFO", "sound outputs", f"{len(outputs)}", t)
    except ImportError as error:
        report.add("FAIL", "system voices", str(error), t)
    synthetic_weather(paths.cache)
    project = sample_project()
    file = folder / "Self-test.meridiana"
    project.save(file)

    t = time.perf_counter()
    from .window import MainWindow
    win = MainWindow(paths, cfg)
    log.tell_with(win.tell_error)
    seen: list[str] = []
    if win.skeleton is not None:
        win.skeleton.gone.connect(seen.append)
    win.resize(1400, 900)
    win.open_path(file)
    win.show()
    report.check("window", wait(lambda: win.isVisible(), 10), f"{win.windowTitle()}", t)

    t = time.perf_counter()
    laid = wait(lambda: any(getattr(r, "count", 0) for r in win.results.values()), 60)
    count = sum(getattr(r, "count", 0) for r in win.results.values())
    report.check("layout", laid, f"{count} modules", t)

    t = time.perf_counter()
    status = win.view3d.status()
    errors = "; ".join(e.toString() for e in win.view3d.errors())
    report.check("3D scene", win.view3d.rootObject() is not None and not errors, f"{status.name} {errors}".strip(), t)
    t = time.perf_counter()
    framed = wait(lambda: bool(seen) or win.skeleton is None, 45)
    # Qt Quick 3D draws only on a 3D graphics API (QRhi: Direct3D, OpenGL, Vulkan), into the picture the view shows
    # (ui/quick_image.py). On the offscreen platform there is none, on Windows too: the view draws nothing and its
    # skeleton goes at once («not drawn»). Offscreen this is said; on a screen (MERIDIANA_SELF_TEST_PLATFORM=windows,
    # the CI's Windows job) the 3D must have its API and its first frame
    from PySide6.QtGui import QGuiApplication
    drawn = win.view3d.drawn()
    rhi = win.view3d.rhi
    offscreen = QGuiApplication.platformName() == "offscreen"
    why = (": the 3D view is not drawn here (offscreen: no graphics device; MERIDIANA_SELF_TEST_PLATFORM=windows "
           "draws it)") if offscreen else ": no 3D graphics API, the 3D view is empty"
    report.add("PASS" if drawn else ("INFO" if offscreen else "FAIL"), "3D graphics",
               (rhi.backendName() if rhi is not None else "none") + ("" if drawn else why), t)
    if drawn:
        report.check("3D first frame", framed and (not seen or seen[0] == "frame"),
                     seen[0] if seen else ("drawn" if framed else "none in 45 s"), t)
    else:
        report.add("INFO" if offscreen else "FAIL", "3D first frame", seen[0] if seen else "none", t)

    t = time.perf_counter()
    win._compute_energy(False)
    computed = wait(lambda: bool(win.energy) and win.energy.get("sim") is not None, 120)
    sim = win.energy.get("sim") if win.energy else None
    detail = (f"{sim.energy_kwh:,.0f} kWh/year from {sim.p_stc_kw:,.1f} kWp" if sim is not None
              else str((win.energy or {}).get("error_sim", "no result")))
    report.check("energy", computed and sim is not None and sim.energy_kwh > 0, detail, t)

    if sim is not None:
        t = time.perf_counter()
        from . import report as pdf
        out = folder / "Self-test.pdf"
        pdf.export_pdf(win.project, win.energy, out, None)
        size = out.stat().st_size if out.exists() else 0
        report.check("PDF report", size > 10_000 and out.read_bytes()[:5] == b"%PDF-", f"{size:,} bytes", t)

    t = time.perf_counter()
    image = win.grab().toImage()
    report.check("window grabbed", not image.isNull() and image.width() > 0,
                 f"{image.width()} x {image.height()}", t)
    shot = os.environ.get(f"{ENV_PREFIX}_SCREENSHOT")
    if shot:                            # the picture of the window for the CI's artifact
        image.save(shot)
    win.hide()                          # not close(): nothing to save, no question to ask
    win.deleteLater()
    app.processEvents()


def main(argv: list[str]) -> int:
    started = time.perf_counter()
    report = Report(argv[0] if argv else None)
    report.line(f"{SLUG} {__version__} self-test, Python {sys.version.split()[0]}, "
                f"{'frozen' if getattr(sys, 'frozen', False) else 'from the sources'}, {sys.platform}")
    folder = Path(tempfile.mkdtemp(prefix=f"{SLUG}-self-test-"))
    isolate(folder)
    import threading
    timer = threading.Timer(LIMIT_S, lambda: (report.add("FAIL", "time", f"more than {LIMIT_S:.0f} s"),
                                              os._exit(3)))
    timer.daemon = True
    timer.start()
    try:
        files(report)
        window(report, folder)
    except Exception:  # noqa: BLE001  the test itself broke: said whole, with its exit code
        report.line("FAIL self-test: " + traceback.format_exc().replace("\n", "\n    "))
        timer.cancel()
        return 2
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    timer.cancel()
    report.line(f"{'PASS' if not report.failed else 'FAIL'} all: {report.failed} failed "
                f"[{time.perf_counter() - started:.2f} s]")
    return 1 if report.failed else 0
