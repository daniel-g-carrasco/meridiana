"""What a map server says of itself (capabilities.py, R36), read from documents the servers gave on 25/10/2026
(tests/data/mappe, with its README): the layers usable on the plan, the WMTS matrices on Google's grid whatever their
names, the systems of a WMS inherited from the parent layers, the terms, a server's error said with its words, and the
designer's source made from a layer, ready for tiles.py. No network."""

import unittest

import _setup

from meridiana import capabilities, tiles

FOLDER = _setup.DATA / "mappe"


def read(name: str) -> capabilities.Capabilities:
    return capabilities.read((FOLDER / name).read_bytes())


class Wmts(unittest.TestCase):
    def test_pdok_rest_and_key_value_pairs_its_two_digit_matrices_and_the_dutch_grid_left_out(self):
        caps = read("wmts-pdok.xml")
        self.assertEqual((caps.kind, caps.version, caps.provider), ("wmts", "1.0.0", "PDOK"))
        self.assertEqual(caps.url, "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0?")
        layer = caps.layer("Actueel_orthoHR")
        self.assertEqual((layer.matrix_set, layer.matrices[0], layer.matrices[5], layer.matrices[21], len(layer.matrices)),
                         ("EPSG:3857", "00", "05", "21", 22))                 # EPSG:28992, the Dutch grid: not used
        self.assertEqual(layer.template, "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/"
                                         "{TileMatrixSet}/{TileMatrix}/{TileCol}/{TileRow}.jpeg")
        self.assertEqual(layer.problem("wmts"), "")
        d = capabilities.source_dict(caps, layer, "user-00000001", "", "https://service.pdok.nl/hwh/luchtfotorgb/wmts/"
                                     "v1_0?request=GetCapabilities&service=WMTS", "2026-10-25")
        s = tiles.custom_source({**d, "attribution": "Luchtfoto © Beeldmateriaal.nl, CC BY 4.0"})
        self.assertEqual(s.tile_url(18, 134634, 86146), tiles.SOURCES["nl-pdok"].tile_url(18, 134634, 86146))
        self.assertEqual((s.min_zoom, s.max_zoom), (0, 21))

    def test_nrw_names_zoom_five_00_and_says_its_licence(self):
        caps = read("wmts-nrw.xml")
        [layer] = caps.layers
        self.assertEqual((layer.name, layer.matrix_set), ("nw_dop", "EPSG_3857_16"))  # not EPSG_25832_16
        self.assertEqual(layer.matrices[:6], ("", "", "", "", "", "00"))
        self.assertEqual((layer.matrices[18], len(layer.matrices)), ("13", 22))
        self.assertIn("Datenlizenz Deutschland – Zero", caps.terms())
        d = capabilities.source_dict(caps, layer, "user-00000002", "NRW", "https://www.wmts.nrw.de/geobasis/"
                                     "wmts_nw_dop/1.0.0/WMTSCapabilities.xml", "2026-10-25")
        self.assertEqual((d["min_zoom"], d["max_zoom"], d["kind"]), (5, 21, "wmts"))
        s = tiles.custom_source(d)                   # the provider's name is the attribution until it is written
        self.assertEqual(s.attribution, "Geobasis NRW")
        self.assertEqual(s.tile_url(18, 136003, 87497), tiles.SOURCES["de-nw"].tile_url(18, 136003, 87497))

    def test_swisstopo_fills_its_time_and_its_style_in_the_template(self):
        caps = read("wmts-swisstopo.xml")
        layer = caps.layer("ch.swisstopo.swissimage")
        self.assertEqual(layer.template, "https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/"
                                         "{TileMatrix}/{TileCol}/{TileRow}.jpeg")
        self.assertEqual((layer.matrix_set, len(layer.matrices)), ("3857_20", 21))
        self.assertEqual(layer.bbox, (5.140242, 45.398181, 11.47757, 48.230651))

    def test_ign_by_key_value_pairs_only_with_its_default_style(self):
        caps = read("wmts-ign.xml")
        self.assertEqual(caps.url, "https://data.geopf.fr/wmts?SERVICE=WMTS&")
        self.assertIn("cartes.gouv.fr/cgu", caps.terms())
        ortho = caps.layer("ORTHOIMAGERY.ORTHOPHOTOS")
        hr = caps.layer("HR.ORTHOIMAGERY.ORTHOPHOTOS")
        self.assertEqual((ortho.template, ortho.styles, ortho.matrix_set), ("", ("normal",), "PM_0_19"))
        self.assertEqual((hr.matrix_set, hr.matrices[5], hr.matrices[6]), ("PM_6_19", "", "6"))
        d = capabilities.source_dict(caps, ortho, "user-00000003", "IGN", "https://data.geopf.fr/wmts?SERVICE=WMTS&"
                                     "REQUEST=GetCapabilities", "2026-10-25")
        s = tiles.custom_source(d)
        self.assertEqual(s.tile_url(18, 132784, 90184), tiles.SOURCES["fr-ign"].tile_url(18, 132784, 90184))
        self.assertEqual(capabilities.source_dict(caps, hr, "user-4", "HR", "x", "")["min_zoom"], 6)


class Wms(unittest.TestCase):
    def test_wallonia_without_web_mercator_is_asked_in_degrees(self):
        caps = read("wms-wallonie.xml")
        self.assertEqual((caps.kind, caps.version), ("wms", "1.3.0"))
        [layer] = caps.layers
        self.assertEqual((layer.name, layer.crs), ("0", ("CRS:84", "EPSG:4326", "EPSG:31370")))
        self.assertEqual(capabilities.choose_crs(layer.crs), "CRS:84")
        d = capabilities.source_dict(caps, layer, "user-00000005", "", "https://geoservices.wallonie.be/arcgis/"
                                     "services/IMAGERIE/ORTHO_LAST/MapServer/WMSServer?request=GetCapabilities&"
                                     "service=WMS", "2026-10-25")
        self.assertEqual((d["crs"], d["format"], d["name"]), ("CRS:84", "image/jpeg", "ORTHO"))
        self.assertEqual(d["url"], "https://geoservices.wallonie.be/arcgis/services/IMAGERIE/ORTHO_LAST/MapServer/"
                                   "WMSServer")
        self.assertEqual(tiles.problems({**d, "attribution": "SPW"}), [])
        self.assertTrue(tiles.problems(d))           # the server gives no attribution: the designer writes it

    def test_bavaria_in_1_1_1_its_parent_systems_inherited_and_its_own_parameter_kept(self):
        caps = read("wms-bayern-111.xml")
        self.assertEqual(caps.version, "1.1.1")
        layer = caps.layer("by_dop20c")
        self.assertIn("EPSG:3857", layer.crs)        # declared on the parent layer
        self.assertIn("CC BY 4.0", caps.terms())
        d = capabilities.source_dict(caps, layer, "user-00000006", "", "https://geoservices.bayern.de/od/wms/dop/v1/"
                                     "dop20?SERVICE=WMS&REQUEST=GetCapabilities", "2026-10-25")
        self.assertEqual((d["url"], d["crs"], d["version"]),
                         ("https://geoservices.bayern.de/od/wms/dop/v1/dop20?language=ger", "EPSG:3857", "1.1.1"))
        url = tiles.custom_source({**d, "attribution": "Bayerische Vermessungsverwaltung"}).tile_url(18, 1, 1)
        self.assertIn("?language=ger&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=by_dop20c&", url)
        self.assertIn("&SRS=EPSG:3857&", url)

    def test_an_error_of_the_server_and_what_is_not_capabilities_are_said(self):
        with self.assertRaisesRegex(ValueError, "Could not find layer stem:nonexistent"):
            read("wms-errore.xml")
        for data, why in ((b"<html><body>Maintenance</body></html>", "not the capabilities"),
                          (b"\x89PNG\r\n", "not XML"), (b"", "not XML")):
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                capabilities.read(data)


class Addresses(unittest.TestCase):
    def test_the_capabilities_are_asked_with_what_the_designer_pasted(self):
        self.assertEqual(capabilities.capabilities_url("https://geo.api.vlaanderen.be/omwrgbmrvl/wmts", "wmts"),
                         "https://geo.api.vlaanderen.be/omwrgbmrvl/wmts?SERVICE=WMTS&REQUEST=GetCapabilities")
        self.assertEqual(capabilities.capabilities_url(" https://x.example/wms?map=a ", "wms"),
                         "https://x.example/wms?map=a&SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0")
        for kept in ("https://wmts.geo.admin.ch/EPSG/3857/1.0.0/WMTSCapabilities.xml",
                     "https://x.example/wms?service=WMS&request=GetCapabilities"):
            self.assertEqual(capabilities.capabilities_url(kept, "wms"), kept)
        self.assertEqual(capabilities.base_url("http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/"
                                               "ortofoto_colore_12.map&service=WMS&request=GetCapabilities"),
                         "http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/ortofoto_colore_12.map")


if __name__ == "__main__":
    unittest.main()
