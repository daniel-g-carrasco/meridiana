"""The camera of the 3D view, without Qt (study 15, 2.6 B; study 12a, 2.4-2.5): the orbit as a turntable (the
vertical stays vertical, the default for buildings) or an arcball, around the point under the cursor with the
ground plane as the fallback; the zoom towards the cursor; the pan that keeps the point under the cursor; a short
middle click that recentres; the standard views; and the animation from one camera to another (250 ms with an
ease-out, none when the system asks for less motion).

Coordinates are Qt Quick 3D's (mesh.to_qt): x East, y up, z South. The camera looks along its own -z with its
+y up; `rotation` is the quaternion (w, x, y, z) from the camera's axes to the scene's, as QML's
PerspectiveCamera.rotation takes it. The view binds position and rotation; Python never sets a QML property."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

ANIMATION_MS = 250
DEGREES_PER_PIXEL = 0.35
ZOOM_STEP = 0.8                 # each wheel step brings the camera this much closer to the point (FreeCAD: 0.2)
MIN_DISTANCE = 0.5
ELEVATION_LIMIT = 89.0          # the turntable never goes over the top: the vertical stays vertical
CLIP = 20000.0                  # the parallel camera draws what lies within this distance before and behind it


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def qmul(a, b) -> np.ndarray:
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def axis_angle(axis, degrees: float) -> np.ndarray:
    a = _unit(axis)
    h = math.radians(degrees) / 2
    return np.array([math.cos(h), *(a * math.sin(h))])


def rotate(q, v) -> np.ndarray:
    p = np.array([0.0, *v])
    qc = np.array([q[0], -q[1], -q[2], -q[3]])
    return qmul(qmul(q, p), qc)[1:]


def slerp(a, b, t: float) -> np.ndarray:
    a, b = _unit(a), _unit(b)
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        return _unit(a + t * (b - a))
    theta = math.acos(d)
    return (math.sin((1 - t) * theta) * a + math.sin(t * theta) * b) / math.sin(theta)


def ease(t: float) -> float:
    """Ease-out (cubic), as the animations of study 12a, 2.5."""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def look(bearing: float, elevation: float) -> np.ndarray:
    """The rotation of a camera that looks towards `bearing` (degrees from North, clockwise) and `elevation`
    degrees above the horizon (negative: down)."""
    return qmul(axis_angle((0, 1, 0), -bearing), axis_angle((1, 0, 0), elevation))


# the standard views: where the camera looks from (study 12a, 2.10: Top, N, E, S, W rather than front and back)
VIEWS = {"top": (0.0, -90.0), "south": (0.0, 0.0), "north": (180.0, 0.0), "east": (270.0, 0.0), "west": (90.0, 0.0),
         "home": (30.0, -35.0)}


@dataclass
class Camera:
    position: np.ndarray = field(default_factory=lambda: np.array([0.0, 50.0, 80.0]))
    rotation: np.ndarray = field(default_factory=lambda: look(*VIEWS["home"]))
    target: np.ndarray = field(default_factory=lambda: np.zeros(3))      # the centre of the orbit by default
    fov: float = 60.0               # vertical, degrees (Qt's default)
    ortho: bool = False

    def copy(self) -> "Camera":
        return replace(self, position=self.position.copy(), rotation=self.rotation.copy(), target=self.target.copy())

    # the camera's axes in the scene

    def forward(self) -> np.ndarray:
        return rotate(self.rotation, (0.0, 0.0, -1.0))

    def right(self) -> np.ndarray:
        return rotate(self.rotation, (1.0, 0.0, 0.0))

    def up(self) -> np.ndarray:
        return rotate(self.rotation, (0.0, 1.0, 0.0))

    def bearing(self) -> float:
        """Where the camera looks, degrees from North clockwise. Straight down it is where the top of the view
        points (straight up, the bottom), as look() makes it: the direction itself has nothing left of it on the
        ground, and its rounding errors turned the plan of the cube's Top and its arrows (review, 23/10/2026)."""
        f = self.forward()
        if math.hypot(f[0], f[2]) < 1e-6:
            f = self.up() if f[1] < 0 else -self.up()
        return math.degrees(math.atan2(f[0], -f[2])) % 360.0

    def elevation(self) -> float:
        return math.degrees(math.asin(max(-1.0, min(1.0, self.forward()[1]))))

    def half_height(self) -> float:
        """The parallel view's metres from the middle of the view to its top edge: what the perspective view shows
        at the depth of the target. The view's magnification (pixels per metre) is h / (2 * half_height)."""
        d = max(MIN_DISTANCE, float(np.dot(self.target - self.position, self.forward())))
        return d * math.tan(math.radians(self.fov) / 2)

    # pixels and rays

    def ray(self, px: float, py: float, w: float, h: float) -> tuple[np.ndarray, np.ndarray]:
        """The ray from the camera through the pixel (px, py) of a w x h view. In the parallel view every ray
        has the camera's direction and starts on its plane, beside it: they all went out of the camera's point,
        and what was drawn 20 m from the middle was looked for 31 px away (review, 23/10/2026)."""
        x, y = 2 * px / w - 1, 1 - 2 * py / h
        if self.ortho:
            half = self.half_height()
            return self.position + self.right() * (x * half * w / h) + self.up() * (y * half), self.forward()
        t = math.tan(math.radians(self.fov) / 2)
        return self.position.copy(), _unit(rotate(self.rotation, (x * t * (w / h), y * t, -1.0)))

    def project(self, point, w: float, h: float) -> tuple[float, float] | None:
        """The pixel where a point of the scene is drawn; None where it is not drawn: behind the camera, or in the
        parallel view farther than CLIP before or behind it (that view draws what is behind its plane too)."""
        v = np.asarray(point, dtype=float) - self.position
        z = float(np.dot(v, self.forward()))
        if self.ortho:
            if abs(z) > CLIP:
                return None
            half = self.half_height()
            x, y = float(np.dot(v, self.right())) / (half * w / h), float(np.dot(v, self.up())) / half
            return (x + 1) * w / 2, (1 - y) * h / 2
        if z <= 1e-9:
            return None
        t = math.tan(math.radians(self.fov) / 2)
        x = float(np.dot(v, self.right())) / (z * t * (w / h))
        y = float(np.dot(v, self.up())) / (z * t)
        return (x + 1) * w / 2, (1 - y) * h / 2

    def ground(self, px: float, py: float, w: float, h: float) -> np.ndarray | None:
        """Where the ray through a pixel meets the ground (y = 0), in front of the camera; None if it does not."""
        o, d = self.ray(px, py, w, h)
        if abs(d[1]) < 1e-9:
            return None
        s = -o[1] / d[1]
        return o + s * d if s > 0 else None

    def pivot(self, px: float, py: float, w: float, h: float, hit=None) -> np.ndarray:
        """The centre of an orbit started at (px, py): the point of the model under the cursor, else the ground
        under it, else the target (FreeCAD's «Drag at cursor», with 12a's fallback)."""
        if hit is not None:
            return np.asarray(hit, dtype=float)
        g = self.ground(px, py, w, h)
        return g if g is not None else self.target.copy()

    def keep_in_view(self, point, w: float, h: float) -> np.ndarray:
        """`point` while it is drawn within the view; else the middle of the view at the same depth along the
        sight (Autodesk's «Safe 3D Navigation»: a pivot that left the screen is centred on the canvas, keeping its
        depth, so that the orbit does not swing away like a zoom). A point behind the camera, or farther than the
        camera draws, takes the depth of the target."""
        p = np.asarray(point, dtype=float)
        seen = self.project(p, w, h)
        if seen is not None and 0.0 <= seen[0] <= w and 0.0 <= seen[1] <= h:
            return p
        depth = float(np.dot(p - self.position, self.forward()))
        if not MIN_DISTANCE <= depth <= CLIP:
            depth = max(MIN_DISTANCE, float(np.dot(self.target - self.position, self.forward())))
        return self.position + self.forward() * depth

    def pixel_size(self, point, h: float) -> float:
        """The metres one pixel of a view `h` pixels high covers at `point`: what a mark that must stay the same
        size on the screen is scaled by. In the parallel view it is the same everywhere."""
        if self.ortho:
            return 2 * self.half_height() / max(h, 1.0)
        depth = max(MIN_DISTANCE, float(np.dot(np.asarray(point, dtype=float) - self.position, self.forward())))
        return 2 * depth * math.tan(math.radians(self.fov) / 2) / max(h, 1.0)

    # moves

    def orbit(self, dx: float, dy: float, pivot, mode: str = "turntable") -> None:
        """Dragging right turns the model to the right, dragging down shows it more from above. The turntable keeps
        the vertical vertical; the arcball turns about the axis across the drag."""
        p = np.asarray(pivot, dtype=float)
        if mode == "arcball":
            axis = _unit(self.up() * dx + self.right() * dy)
            if np.linalg.norm(axis) > 0:
                self._turn(axis_angle(axis, -math.hypot(dx, dy) * DEGREES_PER_PIXEL), p)
            return
        self._turn(axis_angle((0, 1, 0), -dx * DEGREES_PER_PIXEL), p)
        elev = self.elevation()
        new = max(-ELEVATION_LIMIT, min(ELEVATION_LIMIT, elev - dy * DEGREES_PER_PIXEL))
        right = self.right()
        right[1] = 0.0                                  # about a horizontal axis: no roll creeps in
        if np.linalg.norm(right) > 1e-9:
            self._turn(axis_angle(right, new - elev), p)

    def _turn(self, q, p) -> None:
        self.position = p + rotate(q, self.position - p)
        self.target = p + rotate(q, self.target - p)
        self.rotation = _unit(qmul(q, self.rotation))

    def pan(self, dx: float, dy: float, w: float, h: float, depth_point=None) -> None:
        """The view follows the pointer: the point at the depth of `depth_point` (the target if not given) stays
        under it."""
        p = self.target if depth_point is None else np.asarray(depth_point, dtype=float)
        depth = max(MIN_DISTANCE, float(np.dot(p - self.position, self.forward())))
        # metres per pixel: at that depth in perspective, the same at every depth in the parallel view
        s = 2 * (self.half_height() if self.ortho else math.tan(math.radians(self.fov) / 2) * depth) / h
        move = -self.right() * dx * s + self.up() * dy * s
        self.position = self.position + move
        self.target = self.target + move

    def zoom(self, steps: float, point) -> None:
        """Closer to `point` (the point under the cursor) by ZOOM_STEP per step, along the ray through it: the point
        stays where it is on the screen. Negative steps go away."""
        p = np.asarray(point, dtype=float)
        f = ZOOM_STEP ** steps
        if np.linalg.norm(self.position - p) * f < MIN_DISTANCE:
            f = MIN_DISTANCE / max(np.linalg.norm(self.position - p), 1e-9)
        self.position = p + (self.position - p) * f
        self.target = p + (self.target - p) * f

    def zoom_point(self, px: float, py: float, w: float, h: float, hit=None) -> np.ndarray:
        """What the wheel zooms towards: the model under the cursor, the ground, or the plane of the target."""
        if hit is not None:
            return np.asarray(hit, dtype=float)
        g = self.ground(px, py, w, h)
        o, d = self.ray(px, py, w, h)
        depth = float(np.dot(self.target - o, self.forward()))
        plane = o + d * (depth / max(float(np.dot(d, self.forward())), 1e-6))
        if g is not None and np.linalg.norm(g - o) < 20 * max(np.linalg.norm(self.target - o), 1.0):
            return g
        return plane

    def recentre(self, point) -> None:
        """A short middle click: the point to the middle of the view, at the same distance; it becomes the target."""
        p = np.asarray(point, dtype=float)
        d = float(np.linalg.norm(p - self.position))
        self.position = p - self.forward() * d
        self.target = p

    def fit(self, centre, radius: float, aspect: float) -> None:
        """The whole sphere around the scene inside the narrower of the two angles of view."""
        c = np.asarray(centre, dtype=float)
        v = math.radians(self.fov)
        hfov = 2 * math.atan(math.tan(v / 2) * aspect)
        d = radius / math.sin(min(v, hfov) / 2)
        self.position = c - self.forward() * d
        self.target = c

    def view(self, name: str, centre, radius: float, aspect: float) -> None:
        """A standard view (VIEWS): Top, from South, East, North, West, or Home."""
        bearing, elevation = VIEWS[name]
        self.rotation = look(bearing, elevation)
        self.fit(centre, radius, aspect)


def between(a: Camera, b: Camera, t: float) -> Camera:
    """The camera at `t` (0 to 1, eased) of the way from `a` to `b`: positions along a line, rotations by slerp."""
    e = ease(t)
    return replace(a, position=a.position + (b.position - a.position) * e, rotation=slerp(a.rotation, b.rotation, e),
                   target=a.target + (b.target - a.target) * e, ortho=b.ortho if t >= 1 else a.ortho)


def axonometric(points, bearing: float, elevation: float, aspect: float, margin: float = 0.06) -> Camera:
    """A parallel camera looking towards `bearing` at `elevation` (look()) that holds all of `points` (Qt axes) in a
    view `aspect` wide for each unit of height, `margin` of the view's width and height left free on every side: the
    3D pictures of the report. Its target is the middle of what it holds, at the distance at which the perspective
    camera shows the same, so that the parallel view's scale is h / (2 * half_height()) as in the window."""
    cam = Camera(rotation=look(bearing, elevation), ortho=True)
    pts = np.asarray(points, dtype=float).reshape(-1, 3)
    if not len(pts):
        pts = np.zeros((1, 3))
    r, u, f = cam.right(), cam.up(), cam.forward()
    x, y, z = pts @ r, pts @ u, pts @ f
    room = 1 - 2 * margin
    half = max((y.max() - y.min()) / 2 / room, (x.max() - x.min()) / 2 / room / aspect, 0.5)
    centre = r * (x.max() + x.min()) / 2 + u * (y.max() + y.min()) / 2 + f * (z.max() + z.min()) / 2
    d = max(MIN_DISTANCE, half / math.tan(math.radians(cam.fov) / 2))
    cam.target = centre
    cam.position = centre - f * d
    return cam
