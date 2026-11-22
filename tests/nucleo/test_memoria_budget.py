"""Study 56, point 3 (R435): the budget's shares, a budget that counts what the caches hold (it no longer shrinks by
itself), one place that makes every cache give memory back when the machine gets short, and the prudence of a PC
with 8 GB. The machine's memory is made up (system_memory, memory_is_short)."""
import os
import threading
import unittest
from unittest import mock

import _setup
from meridiana.core.compute import resources

GIB, MIB = resources.GIB, resources.MIB
setUpModule = _setup.keep_global_state         # configure() writes MERIDIANA_MEMORY_MODE


class Machine:
    """A PC of `total` bytes with `free` bytes free before Meridiana's caches: what they hold is not available."""

    def __init__(self, total, free, short=False):
        self.total, self.free, self.short = total, free, short
        self.held = resources.held          # the bytes really held, whatever the budget is told

    def memory(self):
        return self.total, max(0, self.free - self.held())

    def patch(self):
        return (mock.patch.object(resources, "system_memory", self.memory),
                mock.patch.object(resources, "memory_is_short", lambda: self.short))


class Base(unittest.TestCase):
    def setUp(self):
        resources.configure("auto")
        self.addCleanup(resources.configure, "auto")
        # only this test's caches: those of the other tests of the process counted for nothing
        saved = dict(resources._CACHES)
        resources._CACHES.clear()
        self.addCleanup(lambda: (resources._CACHES.clear(), resources._CACHES.update(saved)))
        look = dict(resources._LOOK)
        self.addCleanup(lambda: resources._LOOK.update(look))
        resources._LOOK.update(budget=None, short=False)

    def machine(self, *args, **kwargs):
        machine = Machine(*args, **kwargs)
        for patch in machine.patch():
            patch.start()
            self.addCleanup(patch.stop)
        return machine


def size(value):
    """The values of these caches are their size: nothing is allocated."""
    return value


class Shares(Base):
    def test_the_shares_of_the_study_and_the_old_names(self):
        self.assertEqual(resources.CACHE_SHARES,
                         {"shading": 0.25, "network": 0.10, "images": 0.12, "plan": 0.05, "models": 0.15})
        self.assertEqual(resources.CACHE_SHARES_ALL,
                         {"shading": 0.35, "network": 0.15, "images": 0.15, "plan": 0.08, "models": 0.20})
        self.machine(32 * GIB, 20 * GIB)
        self.assertEqual(resources.cache_limit("tiles"), resources.cache_limit("images"))   # plan_tiles asks «tiles»
        self.assertEqual(resources.cache_limit("images"), int(18 * GIB * 0.12))
        resources.configure("all")
        self.assertEqual(resources.cache_limit("models"), int(19 * GIB * 0.20))


class Counted(Base):
    def test_a_budget_that_counts_what_is_held_does_not_shrink_by_itself(self):
        # before: the caches full, the budget fell to S/(1+S) of the free memory; now it stays where it was
        self.machine(32 * GIB, 20 * GIB)
        caches = [resources.Cache(lambda k=kind: resources.cache_limit(k), size) for kind in ("shading", "network")]
        start = resources.budget().bytes()
        for _round in range(30):                        # every cache filled again and again up to its limit
            for cache in caches:
                cache.put(_round, 256 * MIB)
        self.assertEqual(resources.budget().bytes(), start)
        self.assertGreater(resources.held(), 0.30 * start)             # 0,25 + 0,10 of the budget, nearly
        with mock.patch.object(resources, "held", lambda: 0):           # what the budget was before
            self.assertLess(resources.budget().bytes(), 0.75 * start)

    def test_what_is_held_never_makes_more_than_the_machine(self):
        self.machine(8 * GIB, 8 * GIB)
        kept = resources.Kept(lambda: 8 * GIB, size)
        kept["a"] = 1 * MIB
        with mock.patch.object(resources, "held", lambda: 6 * GIB):
            self.assertEqual(resources.Budget(mode="auto").bytes(), 6 * GIB)    # 8 GB less the reserve, no more
            self.assertEqual(resources.Budget(mode="save").bytes(), int(8 * GIB * resources.SAVE_SHARE))


class GiveBack(Base):
    def test_another_program_takes_memory_and_every_cache_gives_back(self):
        machine = self.machine(32 * GIB, 20 * GIB)
        costly = resources.Cache(lambda: resources.cache_limit("shading"), size)
        images = resources.Kept(lambda: resources.cache_limit("images"), size)
        costly.put("year", 1 * GIB, cost=60)
        for n in range(8):
            costly.put(n, 512 * MIB, cost=0.1)
            images[n] = 256 * MIB
        self.assertFalse(resources.look())               # the first look only sets the mark
        held = resources.held()
        machine.free -= 2 * GIB                          # a little: under the hysteresis, nothing
        self.assertFalse(resources.look())
        machine.free -= 10 * GIB                         # another program took 12 GB: the budget fell by 70 %
        self.assertTrue(resources.look())
        given = resources.give_back()
        self.assertGreater(given, 0)
        self.assertEqual(resources.held(), held - given)
        self.assertLessEqual(costly.bytes(), resources.cache_limit("shading"))
        self.assertLessEqual(images.bytes(), resources.cache_limit("images"))
        self.assertIn("year", costly)                    # the costly result stays
        self.assertFalse(resources.look())               # the new mark: the next look is quiet

    def test_the_system_says_it_is_short_once_and_the_caches_give_back(self):
        machine = self.machine(16 * GIB, 10 * GIB)
        self.assertFalse(resources.look())
        machine.short = True
        self.assertTrue(resources.look())                # a quarter of the budget, and the system said it
        self.assertFalse(resources.look())               # still short: once
        machine.short = False
        self.assertFalse(resources.look())               # back: the mark only goes up

    def test_the_watch_runs_in_a_thread_of_its_own_once(self):
        machine = self.machine(32 * GIB, 20 * GIB)
        cache = resources.Kept(lambda: resources.cache_limit("models"), size)
        for n in range(20):
            cache[n] = 128 * MIB
        trimmed = threading.Event()
        real = cache.trim

        def trim():
            real()
            trimmed.set()
        cache.trim = trim
        self.assertFalse(resources.look())              # the mark of a machine with 20 GB free
        self.addCleanup(lambda: [stop.set() for stop in resources._WATCH] and None)
        self.addCleanup(resources._WATCH.clear)
        with mock.patch.dict(os.environ, {"MERIDIANA_MEMORY_WATCH": "0"}):
            self.assertFalse(resources.watch(0.01))      # off in the tests unless asked
        with mock.patch.object(resources, "_WATCH", []), mock.patch.dict(os.environ, {"MERIDIANA_MEMORY_WATCH": "1"}):
            self.assertTrue(resources.watch(0.01))
            self.assertFalse(resources.watch(0.01))      # once per process
            watcher = next(t for t in threading.enumerate() if t.name == "meridiana-memory-watch")
            self.assertTrue(watcher.daemon)
            machine.free = 4 * GIB
            self.assertTrue(trimmed.wait(5))
            for stop in resources._WATCH:
                stop.set()
        self.assertLessEqual(cache.bytes(), resources.cache_limit("models"))


class Small(Base):
    def test_a_pc_with_8_gb_stays_prudent(self):
        # 8 GB with 3 free: about 1 GB of budget, a little more counting what is held, nothing prepared ahead
        machine = self.machine(8 * GIB, 3 * GIB)
        plan = resources.Kept(lambda: resources.cache_limit("plan"), size)
        for n in range(10):
            plan[n] = 20 * MIB
        self.assertEqual(resources.budget().bytes(), 1 * GIB)          # the 200 MB held are this budget's already
        self.assertEqual(resources.cache_limit("plan"), int(GIB * 0.05))     # 5 % of 1 GB: two scenes of 10 000
        self.assertLessEqual(plan.bytes(), resources.cache_limit("plan"))
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": ""}), \
                mock.patch.object(resources, "on_battery", lambda: False):
            self.assertFalse(resources.preload())
            resources.configure("save")
            self.assertLessEqual(resources.budget().bytes(), int(8 * GIB * resources.SAVE_SHARE))
            self.assertFalse(resources.preload())
            resources.configure("all")
            self.assertEqual(resources.budget().bytes(), 2 * GIB)        # 3 GB less the 1 GB of «all»
            self.assertTrue(resources.preload())
            machine.short = True                         # the system short: a quarter, nothing ahead
            self.assertEqual(resources.budget().bytes(), 2 * GIB // 4)
            self.assertFalse(resources.preload())
            self.assertEqual(resources.cache_limit("plan"), int(GIB // 2 * 0.08))
            resources.configure("auto")
            self.assertEqual(resources.cache_limit("plan"), 32 * MIB)  # 512 MB / 4 x 0,05 under the floor of a share


class KeptAndCache(unittest.TestCase):
    def test_kept_counts_its_bytes_and_lets_the_oldest_go(self):
        limit = [100]
        kept = resources.Kept(lambda: limit[0], len, most=3)
        self.assertEqual(kept, {})
        kept["a"], kept["b"], kept["c"] = b"x" * 40, b"y" * 40, b"z" * 30
        self.assertEqual(list(kept), ["b", "c"])         # over 100 bytes: the oldest went
        kept.get("b")                                    # asked for: now the last to go
        kept["d"], kept["e"] = b"1", b"22"
        self.assertEqual(list(kept), ["b", "d", "e"])    # at most three
        self.assertEqual(kept.bytes(), 43)
        kept["big"] = b"w" * 101                         # larger than the limit alone: not kept
        self.assertNotIn("big", kept)
        self.assertEqual(kept.pop("b"), b"y" * 40)
        self.assertEqual((kept.bytes(), kept.pop("none", None)), (3, None))
        kept["d"] = b"1234"                              # put again: counted once
        self.assertEqual((list(kept), kept.bytes()), (["e", "d"], 6))
        limit[0] = 4
        kept.trim()
        self.assertEqual((list(kept), kept.bytes()), (["d"], 4))
        kept.clear()
        self.assertEqual((kept, kept.bytes()), ({}, 0))
        self.assertIn(kept, resources.registered())

    def test_the_cache_keeps_its_total_and_gives_once(self):
        cache = resources.Cache(lambda: 1000, len)
        cache.put("a", b"x" * 300)
        cache.put("a", b"x" * 200)                       # the same key again: counted once
        cache.put("b", b"y" * 500)
        self.assertEqual(cache.bytes(), 700)
        self.assertEqual(cache.pop("a"), b"x" * 200)
        self.assertEqual((cache.bytes(), cache.pop("a")), (500, None))
        for n in range(400):                             # a trim of many entries: one sort
            cache.put(n, b"z" * 5)
        self.assertLessEqual(cache.bytes(), 1000)


if __name__ == "__main__":
    unittest.main()
