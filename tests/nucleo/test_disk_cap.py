"""The one ceiling of the stores on disk (app/platform/disk_cap.py, study 48 chapter 8): past the ceiling the oldest go
down to the low mark, what is in use and what is young stay, the minimum kept, a file that cannot be taken does not
stop the cleaning, two stores count together, the ceiling from the disk's free space (given, no real disk), the
leases of processes gone; then the real stores: the sun map's after a real job, the IFC geometry of the project open.
Everything in a temporary folder of its own."""

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401  (src on the path)
from _fixtures import capannone, clear_sky_meteo, mixed, write_cache

from meridiana.app import jobs
from meridiana.app.exchange import ifc_cache
from meridiana.app.platform import disk_cap
from meridiana.app.session import ProjectSession
from meridiana.app.sun_map import SunMap
from meridiana.app.work.center import Center

HOUR = 3600.0
SMALL = dict(KEEP=1000, MOST=10 ** 9, FREE_SHARE=0.5, LOW_MARK=0.5, YOUNG=HOUR)   # a ceiling of a few kB


class Base(unittest.TestCase):
    def setUp(self):
        self.before = self.outside()
        self.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name) / "caches"
        self.now = time.time()
        self.addCleanup(lambda: self.assertEqual(self.outside(), self.before, "nothing written outside the test's folder"))
        self.addCleanup(disk_cap._state.clear)

    @staticmethod
    def outside():
        """What the ceiling could leave in the system's temporary folder (the test's folder's parent)."""
        parent = Path(tempfile.gettempdir())
        return sorted(p.name for p in parent.iterdir() if p.name in (disk_cap.STORES, disk_cap.LEASES, disk_cap.MARK))

    def store(self, name="a"):
        return disk_cap.register(self.root / name, self.root)

    def make(self, folder, name, size, hours):
        path = folder / name
        path.write_bytes(b"\x01" * size)
        when = self.now - hours * HOUR
        os.utime(path, (when, when))
        return path

    def left(self, folder):
        return sorted(p.name for p in folder.iterdir() if not p.name.startswith("."))


class Ceiling(Base):
    def test_the_ceiling_from_the_free_space_with_a_minimum_and_a_maximum(self):
        gib = disk_cap.GIB
        self.assertEqual(disk_cap.ceiling(0, 0), int(disk_cap.KEEP / disk_cap.LOW_MARK), "a disk full: the minimum")
        self.assertEqual(disk_cap.ceiling(5 * gib, 0), int(disk_cap.KEEP / disk_cap.LOW_MARK))
        self.assertEqual(disk_cap.ceiling(50 * gib, 0), 5 * gib, "a share of the free space")
        self.assertEqual(disk_cap.ceiling(40 * gib, 10 * gib), 5 * gib, "what the stores hold counts as room")
        self.assertEqual(disk_cap.ceiling(2000 * gib, 0), disk_cap.MOST, "a large disk: the maximum")

    def test_past_the_ceiling_the_oldest_go_down_to_the_low_mark(self):
        a = self.store()
        for n in range(10):
            self.make(a, f"k{n}.npz", 500, hours=2 + n)        # k0 the youngest, k9 the oldest
        with mock.patch.multiple(disk_cap, **SMALL):
            report = disk_cap.clean(self.root, free=0, now=self.now)
        # 5000 bytes, ceiling max(2000, 2500) = 2500, low mark 1250: the eight oldest go
        self.assertEqual(report["ceiling"], 2500)
        self.assertEqual(self.left(a), ["k0.npz", "k1.npz"])
        self.assertEqual((report["used"], report["freed"], report["busy"]), (1000, 4000, 0))
        with mock.patch.multiple(disk_cap, **SMALL):
            again = disk_cap.clean(self.root, free=0, now=self.now)
        self.assertEqual(again["removed"], [], "under the ceiling: nothing at the next write")

    def test_what_is_in_use_stays_even_when_it_is_the_oldest(self):
        a = self.store()
        for n in range(10):
            self.make(a, f"k{n}.npz", 500, hours=2 + n)
        disk_cap.protect(a, "test", {"k9", "k8"}, self.root)
        with mock.patch.multiple(disk_cap, **SMALL):
            disk_cap.clean(self.root, free=0, now=self.now)
        self.assertEqual(self.left(a), ["k8.npz", "k9.npz"], "the two in use stay; the others go down to 1250 bytes")
        disk_cap.protect(a, "test", (), self.root)
        self.assertEqual(disk_cap.in_use(self.root), {}, "let go")

    def test_the_minimum_is_kept_even_on_a_full_disk(self):
        a = self.store()
        for n in range(10):
            self.make(a, f"k{n}.npz", 1000, hours=2 + n)
        with mock.patch.multiple(disk_cap, **{**SMALL, "KEEP": 4000}):
            report = disk_cap.clean(self.root, free=0, now=self.now)
        # 10000 bytes, ceiling max(8000, 5000): over; down to max(KEEP, 4000): four stay, never fewer
        self.assertEqual(self.left(a), ["k0.npz", "k1.npz", "k2.npz", "k3.npz"])
        self.assertEqual(report["used"], 4000)

    def test_young_files_are_never_taken(self):
        a = self.store()
        for n in range(10):
            self.make(a, f"k{n}.npz", 500, hours=0.1 * n)         # all used within the last hour
        with mock.patch.multiple(disk_cap, **SMALL):
            report = disk_cap.clean(self.root, free=0, now=self.now)
        self.assertEqual(len(self.left(a)), 10)
        self.assertEqual(report["removed"], [])

    def test_a_file_that_cannot_be_taken_does_not_stop_the_cleaning(self):
        a = self.store()
        paths = [self.make(a, f"k{n}.npz", 500, hours=2 + n) for n in range(10)]
        if sys.platform == "win32":                 # a file open in another program cannot be deleted on Windows
            held = open(paths[9], "rb")
            self.addCleanup(held.close)
            context = mock.patch.multiple(disk_cap, **SMALL)
        else:                                       # elsewhere the same refusal, as Windows gives it
            real = os.unlink

            def refuse(path):
                if Path(path) == paths[9]:
                    raise PermissionError(13, "in use by another process")
                real(path)
            context = mock.patch.multiple(disk_cap, **SMALL)
            self.addCleanup(mock.patch.stopall)
            mock.patch("os.unlink", refuse).start()
        with context:
            report = disk_cap.clean(self.root, free=0, now=self.now)
        self.assertEqual(report["busy"], 1)
        self.assertIn("k9.npz", self.left(a), "left where it was")
        self.assertEqual(self.left(a), ["k0.npz", "k9.npz"], "the others went on to the low mark")

    def test_two_stores_count_together_and_lose_their_oldest_whichever_they_are(self):
        a, b = self.store("a"), self.store("deeper/b")
        for n in range(5):
            self.make(a, f"a{n}.npz", 500, hours=2 + 2 * n)        # a: 2, 4, 6, 8, 10 hours
            self.make(b, f"b{n}.npz", 500, hours=3 + 2 * n)        # b: 3, 5, 7, 9, 11 hours
        with mock.patch.multiple(disk_cap, **SMALL):
            report = disk_cap.clean(self.root, free=0, now=self.now)
        self.assertEqual(report["ceiling"], 2500, "5000 bytes together, not 2500 each")
        self.assertEqual(self.left(a) + self.left(b), ["a0.npz", "b0.npz"])

    def test_a_group_goes_whole_and_pieces_being_written_are_left(self):
        a = self.store()
        self.make(a, "ifc-old-m3.npz", 2000, hours=9)
        self.make(a, "ifc-old-m3.read-1234.json", 100, hours=8)
        self.make(a, "ifc-new-m3.npz", 900, hours=2)
        self.make(a, ".ifc-new-m3.npz.part.npz", 100, hours=5)      # being written by a reader
        self.make(a, "ifc-x-m3.npz.part.npz", 3000, hours=48)     # left by a crash
        with mock.patch.multiple(disk_cap, **SMALL):
            disk_cap.clean(self.root, free=0, now=self.now)
        # 3100 bytes without the crash's piece, ceiling 2000, low mark 1000: the old model goes, mesh and reading
        self.assertEqual(self.left(a), ["ifc-new-m3.npz"])
        self.assertTrue((a / ".ifc-new-m3.npz.part.npz").exists())

    def test_the_lease_of_a_process_gone_protects_nothing(self):
        a = self.store()
        self.make(a, "k0.npz", 3000, hours=5)
        gone = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True,
                              check=True)
        pid = int(gone.stdout)
        leases = self.root / disk_cap.LEASES
        leases.mkdir()
        (leases / f"{pid}-test.json").write_text(f'{{"pid": {pid}, "store": "a", "groups": ["k0"]}}')
        self.assertEqual(disk_cap.in_use(self.root), {}, "its process ended")
        self.assertEqual(list(leases.iterdir()), [], "and its lease taken away")
        disk_cap.protect(a, "mine", {"k0"}, self.root)
        self.assertEqual(disk_cap.in_use(self.root), {"a": {"k0"}})

    def test_a_write_counts_and_looks_at_the_disk_only_now_and_then(self):
        a = self.store()
        calls = []
        real = disk_cap.clean

        def counted(root, **kw):
            calls.append(root)
            return real(root, **kw)
        with mock.patch.object(disk_cap, "clean", counted):
            disk_cap.wrote(a, 100, self.root)
            self.assertEqual(len(calls), 1, "the first write of a process looks")
            for _ in range(50):
                disk_cap.wrote(a, 100, self.root)
            self.assertEqual(len(calls), 1, "then it only counts")
            disk_cap.wrote(a, 1 << 40, self.root)
            self.assertEqual(len(calls), 2, "a write past the ceiling looks again")
            disk_cap._state[str(self.root)][2] -= disk_cap.RESCAN + 1
            disk_cap.wrote(a, 1, self.root)
            self.assertEqual(len(calls), 3, "and so does one after RESCAN")


class RealStores(Base):
    def test_the_sun_maps_store_is_registered_and_comes_down_keeping_the_map_in_hand(self):
        weather = Path(self.folder.name) / "weather"
        write_cache(clear_sky_meteo(), weather)
        p = mixed()                         # the gable house alone, with its chimney and its modules: a short job
        p.buildings = [b for b in p.buildings if b.id == "b9"]
        p.exclusions = [e for e in p.exclusions if e.id == "e10"]
        p.subfields = [s for s in p.subfields if s.building == "b9"]
        session = ProjectSession(p)
        results, keys, _laid = jobs.layout_of(session.project)
        session.layout_done(session.generation, results, keys)
        posted = threading.Event()
        center = Center(posted.set)
        self.addCleanup(center.close)
        session.subscribe(center.changed)
        from meridiana.app import irradiance_job as job
        store = job.store_of(self.root)
        sun = SunMap(center, session, weather, store)
        self.addCleanup(sun.close)

        def finished(seconds=600.0):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                posted.clear()
                center.pump()
                if not sun.busy and (sun.done or sun.error):
                    return True
                posted.wait(0.02)
            return False
        sun.set_on(True)
        self.assertTrue(finished(), (sun.error, center.rows()))
        first = set(self.left(store))
        self.assertTrue(first)
        self.assertEqual([name for name, _f in disk_cap.stores(self.root)], ["sun_map"],
                         "registered by the job's own process")
        self.assertTrue(disk_cap.settle_pending())
        in_use = disk_cap.in_use(self.root)["sun_map"]
        self.assertEqual({n.split(".")[0] for n in first}, in_use, "the map in hand declares its files")
        sun.set_day((6, 21))
        self.assertTrue(finished(), sun.error)
        self.assertTrue(disk_cap.settle_pending())
        second = set(self.left(store)) - first
        self.assertTrue(second)
        later = self.now + 3 * HOUR                        # every file is old by then
        with mock.patch.multiple(disk_cap, **{**SMALL, "KEEP": 1, "MOST": 1}):
            report = disk_cap.clean(self.root, free=0, now=later)
        kept = set(self.left(store))
        self.assertTrue(report["removed"])
        self.assertLess(len(kept), len(first | second), "the store came down")
        self.assertTrue(second <= kept, "the levels of the day in hand stay: the open map uses them")
        sun.close()
        self.assertTrue(disk_cap.settle_pending())
        with mock.patch.multiple(disk_cap, **{**SMALL, "KEEP": 1, "MOST": 1}):
            disk_cap.clean(self.root, free=0, now=later)
        self.assertEqual(self.left(store), [], "the map closed: nothing in use")

    def test_the_ifc_geometry_is_registered_and_the_open_projects_model_kept(self):
        ifc = ifc_cache.folder_of(self.root / "quick-profile" / "cache")       # the window's caches, inside the root
        ifc.mkdir(parents=True)
        mine = self.make(ifc, "ifc-aaa-m3.npz", 2000, hours=30)
        self.make(ifc, "ifc-aaa-m3.read-0ae1.json", 200, hours=30)
        self.make(ifc, "ifc-bbb-m3.npz", 2000, hours=5)
        self.make(ifc, "ifc-ccc-m2.npz", 2000, hours=50)
        p = capannone()
        p.resources = dict(p.resources or {}, ifc_reference={"context": {"mesh": str(mine), "triangles": 1}})
        session = ProjectSession(p)
        follow = ifc_cache.Follow(session, ifc, self.root)
        self.addCleanup(follow.close)
        disk_cap.clean_soon(self.root, register_too=(ifc,)).join(10)
        self.assertEqual([name for name, _f in disk_cap.stores(self.root)], ["quick-profile/cache/ifc"])
        self.assertTrue(disk_cap.settle_pending())
        with mock.patch.multiple(disk_cap, **{**SMALL, "KEEP": 1, "MOST": 1}):
            disk_cap.clean(self.root, free=0, now=self.now)
        self.assertEqual(self.left(ifc), ["ifc-aaa-m3.npz", "ifc-aaa-m3.read-0ae1.json"],
                         "the model of the open project stays, mesh and reading, though the oldest")
        self.assertAlmostEqual(os.path.getmtime(mine), self.now - 30 * HOUR, delta=1,
                               msg="its date untouched: the keys made of it hold")
        session.take(capannone("Another"), None, saved=False)          # another project opened, without a model
        self.assertTrue(disk_cap.settle_pending())
        self.assertEqual(disk_cap.in_use(self.root), {}, "let go")
        with mock.patch.multiple(disk_cap, **{**SMALL, "KEEP": 1, "MOST": 1}):
            disk_cap.clean(self.root, free=0, now=self.now)
        self.assertEqual(self.left(ifc), ["ifc-aaa-m3.npz", "ifc-aaa-m3.read-0ae1.json"],
                         "used a moment ago: young by its last declared use")
        with mock.patch.multiple(disk_cap, **{**SMALL, "KEEP": 1, "MOST": 1}):
            disk_cap.clean(self.root, free=0, now=self.now + 2 * HOUR)
        self.assertEqual(self.left(ifc), [])


if __name__ == "__main__":
    unittest.main()
