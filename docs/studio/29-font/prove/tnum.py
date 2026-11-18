import sys
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv); root = Path(sys.argv[1])
for p in sorted((root / "inter-static").glob("Inter-*.ttf")): fam = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(p)))[0]
f = QFont(fam); f.setPixelSize(13)
m = QFontMetricsF(f); print("default 1,111 vs 0,000:", m.horizontalAdvance("1,111"), m.horizontalAdvance("0,000"))
g = QFont(f); g.setFeature(QFont.Tag("tnum"), 1); m = QFontMetricsF(g); print("tnum    1,111 vs 0,000:", m.horizontalAdvance("1,111"), m.horizontalAdvance("0,000"))
