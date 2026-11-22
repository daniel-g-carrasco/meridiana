"""The guard of the window applied to the sun map (R598, study 48 chapter 5; study 45 package 4): while the map's job
runs in its processes, from the request to the last finest level, no call of the jobs' center on the window's thread
takes more than 5 ms and the window's beat never stops more than 50 ms. The window is the real one, off screen, with
the real bridge of the jobs (gui/backend/work.py)."""
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from _fixtures import clear_sky_meteo, mixed, write_cache
from meridiana.app.sun_map import SunMap
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import window_stays_free


class SunMapFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)
        write_cache(clear_sky_meteo(), cls.cache)
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
        """Turns the events until the window's beat has kept under `beat_ms` for `seconds`: what the window still
        does by itself after its opening (the icons drawn the first time they are shown, 30-100 ms on the window's
        thread, measured on 13/11/2026) is not the map's to answer for."""
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

    def test_the_window_stays_free_while_the_map_is_computed(self):
        self.assertTrue(_setup.wait_for(lambda: not self.host.bridge.busy and not self.work.rows, 120000),
                        'the opening of the window has ended')
        self.assertTrue(self.quiet(), 'the window has settled after its opening')
        session = self.host.bridge.session
        store = self.cache / 'sun_map'
        sm = SunMap(self.center, session, self.cache, store)
        self.addCleanup(sm.close)
        with window_stays_free(self.center, call_ms=5, beat_ms=50) as seen:
            sm.set_on(True)
            self.assertTrue(_setup.wait_for(lambda: sm.done or bool(sm.error), 180000), 'the map is done')
        self.assertEqual(sm.error, '')
        self.assertTrue(sm.surfaces)
        self.assertTrue(all(s.fine for s in sm.surfaces.values()))
        self.assertGreater(seen.calls, len(sm.surfaces))


if __name__ == '__main__':
    unittest.main()
