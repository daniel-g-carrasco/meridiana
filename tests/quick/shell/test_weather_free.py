"""The guard of the window applied to the weather's job (R598, study 48 chapter 5): the sun map turned on without the
weather of the site fetches it by itself (Daniel, 14/11/2026), a job of the Center in a thread (app/weather_job.py),
then computes the map; from the request to the last finest level no call of the jobs' center on the window's thread
takes more than 5 ms and the window's beat never stops more than 50 ms. The window is the real one, off screen, with
the real bridge of the jobs (gui/backend/work.py); PVGIS without the network (FakePvgis: its recorded answers)."""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import _setup
from _fixtures import FakePvgis, mixed
from meridiana.app.sun_map import SunMap
from meridiana.core.energy import meteo
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import window_stays_free
from quick.aiuti.tempi import timed


class WeatherFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)               # no weather in it: the map has to fetch it
        cls.host = QuickWindow(mixed(), cls.cache, theme={'theme': 'light'})
        cls.work = cls.host.work
        cls.center = cls.work.center
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def quiet(self, seconds=1.0, beat_ms=20.0, most=30.0) -> bool:
        """Turns the events until the window's beat has kept under `beat_ms` for `seconds` (as test_sun_map_free):
        what the window still does by itself after its opening is not the job's to answer for."""
        from PySide6.QtCore import Qt, QTimer
        last, since = [time.perf_counter()], [time.perf_counter()]

        def beat():
            now = time.perf_counter()
            if (now - last[0]) * 1000 > beat_ms:
                since[0] = now
            last[0] = now
        timer = QTimer()
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.setInterval(5)
        timer.timeout.connect(beat)
        timer.start()
        try:
            return _setup.wait_for(lambda: time.perf_counter() - since[0] >= seconds, int(most * 1000))
        finally:
            timer.stop()

    @timed('no call of the window over 5 ms, no beat over 50 ms')
    def test_the_window_stays_free_while_the_weather_is_fetched_and_the_map_computed(self):
        self.assertTrue(_setup.wait_for(lambda: not self.host.bridge.busy and not self.work.rows, 120000),
                        'the opening of the window has ended')
        self.assertTrue(self.quiet(), 'the window has settled after its opening')
        session = self.host.bridge.session
        sm = SunMap(self.center, session, self.cache, self.cache / 'sun_map', SimpleNamespace(network_pvgis=True))
        self.addCleanup(sm.close)
        titles = []
        self.center.subscribe(lambda: titles.extend(r['title'] for r in self.center.rows()))
        with FakePvgis() as pvgis, window_stays_free(self.center, call_ms=5, beat_ms=50) as seen:
            sm.set_on(True)
            self.assertTrue(_setup.wait_for(lambda: not sm.busy and (sm.done or bool(sm.error)), 180000),
                            'the weather fetched and the map done')
        print(f'\nweather and sun map, the guard: {seen}')
        self.assertEqual(sm.error, '')
        self.assertIn('Weather of the site', titles, 'the weather was a job of the Center, in the bar')
        self.assertEqual(len(pvgis.asked), 2, 'the typical year and the horizon')
        self.assertTrue(meteo.cached(session.project.site.lat, session.project.site.lon, self.cache))
        self.assertTrue(sm.surfaces and all(s.fine for s in sm.surfaces.values()))
        self.assertGreater(seen.calls, len(sm.surfaces))


if __name__ == '__main__':
    unittest.main()
