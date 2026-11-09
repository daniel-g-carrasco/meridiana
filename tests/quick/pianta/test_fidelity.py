"""R326/R389: native rendering, persistent fit and the same gestures as PlanView."""
import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from quick.pianta.test_window import WindowTest, settle_zoom, setUpModule  # noqa: F401
from meridiana import model, view_colours
from quick.gestures import item


class Fidelity(unittest.TestCase):
    setUp = WindowTest.setUp
    tearDown = WindowTest.tearDown

    def test_selected_outline_stays_solid_above_hover(self):
        self.controller.session.edit('Building', lambda p: p.buildings.append(model.Building(
            id='b1', name='Building', footprint=[[0, 0], [20, 0], [20, 10], [0, 10]])))
        self.controller.editor.select('building', 'b1')
        self.controller._overlays()
        for name, value in (('zoom', 10), ('panX', 500), ('panY', 400)):
            self.plan.setProperty(name, value)
        colours = []
        for point in (QPoint(100, 100), QPoint(600, 350)):
            QTest.mouseMove(self.window, point)
            QTest.qWait(60)
            image = self.window.grabWindow()
            dpr = image.devicePixelRatio()
            colours.append([image.pixelColor(int((x+.5)*dpr), int(400*dpr)).name() for x in range(550, 650)])
        self.assertEqual(colours[0], colours[1], 'The hover is below the opaque selected outline, as in Widgets')

    def test_outline_dashes_keep_their_screen_spacing_at_two_zoom_levels(self):
        self.controller.session.edit('Array', lambda p: p.subfields.append(model.SubField(
            id='s1', name='Array', ring=[[-40, 0], [40, 0], [40, 20], [-40, 20]], filled=False)))
        periods = []
        for zoom in (5, 10):
            self.plan.setProperty('zoom', zoom)
            self.plan.setProperty('panX', 500)
            self.plan.setProperty('panY', 400)
            QTest.mouseMove(self.window, QPoint(100, 100))
            settle_zoom(self.plan, self.controller)     # R541: the dashes are laid out once the zoom settles
            QTest.qWait(80)
            image = self.window.grabWindow(); dpr = image.devicePixelRatio()
            values = [image.pixelColor(int((x+.5)*dpr), int(400*dpr)).blue() for x in range(350, 650)]
            starts = [i for i in range(1,len(values)) if values[i]>180 and values[i-1]<=180]
            self.assertGreater(len(starts), 15, starts)
            periods.append(sum(b-a for a,b in zip(starts,starts[1:],strict=False))/(len(starts)-1))
        self.assertAlmostEqual(periods[0],periods[1],delta=.25)

    def test_exclusion_hatching_is_cosmetic_at_two_zoom_levels(self):
        self.controller.session.edit('Exclusion', lambda p: p.exclusions.append(model.ExclusionItem(
            id='e1', ring=[[-20, -20], [20, -20], [20, 20], [-20, 20]])))
        for zoom in (5, 10):
            self.plan.setProperty('zoom', zoom)
            self.plan.setProperty('panX', 500)
            self.plan.setProperty('panY', 400)
            QTest.mouseMove(self.window, QPoint(100, 100))
            settle_zoom(self.plan, self.controller)     # R541: the dashes are laid out once the zoom settles
            QTest.qWait(80)
            image = self.window.grabWindow()
            dpr = image.devicePixelRatio()
            values = [image.pixelColor(int((x+.5)*dpr), int(400.5*dpr)).name() for x in range(450, 514)]
            pink = [i for i, colour in enumerate(values) if colour == '#ff5fa2']
            self.assertGreaterEqual(len(pink), 7, values)
            self.assertEqual(set(b-a for a, b in zip(pink, pink[1:], strict=False)), {8})

    def test_length_field_keeps_the_pills_disc_height_and_position(self):
        self.controller.session.edit('Building', lambda p: p.buildings.append(model.Building(
            id='b1', name='Building', footprint=[[0, 0], [20, 0], [20, 10], [0, 10]])))
        self.controller.editor.select('building', 'b1')
        self.controller._overlays()
        self.plan.fit()
        QTest.qWait(100)
        pill = item(self.window, 'sidePill0')
        self.assertIsNotNone(pill)
        self.controller.editSide(0)
        QTest.qWait(50)
        field = item(self.window, 'sideEditor')
        self.assertIsNotNone(field)
        self.assertEqual(field.property('height'), pill.property('height'))
        self.assertAlmostEqual(field.property('x'), pill.property('x'), delta=1)
        self.assertAlmostEqual(field.property('y'), pill.property('y'), delta=1)
        QTest.keyClick(self.window, Qt.Key_Escape)
        self.assertFalse(self.controller.sideEditing)

    def test_selection_uses_widgets_halo_fill_and_solid_contour(self):
        self.controller.session.edit('Building', lambda p: p.buildings.append(model.Building(
            id='b1', name='Building', footprint=[[0, 0], [20, 0], [20, 10], [0, 10]])))
        self.controller.editor.select('building', 'b1')
        self.controller._overlays()
        halo, ink = self.controller.highlights
        self.assertEqual(halo['width'], view_colours.WIDTHS['select'] + view_colours.WIDTHS['select_halo'])
        self.assertEqual(ink['width'], view_colours.WIDTHS['select'])
        self.assertEqual(halo['fill'], '#1eb48cff')
        self.assertEqual(ink['fill'], 'transparent')
        self.assertFalse(ink.get('dashed', False))
        self.plan.fit()
        point = self.plan.screen(10, 5).toPoint()
        QTest.mouseMove(self.window, QPoint(100, 100))
        QTest.qWait(100)
        image = self.window.grabWindow()
        dpr = image.devicePixelRatio()
        colour = image.pixelColor(int((point.x()+.5)*dpr), int((point.y()+.5)*dpr))
        QTest.mouseMove(self.window, point)
        QTest.qWait(100)
        hovered = self.window.grabWindow()
        self.assertEqual(hovered.pixelColor(int((point.x()+.5)*dpr), int((point.y()+.5)*dpr)), colour,
                         'Hover outlines the building; it must not add a second translucent fill.')
    def test_fit_follows_resize_until_the_first_manual_pan(self):
        self.plan.fit()
        zoom = self.plan.property('zoom')
        self.window.resize(1700, 1100)
        QTest.qWait(50)
        self.assertGreater(self.plan.property('zoom'), zoom)
        QTest.mousePress(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(500, 400))
        QTest.mouseMove(self.window, QPoint(550, 450))
        QTest.mouseRelease(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(550, 450))
        zoom = self.plan.property('zoom')
        self.window.resize(1300, 850)
        QTest.qWait(50)
        self.assertEqual(self.plan.property('zoom'), zoom)
        self.plan.fit()
        zoom = self.plan.property('zoom')
        self.window.resize(1700, 1100)
        QTest.qWait(50)
        self.assertGreater(self.plan.property('zoom'), zoom)

    def test_escape_drawing_three_states_and_focus_after_tool_button(self):
        self.controller.setTool('building')
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(500, 400))
        QTest.keyClick(self.window, Qt.Key_1)
        QTest.keyClick(self.window, Qt.Key_2)
        self.assertEqual(self.controller.drawing.typed, '12')
        QTest.keyClick(self.window, Qt.Key_Escape)
        self.assertEqual(self.controller.tool, 'building')
        self.assertFalse(self.controller.drawing.typed)
        self.assertTrue(self.controller.drawing.points)
        QTest.keyClick(self.window, Qt.Key_Escape)
        self.assertFalse(self.controller.drawing.points)
        self.assertEqual(self.controller.tool, 'building')
        QTest.keyClick(self.window, Qt.Key_Escape)
        self.assertEqual(self.controller.tool, 'select')


if __name__ == '__main__':
    unittest.main()
