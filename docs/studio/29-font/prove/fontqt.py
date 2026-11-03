"""Qt side of the font study: loads the candidates' files and makes QFonts. Needs a QGuiApplication."""
from PySide6.QtGui import QFont, QFontDatabase

import fontset

_FAM: dict = {}      # candidate -> {file basename: family}


def load(cid: str, dl=None) -> dict:
    c = fontset.CANDIDATES[cid]
    if "base" in c:
        return load(c["base"], dl)
    if cid in _FAM:
        return _FAM[cid]
    root = dl or fontset.DL
    res = {}
    for rel in c["files"]:
        fid = QFontDatabase.addApplicationFont(str(root / rel))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        res[rel] = fams[0] if fams else None
    _FAM[cid] = res
    return res


def make(cid: str, weight: int = 400, px: float = 13, dl=None, hinting=None) -> QFont:
    """The candidate at `weight` (400 or 600) and `px`."""
    c = fontset.CANDIDATES[cid]
    fam = next(iter(load(cid, dl).values()))
    f = QFont(fam)
    f.setPixelSize(int(round(px)))
    f.setWeight(QFont.Weight.DemiBold if weight >= 600 else QFont.Weight.Normal)
    if c.get("style"):
        f.setStyleName(c["style"])
    for tag, v in c.get("axes", {}).items():
        f.setVariableAxis(QFont.Tag(tag), v)
    for tag in c.get("features", []):
        f.setFeature(QFont.Tag(tag), 1)
    if "ls" in c:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, c["ls"])
    if hinting is not None:
        f.setHintingPreference(hinting)
    return f
