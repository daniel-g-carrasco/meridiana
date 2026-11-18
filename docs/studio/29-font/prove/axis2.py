"""Step 3: what Qt does with the wdth axis. usage: axis2.py <fontdir> <outdir> [tag]"""
import sys, json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetricsF, QImage, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
app = QApplication(sys.argv)
root, out = Path(sys.argv[1]), Path(sys.argv[2]); tag = sys.argv[3] if len(sys.argv) > 3 else "win"
out.mkdir(exist_ok=True, parents=True)
def load(rel):
    fid = QFontDatabase.addApplicationFont(str(root / rel)); return QFontDatabase.applicationFontFamilies(fid)[0]
fam = {k: load(v) for k, v in dict(os="opensans/OpenSans[wdth,wght].ttf", rb="roboto/Roboto[wdth,wght].ttf", rc="robotocondensed/RobotoCondensed[wght].ttf",
       noto="notosans/NotoSans[wdth,wght].ttf", plex="ibmplexsans/IBMPlexSans[wdth,wght].ttf", arch="archivo/Archivo[wdth,wght].ttf").items()}
T = "Bilancio ed economia 5.489,56 Producibilità"
rows = []   # (caption, QFont)
def F(name, px=13, w=None, axes=None, stretch=None, style=None):
    f = QFont(fam[name]); f.setPixelSize(px)
    if w: f.setWeight(w)
    for k, v in (axes or {}).items(): f.setVariableAxis(QFont.Tag(k), v)
    if stretch: f.setStretch(stretch)
    if style: f.setStyleName(style)
    return f
for n in ("os", "noto", "rb", "plex", "arch"):
    rows.append((f"{n} wdth axis 100", F(n, axes={"wdth": 100})))
    rows.append((f"{n} wdth axis 87.5", F(n, axes={"wdth": 87.5})))
    rows.append((f"{n} wdth axis 75", F(n, axes={"wdth": 75})))
    rows.append((f"{n} setStretch(75)", F(n, stretch=75)))
rows.append(("Roboto Condensed family", F("rc")))
rows.append(("Roboto style 'Condensed Regular'", F("rb", style="Condensed Regular")))
rows.append(("Open Sans style 'Condensed Regular'", F("os", style="Condensed Regular")))
rows.append(("Open Sans wdth 75 + DemiBold", F("os", w=QFont.Weight.DemiBold, axes={"wdth": 75})))
rows.append(("Open Sans wdth 75, copy then setPixelSize(14)", (lambda f: (f.setPixelSize(14), f)[1])(QFont(F("os", axes={"wdth": 75})))))
meta = []
img = QImage(560, 24 * len(rows) + 10, QImage.Format.Format_ARGB32); img.fill(QColor("white"))
p = QPainter(img); p.setPen(QColor("black"))
y = 18
for cap, f in rows:
    p.setFont(f); p.drawText(5, y, T)
    w = QFontMetricsF(f).horizontalAdvance(T)
    ps = QFont(f); ps.setPixelSize(10); p.setFont(ps); p.drawText(330, y, f"{cap}: {w:.0f}px")
    meta.append((cap, round(w, 1))); y += 24
p.end(); img.save(str(out / f"axis-{tag}.png"))
print(json.dumps(meta, indent=0))
# QSS and QFont copies
w = QWidget(); l = QVBoxLayout(w); lab = QLabel(T); l.addWidget(lab)
lab.setFont(F("os", axes={"wdth": 75}))
before = lab.sizeHint().width()
lab.setStyleSheet("QLabel{color:#333}"); after_qss_color = lab.sizeHint().width()
lab.setStyleSheet("QLabel{font-weight:600}"); after_qss_weight = lab.sizeHint().width()
lab.setStyleSheet("QLabel{font-size:14px}"); after_qss_size = lab.sizeHint().width()
lab.setStyleSheet("QLabel{font-family:'Open Sans'}"); after_qss_family = lab.sizeHint().width()
lab.setStyleSheet("")
app.setFont(F("os", axes={"wdth": 75})); lab2 = QLabel(T); inherited = lab2.sizeHint().width()
print(json.dumps(dict(widget_font=before, qss_color=after_qss_color, qss_weight600=after_qss_weight, qss_size14=after_qss_size,
      qss_family=after_qss_family, label_inheriting_app_font=inherited, os_full=round(QFontMetricsF(F("os")).horizontalAdvance(T)),
      os_75=round(QFontMetricsF(F("os", axes={'wdth': 75})).horizontalAdvance(T)))))
