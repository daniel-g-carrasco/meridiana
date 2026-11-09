"""R36 source editing, recorded capabilities and a real local asynchronous request."""
from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch

import _setup
from meridiana import config, i18n, tiles
from meridiana.quick.backend.plan_sources import MapSourcesController

def setUpModule():
    _setup.keep_global_state()
    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle('Basic')  # Same style as quick.app.create_app, before loading any control.
DATA = _setup.DATA / "mappe"
os.environ.setdefault("QSG_RENDER_LOOP", "basic")


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def page(self, **changes):
        i18n.setup("en")
        store = Mock()
        store.get.return_value = ""
        page = MapSourcesController(config.Config(**changes), (45.5226, 9.0300),
                                    network=lambda: False, key_store=store)
        self.addCleanup(page.close)
        self.addCleanup(page.deleteLater)
        return page, store

    def test_background_site_sources_and_licences(self):
        page, _store = self.page()
        self.assertEqual([row["key"] for row in page.defaultOptions],
                         ["auto", "pcn", "eox-2016", "osm", "opentopomap", "none"])
        self.assertEqual(page.defaultOptions[0]["name"],
                         "Automatic: Italy: orthophoto 2012 (Geoportale Nazionale)")
        self.assertEqual([row["name"] for row in page.siteSources][:2],
                         ["Italy: orthophoto 2012 (Geoportale Nazionale)",
                          "World: Sentinel-2 cloudless 2016 (10 m)"])
        self.assertEqual(len(page.allSources), len(tiles.SOURCES))
        rows = [(r["name"], r["licence"]) for r in page.allSources]
        self.assertIn(("France: IGN orthophotos", "Licence Ouverte 2.0 (Etalab)"), rows)
        self.assertIn(("OpenStreetMap", "ODbL data; OpenStreetMap's tile usage policy"), rows)
        page.setDefault("osm")
        self.assertEqual(page.choice(), ("osm", []))
        elsewhere, _store = self.page(background="fr-ign")
        selected = next(r for r in elsewhere.defaultOptions if r["key"] == elsewhere.defaultChoice)
        self.assertEqual(selected["name"], "France: IGN orthophotos (not at this site)")
        self.assertEqual(elsewhere.choice()[0], "fr-ign")

    def test_xyz_waits_for_attribution_and_secret_never_enters_payload(self):
        page, store = self.page()
        page.add()
        page.updateField("name", "Comune di Rho")
        page.updateField("url", "https://tiles.example.org/{z}/{x}/{y}.jpg?key={key}")
        self.assertEqual(store.get.call_count, 1)
        self.assertEqual(page.keyState, "No key yet.")
        self.assertIn("attribution", page.problems)
        self.assertIn("(not used yet)", page.customRows[0]["name"])
        page.updateField("attribution", "© Comune di Rho")
        self.assertFalse(page.problems)
        self.assertEqual(page.customRows[0]["name"], "Comune di Rho")
        row = page.choice()[1][0]
        self.assertIn(row["key"], [r["key"] for r in page.defaultOptions])
        self.assertTrue(tiles.custom_source(row).needs_key)
        self.assertTrue(page.needsKey)
        page.setKey("abc-123-secret-9876")
        store.put.assert_called_once_with(row["key"], "abc-123-secret-9876", service="meridiana-maps")
        self.assertEqual(page.keyState, "Key in the system's keyring: abc-123…9876")
        self.assertNotIn("secret", json.dumps(page.choice()))
        self.assertNotIn("secret", json.dumps(page.currentSource))
        self.assertEqual(store.get.call_count, 1)
        page.remove()
        store.forget.assert_called_once_with(row["key"], service="meridiana-maps")
        self.assertEqual(page.customRows, [])

    def test_wms_wmts_recorded_capabilities_and_privacy(self):
        page, _store = self.page()
        page.add(); page.updateField("kind", "wms")
        page.updateField("url", "https://geoservices.wallonie.be/arcgis/services/IMAGERIE/ORTHO_LAST/MapServer/WMSServer")
        page.readCapabilities()
        self.assertIn("Privacy", page.readState)
        self.assertFalse(page.busy)
        page.show_capabilities((DATA / "wms-wallonie.xml").read_bytes())
        self.assertEqual([r["key"] for r in page.layers], ["0"])
        row = page.choice()[1][0]
        self.assertEqual((row["kind"], row["crs"], row["layer"], row["name"]), ("wms", "CRS:84", "0", "ORTHO"))
        self.assertIn("attribution", page.problems)
        page.updateField("attribution", "Source : SPW, CC BY 4.0")
        self.assertIsNotNone(tiles.custom_source(page.choice()[1][0]))
        page.add(); page.updateField("kind", "wms")
        page.updateField("url", "https://www.wmts.nrw.de/geobasis/wmts_nw_dop/1.0.0/WMTSCapabilities.xml")
        page.show_capabilities((DATA / "wmts-nrw.xml").read_bytes())
        row = page.choice()[1][1]
        self.assertEqual((row["kind"], row["matrix_set"], row["min_zoom"], row["attribution"]),
                         ("wmts", "EPSG_3857_16", 5, "Geobasis NRW"))
        self.assertFalse(page.problems)
        self.assertIn("1 layers usable", page.readState)
        page.show_capabilities(b"<html>Wartungsarbeiten</html>")
        self.assertIn("Not readable", page.readState)
        page.show_capabilities(None, "Connection refused")
        self.assertIn("Connection refused", page.readState)
        for row in page.choice()[1]:
            self.assertNotIn(row["key"], [r["key"] for r in page.defaultOptions])

    def test_capabilities_request_is_async_uses_user_agent_and_refuses_stale_source(self):
        payload = (DATA / "wms-wallonie.xml").read_bytes()
        received, proceed = threading.Event(), threading.Event()
        headers = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                headers.append(dict(self.headers)); received.set(); proceed.wait(5)
                self.send_response(200); self.end_headers()
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                    # Changing source cancels the request, intentionally closing this socket.
                    return

            def log_message(self, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(proceed.set)
        page, _store = self.page()
        page.network = lambda: True
        page.add(); page.updateField("kind", "wms")
        page.updateField("url", f"http://127.0.0.1:{server.server_port}/wms")
        page.readCapabilities()
        self.assertTrue(page.busy)
        self.assertTrue(_setup.wait_until(self.app, received.is_set, 5))
        self.assertIn("Meridiana", headers[0]["User-Agent"])
        # A late answer to the first source must not fill a different editor.
        page.add(); second = page.currentSource["key"]
        proceed.set()
        self.assertTrue(_setup.wait_until(self.app, lambda: not page.busy, 5))
        self.assertEqual(page.currentSource["key"], second)
        self.assertNotIn("layer", page.currentSource)
        page.select(0); page.readCapabilities()
        self.assertTrue(_setup.wait_until(self.app, lambda: not page.busy, 5))
        self.assertEqual(page.currentSource["layer"], "0")
        original = page.currentSource
        with patch("meridiana.capabilities.MAX_BYTES", 100):
            page.readCapabilities()
            self.assertTrue(_setup.wait_until(self.app, lambda: not page.busy, 5))
            self.assertIn("Not readable", page.readState)
            self.assertEqual(page.currentSource, original)
        page.readCapabilities()
        page.network = lambda: False
        self.assertTrue(_setup.wait_until(self.app, lambda: not page.busy, 5))
        self.assertIn("Privacy", page.readState)
        self.assertEqual(page.currentSource, original)

    def test_apply_emits_a_copy_and_edited_settings_remain_a_draft(self):
        page, _store = self.page()
        page.add(); page.updateField("name", "Draft")
        captured = []
        page.applied.connect(lambda choice, sources: captured.append((choice, sources)))
        page.apply()
        self.assertEqual(captured[0], page.choice())
        captured[0][1][0]["name"] = "Listener changed its own copy"
        self.assertEqual(page.currentSource["name"], "Draft")

    def test_field_bindings_keep_spaces_between_typed_words(self):
        page, _store = self.page()
        page.add()
        for field, wanted in (("name", "Comune di Rho"), ("attribution", "Comune di Rho, CC BY 4.0")):
            value = ""
            for char in wanted:
                page.updateField(field, value+char)
                value = page.currentSource[field]
            self.assertEqual(value, wanted)

    def test_missing_keyring_has_no_secret_or_raw_exception_in_ui(self):
        from meridiana.assistant import keys
        page, store = self.page()
        store.get.side_effect = keys.KeyringMissing("backend unavailable")
        page.add(); page.updateField("url", "https://tiles.example.org/{z}/{x}/{y}?key={key}")
        self.assertIn("No keyring", page.keyState)
        store.put.side_effect = keys.KeyringMissing("failed while storing abc-secret")
        page.setKey("abc-secret")
        self.assertIn("No keyring", page.keyState)
        self.assertNotIn("abc-secret", page.keyState)
        self.assertNotIn("abc-secret", json.dumps(page.choice()))
        store.forget.side_effect = keys.KeyringMissing("unavailable")
        page.remove()
        self.assertEqual(page.customRows, [])

    def test_qml_component_loads_with_complete_editor_fields(self):
        from PySide6.QtCore import QObject, QUrl
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        from meridiana.quick.backend.tokens import install_theme
        page, _store = self.page()
        engine = self.engine = QQmlEngine()
        QQmlEngine.setObjectOwnership(page, QQmlEngine.CppOwnership)
        install_theme(engine)
        self.addCleanup(engine.deleteLater)
        component = self.component = QQmlComponent(engine, QUrl.fromLocalFile(str(
            _setup.ROOT / "src/meridiana/quick/qml/Meridiana/Plan/MapSources.qml")))
        self.assertFalse(component.errors(), [e.toString() for e in component.errors()])
        item = self.item = component.createWithInitialProperties({"backend": page, "width": 800, "height": 720})
        self.assertIsNotNone(item, [e.toString() for e in component.errors()])
        self.addCleanup(item.deleteLater)
        page.add()
        self.app.processEvents()
        for name in ("mapSource-name", "mapSource-url", "mapSource-attribution", "mapSource-licence",
                     "mapSource-licence_url", "mapSourceKind", "mapSourceLayer", "mapSetKey", "mapApply"):
            self.assertIsNotNone(item.findChild(QObject, name), name)


@unittest.skipUnless(os.environ.get("MERIDIANA_QUICK_SOURCE_WINDOW"), "opt-in real map-source window")
class SourceWindowTests(unittest.TestCase):
    page = SourceTests.page

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_xyz_editor_real_keys_secret_dialog_and_theme_photos(self):
        from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QUrl
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtQuick import QQuickView
        from PySide6.QtTest import QSignalSpy, QTest
        from meridiana.quick.backend.tokens import install_theme
        page, store = self.page()
        i18n.setup("it")
        self.view = view = QQuickView()
        install_theme(view.engine(), {"theme": "light"})
        warnings = []
        view.engine().warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        view.setInitialProperties({"backend": page})
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.setSource(QUrl.fromLocalFile(str(_setup.ROOT / "src/meridiana/quick/qml/Meridiana/Plan/MapSources.qml")))
        self.assertFalse(view.errors(), [e.toString() for e in view.errors()])
        view.resize(900, 900); view.show()
        self.addCleanup(view.close)
        self.addCleanup(view.deleteLater)
        self.assertTrue(QTest.qWaitForWindowExposed(view))
        view.requestActivate()
        self.assertTrue(QTest.qWaitForWindowActive(view))
        root = view.rootObject()
        scroll = root.findChild(QObject, "mapSourceScroll")

        def click(name):
            item = root.findChild(QObject, name)
            self.assertIsNotNone(item, name)
            offset = item.mapToItem(scroll, QPointF(0, 0)).y()
            scroll.setProperty("contentY", max(0, min(scroll.property("contentHeight")-scroll.height(),
                                                     scroll.property("contentY")+offset-scroll.height()/2)))
            # Layouts polish after scrolling. Click the rendered field, not the
            # previous frame's position while the new source editor is expanding.
            frame = QSignalSpy(view.frameSwapped)
            view.update()
            self.assertTrue(frame.wait(2000), 'Source editor did not present its layout')
            point = item.mapToScene(QPointF(item.width()/2, item.height()/2))
            self.assertTrue(0 <= point.y() <= view.height(), (name, point))
            QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, point.toPoint())
            self.app.processEvents()

        def type_field(name, text):
            click(name)
            field = root.findChild(QObject, name)
            self.assertTrue(_setup.wait_until(self.app, field.hasActiveFocus, 2), name)
            QTest.keyClick(view, Qt.Key_A, Qt.ControlModifier)
            for char in text:
                self.app.sendEvent(view, QKeyEvent(QEvent.KeyPress, ord(char.upper()) if len(char.upper()) == 1 else 0,
                                                  Qt.NoModifier, char))
                self.app.sendEvent(view, QKeyEvent(QEvent.KeyRelease, 0, Qt.NoModifier, char))

        def photo(label):
            QTest.qWait(100)
            folder = _setup.ROOT / "build/quick-foto/pianta/sources"
            folder.mkdir(parents=True, exist_ok=True)
            image = view.grabWindow()
            self.assertFalse(image.isNull())
            self.assertTrue(image.save(str(folder / f"{label}.png")))

        click("mapAdd")
        click("mapSourceKind")
        QTest.keyClick(view, Qt.Key_Escape)
        type_field("mapSource-name", "Comune di Rho")
        self.assertEqual(page.currentSource["name"], "Comune di Rho")
        type_field("mapSource-url", "https://tiles.example.org/{z}/{x}/{y}.jpg?key={key}")
        self.assertIn("attribu", page.problems)
        photo("xyz-incomplete-light")
        type_field("mapSource-attribution", "Comune di Rho, CC BY 4.0")
        self.assertFalse(page.problems)
        click("mapSetKey")
        QTest.qWait(100)
        secret = root.findChild(QObject, "mapSecret")
        self.assertTrue(secret.hasActiveFocus())
        for char in "abc-123-secret-9876":
            self.app.sendEvent(view, QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, char))
        QTest.keyClick(view, Qt.Key_Return)
        QTest.qWait(150)
        store.put.assert_called_once()
        self.assertEqual(secret.property("text"), "")
        self.assertNotIn("secret", json.dumps(page.choice()))
        photo("xyz-complete-light")
        install_theme(view.engine(), {"theme": "dark"})
        photo("xyz-complete-dark")
        view.resize(480, 720)
        photo("xyz-narrow-dark")
        self.assertFalse(warnings, warnings)


if __name__ == "__main__":
    unittest.main()
