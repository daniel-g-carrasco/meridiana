"""R21/R36/R131/R149/R173/R191: maps, isolated cache and actual Quick pixels."""

import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from meridiana import geo, tiles


class MapStateTests(unittest.TestCase):
    def state(self):
        from meridiana.quick.backend.plan_maps import PlanMaps
        return PlanMaps(geo.Origin(45.5226, 9.03))

    def test_automatic_near_far_manual_and_unknown_source(self):
        state = self.state()
        state.set_view((-100, -100, 100, 100), 1)
        self.assertEqual(state.source, 'pcn')
        state.set_view((-100, -100, 100, 100), 5)
        self.assertEqual(state.source, 'pcn')          # R539: the orthophoto from afar too (it was the street map)
        state.set_source('pcn')
        self.assertEqual(state.source, 'pcn')
        state.set_source('removed-source')
        self.assertEqual(state.source, 'pcn')
        self.assertEqual(state.choice, 'removed-source')

    def test_three_distinct_current_failures_fallback_cooldown_retry_and_choice(self):
        state = self.state()
        state.set_view((-300, -300, 300, 300), 1)
        wanted = list(state.wanted)
        self.assertGreaterEqual(len(wanted), 3)
        state.failed(wanted[0], now=10)
        state.failed(wanted[0], now=10)
        state.failed(('pcn', 1, 0, 0), now=10)
        self.assertEqual(state.source, 'pcn')
        for tile in wanted[1:3]:
            state.failed(tile, now=10)
        self.assertEqual(state.source, 'osm')
        self.assertEqual(state.choice, 'auto')
        self.assertEqual(state.fallback_from, 'pcn')
        state.choose(now=20)
        self.assertEqual(state.source, 'osm')
        state.retry()
        self.assertEqual(state.source, 'pcn')
        self.assertEqual(state.choice, 'auto')

    def test_old_tiles_stay_until_full_new_coverage_and_none_clears(self):
        state = self.state()
        state.set_view((-50, -50, 50, 50), 1)
        old = next(iter(state.wanted))
        state.ready(old, 'old')
        state.set_source('osm')
        self.assertIn(old, state.loaded)
        for tile in list(state.wanted):
            state.ready(tile, 'new')
        self.assertNotIn(old, state.loaded)
        self.assertEqual(set(state.loaded), state.wanted)
        self.assertIn('OpenStreetMap', state.attribution)
        state.set_source('none')
        self.assertEqual(state.loaded, {})
        self.assertEqual(state.attribution, '')
        self.assertFalse(state.veil_visible)

    def test_equal_earth_hysteresis_no_requests_and_all_countries_offline(self):
        state = self.state()
        state.set_view((-1e7, -1e7, 1e7, 1e7), 2000)
        self.assertTrue(state.equal_earth)
        self.assertEqual(state.wanted, set())
        self.assertEqual(state.attribution, 'Natural Earth')
        self.assertFalse(state.veil_visible)
        self.assertEqual(len(state.world()['countries']), 177)
        for scale in (1999, 1600, 1500):
            state.set_view((-100, -100, 100, 100), scale)
            self.assertTrue(state.equal_earth)
        state.set_view((-100, -100, 100, 100), 1499)
        self.assertFalse(state.equal_earth)
        self.assertTrue(state.wanted)

    def test_custom_source_requires_credit_and_dpr_chooses_sharper_tiles(self):
        from meridiana.quick.backend.plan_maps import PlanMaps
        custom = dict(key='user-test', name='Test', kind='xyz',
                      url='https://example.test/{z}/{x}/{y}.png', attribution='')
        state = PlanMaps(geo.Origin(45, 9), custom_sources=[custom])
        self.assertNotIn('user-test', state.sources)
        custom['attribution'] = 'Test credit'
        state.set_catalogue([custom])
        state.set_source('user-test')
        state.set_view((-50, -50, 50, 50), 1, dpr=1)
        first = {t[1] for t in state.wanted}
        state.set_view((-50, -50, 50, 50), 1, dpr=2)
        self.assertEqual({t[1] for t in state.wanted}, {z + 1 for z in first})
        self.assertEqual(state.attribution, 'Test credit')

    def test_quad_transform_maps_all_corners_and_underlay_orientation(self):
        from meridiana.quick.backend.plan_maps import quad_matrix, underlay_record
        from meridiana.underlay import Underlay
        corners = [(2, 3), (6, 2), (7, 8), (1, 7)]
        matrix = quad_matrix(corners)
        for (u, v), (x, y) in zip(((0, 0), (1, 0), (1, 1), (0, 1)), corners, strict=True):
            w = matrix[12] * u + matrix[13] * v + matrix[15]
            self.assertAlmostEqual((matrix[0] * u + matrix[1] * v + matrix[3]) / w, x)
            self.assertAlmostEqual((matrix[4] * u + matrix[5] * v + matrix[7]) / w, y)
        item = underlay_record(Underlay('u', width=100, height=50, x=10, y=20,
                                      scale=.1, rotation=90, opacity=.4))
        self.assertAlmostEqual(item['matrix'][3], 10)
        self.assertAlmostEqual(item['matrix'][7], -20)
        self.assertAlmostEqual(item['matrix'][4], -10)
        self.assertAlmostEqual(item['matrix'][1], 5)
        self.assertEqual(item['opacity'], .4)

    def test_late_tiles_are_discarded_and_a_date_line_site_never_requests_the_whole_world(self):
        from meridiana.quick.backend.plan_maps import PlanMaps
        state = PlanMaps(geo.Origin(0, 179.9999))
        state.set_source('osm')
        state.set_view((-200, -200, 200, 200), 1)
        self.assertLess(len(state.wanted), 50)
        columns = {tile[2] for tile in state.wanted}
        zoom = next(iter(state.wanted))[1]
        self.assertIn(0, columns)
        self.assertIn(2 ** zoom - 1, columns)
        late = next(iter(state.wanted))
        state.set_source('none')
        self.assertFalse(state.ready(late, 'old'))
        self.assertFalse(state.loaded)

    def test_expired_fallback_is_available_again_without_changing_choice(self):
        state = self.state()
        state.unavailable = {'pcn': 1, 'osm': 1}
        state.choose(now=2)
        self.assertEqual(state.source, 'opentopomap')
        state.choose(now=182)
        self.assertEqual(state.source, 'pcn')
        self.assertEqual(state.choice, 'auto')

    def test_fallback_never_substitutes_sentinel_for_a_detailed_orthophoto(self):
        state = self.state()
        state.set_source('pcn')
        state.unavailable['pcn'] = time.monotonic()
        state.set_view((-100, -100, 100, 100), 1)
        self.assertEqual(state.source, 'osm')
        state.set_view((-100, -100, 100, 100), 25)
        self.assertEqual(state.source, 'eox-2016')


class LocalServer:
    def __init__(self):
        import http.server
        import threading
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QColor, QImage
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor('#4f905c'))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')
        self.png, self.asked = bytes(data), []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                owner.asked.append((self.path, self.headers.get('User-Agent')))
                bad = '/bad/' in self.path
                body = b'<ServiceException>archive unavailable</ServiceException>' if bad else owner.png
                self.send_response(200)
                self.send_header('Content-Type', 'text/xml' if bad else 'image/png')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.root = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class LoaderTests(unittest.TestCase):
    def test_camera_settlement_keeps_unchanged_map_items_and_announces_visibility(self):
        from meridiana.quick.backend.plan_tiles import MapController
        with tempfile.TemporaryDirectory() as cache:
            maps = MapController(Path(cache), offline=True)
            maps.setSource('none')
            announced = []
            maps.changed.connect(lambda: announced.append(maps.worldVisible))
            for offset in range(10):
                maps.updateView(-100+offset, -100, 100+offset, 100, 1+offset/10, 1)
            self.assertEqual(announced, [], 'An unchanged background must not rebuild its QML delegates')
            maps.updateView(-1000, -1000, 1000, 1000, 300, 1)
            self.assertEqual(announced, [True])
            maps.updateView(-100, -100, 100, 100, 1, 1)
            self.assertEqual(announced, [True, False])
            self.assertFalse(maps.loader.queued)
            self.assertFalse(maps.loader.in_flight)
            maps.close()

    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def wait(self, condition):
        deadline = time.monotonic() + 5
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(condition())

    def test_cached_tile_is_async_deduplicated_offline_and_has_exact_pixels(self):
        import threading
        from PySide6.QtGui import QColor, QImage
        from meridiana.quick.backend import plan_tiles
        with tempfile.TemporaryDirectory() as cache:
            loader = plan_tiles.TileLoader(Path(cache))
            loader.offline = True
            path = loader._path('osm', 17, 1, 2)
            path.parent.mkdir(parents=True)
            image = QImage(256, 256, QImage.Format.Format_RGB32)
            image.fill(QColor('#c8b89a'))
            self.assertTrue(image.save(str(path), 'PNG'))
            got = []
            loader.tileReady.connect(lambda *args: got.append(args))
            threads = []
            with mock.patch.object(plan_tiles, 'QImage', side_effect=lambda *args:
                                   (threads.append(threading.current_thread()), QImage(*args))[1]):
                loader.request('osm', 17, 1, 2)
                loader.request('osm', 17, 1, 2)
                self.assertEqual(got, [])
                self.wait(lambda: bool(got))
            self.assertTrue(threads)
            self.assertNotIn(threading.main_thread(), threads)
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0][4].pixelColor(20, 20).name(), '#c8b89a')
            loader.request('osm', 17, 1, 3)
            self.assertEqual(len(loader.in_flight), 0)
            loader.close()

    def test_quick_underlay_pixels_keep_north_up_and_are_above_the_veil(self):
        import base64
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QUrl
        from PySide6.QtGui import QColor, QImage
        from PySide6.QtQml import QQmlApplicationEngine
        from meridiana.quick.backend.plan_tiles import MapController
        from meridiana.underlay import Underlay
        image = QImage(20, 10, QImage.Format.Format_RGB32)
        image.fill(QColor('#df3245'))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')
        with tempfile.TemporaryDirectory() as cache:
            maps = MapController(Path(cache), offline=True)
            maps.configure(underlays=[Underlay('test', image=base64.b64encode(data).decode(),
                                             width=20, height=10, x=-10, y=5, scale=1, opacity=1)])
            maps.setVeil(.8)
            engine = QQmlApplicationEngine()
            from meridiana.quick.backend.controls import install_controls
            install_controls(engine)
            engine.addImportPath(str(Path(__file__).resolve().parents[3]/"src/meridiana/quick/qml"))
            maps.install(engine)
            engine.rootContext().setContextProperty('mapsBackend', maps)
            layer = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan'
            engine.loadData(('import QtQuick\nimport QtQuick.Window\nimport "' + layer.as_uri() +
                             '"\nWindow { width: 480; height: 320; visible: true; '
                             'MapLayer { anchors.fill: parent; backend: mapsBackend; viewScale: 10; '
                             'offsetX: 240; offsetY: 160 } }').encode(), QUrl('file:///map-test.qml'))
            self.assertTrue(engine.rootObjects(), 'MapLayer QML must load')
            window = engine.rootObjects()[0]
            self.wait(lambda: window.isExposed())
            self.wait(lambda: not window.grabWindow().isNull())
            grab = window.grabWindow()
            dpr = grab.devicePixelRatio()
            self.assertEqual(grab.pixelColor(round(240 * dpr), round(160 * dpr)).name(), '#df3245')
            self.assertNotEqual(grab.pixelColor(round(240 * dpr), round(100 * dpr)).name(), '#df3245')
            output = Path(f'build/quick-foto/pianta/maps-underlay-{grab.devicePixelRatio():g}x.png')
            output.parent.mkdir(parents=True, exist_ok=True)
            grab.save(str(output))
            window.close()
            maps.close()
            engine.deleteLater()

    def test_xml_failure_retries_then_falls_back_and_keeps_the_saved_choice(self):
        from meridiana.quick.backend import plan_tiles
        server = LocalServer()
        self.addCleanup(server.close)
        sources = {
            'pcn': tiles.Source('pcn', 'Broken photo', 'xyz', server.root + '/bad/{z}/{x}/{y}.png',
                                'Photo credit', rank=40),
            'osm': tiles.Source('osm', 'Good map', 'xyz', server.root + '/good/{z}/{x}/{y}.png',
                                'Map credit', imagery='map', rank=20),
        }
        with tempfile.TemporaryDirectory() as cache, mock.patch.object(plan_tiles, 'RETRIES', (.0,)):
            maps = plan_tiles.MapController(Path(cache), sources=sources)
            maps.updateView(-300, -300, 300, 300, 1, 1)
            self.wait(lambda: maps.state.source == 'osm' and bool(maps.state.loaded))
            self.assertEqual(maps.state.choice, 'auto')
            self.assertIn('Geoportale Nazionale', maps.state.fallback_message)
            self.assertIn('Map credit', maps.state.attribution)
            bad_paths = [p for p, _ua in server.asked if p.startswith('/bad/')]
            self.assertTrue(any(bad_paths.count(path) == 2 for path in bad_paths))
            self.assertTrue(all(ua == plan_tiles.USER_AGENT.decode() for _p, ua in server.asked))
            maps.close()
            self.app.processEvents()

    def test_custom_key_never_enters_cache_or_errors_and_missing_key_sends_nothing(self):
        from dataclasses import replace
        from meridiana.quick.backend import plan_tiles
        server = LocalServer()
        self.addCleanup(server.close)
        custom = dict(key='user-test', name='Designer', kind='xyz', attribution='Designer credit',
                      url=server.root + '/bad/{z}/{x}/{y}.png?key={key}')
        with tempfile.TemporaryDirectory() as cache:
            loader = plan_tiles.TileLoader(Path(cache), sources=tiles.catalogue([custom]))
            failed = []
            loader.tileFailed.connect(lambda *args: failed.append(args))
            with mock.patch('meridiana.assistant.keys.get', return_value='secret-1234') as looked_up, \
                    mock.patch.object(plan_tiles, 'RETRIES', (.0,)):
                loader.request('user-test', 3, 1, 2)
                self.wait(lambda: bool(failed))
            looked_up.assert_called_once_with('user-test', service='meridiana-maps')
            self.assertEqual(len(server.asked), 2)
            self.assertIn('secret-1234', server.asked[0][0])
            self.assertNotIn('secret-1234', failed[0][4])
            self.assertNotIn('secret-1234', str(loader._path('user-test', 3, 1, 2)))
            loader.keys['user-test'] = ''
            loader.request('user-test', 3, 1, 3)
            self.assertEqual(len(server.asked), 2)
            self.assertIn('no key', failed[-1][4])
            loader.keys['user-test'] = 'secret-1234'
            loader.sources['user-test'] = replace(loader.sources['user-test'],
                                                  url=custom['url'].replace('/bad/', '/good/'))
            received = []
            loader.tileReady.connect(lambda *args: received.append(args))
            loader.request('user-test', 3, 1, 4)
            self.wait(lambda: bool(received))
            self.assertEqual(received[0][4].pixelColor(20, 20).name(), '#4f905c')
            path = loader._path('user-test', 3, 1, 4)
            self.assertTrue(path.is_file())
            self.assertIn('user-test-', path.as_posix())
            self.assertNotIn('secret-1234', path.as_posix())
            loader.close()

    def test_obsolete_retry_does_not_send_a_request_after_the_view_changes(self):
        from meridiana.quick.backend import plan_tiles
        server = LocalServer()
        self.addCleanup(server.close)
        source = tiles.Source('osm', 'Test', 'xyz', server.root + '/bad/{z}/{x}/{y}.png', 'credit')
        with tempfile.TemporaryDirectory() as cache, mock.patch.object(plan_tiles, 'RETRIES', (.1,)):
            loader = plan_tiles.TileLoader(Path(cache), sources={'osm': source})
            loader.request('osm', 3, 1, 2)
            self.wait(lambda: bool(loader.retrying))
            loader.keep_only(set())
            self.wait(lambda: not loader.retrying)
            self.assertEqual(len(server.asked), 1)
            loader.close()

    def test_corrupt_cache_requests_image_online_and_offline_never_asks(self):
        from meridiana.quick.backend.plan_tiles import TileLoader
        server = LocalServer()
        self.addCleanup(server.close)
        source = tiles.Source('osm', 'Local', 'xyz', server.root + '/good/{z}/{x}/{y}.png', 'Credit')
        with tempfile.TemporaryDirectory() as cache:
            loader = TileLoader(Path(cache), sources={'osm': source})
            path = loader._path('osm', 3, 1, 2)
            path.parent.mkdir(parents=True)
            path.write_text('corrupt image')
            loader.offline = True
            loader.request('osm', 3, 1, 2)
            self.wait(lambda: not loader.decoding)
            self.assertEqual(server.asked, [])
            loader.offline = False
            received = []
            loader.tileReady.connect(lambda *args: received.append(args))
            loader.request('osm', 3, 1, 2)
            self.wait(lambda: bool(received))
            self.assertEqual(len(server.asked), 1)
            self.assertEqual(received[0][4].pixelColor(20, 20).name(), '#4f905c')
            loader.close()

    def test_offline_stops_pending_queue_and_a_destroyed_loader_cancels_retry(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtTest import QTest
        from meridiana.quick.backend import plan_tiles
        server = LocalServer()
        self.addCleanup(server.close)
        source = tiles.Source('osm', 'Local', 'xyz', server.root + '/bad/{z}/{x}/{y}.png', 'Credit')
        with tempfile.TemporaryDirectory() as cache, mock.patch.object(plan_tiles, 'RETRIES', (.1,)):
            loader = plan_tiles.TileLoader(Path(cache), sources={'osm': source})
            tile = ('osm', 3, 1, 2)
            loader.offline = True
            loader.queue.append(tile)
            loader.queued.add(tile)
            loader._pump()
            self.assertEqual(server.asked, [])
            self.assertIn(tile, loader.queue)
            loader.offline = False
            loader._pump()
            self.wait(lambda: bool(loader.retrying))
            loader.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            QTest.qWait(150)
            self.assertEqual(len(server.asked), 1)

    def test_missing_keyring_and_removed_source_send_no_requests(self):
        from meridiana.assistant import keys
        from meridiana.quick.backend import plan_tiles
        server = LocalServer()
        self.addCleanup(server.close)
        custom = dict(key='user-test', name='Designer', kind='xyz', attribution='Credit',
                      url=server.root + '/good/{z}/{x}/{y}.png?key={key}')
        with tempfile.TemporaryDirectory() as cache:
            loader = plan_tiles.TileLoader(Path(cache), sources=tiles.catalogue([custom]))
            failed = []
            loader.tileFailed.connect(lambda *args: failed.append(args))
            with mock.patch('meridiana.assistant.keys.get', side_effect=keys.KeyringMissing('no backend')) as asked, \
                    mock.patch('meridiana.log.complain'):
                loader.request('user-test', 3, 1, 2)
                loader.request('user-test', 3, 1, 3)
                loader.request('gone-source', 3, 1, 4)
                asked.assert_called_once_with('user-test', service='meridiana-maps')
            self.assertEqual(server.asked, [])
            self.assertEqual(len(failed), 2)
            loader.close()

    def test_quick_world_draws_country_pixels_and_labels_at_a_real_window(self):
        from PySide6.QtCore import QRectF, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from meridiana.quick.backend.plan_tiles import MapController
        with tempfile.TemporaryDirectory() as cache:
            maps = MapController(Path(cache), offline=True)
            maps.setSource('none')
            maps.updateView(-21e6, -11e6, 21e6, 11e6, 35000, 1)
            engine = QQmlApplicationEngine()
            from meridiana.quick.backend.controls import install_controls
            install_controls(engine)
            engine.addImportPath(str(Path(__file__).resolve().parents[3]/"src/meridiana/quick/qml"))
            maps.install(engine)
            engine.rootContext().setContextProperty('mapsBackend', maps)
            layer = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan'
            engine.loadData(('import QtQuick\nimport QtQuick.Window\nimport "' + layer.as_uri() +
                             '"\nWindow { width: 1200; height: 750; visible: true; '
                             'MapLayer { anchors.fill: parent; backend: mapsBackend; viewScale: 1 / 35000; '
                             'offsetX: 600; offsetY: 210 } }').encode(), QUrl('file:///world-test.qml'))
            self.assertTrue(engine.rootObjects(), 'World MapLayer QML must load')
            window = engine.rootObjects()[0]
            self.wait(lambda: window.isExposed())
            self.wait(lambda: not window.grabWindow().isNull())
            def descendants(item):
                for child in item.childItems():
                    yield child
                    yield from descendants(child)
            labels = [item for item in descendants(window.contentItem())
                      if item.objectName() == 'mapCountryLabel' and item.property('visible')]
            self.assertGreater(len(labels), 10)
            occupied = []
            for label in labels:
                rect = QRectF(label.property('x'), label.property('y'),
                              label.property('width'), label.property('height'))
                self.assertFalse(any(rect.intersects(other) for other in occupied), label.property('text'))
                occupied.append(rect)
            grab = window.grabWindow()
            output = Path(f'build/quick-foto/pianta/maps-world-{grab.devicePixelRatio():g}x.png')
            output.parent.mkdir(parents=True, exist_ok=True)
            grab.save(str(output))
            colors = {grab.pixelColor(x, y).name() for x in range(0, grab.width(), 4)
                      for y in range(0, grab.height(), 4)}
            self.assertIn('#263943', colors)
            for land in ('#52665b', '#5c6858', '#4e6261'):
                self.assertTrue(land in colors, land)
            dpr = grab.devicePixelRatio()
            self.assertEqual(grab.pixelColor(round(600 * dpr), round(210 * dpr)).name(), '#ff38c8')
            window.close()
            maps.close()
            engine.deleteLater()

    def test_quick_tile_provider_georeferences_image_pixels_and_applies_veil(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QColor, QImage, QPainter
        from PySide6.QtQml import QQmlApplicationEngine
        from meridiana.quick.backend.plan_tiles import MapController
        z, x, y = 15, 17200, 11700
        west, south, east, north = geo.tile_bounds(x, y, z)
        lon, lat = geo.mercator_to_lonlat((west + east) / 2, (south + north) / 2)
        origin = geo.Origin(lat, lon)
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor('#4080c0'))
        painter = QPainter(image)
        painter.fillRect(0, 0, 128, 256, QColor('#c08040'))
        painter.end()
        source = tiles.Source('local', 'Local', 'xyz', 'http://127.0.0.1/{z}/{x}/{y}.png',
                              'Local credit', min_zoom=z, max_zoom=z)
        with tempfile.TemporaryDirectory() as cache:
            maps = MapController(Path(cache), origin=origin, sources={'local': source}, offline=True)
            maps.setSource('local')
            maps.updateView(-300, -200, 300, 200, 1, 1)
            maps._ready('local', z, x, y, image)
            maps.setVeil(.5)
            engine = QQmlApplicationEngine()
            from meridiana.quick.backend.controls import install_controls
            install_controls(engine)
            engine.addImportPath(str(Path(__file__).resolve().parents[3]/"src/meridiana/quick/qml"))
            maps.install(engine)
            engine.rootContext().setContextProperty('mapsBackend', maps)
            layer = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan'
            engine.loadData(('import QtQuick\nimport QtQuick.Window\nimport "' + layer.as_uri() +
                             '"\nWindow { width: 600; height: 400; visible: true; '
                             'MapLayer { anchors.fill: parent; backend: mapsBackend; viewScale: 1; '
                             'offsetX: 300; offsetY: 200 } }').encode(), QUrl('file:///tile-test.qml'))
            self.assertTrue(engine.rootObjects())
            window = engine.rootObjects()[0]
            self.wait(lambda: window.isExposed())
            self.wait(lambda: not window.grabWindow().isNull())
            grab = window.grabWindow()
            dpr = grab.devicePixelRatio()
            left = grab.pixelColor(round(250 * dpr), round(200 * dpr))
            right = grab.pixelColor(round(350 * dpr), round(200 * dpr))
            for got, expected in zip(left.getRgb()[:3], (96, 64, 32), strict=True):
                self.assertLessEqual(abs(got - expected), 1)
            for got, expected in zip(right.getRgb()[:3], (32, 64, 96), strict=True):
                self.assertLessEqual(abs(got - expected), 1)
            output = Path(f'build/quick-foto/pianta/maps-tiles-{grab.devicePixelRatio():g}x.png')
            output.parent.mkdir(parents=True, exist_ok=True)
            grab.save(str(output))
            window.close()
            maps.close()
            engine.deleteLater()


if __name__ == '__main__':
    unittest.main()
