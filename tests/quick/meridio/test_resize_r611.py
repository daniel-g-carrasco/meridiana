"""R611: the bubble's grip follows the pointer point by point (Daniel 14/11/2026, on the Linux laptop).

«Il ridimensionamento non segue il puntatore, cambia grandezza a scalini»: the grip is dragged by small steps, one
point at a time, along each way it allows (across, up and down, and both together), and at every step the bubble's
moving edge stands where the pointer is, at the same distance it had at the press (within 1 px, no jump), while the
opposite edge stays. Synthetic events given to the window only (QTest's mouse), offscreen.
"""
import time
import unittest

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana import i18n
from meridiana.app.platform import config
from meridiana.gui.backend.assistant import build_page
from meridiana.gui.backend.assistant_chat import AssistantChat
from quick.meridio.support import Host, KeyStore, Voice
from quick.gestures import pump, wait_for


class ResizeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r611-tests'])

    def scene(self, chat=None):
        engine, window, _ = build_page('meridio', options={'reducedMotion': True}, chat=chat)
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        layer = window.findChild(QObject, 'assistantLayer')
        wait_for(lambda: not layer.property('relocating'), 5)

        def cleanup():
            window.close()
            delete(engine)
        self.addCleanup(cleanup)
        return window, layer

    def drag(self, window, layer, way, steps=40):
        """The grip pressed and carried `steps` times by `way`: the worst distance, at any step, between where the
        moving edges are and where the pointer took them, and the edges that should have stayed and moved."""
        bubble = layer.findChild(QObject, 'assistantBubble')
        grip = layer.findChild(QObject, 'assistantGrip')
        left, top = grip.property('gripLeft'), grip.property('gripTop')

        def edges():
            p = bubble.mapToScene(QPointF(0, 0))
            return p.x(), p.y(), p.x() + bubble.width(), p.y() + bubble.height()

        start = grip.mapToScene(QPointF(8, 8)).toPoint()
        x0, y0, r0, b0 = edges()
        # the moving corner's distance from the pointer at the press
        ox = start.x() - (x0 if left else r0)
        oy = start.y() - (y0 if top else b0)
        QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        worst, stayed = 0.0, 0.0
        for i in range(1, steps + 1):
            at = start + way * i
            QTest.mouseMove(window, at)
            pump(1)
            x, y, r, b = edges()
            mx = x if left else r
            my = y if top else b
            if way.x():
                worst = max(worst, abs(at.x() - ox - mx))
                stayed = max(stayed, abs((r if left else x) - (r0 if left else x0)))
            if way.y():
                worst = max(worst, abs(at.y() - oy - my))
                stayed = max(stayed, abs((b if top else y) - (b0 if top else y0)))
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + way * steps)
        return worst, stayed

    def test_the_grip_follows_the_pointer_point_by_point(self):
        grip_ways = {'across, outwards': QPoint(-1, 0), 'across, inwards': QPoint(1, 0),
                     'up and down, outwards': QPoint(0, -1), 'up and down, inwards': QPoint(0, 1),
                     'both, outwards': QPoint(-1, -1), 'both, inwards': QPoint(1, 1)}
        for name, way in grip_ways.items():
            with self.subTest(way=name):
                window, layer = self.scene()
                grip = layer.findChild(QObject, 'assistantGrip')
                # the preview's grip is at the top left (the tail on the right, Meridio below the middle)
                self.assertTrue(grip.property('gripLeft') and grip.property('gripTop'))
                worst, stayed = self.drag(window, layer, way)
                print(f'R611 {name}: worst {worst:.2f} px from the pointer, opposite edge moved {stayed:.2f} px')
                self.assertLessEqual(worst, 1.0, 'the moving edge left the pointer')
                self.assertLessEqual(stayed, 1.0, 'the opposite edge moved')

    def test_the_words_follow_the_bubble_at_every_point(self):
        # R647 (Daniel 15/11/2026: «i contenuti non si modificano dinamicamente. Accade solo quando rilascio»): half way
        # through the gesture the words are already as wide as the bubble less its margins; the cost of a point is
        # measured with ten long answers (R611 had the words keep the width of the press for it: 56 ms a point, 14/11)
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'),
                             key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        window, layer = self.scene(chat)
        for _ in range(10):
            chat.view.answer(chr(10).join('Un paragrafo lungo con dettagli utili da leggere.' for _ in range(6)))
        scroll = layer.findChild(QObject, 'conversationScroll')
        bubble = layer.findChild(QObject, 'assistantBubble')
        wait_for(lambda: scroll.property('contentItem').property('contentHeight') > scroll.height() + 200, 5)
        gap = bubble.width() - scroll.width()          # the margins, the frame and the tail around the words
        grip = layer.findChild(QObject, 'assistantGrip')
        start = grip.mapToScene(QPointF(8, 8)).toPoint()
        QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        times = []
        for i in range(1, 41):
            t = time.perf_counter()
            QTest.mouseMove(window, start + QPoint(-i, 0))
            pump(1)
            times.append((time.perf_counter() - t) * 1000)
            if i == 20:
                self.assertAlmostEqual(scroll.width(), bubble.width() - gap, delta=0.5,
                                       msg='half way through the gesture the words kept another width')
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(-40, 0))
        pump(20)
        times.sort()
        print(f'R647 a point of the grip with ten long answers: {times[20]:.1f} ms (median), {times[-1]:.1f} ms at worst')
        self.assertAlmostEqual(scroll.width(), bubble.width() - gap, delta=0.5)

    def test_every_step_of_the_tour_fits_its_words(self):
        # «nella presentazione il fumetto si adatta al testo ma non si allarga quel tanto in più che servirebbe: resta
        # una barra di scorrimento per poche righe mancanti»: the height asked left the bubble's title out, 24 px short
        # at every step; with room in the window no step scrolls (before: all 13, it and en, 1366x900 and 1280x720)
        for lang in ('it', 'en'):
            i18n.setup(lang)
            self.addCleanup(i18n.setup, 'it')
            engine, window, _ = build_page('tour', options={'reducedMotion': True}, width=1280, height=720)
            self.addCleanup(lambda w=window, e=engine: (w.close(), delete(e)))
            pump(200)
            layer = window.findChild(QObject, 'assistantLayer')
            service = engine._assistant_help
            for i in range(len(service.property('tourSteps'))):
                service.goToStep(i)
                pump(100)
                card = layer.findChild(QObject, 'assistantContent').property('item')
                pending, page = [card], None
                while pending and page is None:
                    node = pending.pop()
                    if node.metaObject().className().startswith('ScrollPage_'):
                        page = node
                    pending.extend(node.childItems())
                view = page.property('contentItem')
                with self.subTest(lang=lang, step=i + 1):
                    self.assertLessEqual(view.property('contentHeight') - view.height(), 0.5, 'the step scrolls')


class BindingLoopTest(unittest.TestCase):
    """15/11/2026, the log of the Linux laptop: «Binding loop detected for property "fittedHeight"» twice a round at
    the opening of the bubble. The height that fits a page depended on the tail's side, and the bubble was placed (its
    side chosen by the height) while that height was being written. In the real window, his conversation opened, the
    whole tour walked and a help shown: not one binding loop, in the log or in the engine's warnings."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r611-tests'])

    def test_opening_the_bubble_and_walking_the_tour_make_no_binding_loop(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from PySide6.QtCore import qInstallMessageHandler
        from _fixtures import capannone
        from meridiana.gui.application import QuickWindow
        said = []
        previous = qInstallMessageHandler(lambda kind, context, message: said.append(message))
        self.addCleanup(qInstallMessageHandler, previous)
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        with patch('meridiana.gui.backend.assistant_chat.keys', KeyStore()), \
                patch('meridiana.gui.backend.voice.Voice', return_value=Voice()):
            host = QuickWindow(capannone(), Path(temp.name), real_views=True,
                               theme={'theme': 'light', 'reducedMotion': True})
        self.addCleanup(host.close)
        host.window.show()
        host.window.resize(1600, 960)
        self.assertTrue(QTest.qWaitForWindowExposed(host.window))
        wait_for(lambda: host.window.findChild(QObject, 'assistantLayer') is not None, 10)
        layer = host.window.findChild(QObject, 'assistantLayer')
        host.parts.controllers['assistant'].cfg.assistant_introduced = True
        host.shell.trigger('assistant')                     # the conversation opened and closed
        wait_for(lambda: layer.property('opened'), 5)
        pump(200)
        host.shell.trigger('assistant')
        service = host.parts.controllers['assistant_help']
        host.shell.trigger('guided_tour')
        wait_for(lambda: service.tourActive, 5)
        for i in range(service.tourStep['total']):
            service.goToStep(i)
            pump(150)
        service.pauseTour()
        service.request('phase.model')
        pump(300)
        loops = [m for m in said + host.warnings if 'Binding loop' in m]
        self.assertEqual(loops, [], 'binding loops while the bubble opened and the tour was walked')


if __name__ == '__main__':
    unittest.main()
