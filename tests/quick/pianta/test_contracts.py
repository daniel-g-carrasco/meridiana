"""Remaining R389 plan contracts driven through the real Quick event adapter."""
import math
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from meridiana import model, move
from quick.pianta import test_edit_window as edit

setUpModule = edit.setUpModule


class Contracts(unittest.TestCase):
    setUp = edit.EditWindowTest.setUp
    tearDown = edit.EditWindowTest.tearDown
    screen = edit.EditWindowTest.screen
    click = edit.EditWindowTest.click
    key = edit.EditWindowTest.key
    text = edit.EditWindowTest.text
    visual = edit.EditWindowTest.visual

    def test_rotation_card_matches_the_committed_angle_and_copy(self):
        self.session.edit('Small subfield', lambda p: setattr(p.subfields[0], 'ring',
                                                            [[15, 8], [25, 8], [25, 12], [15, 12]]))
        self.controller.setPhase('plant')
        self.controller.editor.select('subfield', 's1')
        self.controller.setTool('move')
        QTest.mouseMove(self.window, self.screen((30, 10)))
        self.key(Qt.Key_R)
        point = (20+10*math.cos(math.radians(32)), 10+10*math.sin(math.radians(32)))
        QTest.mouseMove(self.window, self.screen(point))
        QTest.qWait(40)
        self.assertEqual(self.controller.preview['degrees'], 30)
        card = self.visual('toolCardText')
        self.assertTrue(card.isVisible())
        self.assertIn('30°', card.property('text'))
        point_in_view = self.screen(self.controller.editor.pointer)
        # R550: beside the pointer as every tooltip (ControlMetrics.besidePointer)
        self.assertAlmostEqual(card.parentItem().x(), point_in_view.x()+2, delta=1)
        self.assertAlmostEqual(card.parentItem().y(), point_in_view.y()+21, delta=1)
        from meridiana.ui.plan import PlanView
        reference = SimpleNamespace(gesture=self.controller.editor.gesture,
                                    _transform_now=lambda: self.controller.preview, move_mods=set())
        self.assertEqual(card.property('text').splitlines(), PlanView._move_labels(reference))
        folder = Path(__file__).resolve().parents[3]/'build/quick-foto/pianta/contracts'
        folder.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.window.grabWindow().save(str(folder/'rotate-card.png')))
        expected = model.Project.from_json(self.session.snapshot())
        move.rotate(expected, 'subfield', 's1', 20, 10, 30)(expected)
        self.click(point)
        self.assertEqual(self.session.project.subfields[0].ring, expected.subfields[0].ring)
        self.assertEqual(self.session.project.subfields[0].params, expected.subfields[0].params)
        self.key(Qt.Key_C)
        self.text('45')
        QTest.qWait(20)
        self.assertIn('copia', card.property('text'))
        self.key(Qt.Key_Return)
        self.assertEqual(len(self.session.project.subfields), 2)
        self.assertEqual(self.session.project.subfields[0].ring, expected.subfields[0].ring)
        self.assertFalse(self.warnings, self.warnings)

    def test_rotate_before_picking_and_move_distance_card(self):
        self.controller.editor.select('site', '')
        self.controller.setTool('rotate')
        self.click((1, 1))
        self.assertEqual(self.controller.editor.selection, ('building', 'b1'))
        self.text('90')
        expected = model.Project.from_json(self.session.snapshot())
        move.rotate(expected, 'building', 'b1', 20, 10, 90)(expected)
        self.key(Qt.Key_Return)
        self.assertEqual(self.session.project.buildings[0].footprint, expected.buildings[0].footprint)
        self.controller.setTool('move')
        self.click((20, 10))
        self.text('3;4')
        QTest.qWait(30)
        card = self.visual('toolCardText')
        self.assertTrue(card.isVisible())
        self.assertIn('5,00 m', card.property('text'))
        self.assertIn('E 3,00 m, N 4,00 m', card.property('text'))
        folder = Path(__file__).resolve().parents[3]/'build/quick-foto/pianta/contracts'
        folder.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.window.grabWindow().save(str(folder/'move-card.png')))
        self.key(Qt.Key_Escape)
        self.assertFalse(self.controller.editor.gesture.typing)
        self.assertNotIn('3;4', card.property('text'))
        self.key(Qt.Key_Escape)
        self.assertFalse(card.isVisible())

    def test_edge_collection_hover_cancel_and_short_side_without_pill(self):
        ring = self.session.project.buildings[0].footprint
        picked = []
        self.controller.edgePicked.connect(lambda *args: picked.append(args))
        self.controller.pickEdge('ridge', 'building', 'b1', ring)
        QTest.mouseMove(self.window, self.screen((40.1, 10)))
        QTest.qWait(30)
        self.assertEqual(self.controller.collector.hover[-1], 1)
        self.click((40.1, 10))
        self.assertEqual(picked, [('ridge', 'building', 'b1', 1)])
        self.assertFalse(self.controller.collector.active)
        self.controller.pickEdge('eave', 'building', 'b1', ring)
        self.key(Qt.Key_Escape)
        self.assertFalse(self.controller.collector.active)
        self.assertEqual(len(picked), 1)
        notch = [[0, 0], [12, 0], [12, 8], [6.3, 8], [6.3, 7.7], [6, 7.7], [6, 8], [0, 8]]
        self.session.edit('Notch', lambda p: setattr(p.buildings[0], 'footprint', notch))
        self.controller.editor.select('building', 'b1')
        self.controller.setTool('select')
        self.plan.setProperty('zoom', 30)
        self.controller.editSide(4)
        QTest.qWait(30)
        self.assertTrue(self.controller.sideEditing)
        self.assertTrue(self.visual('sideEditor').isVisible())
        self.key(Qt.Key_Escape)
        self.assertFalse(self.controller.sideEditing)

    def test_renaming_and_camera_changes_retain_native_module_paths(self):
        batch = self.visual('moduleGeometry')
        uploads = batch.uploads
        paths = batch.paths
        self.controller.editor.select('building', 'b1')
        self.controller.rename('New name')
        for step in range(12):
            self.plan.setProperty('panX', 200+step)
            self.plan.setProperty('zoom', 5+step/10)
            QTest.mouseMove(self.window, QPoint(600+step, 500))
        QTest.qWait(40)
        self.assertEqual(batch.uploads, uploads)
        self.assertEqual(batch.paths, paths)
        self.assertEqual(self.controller.calls['pointer'], 0)
        self.assertTrue(batch.property('ready'))

    def test_navigation_without_sweep_does_not_repaint_the_selection_mask(self):
        overlay = self.visual('selectionOverlay')
        QTest.mouseMove(self.window, QPoint(100, 100))
        QTest.qWait(80)
        paints = overlay.property('paintCount')
        for step in range(10):
            self.plan.setProperty('panX', 250+step)
            self.plan.setProperty('zoom', 5+step/10)
            QTest.mouseMove(self.window, QPoint(600+step, 500))
            QTest.qWait(20)
        self.assertEqual(overlay.property('paintCount'), paints)
        self.assertFalse(overlay.property('sweeping'))

    def test_viewbar_buttons_match_widgets_geometry_and_groups(self):
        import _setup
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QWidget, QMenu
        from meridiana.ui import icons
        from meridiana.ui.viewbar import ViewBar
        theme = _setup.meridiana_look()
        root = QWidget()
        self.addCleanup(root.close)
        self.addCleanup(root.deleteLater)
        menu = QMenu(root)
        groups = [[] for _ in range(5)]
        for row in self.controller.viewTools:
            action = QAction(icons.icon(row['icon']), row['tip'], root)
            action.setObjectName(row['command'])
            if row['command'] == 'background':
                action.setMenu(menu)
            groups[row['group']].append(action)
        reference = ViewBar(root, groups)
        reference.set_colours(theme.tokens)
        root.resize(600, 200)
        root.show()
        QTest.qWait(30)
        reference.adjustSize()
        quick = self.visual('planViewBar')
        self.assertEqual((quick.width(), quick.height()), (reference.width(), reference.height()))
        for action, button in reference.buttons.items():
            actual = self.visual('planView-'+action.objectName())
            at = actual.mapToItem(quick, QPointF(0, 0))
            self.assertEqual((at.x(), at.y(), actual.width(), actual.height()), button.geometry().getRect())
