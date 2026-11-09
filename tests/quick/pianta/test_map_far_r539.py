"""R539, Daniel 07/11/2026 sera: with «Automatic» the orthophoto stays from afar too (past 2 m per pixel the plan went
to OpenStreetMap), as long as the source covers the site; OpenStreetMap only where the orthophoto is not or gives no
tiles. The coarser tiles of a source are asked only where it has them (the national orthophoto: none past 1:500.000,
its capabilities): further out its nearest level is drawn around the site, the street map under it."""

import unittest

from meridiana import geo, tiles
from meridiana.quick.backend import plan_maps

from .test_map_offline import wms

ORIGIN = geo.Origin(45.5226, 9.03)          # Rho


def osm():
    return tiles.Source('osm', 'OpenStreetMap', 'xyz', 'http://127.0.0.1:1/{z}/{x}/{y}.png', 'OSM contributors',
                        imagery='map', rank=10, max_zoom=19)


class FarAutomatic(unittest.TestCase):
    def state(self, min_zoom=11):
        sources = {'pcn': wms('http://127.0.0.1:1', detail_zoom=18, min_zoom=min_zoom), 'osm': osm()}
        return plan_maps.PlanMaps(ORIGIN, sources=sources)

    def test_the_orthophoto_stays_past_two_metres_per_pixel(self):
        state = self.state()
        for mpp in (.3, 2.5, 10, 60):
            state.set_view((-800 * mpp, -500 * mpp, 800 * mpp, 500 * mpp), mpp, 1)
            self.assertEqual(state.source, 'pcn', mpp)
            self.assertEqual({t[0] for t in state.wanted}, {'pcn'})

    def test_past_its_coarsest_level_the_nearest_one_around_the_site_and_the_street_map_under_it(self):
        state = self.state()
        mpp = 200.0                                     # zoom 10: the national orthophoto starts at 11
        state.set_view((-800 * mpp, -500 * mpp, 800 * mpp, 500 * mpp), mpp, 1)
        self.assertEqual(state.source, 'pcn')
        self.assertEqual({t[1] for t in state.wanted}, {11})                 # never a level it has not
        self.assertLessEqual(len(state.wanted), plan_maps.FAR_PHOTO_TILES)  # around the site, not the whole view
        self.assertTrue(state.backdrop)
        self.assertEqual({t[0] for t in state.backdrop}, {'osm'})
        self.assertLess(max(t[1] for t in state.backdrop), 11)
        self.assertFalse(state.around)
        # the street map's credit is there while its tiles are
        tile = sorted(state.backdrop)[0]
        state.ready(tile, 'image://m/osm')
        self.assertIn('OSM contributors', state.attribution)

    def test_a_source_with_its_coarse_levels_gets_no_street_map(self):
        state = self.state(min_zoom=0)
        mpp = 400.0
        state.set_view((-800 * mpp, -500 * mpp, 800 * mpp, 500 * mpp), mpp, 1)
        self.assertEqual({t[0] for t in state.backdrop}, {'pcn'})

    def test_the_national_orthophoto_has_no_level_past_one_to_500000(self):
        # MaxScaleDenominator 500000 in its capabilities (read 07/11/2026): zoom 10 is 1:546.000, 11 is 1:273.000
        self.assertEqual(tiles.catalogue(())['pcn'].min_zoom, 11)

    def test_the_widgets_keep_their_street_map_from_afar(self):
        # R542: the Widgets window is frozen, its rule stays
        sources = {'pcn': wms('http://127.0.0.1:1'), 'osm': osm()}
        self.assertEqual(tiles.effective(tiles.AUTO, sources, ORIGIN.lon, ORIGIN.lat, 10.0), 'osm')


if __name__ == '__main__':
    unittest.main()
