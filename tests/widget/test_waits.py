"""Waits made visible, one widget at a time (study 16, theme F; task 16f): nothing under 300 ms, an arc past it,
still with less motion, in the text's colour on a faint ring (not the accent, R104); a value to update drawn in the muted text and back; the
catalogue's window open before its catalogue is read, with the arc over the list. The waits of the window (the
values greyed, the arcs of the plan and of the pages, the skeleton, the bars of PVGIS and of the report) are in
finestra/test_waits.py. Here the time itself is what is tested: the events are turned for the milliseconds asked
(_setup.turn_events). PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _setup import turn_events as spin

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Arc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from PySide6.QtWidgets import QWidget

        from meridiana.ui import waiting
        self.host = QWidget()
        self.host.resize(200, 120)
        self.host.show()
        self.spinner = waiting.Spinner(self.host, 48)
        self.spinner.reduced_motion = False
        self.wait = waiting.Delayed(self.spinner)
        self.seen = []
        self.wait.shown.connect(self.seen.append)

    def tearDown(self):
        _setup.dispose(self.host)

    def test_a_wait_of_100_ms_shows_nothing(self):
        self.wait.begin()
        spin(self.app, 100)
        self.assertTrue(self.spinner.isHidden())
        self.wait.end()
        spin(self.app, 400)                                 # the threshold passes after the end: still nothing
        self.assertTrue(self.spinner.isHidden())
        self.assertEqual(self.seen, [])
        self.assertEqual(self.spinner.frames, 0)

    def test_a_wait_of_600_ms_shows_the_arc_after_the_threshold_and_takes_it_away_at_the_end(self):
        from meridiana.ui import waiting
        self.wait.begin()
        spin(self.app, waiting.THRESHOLD_MS - 120)
        self.assertTrue(self.spinner.isHidden())            # not yet
        spin(self.app, 420)
        self.assertFalse(self.spinner.isHidden())
        self.assertTrue(self.spinner.turning())
        self.assertGreater(self.spinner.frames, 3)          # it turns: frame after frame
        self.wait.begin()                                   # asked again while waiting: the same wait
        self.wait.end()
        self.assertTrue(self.spinner.isHidden())            # gone at once at the end
        self.assertFalse(self.spinner.turning())
        self.assertEqual(self.seen, [True, False])

    def test_with_less_motion_the_arc_stands_still(self):
        self.spinner.reduced_motion = True
        self.wait.begin()
        spin(self.app, 700)
        self.assertFalse(self.spinner.isHidden())
        self.assertFalse(self.spinner.turning())
        self.assertEqual(self.spinner.angle(), 0.0)
        self.assertEqual(self.spinner.frames, 1)            # one frame, and still
        self.spinner._motion(False)                         # the system allows motion again: it turns
        self.assertTrue(self.spinner.turning())
        self.spinner._motion(True)
        self.assertFalse(self.spinner.turning())
        self.wait.end()

    def test_the_arc_is_drawn_in_the_text_s_colour_on_a_faint_ring(self):
        from PySide6.QtGui import QColor, QPalette
        self.spinner.reduced_motion = True
        self.spinner.start()
        image = self.spinner.grab().toImage()
        accent = self.spinner.palette().color(QPalette.ColorRole.Text)
        # at twelve o'clock, still, the arc starts: the pixel just inside the top of the ring is the text's
        ratio = image.devicePixelRatio()
        top = image.pixelColor(int(self.spinner.width() / 2 * ratio + 2 * ratio), int(4 * ratio))
        self.assertLess(abs(top.red() - accent.red()) + abs(top.green() - accent.green())
                        + abs(top.blue() - accent.blue()), 60, (top.name(), accent.name()))
        self.spinner.set_colours(arc="#ffffff", chip="#14161ac8")
        self.assertEqual(self.spinner.colours["chip"].alpha(), 0xc8)        # the tokens' #rrggbbaa read right
        self.assertEqual(self.spinner.colours["arc"], QColor("#ffffff"))


class Stale(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_value_to_update_is_drawn_in_the_muted_text_and_back(self):
        from PySide6.QtGui import QPalette
        from PySide6.QtWidgets import QLabel

        from meridiana.ui import waiting
        label = QLabel("92.410")
        f = label.font()
        f.setPointSizeF(f.pointSizeF() * 2)
        label.setFont(f)
        label.resize(140, 40)
        label.show()

        def ink() -> int:
            """How far the text's strongest pixel is from the floor, in lightness: dark text on a light palette,
            light text on a dark one (the system's palette, dark on a Windows set to dark)."""
            image = label.grab().toImage()
            floor = label.palette().color(QPalette.ColorRole.Window).lightness()
            return max(abs(image.pixelColor(x, y).lightness() - floor)
                       for x in range(image.width()) for y in range(image.height()))

        fresh = ink()
        waiting.set_stale(label, True)
        self.assertTrue(waiting.is_stale(label))
        self.assertEqual(label.foregroundRole(), QPalette.ColorRole.PlaceholderText)
        self.assertLess(ink(), fresh - 20)                  # grey, nearer the floor, still there to read
        waiting.set_stale(label, False)
        self.assertFalse(waiting.is_stale(label))
        self.assertEqual(ink(), fresh)
        _setup.dispose(label)


class CatalogueReading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_catalogue_window_opens_before_the_catalogue_is_read_and_shows_the_arc(self):
        import threading
        from unittest import mock

        from _setup import wait_until

        from meridiana import catalog
        from meridiana.ui import catalog_dialog
        catalog_dialog.forget_filters()
        catalog._ORDERED.pop("batteries", None)                     # as at the first opening
        gate = threading.Event()
        prepare = catalog.prepare

        def held(kind):
            gate.wait(10)
            prepare(kind)

        with mock.patch.object(catalog, "prepare", held):
            dialog = catalog_dialog.CatalogDialog("batteries")
            self.assertTrue(dialog.reading)                         # open, the catalogue not read yet
            self.assertEqual(dialog.model.rowCount(), 0)
            self.assertIn("Reading", dialog.count.text())
            dialog.show()
            dialog.query.setText("x")                               # a filter set meanwhile waits for the list
            spin(self.app, 450)
            self.assertFalse(dialog.spinner.isHidden())             # the arc over the list, past the threshold
            centre = dialog.table.viewport().rect().center()
            self.assertLess((dialog.spinner.geometry().center() - centre).manhattanLength(), 4)
            dialog.query.clear()
            gate.set()
            self.assertTrue(wait_until(self.app, lambda: not dialog.reading, 20))
        self.assertTrue(dialog.spinner.isHidden())
        self.assertGreater(dialog.model.rowCount(), 0)
        self.assertGreater(dialog.rows.rowCount(), 0)
        self.assertGreater(dialog.maker.count(), 0)
        self.assertTrue(catalog.ready("batteries"))
        _setup.dispose(dialog)
        again = catalog_dialog.CatalogDialog("batteries")           # read already: the list at once, no wait
        self.assertFalse(again.reading)
        self.assertGreater(again.model.rowCount(), 0)
        _setup.dispose(again)


class Skeleton(unittest.TestCase):
    """The 3D view's skeleton alone (waiting.Skeleton3D): taken away by the time limit when no frame comes, said in
    the log; in light and in dark. The skeleton of the window until its first frame is in finestra/test_waits.py."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_with_no_frame_the_time_limit_takes_it_away_and_the_log_says_why(self):
        from unittest import mock

        from PySide6.QtWidgets import QWidget

        from meridiana import log
        from meridiana.ui import waiting
        host = QWidget()
        host.resize(300, 200)
        self.addCleanup(_setup.dispose, host)
        skeleton = waiting.Skeleton3D(host, limit_ms=250)            # no Qt Quick under it: no frame comes
        with mock.patch.object(log, "complain") as complained:
            host.show()
            spin(self.app, 100)
            self.assertTrue(skeleton.isVisible())
            self.assertTrue(_setup.wait_until(self.app, lambda: bool(skeleton.why), 3))
        self.assertEqual(skeleton.why, "time")
        complained.assert_called_once()
        self.assertIn("no frame", str(complained.call_args[0][1]))

    def test_the_skeleton_in_light_and_in_dark(self):
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QWidget

        from meridiana import theme_colors, view_colours
        from meridiana.ui import waiting

        def near(a: QColor, b: QColor, tolerance: int = 12) -> bool:
            return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue()) <= tolerance

        inks = {}
        for dark in (False, True):
            host = QWidget()
            host.resize(480, 320)
            self.addCleanup(_setup.dispose, host)
            skeleton = waiting.Skeleton3D(host, limit_ms=60_000)
            skeleton.set_buildings([([[0, 0], [40, 0], [40, 20], [0, 20]], 9.5), ([[50, 5], [60, 5], [60, 15]], 4.0)])
            tokens = theme_colors.derive(theme_colors.DEFAULT_SEED, dark).tokens
            skeleton.set_colours(tokens)
            host.show()
            image = skeleton.grab().toImage()
            w, h = image.width(), image.height()
            # the view's own sky and ground, the same in both themes (R16)
            self.assertTrue(near(image.pixelColor(3, 3), QColor(view_colours.D3["sky_top"])))
            self.assertTrue(near(image.pixelColor(3, h - 3), QColor(view_colours.D3["ground"])))
            ink = QColor(tokens["muted"])
            outline = sum(1 for x in range(0, w, 2) for y in range(0, h, 2) if near(image.pixelColor(x, y), ink, 30))
            self.assertGreater(outline, 40, dark)                   # the buildings, outlined in the theme's ink
            inks[dark] = ink.name()
            skeleton.done("frame")
        self.assertNotEqual(inks[False], inks[True])


if __name__ == "__main__":
    unittest.main()
