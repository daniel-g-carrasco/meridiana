"""Side by side photos of the two windows: Widgets on the left, Quick on the right, the same step.

    python tests/quick/confronto/componi.py <photo dir> <out dir> [--width 1800]

Pairs: <name>-widgets.png with <name>-quick.png (the giro), <journey>-widgets-<name>.png with
<journey>-quick-<name>.png (the modelling journeys). A Widgets dialog is a window of its own
(<step>-widgets-dialogo.png): it is drawn over the corner of the Widgets photo, as the screen would show it.
Written as JPEG, the two halves scaled to the same width, with a title band.
"""
import os
from pathlib import Path
import re
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter  # noqa: E402


def pairs(folder):
    found = {}
    for path in Path(folder).glob('*.png'):
        name = path.stem
        m = re.fullmatch(r'(.+)-(widgets|quick)', name)
        if m:
            found.setdefault(m.group(1), {})[m.group(2)] = path
            continue
        m = re.fullmatch(r'(.+?)-(widgets|quick)-(.+)', name)
        if m and m.group(3) != 'dialogo':
            found.setdefault(f'{m.group(1)}-{m.group(3)}', {})[m.group(2)] = path
    return {k: v for k, v in found.items() if 'widgets' in v and 'quick' in v}


def compose(left_path, right_path, target, width=1800, dialog=None):
    half = width//2
    left, right = QImage(str(left_path)), QImage(str(right_path))
    if dialog is not None and Path(dialog).exists():
        box = QImage(str(dialog))
        painter = QPainter(left)
        scale = min(1.0, left.width()*0.7/box.width(), left.height()*0.8/box.height())
        w, h = int(box.width()*scale), int(box.height()*scale)
        x, y = (left.width()-w)//2, (left.height()-h)//2
        painter.fillRect(QRect(x-3, y-3, w+6, h+6), QColor('#c2306f'))
        painter.drawImage(QRect(x, y, w, h), box)
        painter.end()
    left = left.scaledToWidth(half, Qt.TransformationMode.SmoothTransformation)
    right = right.scaledToWidth(half, Qt.TransformationMode.SmoothTransformation)
    band = 34
    out = QImage(width, band+max(left.height(), right.height()), QImage.Format.Format_RGB32)
    out.fill(QColor('#ffffff'))
    painter = QPainter(out)
    font = QFont('IBM Plex Sans')
    font.setPixelSize(18)
    painter.setFont(font)
    painter.setPen(QColor('#202020'))
    painter.drawText(QRect(8, 0, half-16, band), Qt.AlignmentFlag.AlignVCenter, 'Vecchia (Widgets)')
    painter.drawText(QRect(half+8, 0, half-16, band), Qt.AlignmentFlag.AlignVCenter, 'Nuova (Quick)')
    painter.drawImage(0, band, left)
    painter.drawImage(half, band, right)
    painter.fillRect(QRect(half-1, 0, 2, out.height()), QColor('#888888'))
    painter.end()
    out.save(str(target), 'JPG', 82)


def main(folder, out, width=1800):
    app = QGuiApplication.instance() or QGuiApplication([])
    from PySide6.QtGui import QFontDatabase
    for font in sorted((Path(__file__).resolve().parents[3]/'data'/'fonts'/'ibm-plex').rglob('*.[ot]tf'))[:4]:
        QFontDatabase.addApplicationFont(str(font))      # offscreen has no system fonts: the titles need one
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for name, two in sorted(pairs(folder).items()):
        # the photo «<step>-aperto» is the one taken with the dialog open: the Widgets dialog goes on it
        dialog = Path(folder)/f'{name[:-len("-aperto")]}-widgets-dialogo.png' if name.endswith('-aperto') else None
        target = out/f'{name}.jpg'
        compose(two['widgets'], two['quick'], target, width, dialog if dialog is not None and dialog.exists() else None)
        done.append(target.name)
    print(len(done), 'foto composte in', out)
    del app
    return done


if __name__ == '__main__':
    args = sys.argv[1:]
    width = 1800
    if '--width' in args:
        i = args.index('--width')
        width = int(args[i+1])
        del args[i:i+2]
    main(args[0], args[1], width)
