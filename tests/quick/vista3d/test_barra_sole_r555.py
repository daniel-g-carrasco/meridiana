"""R555 (Daniel 13/11/2026: «in una vista stretta il testo dell'altezza del sole va sotto il pulsante col sole»): the sun's
bar under the 3D view gives way without overlapping, at every width of the view from 220 to 700 px, at 100 % and 200 %,
in both themes. Measured on the bar as drawn: the controls shown stand one after the other without touching, the row
keeps the same air on the right as on the left, the sun's text is never painted wider than its slot, the icons stay in
their buttons, and the day's button (the one with a ground of its own) has as much bar above it as below it, read on
the pixels. Before (the hand-made widths): at 220 px the sun's button was gone, at 240 and 280 px it stood 20 and 28 px
past the bar's right end, and at 200 % the square buttons had 8 device px above them and 6 below."""
import json
from itertools import pairwise
import os
import subprocess
import sys
import unittest
from pathlib import Path

import _setup

SCALES = ('1', '2')
WIDTHS = tuple(range(220, 701, 20))
ROOT = Path(__file__).resolve().parents[3]
SUN_BAR = ROOT / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana' / 'View3D' / 'SunBar.qml'
NAMES = ('sunPlay', 'sunDay', 'sunHour', 'sunClock', 'sunPosition', 'sunDesign')


def measure():
    """Run in a process with QT_SCALE_FACTOR set: what the bar shows at each width, as JSON."""
    from PySide6.QtCore import Property, QObject, QPointF, QUrl, Signal, Slot
    from PySide6.QtGui import QColor
    from PySide6.QtQml import QQmlComponent
    from PySide6.QtQuick import QQuickItem, QQuickView
    from meridiana.gui.backend.controls import install_controls
    from quick.gestures import pump
    _setup.qt_or_skip()

    class Sun(QObject):
        sunChanged = Signal()

        @Property('QVariantMap', notify=sunChanged)
        def sunData(self):
            return {'year': 2026, 'month': 12, 'day': 21, 'hour': 12 + 1 / 3, 'clock': '12:20',
                    'short': 'h 21,1° · az -0,5°',
                    'description': 'At 12:20 (standard time) the sun is 21,1° above the horizon, azimuth -0,5°.'}

        @Slot(int, int, int, float)
        def setSun(self, *_):
            pass

        @Slot(bool)
        def playSun(self, _):
            pass

        @Slot()
        def stepSun(self):
            pass

        @Slot()
        def designSun(self):
            pass

        @Slot(int)
        def shiftSunDay(self, _):
            pass

    out = {}
    for theme in ('light', 'dark'):
        view = QQuickView()
        install_controls(view.engine(), dict(theme=theme, reducedMotion=True))
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        sun = Sun()
        component = QQmlComponent(view.engine(), QUrl.fromLocalFile(str(SUN_BAR)))
        bar = component.createWithInitialProperties({'backend': sun})
        assert bar is not None, component.errorString()
        view.setContent(QUrl(), component, bar)
        for width in WIDTHS:
            view.resize(width, round(bar.property('implicitHeight')))
            view.show()
            pump(120)
            image = view.grabWindow()
            dpr = image.width() / view.width()
            shown = []
            for name in NAMES:
                item = bar.findChild(QQuickItem, name)
                if not item.isVisible() or item.width() <= 0:
                    continue
                p = item.mapToScene(QPointF(0, 0))
                entry = {'name': name, 'x': p.x(), 'y': p.y(), 'w': item.width(), 'h': item.height()}
                if name == 'sunPosition':
                    entry['painted'] = item.property('paintedWidth')
                icons = [c for c in item.findChildren(QQuickItem) if c.metaObject().className().startswith('Icon')
                         and c.isVisible()]
                entry['ink'] = [[c.mapToScene(QPointF(0, 0)).x(), c.mapToScene(QPointF(0, 0)).y(), c.width(), c.height()]
                                for c in icons]
                shown.append(entry)
            # the day's ground, read down a column inside its rounded corners and before its text
            day = bar.findChild(QQuickItem, 'sunDay')
            x = int((day.mapToScene(QPointF(0, 0)).x() + 9) * dpr)
            ground = QColor(bar.property('color')).rgb()
            rows = [y for y in range(image.height()) if image.pixelColor(x, y).rgb() != ground]
            out[f'{theme} {width}'] = {'bar': [view.width(), view.height()], 'dpr': dpr, 'shown': shown,
                                       'day_ground': [rows[0], image.height() - 1 - rows[-1]] if rows else None}
        view.close()
    print(json.dumps(out))


def setUpModule():
    _setup.keep_global_state()


class TheSunBarGivesWay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = {}
        for scale in SCALES:
            env = dict(os.environ, QT_SCALE_FACTOR=scale, QT_QPA_PLATFORM='offscreen', QSG_RENDER_LOOP='basic')
            run = subprocess.run([sys.executable, __file__, '--measure'], env=env, capture_output=True, text=True,
                                 timeout=240, cwd=ROOT)
            line = [x for x in run.stdout.splitlines() if x.startswith('{')]
            assert line, run.stderr[-2000:]
            cls.found[scale] = json.loads(line[-1])

    def each(self):
        for scale, found in self.found.items():
            self.assertEqual(len(found), 2 * len(WIDTHS), scale)
            for where, seen in found.items():
                yield f'{scale}x {where}', seen

    def test_nothing_overlaps_and_the_sides_keep_the_same_air(self):
        for where, seen in self.each():
            shown, (width, _height), dpr = seen['shown'], seen['bar'], seen['dpr']
            names = [s['name'] for s in shown]
            self.assertIn('sunDesign', names, f'{where}: the sun\'s button stays')
            for a, b in pairwise(shown):
                self.assertLessEqual(a['x'] + a['w'], b['x'] + 0.01, f'{where}: {a["name"]} runs into {b["name"]}')
            left, right = shown[0]['x'], width - (shown[-1]['x'] + shown[-1]['w'])
            self.assertLessEqual(abs(left - right) * dpr, 1, f'{where}: {left} px of air on the left, {right} on the right')

    def test_what_is_drawn_stays_in_its_place_with_as_much_air_above_as_below(self):
        for where, seen in self.each():
            _width, height = seen['bar']
            dpr = seen['dpr']
            for s in seen['shown']:
                self.assertLessEqual(abs(s['y'] - (height - s['y'] - s['h'])) * dpr, 1,
                                     f'{where}: {s["name"]} at {s["y"]} from the top, {height - s["y"] - s["h"]} from the bottom')
                if 'painted' in s:
                    self.assertLessEqual(s['painted'], s['w'] + 0.5, f'{where}: the sun\'s text painted past its slot')
                for x, _y, w, _h in s['ink']:
                    self.assertGreaterEqual(x, s['x'] - 0.01, f'{where}: {s["name"]}\'s icon out on the left')
                    self.assertLessEqual(x + w, s['x'] + s['w'] + 0.01, f'{where}: {s["name"]}\'s icon out on the right')
            top, bottom = seen['day_ground']
            self.assertLessEqual(abs(top - bottom), 1, f'{where}: the day\'s button {top} device px from the top, {bottom} from the bottom')


if __name__ == '__main__':
    if '--measure' in sys.argv:
        measure()
    else:
        unittest.main()
