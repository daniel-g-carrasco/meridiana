"""R372 diagnostic harness. Product sources are executed unchanged or patched in memory.

Run with the repository's Python environment. --tree selects a git-archive snapshot.
Timing runs use --mode plain; --profile adds a main-thread sampler and scoped timers.
All interventions are diagnostic ablations, not proposed production implementations.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import functools
import hashlib
import os
from pathlib import Path
import pickle
import sys
import threading
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


class Probe:
    def __init__(self, mode, profile):
        self.mode = mode
        self.profile = profile
        self.gesture = "startup"
        self.thread = threading.get_ident()
        self.samples = defaultdict(Counter)
        self.calls = defaultdict(lambda: defaultdict(list))
        self.events = defaultdict(lambda: defaultdict(lambda: [0, 0.0, 0.0]))
        self.states = []
        self.occurrences = Counter()
        if profile:
            threading.Thread(target=self.sample, daemon=True).start()

    def sample(self):
        while True:
            frame = sys._current_frames().get(self.thread)
            stack = []
            while frame is not None:
                filename = frame.f_code.co_filename.replace("\\", "/")
                if not filename.endswith("probe.py"):
                    stack.append(f"{filename.rsplit('/', 1)[-1]}:{frame.f_lineno}:{frame.f_code.co_name}")
                frame = frame.f_back
            self.samples[self.gesture][" > ".join(stack[:10])] += 1
            time.sleep(0.002)

    def wrap(self, owner, name):
        original = getattr(owner, name, None)
        if original is None:
            return
        label = f"{owner.__name__}.{name}"

        @functools.wraps(original)
        def timed(*args, **kwargs):
            t0 = time.perf_counter()
            gesture = self.gesture
            try:
                return original(*args, **kwargs)
            finally:
                if threading.get_ident() == self.thread:
                    self.calls[gesture][label].append((time.perf_counter() - t0) * 1000)

        setattr(owner, name, timed)

    def install(self):
        from meridiana.ui import cards, charts, checks_page, file_page, motion, plant_page, style, window

        if self.mode == "no-settings":
            file_page.FilePage._read_settings_ahead = lambda self: None
        elif self.mode == "no-motion":
            motion.reduced = lambda: True
        elif self.mode == "no-rest":
            window.REST_BUILD_MS = None
        elif self.mode == "no-tools":
            cards.CardTitle.set_tools = lambda self, tools: tools.hide()
        elif self.mode == "no-arrange":
            window.MainWindow._arrange = lambda self: None
        elif self.mode == "async-plant":
            original_start = window.MainWindow._start_plant
            window.MainWindow._start_plant = lambda self, now=False: original_start(self, now=False)
        elif self.mode == "instant-file-close":
            motion.leave = lambda area, change, ms=None: (change(), None)[1]
        if self.profile:
            for owner, names in (
                (motion, ("picture", "enter", "leave", "hold", "crossfade")),
                (motion.Entrance, ("play",)),
                (file_page.FilePage, ("_read_settings", "_read_settings_ahead", "open_page", "close_page")),
                (charts, ("_draw_next",)),
                (charts.Chart, ("__init__", "_ensure_plot")),
                (cards.CardTitle, ("place", "sizeHint", "paintEvent")),
                (cards.CardDock, ("_fit_now", "paintEvent")),
                (checks_page.ChecksTree, ("drawRow", "resizeEvent", "_width_settled")),
                (checks_page.ChecksPage, ("_buttons", "_fill", "show_items")),
                (plant_page.PlantSide, ("lend", "give_back")),
                (plant_page.PlantInspector, ("show_plant",)),
                (style.FitArea, ("set_area", "content_height")),
                (window.MainWindow, ("_show_inspector", "_tab_changed", "_settle_layouts", "_arrange", "_rest_build",
                                     "_start_plant", "_plant_done", "_energy_done", "_energy_step", "_show_checks")),
            ):
                for name in names:
                    self.wrap(owner, name)
            try:
                from meridiana.ui.lazy_page import LazyPage
            except ImportError:
                pass
            else:
                self.wrap(LazyPage, "real")

    def ready(self, win):
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QWidget

        self.project_summary = {"buildings": len(win.project.buildings), "subfields": len(win.project.subfields),
                                "module_count": sum(r.count for r in win.results.values() if hasattr(r, "count"))}
        assert self.project_summary["subfields"] == 2, self.project_summary
        assert self.project_summary["module_count"] > 0, self.project_summary
        if self.mode == "no-chart-paint":
            from meridiana.ui import charts
            charts.backend().Plot.paintEvent = lambda self, event: None

        if self.mode in ("no-right-paint", "no-plan-paint", "no-checks-paint"):
            area = {"no-right-paint": win.docks[1], "no-plan-paint": win.plan.viewport(),
                    "no-checks-paint": win.checks_page.tree.viewport()}[self.mode]

            class NoPaint(QObject):
                def eventFilter(self, obj, event):
                    return event.type() == QEvent.Type.Paint

            self.filter = NoPaint(win)
            for widget in [area, *area.findChildren(QWidget)]:
                widget.installEventFilter(self.filter)

    def start(self, name, win):
        self.window = win
        self.occurrences[name] += 1
        self.gesture = f"{name} #{self.occurrences[name]}"
        state = {"gesture": self.gesture}
        for attr in ("energy_page", "consumption_page", "economics_page"):
            page = getattr(win, attr)
            state[attr] = page.is_built() if hasattr(type(page), "is_built") else True
        state["widgets"] = len(win.findChildren(__import__("PySide6.QtWidgets", fromlist=["QWidget"]).QWidget))
        state["window_size"] = [win.width(), win.height()]
        state["dock_sizes"] = [[dock.width(), dock.height()] for dock in win.docks]
        state["phase"] = win.phase()
        state["checks"] = len(win.checks_page.items)
        energy = win.energy or {}
        state["energy_ready"] = energy.get("sim") is not None
        state["energy_error"] = energy.get("error_sim")
        state["settings_read"] = getattr(win.file_page, "_settings_read", None)
        from meridiana.ui.charts import LIVE
        state["plots"] = sum(chart.plot is not None for chart in LIVE)
        self.states.append(state)

    def finish(self):
        from meridiana.ui.charts import LIVE
        win = self.window
        self.states[-1]["after"] = {
            "phase": win.phase(), "energy_ready": (win.energy or {}).get("sim") is not None,
            "plots": sum(chart.plot is not None for chart in LIVE),
            "visible_plots": sum(chart.plot is not None and chart.isVisible() for chart in LIVE),
        }
        self.gesture = "between gestures"

    def settle_energy(self, win, pump):
        """Prepare identical UI inputs; cache only the unmeasured core computation.

        The cache is written by this probe from the authorised sample, never an
        external pickle. Its input key must match the current session exactly.
        Window, pages, charts and their Qt state are always created afresh.
        """
        cache = ROOT / "build/speed/energy-result.pkl"
        key = win.session.energy_key()
        hit = cache.exists()
        if hit:
            with cache.open("rb") as stream:
                saved = pickle.load(stream)
            assert saved["key"] == key, "Energy cache inputs changed"
            win.energy_timer.stop()
            win._abandon_year()
            original_plant_soon = win._plant_soon
            win._plant_soon = lambda: None
            try:
                generation = win.session.energy_asked()
                win._energy_done(generation, saved["energy"])
            finally:
                win._plant_soon = original_plant_soon
            win.plant_timer.stop()
            win.plant_generation += 1
            win._plant_done(win.plant_generation, saved["plant"])
        else:
            if (win.energy or {}).get("sim") is None:
                win._compute_energy(fetch=False)
                deadline = time.perf_counter() + 120
                while (win.energy or {}).get("sim") is None and time.perf_counter() < deadline:
                    pump(0.02)
            assert (win.energy or {}).get("sim") is not None, win.energy
            with cache.open("xb") as stream:
                pickle.dump({"key": win.session.energy_key(), "energy": win.energy, "plant": win.plant_state},
                            stream, protocol=pickle.HIGHEST_PROTOCOL)
        assert (win.energy or {}).get("sim") is not None
        assert not win.session.energy_stale()
        self.energy_setup = {"cache_hit": hit, "input_key_sha256": hashlib.sha256(key.encode()).hexdigest(),
                             "cache_sha256": hashlib.sha256(cache.read_bytes()).hexdigest()}
        pump(1.5)

    def notify(self, receiver, event, deliver):
        kind = event.type().name
        if kind not in ("Paint", "UpdateRequest", "Resize", "LayoutRequest", "PolishRequest"):
            return deliver(receiver, event)
        label = f"{kind}:{type(receiver).__name__}:{receiver.objectName()}"
        t0 = time.perf_counter()
        gesture = self.gesture
        try:
            return deliver(receiver, event)
        finally:
            dt = (time.perf_counter() - t0) * 1000
            counts = self.events[gesture][label]
            counts[0] += 1
            counts[1] += dt
            counts[2] = max(counts[2], dt)

    def summary(self):
        return {
            "mode": self.mode, "profile": self.profile, "states": self.states,
            "weather_cache": getattr(self, "weather_cache", None),
            "settled_energy": getattr(self, "settled_energy", False),
            "harness_sha256": getattr(self, "harness_sha256", None),
            "fluidity_sha256": getattr(self, "fluidity_sha256", None),
            "energy_setup": getattr(self, "energy_setup", None),
            "project_summary": getattr(self, "project_summary", {}),
            "samples": {name: counts.most_common(35) for name, counts in self.samples.items()},
            "calls": {name: {key: {"count": len(values), "total_ms": round(sum(values), 2),
                                  "max_ms": round(max(values), 2)} for key, values in calls.items()}
                      for name, calls in self.calls.items()},
            "events": {name: {key: {"count": values[0], "total_ms": round(values[1], 2),
                                     "max_ms": round(values[2], 2)} for key, values in events.items()}
                       for name, events in self.events.items()},
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, default=ROOT)
    parser.add_argument("--revision", default="b59f832")
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--weather-cache", type=Path)
    parser.add_argument("--settled-energy", action="store_true")
    parser.add_argument("--mode", choices=("plain", "no-settings", "no-motion", "no-rest", "no-tools",
                                           "no-arrange", "no-chart-paint", "no-right-paint", "no-plan-paint",
                                           "no-checks-paint", "reset-heartbeat", "async-plant",
                                           "instant-file-close"), default="plain")
    args, fluidity_args = parser.parse_known_args()
    tree = args.tree.resolve()
    sys.path.insert(0, str(tree / "src"))
    os.environ["PYTHONPATH"] = str(tree / "src")
    probe = Probe(args.mode, args.profile)
    probe.weather_cache = str(args.weather_cache) if args.weather_cache else None
    probe.settled_energy = args.settled_energy
    source = (ROOT / "tools/fluidity.py").read_text(encoding="utf-8")
    probe.harness_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    probe.fluidity_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if args.weather_cache:
        source = source.replace('    t0 = time.perf_counter()\n    win = MainWindow(paths, cfg)',
                                '    shutil.copytree(weather_cache, paths.cache, dirs_exist_ok=True)\n'
                                '    t0 = time.perf_counter()\n    win = MainWindow(paths, cfg)')
    if args.profile:
        source = source.replace('    app = QApplication(["fluidity"])',
                                '    class TimedApplication(QApplication):\n'
                                '        def notify(self, receiver, event):\n'
                                '            return probe.notify(receiver, event, super().notify)\n'
                                '    app = TimedApplication(["fluidity"])')
    source = source.replace("    beat = [time.perf_counter()]", "    probe.install()\n    beat = [time.perf_counter()]")
    source = source.replace('        now_measuring["name"], now_measuring["stalls"] = name, []',
                            '        probe.start(name, win)\n        now_measuring["name"], now_measuring["stalls"] = name, []')
    if args.mode == "reset-heartbeat":
        source = source.replace('        t0 = time.perf_counter()\n        action()',
                                '        t0 = time.perf_counter()\n        beat[0] = t0\n        action()')
    source = source.replace('        results.append(row)', '        results.append(row)\n        probe.finish()')
    settle = ''
    if args.settled_energy:
        settle = '    probe.settle_energy(win, pump)\n'
    source = source.replace('    if args.sequence in ("base", "all"):',
                            settle + '    probe.ready(win)\n    if args.sequence in ("base", "all"):')
    source = source.replace('"results": results}', '"probe": probe.summary(), "results": results}')
    source = source.replace('"commit": commit', '"commit": revision')
    sys.argv = [str(tree / "tools/fluidity.py"), *fluidity_args]
    namespace = {"__file__": str(tree / "tools/fluidity.py"), "__name__": "__main__",
                 "probe": probe, "revision": args.revision, "weather_cache": args.weather_cache}
    exec(compile(source, str(tree / "tools/fluidity.py"), "exec"), namespace)


if __name__ == "__main__":
    main()
