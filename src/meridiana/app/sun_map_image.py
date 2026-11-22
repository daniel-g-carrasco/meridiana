"""What the picture of a surface of the sun map owes to its geometry alone (study 45, package 5; chapter 10: the window's
thread only hands over the bytes): made once for each surface and level where the map's job runs
(app/irradiance_job.py sends it with the level), so that the window only lays the colours of the classes on the tiles
(gui/backend/plan_map.py). Without Qt.

The picture has `k` pixels a side for each tile (pixels_per_tile): row r of the grid is on its lines r k ... (r + 1) k,
column c on its columns c k ... (c + 1) k. On it the raster gives, as flat indices of the picture's pixels:
- `clear`: the pixels of a tile that meets the surface but that lie off its contour (the tiles of the border do not
  leave the surface);
- `edge` and `alpha`: the pixels the contour crosses, with the share of each that is inside (an antialiased edge, on
  every renderer);
- `lines`: the pixels of the hatch on the tiles under an obstacle (a diagonal every HATCH pixels)."""

from __future__ import annotations

import numpy as np

PIXELS = (2, 12)        # a tile's pixels a side in its picture, at least and at most
EDGE_PX = 640           # a picture's longest side at most: the colours laid in about 2 ms on the window's thread
HATCH = 8               # pixels between two lines of the hatch


def pixels_per_tile(rows: int, cols: int) -> int:
    """How many pixels a side a tile takes: enough for the contour's cut and the hatch to read when the plan is
    zoomed in, the picture never longer than EDGE_PX."""
    return int(max(PIXELS[0], min(PIXELS[1], EDGE_PX // max(rows, cols, 1))))


def raster(outline: np.ndarray, shape: tuple, inside: np.ndarray, under: np.ndarray, k: int | None = None) -> dict:
    """The raster of a level's picture (see the module's text): `outline` the surface's contour on the grid's columns
    and rows, `shape` (rows, cols) of the grid, `inside` the tiles that meet the surface, `under` those under an
    obstacle. {k, size (height, width), clear, edge, alpha, lines}."""
    import shapely
    rows, cols = (int(x) for x in shape)
    k = pixels_per_tile(rows, cols) if k is None else int(k)
    height, width = rows * k, cols * k
    contour = shapely.Polygon(np.asarray(outline, dtype=float) * k)
    if not contour.is_valid:
        contour = contour.buffer(0)
    shapely.prepare(contour)
    y, x = np.mgrid[0:height, 0:width]
    centre = shapely.contains_xy(contour, x.ravel() + 0.5, y.ravel() + 0.5).reshape(height, width)
    # the pixels the contour can cross: those whose centre differs from a neighbour's (off the picture is outside)
    padded = np.pad(centre, 1, constant_values=False)
    near = ((padded[1:-1, 1:-1] != padded[:-2, 1:-1]) | (padded[1:-1, 1:-1] != padded[2:, 1:-1])
            | (padded[1:-1, 1:-1] != padded[1:-1, :-2]) | (padded[1:-1, 1:-1] != padded[1:-1, 2:]))
    edge = np.flatnonzero(near)
    ex, ey = edge % width, edge // width
    share = shapely.area(shapely.intersection(shapely.box(ex, ey, ex + 1, ey + 1), contour))
    alpha = np.where(centre.ravel(), 255, 0).astype(np.uint8)
    alpha[edge] = np.clip(np.round(share * 255), 0, 255).astype(np.uint8)
    met = np.repeat(np.repeat(np.asarray(inside, dtype=bool), k, axis=0), k, axis=1).ravel()
    clear = np.flatnonzero(met & (alpha == 0))
    partial = edge[(alpha[edge] > 0) & (alpha[edge] < 255)]
    hatched = np.repeat(np.repeat(np.asarray(under, dtype=bool), k, axis=0), k, axis=1)
    lines = np.flatnonzero(hatched & ((x + (height - 1 - y)) % HATCH == 0) & (alpha.reshape(height, width) > 0))
    return {"k": k, "size": (height, width), "clear": clear.astype(np.int32), "edge": partial.astype(np.int32),
            "alpha": alpha[partial], "lines": lines.astype(np.int32)}
