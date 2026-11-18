"""R516: an orthophoto that stays. The national orthophoto's server answers some exact addresses with an error
document it keeps (the same address asked again gets the same error, any other parameter gets the image: tried
on 07/11/2026), a tile on show must never go blank, a tile on disk is shown whatever its age, and the area of a
project is kept for the plan without network where the licence allows it."""

import http.server
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from meridiana import geo, tiles


def png(colour='#4f905c'):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QImage
    image = QImage(256, 256, QImage.Format.Format_RGB32)
    image.fill(QColor(colour))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'PNG')
    return bytes(data)


class StickyErrors:
    """A WMS behind a cache that kept the error of some exact addresses: those get the error document again and
    again, every other address the image. `poisoned(path)` says which; `down` makes every answer an error."""

    def __init__(self, poisoned=lambda path: True):
        self.poisoned, self.down, self.asked, self.lock = poisoned, False, [], threading.Lock()
        self.image = png()
        self.parallel = self.most = 0
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                with owner.lock:
                    owner.asked.append(self.path)
                    owner.parallel += 1
                    owner.most = max(owner.most, owner.parallel)
                time.sleep(.003)
                bad = owner.down or ('TRANSPARENT' not in self.path and owner.poisoned(self.path))
                body = b'<ServiceExceptionReport>msShapefileOpen(): Unable to access file.</ServiceExceptionReport>' \
                    if bad else owner.image
                self.send_response(200)
                self.send_header('Content-Type', 'text/xml' if bad else 'image/png')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                with owner.lock:
                    owner.parallel -= 1

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.root = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def wms(root, **fields):
    return tiles.Source('pcn', 'Italy: orthophoto 2012 (Geoportale Nazionale)', 'wms', root + '/ogc',
                        'Ortofoto 2012', rank=40, max_zoom=20, layer='ortho', **fields)


class OfflineMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def wait(self, condition, seconds=8):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(condition())

    def spin(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.002)

    def server(self, **options):
        server = StickyErrors(**options)
        self.addCleanup(server.close)
        return server

    def cache(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return Path(folder.name)

    # the cause: an error kept for the exact address, a whole view of the orthophoto lost, then back, then lost

    def test_an_error_kept_for_an_address_is_asked_again_with_another_address(self):
        from meridiana.quick.backend import plan_tiles
        server = self.server()
        loader = plan_tiles.TileLoader(self.cache(), sources={'pcn': wms(server.root)})
        got, failed = [], []
        loader.tileReady.connect(lambda *args: got.append(args[:4]))
        loader.tileFailed.connect(lambda *args: failed.append(args[:4]))
        with mock.patch.object(plan_tiles, 'RETRIES', (.0, .0)):
            loader.request('pcn', 18, 137644, 93758)
            self.wait(lambda: got or failed)
        self.assertEqual(failed, [])
        self.assertEqual(got, [('pcn', 18, 137644, 93758)])
        self.assertTrue(loader._path('pcn', 18, 137644, 93758).exists())
        loader.close()

    def test_the_plan_keeps_the_orthophoto_where_the_server_kept_errors(self):
        """A third of the addresses of a view poisoned, as on 07/11/2026 at zoom 17: before, three failed tiles
        moved the whole plan to the replacement map for three minutes, and back, and away again."""
        from meridiana.quick.backend import plan_tiles
        server = self.server(poisoned=lambda path: hash(path) % 3 == 0)
        sources = {'pcn': wms(server.root),
                   'osm': tiles.Source('osm', 'Map', 'xyz', server.root + '/map/{z}/{x}/{y}.png?TRANSPARENT',
                                       'Map credit', imagery='map', rank=20)}
        maps = plan_tiles.MapController(self.cache(), sources=sources, origin=geo.Origin(45.5226, 9.03))
        maps.setSource('pcn')
        with mock.patch.object(plan_tiles, 'RETRIES', (.0, .0)):
            maps.updateView(-400, -300, 400, 300, .4, 1)
            self.wait(lambda: maps.state.wanted and maps.state.wanted.issubset(maps.state.loaded)
                      or maps.state.source != 'pcn')
        self.assertEqual(maps.state.source, 'pcn', maps.state.fallback_message)
        self.assertEqual(maps.state.failures, set())
        maps.close()

    # the tiles on show and the memory

    def test_a_tile_on_show_survives_the_memory_it_was_pushed_out_of(self):
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QColor, QImage
        from meridiana.quick.backend import plan_tiles
        cache = self.cache()
        loader = plan_tiles.TileLoader(cache, sources={'pcn': wms('http://127.0.0.1:9')})
        images = plan_tiles.MapImages(reread=loader.read)
        tile = ('pcn', 18, 1, 2)
        path = loader._path(*tile)
        path.parent.mkdir(parents=True)
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor('#c8b89a'))
        image.save(str(path), 'PNG')
        with mock.patch.object(plan_tiles.resources, 'cache_limit', lambda kind: 3 * 256 * 1024):
            images.put('1', tile, image)
            for n in range(8):             # the tiles around, asked after it: the memory holds three
                images.put(str(10 + n), ('pcn', 18, 10 + n, 2), image)
            got = images.requestImage('1', QSize(), QSize())
        self.assertFalse(got.isNull(), 'a tile on show came back empty from the provider')
        self.assertEqual(got.pixelColor(5, 5).name(), '#c8b89a')
        loader.close()

    def test_the_tiles_on_show_leave_the_memory_last(self):
        from PySide6.QtGui import QImage
        from meridiana.quick.backend import plan_tiles
        images = plan_tiles.MapImages()
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        shown = {('pcn', 18, n, 0) for n in range(3)}
        with mock.patch.object(plan_tiles.resources, 'cache_limit', lambda kind: 4 * 256 * 1024):
            for n, tile in enumerate(sorted(shown)):
                images.put(str(n), tile, image)
            images.pin(shown)
            for n in range(10):
                images.put(str(10 + n), ('pcn', 18, 10 + n, 1), image)
            self.assertTrue(all(tile in images for tile in shown))

    def test_a_superseded_identifier_still_gives_its_tile(self):
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QImage
        from meridiana.quick.backend import plan_tiles
        images = plan_tiles.MapImages()
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        images.put('1', ('pcn', 18, 1, 1), image)
        images.put('2', ('pcn', 18, 1, 1), image)       # the same tile again (the ring around, a refresh)
        self.assertFalse(images.requestImage('1', QSize(), QSize()).isNull())

    # the disk cache

    def _old_tile(self, cache, loader, tile, days, colour='#c8b89a'):
        from PySide6.QtGui import QColor, QImage
        path = loader._path(*tile)
        path.parent.mkdir(parents=True, exist_ok=True)
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor(colour))
        image.save(str(path), 'PNG')
        old = time.time() - days * 86400
        os.utime(path, (old, old))
        return path

    def test_a_stale_tile_is_shown_at_once_and_stays_when_the_renewal_fails(self):
        from meridiana.quick.backend import plan_tiles
        server = self.server()
        server.down = True
        cache = self.cache()
        source = tiles.Source('osm', 'Map', 'xyz', server.root + '/map/{z}/{x}/{y}.png', 'Map', imagery='map')
        loader = plan_tiles.TileLoader(cache, sources={'osm': source})
        path = self._old_tile(cache, loader, ('osm', 17, 1, 2), days=40)
        got, failed = [], []
        loader.tileReady.connect(lambda *args: got.append(args[4].pixelColor(5, 5).name()))
        loader.tileFailed.connect(lambda *args: failed.append(args))
        with mock.patch.object(plan_tiles, 'RETRIES', (.0,)):
            loader.request('osm', 17, 1, 2)
            self.wait(lambda: got)
            self.wait(lambda: len(server.asked) >= 2)        # renewed in background, twice, both failed
            self.spin(.2)
        self.assertEqual(got, ['#c8b89a'])
        self.assertEqual(failed, [], 'a tile on show is not a failure')
        self.assertTrue(path.exists())
        loader.close()

    def test_a_stale_tile_is_renewed_when_the_server_answers(self):
        from meridiana.quick.backend import plan_tiles
        server = self.server(poisoned=lambda path: False)
        cache = self.cache()
        source = tiles.Source('osm', 'Map', 'xyz', server.root + '/map/{z}/{x}/{y}.png', 'Map', imagery='map')
        loader = plan_tiles.TileLoader(cache, sources={'osm': source})
        path = self._old_tile(cache, loader, ('osm', 17, 1, 2), days=40)
        got = []
        loader.tileReady.connect(lambda *args: got.append(args[4].pixelColor(5, 5).name()))
        loader.request('osm', 17, 1, 2)
        self.wait(lambda: len(got) == 2)
        self.assertEqual(got, ['#c8b89a', '#4f905c'])
        self.assertLess(time.time() - path.stat().st_mtime, 60)
        loader.close()

    def test_an_orthophoto_of_a_fixed_year_never_expires_and_a_map_keeps_a_week(self):
        self.assertEqual(tiles.SOURCES['pcn'].max_age_days, 0)
        for key in ('it-bz', 'it-tn', 'it-toscana', 'it-fvg', 'eox-2016'):
            self.assertEqual(tiles.SOURCES[key].max_age_days, 0, key)
        self.assertGreaterEqual(tiles.SOURCES['osm'].max_age_days, 7)
        from meridiana.quick.backend import plan_tiles
        server = self.server(poisoned=lambda path: False)
        cache = self.cache()
        loader = plan_tiles.TileLoader(cache, sources={'pcn': wms(server.root, max_age_days=0)})
        self._old_tile(cache, loader, ('pcn', 18, 1, 2), days=900)
        got = []
        loader.tileReady.connect(lambda *args: got.append(args))
        loader.request('pcn', 18, 1, 2)
        self.wait(lambda: got)
        self.spin(.3)
        self.assertEqual(len(got), 1)
        self.assertEqual(server.asked, [])
        loader.close()

    def test_a_tile_that_arrives_after_the_view_moved_on_is_kept_on_disk(self):
        from meridiana.quick.backend import plan_tiles
        server = self.server(poisoned=lambda path: False)
        loader = plan_tiles.TileLoader(self.cache(), sources={'pcn': wms(server.root)})
        loader.request('pcn', 18, 5, 6)
        loader.keep_only(set())
        # r24-fasi: written on a decoders' thread (plan_tiles._Arrived), done when the loader has it back
        self.wait(lambda: not loader.in_flight and not loader.arriving)
        self.assertTrue(loader._path('pcn', 18, 5, 6).exists())
        loader.close()

    # the area of the project, kept

    def test_the_area_of_a_project_is_kept_once_at_every_useful_zoom_politely_and_resumes(self):
        from meridiana.quick.backend import plan_offline
        server = self.server(poisoned=lambda path: hash(path) % 5 == 0)
        cache = self.cache()
        source = wms(server.root, bulk=True, detail_zoom=18)
        origin = geo.Origin(45.5226, 9.03)
        area = plan_offline.area_tiles(source, origin, (-50, -50, 50, 50), radius=200)
        zooms = sorted({z for z, _x, _y in area})
        self.assertEqual(zooms[-1], 18, 'not past the detail of the source: further is only enlargement')
        self.assertEqual(zooms[0], 12)
        job = plan_offline.AreaDownload(cache, source, area)
        progress = []
        job.progress.connect(lambda done, total: progress.append((done, total)))
        with mock.patch.object(plan_offline, 'RETRIES', (.0, .0)):
            job.start()
            self.wait(lambda: job.finished, 30)
        self.assertEqual(job.failed, 0)
        self.assertEqual(progress[-1], (len(area), len(area)))
        self.assertLessEqual(server.most, plan_offline.IN_FLIGHT)
        self.assertLessEqual(plan_offline.IN_FLIGHT, 2)
        from meridiana.quick.backend.plan_tiles import tile_path
        self.assertTrue(all(tile_path(cache, source, z, x, y).exists() for z, x, y in area))
        asked = len(server.asked)
        again = plan_offline.AreaDownload(cache, source, area)
        again.start()
        self.wait(lambda: again.finished)
        self.assertEqual(len(server.asked), asked, 'what is on disk is not asked again')

    def test_only_the_sources_whose_licence_allows_it_are_kept_ahead(self):
        self.assertTrue(tiles.SOURCES['pcn'].bulk)
        self.assertEqual(tiles.SOURCES['pcn'].detail_zoom, 18)
        for key in ('osm', 'opentopomap', 'de-bb', 'eox-2016'):
            self.assertFalse(tiles.SOURCES[key].bulk, key)
        from meridiana.quick.backend import plan_offline
        with self.assertRaises(ValueError):
            plan_offline.AreaDownload(self.cache(), tiles.SOURCES['osm'], [(17, 1, 1)])

    def test_the_plan_keeps_its_area_and_then_works_without_network(self):
        from meridiana.quick.backend import plan_offline, plan_tiles
        server = self.server(poisoned=lambda path: False)
        cache = self.cache()
        sources = {'pcn': wms(server.root, bulk=True, detail_zoom=18)}
        origin = geo.Origin(45.5226, 9.03)
        maps = plan_tiles.MapController(cache, sources=sources, origin=origin)
        maps.setSource('pcn')
        with mock.patch.object(plan_offline, 'RADIUS', 150), mock.patch.object(plan_offline, 'START_DELAY', 0):
            maps.keepArea((-30, -30, 30, 30))
            self.wait(lambda: maps.area is not None and maps.area.finished, 30)
        self.assertEqual(maps.area.failed, 0)
        self.assertEqual(maps.offlineText, '')
        maps.close()
        offline = plan_tiles.MapController(cache, sources=sources, origin=origin, offline=True)
        offline.setSource('pcn')
        offline.updateView(-60, -40, 60, 40, .4, 1)
        self.wait(lambda: offline.state.wanted and offline.state.wanted.issubset(offline.state.loaded))
        offline.close()


if __name__ == '__main__':
    unittest.main()
