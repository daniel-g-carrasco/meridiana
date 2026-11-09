"""R540, «vedo ste bande nere intorno alla mappa quando faccio zoom out o mi sposto» (Daniel, 07/11/2026): the bare
background of the plan showed where a tile of the new view had not come yet, a pan revealed the background until the
gesture settled, a zoom out until the coarser tiles came. Now a backdrop two zooms coarser lies under three times the
view, and a tile on its way is stood in for by the nearest coarser one in memory, enlarged."""

import time
import unittest

from meridiana import geo, tiles
from meridiana.quick.backend import plan_maps

from . import test_map_offline as offline
from .test_map_offline import wms

ORIGIN = geo.Origin(45.5226, 9.03)


def covered(state, records):
    """The tiles of the view that no tile on show covers (itself or a coarser one over it)."""
    shown = {(r['key'], r['zoom'], r['source']) for r in records}
    zooms = {}
    for tile in list(state.loaded) + list(state.under) + list(state.stand_ins()):
        zooms.setdefault(tile[1], set()).add(tile)
    bare = []
    for key, z, x, y in state.wanted:
        if not any((key, z - k, x >> k, y >> k) in zooms.get(z - k, ()) for k in range(0, 9)):
            bare.append((key, z, x, y))
    return bare, shown


class BackdropTests(unittest.TestCase):
    def state(self):
        sources = {'pcn': wms('http://127.0.0.1:1', detail_zoom=18)}
        state = plan_maps.PlanMaps(ORIGIN, sources=sources)
        state.set_source('pcn')
        return state

    def test_a_backdrop_two_zooms_coarser_lies_under_three_times_the_view(self):
        state = self.state()
        state.set_view((-80, -50, 80, 50), .3, 1)
        z = next(iter(state.wanted))[1]
        self.assertTrue(state.backdrop)
        self.assertEqual({t[1] for t in state.backdrop}, {z - 2})
        self.assertLess(len(state.backdrop), len(state.wanted))
        # it covers a whole view more on every side
        far = plan_maps.PlanMaps(ORIGIN, sources=state.sources)
        far.set_source('pcn')
        far.set_view((-240, -150, 240, 150), .3, 1)
        ancestors = {(k, zz - 2, x >> 2, y >> 2) for k, zz, x, y in far.wanted}
        self.assertLessEqual(ancestors, state.backdrop)

    def test_a_tile_on_its_way_is_stood_in_for_by_the_nearest_coarser_one_in_memory(self):
        state = self.state()
        state.set_view((-80, -50, 80, 50), .3, 1)
        key, z, x, y = sorted(state.wanted)[0]
        parent = (key, z - 3, x >> 3, y >> 3)
        state.memory = lambda tile: 'image://m/7' if tile == parent else None
        records = state.records()
        self.assertIn(('image://m/7', z - 3), {(r['source'], r['zoom']) for r in records})
        # once the tile itself is there, its stand-in goes
        for tile in state.wanted:
            state.ready(tile, f'image://m/{tile}')
        self.assertNotIn('image://m/7', {r['source'] for r in state.records()})

    def test_the_coarser_tiles_are_drawn_first(self):
        state = self.state()
        state.set_view((-80, -50, 80, 50), .3, 1)
        for tile in state.backdrop:
            state.ready(tile, f'image://m/{tile}')
        tile = sorted(state.wanted)[0]
        state.ready(tile, 'image://m/sharp')
        zooms = [r['zoom'] for r in state.records()]
        self.assertEqual(zooms, sorted(zooms))


class FailoverTests(unittest.TestCase):
    """R539, «c'è ancora questo problema di caricamento dell'ortofoto»: three tiles of a view refused after every
    address moved the whole plan to the street map for three minutes, while the other tiles of the orthophoto came."""

    def state(self):
        sources = {'pcn': wms('http://127.0.0.1:1', detail_zoom=18),
                   'osm': tiles.Source('osm', 'OpenStreetMap', 'xyz', 'http://127.0.0.1:1/{z}/{x}/{y}.png', 'OSM',
                                       imagery='map', rank=10, max_zoom=19)}
        state = plan_maps.PlanMaps(ORIGIN, sources=sources)
        state.set_source('pcn')
        state.set_view((-80, -50, 80, 50), .3, 1)
        return state

    def test_a_few_tiles_refused_while_the_others_come_keep_the_orthophoto(self):
        state = self.state()
        wanted = sorted(state.wanted)
        for tile in wanted[3:]:
            state.ready(tile, f'image://m/{tile}')
        for tile in wanted[:3]:
            self.assertFalse(state.failed(tile, now=0))
        self.assertEqual(state.source, 'pcn')
        self.assertEqual(state.fallback_message, '')

    def test_a_source_that_gives_nothing_is_still_replaced(self):
        state = self.state()
        moved = [state.failed(tile, now=0) for tile in sorted(state.wanted)[:3]]
        self.assertEqual(moved, [False, False, True])
        self.assertEqual(state.source, 'osm')


class BandsOnTheRealLoader(unittest.TestCase):
    """The loader and the plan's model, the network cut after the first view: a pan of a whole view and a zoom out
    of two steps leave no tile of the view bare while the new tiles are on their way."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    tearDown, wait, spin, server, cache = (offline.OfflineMapTests.tearDown, offline.OfflineMapTests.wait,
                                           offline.OfflineMapTests.spin, offline.OfflineMapTests.server,
                                           offline.OfflineMapTests.cache)

    def test_no_bare_band_after_a_pan_or_a_zoom_out_while_the_tiles_come(self):
        from meridiana.quick.backend import plan_tiles
        server = self.server(poisoned=lambda path: False)
        maps = plan_tiles.MapController(self.cache(), sources={'pcn': wms(server.root, detail_zoom=18)},
                                        origin=ORIGIN)
        self.addCleanup(maps.close)
        maps.setSource('pcn')
        maps.updateView(-80, -50, 80, 50, .3, 1)
        self.wait(lambda: maps.state.wanted <= maps.state.loaded.keys() and
                  maps.state.backdrop <= maps.state.under.keys(), 20)
        maps.loader.offline = True      # nothing new comes: what is on show is what the plan already had
        for view, mpp in (((80, -50, 240, 50), .3), ((-160, -100, 160, 100), .6), ((-240, -150, 240, 150), .9)):
            maps.updateView(*view, mpp, 1)
            self.spin(.3)
            bare, _shown = covered(maps.state, maps.tileModel.records)
            self.assertEqual(bare, [], f'{view} {mpp}: {len(bare)} of {len(maps.state.wanted)} tiles bare')


if __name__ == '__main__':
    unittest.main()
