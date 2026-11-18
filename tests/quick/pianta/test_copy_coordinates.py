"""R487: the plan's right click copies the coordinates of the point under it, on nothing or on an object, with any
tool: latitude and longitude (the window's language and the pair maps and GIS read), UTM with zone and EPSG, the
project's metres. Each text read back gives the point clicked within a centimetre."""
import math
import re
import unittest

import _setup
from PySide6.QtGui import QGuiApplication

from meridiana import coordinates, geo, i18n, model
from meridiana.quick.backend.plan import PlanController

setUpModule = _setup.keep_global_state

COMMANDS = ['copy_degrees', 'copy_decimal', 'copy_utm', 'copy_local']


class CopyCoordinates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        i18n.setup('it')
        p = model.Project(name='Coordinates')
        p.site.lat, p.site.lon = 45.52261, 9.03004
        p.buildings.append(model.Building(id='b1', name='Roof', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        self.p = p
        self.c = PlanController(p, manage_layout=False)
        self.addCleanup(self.c.close)
        self.origin = geo.Origin(p.site.lat, p.site.lon)
        self.notices = []
        self.c.notice.connect(self.notices.append)

    def copied(self, command):
        QGuiApplication.clipboard().setText('')
        self.c.contextCommand(command)
        return QGuiApplication.clipboard().text()

    def back(self, command, text):
        """The point a copied text stands for, in the project's metres."""
        if command in ('copy_degrees', 'copy_decimal'):
            reading = coordinates.read_coordinates(text)        # as «Find the site» reads it
            return self.origin.to_local(reading.lon, reading.lat)
        if command == 'copy_utm':
            m = re.fullmatch(r'UTM WGS84 (\d+)([NS]) ([\d.]+) ([\d.]+) \(EPSG:(\d+)\)', text)
            self.assertIsNotNone(m, text)
            zone, hemisphere, east, north, epsg = m.groups()
            self.assertEqual(int(epsg), (32700 if hemisphere == 'S' else 32600) + int(zone))
            lat, lon = geo.from_utm(int(zone), float(east), float(north), hemisphere == 'S')
            return self.origin.to_local(lon, lat)
        m = re.fullmatch(r'E (-?[\d.]*\d,\d+) m, N (-?[\d.]*\d,\d+) m', text)
        self.assertIsNotNone(m, text)
        return tuple(float(v.replace('.', '').replace(',', '.')) for v in m.groups())

    def test_every_form_comes_back_to_the_point_within_a_centimetre(self):
        for point in ((12.3456, 7.891), (-250.25, 1830.5), (2400.0, -1999.99), (0.0, 0.0)):
            self.c.contextAt(*point)
            items = [r for r in self.c.contextItems if not r['separator']]
            self.assertEqual([r['command'] for r in items][-4:], COMMANDS, point)
            for command in COMMANDS:
                with self.subTest(point=point, command=command):
                    text = self.copied(command)
                    self.assertTrue(text, command)
                    self.assertIn(text, next(r['text'] for r in items if r['command'] == command))
                    x, y = self.back(command, text)
                    self.assertLess(math.hypot(x - point[0], y - point[1]), 0.01, text)
                    self.assertEqual(self.notices[-1], 'Negli appunti: ' + text)

    def test_texts_on_an_object_on_nothing_and_with_a_drawing_tool(self):
        self.c.contextAt(10, 10)
        self.assertEqual(self.c.editor.selection, ('building', 'b1'))
        texts = {r['command']: r['text'] for r in self.c.contextItems}
        self.assertTrue(texts['copy_degrees'].startswith('Copia latitudine e longitudine: 45,52'), texts)
        self.assertRegex(texts['copy_degrees'], r'° N, 9,03\d+° E$')
        self.assertRegex(texts['copy_decimal'], r': 45\.52\d{5}, 9\.03\d{5}$')
        self.assertIn('UTM WGS84 32N', texts['copy_utm'])
        self.assertIn('(EPSG:32632)', texts['copy_utm'])
        self.assertEqual(texts['copy_local'], 'Copia le coordinate locali: E 10,000 m, N 10,000 m')
        self.c.contextAt(300, -40)                     # nothing there
        self.assertEqual(self.c.editor.selection[0], 'site')
        self.assertIn('copy_local', [r['command'] for r in self.c.contextItems])
        self.c.setTool('building')
        self.c.contextAt(5, 6)                         # a drawing tool: the point is still the one clicked
        self.assertEqual(self.copied('copy_local'), 'E 5,000 m, N 6,000 m')


if __name__ == '__main__':
    unittest.main()
