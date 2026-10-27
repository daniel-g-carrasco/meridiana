"""Where the line of a string runs on the plan (R117, R184): from module to module through their middles while they
are next to each other; a dashed jump when they are not; and a colour for each string that the strings touching it do
not have. Plain geometry on the modules' corners (any frame: the plan gives them in its scene), no Qt: the plan draws
what this gives.

- Two modules of a string follow each other «next to each other» when the straight line between their middles crosses
  no other module. Each module counts as its outline drawn in by SHRINK of its shorter side: the line between two
  modules side by side, or corner to corner, passes along the gaps between the others.
- A jump in the same row is a direct dashed line. Between rows, an orthogonal bridge joins the centres through the
  gap when it enters no other module. Both module axes are tried, and the shorter valid bridge wins. With no free
  corridor the direct dashed line remains: the modules it passes over are not filled with the string's colour.
- Jumps routed together (R134) keep their own lanes: a screen-derived sideways offset where there is room. One string
  alone, and strings that never meet, keep the original paths. If touching modules leave no free geometry, the route
  stays and the lane number gives the plan a different dash pattern."""

from __future__ import annotations

import math

import numpy as np

SHRINK = 0.04                   # the share of a module's shorter side its outline is drawn in by
TOUCH = 1.5                     # the shorter sides within which two modules are neighbours, for the colours: across
                                # the gap between two rows too (a string in the next row in the same tint misleads)
MAX_BRIDGE_SPAN = 12.0          # shorter sides between centres: a long jump stays direct instead of a huge detour


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
        self.outlines = outlines
        self.outer_tree = shapely.STRtree(outlines)
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

    def _offset(self, path, distance: float, ends: tuple[int, int], avoid=()):
        """A lane beside a polyline. At each corner take the free direction nearest its assigned side, so the lane
        leaves a shared corner through the gap instead of cutting the next module. The module centres stay fixed."""
        import shapely
        if not distance or len(path) < 3:
            return path
        points = np.asarray(path, dtype=float)
        segments = np.diff(points, axis=0)
        lengths = np.linalg.norm(segments, axis=1)
        directions = np.divide(segments, lengths[:, None], out=np.zeros_like(segments), where=lengths[:, None] > 0)
        normals = np.column_stack((-directions[:, 1], directions[:, 0]))
        turns = [0] + [d * sign for d in range(15, 180, 15) for sign in (1, -1)] + [180]
        out = points.copy()
        for k in range(1, len(points) - 1):
            normal = normals[k - 1] + normals[k]
            length = float(np.linalg.norm(normal))
            normal = normal / length if length > 1e-12 else normals[k - 1]
            bearing = math.atan2(normal[1], normal[0])
            found = None
            for turn in turns:
                angle = bearing + math.radians(turn)
                candidate = out.copy()
                candidate[k] = points[k] + distance * np.array([math.cos(angle), math.sin(angle)])
                line = shapely.LineString(candidate)
                if self._outside(candidate, ends) and all(not shapely.intersects(line, other) for other in avoid):
                    found = candidate
                    break
            if found is None:
                return None
            out = found
        return [tuple(map(float, p)) for p in out]

    def _outside(self, path, ends: tuple[int, int]) -> bool:
        """Whether a lane enters no module except the two it connects; running along an edge is not entering."""
        import shapely
        line = shapely.LineString(path)
        oi = self.outer_tree.query(line, predicate="intersects")
        oi = oi[(oi != ends[0]) & (oi != ends[1])]
        return not len(oi) or not bool(np.any(shapely.relate_pattern(line, self.outlines[oi], "T********")))

    def legs_together(self, strings: list[list[int]], gap: float):
        """Routes and lane numbers for strings drawn together. Only jumps that meet get a sideways lane, `gap`
        scene units wide; every jump of a string uses the same lane. Lanes are tried on both sides and accepted only
        if they stay out of the other modules and at least half a gap from the routes already placed. Where no
        geometric lane fits, the original route stays and its distinct lane number selects another dash pattern."""
        import shapely
        base = [self.legs(order) for order in strings]
        if gap <= 0 or sum(jump for legs in base for _path, jump in legs) <= 1:
            return base, [0] * len(strings)
        lines = [[shapely.LineString(path) for path, jump in legs if jump] for legs in base]
        conflicts = [[False] * len(strings) for _ in strings]
        for i in range(len(strings)):
            for j in range(i + 1, len(strings)):
                conflicts[i][j] = conflicts[j][i] = any(shapely.intersects(a, b) for a in lines[i] for b in lines[j])
        choices = [0] + [k * sign for k in range(1, 9) for sign in (1, -1)]
        routed: list = []
        lanes: list[int] = []
        for i, order in enumerate(strings):
            near = [j for j in range(i) if conflicts[i][j]]
            used = {lanes[j] for j in near}
            chosen = None
            for lane in (k for k in choices if k not in used):
                pairs = list(zip(order, order[1:], strict=False))
                avoid = [b for j in near for b in lines[j]]
                candidate = [(self._offset(path, lane * gap, pairs[k], avoid) if jump else path, jump)
                             for k, (path, jump) in enumerate(base[i])]
                valid = all(path is not None for path, _jump in candidate)
                if valid:
                    own = [shapely.LineString(path) for path, jump in candidate if jump]
                    valid = all(shapely.distance(a, b) >= 0.5 * gap for j in near for a in own for b in lines[j])
                    valid = valid and all(self._outside(path, pairs[k]) for k, (path, jump) in enumerate(candidate)
                                          if jump)
                if valid:
                    chosen = lane, candidate
                    break
            lane, candidate = chosen or (next(k for k in choices if k not in used), base[i])
            lanes.append(lane)
            routed.append(candidate)
            lines[i] = [shapely.LineString(path) for path, jump in candidate if jump]
        return routed, lanes

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
        """A direct jump, or the shorter orthogonal bridge through a gap that enters no other module."""
        key = (int(i), int(j))
        if key in self.routes:
            return self.routes[key]
        path = self._corridor(i, j)
        if path is None:
            path = [tuple(map(float, self.centres[i])), tuple(map(float, self.centres[j]))]
        self.routes[key] = path
        return path

    def _corridor(self, i: int, j: int) -> list[tuple[float, float]] | None:
        """The shortest right-angled bridge between two module centres through a free gap, along either module axis."""
        a, b = self.centres[i], self.centres[j]
        if float(np.linalg.norm(b - a)) > MAX_BRIDGE_SPAN * self.size:
            return None
        candidates: list[tuple[float, list[tuple[float, float]]]] = []
        for edge in (self.quads[i, 1] - self.quads[i, 0], self.quads[i, 2] - self.quads[i, 1]):
            length = float(np.linalg.norm(edge))
            if length <= 1e-12:
                continue
            axis = edge / length
            direction = float(np.dot(b - a, axis))
            if abs(direction) < 1e-9:
                continue
            pa, pb = self.quads[i] @ axis, self.quads[j] @ axis
            lane = (float(pa.max()) + float(pb.min())) / 2 if direction > 0 else \
                (float(pa.min()) + float(pb.max())) / 2
            aa = a + (lane - float(np.dot(a, axis))) * axis
            bb = b + (lane - float(np.dot(b, axis))) * axis
            points = (a, aa, bb, b)
            path = [tuple(map(float, point)) for point in points]
            if self._outside(path, (i, j)):
                cost = sum(float(np.linalg.norm(points[k + 1] - points[k])) for k in range(3))
                candidates.append((cost, path))
        return min(candidates, key=lambda candidate: candidate[0])[1] if candidates else None

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
