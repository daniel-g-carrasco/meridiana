"""Inverter gestures change the real project and can be undone."""
import copy
import unittest

import _setup
from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from quick.aiuti.differential import connected_fixture
from quick.gestures import click, drag, item, key, mouse, point, pump
from quick.impianto.panel_fixture import PanelFixture

setUpModule = _setup.keep_global_state


class Reorder(unittest.TestCase):
    def setUp(self):
        project = connected_fixture()
        project.energy['inverters'][0]['count'] = 3
        self.panel = PanelFixture(project)
        self.addCleanup(self.panel.close)
        # Offscreen's initial pointer can open the totals tooltip over the first handle.
        # Give this window an explicit pointer position in empty space before any gesture.
        mouse(self.panel.app, self.panel.window, QEvent.Type.MouseMove, QPointF(500, 1000), Qt.NoButton, Qt.NoButton)
        tips = [o for o in self.panel.root.findChildren(QObject) if o.metaObject().className().startswith('ToolTip')]
        self.assertTrue(tips)
        self.assertTrue(_setup.wait_until(self.panel.app, lambda: all(not tip.property('visible') for tip in tips), 5))
        self.before = copy.deepcopy(project.energy)

    def card(self, number):
        return item(self.panel.window, f'inverter-card-{number}')

    def test_handle_moves_in_the_scrolling_panel_with_destination_preview_and_undo(self):
        window, app = self.panel.window, self.panel.app
        source = self.card(1)
        target = self.card(3)
        start = source.mapToScene(QPointF(20, 20))
        end = point(target)
        mouse(app, window, QEvent.Type.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton)
        for n in range(1, 16):
            mouse(app, window, QEvent.Type.MouseMove, start+(end-start)*n/15, Qt.NoButton, Qt.LeftButton)
            pump(20)
        preview = item(window, 'inverter-drop-preview-1')
        self.assertTrue(preview.isVisible(), (source.property('dropIndex'), source.property('dragging'),
                                             source.y(), target.y(), end, item(window, 'panel-scroll').property('contentY')))
        self.assertEqual(source.property('dropIndex'), 2)
        mouse(app, window, QEvent.Type.MouseButtonRelease, end, Qt.LeftButton, Qt.NoButton)
        self.panel.settle()
        self.assertEqual(self.panel.backend.working, 3)
        self.assertEqual(self.panel.session.project.energy['strings']['runs'][0]['inverter'], 3)
        self.assertTrue(self.panel.backend.strings[0]['label'].startswith('3.'))
        self.panel.backend.undo()
        self.panel.settle()
        self.assertEqual(self.panel.session.project.energy, self.before)

    def test_alt_arrows_keep_focus_and_move_one_place_each_with_undo(self):
        panel = self.panel
        click(panel.app, panel.window, point(self.card(1)))
        key(panel.app, panel.window, Qt.Key_Down, modifiers=Qt.AltModifier)
        panel.settle()
        self.assertEqual(panel.backend.working, 2)
        self.assertTrue(self.card(2).hasActiveFocus())
        key(panel.app, panel.window, Qt.Key_Up, modifiers=Qt.AltModifier)
        panel.settle()
        self.assertEqual(panel.backend.working, 1)
        self.assertEqual(panel.session.project.energy['strings'], self.before['strings'])
        panel.backend.undo()
        panel.settle()
        self.assertEqual(panel.session.project.energy['strings']['runs'][0]['inverter'], 2)
        panel.backend.undo()
        panel.settle()
        self.assertEqual(panel.session.project.energy, self.before)

    def test_cancelled_or_stationary_handle_never_edits(self):
        panel = self.panel
        start = self.card(1).mapToScene(QPointF(20, 20))
        click(panel.app, panel.window, start)
        drag(panel.app, panel.window, start, start + QPointF(2, 2), steps=2)
        panel.settle()
        self.assertEqual(panel.session.project.energy, self.before)

    def test_drag_reaches_the_project_edit(self):
        panel = self.panel
        drag(panel.app, panel.window, self.card(1).mapToScene(QPointF(20, 20)), point(self.card(3)))
        panel.settle()
        self.assertEqual(panel.session.project.energy['strings']['runs'][0]['inverter'], 3)

    def test_closed_nonworking_card_can_move_up_without_moving_the_target(self):
        panel = self.panel
        start = self.card(3).mapToScene(QPointF(20, 20))
        drag(panel.app, panel.window, start, point(self.card(1)))
        panel.settle()
        self.assertEqual(panel.backend.working, 1)
        self.assertEqual(panel.session.project.energy['strings']['runs'][0]['inverter'], 2)
        panel.backend.undo()
        panel.settle()
        self.assertEqual(panel.session.project.energy, self.before)

    def test_drop_outside_cards_and_alt_at_boundary_never_edit(self):
        panel = self.panel
        start = self.card(1).mapToScene(QPointF(20, 20))
        drag(panel.app, panel.window, start, QPointF(500, 1000), steps=10)
        panel.settle()
        self.card(1).forceActiveFocus()
        key(panel.app, panel.window, Qt.Key_Up, modifiers=Qt.AltModifier)
        panel.settle()
        self.assertEqual(panel.session.project.energy, self.before)
