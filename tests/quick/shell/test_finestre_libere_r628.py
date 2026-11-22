"""R628 (Daniel 15/11/2026, the catalogue of the inverters on the Linux laptop): «aprendo il catalogo, mi sono reso conto
che non posso ridimensionarlo, e inoltre me lo fa spostare solo all'interno di un ristrettissimo range di movimento»;
«mantiene dei margini abbastanza larghi da sopra e sotto soprattutto, ma anche dai lati»; «non mi piace il fatto che
non sia utilizzabile meridio». His choice: the windows stay inside the program, but they resize, move freely, and
Meridio stays over them and usable. For every window, in the common one (M.Dialog). On the program's own window, off
screen, with three windows: the catalogue, the IFC import, a short question (delete the strings).

- moved: anywhere over the program's window and past its sides, with ControlMetrics.dialogHold (56) of its head
  inside on every side and its head never above the top; the program made smaller brings it back where it can be taken;
- resized: from the four sides and the four corners, the opposite side standing still, down to its least (its head,
  its foot, a little of its body, its buttons) and up to the whole program's window; the body follows (the list of the
  catalogue grows, the buttons stay at the bottom); the size is kept for its kind, saved with the window's arrangement,
  and a double click on a grip goes back to the size it asks;
- Meridio over a modal window: his figure shown, a click on it opens his bubble, his question takes the keyboard, a
  Return there sends it and does not press the window's button, Esc there does not close the window; dragged, he moves;
- the window's beat while the catalogue is resized, against the same number of moves (the per-step cost printed).

    python -m unittest quick.shell.test_finestre_libere_r628
    python tests/quick/shell/test_finestre_libere_r628.py shot <folder> [light|dark]     (the pictures)
"""
import json
import statistics
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup
from PySide6.QtCore import QEvent, QMetaObject, QObject, QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from quick.aiuti.tempi import timed

HOLD = 56           # ControlMetrics.dialogHold: 2 x Theme.size.CONTROL


def walk(root):
    pending = [root]
    while pending:
        item = pending.pop()
        yield item
        pending.extend(item.childItems())


def shown(item):
    while item is not None:
        if not item.isVisible():
            return False
        item = item.parentItem()
    return True


def rect_of(item):
    p = item.mapToScene(QPointF(0, 0))
    return QRectF(p.x(), p.y(), item.width(), item.height())


ROOT = Path(__file__).resolve().parents[3]


def child_env(work, root=ROOT):
    """A screen larger than the program's window (Qt's offscreen one is 800 x 800), as test_dialoghi_r586 does."""
    import os
    screen = Path(work) / 'screen.json'
    screen.write_text('{"screens": [{"name": "R628", "x": 0, "y": 0, "width": 3000, "height": 2000, '
                      '"logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}', encoding='utf8')
    return dict(os.environ, PYTHONPATH=os.pathsep.join([str(Path(root) / 'tests'), str(Path(root) / 'src')]),
                # relative to the child's folder (tests): the «C:» of a whole path would end the platform's argument
                QT_QPA_PLATFORM='offscreen:configfile=' + os.path.relpath(screen, Path(root) / 'tests').replace(os.sep, '/'),
                QSG_RENDER_LOOP='basic',
                PYTHONUTF8='1', MERIDIANA_PRELOAD='0', R628_INNER='1',
                APPDATA=str(Path(work) / 'APPDATA'), LOCALAPPDATA=str(Path(work) / 'LOCALAPPDATA'))


class Windows(unittest.TestCase):
    """The program's window on a screen large enough for it: the tests of `Free` in a process of their own."""

    def test_r628_free_windows_on_the_program_s_window(self):
        import os
        import shutil
        import subprocess
        if os.environ.get('R628_INNER'):
            self.skipTest('the inner run')
        work = tempfile.mkdtemp(prefix='meridiana-r628-')
        try:
            done = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'quick.shell.test_finestre_libere_r628.Free'],
                                  cwd=ROOT / 'tests', env=child_env(work), capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=900)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        print('\n'.join(line for line in done.stdout.splitlines() if line.startswith('R628')))
        self.assertEqual(done.returncode, 0, done.stderr[-6000:])


class Free(unittest.TestCase):
    theme = 'light'

    @classmethod
    def setUpClass(cls):
        import os
        if not os.environ.get('R628_INNER'):
            raise unittest.SkipTest('run by Windows, on a screen large enough')
        cls.app = _setup.qt_or_skip()
        from meridiana import i18n
        from meridiana.app import jobs
        from meridiana.gui.application import QuickWindow, create_app
        from quick.aiuti.differential import connected_fixture
        from quick.meridio.support import KeyStore, Voice
        create_app()
        i18n.setup('it')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        with patch('meridiana.gui.backend.assistant_chat.keys', KeyStore()), \
                patch('meridiana.gui.backend.voice.Voice', return_value=Voice()):
            cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True,
                                   theme={'theme': cls.theme, 'reducedMotion': True})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()
        QTest.qWaitForWindowExposed(cls.win)
        ctx = cls.host.engine.rootContext()
        cls.actions = ctx.contextProperty('plantActions')
        cls.part = ctx.contextProperty('filePart')
        cls.host.shell.trigger('phase_plant')
        _setup.wait_for(lambda: cls.win.property('phase') == 'plant', 10000)
        cls.pump(400)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.pump(50)
        cls.folder.cleanup()

    @staticmethod
    def pump(ms=16):
        from quick.gestures import pump
        pump(ms)

    # ---- the windows -------------------------------------------------------------------------------------------
    def find(self, name):
        """A window by its name: its popup, the owner of one of the overlay's items (the plant's windows are made by
        their part, out of the window's tree of objects)."""
        overlay = next(c for c in self.win.contentItem().childItems() if c.metaObject().className() == 'QQuickOverlay')
        for item in overlay.childItems():
            owner = item.parent()
            if owner is not None and owner.objectName() == name:
                return owner
        for root in self.host.engine.rootObjects():
            found = root.findChildren(QObject, name)
            if found:
                return found[0]
        return None

    def open(self, which):
        """The window opened by its part, as the program opens it: its popup and its frame."""
        names = {'catalog': 'plant-catalog-dialog', 'clear': 'plant-clear-dialog', 'ifc': 'fileDialogOverlay'}
        if which == 'ifc':
            self.part.openDialog('ifc')
        else:
            self.actions.open(which)

        def opened():
            dialog = self.find(names[which])
            return dialog is not None and dialog.property('opened')
        self.assertTrue(_setup.wait_for(opened, 5000), which)
        self.pump(200)
        return self.find(names[which])

    def close(self, which, dialog):
        if which == 'ifc':
            self.part.dialogs.cancel()
            self.part.dismissDialog()
        else:
            self.actions.dismiss()
        _setup.wait_for(lambda: not dialog.property('visible'), 5000)
        self.pump(100)

    def frame(self, dialog):
        return rect_of(dialog.property('background'))

    def named(self, dialog, name):
        top = dialog.property('background').parentItem()
        return next((o for o in walk(top) if o.objectName() == name and shown(o)), None)

    # ---- the hand ----------------------------------------------------------------------------------------------
    def press(self, p):
        from quick.gestures import mouse
        mouse(self.app, self.win, QEvent.Type.MouseButtonPress, p, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)

    def move(self, p):
        from quick.gestures import mouse
        mouse(self.app, self.win, QEvent.Type.MouseMove, p, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)

    def release(self, p):
        from quick.gestures import mouse
        mouse(self.app, self.win, QEvent.Type.MouseButtonRelease, p, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    def drag(self, start, dx, dy, steps=12):
        self.press(start)
        self.pump(10)
        end = start
        for i in range(1, steps + 1):
            end = QPointF(start.x() + dx * i / steps, start.y() + dy * i / steps)
            self.move(end)
            self.pump(5)
        self.release(end)
        self.pump(60)

    def centre(self, item):
        return item.mapToScene(QPointF(item.width() / 2, item.height() / 2))

    def head(self, dialog):
        """A point of the head inside the program's window (the window may stand past its sides)."""
        title = self.named(dialog, 'dialogTitle')
        frame, middle = self.frame(dialog), self.centre(title)
        left, right = max(frame.left(), 0) + 8, min(frame.right(), self.win.width()) - 8
        return QPointF(max(left, min(right, middle.x())), middle.y())

    def grip(self, dialog, name):
        item = self.named(dialog, 'dialogGrip' + name)
        self.assertIsNotNone(item, name)
        return item

    # ---- moved -------------------------------------------------------------------------------------------------
    def test_r628_a_window_goes_anywhere_and_keeps_its_head_to_take(self):
        width, height = self.win.width(), self.win.height()
        for which in ('catalog', 'ifc', 'clear'):
            with self.subTest(which=which):
                dialog = self.open(which)
                start = self.frame(dialog)
                self.drag(self.head(dialog), 100, 50)
                moved = self.frame(dialog)
                self.assertAlmostEqual(moved.x() - start.x(), 100, delta=1)
                self.assertAlmostEqual(moved.y() - start.y(), min(50, height - HOLD - start.y()), delta=1)
                self.drag(self.head(dialog), 6000, 4000)
                far = self.frame(dialog)
                self.assertAlmostEqual(far.x(), width - HOLD, delta=1, msg='past the right side, the head to take')
                self.assertAlmostEqual(far.y(), height - min(HOLD, far.height()), delta=1, msg='past the bottom')
                # the program made smaller: the window comes back where it can be taken
                self.win.resize(1000, 640)
                self.pump(200)
                small = self.frame(dialog)
                self.assertLessEqual(small.x(), 1000 - HOLD + 1)
                self.assertLessEqual(small.y(), 640 - min(HOLD, small.height()) + 1)
                self.win.resize(width, height)
                self.pump(200)
                self.drag(self.head(dialog), -8000, -6000)
                near = self.frame(dialog)
                self.assertAlmostEqual(near.right(), HOLD, delta=1, msg='past the left side, the head to take')
                self.assertAlmostEqual(near.y(), 0, delta=1, msg='the head never above the top')
                self.close(which, dialog)
                again = self.frame(self.open(which))
                self.assertAlmostEqual(again.x(), start.x(), delta=1, msg='it opens again where it opened')
                self.assertAlmostEqual(again.y(), start.y(), delta=1)
                self.close(which, dialog)

    # ---- resized -----------------------------------------------------------------------------------------------
    def test_r628_a_window_resizes_from_its_sides_and_corners(self):
        cases = {'Left': (-1, 0), 'Right': (1, 0), 'Top': (0, -1), 'Bottom': (0, 1),
                 'TopLeft': (-1, -1), 'TopRight': (1, -1), 'BottomLeft': (-1, 1), 'BottomRight': (1, 1)}
        for which in ('catalog', 'ifc', 'clear'):
            dialog = self.open(which)
            try:
                for name, (sx, sy) in cases.items():
                    with self.subTest(which=which, grip=name):
                        grip = self.grip(dialog, name)
                        cursor = grip.property('cursorShape')
                        want = (Qt.CursorShape.SizeHorCursor if sy == 0 else Qt.CursorShape.SizeVerCursor if sx == 0
                                else Qt.CursorShape.SizeFDiagCursor if sx == sy else Qt.CursorShape.SizeBDiagCursor)
                        self.assertEqual(cursor, want)
                        before = self.frame(dialog)
                        # outwards by 40 (the room lets it: the window opens in the middle with room round it)
                        self.drag(self.centre(grip), 40 * sx, 40 * sy)
                        after = self.frame(dialog)
                        self.assertAlmostEqual(after.width() - before.width(), 40 * abs(sx), delta=1)
                        self.assertAlmostEqual(after.height() - before.height(), 40 * abs(sy), delta=1)
                        # the sides that were not taken stand still
                        if sx >= 0:
                            self.assertAlmostEqual(after.left(), before.left(), delta=1)
                        if sx <= 0:
                            self.assertAlmostEqual(after.right(), before.right(), delta=1)
                        if sy >= 0:
                            self.assertAlmostEqual(after.top(), before.top(), delta=1)
                        if sy <= 0:
                            self.assertAlmostEqual(after.bottom(), before.bottom(), delta=1)
                        # and inwards by as much: as it was (the next grip has the same room)
                        self.drag(self.centre(grip), -40 * sx, -40 * sy)
                        back = self.frame(dialog)
                        for a, b in ((back.left(), before.left()), (back.top(), before.top()),
                                     (back.right(), before.right()), (back.bottom(), before.bottom())):
                            self.assertAlmostEqual(a, b, delta=1)
                with self.subTest(which=which, case='least'):
                    self.drag(self.centre(self.grip(dialog, 'BottomRight')), -5000, -5000)
                    least = self.frame(dialog)
                    self.assertAlmostEqual(least.width(), dialog.property('leastWidth'), delta=1)
                    self.assertAlmostEqual(least.height(), dialog.property('leastHeight'), delta=1)
                    self.assertGreater(least.width(), 200)
                    self.assertLess(least.height(), 400)
                    self.inside(dialog)
                with self.subTest(which=which, case='most'):
                    self.drag(self.centre(self.grip(dialog, 'TopLeft')), -5000, -5000)
                    self.drag(self.centre(self.grip(dialog, 'BottomRight')), 5000, 5000)
                    most = self.frame(dialog)
                    self.assertAlmostEqual(most.width(), self.win.width(), delta=1, msg='as wide as the program')
                    self.assertAlmostEqual(most.height(), self.win.height(), delta=1, msg='as tall as the program')
                    self.assertAlmostEqual(most.x(), 0, delta=1)
                    self.assertAlmostEqual(most.y(), 0, delta=1)
                    self.inside(dialog)
                with self.subTest(which=which, case='most from past the left side'):
                    QMetaObject.invokeMethod(dialog, 'askedSize')
                    self.pump(50)
                    self.drag(self.head(dialog), -8000, 0)
                    self.assertLess(self.frame(dialog).x(), 0)
                    self.drag(self.centre(self.grip(dialog, 'Right')), 5000, 0)
                    most = self.frame(dialog)
                    self.assertAlmostEqual(most.width(), self.win.width(), delta=1)
                    self.assertAlmostEqual(most.x(), 0, delta=1, msg='as wide as the program: on it')
            finally:
                QMetaObject.invokeMethod(dialog, 'askedSize')
                self.close(which, dialog)

    def inside(self, dialog):
        """The body follows the frame: as tall as the room the head and the foot leave, the buttons at the bottom."""
        frame = self.frame(dialog)
        body = rect_of(self.named(dialog, 'dialogBody'))
        self.assertLessEqual(body.bottom(), frame.bottom() + 1)
        buttons = self.named(dialog, 'dialogButtons')
        if buttons is not None:
            self.assertAlmostEqual(rect_of(buttons).right(), frame.right() - 16, delta=1)
            foot = rect_of(buttons).bottom()
            self.assertAlmostEqual(foot, frame.bottom() - 16, delta=1, msg='the buttons at the bottom')
            self.assertLessEqual(body.bottom(), rect_of(buttons).top())

    def test_r628_the_catalogue_s_list_grows_with_its_window(self):
        dialog = self.open('catalog')
        try:
            catalog = self.named(dialog, 'catalogList')
            self.assertIsNotNone(catalog)
            before = catalog.height()
            self.drag(self.centre(self.grip(dialog, 'Bottom')), 0, 30)
            self.drag(self.centre(self.grip(dialog, 'Top')), 0, -30)
            self.pump(100)
            self.assertAlmostEqual(catalog.height() - before, 60, delta=2, msg='the list takes the height given')
            self.inside(dialog)
        finally:
            QMetaObject.invokeMethod(dialog, 'askedSize')
            self.close('catalog', dialog)

    def test_r628_the_size_is_kept_for_its_kind_and_a_double_click_forgets_it(self):
        dialog = self.open('catalog')
        asked = self.frame(dialog)
        self.drag(self.centre(self.grip(dialog, 'BottomRight')), -120, -90)
        chosen = self.frame(dialog)
        self.assertAlmostEqual(chosen.width(), asked.width() - 120, delta=1)
        self.close('catalog', dialog)
        dialog = self.open('catalog')
        again = self.frame(dialog)
        self.assertAlmostEqual(again.width(), chosen.width(), delta=1, msg='kept for its kind')
        self.assertAlmostEqual(again.height(), chosen.height(), delta=1)
        # saved with the window's arrangement, and read back
        saved = self.win.savedLayout().toVariant()
        self.assertEqual(saved['dialogs']['plant-catalog-dialog'], [round(chosen.width()), round(chosen.height())])
        self.host.layout_state.save()
        data = json.loads(self.host.layout_state.path.read_text(encoding='utf8'))
        self.assertEqual(data['dialogs']['plant-catalog-dialog'], [round(chosen.width()), round(chosen.height())])
        # a double click on a grip: the size it asks, forgotten
        grip = self.grip(dialog, 'Right')
        QTest.mouseDClick(self.win, Qt.MouseButton.LeftButton, pos=self.centre(grip).toPoint())
        self.pump(100)
        back = self.frame(dialog)
        self.assertAlmostEqual(back.width(), asked.width(), delta=1)
        self.assertAlmostEqual(back.height(), asked.height(), delta=1)
        self.assertNotIn('plant-catalog-dialog', self.win.savedLayout().toVariant()['dialogs'])
        self.close('catalog', dialog)
        # each kind its own: the IFC import was not touched
        dialog = self.open('ifc')
        self.assertIsNone(dialog.property('chosen').width() or None)
        self.close('ifc', dialog)

    # ---- Meridio over a window ---------------------------------------------------------------------------------
    def test_r628_meridio_is_usable_over_a_window(self):
        from quick.meridio.support import Provider
        chat = self.host.parts.controllers['assistant']
        chat.cfg.assistant_local_model = 'fake'
        chat.cfg.assistant_introduced = True
        fake = Provider(text='Risposta.')
        chat.make_local = lambda: fake
        layer = self.win.findChild(QObject, 'assistantLayer')
        avatar = layer.findChild(QObject, 'assistantCharacter')
        for which in ('catalog', 'ifc', 'clear'):
            with self.subTest(which=which):
                self.meridio_over(which, chat, fake, layer, avatar)

    def meridio_over(self, which, chat, fake, layer, avatar):
        dialog = self.open(which)
        self.assertTrue(dialog.property('modal'))
        self.assertTrue(shown(avatar), 'his figure over the window')
        self.assertGreater(avatar.mapToScene(QPointF(0, 0)).y(), 0)
        # a click on him opens his bubble, over the window
        QTest.mouseClick(self.win, Qt.MouseButton.LeftButton, pos=self.centre(avatar).toPoint())
        self.assertTrue(_setup.wait_for(lambda: layer.property('opened'), 3000), 'the click reached him')
        question = layer.findChild(QObject, 'assistantQuestion')
        self.assertTrue(_setup.wait_for(lambda: question.hasActiveFocus(), 3000), 'his question has the keyboard')
        for char in 'ciao':
            QTest.keyClick(self.win, char)
        self.assertEqual(question.property('text'), 'ciao')
        self.assertTrue(dialog.property('keyboardAway'))
        # Return in his field: his question goes, the window's button is not pressed
        asked = len(fake.requests)
        QTest.keyClick(self.win, Qt.Key.Key_Return)
        self.assertTrue(_setup.wait_for(lambda: len(fake.requests) > asked and not chat.busy, 5000))
        self.assertTrue(dialog.property('visible'), 'Return in his bubble does not press the window')
        # Esc in his field closes his bubble, not the window, and the window has the keyboard again
        QTest.keyClick(self.win, Qt.Key.Key_Escape)
        self.assertTrue(_setup.wait_for(lambda: not layer.property('opened'), 3000))
        self.pump(100)
        self.assertTrue(dialog.property('visible'), 'Esc in his bubble does not close the window')
        self.assertTrue(_setup.wait_for(lambda: not dialog.property('keyboardAway')
                                        and dialog.property('keyboardOver') is None, 3000),
                        'the keyboard back to the window')
        # dragged, he moves
        was = (layer.property('avatarX'), layer.property('avatarY'))
        self.drag(self.centre(avatar), -80, -40)
        self.assertTrue(_setup.wait_for(lambda: (layer.property('avatarX'), layer.property('avatarY')) != was, 3000),
                        'he moves over the window')
        self.assertTrue(dialog.property('visible'))
        # Esc with the keyboard in the window closes it
        QTest.keyClick(self.win, Qt.Key.Key_Escape)
        self.assertTrue(_setup.wait_for(lambda: not dialog.property('visible'), 3000), 'Esc in the window closes it')
        if which == 'ifc':
            self.part.dialogs.cancel()
            self.part.dismissDialog()
        else:
            self.actions.dismiss()
        self.pump(150)

    def test_r628_a_window_of_meridio_s_stands_over_him_and_menus_over_both(self):
        from meridiana.gui.style import design
        stage = self.win.findChild(QObject, 'assistantStage')
        self.assertIsNotNone(stage)
        self.assertEqual(stage.property('z'), design.Stack.ASSISTANT)
        self.assertFalse(stage.property('modal'))
        self.assertTrue(stage.property('visible'))
        dialog = self.open('clear')
        try:
            self.assertEqual(dialog.property('z'), design.Stack.WINDOW)
        finally:
            self.close('clear', dialog)
        s = design.Stack
        self.assertLess(s.WINDOW, s.ASSISTANT)
        self.assertLess(s.ASSISTANT, s.ASSISTANT_WINDOW)
        self.assertLess(s.ASSISTANT_WINDOW, s.POPUP)

    # ---- the beat ----------------------------------------------------------------------------------------------
    @timed('no call of the window over its few ms')
    def test_r628_the_catalogue_resizes_without_steps(self):
        from quick.aiuti.finestra_libera import window_stays_free
        dialog = self.open('catalog')
        try:
            self.pump(500)
            steps = 40

            def steps_of(start, dx, dy):
                """The time of each step: the move given and the frame drawn with it."""
                times = []
                self.press(start)
                self.pump(20)
                drawn = []

                def frame():
                    drawn.append(1)
                self.win.frameSwapped.connect(frame)
                for i in range(1, steps + 1):
                    t = time.perf_counter()
                    drawn.clear()
                    self.move(QPointF(start.x() + dx * i / steps, start.y() + dy * i / steps))
                    _setup.wait_for(lambda: bool(drawn), 2000)
                    times.append((time.perf_counter() - t) * 1000)
                self.win.frameSwapped.disconnect(frame)
                self.release(QPointF(start.x() + dx, start.y() + dy))
                self.pump(100)
                return times
            moves = steps_of(self.head(dialog), -120, -80)
            # inwards, every step a new size (outwards the room ends, and a step with nothing to draw draws no frame)
            with window_stays_free(self.host.work.center, call_ms=5, beat_ms=None) as seen:
                sizes = steps_of(self.centre(self.grip(dialog, 'BottomRight')), -400, -240)
            moved, resized = statistics.median(moves), statistics.median(sizes)
            print(f"\nR628 the catalogue: a step moved {moved:.1f} ms (longest {max(moves):.1f}), resized {resized:.1f} ms "
                  f"(longest {max(sizes):.1f}); {seen}")
            Free.measures = dict(moved=moved, resized=resized, moved_max=max(moves), resized_max=max(sizes),
                                 beat=seen.beat_ms)
            # the window follows the hand at every step: a resize costs about what a move costs, never a second
            self.assertLess(resized, max(3 * moved, moved + 30), (moves, sizes))
        finally:
            QMetaObject.invokeMethod(dialog, 'askedSize')
            self.close('catalog', dialog)


def shots(folder, theme):
    """The pictures: the catalogue moved to a corner, made small and large, with Meridio open over it."""
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    Free.theme = theme
    Free.setUpClass()
    case = Free('test_r628_a_window_goes_anywhere_and_keeps_its_head_to_take')
    try:
        dialog = case.open('catalog')
        Free.win.grabWindow().save(str(out / f'catalogo-aperto-{theme}.png'))
        case.drag(case.head(dialog), 4000, 3000)
        Free.win.grabWindow().save(str(out / f'catalogo-angolo-{theme}.png'))
        case.drag(case.head(dialog), -8000, -6000)
        Free.win.grabWindow().save(str(out / f'catalogo-oltre-sinistra-{theme}.png'))
        case.close('catalog', dialog)
        dialog = case.open('catalog')
        case.drag(case.centre(case.grip(dialog, 'BottomRight')), -5000, -5000)
        Free.win.grabWindow().save(str(out / f'catalogo-piccolo-{theme}.png'))
        case.drag(case.centre(case.grip(dialog, 'TopLeft')), -5000, -5000)
        case.drag(case.centre(case.grip(dialog, 'BottomRight')), 5000, 5000)
        Free.win.grabWindow().save(str(out / f'catalogo-grande-{theme}.png'))
        QTest.mouseDClick(Free.win, Qt.MouseButton.LeftButton, pos=case.centre(case.grip(dialog, 'Right')).toPoint())
        Free.pump(200)
        layer = Free.win.findChild(QObject, 'assistantLayer')
        layer.open()
        Free.pump(400)
        question = layer.findChild(QObject, 'assistantQuestion')
        question.forceActiveFocus()
        for char in 'Che inverter scelgo?':
            QTest.keyClick(Free.win, char)
        Free.pump(200)
        Free.win.grabWindow().save(str(out / f'catalogo-meridio-{theme}.png'))
    finally:
        Free.tearDownClass()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'shot':
        import subprocess
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as work:
            subprocess.run([sys.executable, __file__, 'shot-inner', str(Path(sys.argv[2]).resolve()),
                            sys.argv[3] if len(sys.argv) > 3 else 'light'], cwd=ROOT / 'tests', env=child_env(work), check=True)
    elif len(sys.argv) > 1 and sys.argv[1] == 'shot-inner':
        shots(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
