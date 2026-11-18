"""Font study, step 2: widths of real Meridiana texts at 13 px with Qt, x-height, digits, coverage.
usage: python -I measure.py <out.json>   (QT_QPA_PLATFORM=offscreen; Windows, Qt default hinting = what the program has)"""
import json
import sys
from collections import Counter

from fontTools.ttLib import TTFont
from PySide6.QtGui import QFont, QFontMetricsF, QGuiApplication

import fontqt
import fontset

app = QGuiApplication(sys.argv)
corpus = fontset.corpus()
used = Counter(ch for t in corpus for ch in t if ord(ch) > 127)
used.update(ch for i, s in fontset.parse_po() for ch in s if ord(ch) > 127)
SPECIAL = "°²·«»−≥∥⊥…±×≈γΩ⇧⋯"
res = {"corpus_n": len(corpus), "non_ascii_chars": {c: n for c, n in used.most_common()}, "fonts": {}}


def total(f, texts):
    m = QFontMetricsF(f)
    return sum(m.horizontalAdvance(t) for t in texts)


for cid, c in fontset.CANDIDATES.items():
    base = c.get("base", cid)
    f4 = fontqt.make(cid, 400)
    f6 = fontqt.make(cid, 600)
    m = QFontMetricsF(f4)
    r = {"label": c["label"], "family": f4.family(), "groups": {}, "groups600": {}}
    for g, texts in fontset.GROUPS.items():
        r["groups"][g] = round(total(f4, texts), 2)
        r["groups600"][g] = round(total(f6, texts), 2)
    r["corpus"] = round(total(f4, corpus), 2)
    fn = fontqt.make(cid, 400, hinting=QFont.HintingPreference.PreferNoHinting)
    r["corpus_nohint"] = round(total(fn, corpus), 2)
    r["height"] = m.height()
    r["ascent"] = m.ascent()
    r["descent"] = m.descent()
    r["xheight_qt"] = m.xHeight()
    r["capheight_qt"] = m.capHeight()
    digs = [m.horizontalAdvance(d) for d in "0123456789"]
    r["digits"] = digs
    r["digits_tabular"] = len(set(digs)) == 1
    r["digits_1_vs_0"] = round(digs[1] / digs[0], 3)
    r["fraction_text_width"] = round(m.horizontalAdvance("1.111.111,11"), 2), round(m.horizontalAdvance("0.000.000,00"), 2)
    r["missing_special"] = [ch for ch in SPECIAL if not m.inFontUcs4(ord(ch))]
    r["missing_used"] = [ch for ch in used if not m.inFontUcs4(ord(ch))]
    fpath = fontset.DL / next(iter(fontset.CANDIDATES[base]["files"]))
    r["size_kb"] = [round((fontset.DL / x).stat().st_size / 1024) for x in fontset.CANDIDATES[base]["files"]]
    tt = TTFont(str(fpath), lazy=True)
    os2 = tt["OS/2"]
    upem = tt["head"].unitsPerEm
    r["xheight_em"] = round(getattr(os2, "sxHeight", 0) / upem, 3)
    r["capheight_em"] = round(getattr(os2, "sCapHeight", 0) / upem, 3)
    feats = {fr.FeatureTag for fr in tt["GSUB"].table.FeatureList.FeatureRecord} if "GSUB" in tt else set()
    r["gsub_tnum"] = "tnum" in feats
    r["axes"] = {a.axisTag: [a.minValue, a.defaultValue, a.maxValue] for a in tt["fvar"].axes} if "fvar" in tt else {}
    r["glyphs"] = tt["maxp"].numGlyphs
    names = tt["name"]
    r["name_version"] = (names.getDebugName(5) or "")[:40]
    res["fonts"][cid] = r
    tt.close()
json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("done", len(res["fonts"]), "fonts; corpus", len(corpus), "texts")
