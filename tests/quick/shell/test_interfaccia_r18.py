"""Defects of the Quick interface seen by Daniel on r17-unita (06/11/2026), on one workbench with the real views."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import item, pump
from quick.parity.differential import connected_fixture

# no keep_global_state: in the shell folder an earlier module leaves a QGuiApplication, without styleSheet

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def scene_rect(obj):
    top_left = obj.mapToScene(obj.boundingRect().topLeft())
    return (top_left.x(), top_left.y(), obj.width(), obj.height())


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def descendants(root):
    """Every item under root by the visual tree: what a Repeater or a Loader makes is not always its QObject child."""
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

    def test_r449_no_empty_band_above_the_views_at_opening_and_after_a_resize(self):
        self.phase('model')
        above, central = item(self.win, 'viewsTrailing'), item(self.win, 'centralPanel')
        for size in ((1600, 960), (900, 600), (1400, 860)):
            self.win.resize(*size)
            pump(500)
            self.assertFalse(above.property('active'), f'{size}: the model phase has nothing to put above the views')
            plan = item(self.win, 'plan')
            gap = plan.mapToItem(central, plan.boundingRect().topLeft()).y()
            self.assertLess(gap, 30, f'{size}: the plan starts {gap:.0f} px under the top of its card')
        self.win.resize(1600, 960)
        pump(300)

    def fall_back(self, maps):
        """The source in use stops answering, as after three tiles failed (PlanMaps.failed)."""
        import time
        state = maps.state
        state.unavailable[state.source] = time.monotonic()
        state.choose()
        maps._refresh()             # as PlanMaps.failed reaches the window: MapController._failed
        pump(150)
        self.assertNotEqual(maps.fallbackMessage, '')

    def test_r463_the_fallback_notice_covers_no_control_and_its_buttons_answer(self):
        from PySide6.QtCore import QObject, QPointF
        from quick.gestures import click
        self.phase('model')
        maps = self.host.plan.maps
        self.assertIsNotNone(maps)
        self.addCleanup(maps.retryBackground)
        self.fall_back(maps)
        notice = item(self.win, 'mapNotice')
        self.assertTrue(notice.isVisible())
        self.assertEqual(item(self.win, 'mapNoticeText').property('text'), maps.fallbackMessage)
        box = scene_rect(notice)
        for name in ('compass', 'planViewBar'):
            self.assertFalse(overlap(box, scene_rect(item(self.win, name))), f'the notice covers the {name}')
        self.assertLessEqual(box[3], 40, 'one line')

        def press(name):
            button = item(self.win, name)
            centre = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
            click(self.app, self.win, centre)
            pump(200)

        press('mapNoticeRetry')
        self.assertEqual(maps.state.fallback_from, '', 'Riprova asks the orthophoto again')
        self.assertFalse(notice.isVisible())

        self.fall_back(maps)
        menu = self.win.findChild(QObject, 'backgroundMenu')
        press('mapNoticeChoose')
        self.assertTrue(menu.property('visible'), 'Scegli lo sfondo opens the menu of the background')
        menu.setProperty('visible', False)
        pump(150)

        press('mapNoticeClose')
        self.assertFalse(notice.isVisible(), 'the line closes')
        self.assertNotEqual(maps.state.fallback_from, '', 'closing it changes nothing in the maps')

        # a narrow plan (the capture at 150 %: the words gone and the close over the compass): nothing passes the limit
        maps.retryBackground()
        self.fall_back(maps)
        try:
            for size in ((1100, 700), (900, 600)):
                self.win.resize(*size)
                pump(500)
                if not notice.isVisible():
                    continue
                compass = scene_rect(item(self.win, 'compass'))
                for name in ('mapNoticeText', 'mapNoticeRetry', 'mapNoticeChoose', 'mapNoticeClose'):
                    part = item(self.win, name)
                    if part.isVisible() and part.width() > 0:
                        self.assertFalse(overlap(scene_rect(part), compass), f'{size}: {name} over the compass')
                        box = scene_rect(notice)
                        self.assertLessEqual(scene_rect(part)[0] + part.width(), box[0] + box[2] + .5, f'{size}: {name} out of the line')
        finally:
            self.win.resize(1600, 960)
            pump(300)

    PHASES = ('model', 'plant', 'production', 'consumption', 'economics', 'report')

    def tooltips(self):
        from PySide6.QtCore import QObject
        return [o for o in self.win.findChildren(QObject)
                if 'ToolTip' in o.metaObject().className() and o.metaObject().indexOfProperty('delay') >= 0]

    def test_r468_every_tooltip_waits_as_in_the_widgets(self):
        import re
        root = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml'
        attached = [f'{p.relative_to(root)}:{n}' for p in root.rglob('*.qml')
                    for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1)
                    if re.search(r'\bToolTip\.(visible|text|delay)\s*:', line)]
        self.assertEqual(attached, [], 'the attached tooltip of QtQuick.Controls shows at once, in the Basic look')
        metrics = item(self.win, 'controlTip')
        self.assertIsNotNone(metrics)
        for name in self.PHASES:
            self.phase(name)
            delays = {o.metaObject().className(): o.property('delay') for o in self.tooltips()}
            warm = [o for o in self.tooltips() if o.property('visible')]
            if not warm:
                self.assertEqual(set(delays.values()) - {700}, set(), (name, delays))

    def test_r468_no_tooltip_says_the_words_already_on_its_control(self):
        """The census: every control with a tooltip in every phase, against the visible words inside it."""

        def words(text):
            import re
            text = re.sub(r'&(?!&)', '', str(text or ''))
            return re.sub(r'\s+', ' ', re.sub(r'[\s.…:]+$', '', text)).strip().lower()

        def shown_words(control):
            out = []
            for child in descendants(control):
                meta = child.metaObject()
                if meta.indexOfProperty('truncated') >= 0 and meta.indexOfProperty('text') >= 0 and child.property('visible'):
                    if not child.property('truncated'):
                        out.append(words(child.property('text')))
            return out

        seen, repeated = 0, []
        for name in self.PHASES:
            self.phase(name)
            for control in descendants(self.win.contentItem()):
                meta = control.metaObject()
                if meta.indexOfProperty('tip') < 0 or not control.property('visible'):     # hidden pages too
                    continue
                tip = control.property('shownTip') if meta.indexOfProperty('shownTip') >= 0 else control.property('tip')
                if not isinstance(tip, str) or not tip:
                    continue
                seen += 1
                if words(tip) in shown_words(control):
                    repeated.append(f'{name}: {control.objectName() or meta.className()} «{tip}»')
        self.assertGreater(seen, 60, 'the census found the controls')
        self.assertEqual(sorted(set(repeated)), [], f'{seen} tooltips looked at')

    def test_r468_segments_tell_only_what_their_words_do_not(self):
        """The photo of 06/11: «Giorno tipo» over the segment «Giorno tipo» of the Production page."""
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        component = QQmlComponent(self.host.engine)
        component.setData('import QtQuick\nimport Meridiana.Controls as M\nItem { width: 600; height: 40\n'
                          'M.Segments { width: 600; model: ["Mesi", "Perdite", "Giorno tipo", '
                          '{text: "Come è calcolato", tip: "Le formule e le fonti"}] } }'.encode(), QUrl())
        root = component.create()
        self.assertIsNotNone(root, [e.toString() for e in component.errors()])
        QQmlEngine.setObjectOwnership(root, QQmlEngine.ObjectOwnership.CppOwnership)
        root.setParentItem(self.win.contentItem())
        root.setVisible(False)
        buttons = sorted((b for b in descendants(root) if b.metaObject().indexOfProperty('shownTip') >= 0), key=lambda b: b.x())
        tips = [b.property('shownTip') for b in buttons]
        root.deleteLater()
        self.assertEqual(tips, ['', '', '', 'Le formule e le fonti'])


    def test_r469_every_question_mark_is_the_one_help_mark(self):
        # R21-F3 (Daniel 07/11/2026): one «?» in the program, M.HelpMark, the round icon of the cards' header (20 px,
        # the icon at 12, a flat button): it was R469's square of the Widgets with a hair line round it
        marks = []
        for name in self.PHASES:
            self.phase(name)
            marks += [(name, m) for m in descendants(self.win.contentItem())
                      if m.metaObject().indexOfProperty('helpMark') >= 0 and m.property('visible')]
        self.assertGreater(len(marks), 3)
        for name, mark in marks:
            self.assertEqual((mark.implicitWidth(), mark.implicitHeight()), (20, 20), name)
            if mark.isVisible():
                self.assertEqual((mark.width(), mark.height()), (20, 20), name)
            self.assertTrue(mark.property('flat'), f'{name}: a flat button, no line round it')


    def test_r475_a_second_click_closes_the_menu_and_passing_over_the_next_title_opens_it(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtTest import QTest
        self.phase('model')
        workbench = self.win              # the Workbench is the window: its bar of menus, shown as Alt shows it
        workbench.setProperty('menuOpen', True)
        pump(400)

        def centre(name):
            button = item(self.win, name)
            point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
            return QPoint(round(point.x()), round(point.y()))

        def opened(index):
            return item(self.win, f'mainMenu_{index}').property('menuOpened')

        def click(name):
            QTest.mouseClick(self.win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre(name))
            pump(250)
        try:
            click('mainMenu_0')
            self.assertTrue(opened(0), 'a click opens the menu')
            click('mainMenu_0')
            self.assertFalse(opened(0), 'a second click on its title closes it')
            click('mainMenu_0')
            self.assertTrue(opened(0))
            QTest.mouseMove(self.win, centre('mainMenu_1'))
            pump(250)
            self.assertTrue(opened(1), 'passing over the next title opens its menu')
            self.assertFalse(opened(0), 'and closes the one before')
        finally:
            for _ in range(2):
                QTest.keyClick(self.win, Qt.Key.Key_Escape)
                pump(100)
            workbench.setProperty('menuOpen', False)
            pump(300)


if __name__ == '__main__':
    unittest.main()
