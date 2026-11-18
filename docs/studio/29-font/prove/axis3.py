import sys, json
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
root = Path(sys.argv[1])
T = "Bilancio ed economia 5.489,56 Producibilità"
def run(rel, wdth, wght=600):
    fid = QFontDatabase.addApplicationFont(str(root / rel)); fam = QFontDatabase.applicationFontFamilies(fid)[0]
    def w(f): return round(QFontMetricsF(f).horizontalAdvance(T), 1)
    def mk(weight=None, axes=None, order="weight_first"):
        f = QFont(fam); f.setPixelSize(13)
        if order == "axes_first":
            for k, v in (axes or {}).items(): f.setVariableAxis(QFont.Tag(k), v)
            if weight: f.setWeight(weight)
        else:
            if weight: f.setWeight(weight)
            for k, v in (axes or {}).items(): f.setVariableAxis(QFont.Tag(k), v)
        return f
    return fam, dict(
        regular=w(mk()), wdth_only=w(mk(axes={"wdth": wdth})),
        semibold_only=w(mk(weight=QFont.Weight.DemiBold)),
        semibold_then_wdth=w(mk(QFont.Weight.DemiBold, {"wdth": wdth})),
        wdth_then_semibold=w(mk(QFont.Weight.DemiBold, {"wdth": wdth}, "axes_first")),
        both_axes_only=w(mk(axes={"wdth": wdth, "wght": wght})),
        both_axes_and_weight=w(mk(QFont.Weight.DemiBold, {"wdth": wdth, "wght": wght})),
        bold_then_wdth=w(mk(QFont.Weight.Bold, {"wdth": wdth})))
for rel, wd in (("opensans/OpenSans[wdth,wght].ttf", 75), ("roboto/Roboto[wdth,wght].ttf", 75), ("notosans/NotoSans[wdth,wght].ttf", 75), ("archivo/Archivo[wdth,wght].ttf", 75)):
    fam, r = run(rel, wd); print(fam, r)
