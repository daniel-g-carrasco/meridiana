"""The bar of the sun under the 3D view, alone (ui/sunbar.py), with the 3D view's backend it drives (ui/view3d.Backend,
joined by sunChanged as the window joins them through View3D.set_sun): a site starts on its design day at solar
noon, the hour moves the sun, at night it has no power and the words say so, playing starts again at dawn, the
button goes back to the design day. That the window joins them and sets the site of the project opened is in
finestra/test_window.py. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class SunBarAlone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_sun_starts_on_the_design_day_and_moves(self):
        from meridiana.ui.sunbar import SunBar
        from meridiana.ui.view3d import Backend
        p = capannone()
        bar, backend = SunBar(), Backend()
        self.addCleanup(_setup.dispose, bar)
        self.addCleanup(backend.deleteLater)
        bar.sunChanged.connect(backend.set_sun)
        bar.set_site(p.site.lat, p.site.lon, p.sun_window)  # what the window does with the project opened
        noon = bar.position()
        self.assertEqual((bar.day.date().month(), bar.day.date().day()), (12, 21))
        self.assertLess(abs(noon.azimuth), 3.0)                    # solar noon: the sun in the South
        self.assertAlmostEqual(backend._sun_elev, noon.apparent, places=6)
        bar.hour.setValue(9 * 6)                                   # 09:00 on the clock
        self.assertLess(bar.position().azimuth, -20.0)             # in the morning the sun is to the East
        self.assertAlmostEqual(backend._sun_bearing, bar.position().bearing, places=6)
        bar.hour.setValue(20 * 6)                                  # 20:00 in December: night
        self.assertEqual(backend.sunPower, 0.0)
        self.assertIn("below the horizon", bar.words.text())
        bar.play.setChecked(True)                                  # playing starts again at dawn
        self.assertGreater(bar.position().apparent, 0.0)
        bar._tick()
        self.assertGreater(backend.sunPower, 0.0)
        bar.play.setChecked(False)
        self.assertFalse(bar.timer.isActive())
        bar.to_design_day()
        self.assertAlmostEqual(bar.position().apparent, noon.apparent, delta=0.6)
        bar.set_site(p.site.lat, p.site.lon, p.sun_window)  # the same site again: the hour chosen stays
        bar.hour.setValue(10 * 6)
        bar.set_site(p.site.lat, p.site.lon, p.sun_window)
        self.assertEqual(bar.hour.value(), 10 * 6)


if __name__ == "__main__":
    unittest.main()
