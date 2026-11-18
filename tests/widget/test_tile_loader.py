"""The map tiles of the plan's background (ui/tileloader.py): a tile of the cache decoded away from the window's
thread and handed back through tileReady; offline the cache is read and nothing is asked; a designer's source asked
to a fake server on this PC (R36): Meridiana's User-Agent, the key from the keyring in the address and nowhere else,
a folder of the cache of its own, a refusal said without the key. PySide6 and a display (offscreen will do)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class TileCache(unittest.TestCase):
    """The tiles of the cache are read and decoded away from the window's thread and come back through
    tileReady, the same as before; offline the cache is read and nothing is asked (task 18c, step 9)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_cached_tile_is_decoded_off_the_thread_and_offline_is_respected(self):
        import threading

        from _setup import wait_until

        from meridiana.ui import tileloader
        loader = tileloader.TileLoader(Path(tempfile.mkdtemp()))
        self.addCleanup(loader.deleteLater)
        from PySide6.QtGui import QColor, QImage
        path = loader._path("osm", 17, 1, 2)                           # a .img file: the format said, not guessed
        path.parent.mkdir(parents=True)
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor("#c8b89a"))
        self.assertTrue(image.save(str(path), "PNG"))
        got = []
        loader.tileReady.connect(lambda *a: got.append(a))
        threads = []
        real = tileloader.QImage
        with mock.patch.object(tileloader, "QImage",
                               side_effect=lambda *a: (threads.append(threading.current_thread()), real(*a))[1]):
            loader.request("osm", 17, 1, 2)
            self.assertEqual(got, [])                                  # not yet: decoded away from this thread
            self.assertIn(("osm", 17, 1, 2), loader.decoding)
            loader.request("osm", 17, 1, 2)                            # asked twice: read once
            self.assertTrue(wait_until(self.app, lambda: bool(got), 10))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][:4], ("osm", 17, 1, 2))
        self.assertEqual((got[0][4].width(), got[0][4].height()), (256, 256))
        self.assertEqual(threads, [t for t in threads if t is not threading.main_thread()])
        self.assertEqual((len(loader.queue), len(loader.in_flight), loader.decoding), (0, 0, set()))
        # offline: the cache is read, the servers never asked
        loader.offline = True
        loader.request("osm", 17, 1, 2)
        self.assertTrue(wait_until(self.app, lambda: len(got) == 2, 10))
        loader.request("osm", 17, 1, 3)                                # not in the cache: nothing, nobody asked
        self.app.processEvents()
        self.assertEqual((len(loader.queue), len(loader.in_flight), loader.decoding), (0, 0, set()))
        # a file of the cache that is not an image, online: asked to the server, as before
        loader.offline = False
        bad = loader._path("osm", 17, 1, 4)
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("not an image")
        with mock.patch.object(loader, "_pump") as pump:
            loader.request("osm", 17, 1, 4)
            self.assertTrue(wait_until(self.app, lambda: pump.called, 10))
        self.assertIn(("osm", 17, 1, 4), loader.queued)
        self.assertEqual(len(got), 2)

    def test_turning_offline_stops_a_queue_not_yet_sent(self):
        from meridiana.ui import tileloader
        loader = tileloader.TileLoader(Path(tempfile.mkdtemp()))
        self.addCleanup(loader.deleteLater)
        tile = ("osm", 17, 1, 8)
        loader.queue.append(tile)
        loader.queued.add(tile)
        loader.offline = True
        loader.net.get = mock.Mock()
        loader._pump()
        loader.net.get.assert_not_called()
        self.assertIn(tile, loader.queue)


class Retry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_loader_destroyed_before_the_retry_gets_no_late_call(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtNetwork import QNetworkReply

        from meridiana.ui import tileloader
        loader = tileloader.TileLoader(Path(tempfile.mkdtemp()))
        tile = ("osm", 3, 1, 2)
        reply = mock.Mock()
        reply.readAll.return_value = b"not an image"
        reply.header.return_value = "text/plain"
        reply.error.return_value = QNetworkReply.NetworkError.NoError
        loader.in_flight[reply] = tile
        errors = []
        with mock.patch.object(tileloader, "RETRIES", (0.01,)), \
                mock.patch("sys.excepthook", side_effect=lambda kind, value, tb:
                           errors.append(f"{kind.__name__}: {value}")):
            loader._done(reply)
            loader.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            _setup.turn_events(self.app, 50)
        self.assertEqual(errors, [])


class FakeServer:
    """A map server on 127.0.0.1 (no network): a PNG for /{z}/{x}/{y}.png, 404 for row 9; what it was asked, with
    the User-Agent of each request."""

    def __init__(self):
        import http.server
        import threading

        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QColor, QImage
        image = QImage(256, 256, QImage.Format.Format_RGB32)
        image.fill(QColor("#3a6ea5"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        png = bytes(data)
        self.asked: list = []
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                server.asked.append((self.path, self.headers.get("User-Agent")))
                if "/9.png" in self.path:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png)))
                self.end_headers()
                self.wfile.write(png)

            def log_message(self, *args):
                pass                    # the suite's output stays clean: what was asked is in `asked`

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class DesignersSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.server = FakeServer()
        self.addCleanup(self.server.close)

    def source(self) -> dict:
        return {"key": "user-0a1b2c3d", "name": "Prova", "kind": "xyz", "attribution": "© Prova",
                "url": f"http://127.0.0.1:{self.server.port}/{{z}}/{{x}}/{{y}}.png?key={{key}}"}

    def test_the_key_from_the_keyring_goes_in_the_address_only_with_the_user_agent_and_a_folder_of_its_own(self):
        from _setup import wait_until

        from meridiana import tiles
        from meridiana.ui import tileloader
        cache = Path(tempfile.mkdtemp())
        loader = tileloader.TileLoader(cache, sources=tiles.catalogue([self.source()]))
        self.addCleanup(loader.deleteLater)
        got, failed = [], []
        loader.tileReady.connect(lambda *a: got.append(a))
        loader.tileFailed.connect(lambda *a: failed.append(a))
        with mock.patch("meridiana.assistant.keys.get", return_value="s3cr3t-key-1234") as asked, \
                mock.patch.object(tileloader, "RETRIES", (0.0,)):
            loader.request("user-0a1b2c3d", 3, 1, 2)
            self.assertTrue(wait_until(self.app, lambda: bool(got), 10))
            loader.request("user-0a1b2c3d", 3, 1, 9)                     # the server has not it
            self.assertTrue(wait_until(self.app, lambda: bool(failed), 10))
        asked.assert_called_once_with("user-0a1b2c3d", service="meridiana-maps")       # once, then remembered
        self.assertEqual(got[0][:4], ("user-0a1b2c3d", 3, 1, 2))
        self.assertEqual(self.server.asked[0], ("/3/1/2.png?key=s3cr3t-key-1234", tileloader.USER_AGENT.decode()))
        self.assertEqual(len([a for a in self.server.asked if "/9.png" in a[0]]), 2)        # asked again once
        self.assertNotIn("s3cr3t-key-1234", failed[0][4])                  # what is said of the failure: masked
        [folder] = (cache / "tiles").iterdir()
        self.assertTrue(folder.name.startswith("user-0a1b2c3d-"))
        self.assertTrue((folder / "3" / "1" / "2.img").is_file())
        self.assertNotIn("s3cr3t", "".join(str(f) for f in folder.rglob("*")))

    def test_without_a_key_or_with_the_servers_off_nothing_is_asked(self):
        from meridiana import tiles
        from meridiana.assistant import keys
        from meridiana.ui import tileloader
        loader = tileloader.TileLoader(Path(tempfile.mkdtemp()), sources=tiles.catalogue([self.source()]))
        self.addCleanup(loader.deleteLater)
        failed = []
        loader.tileFailed.connect(lambda *a: failed.append(a))
        with mock.patch("meridiana.assistant.keys.get", side_effect=keys.KeyringMissing("no backend")), \
                mock.patch("meridiana.log.complain"):
            loader.request("user-0a1b2c3d", 3, 1, 2)
        self.assertEqual(failed[0][4], "no key for this source in the system's keyring")
        loader.offline = True                                             # Preferences > Privacy, the map servers off
        loader.keys["user-0a1b2c3d"] = "a-key"
        loader.request("user-0a1b2c3d", 3, 1, 3)
        loader.request("a-source-gone", 3, 1, 3)                          # one the plan no longer has: nothing
        self.app.processEvents()
        self.assertEqual((self.server.asked, len(loader.queue), len(loader.in_flight)), ([], 0, 0))


if __name__ == "__main__":
    unittest.main()
