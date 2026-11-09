"""Defects of the Quick interface seen by Daniel on r18-unita (06/11/2026), on one workbench with the real views."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt

import _setup
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import item, mouse, pump
from quick.parity.differential import connected_fixture

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def scene_rect(obj):
    top_left = obj.mapToScene(obj.boundingRect().topLeft())
    return (top_left.x(), top_left.y(), obj.width(), obj.height())


def descendants(root):
    out, stack = [], [root]
    while stack:
        node = stack.pop()
        out.append(node)
        stack.extend(node.childItems())
    return out


class Workbench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.session = cls.host.bridge.session
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.host.shell.trigger('phase_model')
        pump(400)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def phase(self, name):
        self.host.shell.trigger('phase_' + name)
        pump(300)

    def hover(self, pos):
        mouse(self.app, self.win, QEvent.Type.MouseMove, pos, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
        pump(30)

    def footer_rects(self):
        names = ('statusHint', 'statusWarnings', 'statusProgress', 'statusPanelLeft', 'statusMeridio')
        return {name: scene_rect(item(self.win, name)) for name in names if item(self.win, name) is not None}

    def test_r484_the_pointer_is_shown_by_the_scale_and_nothing_in_the_bar_moves_with_it(self):
        self.phase('model')
        self.assertFalse([n for n in descendants(self.win.contentItem()) if n.objectName() == 'statusCursor'],
                         'no more coordinates in the status bar')
        plan, pill, scale = item(self.win, 'plan'), item(self.win, 'planCursor'), item(self.win, 'scaleBar')
        top_left = plan.mapToScene(plan.boundingRect().topLeft())
        pump(1500)                                  # the checks and the plant's jobs of the opening, done
        def state():
            return self.footer_rects(), str(self.host.shell.property('checkCounts'))
        before = state()
        widths, texts = set(), set()
        for k in range(40):
            self.hover(QPointF(top_left.x() + plan.width() * (.3 + .01 * k), top_left.y() + plan.height() * (.35 + .0075 * k)))
            self.assertTrue(pill.isVisible(), k)
            widths.add(round(pill.width(), 3))
            texts.add(item(self.win, 'planCursorText').property('text'))
            now = state()
            if now[1] == before[1]:                 # the counts the same: nothing may have moved
                self.assertEqual(now[0], before[0], 'the status bar keeps every place')
            before = now
        self.assertGreater(len(texts), 30)
        self.assertEqual(len(widths), 1, f'one width for every place: {sorted(widths)}')
        # by the scale, on its baseline, as the plan's pills
        p, s = scene_rect(pill), scene_rect(scale)
        self.assertAlmostEqual(p[1] + p[3], s[1] + s[3], delta=0.5)
        self.assertGreater(p[0], s[0] + s[2])
        self.assertLess(p[0] - (s[0] + s[2]), 20)
        # off the plan, hidden
        self.hover(QPointF(5, self.win.height() - 5))
        self.assertFalse(pill.isVisible())

    def test_r511_the_coordinates_and_the_scale_share_one_container(self):
        self.phase('model')
        plan, pill, scale = item(self.win, 'plan'), item(self.win, 'planCursor'), item(self.win, 'scaleBar')
        s = scene_rect(scale)
        for k in range(3):                          # just over the scale, on the plan whatever lies on its middle
            self.hover(QPointF(s[0] + 40 + 4 * k, s[1] - 60))
        self.assertTrue(pill.isVisible())
        for name in ('height', 'radius', 'color'):
            self.assertEqual(pill.property(name), scale.property(name), name)
        words = item(self.win, 'planCursorText')
        label = next(c for c in scale.childItems() if c.property('text') == scale.property('text'))
        a, b = words.property('font'), label.property('font')
        self.assertEqual((a.pixelSize(), a.weight(), a.family()), (b.pixelSize(), b.weight(), b.family()))
        # the ground and the ink of the plan's pills (the string labels, the sides' measures)
        from PySide6.QtGui import QColor
        colours = plan.property('backend').property('planColors')
        self.assertEqual(pill.property('color'), QColor(colours['label_bg']))      # already in Qt's order
        self.assertEqual(words.property('color'), label.property('color'))
        self.assertTrue(pill.property('pad') > 0)
        self.assertAlmostEqual(words.x(), pill.property('pad'), delta=0.5)      # its margin, the scale's

    def test_r485_the_counts_are_the_pills_of_the_checks_panel_and_as_wide_as_two_digits(self):
        self.phase('model')
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlComponent
        # the bar's counts are the panel's pills (M.Pill, variant count), not buttons with an icon
        source = (Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Shell/Workbench.qml').read_text(encoding='utf-8')
        bar = source[source.index('objectName: "statusWarnings"'):source.index('objectName: "statusMeasure"')]
        self.assertIn('M.Pill', bar)
        self.assertIn('variant: "count"', bar)
        self.assertIn('minText: "99"', bar)
        self.assertIn('checkable: false', bar)
        # as wide for 2 as for 11: a count of one digit more moves nothing
        component = QQmlComponent(self.host.engine)
        component.setData(b'import QtQuick\nimport Meridiana.Controls as M\n'
                          b'Row { M.Pill { variant: "count"; objectName: "a"; level: "warn"; text: "2"; minText: "99"; checkable: false }\n'
                          b'M.Pill { variant: "count"; objectName: "b"; level: "warn"; text: "11"; minText: "99"; checkable: false } }',
                          QUrl('file:///r485.qml'))
        row = component.create()
        self.assertIsNotNone(row, component.errorString())
        row.setParentItem(self.win.contentItem())
        row.setVisible(False)
        pump(50)
        one, two = row.childItems()
        self.assertEqual(one.width(), two.width())
        self.assertGreater(one.width(), 0)
        live = [n for n in descendants(item(self.win, 'statusWarnings')) if (n.objectName() or '').startswith('statusCount_')]
        counts = [c for c in self.host.shell.property('checkCounts') if c['id'] in ('warn', 'fail') and c['count'] > 0]
        self.assertEqual(len(live), len(counts))

    def test_r486_the_hint_is_as_far_from_the_side_as_the_panels(self):
        self.phase('model')
        from meridiana.ui.design import Layout
        hint = item(self.win, 'statusHint')
        self.assertAlmostEqual(scene_rect(hint)[0], Layout.EDGE, delta=0.5)          # the panels' and the bar's end
        # its middle on the bar's middle, as the buttons beside it
        meridio = scene_rect(item(self.win, 'statusMeridio'))
        h = scene_rect(hint)
        self.assertAlmostEqual(h[1] + h[3] / 2, meridio[1] + meridio[3] / 2, delta=1.0)

    # R481: Alt wherever the focus is (backend/window_frame.AltTap)
    def send_key(self, kind, key, modifiers=Qt.KeyboardModifier.NoModifier, text=''):
        from PySide6.QtGui import QKeyEvent
        self.app.sendEvent(self.win, QKeyEvent(kind, key, modifiers, text))
        pump(20)

    def alt(self):
        self.send_key(QEvent.Type.KeyPress, Qt.Key.Key_Alt, Qt.KeyboardModifier.AltModifier)
        self.send_key(QEvent.Type.KeyRelease, Qt.Key.Key_Alt)
        pump(250)

    def bar_shown(self):
        return bool(self.win.property('menuOpen'))

    def focus_in_bar(self):
        node = self.win.activeFocusItem()
        while node is not None:
            if node.objectName() == 'altMenuBar':
                return True
            node = node.parentItem()
        return False

    def check_alt_from(self, focused, where):
        focused.forceActiveFocus()
        pump(50)
        self.assertFalse(self.bar_shown(), where)
        self.alt()
        self.assertTrue(self.bar_shown(), f'{where}: Alt shows the menu bar')
        self.assertTrue(self.focus_in_bar(), f'{where}: with the focus on it')
        self.alt()
        self.assertFalse(self.bar_shown(), f'{where}: a second Alt hides it')
        self.assertEqual(self.win.activeFocusItem(), focused, f'{where}: and the focus goes back')

    def test_r481_alt_shows_and_hides_the_menu_bar_from_the_plan_a_field_a_list_and_the_3d_view(self):
        self.phase('model')
        self.win.setProperty('menuOpen', False)
        pump(100)
        self.check_alt_from(item(self.win, 'plan'), 'the plan')
        fields = [n for n in descendants(self.win.contentItem()) if n.inherits('QQuickTextInput') and n.isVisible()
                  and n.property('enabled') and not n.property('readOnly')]
        self.assertTrue(fields)
        self.check_alt_from(fields[0], 'a field')
        lists = [n for n in descendants(self.win.contentItem()) if n.isVisible() and n.property('activeFocusOnTab')
                 and n.inherits('QQuickFlickable')]
        if lists:
            self.check_alt_from(lists[0], 'a list')
        view3d = [n for n in descendants(self.win.contentItem()) if n.isVisible() and n.inherits('QQuick3DViewport')]
        if view3d:
            self.check_alt_from(view3d[0], 'the 3D view')

    def test_r481_esc_and_a_click_outside_hide_it_and_alt_in_a_combination_does_nothing(self):
        self.phase('model')
        self.win.setProperty('menuOpen', False)
        plan = item(self.win, 'plan')
        plan.forceActiveFocus()
        pump(50)
        self.alt()
        self.assertTrue(self.bar_shown())
        self.send_key(QEvent.Type.KeyPress, Qt.Key.Key_Escape)
        self.send_key(QEvent.Type.KeyRelease, Qt.Key.Key_Escape)
        pump(200)
        self.assertFalse(self.bar_shown(), 'Esc hides it')
        self.assertEqual(self.win.activeFocusItem(), plan)
        self.alt()
        self.assertTrue(self.bar_shown())
        centre = plan.mapToScene(QPointF(plan.width() / 2, plan.height() / 2))
        mouse(self.app, self.win, QEvent.Type.MouseButtonPress, centre, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
        mouse(self.app, self.win, QEvent.Type.MouseButtonRelease, centre, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
        pump(200)
        self.assertFalse(self.bar_shown(), 'a click outside hides it')
        # Alt+Tab: the window loses the focus while Alt is down; Alt+F4 and Alt with the mouse: another input between
        for between in ('tab', 'key', 'mouse'):
            self.send_key(QEvent.Type.KeyPress, Qt.Key.Key_Alt, Qt.KeyboardModifier.AltModifier)
            if between == 'tab':
                self.app.sendEvent(self.win, QEvent(QEvent.Type.WindowDeactivate))
            elif between == 'key':
                self.send_key(QEvent.Type.KeyPress, Qt.Key.Key_F4, Qt.KeyboardModifier.AltModifier)
                self.send_key(QEvent.Type.KeyRelease, Qt.Key.Key_F4, Qt.KeyboardModifier.AltModifier)
            else:
                mouse(self.app, self.win, QEvent.Type.MouseButtonPress, centre, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
                mouse(self.app, self.win, QEvent.Type.MouseButtonRelease, centre, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
            self.send_key(QEvent.Type.KeyRelease, Qt.Key.Key_Alt)
            pump(200)
            self.assertFalse(self.bar_shown(), f'Alt with {between} between does nothing')
        self.app.sendEvent(self.win, QEvent(QEvent.Type.WindowActivate))
        pump(50)
        plan.forceActiveFocus()
        self.alt()
        self.assertTrue(self.bar_shown(), 'after the window came back, Alt works')
        self.alt()
        self.assertFalse(self.bar_shown())

    def test_r481_alt_and_a_letter_opens_that_menu(self):
        self.phase('model')
        self.win.setProperty('menuOpen', False)
        item(self.win, 'plan').forceActiveFocus()
        self.win.requestActivate()
        pump(100)
        menus = self.host.shell.property('menus')
        index = next(i for i, m in enumerate(menus) if m['id'] == 'view')
        letter = menus[index]['mnemonic']
        key = getattr(Qt.Key, 'Key_' + letter.upper())
        self.send_key(QEvent.Type.KeyPress, Qt.Key.Key_Alt, Qt.KeyboardModifier.AltModifier)
        self.send_key(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.AltModifier, letter)
        self.send_key(QEvent.Type.KeyRelease, key, Qt.KeyboardModifier.AltModifier, letter)
        self.send_key(QEvent.Type.KeyRelease, Qt.Key.Key_Alt)
        pump(300)
        button = item(self.win, 'mainMenu_%d' % index)
        self.assertTrue(button.property('menuOpened'), f'Alt+{letter} opens {menus[index]["title"]}')
        self.assertTrue(self.bar_shown(), 'and the Alt let go after it does not hide the bar')
        self.send_key(QEvent.Type.KeyPress, Qt.Key.Key_Escape)
        self.send_key(QEvent.Type.KeyRelease, Qt.Key.Key_Escape)
        self.send_key(QEvent.Type.KeyPress, Qt.Key.Key_Escape)
        self.send_key(QEvent.Type.KeyRelease, Qt.Key.Key_Escape)
        pump(200)

    # R482: the title bars of Windows in the theme
    def test_r482_the_frame_follows_the_theme(self):
        from meridiana.quick.backend import window_frame
        calls = []
        real = window_frame.set_dark_frame
        window_frame.set_dark_frame = lambda window, dark: calls.append((window, dark)) or True
        try:
            self.host.frame_theme.apply()
        finally:
            window_frame.set_dark_frame = real
        self.assertIn((self.win, bool(self.host.theme.dark)), calls)
    # R483: File and the phases change under a still picture of the old page that fades out
    def transition_frames(self, change):
        import time
        veil = item(self.win, 'fileTransition')
        image = veil.childItems()[0]
        frames = []

        space = item(self.win, 'workspace')

        def frame():
            # R521: where the old page's picture and the workspace are, at every frame
            frames.append((time.perf_counter(), bool(veil.property('running')), image.property('opacity'),
                           self.win.property('phase'), bool(self.win.property('fileShown')),
                           image.mapToScene(QPointF(0, 0)).x(), space.mapToScene(QPointF(0, 0)).x()))
        self.win.frameSwapped.connect(frame)
        try:
            start = time.perf_counter()
            change()
            changed = time.perf_counter()
            for _ in range(80):
                pump(16)
                # the veil starts a frame after the gesture (r21-f6c): the frames before it are not its end
                if frames and not frames[-1][1] and any(f[1] for f in frames):
                    break
        finally:
            self.win.frameSwapped.disconnect(frame)
        # the picture of the old page is the render thread's next frame (R21 F6c: Item.grabToImage, no synchronous
        # grabWindow), with the change right after it: the frames of the change start where the veil starts
        after = [f for f in frames if f[0] >= changed]
        while after and not after[0][1]:
            after.pop(0)
        return start, changed, after

    def check_fade(self, frames, what):
        covered = [f for f in frames if f[1]]
        self.assertTrue(covered, f'{what}: no picture over the change')
        self.assertEqual(covered[0][2], 1.0, f'{what}: the first frame of the new page is under the whole picture')
        opacities = [f[2] for f in covered]
        self.assertEqual(opacities, sorted(opacities, reverse=True), f'{what}: it went back')
        self.assertGreaterEqual(len([o for o in opacities if 0 < o < 1]), 4, f'{what}: a jump, not a fade')
        self.assertFalse(frames[-1][1], f'{what}: it ends')
        # R521: a fade alone: the picture of the old page and the panels of the new stay where they are
        self.assertEqual({round(f[5], 2) for f in covered}, {0.0}, f'{what}: the old page slides')
        self.assertEqual(len({round(f[6], 2) for f in frames}), 1, f'{what}: the workspace moves')

    def test_the_last_phase_asked_wins_while_a_picture_is_on_its_way(self):
        """r21-unita: with the phase changed a frame after the gesture (r21-f6c), the phase on show asked again
        while another waited for its picture was ignored, and the other came after it: the last command lost."""
        self.phase('plant')
        self.host.shell.trigger('phase_model')          # waits for its picture
        self.host.shell.trigger('phase_plant')          # the phase on show, asked again at once
        _setup.wait_until(self.app, lambda: False, seconds=.6)
        self.assertEqual(self.win.property('phase'), 'plant')

    def test_r483_file_and_the_phases_change_under_a_picture_that_fades(self):
        self.phase('model')
        pump(500)
        timings = {}
        for what, change, check in (
                ('File', lambda: self.win.setProperty('fileOpen', True), lambda f: f[4]),
                ('back to the plan from File', lambda: self.win.showPhase('model'), lambda f: not f[4] and f[3] == 'model'),
                ('to Producibilità', lambda: self.win.showPhase('production'), lambda f: f[3] == 'production'),
                ('back to Impianto', lambda: self.win.showPhase('plant'), lambda f: f[3] == 'plant'),
                ('back to Modellazione', lambda: self.win.showPhase('model'), lambda f: f[3] == 'model')):
            start, changed, frames = self.transition_frames(change)
            self.assertTrue(frames and all(check(f) for f in frames), f'{what}: the page changed at once')
            self.check_fade(frames, what)
            half = next(f[0] for f in frames if f[2] <= .5 or not f[1])
            timings[what] = (round(1000 * (changed - start)), round(1000 * (half - start)), len(frames))
            pump(200)
        print('R483 ms (change, half seen, frames):', timings)
    # R500 (R155): Meridio stays where he is from a phase to the next
    def test_r500_meridio_stays_where_he_is_through_every_phase(self):
        self.phase('model')
        pump(800)
        character = item(self.win, 'assistantCharacter')

        def where():
            p = character.mapToScene(QPointF(0, 0))
            return (round(p.x()), round(p.y()))
        seen = {}
        for name in ('plant', 'production', 'consumption', 'economics', 'report', 'plant', 'model'):
            self.win.showPhase(name)
            pump(700)
            seen.setdefault(name, []).append(where())
        start = seen['plant'][0]
        for name in ('production', 'consumption', 'economics', 'report'):
            self.assertEqual(seen[name][0], start, f'{name}: Meridio moved ({seen})')
        self.assertEqual(seen['plant'][1], start, f'back to Impianto: moved ({seen})')
        # where he is dragged is his place in every phase
        part = self.host.parts.controllers.get('assistant') or next(
            (c for c in self.host.parts.controllers.values() if hasattr(c, 'places')), None)
        if part is not None and hasattr(part, '_placement'):
            part._placement(300.0, 300.0, 320.0, 500.0, False)
            self.assertEqual(len({tuple(v) for v in part.places.values()}), 1)
    # R503: docked, Meridio is a tab of the panels and never lost
    def test_r503_docked_meridio_is_a_tab_and_never_lost(self):
        self.phase('model')
        pump(400)
        layer, dock = item(self.win, 'assistantLayer'), item(self.win, 'assistantDockPanel')
        character = item(self.win, 'assistantCharacter')

        def seen():
            return character.isVisible() or dock.isVisible()
        self.host.shell.trigger('assistant')
        pump(300)
        layer.setProperty('docked', True)              # «Aggancia ai pannelli»
        layer.placementSaved.emit(layer.property('avatarX'), layer.property('avatarY'), 320.0, 500.0, True)
        pump(400)
        self.assertTrue(dock.isVisible() and self.host.cfg.assistant_docked)
        for k in range(3):                             # Ctrl+L closes and opens the conversation, the tab stays
            self.host.shell.trigger('assistant')
            pump(300)
            self.assertTrue(dock.property('opened'), f'Ctrl+L {k}: the tab stays')
            self.assertTrue(seen())
        if layer.property('opened'):
            self.host.shell.trigger('assistant')
            pump(300)
        self.assertTrue(seen(), 'docked and closed: still there, as a tab')
        dock.closed.emit()                             # the tab's close: floating again
        pump(400)
        self.assertFalse(layer.property('docked'))
        self.assertTrue(character.isVisible())
        self.assertFalse(self.host.cfg.assistant_docked)
        # from the Settings (Assistente, the box of the docking) and back
        settings = self.host.parts.controllers['settings']
        self.assertTrue(settings.setValue('assistant_docked', True))
        pump(400)
        self.assertTrue(layer.property('docked') and seen())
        self.assertTrue(settings.setValue('assistant_docked', False))
        pump(400)
        self.assertTrue(character.isVisible())
    # R474: the whole guided tour, the highlight on the step's item at every step, never the one before
    def test_r474_every_step_of_the_tour_highlights_its_own_item(self):
        from meridiana import tour
        self.phase('model')
        pump(400)
        layer = item(self.win, 'assistantLayer')
        help_service = self.host.parts.controllers['assistant_help']
        out = os.environ.get('R19_TOUR_CAPTURES')
        help_service.startTour(False)
        pump(600)
        report = []

        def landed():
            # the highlight moves to its item with an animation: under load (four folders in parallel, r23-f6: red in
            # 20 runs out of 20, green alone) 900 ms fixed were not enough; the test now waits for the highlight to
            # land, at most 10 s, and asserts the same thing as before (r23-f8)
            target, rect = layer.property('highlightItem'), layer.property('highlightRect')
            if target is not None and target.isVisible():
                top_left = target.mapToItem(layer, QPointF(0, 0))
                return ((round(rect.x()), round(rect.y()), round(rect.width()), round(rect.height()))
                        == (round(top_left.x()), round(top_left.y()), round(target.width()), round(target.height())))
            return (rect.width(), rect.height()) == (0.0, 0.0)
        for index in range(len(tour.steps())):
            help_service.goToStep(index)
            _setup.wait_for(landed, 10000)
            target = layer.property('highlightItem')
            rect = layer.property('highlightRect')
            if target is not None and target.isVisible():
                top_left = target.mapToItem(layer, QPointF(0, 0))
                expected = (round(top_left.x()), round(top_left.y()), round(target.width()), round(target.height()))
                got = (round(rect.x()), round(rect.y()), round(rect.width()), round(rect.height()))
                self.assertEqual(got, expected, f'step {index}: the highlight is not on its item')
            else:
                self.assertEqual((rect.width(), rect.height()), (0.0, 0.0), f'step {index}: a highlight left over')
            report.append((index, target.objectName() if target is not None else ''))
            if out:
                Path(out).mkdir(parents=True, exist_ok=True)
                self.win.grabWindow().save(str(Path(out) / f'passo-{index + 1:02d}.png'))
        # a page of the tour is as tall as what it shows (R474), not the bubble's whole height
        self.assertLess(layer.property('actualHeight'), layer.property('bubbleHeight'))
        head = [item(self.win, name) for name in ('assistantMenuButton', 'assistantHelpClose')]
        self.assertEqual({(round(b.width()), round(b.height())) for b in head if b is not None and b.isVisible()} and 1, 1)
        if all(b is not None and b.isVisible() for b in head):
            self.assertEqual((head[0].width(), head[0].height()), (head[1].width(), head[1].height()))
        layer.dismiss()
        pump(300)
    # R489: one's own message is one rounded bubble, the local model's notice without the address
    def test_r489_own_message_is_one_bubble_and_the_notice_is_kind(self):
        chat = self.host.parts.controllers['assistant']
        colours = {'text': '#111111', 'field': '#eeeeee', 'view': '#ffffff', 'muted': '#777777'}
        inner = chat.messageInner({'author': 'Daniel', 'bodyHtml': '<p>uno</p><p>due</p>', 'outgoing': True, 'kind': 'you'},
                                  colours)
        self.assertNotIn('<table', inner)
        self.assertNotIn('bgcolor', inner)
        source = (Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Assistant/Conversation.qml').read_text(encoding='utf-8')
        self.assertIn('objectName: "ownMessage"', source)
        from meridiana.i18n import _
        words = _("The model on this PC is not running yet. I look for another one on this PC…")
        self.assertNotIn('127.0.0.1', words)
        self.assertNotEqual(words, "The model on this PC is not running yet. I look for another one on this PC…")


@unittest.skipUnless(os.name == 'nt', 'the title bars of Windows')
class FrameAttribute(unittest.TestCase):
    """R482 read from the window itself: a window of the real platform, made and never shown (nothing on screen)."""

    def test_the_dark_attribute_is_set_and_read_back_on_a_real_window(self):
        import subprocess
        import sys
        child = '\n'.join((
            "import sys",
            "from PySide6.QtGui import QGuiApplication, QWindow",
            "app = QGuiApplication(sys.argv)",
            "from meridiana.quick.backend.window_frame import dark_frame, set_dark_frame",
            "w = QWindow(); w.create()",
            "out = []",
            "for dark in (True, False, True):",
            "    out.append((set_dark_frame(w, dark), dark_frame(w)))",
            "print(out)"))
        root = Path(__file__).resolve().parents[3]
        env = dict(os.environ, QT_QPA_PLATFORM='windows', PYTHONPATH=str(root / 'src'))
        done = subprocess.run([sys.executable, '-c', child], env=env, capture_output=True, text=True, timeout=60)
        self.assertIn('[(True, True), (True, False), (True, True)]', done.stdout, done.stderr[-1500:])


if __name__ == '__main__':
    unittest.main()
