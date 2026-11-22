"""R624: the shape of the soft end of an area that scrolls, read on three pictures of the same window.

A: as drawn; C: the content without soft ends (EdgeFades given no flickable); G: the ground alone (the flickable
hidden). Row by row from the edge inwards, the opacity the content has, alpha = (A - G) / (C - G), averaged on the
columns where C and G differ by CONTRAST levels or more (where the content is not on the ground's colour): the shape
of the dissolve whatever the content, and the same number for a veil of a colour painted over it (the colour of the
veil is then what tells: the wrong grey gives alpha far from the curve or above 1).

A good soft end (Daniel 15/11/2026: «la sfumatura deve essere una trasparenza gradiente del contenuto»; R177, R590):
- nothing of the content at the edge: alpha of the first row at most EDGE;
- it grows without going back (MONOTONE: no row more than that below the one before);
- without a step: no row more than STEP_SLOPE / band above the one before (the even ramp is 1 / band, the smoothstep of
  Controls/edgefade.frag 1.5 / band);
- without a kink, the line seen where a gradient changes its slope suddenly (the old veils: 0.42 two pixels in, then
  nearly gone): the second difference over `s` rows at most KINK * s^2 / band^2 + NOISE;
- short (Daniel: «molto marcata»; the old veil of the report, nearly opaque for half its 24 px): half the content seen
  within HALF band, whole before 1.5 band (alpha at least WHOLE).
`band` is the band of the theme (Size.FADE) in device pixels.
"""
from __future__ import annotations

import statistics

CONTRAST = 40
EDGE = 0.08
MONOTONE = 0.03
STEP_SLOPE = 2.2
KINK = 8.0
NOISE = 0.03
WHOLE = 0.97
HALF = 0.6


def lightness(image, x, y):
    from PySide6.QtGui import QColor
    return QColor(image.pixel(x, y)).lightnessF() * 255


def opacity(A, C, G, x0: int, x1: int, y0: int, rows: int, step: int = 1, downward: bool = True) -> list:
    """alpha row by row from the edge row y0 (downward: inwards from a top edge; otherwise upwards from a bottom one),
    None where fewer than three columns have content off the ground."""
    out = []
    for r in range(rows):
        y = y0 + r if downward else y0 - r
        values = []
        for x in range(x0, x1, step):
            a, c, g = lightness(A, x, y), lightness(C, x, y), lightness(G, x, y)
            if abs(c - g) >= CONTRAST:
                values.append((a - g) / (c - g))
        out.append(statistics.fmean(values) if len(values) >= 3 else None)
    return out


def judge(alpha: list, band: float) -> list[str]:
    """What is wrong with the dissolve `alpha` (rows from the edge) for a band of `band` device pixels: [] if nothing."""
    wrong = []
    known = [(r, v) for r, v in enumerate(alpha) if v is not None]
    inside = [(r, v) for r, v in known if r <= 1.5 * band]
    if len(inside) < band / 2:
        return [f'too few rows with content off the ground ({len(inside)})']
    first_row, first = inside[0]
    if first_row <= 2 and first > EDGE + first_row * STEP_SLOPE / band:
        wrong.append(f'content at the edge: alpha {first:.2f} at row {first_row}')
    pairs = [(r1, v1, v2) for (r1, v1), (r2, v2) in zip(inside, inside[1:], strict=False) if r2 == r1 + 1]
    back = [(r, v1 - v2) for r, v1, v2 in pairs if v2 < v1 - MONOTONE]
    if back:
        wrong.append(f'it goes back: {back[:3]}')
    steepest = max(((v2 - v1), r) for r, v1, v2 in pairs) if pairs else (0, 0)
    if steepest[0] > STEP_SLOPE / band:
        wrong.append(f'a step of {steepest[0]:.3f} at row {steepest[1]} (at most {STEP_SLOPE / band:.3f})')
    s = max(1, round(band / 8))
    values = dict(inside)
    kinks = [(abs(values[r + s] - 2 * values[r] + values[r - s]), r) for r in values
             if r - s in values and r + s in values]
    if kinks:
        worst = max(kinks)
        limit = KINK * s * s / band ** 2 + NOISE
        if worst[0] > limit:
            wrong.append(f'a kink of {worst[0]:.3f} at row {worst[1]} (at most {limit:.3f})')
    slow = [(r, v) for r, v in inside if r >= HALF * band and v < 0.5 - MONOTONE]
    if slow:
        wrong.append(f'too long: alpha {slow[0][1]:.2f} at row {slow[0][0]}, half the content not seen within '
                     f'{HALF * band:.0f} rows')
    late = [v for r, v in known if 1.5 * band <= r <= 1.5 * band + 3]
    if late and min(late) < WHOLE:
        wrong.append(f'not whole past the band: {min(late):.2f}')
    return wrong
