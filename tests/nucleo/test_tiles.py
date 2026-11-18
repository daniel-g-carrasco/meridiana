"""Background tiles: the right zoom for the screen, the tiles that cover the view, placed where they belong; the
map sources as data (R36): the addresses of XYZ, WMTS and WMS, where each source covers, the best one for a site, the
designer's own sources as the settings keep them. No network: tools/try_map_sources.py asks the servers."""

import math
import unittest

import _setup  # noqa: F401

from meridiana import geo, tiles

RHO = geo.Origin(lat=45.5226, lon=9.0300)


class Zoom(unittest.TestCase):
    def test_tiles_are_at_least_as_sharp_as_the_screen(self):
        for mpp in (0.05, 0.3, 2.0, 30.0):
            z = tiles.zoom_for(mpp, 45.5, 22)
            tile_mpp = tiles.WEB_MERCATOR_RES0 * math.cos(math.radians(45.5)) / 2 ** z
            self.assertLessEqual(tile_mpp, mpp + 1e-9)
            self.assertGreater(tile_mpp * 2, mpp)

    def test_the_source_caps_the_zoom(self):
        self.assertEqual(tiles.zoom_for(0.001, 45.5, tiles.SOURCES["osm"].max_zoom), 19)


class Coverage(unittest.TestCase):
    def test_the_tiles_cover_the_box_centre_first(self):
        t = tiles.tiles_for(9.02, 45.52, 9.04, 45.53, 16)
        self.assertGreater(len(t), 1)
        xs = [x for x, _ in t]
        ys = [y for _, y in t]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        first, last = t[0], t[-1]
        self.assertLessEqual((first[0] - cx) ** 2 + (first[1] - cy) ** 2, (last[0] - cx) ** 2 + (last[1] - cy) ** 2)

    def test_a_tile_lands_where_its_corner_is(self):
        z = 19
        x, y = geo.tile_of(RHO.lon, RHO.lat, z)
        quad = tiles.tile_quad(RHO, z, x, y)
        # the origin lies inside its own tile, and the tile is about 54 m wide at this latitude and zoom
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        self.assertTrue(min(xs) <= 0 <= max(xs) and min(ys) <= 0 <= max(ys))
        side = math.dist(quad[0], quad[1])
        # on the ground a tile spans 2 pi / 2^z of longitude, measured on the WGS84 ellipsoid (the
        # transverse radius, 0.17% longer than the sphere of Web Mercator at this latitude)
        s = math.sin(math.radians(RHO.lat))
        transverse = geo.WGS84_A / math.sqrt(1 - geo.WGS84_E2 * s * s)
        self.assertAlmostEqual(side, 2 * math.pi / 2 ** z * transverse * math.cos(math.radians(RHO.lat)), delta=0.01)

    def test_low_zoom_tiles_are_subdivided_and_neighbouring_coasts_share_every_edge_point(self):
        left = tiles.tile_mesh(RHO, 3, 4, 2)
        right = tiles.tile_mesh(RHO, 3, 5, 2)
        self.assertGreater(len(left), 4)
        self.assertEqual(len(left), len(right))
        for left_cell, right_cell in zip(left[3::4], right[0::4], strict=True):
            self.assertEqual(left_cell[4][1:3], right_cell[4][::3])

    def test_europe_fits_the_tile_budget_and_nothing_is_requested_beyond_the_site_hemisphere(self):
        z = tiles.zoom_for(12000.0, RHO.lat, 19)
        europe = tiles.tiles_for(-11, 35, 31, 60, z)
        self.assertLessEqual(len(europe), 400)
        self.assertTrue(all(tiles.tile_in_hemisphere(RHO, z, x, y) for x, y in europe))
        antipode = geo.tile_of(RHO.lon + 180, -RHO.lat, z)
        self.assertFalse(tiles.tile_in_hemisphere(RHO, z, *antipode))
        self.assertEqual(tiles.tile_mesh(RHO, z, *antipode), [])


class Urls(unittest.TestCase):
    def test_osm_is_a_plain_template(self):
        self.assertEqual(tiles.SOURCES["osm"].tile_url(5, 17, 11), "https://tile.openstreetmap.org/5/17/11.png")

    def test_the_orthophoto_asks_the_tile_box_in_web_mercator(self):
        url = tiles.SOURCES["pcn"].tile_url(19, 275302, 186939)
        w, s, e, n = geo.tile_bounds(275302, 186939, 19)
        self.assertIn("REQUEST=GetMap", url)
        self.assertIn("CRS=EPSG:3857", url)
        self.assertIn(f"BBOX={w:.3f},{s:.3f},{e:.3f},{n:.3f}", url)



def custom(**changes) -> dict:
    """A designer's source as Preferences > Maps writes it, complete."""
    d = {"key": "user-0a1b2c3d", "name": "Ortofoto del Comune", "kind": "xyz",
         "url": "https://tiles.example.org/{z}/{x}/{y}.jpg", "layer": "", "style": "", "matrix_set": "", "matrices": [],
         "format": "image/jpeg", "version": "1.3.0", "crs": "EPSG:3857", "attribution": "© Comune, CC BY 4.0",
         "licence": "CC BY 4.0", "licence_url": "https://example.org/licenza", "bbox": [], "imagery": "photo",
         "min_zoom": 0, "max_zoom": 20, "capabilities": "", "added": "2026-10-25"}
    d.update(changes)
    return d


class Addresses(unittest.TestCase):
    """The address of a tile for each kind of source, as the servers were asked on 25/10/2026."""

    def test_an_xyz_template_takes_the_zoom_padded_and_the_tms_row(self):
        pdok = tiles.SOURCES["nl-pdok"]
        self.assertEqual(pdok.tile_url(5, 16, 10),
                         "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/05/16/10.jpeg")
        self.assertEqual(tiles.SOURCES["at-basemap"].tile_url(18, 142994, 90897),     # row before column
                         "https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/18/90897/142994.jpeg")
        tms = tiles.custom_source(custom(url="https://t.example.org/{z}/{x}/{-y}.png"))
        self.assertEqual(tms.tile_url(3, 1, 2), "https://t.example.org/3/1/5.png")
        odd = tiles.custom_source(custom(url="https://t.example.org/{z}/{x}/{y}.png?a={unknown}&k={key}"))
        self.assertEqual(odd.tile_url(3, 1, 2, key="s3cr3t"), "https://t.example.org/3/1/2.png?a={unknown}&k=s3cr3t")

    def test_a_wmts_by_key_value_pairs_names_its_layer_its_set_and_the_matrix_of_the_zoom(self):
        url = tiles.SOURCES["fr-ign"].tile_url(18, 132784, 90184)
        self.assertEqual(url, "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
                              "&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&TILEMATRIXSET=PM_0_19&TILEMATRIX=18"
                              "&TILEROW=90184&TILECOL=132784&FORMAT=image/jpeg")
        self.assertIn("TILEMATRIX=EPSG:900913:18&", tiles.SOURCES["be-bruxelles"].tile_url(18, 134241, 87936))
        self.assertIn("TILEMATRIX=EPSG:3857:18&", tiles.SOURCES["pl-gugik"].tile_url(18, 146373, 86296))

    def test_a_wmts_by_rest_fills_its_template_and_nrw_counts_its_matrices_from_zoom_five(self):
        nrw = tiles.SOURCES["de-nw"]
        self.assertEqual((nrw.min_zoom, nrw.matrices[4], nrw.matrices[5], nrw.matrices[18], nrw.matrices[21]),
                         (5, "", "00", "13", "16"))
        self.assertEqual(nrw.tile_url(18, 136003, 87497),
                         "https://www.wmts.nrw.de/geobasis/wmts_nw_dop/tiles/nw_dop/EPSG_3857_16/13/136003/87497")

    def test_a_wms_is_asked_the_tile_in_web_mercator_or_in_degrees_in_the_order_of_its_version(self):
        w, s, e, n = geo.tile_bounds(139170, 93190, 18)
        tn = tiles.SOURCES["it-tn"].tile_url(18, 139170, 93190)
        self.assertEqual(tn, "https://siat.provincia.tn.it/geoserver/stem/ecw-rgb-2015/wms?SERVICE=WMS&VERSION=1.3.0"
                             f"&REQUEST=GetMap&LAYERS=ecw-rgb-2015&STYLES=&CRS=EPSG:3857&BBOX={w:.3f},{s:.3f},{e:.3f},"
                             f"{n:.3f}&WIDTH=256&HEIGHT=256&FORMAT=image/jpeg")
        self.assertIn("map=owsofc_rt&SERVICE=WMS", tiles.SOURCES["it-toscana"].tile_url(18, 1, 1))  # its own parameter kept
        self.assertIn("?TIME=2024&SERVICE=WMS", tiles.SOURCES["de-hh"].tile_url(18, 1, 1))   # never the 2022 Airbus one
        lon_w, lat_s = geo.mercator_to_lonlat(w, s)
        lon_e, lat_n = geo.mercator_to_lonlat(e, n)
        lon_first = f"BBOX={lon_w:.8f},{lat_s:.8f},{lon_e:.8f},{lat_n:.8f}&"
        lat_first = f"BBOX={lat_s:.8f},{lon_w:.8f},{lat_n:.8f},{lon_e:.8f}&"
        crs84 = tiles.custom_source(custom(kind="wms", url="https://w.example.org/wms", layer="0", crs="CRS:84"))
        self.assertIn("&CRS=CRS:84&" + lon_first, crs84.tile_url(18, 139170, 93190))
        epsg4326 = tiles.custom_source(custom(kind="wms", url="https://w.example.org/wms", layer="0", crs="EPSG:4326"))
        self.assertIn("&CRS=EPSG:4326&" + lat_first, epsg4326.tile_url(18, 139170, 93190))   # 1.3.0: latitude first
        old = tiles.custom_source(custom(kind="wms", url="https://w.example.org/wms?", layer="0", crs="EPSG:4326",
                                         version="1.1.1"))
        self.assertIn("?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap", old.tile_url(18, 139170, 93190))
        self.assertIn("&SRS=EPSG:4326&" + lon_first, old.tile_url(18, 139170, 93190))       # 1.1.1: longitude first

    def test_every_source_of_the_program_names_its_licence_where_it_was_read_and_needs_no_key(self):
        for s in tiles.SOURCES.values():
            with self.subTest(source=s.key):
                self.assertIn(s.kind, tiles.KINDS)
                self.assertTrue(s.attribution and s.licence and s.licence_url.startswith(("http://", "https://")))
                self.assertRegex(s.checked, r"^2026-10-2[35]$")
                self.assertFalse(s.needs_key)
                self.assertFalse(s.custom)
                self.assertEqual(len(s.sample), 2)
                self.assertNotIn("{", s.tile_url(s.max_zoom, 1, 1))          # every placeholder filled
                self.assertEqual(tiles.problems({**tiles.to_dict(s), "key": "user-check"}), [])
                self.assertNotEqual(tiles.display_name(s), "")
        self.assertNotIn(chr(0x2014), "".join(s.attribution + s.licence for s in tiles.SOURCES.values()))
        self.assertIn(str(__import__("datetime").date.today().year), tiles.SOURCES["de-bb"].credit())
        self.assertEqual(tiles.SOURCES["de-bb"].credit(2027)[:25], "© GeoBasis-DE/LGB (2027),")


class AreasAndChoice(unittest.TestCase):
    """Where each source has imagery (mapcoverage.py, from Natural Earth) and which is best for a site."""

    def test_each_source_covers_its_public_square_and_is_the_best_there_when_a_photo(self):
        for s in tiles.SOURCES.values():
            lat, lon = s.sample
            with self.subTest(source=s.key):
                self.assertTrue(s.inside(lon, lat))
                if s.imagery == "photo":
                    self.assertEqual(tiles.best(tiles.SOURCES, lon, lat), s.key)

    def test_the_best_source_is_the_one_of_the_site_not_the_neighbour_across_the_border(self):
        S = tiles.SOURCES
        places = {"Como": (45.8081, 9.0852, "pcn"), "Ponte Chiasso": (45.8370, 9.0300, "pcn"),
                  "Lugano": (46.0037, 8.9511, "ch-swisstopo"), "Bolzano": (46.4983, 11.3548, "it-bz"),
                  "Innsbruck": (47.2692, 11.4041, "at-basemap"), "Strasbourg": (48.5734, 7.7521, "fr-ign"),
                  "Kehl, Baden-Württemberg without a source": (48.5705, 7.8153, "eox-2016"),
                  "Venice, St Mark's": (45.4341, 12.3388, "pcn"), "Capri": (40.5507, 14.2426, "pcn"),
                  "Lampedusa": (35.5, 12.6, "pcn"), "Elba": (42.81, 10.31, "it-toscana"),
                  "Ajaccio": (41.9192, 8.7386, "fr-ign"), "Mallorca": (39.5696, 2.6502, "es-pnoa"),
                  "Berlin, Gendarmenmarkt": (52.5137, 13.3928, "de-be"), "Brussels": (50.8469, 4.3525, "be-bruxelles"),
                  "Rotterdam, the port": (51.95, 4.10, "nl-pdok"), "Tokyo": (35.68, 139.76, "eox-2016"),
                  "the sea off Naples": (40.0, 15.0, "eox-2016")}
        for name, (lat, lon, key) in places.items():
            with self.subTest(place=name):
                self.assertEqual(tiles.best(S, lon, lat), key)
        # near a border both are offered, the site's own first; the maps after the photos
        found = [s.key for s in tiles.covering(S, 9.0300, 45.8370)]
        self.assertEqual(found[:3], ["pcn", "eox-2016", "ch-swisstopo"])
        self.assertEqual(found[-2:], ["osm", "opentopomap"])
        self.assertNotIn("ch-swisstopo", [s.key for s in tiles.covering(S, 9.1900, 45.4641)])    # Milan: too far

    def test_the_choice_is_used_where_it_covers_and_the_best_elsewhere(self):
        S = tiles.SOURCES
        paris, rho = (2.3522, 48.8566), (9.0300, 45.5226)
        self.assertEqual(tiles.effective("fr-ign", S, *paris), "fr-ign")
        self.assertEqual(tiles.effective("fr-ign", S, *rho), "pcn")
        self.assertEqual(tiles.effective("auto", S, *paris), "fr-ign")
        self.assertEqual(tiles.effective("osm", S, *rho), "osm")
        self.assertEqual(tiles.effective("none", S, *rho), "none")
        self.assertEqual(tiles.effective("a-source-of-tomorrow", S, *rho), "pcn")

    def test_a_source_of_the_designer_covers_its_box_and_is_used_only_when_chosen(self):
        mine = custom(bbox=[9.0, 45.5, 9.1, 45.6])
        S = tiles.catalogue([mine])
        s = S["user-0a1b2c3d"]
        self.assertTrue(s.custom and s.covers(9.03, 45.52) and not s.covers(9.5, 45.52))
        self.assertTrue(s.covers(9.1 + 2 / 111.32 / math.cos(math.radians(45.52)), 45.52))      # 2 km past: offered
        self.assertEqual(tiles.best(S, 9.03, 45.52), "pcn")                   # never chosen by itself
        self.assertEqual(tiles.effective("user-0a1b2c3d", S, 9.03, 45.52), "user-0a1b2c3d")
        self.assertEqual(tiles.effective("user-0a1b2c3d", S, 2.35, 48.86), "fr-ign")


class DesignersSources(unittest.TestCase):
    """The sources the designer adds, as the settings keep them: what keeps one from use is said, a damaged one is
    left out and never breaks the program, the key is never in it."""

    def test_a_complete_source_is_used_and_comes_back_the_same(self):
        s = tiles.custom_source(custom())
        self.assertEqual(tiles.problems(custom()), [])
        self.assertEqual(tiles.to_dict(s), custom())
        self.assertEqual(tiles.display_name(s), "Ortofoto del Comune")       # the designer's words, untranslated
        self.assertFalse(s.needs_key)
        keyed = tiles.custom_source(custom(url="https://k.example.org/{z}/{x}/{y}.png?key={key}"))
        self.assertTrue(keyed.needs_key)
        self.assertNotEqual(keyed.cache_name, s.cache_name)                 # another address, another folder
        self.assertTrue(s.cache_name.startswith("user-0a1b2c3d-"))
        self.assertEqual(tiles.SOURCES["osm"].cache_name, "osm")             # the program's: as before R36

    def test_what_is_missing_is_said_and_the_source_is_not_used(self):
        cases = {"name": custom(name=" "), "attribution": custom(attribution=""),
                 "http": custom(url="ftp://x/{z}/{x}/{y}"), "{z}": custom(url="https://x/{x}/{y}.png"),
                 "capabilities": custom(kind="wmts", url="https://x/wmts", layer="a"),
                 "layer": custom(kind="wms", url="https://x/wms"),
                 "EPSG:3857": custom(kind="wms", url="https://x/wms", layer="a", crs="EPSG:25832")}
        for word, d in cases.items():
            with self.subTest(missing=word):
                [problem] = tiles.problems(d)
                self.assertIn(word, problem)
                self.assertIsNone(tiles.custom_source(d))
        self.assertNotIn("user-0a1b2c3d", tiles.catalogue([custom(attribution="")]))

    def test_a_damaged_entry_of_the_settings_is_left_out_with_the_reason(self):
        for bad in (None, "text", {"key": "pcn"}, custom(kind="tms"), custom(max_zoom="20"), custom(bbox=[1, 2]),
                    custom(matrices="0,1"), custom(key="user-x", min_zoom=10, max_zoom=5), custom(name=3)):
            with self.subTest(bad=bad):
                self.assertTrue(tiles.problems(bad)[0].startswith("The source is not readable"))
                self.assertIsNone(tiles.custom_source(bad))
        S = tiles.catalogue([None, custom(), custom(key="osm")])     # the program's own key is never taken
        self.assertEqual(S["osm"], tiles.SOURCES["osm"])
        self.assertIn("user-0a1b2c3d", S)


if __name__ == "__main__":
    unittest.main()
