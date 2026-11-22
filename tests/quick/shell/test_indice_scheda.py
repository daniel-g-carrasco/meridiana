"""The report's contents, a card of the workbench as the others (Daniel 21/11/2026: «come mai in Relazione l'Indice
non è una scheda come tutte le altre?»): in the left column in Report, with its title and its cross, the common tree
inside; the page's own card is not shown; closed with the cross it stays closed (R696); not there in the other
phases. With it the Alt menu bar of the kit (dc3d9bd), on the same window."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QPointF, Qt
from PySide6.QtTest import QTest

from _fixtures import capannone
from meridiana.app.platform import config
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import item, pump, wait_for


class ContentsCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.host = QuickWindow(capannone(), Path(self.temp.name), real_views=True)   # the parts, the report's among them
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        self.win.resize(1600, 960)
        pump(200)
        self.report = self.host.engine.rootContext().contextProperty('reportBackend')

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        self.app.processEvents()
        self.temp.cleanup()
        self.assertEqual(warnings, [])

    def phase(self, name):
        QMetaObject.invokeMethod(self.win, 'showPhase', Q_ARG('QVariant', name))
        pump(900)

    def test_a_card_of_the_left_column_in_report_only(self):
        card = item(self.win, 'contentsPanel')
        self.assertFalse(card.isVisible())
        self.phase('report')
        wait_for(card.isVisible, 5)
        self.assertEqual(card.property('zone'), 'left')
        self.assertEqual(card.property('title'), self.report.labels['contents'])
        self.assertFalse(item(self.win, 'reportOutlinePanel').isVisible())   # the page's own card
        # nothing yet: the kit's empty state
        self.assertTrue(item(self.win, 'reportOutlineEmpty').isVisible())
        self.report._outline = [dict(title='Overview', level=1, page=2), dict(title='Site', level=2, page=3),
                                dict(title='Production', level=1, page=5)]
        self.report.pagesChanged.emit()
        pump(200)
        tree = item(self.win, 'reportOutline')
        self.assertEqual(tree.property('count'), 3)
        self.assertFalse(item(self.win, 'reportOutlineEmpty').isVisible())
        asked = []
        self.report.pageAsked.connect(asked.append)
        at = tree.mapToScene(QPointF(60, tree.property('rowHeight') * 2.5)).toPoint()
        QTest.mouseClick(self.win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at)
        self.assertEqual(asked, [5])
        self.assertEqual(tree.property('currentIndex'), 2)
        # closed as a card is closed: it stays closed, also in the settings (R696)
        card.closed.emit()
        pump(300)
        self.assertFalse(card.isVisible())
        self.assertFalse(self.report.outlineOpen)
        path = self.host.paths.config_file
        wait_for(lambda: path.exists() and not config.load(path).report_outline_open, 5)
        self.phase('model')
        self.assertFalse(card.isVisible())
        self.assertTrue(item(self.win, 'leftPanel').isVisible())


    def test_alt_menu_bar_lays_the_page_out_once(self):
        """The kit (dc3d9bd): the Alt bar takes its room in one step and comes by its opacity, so the workspace under
        it is laid out once when it opens and once when it closes, never at every frame (before: 8 times)."""
        workspace, bar = item(self.win, 'workspace'), item(self.win, 'altMenuBar')
        heights = []
        workspace.heightChanged.connect(lambda: heights.append(workspace.height()))
        self.win.setProperty('menuOpen', True)
        pump(1000)
        self.assertEqual(bar.opacity(), 1)
        self.assertLessEqual(len(heights), 1, f'the page laid out at every frame of the opening: {heights}')
        heights.clear()
        self.win.setProperty('menuOpen', False)
        pump(1000)
        self.assertFalse(bar.isVisible())
        self.assertLessEqual(len(heights), 1, f'the page laid out at every frame of the closing: {heights}')


if __name__ == '__main__':
    unittest.main()
