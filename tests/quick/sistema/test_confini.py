"""R406: the bounds check catches what it was written for, and the whole window passes it.

The first class proves the check on small windows of its own, so that a green matrix means something. The second walks
the real window, offscreen (the layouts are the same, a glyph may differ by a pixel); with MERIDIANA_CONFINI=tutto the
whole matrix of quick/confini.py, about ten minutes."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.tokens import install_theme
from quick import confini
from quick.gestures import pump
from quick.parity.differential import connected_fixture

setUpModule = _setup.keep_global_state

# Offscreen, Qt Quick's threaded render loop dies with an access violation while a job imports pvlib or fits a module
# (8 runs out of 8; 0 out of 8 with the basic loop; real windows not seen to: docs/quick/r14-impianto-esito.md).
if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

ROOM = """
import QtQuick
import QtQuick.Controls as C
import Meridiana.Controls as M
import Meridiana.Theme
C.ApplicationWindow {
    width: 800; height: 600; visible: true
    footer: Item { height: 40; Text { objectName: "statusHint"; text: "stato" } }
    %s
}
"""


class TheCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())      # the next module's language is its own
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def window(self, body):
        engine = QQmlApplicationEngine()
        self.addCleanup(engine.deleteLater)
        install_theme(engine, {'theme': 'light'})
        install_controls(engine)
        path = Path(self.folder.name)/f'room{id(body)}.qml'
        path.write_text(ROOM % body, encoding='utf-8')
        engine.load(QUrl.fromLocalFile(str(path)))
        self.assertTrue(engine.rootObjects(), 'the room does not load')
        window = engine.rootObjects()[0]
        self.addCleanup(window.close)
        pump(120)
        return window

    def kinds(self, body):
        return {f.kind for f in confini.audit(self.window(body), strict=True)}

    def test_r406_a_text_on_the_status_bar(self):
        self.assertIn('barra-di-stato', self.kinds(
            'M.Card { width: 300; height: 200; Text { y: 560; text: "sotto la scheda" } }'))

    def test_a_text_out_of_its_card(self):
        self.assertIn('fuori-contenitore', self.kinds('M.Card { width: 300; height: 100; Text { y: 300; text: "fuori" } }'))

    def test_a_text_out_of_the_window(self):
        self.assertIn('fuori-finestra', self.kinds('Item { x: 780; Text { text: "oltre il bordo della finestra" } }'))

    def test_a_text_larger_than_its_box(self):
        self.assertIn('sforato', self.kinds('Text { width: 20; text: "molto più largo della sua casella" }'))

    def test_an_elided_text_is_not_one(self):
        self.assertNotIn('sforato', self.kinds('Text { width: 20; elide: Text.ElideRight; text: "molto più largo della sua casella" }'))

    def test_a_text_cut_with_nothing_to_scroll(self):
        self.assertIn('tagliato', self.kinds('Item { width: 40; height: 40; clip: true; Text { text: "tagliato dal contenitore" } }'))

    def test_a_list_that_scrolls_is_cut_as_it_should(self):
        kinds = self.kinds('M.ScrollPage { width: 300; height: 100; Text { text: "a\\nb\\nc\\nd\\ne\\nf\\ng\\nh\\ni\\nj" } }')
        self.assertFalse(kinds & {'tagliato', 'senza-barra', 'senza-sfumature'}, kinds)

    def test_a_list_without_bar_or_soft_ends(self):
        kinds = self.kinds('Flickable { width: 300; height: 100; contentHeight: 500; clip: true; Text { text: "riga" } }')
        self.assertIn('senza-barra', kinds)
        self.assertIn('senza-sfumature', kinds)

    def test_two_texts_over_each_other(self):
        self.assertIn('sovrapposto', self.kinds('Item { Text { text: "uno sopra" } Text { text: "uno sotto" } }'))

    def test_an_icon_button_out_of_its_proportions(self):
        self.assertIn('deformato', self.kinds('M.Button { width: 12; height: 40; iconName: "panel-left" }'))

    def test_a_field_with_no_room_for_its_value(self):
        self.assertIn('deformato', self.kinds('M.ComboBox { width: 30; model: ["uno"] }'))

    def test_a_card_larger_than_the_window(self):
        self.assertIn('scheda-grande', self.kinds('M.Card { width: 900; height: 200; title: "grande" }'))


class TheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())      # the next module's language is its own
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        pump(800)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def test_r406_every_state_stays_in_its_bounds(self):
        whole = os.environ.get('MERIDIANA_CONFINI') == 'tutto'
        report = confini.run(self.host, sizes=((1600, 960), (1000, 640), (800, 560)) if whole else ((1000, 640),),
                             themes=('light', 'dark') if whole else ('light',),
                             texts=('medium', 'large') if whole else ('large',),
                             panels=('default', 'narrow', 'wide') if whole else ('narrow',))
        count = report.pop('_count')
        self.assertGreater(count, 30)
        lines = [f'{n} × {k[0]} «{k[2]}» in {k[1]}, first in {first}' for k, n, first in confini.summary(report)]
        self.assertEqual(lines, [], '\n'.join(lines))


if __name__ == '__main__':
    unittest.main()
