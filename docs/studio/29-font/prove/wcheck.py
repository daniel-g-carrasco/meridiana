import sys
from PySide6.QtGui import QGuiApplication, QFont, QFontMetricsF
app = QGuiApplication(sys.argv)
import fontset, fontqt
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
T = "Bilancio ed economia Producibilità"
for cid, rel in (("intertight","intertight/InterTight[wght].ttf"),("noto","notosans/NotoSans[wdth,wght].ttf")):
    fontqt.load(cid)
    for w in (400, 500, 600, 700):
        f = fontqt.make(cid, 400, 13, hinting=QFont.HintingPreference.PreferNoHinting)
        f.setWeight(QFont.Weight(w))
        q = QFontMetricsF(f).horizontalAdvance(T)
        tt = TTFont(str(fontset.DL/rel))
        axes = {"wght": w}
        if "wdth" in [a.axisTag for a in tt["fvar"].axes]: axes["wdth"] = 100
        inst = instantiateVariableFont(tt, axes)
        cmap = inst.getBestCmap(); hm = inst["hmtx"]; upem = inst["head"].unitsPerEm
        ft = sum(hm[cmap[ord(ch)]][0] for ch in T) * 13 / upem
        print(cid, w, "qt", round(q,1), "fonttools", round(ft,1))
