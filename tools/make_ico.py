#!/usr/bin/env python3
"""build-aux/windows/<slug>.ico from the app icon's SVG: one PNG per size, for the title bars, Explorer, the taskbar
and the installer. The title bar draws 16 pixels at 100% and 20 at 125%, and shrinks what it is given without a
filter: every size the system draws must be in the file. An icon with thin lines needs a version redrawn for the
small sizes (SMALL_SVG, as Spola has); a tile with thick shapes reads at 16 pixels as it is.

Qt draws the SVG (QSvgRenderer, from the PySide6 the program already needs; Pillow reads no SVG and GdkPixbuf is
not in a Qt venv), offscreen: no window, no screen.

    python tools/make_ico.py [OUT.ico]
"""

import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from meridiana import APP_ID, SLUG  # noqa: E402

SVG = ROOT / "data" / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg"
SMALL_SVG = ROOT / "build-aux" / "windows" / f"{SLUG}-small.svg"     # optional: drawn for 16-24 pixels
SMALL = (16, 20, 24)
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
# The SVG keeps the icon theme's margin, which on Linux sits well beside the other apps' icons. Windows shrinks the
# icon to 16-24 pixels in the taskbar, where a margin is only a smaller icon (Scriba, 13/11/2026: 22 pixels drawn
# against Chrome's 24): for the .ico the 512 master is drawn with the view closed on the family's canvas, 512/480
# times larger around its centre, as Quotario does. The drawing for 16-24 pixels (SMALL_SVG, on the 16 grid) already
# fills its grid and is taken as it is.
FULL_VIEW = ('viewBox="0 0 512 512"', 'viewBox="16 16 480 480"')

_app = None


def render_png(svg: Path, size: int, full_view: bool = False) -> bytes:
    """The SVG drawn on a transparent square of `size` pixels, as PNG bytes; `full_view`: as Windows shows it, the
    view closed on the canvas (FULL_VIEW), only for the 512 master."""
    global _app
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    if QGuiApplication.instance() is None:
        _app = QGuiApplication([sys.argv[0]])
    text = Path(svg).read_text(encoding="utf-8")
    if full_view and FULL_VIEW[0] in text:
        renderer = QSvgRenderer(QByteArray(text.replace(*FULL_VIEW).encode("utf-8")))
    else:
        renderer = QSvgRenderer(str(svg))
    if not renderer.isValid():
        raise ValueError(f"{svg}: not an SVG Qt can draw")
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def ico(images: list[tuple[int, bytes]]) -> bytes:
    """An .ico holding each (size, PNG) as it is (Windows Vista and later read PNG entries)."""
    offset = 6 + 16 * len(images)
    entries, payload = b"", b""
    for size, png in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset + len(payload))
        payload += png
    return struct.pack("<HHH", 0, 1, len(images)) + entries + payload


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build-aux" / "windows" / f"{SLUG}.ico"
    images = [(size, render_png(SMALL_SVG if size in SMALL and SMALL_SVG.is_file() else SVG, size, full_view=True))
              for size in SIZES]
    out.write_bytes(ico(images))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
