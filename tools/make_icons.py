#!/usr/bin/env python3
"""The PNG sizes of the app icon, from the scalable one in data/icons/hicolor/scalable/apps (drawn by Qt, as
make_ico.py does):

  data/icons/hicolor/<N>x<N>/apps/<APP_ID>.png   for N in 64, 128, 256
  site/icon.png                                   the 256 one, for the site and the Flatpak page

    python tools/make_icons.py

The scalable SVG is the master: edit it, run this, commit both.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_ico import ROOT, SVG, render_png  # noqa: E402

from meridiana import APP_ID  # noqa: E402  (make_ico put src/ on the path)

SIZES = (64, 128, 256)


def main() -> int:
    for size in SIZES:
        png = render_png(SVG, size)
        out = ROOT / "data" / "icons" / "hicolor" / f"{size}x{size}" / "apps" / f"{APP_ID}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(png)
        print(out.relative_to(ROOT))
        if size == 256 and (ROOT / "site").is_dir():
            (ROOT / "site" / "icon.png").write_bytes(png)
            print("site/icon.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
