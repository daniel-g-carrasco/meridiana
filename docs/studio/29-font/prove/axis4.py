import sys
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv); root = Path(sys.argv[1])
T = "Bilancio ed economia 5.489,56 Producibilità"
for d in ("firasanscondensed", "ibmplexsanscondensed", "barlowsemicondensed", "inter-static"):
    fams = set()
    for p in sorted((root / d).glob("*.ttf")):
        fams.add(QDatabase := QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(p)))[0])
    fam = fams.pop(); out = {}
    for name, wt in (("400", QFont.Weight.Normal), ("600", QFont.Weight.DemiBold)):
        f = QFont(fam); f.setPixelSize(13); f.setWeight(wt); out[name] = (round(QFontMetricsF(f).horizontalAdvance(T), 1), f.exactMatch())
    print(d, fam, out)
