"""Real Quick windows and pointer events: R369, R371, R383, R332."""
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.quick.backend.assistant import build_page


class SceneTest(unittest.TestCase):
    maxDiff = None
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['meridio-tests'])

    def scene(self, page='meridio', options=None, width=1366, height=900):
        engine, window, theme = build_page(page, options=options, width=width, height=height)
        errors = []
        engine.warnings.connect(lambda items: errors.extend(i.toString() for i in items))
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        QTest.qWait(220)
        root = window.findChild(QObject, 'assistantLayer')
        def cleanup():
            window.close()
            delete(engine)
            self.assertEqual(errors, [])
        self.addCleanup(cleanup)
        return engine, window, root

    def mouse(self, window, kind, point):
        edge = kind != QEvent.Type.MouseMove
        QCoreApplication.sendEvent(window, QMouseEvent(kind, QPointF(*point), QPointF(*point),
            Qt.MouseButton.LeftButton if edge else Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier))

    def test_all_pages_load_with_pixels(self):
        for page in ('meridio', 'conversation', 'help', 'manual', 'tour', 'setup'):
            with self.subTest(page=page):
                _, window, root = self.scene(page)
                self.assertFalse(window.grabWindow().isNull())
                self.assertTrue(root.property('opened'))

    def test_drag_keeps_every_frame_with_pointer_and_only_flips_when_space_ends(self):
        engine, window, root = self.scene(options={'reducedMotion': True})
        root.setProperty('avatarX', 100)
        root.setProperty('avatarY', 400)
        root.setProperty('tail', 'left')
        root.placeBubble()
        QTest.qWait(40)
        count = engine._assistant_images.requests
        saves = []
        root.placementSaved.connect(lambda *args: saves.append(args))
        self.mouse(window, QEvent.Type.MouseButtonPress, (123, 423))
        for x in range(120, 1000, 20):
            self.mouse(window, QEvent.Type.MouseMove, (x + 23, 423))
            self.assertEqual(root.property('avatarX'), x)
            # A frame is grabbed at every step. No stale screenshot replaces the live subtree.
            image = window.grabWindow()
            self.assertFalse(image.isNull())
            expected_side = 'left' if x + 46 + 4 + 320 <= 1366 else 'right'
            self.assertEqual(root.property('tail'), expected_side)
            expected_x = x + 50 if expected_side == 'left' else x - 324
            self.assertEqual(root.property('bubbleX'), expected_x)
        self.mouse(window, QEvent.Type.MouseButtonRelease, (1003, 423))
        self.assertEqual(len(saves), 1)
        self.assertEqual(engine._assistant_images.requests, count)

    def test_help_avoids_its_target_and_escape_restores_float(self):
        engine, window, root = self.scene(options={'reducedMotion': True})
        start = (root.property('avatarX'), root.property('avatarY'))
        root.remember()
        engine._assistant_help.request('site')
        from PySide6.QtCore import QRectF
        target = QRectF(980, 60, 360, 740)
        root.moveBeside(target)
        bubble = QRectF(root.property('bubbleX'), root.property('bubbleY'), 320, 500)
        self.assertFalse(bubble.intersects(target))
        QTest.keyClick(window, Qt.Key.Key_Escape)
        QTest.qWait(30)
        self.assertEqual((root.property('avatarX'), root.property('avatarY')), start)
        self.assertFalse(root.property('opened'))

    def test_docked_help_stays_and_disabled_character_only_visits(self):
        engine, window, root = self.scene(options={'reducedMotion': True})
        start = (root.property('avatarX'), root.property('avatarY'))
        root.setProperty('docked', True)
        engine._assistant_help.request('site')
        from PySide6.QtCore import QRectF
        root.moveBeside(QRectF(900, 10, 400, 800))
        self.assertEqual((root.property('avatarX'), root.property('avatarY')), start)
        root.dismiss()
        root.setProperty('docked', False)
        root.setProperty('assistantEnabled', False)
        self.assertFalse(root.property('characterVisible'))
        engine._assistant_help.request('site')
        self.assertTrue(root.property('characterVisible'))
        root.dismiss()
        self.assertFalse(root.property('characterVisible'))

    def test_resize_keeps_opposite_edges_and_minimum(self):
        _, window, root = self.scene(options={'reducedMotion': True})
        grip = root.findChild(QObject, 'assistantGrip')
        bubble = root.findChild(QObject, 'assistantBubble')
        right, bottom = bubble.x() + bubble.width(), bubble.y() + bubble.height()
        start = grip.mapToScene(QPointF(8, 8))
        self.mouse(window, QEvent.Type.MouseButtonPress, (start.x(), start.y()))
        self.mouse(window, QEvent.Type.MouseMove, (start.x() - 50, start.y() - 60))
        self.mouse(window, QEvent.Type.MouseButtonRelease, (start.x() - 50, start.y() - 60))
        self.assertEqual(root.property('bubbleWidth'), 370)
        self.assertEqual(root.property('bubbleHeight'), 560)
        self.assertEqual(bubble.x() + bubble.width(), right)
        self.assertEqual(bubble.y() + bubble.height(), bottom)

    def test_vertical_tail_reaches_character_after_window_and_bubble_resize(self):
        _, window, root = self.scene(options={'reducedMotion': True}, width=1600, height=960)
        root.setProperty('avatarX', 1500)
        root.setProperty('avatarY', 870)
        root.setProperty('bubbleWidth', 360)
        root.setProperty('bubbleHeight', 600)
        root.setProperty('tail', 'bottom')
        root.setProperty('tailOffset', 577)
        root.placeBubble()
        self.assertLessEqual(root.property('avatarX') + 23, root.property('bubbleX') + 360 - 23)
        self.assertGreaterEqual(root.property('avatarX') + 23, root.property('bubbleX') + 23)
        self.assertEqual(root.property('bubbleY') + 600 + 4, root.property('avatarY'))

    def test_r361_shrinking_keeps_tail_at_character_and_opposite_edge_fixed(self):
        _, window, root = self.scene(options={'reducedMotion': True})
        root.setProperty('avatarX', 1000)
        root.setProperty('avatarY', 400)
        root.setProperty('bubbleHeight', 600)
        root.setProperty('tailOffset', 250)
        root.placeBubble()
        grip = root.findChild(QObject, 'assistantGrip')
        bubble = root.findChild(QObject, 'assistantBubble')
        before = bubble.y()
        start = grip.mapToScene(QPointF(8, 8))
        self.mouse(window, QEvent.Type.MouseButtonPress, (start.x(), start.y()))
        self.mouse(window, QEvent.Type.MouseMove, (start.x(), start.y()-500))
        self.mouse(window, QEvent.Type.MouseButtonRelease, (start.x(), start.y()-500))
        self.assertEqual(bubble.y(), before)
        self.assertGreaterEqual(bubble.y()+bubble.height()-23, root.property('avatarY')+23)

    def test_r369_side_change_glides_but_character_always_tracks_pointer(self):
        _, window, root = self.scene()
        root.setProperty('relocating', False)
        root.setProperty('avatarX', 900)
        root.setProperty('avatarY', 400)
        root.setProperty('tail', 'left')
        root.placeBubble()
        bubble = root.findChild(QObject, 'assistantBubble')
        old = bubble.x()
        self.mouse(window, QEvent.Type.MouseButtonPress, (923, 423))
        self.mouse(window, QEvent.Type.MouseMove, (1023, 423))
        self.assertEqual(root.property('avatarX'), 1000)
        self.assertEqual(root.property('tail'), 'right')
        self.assertEqual(bubble.x(), old)
        QTest.qWait(90)
        self.assertGreater(bubble.x(), root.property('bubbleX'))
        self.assertLess(bubble.x(), old)
        self.mouse(window, QEvent.Type.MouseButtonRelease, (1023, 423))
        QTest.qWait(180)
        self.assertEqual(bubble.x(), root.property('bubbleX'))

    def test_r369_title_drag_moves_character_and_bubble_together(self):
        _, window, root = self.scene(options={'reducedMotion': True})
        title = root.findChild(QObject, 'assistantTitle')
        start = title.mapToScene(QPointF(title.width()/2, title.height()/2))
        before = (root.property('avatarX'), root.property('avatarY'))
        self.mouse(window, QEvent.Type.MouseButtonPress, (start.x(), start.y()))
        self.mouse(window, QEvent.Type.MouseMove, (start.x()-100, start.y()-30))
        self.mouse(window, QEvent.Type.MouseButtonRelease, (start.x()-100, start.y()-30))
        self.assertEqual((root.property('avatarX'), root.property('avatarY')), (before[0]-100, before[1]-30))

    def test_pixel_style_and_small_docked_large_text_have_pixels(self):
        _, window, root = self.scene(options={'textSize': 'large', 'theme': 'dark'}, width=700, height=500)
        root.setProperty('characterStyle', 'pixel')
        root.setProperty('docked', True)
        QTest.qWait(60)
        self.assertFalse(window.grabWindow().isNull())
        bubble = root.findChild(QObject, 'assistantBubble')
        self.assertLessEqual(bubble.x() + bubble.width(), window.width())

    def test_fade_has_constant_geometry_and_no_additional_top_level(self):
        _, window, root = self.scene()
        bubble = root.findChild(QObject, 'assistantBubble')
        for _ in range(60):     # R500: placed once, he slides into the area grown after it, with his bubble
            if not root.property('relocating'):
                break
            QTest.qWait(20)
        geometry = (bubble.x(), bubble.y(), bubble.width(), bubble.height())
        windows = set(QApplication.topLevelWindows())
        root.dismiss()
        values = []
        for _ in range(12):
            QTest.qWait(15)
            values.append(bubble.opacity())
            self.assertEqual((bubble.x(), bubble.y(), bubble.width(), bubble.height()), geometry)
        self.assertEqual(values[-1], 0)
        self.assertTrue(any(0 < value < 1 for value in values))
        root.open()
        QTest.qWait(220)
        self.assertEqual(bubble.opacity(), 1)
        self.assertEqual(set(QApplication.topLevelWindows()), windows)
