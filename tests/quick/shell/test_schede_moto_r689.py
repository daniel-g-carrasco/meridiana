"""Frame geometry contracts for carrying and docking every shared panel."""
import json
import random
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QKeyEvent

from _fixtures import capannone
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import item, mouse, point, pump, wait_for

setUpModule = _setup.keep_global_state


def geometry(obj):
    return (obj.x(), obj.y(), obj.width(), obj.height())


class PanelMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.host = QuickWindow(capannone(), Path(self.folder.name),
                                theme={'reducedMotion': False})
        self.host.bridge.configure_background(enabled=False)
        self.win = self.host.window
        self.win.show()
        self.win.resize(1600, 960)
        pump(600)
        self.ws = item(self.win, 'workspace')
        self.panel = item(self.win, 'checksPanel')

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        pump(50)
        self.folder.cleanup()
        self.assertEqual(warnings, [])

    def carry(self, x, y, panel_id='checks'):
        start = point(item(self.win, panel_id+'TitleDrag'))
        self.at = point(self.ws, x, y)
        mouse(self.app, self.win, QEvent.Type.MouseButtonPress, start,
              Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
        mouse(self.app, self.win, QEvent.Type.MouseMove, self.at,
              Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        pump(16)

    def release(self):
        mouse(self.app, self.win, QEvent.Type.MouseButtonRelease, self.at,
              Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    def test_floating_release_preserves_carried_size(self):
        before = geometry(self.panel)[2:]
        self.carry(self.ws.width()/2, self.ws.height()/2)
        self.assertEqual(geometry(item(self.win, 'cardLift'))[2:], before)
        self.release()
        for _ in range(30):
            pump(16)
            self.assertEqual(geometry(self.panel)[2:], before)

    def test_views_reflow_continuously_on_floating_release(self):
        central = item(self.win, 'centralPanel')
        before = geometry(central)
        self.carry(self.ws.width()/2, self.ws.height()/2)
        samples = [before]
        self.release()
        samples.append(geometry(central))
        for _ in range(32):
            pump(16)
            samples.append(geometry(central))
        delta = samples[-1][3]-before[3]
        self.assertGreater(delta, 100)
        jumps = [abs(b[3]-a[3]) for a, b in zip(samples, samples[1:], strict=False)]
        self.assertLess(max(jumps), delta*0.6)

    def test_empty_bottom_outline_excludes_the_properties_column(self):
        self.carry(self.ws.width()/2, self.ws.height()/2)
        self.release()
        pump(500)
        self.carry(self.ws.width()/2, self.ws.height()-10)
        outline = geometry(item(self.win, 'dropOutline'))
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        pump(450)
        preview = geometry(item(self.win, 'dropZone'))
        self.release()
        pump(500)
        final = geometry(self.panel)
        for a, b in zip(outline, final, strict=True):
            self.assertAlmostEqual(a, b, delta=1)
        for a, b in zip(preview, final, strict=True):
            self.assertAlmostEqual(a, b, delta=1)

    def test_release_keeps_the_picture_at_the_last_pointer_position(self):
        self.carry(10, self.ws.height()/2)
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        pump(450)
        lift = item(self.win, 'cardLift')
        before = geometry(lift)
        self.release()
        self.assertTrue(lift.isVisible())
        self.assertEqual(geometry(lift), before)
        self.assertEqual(self.panel.opacity(), 0)
        pump(450)
        self.assertFalse(lift.isVisible())
        self.assertEqual(self.panel.opacity(), 1)

    def test_reduced_motion_commits_the_target_without_waiting(self):
        self.host.theme.configure({'reducedMotion': True})
        pump(50)
        self.carry(10, self.ws.height()/2)
        self.assertIsNotNone(self.ws.property('dragTarget'))
        self.release()
        self.assertFalse(self.ws.property('landing'))
        self.assertFalse(item(self.win, 'cardLift').isVisible())
        final = geometry(self.panel)
        pump(80)
        self.assertEqual(geometry(self.panel), final)

    def test_pending_target_wins_a_release_before_the_next_dwell(self):
        self.carry(10, self.ws.height()/2)
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        self.at = point(self.ws, self.ws.width()-10, self.ws.height()/2)
        mouse(self.app, self.win, QEvent.Type.MouseMove, self.at,
              Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        self.release()
        pump(450)
        self.assertEqual(self.panel.property('zone'), 'right')

    def test_reflow_does_not_move_the_target_out_from_under_the_pointer(self):
        project = item(self.win, 'leftPanel')
        self.carry(project.x()+project.width()/2, project.height()*0.4)
        candidate = self.ws.property('candidate')
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        pump(450)
        mouse(self.app, self.win, QEvent.Type.MouseMove, self.at,
              Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        self.assertEqual(self.ws.property('candidate'), candidate)
        self.release()

    def test_preview_and_final_rect_match_on_every_side_for_every_panel(self):
        for panel_id, name in [('checks', 'checksPanel'), ('project', 'leftPanel'),
                               ('properties', 'rightPanel')]:
            for zone in ('left', 'right', 'bottom'):
                with self.subTest(panel=panel_id, zone=zone):
                    self.win.runCommand('default_layout')
                    pump(450)
                    x, y = {'left': (10, self.ws.height()*0.7),
                            'right': (self.ws.width()-10, self.ws.height()*0.7),
                            'bottom': (self.ws.width()/2, self.ws.height()-10)}[zone]
                    self.carry(x, y, panel_id)
                    wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
                    pump(450)
                    preview = geometry(item(self.win, 'dropZone'))
                    self.release()
                    pump(450)
                    self.assertEqual(item(self.win, name).property('zone'), zone)
                    for a, b in zip(preview, geometry(item(self.win, name)), strict=True):
                        self.assertAlmostEqual(a, b, delta=1)

    def test_landing_and_views_follow_the_same_progress_and_finish_together(self):
        # Release into a fresh bottom target before its dwell: both motions start on this release.
        self.carry(self.ws.width()/2, self.ws.height()/2)
        self.release()
        pump(450)
        self.carry(self.ws.width()/2, self.ws.height()-10)
        central, lift = item(self.win, 'centralPanel'), item(self.win, 'cardLift')
        start_y, start_h = lift.y(), central.height()
        self.release()
        samples = []
        for _ in range(30):
            pump(16)
            samples.append((lift.y(), central.height(), self.ws.property('landing')))
        end_y, end_h = self.panel.y(), central.height()
        self.assertGreater(abs(end_y-start_y), 10)
        self.assertGreater(abs(end_h-start_h), 100)
        intermediate = 0
        for y, h, active in samples:
            if active:
                a, b = (y-start_y)/(end_y-start_y), (h-start_h)/(end_h-start_h)
                if 0.05 < a < 0.95:
                    intermediate += 1
                    self.assertAlmostEqual(a, b, delta=0.12)
        self.assertGreater(intermediate, 2)
        self.assertFalse(samples[-1][2])
        self.assertAlmostEqual(lift.y(), end_y, delta=1)

    def test_landing_size_changes_continuously_between_rendered_frames(self):
        self.carry(10, self.ws.height()/2)
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        pump(450)
        lift = item(self.win, 'cardLift')
        widths = [lift.width()]

        def frame():
            widths.append(lift.width())
            self.win.requestUpdate()

        self.win.frameSwapped.connect(frame)
        try:
            self.release()
            pump(500)
        finally:
            self.win.frameSwapped.disconnect(frame)
        self.assertGreater(len(widths), 5)
        delta = abs(widths[-1]-widths[0])
        self.assertGreater(delta, 100)
        jumps = [abs(b-a) for a, b in zip(widths, widths[1:], strict=False)]
        self.assertLess(max(jumps), delta*0.6)
        self.assertAlmostEqual(widths[-1], self.panel.width(), delta=1)

    def test_frozen_view_is_clipped_at_natural_size_without_resizing_its_buffer(self):
        view = item(self.win, 'plan').parentItem()
        size = (view.width(), view.height())
        self.carry(self.ws.width()/2, self.ws.height()/2)
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        pump(450)
        self.assertEqual((view.width(), view.height()), size)
        host = view.parentItem()
        corner = view.mapToItem(host, QPointF(view.width(), view.height()))
        self.assertAlmostEqual(corner.x(), view.width(), delta=0.01)
        self.assertAlmostEqual(corner.y(), view.height(), delta=0.01)
        self.assertTrue(host.clip())
        self.assertGreater(host.height(), view.height())
        self.release()

    def test_preview_border_and_outer_corners_match_the_card(self):
        zone = item(self.win, 'dropZone')
        objects = zone.findChildren(QObject)
        path = next(o for o in objects if 'PathRectangle' in o.metaObject().className())
        stroke = path.parent().property('strokeWidth')
        self.assertAlmostEqual(path.property('x')-stroke/2, 0, delta=0.01)
        self.assertAlmostEqual(path.property('radius')+stroke/2,
                               self.panel.property('radius'), delta=0.01)


    def test_every_rendered_content_keeps_its_natural_size(self):
        # Catch resampling of the carried texture, transformed views and per-frame panel layout.
        lift = item(self.win, 'cardLift')
        picture = next(o for o in lift.childItems()
                       if 'ShaderEffectSource' in o.metaObject().className())
        views = [item(self.win, 'plan').parentItem()]
        cards = [item(self.win, n) for n in ('leftPanel', 'rightPanel')]
        titles = [next(c for c in card.property('headRow').childItems()
                       if c.property('text')) for card in cards]
        samples = []
        stage = 'carry'

        def frame():
            source = picture.property('sourceItem')
            if source and source.width() and source.height():
                corner = picture.mapToScene(QPointF(picture.width(), picture.height()))
                origin = picture.mapToScene(QPointF())
                ratios = [(corner.x()-origin.x())/source.width(),
                          (corner.y()-origin.y())/source.height()]
                for view in views:
                    a = view.mapToScene(QPointF())
                    b = view.mapToScene(QPointF(view.width(), view.height()))
                    ratios.extend([(b.x()-a.x())/view.width(), (b.y()-a.y())/view.height()])
                for title in titles:
                    a = title.mapToScene(QPointF())
                    b = title.mapToScene(QPointF(title.width(), title.height()))
                    ratios.extend([(b.x()-a.x())/title.width(), (b.y()-a.y())/title.height()])
                samples.append(dict(stage=stage, ratios=ratios,
                                    layouts=[geometry(c.property('contentItem'))[2:] for c in cards]))
            self.win.requestUpdate()

        self.carry(10, self.ws.height()*0.3)
        self.win.frameSwapped.connect(frame)
        try:
            pump(750)
            stage = 'landing'
            self.release()
            pump(500)
        finally:
            self.win.frameSwapped.disconnect(frame)
        # Optional evidence contains only synthetic dimensions, never project data.
        import os
        if os.environ.get('MERIDIANA_MOTION_EVIDENCE'):
            Path(os.environ['MERIDIANA_MOTION_EVIDENCE']).write_text(
                json.dumps(samples), encoding='utf-8')
        self.assertGreater(len(samples), 10)
        for sample in samples:
            for ratio in sample['ratios']:
                self.assertAlmostEqual(ratio, 1, delta=0.01, msg=str(sample))
        # Once the target is laid out, the neighbours do not rewrap on animation frames.
        for card in range(len(cards)):
            self.assertLessEqual(len({tuple(r['layouts'][card]) for r in samples}), 2)
        for stage in ('carry', 'landing'):
            layouts = [r['layouts'] for r in samples if r['stage'] == stage]
            self.assertGreater(len(layouts), 3)
            self.assertEqual(layouts[-3:], [layouts[-1]]*3)

    def test_release_coordinates_do_not_retarget_the_displayed_preview(self):
        for accepted in (False, True):
            with self.subTest(accepted=accepted):
                self.win.runCommand('default_layout')
                pump(450)
                self.carry(10, self.ws.height()*0.25)
                if accepted:
                    pump(750)
                hint = item(self.win, 'dropOutline')
                promised = geometry(hint if hint.property('shown') else item(self.win, 'dropZone'))
                # A release coordinate differs from the last move; the displayed promise still wins.
                self.at = point(self.ws, self.ws.width()-10, self.ws.height()*0.75)
                self.release()
                pump(450)
                for a, b in zip(promised, geometry(self.panel), strict=True):
                    self.assertAlmostEqual(a, b, delta=1)

    def test_visible_placeholder_wins_over_a_new_pending_target(self):
        self.carry(10, self.ws.height()*0.25)
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        pump(450)
        # A new outline must not coexist with a different visible placeholder.
        self.at = point(self.ws, self.ws.width()-10, self.ws.height()*0.7)
        mouse(self.app, self.win, QEvent.Type.MouseMove, self.at,
              Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        hint, zone = item(self.win, 'dropOutline'), item(self.win, 'dropZone')
        self.assertFalse(hint.property('shown') and zone.property('shown'))
        promised = geometry(hint if hint.property('shown') else zone)
        self.release()
        pump(450)
        for a, b in zip(promised, geometry(self.panel), strict=True):
            self.assertAlmostEqual(a, b, delta=1)

    def test_tab_preview_includes_room_freed_at_the_origin(self):
        for stacked in (False, True):
            with self.subTest(stacked=stacked):
                self.win.runCommand('default_layout')
                pump(450)
                if stacked:
                    self.carry(10, self.ws.height()*0.75, 'properties')
                    self.release()
                    pump(450)
                anchor = item(self.win, 'rightPanel' if stacked else 'leftPanel')
                self.carry(anchor.x()+anchor.width()/2, anchor.y()+anchor.height()/2)
                self.app.sendEvent(self.win, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Alt,
                                                      Qt.KeyboardModifier.AltModifier))
                pump(16)
                self.assertTrue(self.ws.property('candidate').endswith('|tab'))
                if stacked:
                    pump(750)
                hint = item(self.win, 'dropOutline')
                promised = geometry(hint if hint.property('shown') else item(self.win, 'dropZone'))
                try:
                    self.release()
                    pump(450)
                    for a, b in zip(promised, geometry(self.panel), strict=True):
                        self.assertAlmostEqual(a, b, delta=1)
                    self.assertEqual(geometry(self.panel), geometry(anchor))
                finally:
                    self.app.sendEvent(self.win, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key_Alt,
                                                          Qt.KeyboardModifier.NoModifier))

    def test_preview_holds_through_diagonal_boundary_jitter(self):
        project = item(self.win, 'leftPanel')
        x, y = project.width(), project.height()/2
        self.carry(x-2, y-2)
        wait_for(lambda: self.ws.property('dragTarget') is not None, seconds=2)
        candidate = self.ws.property('candidate')
        for dx, dy in [(2, 2), (5, 5), (1, -1), (-1, 1)]*8:
            self.at = point(self.ws, x+dx, y+dy)
            mouse(self.app, self.win, QEvent.Type.MouseMove, self.at,
                  Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
            pump(16)
            self.assertEqual(self.ws.property('candidate'), candidate)
            self.assertTrue(item(self.win, 'dropZone').property('shown'))
        self.at = point(self.ws, self.ws.width()/2, self.ws.height()/2)
        mouse(self.app, self.win, QEvent.Type.MouseMove, self.at,
              Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        pump(400)
        self.assertFalse(item(self.win, 'dropZone').property('shown'))
        self.release()

    def test_preview_uses_neutral_theme_in_light_and_dark(self):
        from PySide6.QtGui import QColor
        from PySide6.QtQml import QQmlExpression, QQmlEngine
        hint, zone = item(self.win, 'dropOutline'), item(self.win, 'dropZone')
        context = QQmlEngine.contextForObject(hint)
        for theme in ('light', 'dark'):
            expression = QQmlExpression(context, hint,
                'Theme.configure({theme:"'+theme+'", accent:"#ff00ff"})')
            expression.evaluate()
            pump(30)
            neutral = QColor(QQmlExpression(context, hint, 'Theme.colors.hover').evaluate()[0])
            border = QColor(QQmlExpression(context, hint, 'Theme.colors.card_line').evaluate()[0])
            self.assertEqual(hint.property('color'), neutral)
            self.assertEqual(QQmlExpression(context, hint, 'border.color').evaluate()[0], border)
            path = next(o for o in zone.findChildren(QObject)
                        if o.property('fillColor') is not None)
            self.assertEqual(path.property('fillColor'), neutral)
            self.assertEqual(path.property('strokeColor'), border)

    def test_one_hundred_random_releases_land_in_the_shown_preview(self):
        rng = random.Random(689)
        names = {'checks': 'checksPanel', 'project': 'leftPanel', 'properties': 'rightPanel'}
        for gesture in range(100):
            # Restore has a second-click undo: start each independent trial from defaults.
            self.ws.setProperty('previousLayout', None)
            self.win.runCommand('default_layout')
            wait_for(lambda: not self.ws.property('settling'), seconds=2)
            pump(50)
            for p, n in names.items():
                self.assertEqual(item(self.win, n).property('zone'),
                                 {'checks': 'bottom', 'project': 'left', 'properties': 'right'}[p])
            panel_id = rng.choice(list(names))
            w, h = self.ws.width(), self.ws.height()
            side = rng.choice(('left', 'right', 'bottom'))
            x, y = {'left': (rng.uniform(1, 20), rng.uniform(40, h-40)),
                    'right': (w-rng.uniform(1, 20), rng.uniform(40, h-40)),
                    'bottom': (rng.uniform(40, w-40), h-rng.uniform(1, 20))}[side]
            tab = gesture % 4 < 2
            if tab:
                anchor = item(self.win, names[rng.choice([p for p in names if p != panel_id])])
                x, y = anchor.x()+anchor.width()/2, anchor.y()+anchor.height()/2
            state = {p: (item(self.win, n).property('zone'), item(self.win, n).isVisible(),
                         geometry(item(self.win, n))) for p, n in names.items()}
            self.carry(x, y, panel_id)
            self.assertEqual(self.ws.property('draggedPanel'), panel_id,
                             msg=f'gesture {gesture}: {state}')
            if tab:
                self.app.sendEvent(self.win, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Alt,
                                                      Qt.KeyboardModifier.AltModifier))
                pump(16)
            if gesture % 2:
                pump(750)
            hint = item(self.win, 'dropOutline')
            zone = item(self.win, 'dropZone')
            self.assertTrue(hint.property('shown') or zone.property('shown'),
                            msg=f'gesture {gesture}: {state}')
            promised = geometry(hint if hint.property('shown') else zone)
            candidate = self.ws.property('candidate')
            self.release()
            wait_for(lambda: not self.ws.property('landing') and
                     self.ws.property('draggedPanel') == '', seconds=2)
            if tab:
                self.app.sendEvent(self.win, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key_Alt,
                                                      Qt.KeyboardModifier.NoModifier))
            for a, b in zip(promised, geometry(item(self.win, names[panel_id])), strict=True):
                self.assertAlmostEqual(a, b, delta=1, msg=f'gesture {gesture}: {panel_id}, {candidate}, {state}')


if __name__ == '__main__':
    unittest.main()
