"""The assistant's shell, without a model yet (study 14, sections 7.3 and 8; study 17, theme G; design 3.9):
Meridio, a sun at noon over the line of the meridian, drawn on a grid of 24 as Lucide's icons, and his pixel
twin on a grid of 17 (R34); the state machine of his small movements (`Mood`: the rays that turn one turn a
minute and stop a few seconds after the chat is closed, the breath, the blink every 4-8 s, the glance, the gaze
that follows a point, four brief faces); where the character floats on each tab and where his speech bubble
opens (R33: never over him, from the free side towards the middle of the view, never over what is to be
avoided); the questions ready for each tab. No Qt here: ui/assistant.py draws and moves him.

Meridio is Daniel's preference among the three characters of the canvas (22/10/2026 evening), still to be
confirmed: the name is a constant here and in the preferences, nowhere else."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .. import theme_colors

NAME = "Meridio"
SIZE = 46                       # the character alone, closed: a circle of 46 px
MARGIN = 12
INK = "#24211d"                 # the outline, the eyes and the smile: dark in both themes, as a sticker
STYLES = ("smooth", "pixel")    # the two drawings of the character (Preferences > Assistant, R34)
EXPRESSIONS = ("wink", "surprise", "grin", "hmm")      # the brief faces (Daniel, 23/10/2026: «smorfie»)
SMILE = "M10.2 12.1Q12 13.5 13.8 12.1"
GRIN = "M9.6 11.9Q12 14.3 14.4 11.9"
FLAT = "M10.6 12.6H13.4"
DISC = (12.0, 10.2, 5.3)        # the sun's disc: centre and radius, grid of 24
RAY_RADII = (6.9, 8.6)          # the rays, from the disc's edge outwards
RAYS_CLIP_Y = 16.4              # the rays are drawn above this line: turning, they rise on one side and set on the
                                # other, never over the noon line (16.9-21.8) nor the horizon (19.4)
HORIZON = "M3 19.4H21M12 16.9V21.8"


def ray_path(angle: float = 0.0, above: float | None = None) -> str:
    """Twelve rays 30 degrees apart around the disc, turned by `angle` degrees (clockwise, as the sun goes).
    At angle 0 the seven above the horizon are the ones Meridio had from the start (study 14). With `above`,
    each ray is cut at that line and what is under it left out: Qt's SVG renderer (SVG Tiny) has no clipPath and
    painted the clipping rectangle in black (24/10/2026), so the cut is made here, on the geometry."""
    cx, cy, _r = DISC
    r0, r1 = RAY_RADII
    parts = []
    for k in range(12):
        a = math.radians(180 - k * 30 - angle)       # from the left, over the top, to the right, then below
        c, s = math.cos(a), math.sin(a)
        x0, y0, x1, y1 = cx + r0 * c, cy - r0 * s, cx + r1 * c, cy - r1 * s
        if above is not None:
            if y0 > above and y1 > above:
                continue
            if y0 > above or y1 > above:              # one end under the line: cut the segment there
                t = (above - y0) / (y1 - y0)
                xc = x0 + (x1 - x0) * t
                x0, y0, x1, y1 = (xc, above, x1, y1) if y0 > above else (x0, y0, xc, above)
        parts.append(f"M{x0:.2f} {y0:.2f}L{x1:.2f} {y1:.2f}")
    return "".join(parts)


RAYS = ray_path()


def disc_colour(assistant: str, dark: bool | None = None) -> str:
    """The disc of the sun: the assistant's colour (the hue opposite to the one chosen, theme_colors) at a
    chroma of 0.07-0.15, brought to a lightness of 0.58-0.72 in the dark theme and of 0.80 in the light one
    (R33: at 0.58 on a light panel the face was too dark). `dark` is told by the colour itself when not given:
    the light theme's assistant colour has L 0.42, the dark theme's 0.80."""
    L, C, h = theme_colors.lch(assistant)
    if dark is None:
        dark = L > 0.6
    C = min(0.15, max(0.07 if dark else 0.09, C))
    return theme_colors.hex_of(min(0.72, max(0.58, L)) if dark else 0.80, C, h)


def svg(text: str, assistant: str, thinking: bool = False, gaze: tuple[int, int] = (0, 0), blink: bool = False,
        expression: str = "", rays: float = 0.0, dark: bool | None = None, parts: str = "all") -> str:
    """Meridio as SVG on a grid of 24: `text` is the theme's text colour (the rays, the horizon), `assistant` the
    assistant's. The eyes are moved by `gaze` (-1, 0 or 1 on each axis) half a unit; `blink` closes them; thinking,
    they go up by 0.8 and three dots appear at the top right, in the colour of the text; `expression` is one of
    EXPRESSIONS or ""; `rays` turns the rays (degrees). `parts` is "all", "rays" (the turning layer alone) or
    "face" (everything but the rays): the window draws the two layers apart to turn one without the other."""
    cx, cy, r = DISC
    gx = max(-1, min(1, gaze[0])) * 0.5
    gy = max(-1, min(1, gaze[1])) * 0.5
    if expression == "hmm":
        gx, gy = 0.5, -0.5
    eye_y = cy - 0.7 - (0.8 if thinking else 0.0) + gy
    left, right = 10.1 + gx, 13.9 + gx
    eye_r = 1.15 if expression == "surprise" else 0.9
    eyes = ""
    for x, closed in ((left, blink or expression == "wink"), (right, blink)):
        if closed:
            eyes += (f'<path d="M{x - 0.9:g} {eye_y:g}H{x + 0.9:g}" fill="none" stroke="{INK}" stroke-width="1" '
                     f'stroke-linecap="round"/>')
        else:
            eyes += f'<circle cx="{x:g}" cy="{eye_y:g}" r="{eye_r:g}" fill="{INK}"/>'
    if expression == "surprise":
        mouth = f'<ellipse cx="12" cy="12.6" rx="0.75" ry="0.95" fill="none" stroke="{INK}" stroke-width="1.1"/>'
    else:
        d = {"grin": GRIN, "hmm": FLAT}.get(expression, SMILE)
        mouth = (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{1.3 if expression == "grin" else 1.2}" '
                 f'stroke-linecap="round"/>')
    dots = "".join(f'<circle cx="{x}" cy="3.6" r="0.75" fill="{text}"/>' for x in (19.2, 21.2, 23.2)) if thinking else ""
    # the layer alone ("rays") is turned and clipped by the window's painter; the whole picture cuts its own rays
    cut = RAYS_CLIP_Y if parts == "all" else None
    ray_layer = (f'<path d="{ray_path(rays, cut)}" fill="none" stroke="{text}" stroke-width="1.3" '
                 f'stroke-linecap="round"/>') if parts in ("all", "rays") else ""
    face = (f'<path d="{HORIZON}" fill="none" stroke="{text}" stroke-width="1.3" stroke-linecap="round"/>'
            f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{disc_colour(assistant, dark)}" stroke="{INK}" '
            f'stroke-width="1.3"/>{mouth}{eyes}{dots}') if parts in ("all", "face") else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">'
            f'{ray_layer}{face}</svg>')


# The pixel twin (R34): a grid of 17 cells, two device pixels each at the 34 px the character is drawn at inside
# his circle of 46. The same layout as the smooth one scaled by 17/24: the disc's centre at (8, 7), the eyes at
# columns 6 and 10, the horizon on row 14, the noon line on column 8. Drawn cell by cell; "k" is the ink, "d" the
# disc, "." nothing. The rays are rasterised in eight steps of 3.75 degrees (one period of the twelve rays is
# 30 degrees): turning by degrees they would flicker at this size, so they go by steps.
PIXEL_N = 17
PIXEL_DISC = (
    ".................",
    ".................",
    ".................",
    ".......kkk.......",
    ".....kkdddkk.....",
    ".....kdddddk.....",
    "....kdddddddk....",
    "....kdddddddk....",
    "....kdddddddk....",
    ".....kdddddk.....",
    ".....kkdddkk.....",
    ".......kkk.......",
)
PIXEL_EYES = ((6, 6), (10, 6))                              # open eyes, one cell each
PIXEL_MOUTHS = {
    "": ((6, 8), (7, 9), (8, 9), (9, 9), (10, 8)),          # the smile
    "wink": ((6, 8), (7, 9), (8, 9), (9, 9), (10, 8)),
    "grin": ((5, 8), (6, 9), (7, 10), (8, 10), (9, 10), (10, 9), (11, 8)),
    "surprise": ((8, 8), (7, 9), (9, 9), (8, 10)),         # a small "o"
    "hmm": ((6, 9), (7, 9), (8, 9), (9, 9), (10, 9)),       # flat
}
PIXEL_DOTS = ((12, 2), (14, 2), (16, 2))
PIXEL_HORIZON = tuple((x, 14) for x in range(2, 15)) + ((8, 12), (8, 13), (8, 15))
PIXEL_RAY_STEPS = 8
PIXEL_RAYS_CLIP_ROW = 11


def pixel_rays(step: int) -> tuple[tuple[int, int], ...]:
    """The cells of the twelve rays turned by `step` eighths of their 30-degree period, above row 11."""
    cells = set()
    for k in range(12):
        a = math.radians(k * 30 - (step % PIXEL_RAY_STEPS) * 30 / PIXEL_RAY_STEPS)
        for radius in (5.0, 5.6, 6.1):
            x, y = round(8 + radius * math.cos(a)), round(7 - radius * math.sin(a))
            if 0 <= x < PIXEL_N and 0 <= y <= PIXEL_RAYS_CLIP_ROW:
                cells.add((x, y))
    return tuple(sorted(cells))


def pixel_cells(thinking: bool = False, gaze: tuple[int, int] = (0, 0), blink: bool = False, expression: str = "",
                step: int = 0, parts: str = "all") -> dict[str, set[tuple[int, int]]]:
    """The cells of the pixel Meridio by colour: "text" (rays, horizon, dots), "disc" and "ink"."""
    out: dict[str, set] = {"text": set(), "disc": set(), "ink": set()}
    if parts in ("all", "rays"):
        out["text"].update(pixel_rays(step))
    if parts not in ("all", "face"):
        return out
    for y, row in enumerate(PIXEL_DISC):
        for x, c in enumerate(row):
            if c == "d":
                out["disc"].add((x, y))
            elif c == "k":
                out["ink"].add((x, y))
    out["text"].update(PIXEL_HORIZON)
    gx = max(-1, min(1, gaze[0]))
    gy = max(-1, min(1, gaze[1]))
    if expression == "hmm":
        gx, gy = 1, -1
    if thinking:
        gy -= 1
    for n, (ex, ey) in enumerate(PIXEL_EYES):
        x, y = ex + gx, ey + gy
        if blink or (expression == "wink" and n == 0):
            out["ink"].update({(x - 1, y + 1), (x, y + 1), (x + 1, y + 1)})     # the lid, a line one row down
        elif expression == "surprise":
            out["ink"].update({(x, y), (x, y - 1)})                            # wide open: two cells tall
        else:
            out["ink"].add((x, y))
    out["ink"].update(PIXEL_MOUTHS.get(expression, PIXEL_MOUTHS[""]))
    if thinking:
        out["text"].update(PIXEL_DOTS)
    out["disc"] -= out["ink"]
    return out


def pixel_svg(text: str, assistant: str, thinking: bool = False, gaze: tuple[int, int] = (0, 0), blink: bool = False,
              expression: str = "", step: int = 0, dark: bool | None = None, parts: str = "all") -> str:
    """The pixel Meridio as SVG, one rect per run of cells, crisp edges; the same arguments as `svg`, with the
    rays' `step` (0-7) in place of their angle."""
    cells = pixel_cells(thinking, gaze, blink, expression, step, parts)
    colours = {"text": text, "disc": disc_colour(assistant, dark), "ink": INK}
    rects = []
    for key in ("text", "disc", "ink"):
        for y in range(PIXEL_N):
            x = 0
            while x < PIXEL_N:
                if (x, y) in cells[key]:
                    start = x
                    while (x, y) in cells[key]:
                        x += 1
                    rects.append(f'<rect x="{start}" y="{y}" width="{x - start}" height="1" fill="{colours[key]}"/>')
                else:
                    x += 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PIXEL_N} {PIXEL_N}" width="{PIXEL_N}" '
            f'height="{PIXEL_N}" shape-rendering="crispEdges">{"".join(rects)}</svg>')


def pixel_step(rays: float) -> int:
    """The step (0-7) of the pixel rays for the angle of the smooth ones: the same state machine, drawn by steps."""
    return int((rays % 30.0) / (30.0 / PIXEL_RAY_STEPS)) % PIXEL_RAY_STEPS


# The small movements (study 17, G.6 and the decisions of 23/10/2026): a state machine with the time as input,
# deterministic for a seed. The window asks for the frame twenty times a second and redraws only when it changed.
IDLE, THINKING, ANSWERING = "idle", "thinking", "answering"
AWAKE_S = 5.0                   # after the chat is closed or used, the rays turn and the breath goes this long
RAYS_DEG_PER_S = 6.0            # one turn a minute (G2, slowed down: a continuous movement at the edge of sight)
BREATH_S = 4.0                  # the breath's period; the scale goes 1 to 1.04 with a sine
BLINK_S = 0.12
BLINK_EVERY = (4.0, 8.0)
GLANCE_EVERY = (7.0, 16.0)      # the eyes look aside for a moment now and then: the small movements
GLANCE_S = (0.6, 1.3)
EXPRESSION_EVERY = (60.0, 120.0)    # a face at random, slowly (Daniel: «ogni tanto a random»)
EXPRESSION_S = (0.8, 1.3)
EXPRESSION_AFTER_USE = 0.35     # and soon after the chat is used
FOLLOW_LAG = 0.1                # the gaze follows a point this much later
FOLLOW_REST = 2.0               # and comes back to the centre when the point stood still this long
FOLLOW_DEAD = 0.3               # a point nearer than this (in character sizes) is straight ahead


@dataclass(frozen=True)
class Frame:
    """What to draw: the same frame means nothing to redraw."""
    gaze: tuple[int, int] = (0, 0)
    blink: bool = False
    thinking: bool = False
    expression: str = ""
    rays: float = 0.0           # degrees, 0-360
    scale: float = 1.0          # the breath
    awake: bool = False         # the rays turn and the breath goes


class Mood:
    """Meridio's state (idle, thinking, answering) and his small movements over time. `now` is any clock in
    seconds, given by the caller: the tests run it, the window gives the monotonic clock."""

    def __init__(self, seed: int = 0, now: float = 0.0):
        self.random = random.Random(seed)
        self.state = IDLE
        self.opened = False
        self.awake_until = now + AWAKE_S
        self._last = now
        self._angle = 0.0
        self._breath = 0.0
        self.next_blink = now + self.random.uniform(*BLINK_EVERY)
        self.blink_until = -1.0
        self.next_glance = now + self.random.uniform(*GLANCE_EVERY)
        self.glance: tuple[tuple[int, int], float] = ((0, 0), -1.0)
        self.next_expression = now + self.random.uniform(*EXPRESSION_EVERY)
        self.expression: tuple[str, float] = ("", -1.0)
        self.point: tuple[int, int] | None = None          # the gaze asked for, and when it was asked
        self.point_since = -1.0
        self.point_moved = -1.0
        self.gaze = (0, 0)

    # what happens

    def set_state(self, state: str, now: float) -> None:
        if state not in (IDLE, THINKING, ANSWERING):
            raise ValueError(state)
        self.state = state
        self.touch(now)

    def set_opened(self, opened: bool, now: float) -> None:
        self.opened = opened
        self.touch(now)

    def touch(self, now: float) -> None:
        """The chat used (opened, closed, a question sent): awake for a while, and a face soon."""
        self.awake_until = max(self.awake_until, now + AWAKE_S)
        if now >= self.expression[1]:
            self.next_expression = min(self.next_expression, now + EXPRESSION_AFTER_USE)

    def look_at(self, point: tuple[float, float] | None, now: float) -> None:
        """A point to look at, in character sizes from the centre of the character (the pointer); None to stop."""
        if point is None:
            self.point = None
            return
        gaze = tuple(0 if abs(v) < FOLLOW_DEAD else (1 if v > 0 else -1) for v in point)
        if gaze != self.point:
            self.point = gaze
            self.point_since = now
        self.point_moved = now

    # what to draw

    def awake(self, now: float) -> bool:
        return self.opened or self.state != IDLE or now < self.awake_until

    def frame(self, now: float) -> Frame:
        dt = max(0.0, now - self._last)
        self._last = now
        awake = self.awake(now)
        if awake:
            self._angle = (self._angle + RAYS_DEG_PER_S * dt) % 360.0
        if awake or self._breath > 0.0:
            b = self._breath + dt
            if not awake and (b >= BREATH_S or b % BREATH_S < self._breath % BREATH_S):
                b = 0.0                                 # asleep: the breath ends its cycle, then stops
            self._breath = b
        scale = 1.0 + 0.02 * (1.0 - math.cos(2 * math.pi * self._breath / BREATH_S))
        if now >= self.next_blink:
            self.blink_until = now + BLINK_S
            self.next_blink = now + self.random.uniform(*BLINK_EVERY)
        if now >= self.next_expression:
            self.expression = (self.random.choice(EXPRESSIONS), now + self.random.uniform(*EXPRESSION_S))
            self.next_expression = now + self.random.uniform(*EXPRESSION_EVERY)
        if now >= self.next_glance:
            aside = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
            self.glance = (self.random.choice(aside), now + self.random.uniform(*GLANCE_S))
            self.next_glance = now + self.random.uniform(*GLANCE_EVERY)
        if self.point is not None and now - self.point_moved >= FOLLOW_REST:
            self.point = None                           # still for a while: back to the centre
        if self.point is not None:
            if now - self.point_since >= FOLLOW_LAG:
                self.gaze = self.point
        elif now < self.glance[1]:
            self.gaze = self.glance[0]
        else:
            self.gaze = (0, 0)
        expression = self.expression[0] if now < self.expression[1] else ""
        return Frame(gaze=self.gaze, blink=now < self.blink_until, thinking=self.state == THINKING,
                     expression=expression, rays=round(self._angle, 2) % 360.0, scale=round(scale, 4), awake=awake)


def _tabs() -> tuple:
    from .. import phases
    return tuple(phases.ids())


TABS = _tabs()          # the ids of the phases (phases.py): where the character stands is kept per phase

# Where the assistant stands in the central area (the panels are outside it): the side of the area it keeps to,
# left or right and top or bottom, and its distances from those two edges. Kept as distances from the edges, it
# stays in its corner when the area changes size (a panel opened or closed, the window narrowed).
Anchor = tuple[str, str, int, int]
Rect = tuple[int, int, int, int]        # x, y, width, height


def default_anchor(tab: str, reserved_bottom: int = 0) -> Anchor:
    """Where the assistant floats on a tab (study 14, 7.3): at the bottom right of the card in the middle; on the
    model above the sun bar, on the plant above the plan's attribution (`reserved_bottom` pixels)."""
    # since the drafts of the phases (24/10/2026) the results stand in the middle of every phase: bottom right
    return ("right", "bottom", MARGIN, MARGIN + (reserved_bottom if tab in ("model", "plant") else 0))


def place(anchor: Anchor, size: tuple[int, int], area: tuple[int, int]) -> tuple[int, int]:
    """The top left corner of a widget of `size` standing at `anchor` in an area of `area` pixels."""
    hside, vside, dx, dy = anchor
    w, h = size
    aw, ah = area
    x = dx if hside == "left" else aw - w - dx
    y = dy if vside == "top" else ah - h - dy
    return clamp((x, y), area, size)


def anchor_of(pos: tuple[int, int], size: tuple[int, int], area: tuple[int, int]) -> Anchor:
    """Where a widget dragged to `pos` stands: the nearest sides of the area and its distances from them."""
    x, y = pos
    w, h = size
    aw, ah = area
    hside = "left" if x + w / 2 < aw / 2 else "right"
    vside = "top" if y + h / 2 < ah / 2 else "bottom"
    dx = x if hside == "left" else aw - w - x
    dy = y if vside == "top" else ah - h - y
    return hside, vside, max(0, int(dx)), max(0, int(dy))


def valid_anchor(value) -> Anchor | None:
    """An anchor read back from the window's state, or None when it is not one."""
    try:
        hside, vside, dx, dy = value
    except (TypeError, ValueError):
        return None
    if hside in ("left", "right") and vside in ("top", "bottom") and all(isinstance(d, int) and d >= 0 for d in (dx, dy)):
        return hside, vside, dx, dy
    return None


def clamp(place: tuple[int, int], area: tuple[int, int], size: tuple[int, int]) -> tuple[int, int]:
    """A place kept inside the area, as much as the widget fits."""
    x = max(0, min(int(place[0]), area[0] - size[0]))
    y = max(0, min(int(place[1]), area[1] - size[1]))
    return x, y


# The speech bubble (R33, design 3.9): it opens beside the character, from his free side towards the middle of
# the view, with its tail towards him; never over him, never over what the window says to avoid (the selection,
# the point being drawn); when there is no room, the character slides to a free corner and opens there.
TAIL = 12                       # the tail's length, px
GAP = 4                         # between the character's circle and the tail's tip
BUBBLE_MIN = (280, 240)
BUBBLE_DEFAULT = (320, 400)


@dataclass(frozen=True)
class Bubble:
    x: int
    y: int
    width: int
    height: int
    tail: str                   # the side of the bubble the tail is on: "left", "right", "top", "bottom"
    at: int                     # where along that side the tail points, px from the bubble's left or top

    @property
    def rect(self) -> Rect:
        return self.x, self.y, self.width, self.height

    @property
    def grip(self) -> str:
        """The corner that resizes it, opposite the tail: "top-left", "top-right", "bottom-left", "bottom-right"."""
        if self.tail in ("left", "right"):
            vertical = "top" if self.at > self.height / 2 else "bottom"
            return f"{vertical}-{'right' if self.tail == 'left' else 'left'}"
        horizontal = "left" if self.at > self.width / 2 else "right"
        return f"{'bottom' if self.tail == 'top' else 'top'}-{horizontal}"


def overlaps(a: Rect, b: Rect) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def bubble_size(size: tuple[int, int], area: tuple[int, int]) -> tuple[int, int]:
    """The bubble's size kept to what the area can hold beside the character (never under BUBBLE_MIN unless
    the area itself is smaller)."""
    w = min(size[0], area[0] - SIZE - GAP - 2 * MARGIN)
    h = min(size[1], area[1] - 2 * MARGIN)
    return max(min(BUBBLE_MIN[0], area[0]), w), max(min(BUBBLE_MIN[1], area[1]), h)


def bubble_place(character: Rect, size: tuple[int, int], area: tuple[int, int],
                 avoid: tuple[Rect, ...] | list = ()) -> Bubble | None:
    """Where a bubble of `size` opens for the character at `character` (x, y, w, h) in an area of `area`:
    beside him towards the middle of the area first, then above or below, the first that is inside the area
    and over neither him nor an `avoid` rectangle; None when none is."""
    cx, cy, cw, ch = character
    aw, ah = area
    bw, bh = size
    mid_x, mid_y = cx + cw / 2, cy + ch / 2
    candidates = []
    horizontal = ["left", "right"] if mid_x > aw / 2 else ["right", "left"]      # towards the middle first
    vertical = ["top", "bottom"] if mid_y > ah / 2 else ["bottom", "top"]
    for side in horizontal:                 # the bubble (its tail included) on this side of the character
        x = cx - GAP - bw if side == "left" else cx + cw + GAP
        y = cy + ch - bh if mid_y > ah / 2 else cy       # its near edge level with the character's
        y = max(0, min(y, ah - bh))
        candidates.append((x, y, "right" if side == "left" else "left"))
    for side in vertical:
        y = cy - GAP - bh if side == "top" else cy + ch + GAP
        x = cx + cw - bw if mid_x > aw / 2 else cx
        x = max(0, min(x, aw - bw))
        candidates.append((x, y, "bottom" if side == "top" else "top"))
    for x, y, tail in candidates:
        if x < 0 or y < 0 or x + bw > aw or y + bh > ah:
            continue
        rect = (int(x), int(y), bw, bh)
        if overlaps(rect, character) or any(overlaps(rect, r) for r in avoid):
            continue
        at = int(mid_y - y) if tail in ("left", "right") else int(mid_x - x)
        return Bubble(int(x), int(y), bw, bh, tail, at)
    return None


def bubble_fallback(character: Rect, size: tuple[int, int], area: tuple[int, int]) -> Bubble:
    """When nothing fits (an area smaller than the character and the bubble side by side): beside him towards
    the middle, kept inside the area, over him if it must."""
    cx, cy, cw, ch = character
    bw, bh = size
    if cx + cw / 2 > area[0] / 2:
        x, tail = cx - GAP - bw, "right"
    else:
        x, tail = cx + cw + GAP, "left"
    x, y = clamp((x, cy + ch - bh), area, size)
    return Bubble(x, y, bw, bh, tail, int(cy + ch / 2 - y))


def free_corners(character: Rect, area: tuple[int, int], avoid: tuple[Rect, ...] | list, margins: tuple[int, int]
                 ) -> list[tuple[int, int]]:
    """The places of the character in the four corners of the area (its own distances from the edges), the
    farthest from what is to be avoided first; the corner it is in is left out."""
    cw, ch = character[2], character[3]
    dx, dy = margins
    corners = [(dx, dy), (area[0] - cw - dx, dy), (dx, area[1] - ch - dy), (area[0] - cw - dx, area[1] - ch - dy)]

    def distance(corner: tuple[int, int]) -> float:
        x, y = corner[0] + cw / 2, corner[1] + ch / 2
        return min((math.hypot(x - (r[0] + r[2] / 2), y - (r[1] + r[3] / 2)) for r in avoid), default=0.0)
    return sorted((c for c in corners if c != (character[0], character[1])), key=distance, reverse=True)


def questions(tab: str) -> list[str]:
    """Three questions ready for the phase open (study 14, 7.3), from phases.py; the economics' for a phase it
    does not know."""
    from .. import phases
    try:
        return list(phases.by_id(tab).questions)
    except KeyError:
        return list(phases.by_id("economics").questions)
