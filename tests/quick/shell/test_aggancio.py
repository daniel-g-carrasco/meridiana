"""R504: the cards carried and docked (docs/studio/36-aggancio-schede.md).

The drop zone appears from the carried card, not from the window's corner; near a side of the workspace that side
wins whatever the half; a card can lie at the top of the left column and one at the top of the right column, each
column shared by its own handle.
"""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QMetaObject, QPointF, QRect, Qt
from PySide6.QtGui import QKeyEvent

from _fixtures import capannone
from meridiana import jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import click, drag, item, mouse, point, pump, wait_for


class DockingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.host = QuickWindow(capannone(), Path(self.temp.name))
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        self.win.resize(1600, 960)
        results, keys, _ = jobs.layout_of(self.host.bridge.session.project)
        self.host.bridge.accept_layout(0, results, keys)
        pump(100)
        item(self.win, 'plan').fit()
        self.workspace = item(self.win, 'workspace')

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        self.app.processEvents()
        self.temp.cleanup()
        self.assertEqual(warnings, [])

    def carry(self, panel, x, y):
        """Press on the card's title and carry it to (x, y) of the workspace, in eight steps; the button stays down."""
        start = point(item(self.win, panel+'TitleDrag'))
        end = point(self.workspace, x, y)
        mouse(self.app, self.win, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
        for i in range(1, 9):
            mouse(self.app, self.win, QEvent.Type.MouseMove, start+(end-start)*(i/8), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
            pump(16)
        return end

    def release(self, at):
        mouse(self.app, self.win, QEvent.Type.MouseButtonRelease, at, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
        pump(450)

    def zone_at(self, panel, x, y):
        """The zone answered after the dwell for `panel` carried to (x, y); the card is then dropped there."""
        end = self.carry(panel, x, y)
        wait_for(lambda: self.workspace.property('dragTarget') is not None, seconds=2)
        zone = self.workspace.property('targetZone')
        self.release(end)
        return zone

    def rect(self, name):
        obj = item(self.win, name)
        return (obj.x(), obj.y(), obj.width(), obj.height())

    def test_the_outline_answers_at_once_and_the_drop_zone_grows_out_of_it(self):
        # Study 36, proposal 1: an accent outline on the place before the dwell, the dashed drop zone after it.
        # r23-unita: the drop zone's first place is read when the target is chosen, not after the wait's slice of
        # events: on a busy PC that slice already held frames of the growth (2 runs in 3 of the whole suite, r23-f8)
        appeared = []
        self.workspace.dragTargetChanged.connect(
            lambda: appeared.append(self.rect('dropZone')) if self.workspace.property('dragTarget') is not None else None)
        end = self.carry('checks', 100, 40)
        outline, project = item(self.win, 'dropOutline'), item(self.win, 'leftPanel')
        revision = self.workspace.property('revision')
        self.assertIsNone(self.workspace.property('dragTarget'))
        self.assertTrue(outline.property('shown'))
        told = self.rect('dropOutline')         # its place is there at once; the fade follows
        card = (project.x(), project.y(), project.width(), project.height())
        wait_for(lambda: outline.opacity() == 1, seconds=1)
        # The upper half of the Project card: nothing has moved yet. r23-unita: on a busy PC the fade's wait can outlast
        # the dwell (Theme.motion.DWELL), and then the room made for the card is the dwell's, not an early relayout
        # (the whole tests/quick, 1 run in 2): the check holds while the dwell has not answered.
        if self.workspace.property('dragTarget') is None:
            self.assertEqual(self.workspace.property('revision'), revision)
        self.assertAlmostEqual(told[0], card[0], delta=1); self.assertAlmostEqual(told[1], card[1], delta=1)
        self.assertAlmostEqual(told[2], card[2], delta=1); self.assertAlmostEqual(told[3], card[3]/2, delta=1.5)
        wait_for(lambda: self.workspace.property('dragTarget') is not None, seconds=2)
        self.assertTrue(appeared, 'dragTargetChanged told when the target came')
        first = appeared[0]
        self.assertFalse(outline.property('shown'))
        pump(450)
        settled = self.rect('dropZone')
        self.release(end)
        self.assertNotEqual(first, (0.0, 0.0, 0.0, 0.0))
        # The drop zone's first frame is the outline's place, then it settles on the slice.
        for a, b in zip(first, told):
            self.assertAlmostEqual(a, b, delta=1)
        self.assertNotEqual(settled, first)
        self.assertAlmostEqual(settled[1], 0, delta=1)
        self.assertFalse(outline.isVisible())

    def test_the_outline_goes_when_the_card_floats_and_comes_back_in_place(self):
        w, h = self.workspace.width(), self.workspace.height()
        outline = item(self.win, 'dropOutline')
        self.carry('checks', 100, 40)
        self.assertTrue(outline.property('shown'))
        at = point(self.workspace, w/2, h/2)
        mouse(self.app, self.win, QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        pump(16)
        self.assertFalse(outline.property('shown'))
        wait_for(lambda: not outline.isVisible(), seconds=1)
        at = point(self.workspace, w-10, h/2)
        mouse(self.app, self.win, QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        pump(16)
        self.assertTrue(outline.property('shown'))
        # Shown again it is in place at once, not sliding over from where it last was.
        properties = item(self.win, 'rightPanel')
        self.assertAlmostEqual(outline.x(), properties.x(), delta=1)
        self.assertAlmostEqual(outline.y(), properties.y()+properties.height()/2, delta=1.5)
        self.release(at)
        self.assertEqual(item(self.win, 'checksPanel').property('zone'), 'right')

    def test_the_views_keep_their_size_while_a_card_is_carried(self):
        # The real views, the 3D among them: the fixture of setUp has the placeholders.
        self.host.close(); self.app.processEvents()
        self.host = QuickWindow(capannone(), Path(self.temp.name), real_views=True)
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show(); self.win.resize(1600, 960)
        controller = self.host.engine.incubationController()
        wait_for(lambda: controller.incubatingObjectCount() == 0, seconds=10)
        pump(300)
        self.workspace = item(self.win, 'workspace')
        scene, host = item(self.win, 'viewport3d'), item(self.win, 'view3dHost')
        before = (scene.width(), scene.height(), host.width(), host.height())
        end = self.carry('checks', 100, 40)
        wait_for(lambda: self.workspace.property('dragTarget') is not None, seconds=2)
        pump(450)
        # The room made for the card changed the central card, not the 3D view, until the drop.
        self.assertNotEqual((host.width(), host.height()), before[2:])
        self.assertEqual((scene.width(), scene.height()), before[:2])
        self.release(end)
        self.assertEqual((scene.width(), scene.height()), (host.width(), host.height()))

    def test_the_last_centimetre_at_a_side_wins_over_the_half(self):
        w, h = self.workspace.width(), self.workspace.height()
        self.assertEqual(self.zone_at('checks', 40, h-10), 'bottom')      # bottom-left corner: the bottom, not the left column
        self.win.runCommand('default_layout'); pump(450)
        self.assertEqual(self.zone_at('project', 40, h-10), 'bottom')
        self.win.runCommand('default_layout'); pump(450)
        self.assertEqual(self.zone_at('checks', w-10, h/2), 'right')
        self.win.runCommand('default_layout'); pump(450)
        self.assertEqual(self.zone_at('properties', 10, h/2), 'left')
        self.win.runCommand('default_layout'); pump(450)
        self.assertEqual(self.zone_at('project', w/2, h-10), 'bottom')

    def test_a_card_at_the_top_of_each_column_with_its_own_handle(self):
        w, h = self.workspace.width(), self.workspace.height()
        self.assertEqual(self.zone_at('checks', 100, 40), 'left')
        checks, project = item(self.win, 'checksPanel'), item(self.win, 'leftPanel')
        self.assertEqual((checks.property('zone'), project.property('zone')), ('left', 'left'))
        self.assertLess(checks.y()+checks.height(), project.y())
        self.assertEqual(self.zone_at('project', w-100, 40), 'right')
        properties = item(self.win, 'rightPanel')
        self.assertEqual((project.property('zone'), properties.property('zone')), ('right', 'right'))
        self.assertLess(project.y()+project.height(), properties.y())
        self.assertAlmostEqual(checks.height(), h, delta=1)
        handles = [o for o in self.workspace.childItems() if o.objectName() == 'sliceHandle' and o.isVisible()]
        self.assertEqual(len(handles), 1)
        before = project.height()
        start = point(handles[0])
        drag(self.app, self.win, start, start+QPointF(0, 120), steps=6)
        pump(450)
        self.assertGreater(project.height(), before+100)
        self.assertAlmostEqual(project.height()+properties.height()+handles[0].height(), h, delta=2)

    def test_the_pointer_over_the_centre_moves_the_card_without_relayout(self):
        w, h = self.workspace.width(), self.workspace.height()
        start = point(item(self.win, 'checksTitleDrag'))
        mouse(self.app, self.win, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
        mouse(self.app, self.win, QEvent.Type.MouseMove, point(self.workspace, w/2, h/2), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        pump(400)
        revision = self.workspace.property('revision')
        lift = item(self.win, 'cardLift')
        lifted = (lift.x(), lift.y())
        for i in range(1, 40):
            at = point(self.workspace, w/2+i*4, h/2-i*2)
            mouse(self.app, self.win, QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
            pump(8)
        self.assertEqual(self.workspace.property('revision'), revision)
        # The carried card is at the pointer at once: no animation behind it.
        self.assertAlmostEqual(lift.x()-lifted[0], 39*4, delta=2)
        self.assertAlmostEqual(lift.y()-lifted[1], -39*2, delta=2)
        self.release(point(self.workspace, w/2+156, h/2-78))
        self.assertEqual(item(self.win, 'checksPanel').property('zone'), 'floating')

    # R317, R527: the tabs only with Alt held. Without it a card under the pointer takes the carried one before or
    # after itself, by the half of the point; with Alt its middle takes it behind itself as a tab. Alt pressed or let
    # go while the card is carried answers at once, the mouse still; and Alt used for the carry never opens the menu.
    def alt(self, kind):
        modifiers = Qt.KeyboardModifier.AltModifier if kind == QEvent.Type.KeyPress else Qt.KeyboardModifier.NoModifier
        self.app.sendEvent(self.win, QKeyEvent(kind, Qt.Key.Key_Alt, modifiers))
        pump(16)

    def middle_of(self, name):
        card = item(self.win, name)
        return card.x()+card.width()/2, card.y()+card.height()/2

    def test_without_alt_the_middle_of_a_card_is_never_a_tab(self):
        project = item(self.win, 'leftPanel')
        for share in (0.4, 0.5, 0.6):
            top, height = project.y(), project.height()
            end = self.carry('checks', project.x()+project.width()/2, top+height*share)
            self.assertEqual(self.workspace.property('candidate'), 'left|project|'+('before' if share < 0.5 else 'after'),
                             (share, top, height, project.x(), project.width(), project.property('zone')))
            outline = item(self.win, 'dropOutline')
            self.assertTrue(outline.property('shown'))
            pump(250)
            self.assertAlmostEqual(outline.height(), height/2, delta=2)
            self.release(end)
            self.win.runCommand('default_layout'); pump(450)

    def test_alt_held_makes_the_middle_a_tab_and_letting_it_go_takes_it_back(self):
        x, y = self.middle_of('leftPanel')
        end = self.carry('checks', x, y)
        self.assertEqual(self.workspace.property('candidate'), 'left|project|after')
        hint = item(self.win, 'tabHint')
        self.assertTrue(hint.property('shown'))           # «Alt: a linguette», low in the card under the pointer
        project = item(self.win, 'leftPanel')
        self.assertGreater(hint.y(), project.y()+project.height()/2)
        self.alt(QEvent.Type.KeyPress)
        self.assertEqual(self.workspace.property('candidate'), 'left|project|tab')
        self.assertFalse(hint.property('shown'))
        project = item(self.win, 'leftPanel')
        pump(250)
        self.assertEqual(self.rect('dropOutline'), (project.x(), project.y(), project.width(), project.height()))
        self.alt(QEvent.Type.KeyRelease)
        self.assertEqual(self.workspace.property('candidate'), 'left|project|after')
        self.alt(QEvent.Type.KeyPress)
        wait_for(lambda: self.workspace.property('grouping'), seconds=2)
        self.release(end)
        self.alt(QEvent.Type.KeyRelease)
        checks = item(self.win, 'checksPanel')
        self.assertEqual(checks.property('zone'), 'left')
        self.assertFalse(checks.property('stacked'))
        self.assertFalse(self.win.property('menuOpen'))

    def test_alt_tapped_while_a_card_is_carried_does_not_open_the_menu(self):
        x, y = self.middle_of('leftPanel')
        end = self.carry('checks', x, y)
        self.alt(QEvent.Type.KeyPress)
        self.alt(QEvent.Type.KeyRelease)
        self.assertFalse(self.win.property('menuOpen'))
        self.release(end)
        self.assertFalse(self.win.property('menuOpen'))
        # and Alt alone afterwards still opens it
        self.alt(QEvent.Type.KeyPress)
        self.alt(QEvent.Type.KeyRelease)
        self.assertTrue(self.win.property('menuOpen'))


    # R528: the cards in tabs have the segmented control of Checks at their head, under the title, as wide as the
    # body; a click brings a card forward, a tab carried away takes its card out of the group.
    def group(self):
        item(self.win, 'checksPanel').setProperty('zone', 'left')
        QMetaObject.invokeMethod(self.workspace, 'arrangementChanged')
        pump(600)
        return item(self.win, 'projectGroupTabs')

    def test_the_cards_in_tabs_have_the_segments_at_their_head(self):
        self.assertFalse(item(self.win, 'projectGroupTabs').isVisible())
        bar, project = self.group(), item(self.win, 'leftPanel')
        self.assertTrue(bar.isVisible())
        self.assertEqual(bar.property('currentIndex'), 0)
        body = project.property('contentItem')
        self.assertEqual((bar.x(), bar.width()), (body.x(), body.width()))
        self.assertLess(bar.y(), 80)                                    # at the head, not at the foot
        self.assertGreaterEqual(body.y(), bar.y()+bar.height())
        # R528 (r23-f5): the tabs say the titles: the head does not say the card's title again above them
        self.assertFalse(project.property('titleShown'))
        self.assertTrue(item(self.win, 'rightPanel').property('titleShown'))
        click(self.app, self.win, point(bar, bar.width()*0.75, bar.height()/2))
        pump(300)
        checks = item(self.win, 'checksPanel')
        self.assertTrue(checks.isVisible())
        self.assertFalse(project.isVisible())
        self.assertEqual(item(self.win, 'checksGroupTabs').property('currentIndex'), 1)

    def test_a_narrow_column_cuts_the_names_and_the_tooltip_says_them_whole(self):
        bar = self.group()
        self.workspace.setProperty('leftExtent', 130)
        QMetaObject.invokeMethod(self.workspace, 'arrangementChanged')
        pump(600)
        self.assertLess(bar.width(), bar.property('naturalWidth'))
        def under(node):
            for child in node.childItems():
                yield child
                yield from under(child)
        segments = [o for o in under(bar) if o.property('shownTip') is not None and o.property('text')]
        tips = sorted(o.property('shownTip') for o in segments)
        self.assertEqual(len(segments), 2)
        self.assertTrue(all(o.property('contentItem').property('truncated') for o in segments))
        self.assertEqual(tips, sorted(item(self.win, n).property('title') for n in ('leftPanel', 'checksPanel')))

    def test_a_tab_carried_away_takes_its_card_out_of_the_group(self):
        bar = self.group()
        w, h = self.workspace.width(), self.workspace.height()
        start, end = point(bar, bar.width()*0.75, bar.height()/2), point(self.workspace, w-10, h/2)
        mouse(self.app, self.win, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
        for i in range(1, 13):
            mouse(self.app, self.win, QEvent.Type.MouseMove, start+(end-start)*(i/12), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
            pump(16)
        self.assertEqual(self.workspace.property('draggedPanel'), 'checks')
        self.assertTrue(item(self.win, 'leftPanel').isVisible())        # the card shown stays while the other goes
        wait_for(lambda: self.workspace.property('dragTarget') is not None, seconds=2)
        self.release(end)
        self.assertEqual(item(self.win, 'checksPanel').property('zone'), 'right')
        self.assertFalse(bar.isVisible())


    # R536: the cards over the words of the bar at the foot, docked low, floating or carried over it.
    def test_the_cards_lie_over_the_words_at_the_foot(self):
        hint, checks = item(self.win, 'statusHint'), item(self.win, 'checksPanel')
        top = hint.mapToScene(hint.boundingRect().topLeft()).y()
        low = checks.mapToScene(checks.boundingRect().bottomLeft()).y()
        self.assertLessEqual(low, top)                                  # docked at the bottom: above the words
        self.assertLess(hint.parentItem().z(), self.workspace.parentItem().z())
        self.workspace.setProperty('settling', False)
        checks.setProperty('floatY', self.workspace.height()-120)
        checks.setProperty('floatHeight', 300)
        checks.setProperty('zone', 'floating')
        QMetaObject.invokeMethod(self.workspace, 'arrangementChanged')
        pump(500)
        at = hint.mapToScene(hint.boundingRect().topLeft())
        self.assertGreater(checks.mapToScene(checks.boundingRect().bottomLeft()).y(), at.y()+hint.height())
        dpr = self.win.grabWindow().width()/self.win.width()
        left = max(at.x(), checks.mapToScene(checks.boundingRect().topLeft()).x()) + 2
        area = QRect(int(left*dpr), int(at.y()*dpr), int((checks.width()-4)*dpr), int(hint.height()*dpr))
        shown = self.win.grabWindow().copy(area)
        hint.setVisible(False)
        pump(50)
        hidden = self.win.grabWindow().copy(area)
        hint.setVisible(True)
        self.assertEqual(shown, hidden)                                 # not one pixel of the words over the card


if __name__ == '__main__':
    unittest.main()
