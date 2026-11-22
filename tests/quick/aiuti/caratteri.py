"""The one tolerance for a measure that depends on how a font is drawn: GLYPH_PX.

The tests of the interface were written on Windows, where DirectWrite lays out the text: the width of a word, the
height of a line, where the capitals stand. On Linux FreeType (with fontconfig's hinting) lays out the same font with
other advances and other line heights: a word a pixel wider or narrower, a line of 18.73 px where Windows gives 18.62,
capitals a pixel lower (22/11/2026, the WSL and the CI's runner). Neither is wrong; a test that asked the Windows
pixel there measured the rasteriser, not the program.

So, and only there, a measure that comes from the drawing of the text (where a text is centred or aligned, the width
it takes, the height of its lines) is allowed GLYPH_PX either way on a platform that is not Windows; on Windows it
stays exact, as written. What does not come from the font (a margin of a frame, the gap between two boxes, a size
set in pixels) stays exact everywhere: never use this for it."""
from __future__ import annotations

import sys

# ± pixels for a measure drawn by the font, outside Windows; 0 on Windows (the measures the tests were written on)
GLYPH_PX = 0.0 if sys.platform == 'win32' else 2.0


def glyph(tolerance: float = 0.0) -> float:
    """The tolerance for a measure that depends on the drawing of a font: the test's own on Windows, at least
    GLYPH_PX elsewhere."""
    return max(float(tolerance), GLYPH_PX)
