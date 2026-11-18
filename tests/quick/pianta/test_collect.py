"""R301: temporary edge/point tools preserve the drawing they interrupt."""
import unittest

from meridiana.quick.backend.plan_collect import Collector


class CollectorTest(unittest.TestCase):
    def test_r505_the_nearest_side_in_pixel_reach_and_of_two_the_longest(self):
        # R505 (r19-selezione): the side nearest the pointer within 14 px; of two within 3 px the longest on screen
        # (before it, the smallest kind won: the exclusion's side over the building's on the same line)
        outer = [[0, 0], [20, 0], [20, 20], [0, 20]]
        inner = [[5, 0], [10, 0], [10, 5], [5, 5]]
        c = Collector()
        c.edges('align', [('building', 'b', outer), ('exclusion', 'x', inner)])
        self.assertIsNone(c.click((7, -2), .1))                     # 20 px away: out of reach
        self.assertEqual(c.click((7, -.5), .1), {'type': 'edge', 'purpose': 'align',
                         'kind': 'building', 'oid': 'b', 'side': 0, 'angle': 0.})
        self.assertFalse(c.active)
        c = Collector()
        c.edges('align', [('building', 'b', outer), ('exclusion', 'x', inner)])
        found = c.click((7, 5.3), .1)                               # 3 px from the inner side, 53 from the outer
        self.assertEqual((found['oid'], found['side']), ('x', 2))

    def test_points_hints_back_and_cancel(self):
        c = Collector()
        c.points('scale', ['First point', 'Second point'])
        self.assertEqual(c.hint, 'First point')
        self.assertIsNone(c.click((1, 2), .1))
        self.assertEqual(c.hint, 'Second point')
        c.key('Backspace')
        self.assertEqual(c.hint, 'First point')
        c.click((3, 4), .1)
        self.assertEqual(c.click((7, 8), .1)['points'], [[3., 4.], [7., 8.]])
        c.points('move', ['First', 'Second'])
        c.key('Escape')
        self.assertFalse(c.active)

    def test_edges_order_and_alignment_angle(self):
        c = Collector()
        c.edges('align', [('building', 'b', [[0, 0], [10, 10], [0, 10]])])
        # This ring turns counter-clockwise: the side keeps its own direction, the inside (0, 10) ends above it.
        self.assertAlmostEqual(c.click((5, 5), .1)['angle'], 45.)

    def test_aligned_side_is_horizontal_at_the_bottom_whatever_the_ring_and_the_view(self):
        """R477: rotated buildings, rings of both turns, pitches, triangles and pentagons, the view already turned:
        the chosen side ends horizontal and at the bottom, the outline above it."""
        import math
        import random
        from meridiana.quick.backend.plan_collect import align_angle
        rng = random.Random(477)

        def screen(point, bearing):          # Plan.qml, screen(): the drawing's point (x, y) at this bearing
            a = math.radians(bearing)
            return point[0] * math.cos(a) + point[1] * math.sin(a), point[0] * math.sin(a) - point[1] * math.cos(a)

        def polygon(n, radius, turn):
            # Convex (points of one circle), moved anywhere: the middle lies inside, above every side once aligned.
            angles = sorted(rng.uniform(0, 2 * math.pi) for _ in range(n))
            dx, dy = rng.uniform(-50, 50), rng.uniform(-50, 50)
            ring = [[radius * math.cos(t) + dx, radius * math.sin(t) + dy] for t in angles]
            return ring if turn > 0 else ring[::-1]           # sorted angles: counter-clockwise
        rings = []
        for turn in (1, -1):
            for angle in (0, 17, 45, 90, 123, 200, 300):
                a = math.radians(angle)
                box = [[0, 0], [12, 0], [12, 7], [0, 7]]
                rotated = [[x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)] for x, y in box]
                rings.append(rotated if turn > 0 else rotated[::-1])
            for n in (3, 5, 7):
                rings.append(polygon(n, 20, turn))
        checked = 0
        for ring in rings:
            for side in range(len(ring)):
                for before in (0, 33, -120, 270):
                    bearing = align_angle(ring, side)
                    self.assertAlmostEqual(bearing, (bearing + before - before), msg='the start does not matter')
                    a, b = ring[side], ring[(side + 1) % len(ring)]
                    sa, sb = screen(a, bearing), screen(b, bearing)
                    self.assertAlmostEqual(sa[1], sb[1], places=6, msg=f'not horizontal: {ring} side {side}')
                    cx = sum(p[0] for p in ring) / len(ring)
                    cy = sum(p[1] for p in ring) / len(ring)
                    inside = screen((cx, cy), bearing)
                    self.assertLess(inside[1], sa[1] - 1e-6, msg=f'the outline is under its side: {ring} side {side}')
                    checked += 1
        self.assertGreater(checked, 200)

