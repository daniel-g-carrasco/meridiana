"""Meridiana: photovoltaic design (map, buildings and roofs, module layout, energy, checks, report).

The package is split so that everything that computes (geometry, sun, roofs, layout, the energy models, the
checks and the rules) is plain Python without Qt, covered by the tests in tests/; the window (ui/, with Qt 6
and Qt Quick 3D) only displays and collects the gestures. The constants below are the one place the app's
identity lives: the code derives every name (the executable, the installer, the text domain, the environment
variables) from them.
"""

import sys
from pathlib import Path

__version__ = "0.2.1"

WINDOWS = sys.platform == "win32"

APP_ID = "io.github.daniel_g_carrasco.meridiana"
APP_NAME = "Meridiana"
SLUG = "meridiana"                 # the repository, the binary on Linux, the file names of a release
EXE_NAME = "Meridiana"              # the Windows executable and its folder (no spaces, as Setup likes it)
TEXTDOMAIN = SLUG
ENV_PREFIX = "MERIDIANA"           # the developer aids: MERIDIANA_SCREENSHOT and the like
GITHUB_REPO = "daniel-g-carrasco/meridiana"
WEBSITE = f"https://github.com/{GITHUB_REPO}"

# the two anchors of the paths (study 43, risk R3): the folder of the package and, in a checkout, the repository
# (src/ is between them). A module finds a file by them, never by counting its own folders up from __file__: the
# count breaks when the module moves to another layer.
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent.parent
