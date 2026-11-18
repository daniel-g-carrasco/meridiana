"""Images under the drawing (Daniel, 23/10/2026, R21: «importare immagini (con visualizzazione con trasparenze e
possibilità di metterlo in scala)»): a roof plan, a cadastral map, the first page of a PDF, laid on the plan with
its own transparency, put in scale with two points and the true distance typed, moved, turned, hidden. Saved in
the project, the image itself included, so that the file is whole on another PC. No Qt here: the window decodes
and draws the image, this module says where its pixels go.

A pixel (u, v) of the image, v downwards as in every image file, goes on the plan at

    (x, y) + R(rotation) · (u · scale, -v · scale)

with (x, y) the plan point of the image's top left corner, `scale` metres per pixel and `rotation` in degrees,
anticlockwise as the plan's angles."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .i18n import _

MAX_SIDE = 4096                 # pixels: a larger image is made smaller on import (the project carries it)
MIN_DISTANCE = 1e-6             # metres: two points closer than this give no scale


@dataclass
class Underlay:
    id: str
    name: str = ""                  # the file it came from, for the menu
    image: str = ""                 # the image file itself (PNG or JPEG), in base64
    width: int = 0                  # pixels of the image
    height: int = 0
    x: float = 0.0                  # the plan point of its top left corner, metres
    y: float = 0.0
    scale: float = 0.05             # metres per pixel
    rotation: float = 0.0           # degrees, anticlockwise
    opacity: float = 0.6            # 0 (not seen) to 1
    visible: bool = True

    def to_plan(self, u: float, v: float) -> tuple[float, float]:
        """Where a pixel of the image is on the plan."""
        c, s = math.cos(math.radians(self.rotation)), math.sin(math.radians(self.rotation))
        du, dv = u * self.scale, -v * self.scale
        return self.x + c * du - s * dv, self.y + s * du + c * dv

    def from_plan(self, x: float, y: float) -> tuple[float, float]:
        """The pixel of the image at a plan point."""
        c, s = math.cos(math.radians(self.rotation)), math.sin(math.radians(self.rotation))
        dx, dy = x - self.x, y - self.y
        du, dv = c * dx + s * dy, -s * dx + c * dy
        return du / self.scale, -dv / self.scale

    def corners(self) -> list[tuple[float, float]]:
        """The four corners on the plan, top left first, clockwise as the image is seen."""
        return [self.to_plan(u, v) for u, v in ((0, 0), (self.width, 0), (self.width, self.height),
                                                (0, self.height))]

    def centre(self) -> tuple[float, float]:
        return self.to_plan(self.width / 2, self.height / 2)

    # what the designer does with it: each gives a new underlay, the old one stays for the undo

    def scaled(self, a: tuple[float, float], b: tuple[float, float], distance: float) -> "Underlay":
        """In scale: `a` and `b` are two points of the image as it lies on the plan now, `distance` how far apart
        they truly are (metres). The image grows or shrinks about `a`, which stays where it is."""
        now = math.dist(a, b)
        if now < MIN_DISTANCE or not distance > 0:
            raise ValueError(_("two distinct points and a distance above zero are needed"))
        k = distance / now
        return replace(self, scale=self.scale * k, x=a[0] + (self.x - a[0]) * k, y=a[1] + (self.y - a[1]) * k)

    def moved(self, dx: float, dy: float) -> "Underlay":
        return replace(self, x=self.x + dx, y=self.y + dy)

    def rotated(self, degrees: float, about: tuple[float, float] | None = None) -> "Underlay":
        """Turned by `degrees` (anticlockwise) about a plan point, its centre when none is given."""
        px, py = about if about is not None else self.centre()
        c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
        dx, dy = self.x - px, self.y - py
        return replace(self, x=px + c * dx - s * dy, y=py + s * dx + c * dy,
                       rotation=(self.rotation + degrees) % 360.0)


def placed(uid: str, name: str, image: str, width: int, height: int, centre: tuple[float, float],
           across: float) -> Underlay:
    """A new underlay `across` metres wide, centred on a plan point (the middle of the view): in scale later, with
    two points."""
    scale = across / max(width, 1)
    return Underlay(id=uid, name=name, image=image, width=width, height=height,
                    x=centre[0] - width * scale / 2, y=centre[1] + height * scale / 2, scale=scale)


def fitted_size(width: int, height: int, limit: int = MAX_SIDE) -> tuple[int, int]:
    """The size an image is kept at in the project: as it is, or with its longer side at `limit`."""
    k = min(1.0, limit / max(width, height, 1))
    return max(1, round(width * k)), max(1, round(height * k))
