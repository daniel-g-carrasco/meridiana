"""Font study, step 4: Meridiana's real window offscreen with a candidate font, loaded without touching the source.
usage (from the repository root, env of the tests, QT_QPA_PLATFORM=offscreen:configfile=...):
  python photo.py <variant> <scale 1|2> <light|dark> <outdir> <locale>
variants: inter, intertight, plex, plexcond (Plex Sans with its Condensed in the narrow places), fira, firacond, noto,
          notowdth, jball (JetBrains Mono everywhere), jbnum (JetBrains Mono for numbers and fields, Inter elsewhere),
          inter-tnum, inter-ls (Inter, spacing -0.2 px), adwaita
Writes <outdir>/<variant>-<scale>x-<theme>-{window,bar,panel}.png and prints what it did as JSON."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\Grasso\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\fontscripts")))
import fontset  # noqa: E402

variant, scale, themename, outdir, locale = sys.argv[1], int(sys.argv[2]), sys.argv[3], Path(sys.argv[4]), sys.argv[5]
DL = fontset.DL

# variant -> (folder, files for FONT_FILES, weights, family-of-the-narrow-places folder or None)
SETS = {
    "inter": ("inter-static", ["Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]),
    "inter-tnum": ("inter-static", ["Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]),
    "inter-ls": ("inter-static", ["Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]),
    "intertight": ("intertight", ["InterTight[wght].ttf"]),
    "adwaita": ("adwaita-sans", ["AdwaitaSans-Regular.ttf"]),
    "plex": ("ibmplexsans", ["IBMPlexSans[wdth,wght].ttf"]),
    "plexcond": ("ibmplexsans", ["IBMPlexSans[wdth,wght].ttf"]),
    "fira": ("firasans", ["FiraSans-Regular.ttf", "FiraSans-SemiBold.ttf"]),
    "firacond": ("firasans", ["FiraSans-Regular.ttf", "FiraSans-SemiBold.ttf"]),
    "noto": ("notosans", ["NotoSans[wdth,wght].ttf"]),
    "notowdth": ("notosans", ["NotoSans[wdth,wght].ttf"]),
    "jball": ("jetbrains-static", ["JetBrainsMono-Regular.ttf", "JetBrainsMono-SemiBold.ttf"]),
    "intercond": ("inter-static", ["Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]),
    "intertight-narrow": ("inter-static", ["Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]),
    "jbnum": ("inter-static", ["Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]),
}
folder, files = SETS[variant]
# the program's own loader reads theme.FONT_DIR / FONT_FILES through paths.shipped: pointed at the candidate's folder
import _setup  # noqa: E402,I001
from meridiana import config, i18n, paths  # noqa: E402
from meridiana.ui import theme  # noqa: E402

i18n._locale_dirs = lambda: [Path(locale)]
i18n.setup("it")
real_shipped = paths.shipped
_orig = real_shipped


def shipped(*parts):
    if parts[:2] == ("fonts", "candidate"):
        return DL / folder
    return _orig(*parts)


paths.shipped = shipped
theme.FONT_DIR = "candidate"
theme.FONT_FILES = tuple(files)
theme.FONT_WEIGHTS = {n: w for n, w in zip(files, (400, 600, 700), strict=False)}

from _fixtures import capannone  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QComboBox, QDockWidget, QLabel,  # noqa: E402
                               QLineEdit, QTabBar, QToolBar, QToolButton)

W, H = 1500, 960


class Case(unittest.TestCase):
    def runTest(self):
        pass


case = Case()
cfg = config.Config(background="none", network_pvgis=False, accent="indigo", language="it", theme=themename)
win = _setup.window(case, capannone(), cfg=cfg, size=(W, H))
app = _setup.qt_or_skip()
_setup.wait_settled(app, lambda: win.size().toTuple())
log = {"variant": variant, "scale": scale, "theme": themename, "family": theme.load_fonts(), "app_font": app.font().family()}


def fam_of(rel):
    fid = QFontDatabase.addApplicationFont(str(DL / rel))
    return QFontDatabase.applicationFontFamilies(fid)[0]


def set_family(widget, family, axes=None, features=(), spacing=None, style=None):
    f = QFont(widget.font())
    f.setFamily(family)
    if style:
        f.setStyleName(style)
    # a variable font: weight and width as axes (Qt on Linux drops the width when the weight is set with setWeight)
    for tag, v in (axes or {}).items():
        f.setVariableAxis(QFont.Tag(tag), v)
    for tag in features:
        f.setFeature(QFont.Tag(tag), 1)
    if spacing is not None:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    widget.setFont(f)


def all_widgets():
    return app.allWidgets()


def apply():
    if variant == "inter-tnum":
        f = QFont(app.font())
        f.setFeature(QFont.Tag("tnum"), 1)
        app.setFont(f)
        for w in all_widgets():
            g = QFont(w.font())
            g.setFeature(QFont.Tag("tnum"), 1)
            w.setFont(g)
    elif variant == "inter-ls":
        for w in all_widgets():
            g = QFont(w.font())
            g.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.2)
            w.setFont(g)
    elif variant in ("plexcond", "firacond", "notowdth", "intercond", "intertight-narrow"):
        # the narrow places only: the bars' buttons, the tab row, the docks' titles
        if variant == "intertight-narrow":
            cond = fam_of("intertight/InterTight[wght].ttf")
        if variant in ("plexcond", "intercond"):
            cond = fam_of("ibmplexsanscondensed/IBMPlexSansCondensed-Regular.ttf")
            fam_of("ibmplexsanscondensed/IBMPlexSansCondensed-SemiBold.ttf")
        elif variant == "firacond":
            cond = fam_of("firasanscondensed/FiraSansCondensed-Regular.ttf")
            fam_of("firasanscondensed/FiraSansCondensed-SemiBold.ttf")
        n = 0
        for w in all_widgets():
            if (isinstance(w, QToolButton) and w.parent() is not None and w.text()) or isinstance(w, QTabBar) \
                    or w.metaObject().className() == "QDockWidgetTitle"                     or (isinstance(w, QLabel) and w.window() is win and any(d.objectName() == "properties" and d.isAncestorOf(w) for d in win.findChildren(QDockWidget))):
                if variant == "intertight-narrow":
                    set_family(w, cond, axes={"wght": 600 if w.font().weight() >= 600 else 400})
                elif variant == "notowdth":
                    # Noto's own width axis: the weight too as an axis, as the recipe that works on both platforms
                    weight = 600 if w.font().weight() >= 600 else 400
                    set_family(w, theme.load_fonts(), axes={"wdth": 75, "wght": weight})
                else:
                    set_family(w, cond)
                n += 1
        log["condensed_widgets"] = n
    elif variant == "jball":
        log["note"] = "JetBrains Mono as the application font by the program's own loader"
    elif variant == "jbnum":
        mono = fam_of("jetbrains-static/JetBrainsMono-Regular.ttf")
        fam_of("jetbrains-static/JetBrainsMono-SemiBold.ttf")
        n = 0
        num = re.compile(r"^[\d\s.,%°²/+\u2212\-]*\d[\d\s.,%°²/+\u2212\-]*(\s?[A-Za-z\u03a9/²]{1,6})?$")
        for w in all_widgets():
            if isinstance(w, (QAbstractSpinBox, QLineEdit, QComboBox, QAbstractItemView)) or \
                    (isinstance(w, QLabel) and num.match(w.text() or "")):
                set_family(w, mono)
                n += 1
        log["mono_widgets"] = n



pid = "plant"
i = win.tabs.index_of_phase(pid)
win.tabs.setCurrentIndex(i)
_setup.wait_settled(app, lambda: (win.size().toTuple(), win.centralWidget().size().toTuple()))
_setup.turn_events(app, 400)
win._select("subfield", win.project.subfields[0].id)
_setup.turn_events(app, 300)
from PySide6.QtWidgets import QAbstractButton
props = [d for d in win.findChildren(QDockWidget) if d.objectName() == "properties"][0]
opened = []
for b in props.findChildren(QAbstractButton):
    if b.isVisible() and b.text().strip() in ("Pannelli", "Inverter", "Accumulo") and b.isCheckable() and not b.isChecked():
        b.click()
        opened.append(b.text())
    elif b.isVisible() and b.text().strip() in ("Pannelli", "Inverter", "Accumulo"):
        opened.append(("seen", type(b).__name__, b.isCheckable(), b.isChecked()))
_setup.turn_events(app, 400)
apply()
_setup.turn_events(app, 400)
apply()
_setup.turn_events(app, 300)
docks = {d.objectName() or d.windowTitle(): d for d in win.findChildren(QDockWidget) if d.isVisible()}
log["opened"] = opened
log["docks"] = {k: d.geometry().getRect() for k, d in docks.items()}
# the narrow panel: the biggest right-hand dock to 276 px, as the study asks
target = None
target = docks.get("properties")
if target is not None:
    win.resizeDocks([target], [276], Qt.Orientation.Horizontal)
    _setup.turn_events(app, 400)
    log["panel_rect"] = target.geometry().getRect()
if variant in ("jbnum",):
    # widgets made later (the dock's pages) also: again
    pass
outdir.mkdir(parents=True, exist_ok=True)
tag = f"{variant}-{scale}x-{themename}"
img = win.grab()
img.save(str(outdir / f"{tag}-window.png"))
bars = [b for b in win.findChildren(QToolBar) if b.isVisible() and b.width() > 200]
if bars:
    b = bars[0]
    top = b.mapTo(win, b.rect().topLeft())
    win.grab(b.rect().translated(top)).save(str(outdir / f"{tag}-bar.png")) if False else \
        img.copy(int(top.x() * scale), int(top.y() * scale), int(b.width() * scale), int(b.height() * scale)).save(str(outdir / f"{tag}-bar.png"))
    log["bar_rect"] = [top.x(), top.y(), b.width(), b.height()]
if target is not None:
    t = target.mapTo(win, target.rect().topLeft())
    img.copy(int(t.x() * scale), int(t.y() * scale), int(target.width() * scale), int(target.height() * scale)).save(
        str(outdir / f"{tag}-panel.png"))
print("RESULT " + json.dumps(log, ensure_ascii=False))
case.doCleanups()
