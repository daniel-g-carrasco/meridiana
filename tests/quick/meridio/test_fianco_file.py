"""Meridio's place over File and the Settings (Daniel 15/11/2026: «spostalo, tienilo sul fianco libero, va bene che se
agganciato al pannello diventa flottante, ma tornando indietro nel progetto ritorna nel pannello»).

Over File he stood where he was in the project, over a page's words. Now: while File is open he is on the free side of
the page, right of its column, the same rule for every page of File and of the Settings; closing File gives him back
his place in the project, and docked he is the panels' tab again; the «–» only hides him.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, QPointF, QRectF, Qt

from _fixtures import capannone
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import click, drag, point, pump, wait_for
from quick.meridio.support import KeyStore, Voice
from quick.aiuti.avvisi import real


def find(window, name):
    """An item by name from the window's own root: Meridio's stage is in Qt's overlay, beside the content."""
    top = window.contentItem()
    while top.parentItem() is not None:
        top = top.parentItem()
    pending = [top]
    while pending:
        node = pending.pop()
        if node.objectName() == name:
            return node
        pending.extend(node.childItems())
    raise AssertionError('Missing Quick item: ' + name)


def scene(item):
    p = item.mapToScene(QPointF(0, 0))
    return QRectF(p.x(), p.y(), item.width(), item.height())


class FreeSideTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        with patch('meridiana.gui.backend.assistant_chat.keys', KeyStore()), \
                patch('meridiana.gui.backend.voice.Voice', return_value=Voice()):
            self.host = QuickWindow(capannone(), Path(self.temp.name), real_views=True,
                                    theme={'theme': 'light', 'reducedMotion': True})
        win = self.window = self.host.window
        win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        win.show()
        win.resize(1400, 900)
        results, keys, _ = jobs.layout_of(self.host.bridge.session.project)
        self.host.bridge.accept_layout(self.host.bridge.session.generation, results, keys)
        pump(300)
        wait_for(lambda: self.window.findChild(QObject, 'assistantLayer') is not None, 10)
        self.layer = self.window.findChild(QObject, 'assistantLayer')
        self.chat = self.host.parts.controllers['assistant']
        self.chat.cfg.assistant_introduced = True
        wait_for(lambda: self.layer.property('placedOnce'), 5)
        pump(400)
        self.addCleanup(self.close)

    def close(self):
        warnings = real(self.host.warnings)
        self.host.close()
        self.app.processEvents()
        self.assertEqual(warnings, [])

    def spot(self):
        return (round(self.layer.property('avatarX')), round(self.layer.property('avatarY')))

    def side(self):
        r = self.layer.property('fileSide')
        return QRectF(r.x(), r.y(), r.width(), r.height())

    def open_file(self, section):
        self.host.parts.controllers['files'].selectSection(section)
        self.window.setProperty('fileOpen', True)
        wait_for(lambda: self.side().width() > 0, 5)
        pump(500)

    def close_file(self):
        self.window.setProperty('fileOpen', False)
        wait_for(lambda: self.side().width() == 0, 5)
        pump(500)

    def character(self):
        return scene(find(self.window, 'assistantCharacter'))

    def test_over_every_page_he_is_on_the_free_side_right_of_the_column(self):
        files = self.host.parts.controllers['files']
        self.open_file('open')
        pages = list(files.property('sections')) + ['preferences:' + k for k in (
            'appearance', 'navigation', 'keyboard', 'assistant', 'report', 'maps', 'performance', 'privacy')]
        for page in pages:
            files.selectSection(page)
            pump(300)
            side, him = self.side(), self.character()
            self.assertTrue(side.contains(him), f'{page}: Meridio {him} out of the free side {side}')
            # the column's own items end where the free side begins
            column = find(self.window, 'settingsHeading' if page.startswith('preferences') else 'fileSectionTitle')
            if not page.startswith('preferences'):
                column = column.parentItem()
            self.assertLessEqual(scene(column).right(), side.left() + 0.5, page)

    def test_in_a_narrow_window_the_column_gives_him_his_room_down_to_its_least(self):
        # Daniel 15/11/2026: «ci sta che la colonna gli ceda quei 42px, ma porre dei limiti»
        from meridiana.gui.style.design import Size, Space
        from meridiana.app.assistant import figure
        room = figure.SIZE + 2 * Space.L
        files = self.host.parts.controllers['files']
        self.open_file('preferences:appearance')
        for width, gives in ((1100, True), (900, True), (800, False)):
            self.window.resize(width, 600)
            files.selectSection('preferences:appearance')
            pump(400)
            side, him = self.side(), self.character()
            column = find(self.window, 'settingsHeading')
            if gives:
                self.assertGreaterEqual(side.width(), room - 0.5, f'{width} px: the column did not give him his room')
                self.assertTrue(side.contains(him), f'{width} px: Meridio out of the free side')
                self.assertLessEqual(scene(column).right(), him.left() - Space.L + 0.5)
            else:
                self.assertLess(side.width(), room, f'{width} px: the column went under its least')
            self.assertGreaterEqual(column.width(), Size.READING - 0.5, f'{width} px: the column under its least')

    def test_closing_file_gives_him_back_his_place_in_the_project(self):
        before = self.spot()
        self.open_file('export')
        self.assertNotEqual(self.spot(), before, 'over File he stayed where he was in the project')
        self.close_file()
        self.assertEqual(self.spot(), before)

    def test_moved_by_hand_over_file_his_place_in_the_project_stays(self):
        places = dict(self.chat.host.places)
        before = self.spot()
        self.open_file('preferences:appearance')
        him = find(self.window, 'assistantCharacter')
        drag(self.app, self.window, point(him), point(him, -200, -100))
        pump(300)
        moved = self.spot()
        self.assertNotEqual(moved, before)
        self.host.parts.controllers['files'].selectSection('preferences:keyboard')
        pump(300)
        self.assertEqual(self.spot(), moved, 'moved by hand over File, he was put back on the side')
        self.assertEqual(dict(self.chat.host.places), places, 'a move over File changed his place in the project')
        self.close_file()
        self.assertEqual(self.spot(), before)

    def test_docked_he_floats_over_file_and_is_the_tab_again_after(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.layer.property('opened'), 5)
        click(self.app, self.window, point(find(self.window, 'assistantDock')))
        dock = find(self.window, 'assistantDockPanel')
        bubble = find(self.window, 'assistantBubble')
        wait_for(lambda: dock.isVisible() and bubble.parentItem() is dock.property('assistantSpace'), 5)
        self.open_file('export')
        self.assertTrue(self.layer.property('docked'))
        self.assertFalse(self.layer.property('dockedNow'))
        self.assertFalse(dock.isVisible(), 'over File his tab is nowhere')
        self.assertTrue(find(self.window, 'assistantCharacter').isVisible())
        self.assertTrue(self.side().contains(self.character()))
        self.close_file()
        wait_for(lambda: dock.isVisible() and bubble.parentItem() is dock.property('assistantSpace'), 5)
        self.assertTrue(self.layer.property('dockedNow'))
        self.assertTrue(self.layer.property('opened'))
        self.assertFalse(find(self.window, 'assistantCharacter').isVisible())

    def test_the_minus_only_hides_him(self):
        for docked in (False, True):
            if docked:
                self.host.shell.trigger('assistant')
                wait_for(lambda: self.layer.property('opened'), 5)
                click(self.app, self.window, point(find(self.window, 'assistantDock')))
                wait_for(lambda: self.layer.property('dockedNow'), 5)
            for over_file in (True, False):
                if over_file:
                    self.open_file('export')
                if not self.layer.property('opened'):
                    self.host.shell.trigger('assistant')
                    wait_for(lambda: self.layer.property('opened'), 5)
                    pump(300)
                where = self.spot()
                click(self.app, self.window, point(find(self.window, 'assistantClose')))
                wait_for(lambda: not self.layer.property("opened"), 5)
                pump(300)
                what = f'docked {docked}, over File {over_file}'
                self.assertEqual(self.layer.property('docked'), docked, what + ': the «–» changed his docking')
                self.assertEqual(self.spot(), where, what + ': the «–» moved him')
                if over_file:
                    self.close_file()


if __name__ == '__main__':
    unittest.main()
