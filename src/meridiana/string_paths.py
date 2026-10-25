"""Where the line of a string runs on the plan (R117, Daniel 25/10/2026: «non si riesce a intuire quando si sta saltando un
pannello»): from module to module through their middles while they are next to each other; around the modules it skips
when they are not, along the edges between the modules, so that the line never passes over a module that is not its
own and the jump is seen; and a colour for each string that the strings touching it do not have. Plain geometry on the
modules' corners (any frame: the plan gives them in its scene), no Qt: the plan draws what this gives.

- Two modules of a string follow each other «next to each other» when the straight line between their middles crosses
  no other module. Each module counts as its outline drawn in by SHRINK of its shorter side: the line between two
  modules side by side, or corner to corner, passes along the gaps between the others.
- Otherwise the line goes round: the shortest way from middle to middle that keeps out of every other module (drawn in
  as above, so that the way runs along their edges), found among the corners of the modules near the line between the
  two (A* on the corners each can see); the plan draws it dashed, a jump. A way not found there (a jump across more
  than MAX_CORNERS / 4 modules, or modules on top of each other) is the straight line, still a jump: the modules it
  passes over are not filled with the string's colour, so the jump still shows."""

from __future__ import annotations

import heapq
import math

import numpy as np

SHRINK = 0.04                   # the share of a module's shorter side its outline is drawn in by
TOUCH = 1.5                     # the shorter sides within which two modules are neighbours, for the colours: across
                                # the gap between two rows too (a string in the next row in the same tint misleads)
MAX_CORNERS = 480               # the corners a way around is looked for among (120 modules): beyond, a straight jump
MAX_STEPS = 160                 # the corners the search may take before it gives up


class Router:
    """The modules of the plan, `quads` (N, 4, 2), to route the strings over them: module i is quads[i]."""

    def __init__(self, quads):
        import shapely
        q = np.asarray(quads, dtype=float).reshape(-1, 4, 2)
        self.quads = q
        self.centres = q.mean(axis=1) if len(q) else np.zeros((0, 2))
        if len(q):
            sides = np.minimum(np.linalg.norm(q[:, 1] - q[:, 0], axis=1), np.linalg.norm(q[:, 2] - q[:, 1], axis=1))
        else:
            sides = np.zeros(0)
        self.sides = sides
        self.size = float(np.median(sides)) if len(sides) else 1.0
        outlines = shapely.polygons(q) if len(q) else np.array([], dtype=object)
        self.polys = shapely.buffer(outlines, -SHRINK * sides, join_style="mitre") if len(q) else outlines
        self.tree = shapely.STRtree(self.polys)
        self._near = None
        self.routes: dict = {}                  # (i, j) -> the way found, kept while the modules are these

    # a string's line

    def legs(self, order: list[int]) -> list[tuple[list[tuple[float, float]], bool]]:
        """The line of a string through modules `order` (indices), one leg for each two that follow each other: (its
        points from the middle of the first to the middle of the second, jumped)."""
        pairs = list(zip(order, order[1:], strict=False))
        if not pairs:
            return []
        blocked = self.blocked(pairs)
        out = []
        for (i, j), jump in zip(pairs, blocked, strict=True):
            a, b = tuple(map(float, self.centres[i])), tuple(map(float, self.centres[j]))
            out.append((self.route(i, j), True) if jump else ([a, b], False))
        return out

    def blocked(self, pairs: list[tuple[int, int]]) -> list[bool]:
        """For each pair of modules, whether the straight line between their middles crosses another module."""
        import shapely
        if not pairs:
            return []
        ii = np.array([p[0] for p in pairs])
        jj = np.array([p[1] for p in pairs])
        lines = shapely.linestrings(np.stack([self.centres[ii], self.centres[jj]], axis=1))
        li, pi = self.tree.query(lines, predicate="intersects")
        other = (pi != ii[li]) & (pi != jj[li])
        out = np.zeros(len(pairs), dtype=bool)
        out[li[other]] = True
        return out.tolist()

    def route(self, i: int, j: int) -> list[tuple[float, float]]:
        """The way from the middle of module i to the middle of module j that keeps out of every other module; the
        straight line when none is found among the corners near the two (a jump across many modules)."""
        key = (int(i), int(j))
        if key in self.routes:
            return self.routes[key]
        a, b = self.centres[i], self.centres[j]
        path = None
        for reach in (1.5 * self.size, 4.0 * self.size):
            path = self._around(i, j, reach)
            if path is not None:
                break
        if path is None:
            path = [tuple(map(float, a)), tuple(map(float, b))]
        self.routes[key] = path
        return path

    def _around(self, i: int, j: int, reach: float):
        """A* over the corners of the modules within `reach` of the line between i and j, from i's middle to j's; None
        when there are more than MAX_CORNERS of them or the way is not found in MAX_STEPS."""
        import shapely
        a, b = self.centres[i], self.centres[j]
        corridor = shapely.buffer(shapely.linestrings([a, b]), reach)
        local = self.tree.query(corridor)
        local = local[(local != i) & (local != j)]
        if not len(local):
            return [tuple(map(float, a)), tuple(map(float, b))]
        if 4 * len(local) > MAX_CORNERS:
            return None
        obstacles = self.polys[local]
        corners = shapely.get_coordinates(shapely.get_exterior_ring(obstacles)).reshape(len(local), -1, 2)[:, :-1]
        own = self.quads[local]                                      # (k, 4, 2): the corners each comes from
        nearest = np.linalg.norm(corners[:, :, None, :] - own[:, None, :, :], axis=3).argmin(axis=2)
        edges = np.take_along_axis(own, nearest[:, :, None], axis=1).reshape(-1, 2)
        points = np.vstack([a[None, :], b[None, :], corners.reshape(-1, 2)])
        goal = 1
        best = {0: 0.0}
        came: dict = {}
        heap = [(float(np.hypot(*(b - a))), 0.0, 0)]
        closed: set = set()
        while heap and len(closed) < MAX_STEPS:
            _f, g, u = heapq.heappop(heap)
            if u in closed:
                continue
            if u == goal:
                way = [u]
                while way[-1] in came:
                    way.append(came[way[-1]])
                # each corner of a module drawn in goes back to the module's own corner: the way runs on the edges
                # and in the gaps, not a few centimetres inside the modules it passes by
                return [tuple(map(float, points[k] if k < 2 else edges[k - 2])) for k in reversed(way)]
            closed.add(u)
            others = np.array([k for k in range(len(points)) if k not in closed and k != u])
            if not len(others):
                continue
            seen = self._visible(points[u], points[others], (i, j))
            for v in others[seen]:
                cost = g + float(np.hypot(*(points[v] - points[u])))
                if cost < best.get(int(v), math.inf) - 1e-12:
                    best[int(v)] = cost
                    came[int(v)] = u
                    heapq.heappush(heap, (cost + float(np.hypot(*(b - points[v]))), cost, int(v)))
        return None

    def _visible(self, p, targets, ends: tuple) -> np.ndarray:
        """Which of `targets` the point `p` sees: the line to it enters no module but the two `ends` (running along
        an edge, or touching a corner, is not entering)."""
        import shapely
        lines = shapely.linestrings(np.stack([np.broadcast_to(p, targets.shape), targets], axis=1))
        li, oi = self.tree.query(lines, predicate="intersects")
        keep = (oi != ends[0]) & (oi != ends[1])
        li, oi = li[keep], oi[keep]
        out = np.ones(len(targets), dtype=bool)
        if len(li):
            inside = shapely.relate_pattern(lines[li], self.polys[oi], "T********")
            out[li[inside]] = False
        return out

    # the colours

    def neighbours(self) -> list[set]:
        """For each module, its neighbours (within TOUCH of its shorter side)."""
        if self._near is None:
            import shapely
            near: list[set] = [set() for _q in range(len(self.quads))]
            if len(self.quads):
                grown = shapely.buffer(shapely.polygons(self.quads), TOUCH * self.sides, join_style="mitre")
                a, b = self.tree.query(grown, predicate="intersects")
                for x, y in zip(a.tolist(), b.tolist(), strict=True):
                    if x != y:
                        near[x].add(y)
                        near[y].add(x)
            self._near = near
        return self._near


def colours(strings: list[list[int]], router: Router | None, count: int, seeds: list[int] | None = None) -> list[int]:
    """A colour for each string, an index into `count` tints: its own (`seeds`, a number of the string that does not
    change when other strings come or go, so that deleting one does not repaint the others; without them its place in
    the list), unless a string before it that touches it already has that colour; then the next one free among those
    of the strings it touches. The same plan, the same colours."""
    count = max(1, int(count))
    out: list[int] = []
    owner: dict = {}
    for s, mods in enumerate(strings):
        for m in mods:
            owner.setdefault(m, s)
    near = router.neighbours() if router is not None else None
    for s, mods in enumerate(strings):
        taken = set()
        if near is not None:
            for m in mods:
                for n in near[m] if 0 <= m < len(near) else ():
                    t = owner.get(n, s)
                    if t < s:
                        taken.add(out[t])
        own = seeds[s] if seeds is not None else s
        choice = own % count
        for k in range(count):
            if (own + k) % count not in taken:
                choice = (own + k) % count
                break
        out.append(choice)
    return out
