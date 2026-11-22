"""The sun map as a job of the common mechanism (study 45, package 4; study 48): the real job through the Center, in
real processes, on a small project without the network. The plan first, the preview at 2 m before the finest tiles,
the figures of irradiance_map called directly, the store that serves a second request without casting again, Cancel
that reaches the computation, a change of the project halfway (the surface not touched keeps its figures, the one
touched is to be updated until its new ones come), two processes that share the surfaces, a clear failure without
the weather. Every test closes its center and checks that no process is left."""

import os
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

import _setup  # noqa: F401  (src on the path)
from _fixtures import FakePvgis, clear_sky_meteo, mixed, write_cache

from meridiana.app import irradiance_job as ij
from meridiana.app import jobs, pipeline, weather_job
from meridiana.app.session import ProjectSession
from meridiana.app.sun_map import SunMap, round_edges
from meridiana.app.work.center import Center
from meridiana.core.energy import irradiance_map as im
from meridiana.core.energy import meteo, system
from meridiana.core.energy.simulate import _first_pass
from meridiana.i18n import _

POLL = 0.02


def alive(pid) -> bool:
    if pid is None:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def project():
    """The shed of Rho (flat roof: parapet, smoke vent, plant; modules laid) and the gable house with its chimney and
    its modules: the mixed project without the villa, the shelter and the tree, so that the job is short."""
    p = mixed()
    p.buildings = [b for b in p.buildings if b.id in ("b1", "b9")]
    p.exclusions = [e for e in p.exclusions if e.id != "e9"]
    return p


ONE = replace(ij.KIND, processes=1)
TWO = replace(ij.KIND, processes=2)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.weather = Path(cls.folder.name) / "weather"
        write_cache(clear_sky_meteo(), cls.weather)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        self.posted = threading.Event()
        self.center = Center(self.posted.set)
        self.pids = []
        self.addCleanup(self.no_process_left)
        self.addCleanup(self.center.close)
        self.store = Path(tempfile.mkdtemp(dir=self.folder.name, prefix="store-"))

    def until(self, condition, seconds=120.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.posted.clear()
            self.center.pump()
            for proc in self.center.runner.all_processes():
                for pid in (proc.popen.pid if proc.popen is not None else None, proc.pid):
                    if pid is not None and pid not in self.pids:
                        self.pids.append(pid)
            if condition():
                return True
            self.posted.wait(POLL)
        return condition()

    def no_process_left(self):
        gone = threading.Event()
        end = time.monotonic() + 5
        while time.monotonic() < end and any(alive(p) for p in self.pids):
            gone.wait(POLL)
        self.assertEqual([p for p in self.pids if alive(p)], [], "processes left after close()")

    def submit(self, request, kind=ONE):
        got = {"events": [], "done": [], "failed": []}
        handle = self.center.submit(kind, request,
                                    on_partial=lambda k, d: got["events"].append((k, d)),
                                    on_done=lambda r, stale: got["done"].append(r),
                                    on_failed=lambda k, text: got["failed"].append(text))
        return handle, got

    def request(self, p, **more):
        return ij.request_of(p.to_json(), self.weather, self.store, **more)


class TheJob(Base):
    def test_the_plan_then_the_preview_then_the_finest_the_figures_of_the_core(self):
        p = project()
        handle, got = self.submit(self.request(p))
        self.assertTrue(self.until(lambda: got["done"] or got["failed"]), got["failed"])
        self.assertEqual(got["failed"], [])
        events = got["events"]
        self.assertEqual(events[0][0], ij.PLAN, "the plan comes first")
        plan = events[0][1]
        ids = [s["id"] for s in plan["surfaces"]]
        self.assertEqual(set(ids), {"b1:0", "b9:0", "b9:2"})
        levels = [(k, d) for k, d in events if k in ids]
        coarse = [k for k, d in levels if not d["fine"]]
        fine = [k for k, d in levels if d["fine"]]
        self.assertEqual(sorted(coarse), sorted(ids))
        self.assertEqual(sorted(fine), sorted(ids))
        last_coarse = max(i for i, (k, d) in enumerate(events) if k in ids and not d["fine"])
        first_fine = min(i for i, (k, d) in enumerate(events) if k in ids and d["fine"])
        self.assertLess(last_coarse, first_fine, "every preview before the first finest level")
        # the figures of irradiance_map called directly, to the bit
        m = pipeline.weather_of(p, self.weather)
        light = im.prepare(m, system.losses_of(p))
        results = {k: r for k, r in jobs.layout_of(p)[0].items() if not isinstance(r, Exception)}
        by_id = {s["id"]: s for s in plan["surfaces"]}
        for s in im.surfaces_of(p, results):
            with self.subTest(surface=s.id):
                fine_grid, coarse_grid = im.grid_of(s, 0.5), im.grid_of(s, 2.0)
                shadows = im.cast_surface(light, s, coarse_grid)
                reader = im.surface_reader(light, s)
                want = {False: im.read(light, reader, shadows, coarse_grid), True: im.read(light, reader, shadows, fine_grid)}
                self.assertEqual(by_id[s.id]["key"], im.key_of(light, s, fine_grid))
                for _k, d in [(k, d) for k, d in levels if k == s.id]:
                    for name in ("year", "loss", "hours"):
                        self.assertEqual(d[name].dtype, np.float32)
                        self.assertTrue(np.array_equal(d[name], getattr(want[d["fine"]], name), equal_nan=True), name)
                    self.assertEqual(d["free"], want[d["fine"]].free)
                    self.assertTrue(np.array_equal(d["inside"], (fine_grid if d["fine"] else coarse_grid).inside))
        self.assertGreater(float(np.nanmax(next(d for k, d in levels if k == "b1:0" and d["fine"])["loss"])), 1.0)
        # the modules: the year's light after the rows, cast the light way, as module_values gives them
        modules = next(d for k, d in events if k == ij.MODULES)
        self.assertEqual(modules["key"], plan["modules"])
        arrays = system.arrays_of(p, results)
        first = _first_pass(m, arrays, None, replace(system.losses_of(p), use_near=False), None)
        for ap, a in zip(first.per_array, modules["arrays"], strict=True):
            values = im.module_values(light, ap)
            self.assertEqual(a["keys"], [str(k) for k in values.keys])
            self.assertTrue(np.array_equal(a["loss"], values.loss.astype(np.float32)))
        self.assertEqual({a["surface"] for a in modules["arrays"]}, {"b1:0", "b9:0"})
        self.assertEqual(got["done"][0]["cast"], 3)
        self.assertEqual(handle.state, "done")
        self.assertGreater(handle.peak_memory, 0)

        # a second request: everything from the store, nothing cast or read again
        again, got2 = self.submit(self.request(p))
        self.assertTrue(self.until(lambda: got2["done"] or got2["failed"]), got2["failed"])
        counts = got2["done"][0]
        self.assertEqual((counts["cast"], counts["read"], counts["stored"], counts["modules"]), (0, 0, 3, 2))
        stored = [d for k, d in got2["events"] if k in ids]
        self.assertTrue(all(d["fine"] and d["stored"] for d in stored))
        # and the keys the window has are not even sent
        third, got3 = self.submit(self.request(p, have={s["key"] for s in plan["surfaces"]} | {plan["modules"]}))
        self.assertTrue(self.until(lambda: got3["done"]))
        self.assertEqual(got3["done"][0]["skipped"], 3)
        self.assertEqual([k for k, _d in got3["events"] if k not in (ij.PLAN,)], [])

    def test_two_processes_do_every_surface_once(self):
        with mock.patch.dict(os.environ, {"MERIDIANA_WORKERS": "2"}):
            handle, got = self.submit(self.request(project()), kind=TWO)
            self.assertTrue(self.until(lambda: got["done"] or got["failed"]), got["failed"])
        counts = got["done"][0]
        self.assertEqual(len(counts), 2, "a result for each process")
        self.assertTrue(all(c["read"] > 0 for c in counts), counts)
        self.assertEqual(sum(c["read"] for c in counts), 3)
        self.assertEqual(sum(c["modules"] for c in counts), 2)
        fine = [k for k, d in got["events"] if isinstance(d, dict) and d.get("fine")]
        self.assertEqual(sorted(fine), ["b1:0", "b9:0", "b9:2"], "each surface once")

    def test_cancel_reaches_the_computation_and_the_process_stays_warm(self):
        handle, got = self.submit(self.request(project()))
        self.assertTrue(self.until(lambda: any(k == "b9:2" or k == "b9:0" for k, _d in got["events"])))
        self.center.cancel(handle)
        self.assertEqual(handle.state, "cancelled")
        self.assertEqual(self.center.rows(), [])
        procs = self.center.runner.processes()
        self.assertEqual(len(procs), 1)
        # stopped within the grace by the computation's own checkpoint, not killed: idle and warm
        self.assertTrue(self.until(lambda: procs[0].run is None, 2.0), "the job heard the stop")
        self.until(lambda: False, 0.5)
        self.assertTrue(procs[0].alive)
        seen = len(got["events"])
        self.until(lambda: False, 0.5)
        self.assertEqual(len(got["events"]), seen, "nothing more after Cancel")
        self.assertEqual(got["done"], [])

    def test_without_the_weather_a_clear_failure(self):
        empty = Path(tempfile.mkdtemp(dir=self.folder.name, prefix="empty-"))
        handle, got = self.submit(ij.request_of(project().to_json(), empty, self.store))
        self.assertTrue(self.until(lambda: got["failed"] or got["done"]))
        self.assertEqual(handle.state, "failed")
        self.assertEqual(got["failed"], [_("The weather of the site is not on this PC and PVGIS is off in Settings > "
                                           "Privacy: turn it on there to fetch it.")])
        self.assertEqual([k for k, _d in got["events"]], [])
        self.assertEqual(list(self.store.iterdir()), [])

    def test_without_the_weather_that_may_be_fetched_it_says_so_at_once(self):
        # the decision is the job's, in its process: nothing sent, nothing kept, the site said for the owner
        empty = Path(tempfile.mkdtemp(dir=self.folder.name, prefix="empty-"))
        handle, got = self.submit(ij.request_of(project().to_json(), empty, self.store, network=True))
        self.assertTrue(self.until(lambda: got["failed"] or got["done"]))
        self.assertEqual(got["failed"], [])
        self.assertEqual(got["done"], [{"missing": ij.WEATHER, "site": (45.5226, 9.03)}])
        self.assertEqual([k for k, _d in got["events"]], [])
        self.assertEqual(list(self.store.iterdir()), [])
        self.assertEqual(list(empty.iterdir()), [], "nothing fetched by the map's job")


class TheMap(Base):
    def setUp(self):
        super().setUp()
        self.session = ProjectSession(project())
        jobs_results, keys, _laid = jobs.layout_of(self.session.project)
        self.session.layout_done(self.session.generation, jobs_results, keys)
        self.session.subscribe(self.center.changed)
        self.map = SunMap(self.center, self.session, self.weather, self.store)
        self.addCleanup(self.map.close)
        self.told = []
        self.map.subscribe(self.told.append)

    def finished(self):
        return not self.map.busy and (self.map.done or bool(self.map.error))

    def test_a_change_keeps_what_it_did_not_touch_and_marks_what_it_did(self):
        sm = self.map
        sm.set_on(True)
        self.assertTrue(self.until(self.finished), sm.error)
        self.assertEqual(sm.error, "")
        self.assertEqual(set(sm.surfaces), {"b1:0", "b9:0", "b9:2"})
        self.assertTrue(all(s.fine and not s.stale for s in sm.surfaces.values()))
        self.assertEqual(set(sm.modules), {"b1:0", "b9:0"})
        roof = sm.surfaces["b1:0"]
        keys = {sid: s.key for sid, s in sm.surfaces.items()}
        # the quantity, the colours, the classes: nothing computed
        handle = sm.handle
        classes = sm.classes_of("b1:0")
        self.assertEqual(classes.dtype, np.uint8)
        self.assertEqual(classes.shape, sm.level_of("b1:0")["shape"])
        sm.set_quantity("year")
        self.assertIs(sm.handle, handle)
        self.assertEqual(self.center.rows(), [])
        legend = sm.legend()
        self.assertEqual(legend["unit"], "kWh/m²")
        self.assertEqual(sm.layers("b1:0"), (False, True), "kWh/m² on a roof with tilted rows: only the modules")
        self.assertEqual(sm.layers("b9:0"), (True, True), "modules flat on the pitch: one plane")
        self.assertEqual(sm.layers("b9:2"), (True, False))
        self.assertEqual(legend["planes"], ["plane of the pitch", "plane of the modules"])
        level = sm.level_of("b1:0")
        self.assertGreaterEqual(float(np.nanmin(level["year"])), legend["edges"][0])
        self.assertLessEqual(float(np.nanmax(level["year"])), legend["edges"][-1])
        sm.set_quantity("loss")
        self.assertEqual(sm.legend()["edges"], im.LOSS_CLASSES)
        self.assertEqual(sm.layers("b1:0"), (True, True), "the loss: the modules and the roof under them")
        # the value under the pointer, from the plan's coordinates of a tile's centre
        i, j = np.argwhere(np.isfinite(level["loss"]))[len(np.argwhere(np.isfinite(level["loss"]))) // 2]
        x0, y0, ax, ay, bx, by = roof.transform(level)
        x, y = x0 + (j + 0.5) * ax + (i + 0.5) * bx, y0 + (j + 0.5) * ay + (i + 0.5) * by
        value = sm.value_at(x, y)
        self.assertEqual(value["surface"], "b1:0")
        self.assertAlmostEqual(value["loss"], float(level["loss"][i, j]), places=5)
        self.assertIsNone(sm.value_at(-100.0, -100.0))
        # the chimney of the house moves on its northern pitch: that pitch to update; the southern pitch (shaded by
        # the shed, not by the chimney) and the shed (higher, far) untouched
        self.told.clear()

        def move(p):
            e = next(x for x in p.exclusions if x.id == "e10")
            e.ring = [[q[0] + 1.0, q[1]] for q in e.ring]
        changed = time.monotonic()
        self.session.edit("Move the chimney", move)
        self.assertTrue(sm.busy, "asked again, after the quiet")
        self.assertTrue(sm.changing, "at once every surface may be old: the views dim them until the plan comes")
        self.assertIn({"*"}, self.told, "the views told at once")
        self.assertTrue(self.until(lambda: sm.surfaces["b9:2"].key != keys["b9:2"], 60))
        self.assertFalse(sm.changing, "the plan came: it says which surfaces keep their map")
        self.assertGreaterEqual(time.monotonic() - changed, ij.KIND.settle * 0.9, "not before the quiet")
        for sid in ("b1:0", "b9:0"):
            self.assertEqual(sm.surfaces[sid].key, keys[sid])
            self.assertFalse(sm.surfaces[sid].stale)
            self.assertTrue(sm.surfaces[sid].fine)
        stale_seen = sm.surfaces["b9:2"].stale
        self.assertTrue(self.until(self.finished), sm.error)
        self.assertFalse(any(s.stale for s in sm.surfaces.values()))
        counts = {k: sum(c[k] for c in sm.counts) for k in sm.counts[0]}      # over the processes
        self.assertEqual(counts["skipped"], 2, "the surfaces not touched are not computed again")
        self.assertEqual((counts["read"], counts["cast"]), (1, 1))
        self.assertTrue(stale_seen, "the pitch touched was to update until its figures came")
        self.assertIn({"b9:2"}, self.told, "its listeners told for that surface alone")
        # halfway: another move while the job runs; it restarts after the quiet and ends with the plan of the last
        self.session.edit("Move the chimney", move)
        self.assertTrue(self.until(lambda: sm.handle.state == "running", 30))
        plan = sm.plan_id
        self.session.edit("Move the chimney", move)
        self.assertEqual(sm.handle.state, "settling")
        self.assertTrue(self.until(self.finished), sm.error)
        self.assertEqual(sm.error, "")
        self.assertNotEqual(sm.plan_id, plan, "the plan of the last change")
        self.assertFalse(any(s.stale for s in sm.surfaces.values()))
        self.assertTrue(all(s.fine for s in sm.surfaces.values()))
        self.assertEqual(sum(c["skipped"] for c in sm.counts), 2)
        # off: the job cancelled
        self.session.edit("Move the chimney", move)
        self.assertTrue(sm.busy)
        sm.set_on(False)
        self.assertFalse(sm.busy)
        self.assertEqual(self.center.rows(), [])

    def test_without_the_weather_one_sentence(self):
        empty = Path(tempfile.mkdtemp(dir=self.folder.name, prefix="empty-"))
        sm = SunMap(self.center, self.session, empty, self.store)
        self.addCleanup(sm.close)
        sm.set_on(True)
        self.assertTrue(self.until(lambda: bool(sm.error)))
        self.assertEqual(sm.error, _("The weather of the site is not on this PC and PVGIS is off in Settings > "
                                     "Privacy: turn it on there to fetch it."))
        self.assertEqual(sm.surfaces, {})
        self.assertIsNone(sm.weather_handle, "no network asked without the settings' switch")


NETWORK = SimpleNamespace(network_pvgis=True)      # the settings' switch of PVGIS on (Config's default)
MAP_S = 600.0       # a whole map from nothing, the light prepared with the horizon: 110 s seen on a loaded PC


class TheWeather(Base):
    """Without the weather of the site the map fetches it by itself (Daniel, 14/11/2026): the weather's job of the
    Center (a thread: the network faked, FakePvgis), then the map, the same as with the weather in the cache; the
    year's consent; a network that fails; Cancel; the site moved halfway."""

    def setUp(self):
        super().setUp()
        self.session = ProjectSession(project())
        results, keys, _laid = jobs.layout_of(self.session.project)
        self.session.layout_done(self.session.generation, results, keys)
        self.session.subscribe(self.center.changed)
        self.told = []
        self.center.tell = self.told.append                 # the status bar's sentence (gui/backend/work.py)
        self.cache = Path(tempfile.mkdtemp(dir=self.folder.name, prefix="cache-"))

    def sun(self, cache=None, settings=NETWORK) -> SunMap:
        store = Path(tempfile.mkdtemp(dir=self.folder.name, prefix="store-"))
        sm = SunMap(self.center, self.session, cache or self.cache, store, settings)
        self.addCleanup(sm.close)
        return sm

    @staticmethod
    def finished(sm):
        return not sm.busy and (sm.done or bool(sm.error))

    def until(self, condition, seconds=MAP_S) -> bool:
        return super().until(condition, seconds)

    def test_the_weather_is_fetched_then_the_map_comes_as_with_it_in_the_cache(self):
        site = (45.5226, 9.03)
        with FakePvgis() as pvgis:
            sm = self.sun()
            sm.set_on(True)
            self.assertTrue(self.until(lambda: sm.weather_handle is not None), "the map's job found it missing")
            self.assertEqual(sm.surfaces, {}, "nothing of the map before its weather")
            self.assertTrue(sm.busy)
            self.assertIn("Weather of the site", [r["title"] for r in self.center.rows()], "its row in the bar")
            self.assertTrue(self.until(lambda: self.finished(sm)), sm.error)
            self.assertEqual(sm.error, "")
            self.assertEqual(self.told, [])
            fetched = [url.rsplit("/", 1)[-1] for url, _p in pvgis.asked]
            self.assertEqual(fetched, ["tmy", "printhorizon"], "the typical year and the horizon, once each")
            # the year finds them: the same functions, the same cache, the same keys
            p = self.session.project
            self.assertTrue(pipeline.weather_at_hand(p, self.cache))
            self.assertIsNotNone(pipeline.horizon_of(p, self.cache, fetch=False))
            self.assertTrue(meteo.cached(*site, self.cache) and meteo.cached(*site, self.cache, "horizon"))
            # turned on again: from the cache, nothing asked of the network
            sm.set_on(False)
            sm.set_on(True)
            self.assertTrue(self.until(lambda: self.finished(sm)), sm.error)
            self.assertEqual(len(pvgis.asked), 2)
            # the same map as with the weather in the cache before: the year's own fetch of the same answers
            ready = Path(tempfile.mkdtemp(dir=self.folder.name, prefix="ready-"))
            meteo.typical_year(*site, ready)
            meteo.horizon(*site, ready)
        again = self.sun(ready, settings=None)
        again.set_on(True)
        self.assertTrue(self.until(lambda: self.finished(again)), again.error)
        self.assertIsNone(again.weather_handle)
        self.assertEqual(again.plan_id, sm.plan_id)
        self.assertEqual(set(again.surfaces), set(sm.surfaces))
        for sid in sm.surfaces:
            with self.subTest(surface=sid):
                a, b = sm.level_of(sid), again.level_of(sid)
                self.assertTrue(a["fine"] and b["fine"])
                for name in ("year", "loss", "hours"):
                    self.assertTrue(np.array_equal(a[name], b[name], equal_nan=True), name)
                self.assertEqual(a["free"], b["free"])
        self.assertEqual(sm.modules_key, again.modules_key)

    def test_a_network_that_fails_is_one_sentence_and_no_map(self):
        with FakePvgis(fail=True) as pvgis:
            sm = self.sun()
            sm.set_on(True)
            self.assertTrue(self.until(lambda: self.finished(sm)))
            sentence = _("The weather of the site could not be fetched from PVGIS: check the network and try again.")
            self.assertEqual(sm.error, sentence)
            self.assertEqual(self.told, [sentence], "one sentence in the status bar")
            self.assertEqual(sm.surfaces, {})
            asked = len(pvgis.asked)
            self.assertEqual(asked, 2, "PVGIS 5.3 and then 6, once each")
            self.until(lambda: False, 1.0)
            self.assertEqual(len(pvgis.asked), asked, "no round of retries")
            self.assertFalse(sm.busy)
            self.assertEqual(self.center.rows(), [])
        self.assertFalse(meteo.cached(45.5226, 9.03, self.cache))

    def test_cancel_during_the_fetch_and_the_map_does_not_start(self):
        with FakePvgis() as pvgis:
            pvgis.hold(45.5226)
            sm = self.sun()
            sm.set_on(True)
            self.assertTrue(self.until(pvgis.waiting.is_set), "the fetch is on its way")
            map_job, weather = sm.handle, sm.weather_handle
            row = next(r for r in self.center.rows() if r["title"] == "Weather of the site")
            self.assertTrue(row["cancellable"])
            self.center.find(row["id"]).cancel()            # the bar's Cancel
            self.assertEqual(weather.state, "cancelled")
            self.assertFalse(sm.busy)
            pvgis.release()
            self.until(lambda: False, 1.5)
            self.assertIs(sm.handle, map_job, "no map asked after the Cancel")
            self.assertEqual(map_job.state, "done")
            self.assertEqual(sm.surfaces, {})
            self.assertEqual(self.center.rows(), [])
            self.assertEqual((sm.error, self.told), ("", []), "Cancel is not an error")

    def test_the_site_moved_halfway_the_old_weather_stays_the_map_is_of_the_new_site(self):
        old, new = (45.5226, 9.03), (45.5326, 9.03)
        with FakePvgis() as pvgis:
            pvgis.hold(old[0])
            sm = self.sun()
            sm.set_on(True)
            self.assertTrue(self.until(pvgis.waiting.is_set), "the fetch for the old site is on its way")
            weather = sm.weather_handle

            def move(p):
                p.site.lat = new[0]
            self.session.edit("Move the site", move)
            self.assertEqual(weather.state, "settling", "the weather's job restarts after the quiet (on_change)")
            self.assertTrue(self.until(lambda: any(params.get("lat") == new[0] for _u, params in pvgis.asked), 30),
                            "fetched again for the new site")
            pvgis.release()
            self.assertTrue(self.until(lambda: self.finished(sm)), sm.error)
            self.assertEqual(sm.error, "")
            self.assertTrue(self.until(lambda: meteo.cached(*old, self.cache), 30),
                            "what was fetched for the old site stays in the cache")
            self.assertTrue(meteo.cached(*new, self.cache))
            self.assertEqual(sum(1 for url, params in pvgis.asked if url.endswith("tmy") and params["lat"] == old[0]), 1,
                             "the old site's fetch not asked again")
            self.assertTrue(sm.surfaces and all(s.fine for s in sm.surfaces.values()))
        # the map is the new site's (its weather says the site asked: FakePvgis), not the old one's
        p = self.session.project
        self.assertEqual((p.site.lat, p.site.lon), new)
        results = {k: r for k, r in jobs.layout_of(p)[0].items() if not isinstance(r, Exception)}

        def keys(lat):
            q = project()
            q.site.lat = lat
            light = im.prepare(pipeline.weather_of(q, self.cache), system.losses_of(q),
                               pipeline.horizon_of(q, self.cache, fetch=False))
            return {s.id: im.key_of(light, s, im.grid_of(s, ij.FINE)) for s in im.surfaces_of(p, results)}
        self.assertNotEqual(keys(old[0]), keys(new[0]))
        self.assertEqual({sid: s.key for sid, s in sm.surfaces.items()}, keys(new[0]))

    def test_without_the_consent_one_sentence_and_no_network(self):
        reserved = _("The weather of the site is not on this PC and this project is reserved: allow PVGIS weather "
                     "in its Properties to fetch it.")
        off = _("The weather of the site is not on this PC and PVGIS is off in Settings > Privacy: turn it on there "
                "to fetch it.")
        with FakePvgis() as pvgis:
            sm = self.sun(settings=SimpleNamespace(network_pvgis=False))
            sm.set_on(True)
            self.assertTrue(self.until(lambda: self.finished(sm)))
            self.assertEqual(sm.error, off)
            self.session.edit("Reserved", lambda p: setattr(p, "reserved", True))
            sm2 = self.sun()
            sm2.set_on(True)
            self.assertTrue(self.until(lambda: self.finished(sm2)))
            self.assertEqual(sm2.error, reserved)
            self.assertEqual(self.told, [off, reserved])
            self.assertEqual(pvgis.asked, [], "nothing asked of the network")
            self.assertIsNone(sm.weather_handle)
            self.assertIsNone(sm2.weather_handle)
        # with the project's own consent it may (the year's rule, Project.online_allowed)
        p = self.session.project
        self.assertEqual(weather_job.refusal(p, True), reserved)
        p.network_consent = {"pvgis": "2026-11-14"}
        self.assertEqual(weather_job.refusal(p, True), "")
        self.assertEqual(weather_job.refusal(p, False), off)


class RoundEdges(unittest.TestCase):
    def test_round_steps_that_hold_the_figures(self):
        self.assertEqual(round_edges(904.5, 1892.9), (800.0, 1000.0, 1200.0, 1400.0, 1600.0, 1800.0, 2000.0))
        self.assertEqual(round_edges(0.0, 9.2), (0.0, 2.0, 4.0, 6.0, 8.0, 10.0))
        self.assertEqual(round_edges(3.1, 3.4), (3.1, 3.15, 3.2, 3.25, 3.3, 3.35, 3.4))
        for low, high in ((0.0, 1.0), (1200.0, 1210.0), (12.0, 980.0), (0.3, 8.7)):
            edges = round_edges(low, high)
            self.assertLessEqual(len(edges) - 1, 6)
            self.assertLessEqual(edges[0], low)
            self.assertGreaterEqual(edges[-1], high)


if __name__ == "__main__":
    unittest.main()
