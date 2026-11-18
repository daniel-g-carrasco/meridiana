"""Preferences > Maps (ui/map_sources.py, R36): the background to start from among the sources of the site, the
sources as rows with their licences, the designer's own sources: an XYZ template, a WMS or a WMTS from capabilities
recorded on 25/10/2026 (tests/data/mappe), unused while the attribution is missing, the key to the keyring, the
network asked only when Privacy allows it. PySide6 and a display (offscreen will do); no network."""

import unittest
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

RHO = (45.5226, 9.0300)
DATA = _setup.DATA / "mappe"


class MapsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def page(self, **changes):
        from meridiana import config
        from meridiana.ui.map_sources import MapsPage
        cfg = config.Config(**changes)
        page = MapsPage(cfg, RHO, network=lambda: False)
        self.addCleanup(page.deleteLater)
        return page

    def type(self, field, text):
        from PySide6.QtTest import QTest
        field.selectAll()
        field.del_()
        QTest.keyClicks(field, text)

    def test_the_background_to_start_from_is_one_of_the_site_and_the_sources_are_rows_with_their_licence(self):
        from meridiana import tiles
        from meridiana.ui.rows import RowList
        page = self.page()
        data = [page.default.itemData(i) for i in range(page.default.count())]
        self.assertEqual(data, ["auto", "pcn", "eox-2016", "osm", "opentopomap", "none"])
        self.assertEqual(page.default.itemText(0), "Automatic: Italy: orthophoto 2012 (Geoportale Nazionale)")
        here, every = page.findChildren(RowList)
        self.assertEqual([r[0] for r in here.texts()][:2], ["Italy: orthophoto 2012 (Geoportale Nazionale)",
                                                            "World: Sentinel-2 cloudless 2016 (10 m)"])
        self.assertEqual(len(every.texts()), len(tiles.SOURCES))
        self.assertIn(("France: IGN orthophotos", "Licence Ouverte 2.0 (Etalab)"), every.texts())
        self.assertIn(("OpenStreetMap", "ODbL data; OpenStreetMap's tile usage policy"), every.texts())
        from meridiana import i18n                                       # the words of a licence in the language
        italian = i18n.translation_for("it")
        with mock.patch.object(i18n, "_translation", italian):
            self.assertEqual(tiles.display_licence(tiles.SOURCES["pl-gugik"]),
                             "libera per qualsiasi uso, senza prelievo massivo")
            self.assertEqual(tiles.display_licence(tiles.SOURCES["fr-ign"]), "Licence Ouverte 2.0 (Etalab)")
        page.default.setCurrentIndex(page.default.findData("osm"))
        self.assertEqual(page.choice(), ("osm", []))
        # a source chosen on a project elsewhere is still offered, said as not at this site
        elsewhere = self.page(background="fr-ign")
        self.assertEqual(elsewhere.default.currentText(), "France: IGN orthophotos (not at this site)")
        self.assertEqual(elsewhere.choice()[0], "fr-ign")

    def test_an_xyz_source_is_not_used_until_it_has_its_attribution_and_its_key_goes_to_the_keyring(self):
        from meridiana import tiles
        page = self.page()
        page._add()
        self.assertEqual(page.chooser.count(), 1)
        self.type(page.name, "Comune di Rho")
        with mock.patch("meridiana.assistant.keys.get", return_value="") as asked:      # never the PC's own keyring
            self.type(page.url, "https://tiles.example.org/{z}/{x}/{y}.jpg?key={key}")
        self.assertEqual(asked.call_count, 1)                             # asked once, not at every key typed
        self.assertEqual(page.key_state.text(), "No key yet.")
        self.assertIn("attribution", page.problems.text())
        self.assertIn("(not used yet)", page.chooser.itemText(0))
        self.type(page.attribution, "© Comune di Rho")
        self.assertEqual(page.problems.text(), "")
        self.assertEqual(page.chooser.itemText(0), "Comune di Rho")
        [d] = page.choice()[1]
        self.assertNotEqual(page.default.findData(d["key"]), -1)          # usable, and everywhere: a default too
        s = tiles.custom_source(d)
        self.assertTrue(s.needs_key)
        self.assertNotIn("key=", "".join(str(v) for k, v in d.items() if k != "url"))
        self.assertTrue(page.set_key.isEnabled())
        with mock.patch("meridiana.ui.map_sources.QInputDialog.getText", return_value=("abc-123-secret-9876", True)), \
                mock.patch("meridiana.assistant.keys.put") as put:
            page._set_key()
        put.assert_called_once_with(d["key"], "abc-123-secret-9876", service="meridiana-maps")
        self.assertEqual(page.key_state.text(), "Key in the system's keyring: abc-123…9876")     # masked
        with mock.patch("meridiana.assistant.keys.forget") as forget:
            page._remove()
        forget.assert_called_once_with(d["key"], service="meridiana-maps")
        self.assertEqual((page.chooser.count(), page.choice()[1]), (0, []))

    def test_a_wms_and_a_wmts_from_their_capabilities_with_the_network_asked_only_when_allowed(self):
        from meridiana import tiles
        page = self.page()
        page._add()
        page.kind.setCurrentIndex(page.kind.findData("wms"))
        self.type(page.url, "https://geoservices.wallonie.be/arcgis/services/IMAGERIE/ORTHO_LAST/MapServer/WMSServer")
        page.read_capabilities()                                          # Privacy has the map servers off
        self.assertIn("Privacy", page.read_state.text())
        page.show_capabilities((DATA / "wms-wallonie.xml").read_bytes())
        self.assertEqual((page.layer.count(), page.layer.currentData()), (1, "0"))
        d = page.choice()[1][0]
        self.assertEqual((d["kind"], d["crs"], d["layer"], d["name"]), ("wms", "CRS:84", "0", "ORTHO"))
        self.assertIn("attribution", page.problems.text())                # the server gives none
        self.type(page.attribution, "Source : SPW, CC BY 4.0")
        self.assertIsNotNone(tiles.custom_source(page.choice()[1][0]))
        # a WMTS read where a WMS was said: the type follows the server, the matrices come with the layer
        page._add()
        page.kind.setCurrentIndex(page.kind.findData("wms"))
        self.type(page.url, "https://www.wmts.nrw.de/geobasis/wmts_nw_dop/1.0.0/WMTSCapabilities.xml")
        page.show_capabilities((DATA / "wmts-nrw.xml").read_bytes())
        d = page.choice()[1][1]
        self.assertEqual((d["kind"], d["matrix_set"], d["min_zoom"], d["attribution"]),
                         ("wmts", "EPSG_3857_16", 5, "Geobasis NRW"))
        self.assertEqual(page.problems.text(), "")
        self.assertIn("1 layers usable", page.read_state.text())
        page.show_capabilities(b"<html>Wartungsarbeiten</html>")          # what a server says when it is down
        self.assertIn("Not readable", page.read_state.text())
        page.show_capabilities(None, "Connection refused")
        self.assertIn("Connection refused", page.read_state.text())
        # the default is chosen among the sources that cover the site: neither Wallonia nor NRW covers Rho
        for mine in page.choice()[1]:
            self.assertEqual(page.default.findData(mine["key"]), -1)


if __name__ == "__main__":
    unittest.main()
