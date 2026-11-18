"""Measure a real CardDock and Card on one window floor, without nested panels."""
import argparse
import html
import json
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QUrl
from PySide6.QtGui import QColor, QPalette
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow

from meridiana.config import Config
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.capture import grab
from meridiana.ui.theme import Theme
from quick.controlli.capture_pairs import reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', choices=('light', 'dark'), required=True)
    args = parser.parse_args()
    app = QApplication([])
    native_theme = Theme(Config(theme=args.theme, font='plex', accent='indigo', backgrounds='grey'))
    engine = QQmlEngine()
    theme = install_controls(engine, dict(theme=args.theme, reducedMotion=True))
    component = QQmlComponent(engine)
    component.setData(b'''import QtQuick
import Meridiana.Controls as M
M.Card { x: 12; y: 12; width: 300; height: 160; title: "Proprieta"; closable: true
    M.Label { text: "Capannone Rho" }
}''', QUrl())
    card = component.create()
    assert card is not None, component.errors()
    quick = QQuickWindow()
    quick.setColor(QColor(theme.colors['window']))
    quick.resize(360, 210)
    card.setParentItem(quick.contentItem())
    native = QMainWindow()
    palette = native.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(native_theme.tokens['window']))
    native.setPalette(palette)
    native.setAutoFillBackground(True)
    native.resize(360, 210)
    dock, _ = reference('card', native_theme, native)
    dock.setWindowTitle('Proprieta')
    dock.setGeometry(QRect(12, 12, 300, 160))
    dock.show()
    out = Path('docs/quick/confronto/controlli/superfici')
    out.mkdir(exist_ok=True)
    images = {}
    for name, window in (('widgets', native), ('quick', quick)):
        window.show()
        assert QTest.qWaitForWindowExposed(window)
        QTest.mouseMove(window, QPoint(350, 200))
        QTest.qWait(80)
        image = window.grab().toImage() if name == 'widgets' else grab(window)
        ratio = image.devicePixelRatio()
        stem = f'{args.theme}-s{ratio:g}'
        image.save(str(out / f'{stem}-{name}.png'))
        images[name] = image
    samples = {}
    for label, x, y, token in (('left-floor', 4, 100, 'window'), ('bottom-floor', 100, 185, 'window'),
                               ('header-ground', 200, 24, 'panel'), ('body-ground', 200, 100, 'panel')):
        colours = {}
        for name, image in images.items():
            ratio = image.devicePixelRatio()
            colours[name] = sorted({image.pixelColor(px, py).name()
                                    for px in range(round(x * ratio), round((x + 4) * ratio))
                                    for py in range(round(y * ratio), round((y + 4) * ratio))})
            assert colours[name] == [theme.colors[token]], (label, name, colours[name], theme.colors[token])
        samples[label] = dict(position=[x, y], colours=colours)
    report = dict(theme=args.theme, scale=ratio, samples=samples,
                  graphics=str(quick.rendererInterface().graphicsApi()))
    (out / f'{stem}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    sections = []
    for path in sorted(out.glob('*-s*.json')):
        label = html.escape(path.stem)
        sections.append(f'<h2>{label}</h2><div>' + ''.join(
            f'<figure><figcaption>{name}</figcaption><img src="{label}-{name}.png" width="720" height="420"></figure>'
            for name in ('widgets', 'quick')) + '</div>')
    (out / 'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Un solo fondo</title>
<style>body{font:14px system-ui;background:#ccc}div{display:flex;gap:24px}figure{margin:0}img{image-rendering:pixelated}</style>
<h1>Una scheda su un solo fondo, confronto al 200 %</h1>''' + ''.join(sections), encoding='utf-8')
    print(json.dumps(report))
    quick.close()
    native.close()
    card.setParentItem(None)
    card.deleteLater()
    app.processEvents()


if __name__ == '__main__':
    main()
