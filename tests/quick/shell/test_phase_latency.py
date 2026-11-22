"""Guard cold and retained phase latency with a complete computed year."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
import _setup

from _fixtures import casa_a_falde, inverter_record, clear_sky_meteo, write_cache
from meridiana.app import jobs, pipeline
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import pump, wait_for
from quick.aiuti.tempi import timed

def setUpModule():
    _setup.keep_global_state()
    # the same renderer as the paired Windows benchmark, in an offscreen window. Here and not at the import: a group
    # imports all its modules before it runs them, and MERIDIANA_PRELOAD=0 then reached every other module of
    # tests/quick/shell (pages not made ahead: test_aiuti_r597 found no help mark of the Site); keep_global_state
    # puts the environment back after this module
    os.environ.setdefault("MERIDIANA_PRELOAD", "0")
    # the renderer of the Windows benchmark only on Windows: on Linux, alone (the CI's timing job), Direct3D drew no
    # frame and the threaded loop over the software OpenGL stopped the events (10 minutes); there the run's own stays
    if sys.platform == "win32":
        os.environ.setdefault("QT_QUICK_BACKEND", "rhi")
        os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")
        os.environ.setdefault("QSG_RENDER_LOOP", "threaded")


class PhaseLatency(unittest.TestCase):
    @timed('a phase on screen within 500 ms')
    def test_cold_and_retained_phases_with_a_complete_year(self):
        app = _setup.qt_or_skip()
        create_app()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            cache = Path(folder)
            project = casa_a_falde()
            project.energy["inverters"] = [{"record": inverter_record(), "count": 1, "name": ""}]
            project.energy["strings"] = {"auto": True}
            write_cache(clear_sky_meteo(), cache)
            host = QuickWindow(project, cache, real_views=True, theme={'reducedMotion': False})
            try:
                host.bridge.configure_background(enabled=False)
                host.keep_on_screen = lambda: None
                host._placement.timeout.disconnect()
                win = host.window
                win.resize(1400, 900)
                win.show()
                pump(1500)
                # Finish the opening layout before publishing the measured year:
                # a late opening answer would invalidate it during a phase sample.
                wait_for(lambda: not host.bridge.busy and host.bridge._layout is None
                         and not host.bridge.session.telling())
                project = host.bridge.session.project
                layouts, keys, _ = jobs.layout_of(project)
                energy = pipeline.compute(project, layouts, cache, fetch=False).as_dict()
                self.assertIsNotNone(energy['sim'])
                self.assertEqual(len(energy["sim"].hourly), 8760)
                host.bridge.session.take_year(layouts, keys, energy)
                wait_for(lambda: not host.bridge.session.telling() and not host.parts.controllers['results'].busy)
                self.assertFalse(host.bridge.session.year_outdated())
                pump(1500)
                for phase in ('plant', 'production', 'consumption', 'economics', 'report',
                              'model', 'production', 'plant', 'report', 'economics', 'model'):
                    with self.subTest(phase=phase):
                        frames = []
                        from PySide6.QtCore import Qt
                        marker = {'armed': False, 'synced': False}
                        def synchronized(marker=marker):
                            if marker['armed']:
                                marker['synced'] = True
                        def swapped(frames=frames, marker=marker):
                            if marker['synced']:
                                frames.append(time.perf_counter())
                        win.afterSynchronizing.connect(synchronized, Qt.ConnectionType.DirectConnection)
                        win.frameSwapped.connect(swapped, Qt.ConnectionType.DirectConnection)
                        start = time.perf_counter()
                        win.showPhase(phase)
                        call_ms = (time.perf_counter()-start)*1000
                        marker['armed'] = True
                        worst_turn = call_ms
                        deadline = time.perf_counter()+.6
                        while time.perf_counter() < deadline:
                            win.requestUpdate()
                            at = time.perf_counter()
                            app.processEvents()
                            worst_turn = max(worst_turn, (time.perf_counter()-at)*1000)
                            time.sleep(.001)  # wait: a breath between two turns of the loop that is measured
                        tail = time.perf_counter()
                        win.requestUpdate()
                        while (not frames or frames[-1] < tail) and time.perf_counter() < tail+5:
                            at = time.perf_counter()
                            app.processEvents()
                            worst_turn = max(worst_turn, (time.perf_counter()-at)*1000)
                            time.sleep(.001)  # wait: a breath between two turns of the loop that is measured
                        win.frameSwapped.disconnect(swapped)
                        win.afterSynchronizing.disconnect(synchronized)
                        self.assertTrue(frames, 'A phase must actually draw')
                        visible_ms = (frames[0]-start)*1000
                        worst_frame = max((b-a)*1000 for a, b in zip([start]+frames, frames, strict=False))
                        print(f'{phase}: visible {visible_ms:.1f}, frame {worst_frame:.1f}, turn {worst_turn:.1f} ms')
                        # Headroom for shared Windows runners; the benchmark keeps the 100/50 ms goals.
                        self.assertLess(visible_ms, 500, 'Phase visible too late')
                        self.assertLess(worst_frame, 500, 'A frame was blocked')
            finally:
                host.close()


if __name__ == '__main__':
    unittest.main()
