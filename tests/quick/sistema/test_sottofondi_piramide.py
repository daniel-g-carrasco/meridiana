"""Study 56, point 4 (R710): the underlays from a pyramid through the image provider `underlay`, decoded on Qt's
loading threads at the side the view needs, within the budget's images; the map's records without the picture's
base64; a change of transparency that keeps the delegates and their textures. Offscreen, a synthetic project."""
import base64
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import _setup
from meridiana.core.compute import resources

setUpModule = _setup.keep_global_state


def jpeg_underlay(uid, side, seed=0):
    """An underlay of `side` px, a noisy JPEG as an orthophoto (a plain colour would decode too fast to tell)."""
    import numpy as np
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QImage
    from meridiana.core.model import underlay
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 256, (side, side, 4), dtype=np.uint8)
    pixels[..., 3] = 255
    image = QImage(pixels.data, side, side, side * 4, QImage.Format.Format_ARGB32).copy()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPG", 90)
    data = base64.b64encode(bytes(buffer.data())).decode("ascii")
    return underlay.placed(uid, f"{uid}.jpg", data, side, side, (0.0, 0.0), 200.0)


class Pyramid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.gui.backend import underlays
        underlays._LEVELS.clear()
        self.addCleanup(underlays._LEVELS.clear)

    def test_the_sides_of_the_pyramid(self):
        from meridiana.core.model.underlay import Underlay
        from meridiana.gui.backend.underlays import levels
        self.assertEqual(levels(Underlay("a", width=4096, height=3000)), [256, 512, 1024, 2048, 4096])
        self.assertEqual(levels(Underlay("b", width=300, height=200)), [256, 300])
        self.assertEqual(levels(Underlay("c", width=100, height=40)), [100])

    def test_a_level_is_decoded_at_its_side_once_and_given_back_when_memory_is_short(self):
        from meridiana.gui.backend import underlays
        u = jpeg_underlay("u1", 1024)
        record = underlays.source_of(u)
        self.assertNotIn(u.image[:100], str(record))                   # the base64 stays in Python
        key = record["source"].rpartition("/")[2]
        before = len(underlays.decoded)
        small = underlays.level(key, 256)
        self.assertEqual((small.width(), small.height()), (256, 256))    # decoded straight at its side
        self.assertEqual(underlays.level(key, 256).cacheKey(), small.cacheKey())     # kept: not decoded again
        self.assertEqual(underlays.level(key, 4096).width(), 1024)       # never more than the picture
        self.assertEqual(len(underlays.decoded) - before, 2)
        self.assertIn(underlays._LEVELS, resources.registered())
        with mock.patch.object(resources, "cache_limit", lambda kind: 1):
            resources.give_back()
        self.assertLessEqual(len(underlays._LEVELS), 1)                  # the last entry of a Cache stays
        self.assertTrue(underlays.level("unknown-key", 256).isNull())


def items(window, name):
    return items_of(window.contentItem(), name)


def items_of(root, name):
    found, todo = [], [root]
    while todo:
        item = todo.pop()
        todo.extend(item.childItems())
        if item.objectName() == name:
            found.append(item)
    return found


class InTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QObject
        from _fixtures import capannone
        from meridiana.gui.application import QuickWindow, create_app
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone("Sottofondi"), Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light'})
        cls.window = cls.host.window
        cls.window.resize(1400, 900)
        cls.window.show()
        cls.host.plan.configureMaps({'offline': True})
        cls.window.showPhase('model')
        cls.window.setProperty('viewMode', 'plan')
        _setup.wait_until(cls.app, lambda: cls.window.findChild(QObject, 'plan') is not None, 60)
        _setup.turn_events(cls.app, 1500)
        cls._levels = {}

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def stalls_until(self, condition, seconds):
        """The gaps above 30 ms of the window's thread until `condition` holds (or `seconds` pass), and whether it
        held."""
        from PySide6.QtCore import QTimer
        beat, gaps = [time.perf_counter()], []

        def tick():
            now = time.perf_counter()
            if now - beat[0] > 0.030:
                gaps.append(round((now - beat[0]) * 1000, 1))
            beat[0] = now
        heart = QTimer()
        heart.setInterval(2)
        heart.timeout.connect(tick)
        heart.start()
        held = _setup.wait_until(self.app, condition, seconds)
        heart.stop()
        return gaps, held

    def shown(self, uid):
        """(the side of the low level loaded, the side of the sharp level loaded) of the underlay `uid`, None while it
        has no delegate. The delegate is looked for once among the window's 7000 items (a walk is 70 ms on the
        window's thread: asked at every turn of a wait, it was what held the window), then only read."""
        levels = self._levels.get(uid)
        if levels is None:
            from PySide6.QtCore import QObject
            plan = self.window.findChild(QObject, 'plan')
            for item in items_of(plan, "underlay"):
                if (item.property("modelData") or {}).get("id") == uid:
                    levels = [next(i for i in item.childItems() if i.objectName() == name)
                              for name in ("underlayLow", "underlayLevel")]
                    self._levels[uid] = levels
                    break
            else:
                return None
        return tuple(level.property("sourceSize").width() for level in levels)

    def plan_centre(self):
        from PySide6.QtCore import QObject, QPointF
        plan = self.window.findChild(QObject, 'plan')
        return plan.mapToScene(QPointF(plan.width() / 2, plan.height() / 2))

    def test_1_a_large_underlay_arrives_decoded_off_the_windows_thread(self):
        from meridiana.gui.backend import underlays
        small = jpeg_underlay("small", 64, seed=2)              # the control: what any underlay arriving costs
        self.host.bridge.session.edit("arrives", lambda p: p.underlays.append(small))
        control, held = self.stalls_until(lambda: (self.shown("small") or (0, 0))[0] == 64, 20)
        self.assertTrue(held, self.shown("small"))
        big = jpeg_underlay("big", 4096, seed=1)
        before = len(underlays.decoded)
        self.host.bridge.session.edit("arrives", lambda p: p.underlays.append(big))
        record = next(r for r in self.host.plan.maps.underlays if r["id"] == "big")
        self.assertLess(len(str(record)), 2000)                           # no base64 to the QML any more
        gaps, held = self.stalls_until(lambda: (self.shown("big") or (0, 0))[1] > 256
                                       and self.shown("big")[0] == 256, 20)
        self.assertTrue(held, f"the two levels never came: {self.shown('big')}")      # the small one under it
        made = underlays.decoded[before:]
        self.assertTrue(made)
        self.assertFalse([d for d in made if d[2]], "a level decoded on the window's thread")
        # after the edit, while the levels load, the window goes on drawing: no gap longer than the control's by
        # more than one frame (offscreen a frame is 30-60 ms of the software renderer on the window's thread; the
        # whole picture decoded there took 650 ms, study 56). On the graphics card: to be tried (study 56, 8).
        self.assertLessEqual(max(gaps, default=0), max(control, default=0) + 60, (gaps, control))

    def test_2_a_zoom_asks_for_its_level_once_it_has_rested(self):
        from meridiana.gui.backend import underlays
        from quick.gestures import wheel
        if self.shown("big") is None:
            self.host.bridge.session.edit("arrives", lambda p: p.underlays.append(jpeg_underlay("big", 4096, 1)))
            _setup.wait_until(self.app, lambda: (self.shown("big") or (0, 0))[1] > 256, 20)
        first = self.shown("big")[1]
        before = len(underlays.decoded)
        centre = self.plan_centre()
        wheel(self.app, self.window, centre, notches=8, dy=120)                  # in: a larger side
        _setup.wait_until(self.app, lambda: self.shown("big")[1] > first, 20)
        self.assertGreater(self.shown("big")[1], first)
        asked = underlays.decoded[before:]
        self.assertLessEqual(len(asked), 2, asked)                    # not one level per notch: once rested
        self.assertFalse([d for d in asked if d[2]])
        bigger = self.shown("big")[1]
        before = len(underlays.decoded)
        wheel(self.app, self.window, centre, notches=8, dy=-120)       # out again: kept, not decoded
        _setup.wait_until(self.app, lambda: self.shown("big")[1] < bigger, 20)
        self.assertLess(self.shown("big")[1], bigger)
        self.assertEqual(underlays.decoded[before:], [])

    def test_3_a_change_of_transparency_keeps_the_delegates(self):
        if self.shown("big") is None:
            self.host.bridge.session.edit("arrives", lambda p: p.underlays.append(jpeg_underlay("big", 4096, 1)))
            _setup.wait_until(self.app, lambda: (self.shown("big") or (0, 0))[1] > 256, 20)
        delegates = items(self.window, "underlay")
        self.host.plan.underlays.action("big", "opacity", 0.3)
        _setup.turn_events(self.app, 300)
        after = items(self.window, "underlay")
        from shiboken6 import getCppPointer
        self.assertEqual([getCppPointer(d) for d in after], [getCppPointer(d) for d in delegates])   # not made again
        mine = next(d for d in after if d.property("modelData").get("id") == "big")
        self.assertAlmostEqual(mine.property("opacity"), 0.3, 3)


if __name__ == "__main__":
    unittest.main()
