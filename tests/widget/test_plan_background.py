"""Visible fallback of the plan's background: valid tiles stay while replacements arrive, failed tiles use another
source for the same place, an unavailable source rests for a while, and the user's saved choice never changes.
Only a fake server on this PC is used."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state


class HalfBrokenServer:
    def __init__(self, xml=False):
        import http.server
        import threading

        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QColor, QImage

        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor("#758a68"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        self.png = bytes(data)
        self.asked = []
        self.fail = True
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                server.asked.append(self.path)
                failed = "/pcn/" in self.path and (xml or self.path.endswith("/0.png") or server.fail)
                server.fail = not server.fail
                if failed:
                    body = b"<ServiceException>archive unavailable</ServiceException>" if xml else b"missing"
                    self.send_response(200 if xml else 503)
                    self.send_header("Content-Type", "text/xml" if xml else "text/plain")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(server.png)))
                self.end_headers()
                self.wfile.write(server.png)

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class Fallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana import tiles
        from meridiana.ui.plan import PlanView

        self.server = HalfBrokenServer()
        self.addCleanup(self.server.close)
        root = f"http://127.0.0.1:{self.server.port}"
        pcn = tiles.Source("pcn", "Test orthophoto", "xyz", root + "/pcn/{z}/{x}/{y}.png",
                           "Test orthophoto", "test", "https://example.org", "2026-10-26", rank=40, custom=True)
        osm = tiles.Source("osm", "Test map", "xyz", root + "/osm/{z}/{x}/{y}.png",
                           "Test map", "test", "https://example.org", "2026-10-26", imagery="map", rank=20,
                           custom=True)
        self.view = PlanView(Path(tempfile.mkdtemp()))
        self.view.sources = {"pcn": pcn, "osm": osm}
        self.view.loader.sources = self.view.sources
        self.view.choice = "auto"
        self.view.source = "pcn"
        self.view.resize(800, 600)
        self.view.show()
        self.view.setTransform(self.view.transform().scale(0.1, 0.1))
        self.view.centerOn(0, 0)
        self.addCleanup(self.view.deleteLater)
        self.addCleanup(self.view.close)

    def test_failed_tiles_are_replaced_the_source_rests_and_retry_does_not_change_the_choice(self):
        from meridiana.ui import tileloader

        view = self.view
        with mock.patch.object(tileloader, "RETRIES", (0.0,)), \
                mock.patch("meridiana.ui.plan.FAILOVER_COOLDOWN", 180.0):
            view._update_tiles()
            self.assertTrue(_setup.wait_until(self.app, lambda: view.source == "osm", 15))
            self.assertTrue(view.fallback_strip.isVisibleTo(view))
            self.assertIn("Test orthophoto", view.fallback_strip.message.text())
            self.assertEqual(view.choice, "auto")
            pcn_asks = len([p for p in self.server.asked if p.startswith("/pcn/")])
            view._update_tiles()
            view._update_tiles()
            self.app.processEvents()
            self.assertEqual(len([p for p in self.server.asked if p.startswith("/pcn/")]), pcn_asks)
            view.fallback_strip.retry.click()
            self.assertTrue(_setup.wait_until(self.app, lambda: view.source == "pcn", 5))
            self.assertGreater(len([p for p in self.server.asked if p.startswith("/pcn/")]), pcn_asks)
            self.assertEqual(view.choice, "auto")

    def test_old_tiles_stay_until_the_new_view_is_covered(self):
        from PySide6.QtGui import QColor, QImage

        view = self.view
        view.loader.offline = True
        view._tile_ready("pcn", 3, 4, 3, QImage(256, 256, QImage.Format.Format_RGB32))
        old = view.tile_items[("pcn", 3, 4, 3)]
        view.set_source("osm")
        self.assertIn(("pcn", 3, 4, 3), view.tile_items)
        self.assertIn(old, view.scene().items())
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor("#58738b"))
        view._tile_ready("osm", 3, 4, 3, image)
        self.assertEqual(view.tile_items[("osm", 3, 4, 3)].pixmap().toImage().pixelColor(20, 20), QColor("#58738b"))

    def test_an_xml_error_document_instead_of_an_image_also_uses_the_fallback(self):
        import dataclasses

        from meridiana.ui import tileloader

        server = HalfBrokenServer(xml=True)
        self.addCleanup(server.close)
        root = f"http://127.0.0.1:{server.port}"
        view = self.view
        view.sources = {key: dataclasses.replace(source, url=root + f"/{key}/{{z}}/{{x}}/{{y}}.png")
                        for key, source in view.sources.items()}
        view.loader.sources = view.sources
        with mock.patch.object(tileloader, "RETRIES", (0.0,)):
            view._update_tiles()
            self.assertTrue(_setup.wait_until(self.app, lambda: view.source == "osm", 15))
        self.assertTrue(any(path.startswith("/pcn/") for path in server.asked))
        self.assertTrue(view.fallback_strip.isVisibleTo(view))

    def test_a_fallback_is_for_the_same_purpose_and_never_sentinel_close_up(self):
        from meridiana import tiles

        self.assertEqual(tiles.fallbacks(tiles.SOURCES, "pcn", 9.03, 45.5226, detailed=True), ["osm", "opentopomap"])
        self.assertEqual(tiles.fallbacks(tiles.SOURCES, "pcn", 9.03, 45.5226, detailed=False)[0], "eox-2016")


if __name__ == "__main__":
    unittest.main()
