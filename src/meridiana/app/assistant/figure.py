"""Meridio's figure (R619, Daniel 14/11/2026): a sun at noon made of flat slabs, without the grey disc.

A yellow half disc (the face) completed above by blue hair in rays of sun, one solid with five rays (the two at the
ends half rays on the base); under the face three short red flaps, the middle one larger and in front; two black eyes,
full, without a gleam, that move inside the yellow and change shape with a curved cut in the expressions («basta il
taglio dell'occhio»). Every part is a slab of the same thickness, all on the same plane: they turn in space as one
object, the hair, the face and the flaps follow the movements with inertia, moving and turning in the plane only.

**The order of drawing is fixed** (Daniel was angry twice about it): first every side of every slab, which lies behind
the plane of the faces, then the faces red, yellow, blue, then the eyes; a side never over another solid's face.
Two looks, chosen in Settings > Meridio: «sticker» (one white border round the whole figure, under everything, the
default: it stands out over the map without the disc) and «solid» (the full faces with their thickness).

The figure is drawn in a square of `UNITS` units, the item's side; the geometry here is in those units, y downwards.
Pure Python, no Qt: the window (Meridiana/Assistant/Character.qml, gui/backend/assistant.py) draws these outlines
with an affine matrix for every part (`part_matrix`, the same formula in the QML) and asks here for the eyes' outline
when the cut changes. The prototype approved by Daniel is meridiana-prove/r35-meridio-volto/kimi-4/meridio_kimi4.py
(phase 1d, Kimi): the shapes, colours, poses and cuts are its own."""

from __future__ import annotations

import math
from functools import lru_cache

# R642: Meridio's side on the screen, in logical pixels: the one source of his size (app/assistant SIZE, the window's
# Theme.size.FIGURE and ControlMetrics.figure read it); the drawing's own scale (UNITS) and its small style follow it
SIZE = 50                       # R642 (Daniel 15/11/2026: «meridio leggermente più grande»): 46 before, +9 %
UNITS = 115.0                   # the item's side, in figure units (46 / 115 px a unit: the figure 40 px tall in its
                                # 46 px; 150 at first, 31 px tall, too small on a real screen: Daniel, 14/11/2026)
PLATE = 7.0                     # every slab's thickness
RADIUS = 22.0                   # the face's half disc
TOP = -6.0                      # the face's diameter, where the hair stands
FILLET = 1.8                    # the round of every point of the hair and the flaps (Daniel: «leggermente arrotondate»)
STICKER = 3.5                   # the sticker's white border, units beyond the figure (doubled at his size and under);
                                # R642 («sfondo bianco stile adesivo leggerissimamente più ampio»): 3.2 before, 2.6 px
                                # at 46 px, now 3.0 px at 50
INK = "#181512"                 # the eyes
WHITE = "#FFFFFF"               # the sticker's border
SMALL = SIZE                    # at his side and under, the cuts are a little deeper and the lines thicker

HAIR = tuple((x * 0.92, TOP + (y + 14) * 0.92) for x, y in (
    (-41, -15), (-25, -27), (-35, -49), (-11, -40), (1, -63), (9, -42), (29, -54), (23, -27), (41, -15)))
# the flaps: the pivot each turns about, and its triangle
FLAPS = (
    # R699 (Daniel 17/11/2026): the side flaps mirror each other, a little smaller, their top corners inside the
    # face's yellow (the right one stuck out of it)
    ((-10.5, 11.0), ((-16.5, 6.5), (-4.0, 12.5), (-19.5, 33.0))),
    ((1.0, 14.0), ((-10.0, 13.0), (12.0, 12.0), (1.0, 49.0))),
    ((10.5, 11.0), ((16.5, 6.5), (4.0, 12.5), (19.5, 33.0))),
)
EYES = ((-9.0, 2.5), (9.0, 2.5))            # the eyes' centres at rest
EYE_RADIUS = 4.4
GAZE_REACH = (3.0, 2.0)                     # how far the eyes go for a whole gaze, x and y
# palette C of phase 1b: the faces, and the sides in the dark tone of each, with a slight shift of hue
COLOURS = {"hat": "#4F93AE", "face": "#EDBD59", "flap0": "#9F5043", "flap1": "#C96049", "flap2": "#DF8866"}
SIDES = {"hat": "#41788F", "face": "#CB9B49", "flap0": "#89443D", "flap1": "#A75040", "flap2": "#BC6E56"}
# the faces in the order they are drawn: the red flaps (the middle one last, in front), the yellow, the blue
ORDER = ("flap0", "flap2", "flap1", "face", "hat")
SIDE_COPIES = 5                 # a side is drawn as copies of the face's outline from the back plane to the front
STICKER_COPIES = (0.0, 0.5, 1.0)    # the white border: the front, the middle and the back plane (two leave it thin turned)

# the pose: what each expression sets; every value goes to its target with a spring (POSE_SPRING)
POSE_KEYS = ("gx", "gy", "blink", "happy", "wide", "perplexed", "worried", "sleepy", "speak", "yaw", "pitch", "hat",
             "flap0", "flap1", "flap2", "hairX", "hairY", "faceX", "faceY",
             "flap0X", "flap0Y", "flap1X", "flap1Y", "flap2X", "flap2Y")


def pose(**values) -> dict:
    """A pose with every key, 0 where not given."""
    unknown = set(values) - set(POSE_KEYS)
    if unknown:
        raise KeyError(sorted(unknown))
    return {key: float(values.get(key, 0.0)) for key in POSE_KEYS}


# The expressions of the prototype (kimi-4, POSE_LIBRARY), by the names the program uses: rest (fermo), listen
# (ascolta), think (pensa), speak (parla), happy (contento), surprised (sorpreso), puzzled (perplesso), worried
# (preoccupato), proud (fiero), drowsy (assonnato), asleep (dorme), wave (saluta).
POSES = {
    "rest": pose(),
    "listen": pose(gx=-0.45, gy=0.12, blink=0.06, wide=0.28, hat=-8, faceX=-1, flap0=2, flap1=-2, flap2=3),
    "think": pose(gx=0.82, gy=-0.82, worried=-0.42, hat=-5, hairX=1.5, hairY=-2, flap0=3, flap1=-3, flap2=4),
    "speak": pose(gx=0.2, gy=-0.1, speak=1, hat=2, faceY=-0.7),
    "happy": pose(happy=1, hairY=-1.8, flap0=-8, flap2=8),
    "surprised": pose(wide=1, hairY=-4.5, faceY=1, flap0X=-3, flap0Y=2, flap1Y=4, flap2X=3, flap2Y=2),
    "puzzled": pose(perplexed=1, gx=0.5, gy=-0.2, hat=-7, flap0=-4, flap1=3, flap2=7),
    "worried": pose(worried=1, gy=0.55, hat=4, flap0=7, flap1=-5, flap2=4),
    "proud": pose(happy=0.15, sleepy=0.18, gy=-0.4, pitch=-7, flap0=-10, flap2=10, hairY=-1.8),
    "drowsy": pose(sleepy=0.75, blink=0.12, hat=-6, flap0=5, flap1=1, flap2=-3, faceY=1),
    "asleep": pose(sleepy=1, blink=1, hat=-10, hairX=-1.5, hairY=2.5, faceY=2, flap0=7, flap1=2, flap2=-5),
    "wave": pose(happy=1, yaw=-8, hat=5, flap0=-18, flap1=-3, flap2=18, hairY=-1.8),
}
EXPRESSIONS = tuple(POSES)
# how long a reaction holds before he goes back to what the state says (seconds)
REACTIONS = {"happy": 1.4, "surprised": 0.9, "puzzled": 1.6, "worried": 2.4, "proud": 1.8, "wave": 1.8}
RANDOM_FACES = ("happy", "surprised", "puzzled")    # now and then, by himself (as the brief faces of before)

# the time: the same rhythm as the sun of before (study 17, G.6) where it still holds
BLINK_S = 0.12
BLINK_EVERY = (4.0, 8.0)
GLANCE_EVERY = (7.0, 16.0)
GLANCE_S = (0.6, 1.3)
FACE_EVERY = (60.0, 120.0)
FACE_AFTER_USE = 0.35
FOLLOW_LAG = 0.1
FOLLOW_REST = 2.0
FOLLOW_DEAD = 0.3
LISTEN_S = 1.5                  # he listens this long after the last key typed
DROWSY_S = 120.0                # nothing done for this long (no pointer, no key, no answer): drowsy
ASLEEP_S = 300.0                # and asleep
# the springs (per second): the pose towards its target, as the prototype's spring01 (1 - e^-6v cos 7v over 0,24 s:
# a decay of 25/s and 29 rad/s, a small overshoot); the lags of the inertia as its Followers
POSE_SPRING = (25.0 ** 2 + 29.0 ** 2, 2 * 25.0)
LAG_X = (52.0, 7.5, 0.007)
LAG_Y = (56.0, 7.5, 0.005)
TURN = (48.0, 7.0, 0.05, 0.075)             # the hair's gain, the flaps' and the face's
LAG_LIMIT = 6.0                             # units: how far a part strays from its place
TURN_LIMITS = (10.0, 13.0)                  # degrees: the hair, the flaps
YAW_PER_PX_S = 0.05                         # the body turns towards where it goes: degrees per px/s, up to YAW_LIMIT
PITCH_PER_PX_S = 0.035
YAW_LIMIT, PITCH_LIMIT = 24.0, 16.0
GAZE_TURN = (8.0, 5.0)                      # degrees the body turns with a whole gaze, yaw and pitch


def rounded_polygon(points, radius: float = FILLET, arc_steps: int = 6) -> list[tuple[float, float]]:
    """The polygon with every corner rounded by a circular arc of `radius` (concave corners too), as the prototype."""
    n = len(points)
    result = []
    for i, point in enumerate(points):
        previous, following = points[i - 1], points[(i + 1) % n]
        ux, uy = previous[0] - point[0], previous[1] - point[1]
        vx, vy = following[0] - point[0], following[1] - point[1]
        un, vn = math.hypot(ux, uy), math.hypot(vx, vy)
        ux, uy, vx, vy = ux / un, uy / un, vx / vn, vy / vn
        theta = math.acos(max(-1.0, min(1.0, ux * vx + uy * vy)))
        if theta < 1e-5 or abs(math.pi - theta) < 1e-5:
            result.append(point)
            continue
        # convex or concave, the arc is tangent to both edges inside the angle `theta` they make at the point: its
        # centre on that angle's bisector (R699: the concave corners had the centre on the wrong side, a little bump
        # in every valley of the hair)
        tangent, distance, direction = radius / math.tan(theta / 2), radius / math.sin(theta / 2), 1
        tangent = min(tangent, un * 0.45, vn * 0.45)
        bx, by = ux + vx, uy + vy
        bn = math.hypot(bx, by)
        cx, cy = point[0] + direction * bx / bn * distance, point[1] + direction * by / bn * distance
        ax, ay = point[0] + ux * tangent, point[1] + uy * tangent
        ex, ey = point[0] + vx * tangent, point[1] + vy * tangent
        start, end = math.atan2(ay - cy, ax - cx), math.atan2(ey - cy, ex - cx)
        delta = (end - start + math.pi) % (2 * math.pi) - math.pi
        result.append((ax, ay))
        for step in range(1, arc_steps + 1):
            angle = start + delta * step / arc_steps
            result.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return result


def face_outline(n: int = 56) -> list[tuple[float, float]]:
    return [(RADIUS * math.cos(math.pi - math.pi * i / n), TOP + RADIUS * math.sin(math.pi - math.pi * i / n))
            for i in range(n + 1)]


@lru_cache(maxsize=None)
def outline(key: str) -> tuple[tuple[float, float], ...]:
    """The face of the part `key` at rest, in figure units."""
    if key == "face":
        return tuple(face_outline())
    if key == "hat":
        return tuple(rounded_polygon(HAIR))
    return tuple(rounded_polygon(FLAPS[int(key[-1])][1]))


def pivot(key: str) -> tuple[float, float]:
    """The point the part turns about in the plane."""
    if key == "hat":
        return (0.0, TOP)
    if key == "face":
        return (0.0, 0.0)
    return FLAPS[int(key[-1])][0]


def turn_and_shift(key: str, p: dict) -> tuple[float, tuple[float, float]]:
    """The part's own movement in the plane in the pose `p`: its angle (degrees) about `pivot` and its shift."""
    if key == "hat":
        return p["hat"], (p["hairX"], p["hairY"])
    if key == "face":
        return 0.0, (p["faceX"], p["faceY"])
    return p[key], (p[key + "X"], p[key + "Y"])


@lru_cache(maxsize=None)
def sticker_outline(key: str, small: bool = True) -> tuple[tuple[float, float], ...]:
    """The part's outline grown by the sticker's border (`STICKER` units at 46 px and under, half above), round."""
    from shapely.geometry import Polygon
    grown = Polygon(outline(key)).buffer(STICKER if small else STICKER / 2, quad_segs=4)
    return tuple((round(x, 3), round(y, 3)) for x, y in grown.exterior.coords[:-1])


# the projection: orthographic, the figure turned by yaw about the vertical and by pitch about the horizontal. A point
# of a plane at depth z goes on the screen by an affine map: a matrix (a, b, c, d, e, f), X = a x + b y + c,
# Y = d x + e y + f. Character.qml computes the same matrices (partMatrix), checked by the Quick tests.

def view_matrix(yaw: float, pitch: float, scale: float, ox: float, oy: float, z: float) -> tuple:
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    return (scale * cy, 0.0, ox + scale * z * sy, scale * sy * sp, scale * cp, oy - scale * z * cy * sp)


def depth_shift(yaw: float, pitch: float, scale: float, dz: float) -> tuple[float, float]:
    """How far on the screen a point goes when it goes `dz` deeper (towards the back: dz < 0)."""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    sp = math.sin(math.radians(pitch))
    return (scale * dz * sy, -scale * dz * cy * sp)


def compose(m: tuple, n: tuple) -> tuple:
    """The matrix that applies `n` and then `m`."""
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + b * s, a * q + b * t, a * r + b * u + c, d * p + e * s, d * q + e * t, d * r + e * u + f)


def turn_matrix(angle: float, about: tuple[float, float], shift: tuple[float, float]) -> tuple:
    """A turn of `angle` degrees about `about`, then a shift."""
    co, si = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    px, py = about
    return (co, -si, px - co * px + si * py + shift[0], si, co, py - si * px - co * py + shift[1])


def part_matrix(key: str, p: dict, scale: float, ox: float, oy: float, front: bool = True) -> tuple:
    """Where the part's face (or its back) goes on the screen in the pose `p`."""
    angle, shift = turn_and_shift(key, p)
    z = PLATE / 2 if front else -PLATE / 2
    return compose(view_matrix(p["yaw"], p["pitch"], scale, ox, oy, z), turn_matrix(angle, pivot(key), shift))


def apply(m: tuple, points) -> list[tuple[float, float]]:
    a, b, c, d, e, f = m
    return [(a * x + b * y + c, d * x + e * y + f) for x, y in points]


def origin(side: float) -> tuple[float, float, float]:
    """The scale and the centre of the figure in an item of `side` px: as the prototype, a hair under the middle."""
    return side / UNITS, side / 2, side / 2 + side / 240


def draw_plan() -> list[tuple[str, str, float]]:
    """What is drawn, in order: (layer, part, depth from the front, 0 to 1). The sticker's white first, then every
    side (copies of the outline from the back to just behind the front), then the faces red, yellow, blue."""
    plan = []
    plan += [("sticker", key, t) for key in ORDER for t in STICKER_COPIES]
    plan += [("side", key, (SIDE_COPIES - i) / SIDE_COPIES) for key in ORDER for i in range(SIDE_COPIES)]
    plan += [("face", key, 0.0) for key in ORDER]
    return plan


def fitted(side: float, margin: float = 0.04) -> tuple[float, float, float]:
    """The scale and centre that make the figure at rest fill a square of `side` px (an icon: the status bar's)."""
    points = [q for key in ORDER for q in outline(key)]
    x0, x1 = min(x for x, _y in points), max(x for x, _y in points)
    y0, y1 = min(y for _x, y in points), max(y for _x, y in points)
    scale = side * (1 - 2 * margin) / max(x1 - x0, y1 - y0)
    return scale, side / 2 - scale * (x0 + x1) / 2, side / 2 - scale * (y0 + y1) / 2


def projected(p: dict, side: float, place: tuple | None = None) -> list[tuple[str, str, list]]:
    """The draw plan with every outline on the screen of an item of `side` px (`place`: scale and centre, `origin`
    by default): what the window shows, for the tests and the status bar's icon (the window draws the same outlines
    with the same matrices)."""
    scale, ox, oy = place or origin(side)
    small = side <= SMALL
    out = []
    for layer, key, t in draw_plan():
        m = part_matrix(key, p, scale, ox, oy)
        dx, dy = depth_shift(p["yaw"], p["pitch"], scale, -PLATE * t)
        m = (m[0], m[1], m[2] + dx, m[3], m[4], m[5] + dy)
        points = sticker_outline(key, small) if layer == "sticker" else outline(key)
        out.append((layer, key, apply(m, points)))
    return out


def projected_eyes(p: dict, side: float, place: tuple | None = None) -> list[dict]:
    """Both eyes on the screen: their outline, the arch and its width in px."""
    scale, ox, oy = place or origin(side)
    face = part_matrix("face", p, scale, ox, oy)
    out = []
    for index, eye in enumerate(eyes(p, side <= SMALL)):
        cx, cy = eye_centre(p, index)
        m = compose(face, (1.0, 0.0, cx, 0.0, 1.0, cy))
        out.append({"outline": apply(m, eye["outline"]), "arch": apply(m, eye["arch"]),
                    "arch_line": eye["arch_line"] * scale})
    return out


def colour(layer: str, key: str) -> str:
    return WHITE if layer == "sticker" else SIDES[key] if layer == "side" else COLOURS[key]


# the eyes: a full black circle at rest; an expression cuts it with a curve from above (the lid: think, worried,
# puzzled on one eye, drowsy, asleep, a blink) or from below (happy, a crescent), and the cut's edge is a black line of
# the eye itself; surprise makes it larger with a thin arch apart above. The outline is computed here, centred on the
# eye; the window places it (the gaze, the face's shift) and asks again only when the cut changes.

def eye_cuts(p: dict, index: int, small: bool = True) -> dict:
    """The eye's cut in the pose `p`: radius, how deep from above (0-1) and from below, the lid's tilt, the line."""
    upper = max(p["blink"] * 0.99, p["sleepy"] * 0.78, abs(p["worried"]) * 0.46,
                p["perplexed"] * 0.48 if index == 0 else 0.0, p["speak"] * 0.08)
    lower = p["happy"] * 0.66
    tilt = (-1 if index == 0 else 1) * 0.36 * p["worried"]
    boost = 0.06 if small else 0.0
    # the deeper cut of the small figure comes in with the cut (the prototype added it at once, a small jump)
    upper = min(0.98 if small else 0.94, upper + boost * min(1.0, max(0.0, upper) / 0.06)) if upper > 0.005 else 0.0
    lower = min(0.88, lower + boost * min(1.0, max(0.0, lower) / 0.06)) if lower > 0.005 else 0.0
    return {"radius": EYE_RADIUS * (1 + 0.18 * p["wide"]), "upper": upper, "lower": lower, "tilt": tilt,
            "line": 1.85 if small else 1.15, "arch": p["wide"] > 0.5,
            "arch_line": 1.05 if small else 0.72}


def lid(r: float, amount: float, tilt: float, upper: bool, x: float) -> tuple[float, float]:
    """The lid's curve over the eye of radius `r` centred on 0 at `x`: its height and slope (a parabola, as the
    prototype's arc)."""
    u = max(-1.0, min(1.0, x / r))
    if upper:
        return -r + 2 * r * amount + tilt * r * u - 0.10 * r * (1 - u * u), tilt + 0.20 * u
    return r - 2 * r * amount - 0.18 * r * (1 - u * u), 0.36 * u


def eye_outline(radius: float, upper: float = 0.0, lower: float = 0.0, tilt: float = 0.0, line: float = 1.85,
                samples: int = 64) -> list[tuple[float, float]]:
    """The eye's black outline, centred on 0: the circle less what the cuts take, their line included (the line of
    width `line` along the cut, inside the circle, is the eye's own edge). [] when the eye is wholly closed."""
    r, h = radius, line / 2

    def bounds(x):
        c = math.sqrt(max(0.0, r * r - x * x))
        top, bottom = -c, c
        if upper > 0:
            y, slope = lid(r, upper, tilt, True, x)
            top = max(top, y - h * math.sqrt(1 + slope * slope))
        if lower > 0:
            y, slope = lid(r, lower, 0.0, False, x)
            bottom = min(bottom, y + h * math.sqrt(1 + slope * slope))
        return top, bottom

    xs = [-r * math.cos(math.pi * k / samples) for k in range(samples + 1)]
    rows = [bounds(x) for x in xs]
    gaps = [b - t for t, b in rows]
    runs, run = [], []
    for k, g in enumerate(gaps):
        if g > 1e-9:
            run.append(k)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    if not runs:
        return []
    run = max(runs, key=len)
    first, last = run[0], run[-1]

    def crossing(i, j):                 # between a sample outside (i) and one inside (j)
        x = xs[i] + (xs[j] - xs[i]) * (-gaps[i]) / (gaps[j] - gaps[i])
        top, _bottom = bounds(x)
        return (x, top)
    tops = [(xs[k], rows[k][0]) for k in run]
    bottoms = [(xs[k], rows[k][1]) for k in reversed(run)]
    left = [crossing(first - 1, first)] if first > 0 else []
    right = [crossing(last + 1, last)] if last < samples else []
    return left + tops + right + bottoms


def eye_arch(radius: float) -> list[tuple[float, float]]:
    """Surprise's thin arch apart above the eye, centred on the eye."""
    return [(radius * 1.04 * v, -radius * 1.38 - radius * 0.25 * (1 - v * v))
            for v in (-1 + 2 * k / 32 for k in range(33))]


def eye_centre(p: dict, index: int) -> tuple[float, float]:
    """Where the eye's centre is on the face's plane: its place, the gaze, the face's shift."""
    gx, gy = max(-1.0, min(1.0, p["gx"])), max(-1.0, min(1.0, p["gy"]))
    return (EYES[index][0] + p["faceX"] + gx * GAZE_REACH[0], EYES[index][1] + p["faceY"] + gy * GAZE_REACH[1])


EYE_KEYS = ("blink", "happy", "wide", "perplexed", "worried", "sleepy", "speak")


def eye_key(p: dict, small: bool = True) -> tuple:
    """What the eyes' outline depends on, rounded: the same key, the same outline (the window asks only on a new one)."""
    return tuple(round(p[k], 2) for k in EYE_KEYS) + (bool(small),)


@lru_cache(maxsize=512)
def _eyes(key: tuple) -> tuple:
    p = pose(**dict(zip(EYE_KEYS, key[:-1], strict=True)))
    out = []
    for index in (0, 1):
        cut = eye_cuts(p, index, key[-1])
        out.append({"outline": eye_outline(cut["radius"], cut["upper"], cut["lower"], cut["tilt"], cut["line"]),
                    "arch": eye_arch(cut["radius"]) if cut["arch"] else [], "arch_line": cut["arch_line"]})
    return tuple(out)


def eyes(p: dict, small: bool = True) -> tuple:
    """Both eyes' outlines for the pose, centred on each eye (place them at `eye_centre`)."""
    return _eyes(eye_key(p, small))


def window_data() -> dict:
    """What the window needs once: the parts in the order they are drawn, the poses, the rhythm."""
    return {
        "units": UNITS, "plate": PLATE, "ink": INK, "white": WHITE, "small": SMALL,
        "parts": [{"key": key, "colour": COLOURS[key], "side": SIDES[key], "pivot": list(pivot(key))}
                  for key in ORDER],
        "eyes": [list(e) for e in EYES], "gazeReach": list(GAZE_REACH),
        "sideCopies": SIDE_COPIES, "stickerCopies": list(STICKER_COPIES),
        "poses": POSES, "poseKeys": list(POSE_KEYS), "eyeKeys": list(EYE_KEYS),
        "reactions": REACTIONS, "randomFaces": list(RANDOM_FACES),
        "blink": BLINK_S, "blinkEvery": list(BLINK_EVERY), "glanceEvery": list(GLANCE_EVERY), "glance": list(GLANCE_S),
        "faceEvery": list(FACE_EVERY), "faceAfterUse": FACE_AFTER_USE, "followLag": FOLLOW_LAG,
        "followRest": FOLLOW_REST, "followDead": FOLLOW_DEAD, "listen": LISTEN_S, "drowsy": DROWSY_S,
        "asleep": ASLEEP_S, "poseSpring": list(POSE_SPRING), "lagX": list(LAG_X), "lagY": list(LAG_Y),
        "turn": list(TURN), "lagLimit": LAG_LIMIT, "turnLimits": list(TURN_LIMITS),
        "yawPerPx": YAW_PER_PX_S, "pitchPerPx": PITCH_PER_PX_S, "yawLimit": YAW_LIMIT, "pitchLimit": PITCH_LIMIT,
        "gazeTurn": list(GAZE_TURN),
    }
