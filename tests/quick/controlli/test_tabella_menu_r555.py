"""R555, measured on the drawn image in device pixels at 100 and 200 %, in both themes.

Tables (Daniel 14/11/2026, Settings > Shortcuts: «agli angoli arrotondati manca il contorno, i due in alto
(l'intestazione ci dipinge sopra) e quello in basso a sinistra (le righe ci dipingono sopra)»): a framed M.Table, with
its last row chosen and scrolled to its end, shows its outline on the arc of each of its four corners (the pixel of the
diagonal nearest the line's colour is at least half way to it), and the square corner outside the arc keeps the ground
around the table. Before: the two at the top not drawn at all (the shortcuts' heading over them).

Menus (Daniel, the Sub-field's menu: «il margine destro dopo la scorciatoia deve essere uguale al sinistro prima del
simbolo»; «il suggerimento della voce si apre sopra il menu e ne copre il bordo»): from the hover's grey to the first ink
(the icon) and from the last ink (the key) to the grey, the same within one device pixel; the tooltip of an entry
does not cover the menu's frame; the menu keeps its width under the pointer (R491) and the entry under it has the
hover's grey (R525). Before: 5 px at the left, 28 at the right; the tooltip over the frame."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _setup

QML = b'''
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 640; height: 420; color: Theme.colors.window
    M.Table { objectName: "table"; x: 20; y: 20; width: 300; height: 180; framed: true; rowHeight: Theme.size.COMPACT
        columns: [{key: "a", title: "Comando", weight: 2}, {key: "b", title: "Tasti", weight: 1}]
        model: Array.from({length: 30}, (_, i) => ({a: "Comando " + i, b: "Ctrl+" + i}))
        currentIndex: 29 }
    M.Button { id: opener; objectName: "opener"; x: 360; y: 20; text: "Menu"
        M.Menu { id: menu; objectName: "menu"; y: opener.height
            M.MenuItem { objectName: "first"; text: "Sottocampo"; iconName: "subfield"; shortcutText: "S"
                tip: "Disegna il sottocampo: i moduli lo riempiono mentre lo disegni" }
            M.MenuItem { objectName: "second"; text: "Fila di moduli"; iconName: "row"; shortcutText: "L" }
            M.MenuItem { objectName: "third"; text: "Su pensilina"; iconName: "carport" } } }
}
'''
SCALES = ('1', '2')
ROOT = Path(__file__).resolve().parents[3]


def dist(a, b):
    return ((a.red() - b.red()) ** 2 + (a.green() - b.green()) ** 2 + (a.blue() - b.blue()) ** 2) ** 0.5


def corners(image, dpr, item, radius):
    """Per corner: how near the arc's best pixel comes to the line's colour (1 = the line), and whether the square
    corner outside it keeps the ground outside."""
    from PySide6.QtCore import QPointF
    p = item.mapToScene(QPointF(0, 0))
    x0, y0 = round(p.x() * dpr), round(p.y() * dpr)
    x1, y1 = round((p.x() + item.width()) * dpr) - 1, round((p.y() + item.height()) * dpr) - 1
    line = image.pixelColor(x0, (y0 + y1) // 2)
    r = radius * dpr
    out = {}
    for name, (cx, cy, sx, sy) in {'top-left': (x0, y0, 1, 1), 'top-right': (x1, y0, -1, 1),
                                   'bottom-left': (x0, y1, 1, -1), 'bottom-right': (x1, y1, -1, -1)}.items():
        outside = image.pixelColor(cx - sx * 2, cy - sy * 2)
        inside = image.pixelColor(cx + sx * int(r + 2 * dpr), cy + sy * int(r + 2 * dpr))
        span = max(dist(outside, line), dist(inside, line), 1)
        arc = max(1 - dist(image.pixelColor(cx + sx * k, cy + sy * k), line) / span for k in range(int(r) + 1))
        out[name] = [round(arc, 2), dist(image.pixelColor(cx, cy), outside) < 0.25 * span]
    return out


def margins(image, dpr, entry):
    """Device pixels from the entry's grey to its first ink and from its last ink to the grey."""
    from PySide6.QtCore import QPointF
    p = entry.mapToScene(QPointF(0, 0))
    x0, x1 = round(p.x() * dpr), round((p.x() + entry.width()) * dpr)
    rows = range(round((p.y() + entry.height() * .2) * dpr), round((p.y() + entry.height() * .8) * dpr))
    ground = image.pixelColor(x0 + 1, round((p.y() + entry.height() / 2) * dpr))
    ink = [x for x in range(x0, x1) if any(dist(image.pixelColor(x, y), ground) > 60 for y in rows)]
    return ink[0] - x0, x1 - 1 - ink[-1], ground.name()


def walk(item):
    pending = [item]
    while pending:
        node = pending.pop()
        yield node
        pending.extend(node.childItems())


def measure():
    """Run in a process with QT_SCALE_FACTOR set: the corners, the margins and the tooltip, as JSON."""
    from PySide6.QtCore import QMetaObject, QObject, QPointF, QUrl
    from PySide6.QtQuick import QQuickItem, QQuickView
    from PySide6.QtTest import QTest
    from meridiana.gui.backend.controls import install_controls
    from quick.gestures import pump
    _setup.qt_or_skip()
    file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
    file.write(QML)
    file.close()
    out = {}
    for theme in ('light', 'dark'):
        view = QQuickView()
        install_controls(view.engine(), dict(theme=theme, reducedMotion=True))
        view.setSource(QUrl.fromLocalFile(file.name))
        view.show()
        pump(300)
        root = view.rootObject()
        table = root.findChild(QQuickItem, 'table')
        rows = next(o for o in walk(table) if o.objectName() == 'tableView')
        rows.setProperty('contentY', rows.property('contentHeight') - rows.height())
        pump(300)
        image = view.grabWindow()
        dpr = image.width() / view.width()
        found = {'corners': corners(image, dpr, table, 6)}
        menu = root.findChild(QObject, 'menu')
        QMetaObject.invokeMethod(menu, 'open')
        pump(500)
        first = next(o for o in walk(view.contentItem()) if o.objectName() == 'first')
        width = menu.property('width')
        image = view.grabWindow()
        found['margins'] = margins(image, dpr, first)
        at = first.mapToScene(QPointF(first.width() * .4, first.height() / 2))
        QTest.mouseMove(view, QPointF(5, 400).toPoint())      # from elsewhere: the second view starts where the first left
        pump(100)
        QTest.mouseMove(view, at.toPoint())
        pump(1400)
        image = view.grabWindow()
        left, right, grey = margins(image, dpr, first)
        found['hovered'] = [left, right, grey]
        found['width'] = [width, menu.property('width')]
        popup_item = first.parentItem().parentItem().parentItem()      # entry > list's content > list > popup
        frame = max((c for c in popup_item.childItems() if c is not first.parentItem().parentItem()),
                    key=lambda c: c.width() * c.height())
        f = frame.mapToScene(QPointF(0, 0))
        found['frame'] = [f.x(), f.y(), frame.width(), frame.height()]
        overlay = popup_item.parentItem()
        tips = [c for c in overlay.childItems() if c is not popup_item and c.isVisible() and c.opacity() > 0]
        found['tips'] = [[t.mapToScene(QPointF(0, 0)).x(), t.mapToScene(QPointF(0, 0)).y(), t.width(), t.height()]
                         for t in tips]
        out[theme] = found
        view.close()
    print(json.dumps(out))
    os.unlink(file.name)


def setUpModule():
    _setup.keep_global_state()


class TablesAndMenus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = {}
        for scale in SCALES:
            env = dict(os.environ, QT_SCALE_FACTOR=scale, QT_QPA_PLATFORM='offscreen', QSG_RENDER_LOOP='basic')
            run = subprocess.run([sys.executable, __file__, '--measure'], env=env, capture_output=True, text=True,
                                 timeout=180, cwd=ROOT)
            line = [x for x in run.stdout.splitlines() if x.startswith('{')]
            assert line, run.stderr[-3000:]
            cls.found[scale] = json.loads(line[-1])

    def each(self):
        for scale, themes in self.found.items():
            for theme, found in themes.items():
                yield f'x{scale} {theme}', found

    def test_the_table_shows_its_outline_at_all_four_corners(self):
        for where, found in self.each():
            for corner, (arc, outside) in found['corners'].items():
                self.assertGreaterEqual(arc, 0.5, f'{where} {corner}: the outline is not drawn on the arc ({arc})')
                self.assertTrue(outside, f'{where} {corner}: the table shows past its round corner')

    def test_an_entry_has_the_same_margin_at_both_sides(self):
        for where, found in self.each():
            for name in ('margins', 'hovered'):
                left, right = found[name][:2]
                self.assertLessEqual(abs(left - right), 1, f'{where} {name}: {left} px before the icon, {right} after the key')

    def test_the_menu_keeps_its_width_and_greys_the_entry_under_the_pointer(self):
        for where, found in self.each():
            self.assertEqual(found['width'][0], found['width'][1], where)
            self.assertNotEqual(found['hovered'][2], found['margins'][2], f'{where}: no hover grey')

    def test_the_tooltip_of_an_entry_does_not_cover_the_menu(self):
        for where, found in self.each():
            self.assertTrue(found['tips'], f'{where}: no tooltip shown')
            fx, fy, fw, fh = found['frame']
            for x, y, w, h in found['tips']:
                apart = x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy
                self.assertTrue(apart, f'{where}: the tooltip {x, y, w, h} covers the menu {fx, fy, fw, fh}')


if __name__ == '__main__':
    if '--measure' in sys.argv:
        measure()
    else:
        unittest.main()
