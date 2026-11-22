"""R616 (Daniel 14/11/2026: «sovrapposizione stringhe su questa barra delle coordinate. È già successa spesso sta roba
di elementi che si sovrappongono in modo improprio, dobbiamo farci molta attenzione»): what lies over a view (the view
bar, the compass, the scale, the pointer's coordinates, the map's credit; in the 3D view the cube, the tools and the
sun's bar) stands over everything that belongs to the drawing.

Two guards:
- in the real window off screen, each element of the drawing (a string's name, a check's mark, the side highlighted, a
  side's pill, a corner's grip; in the 3D view a check's mark) is brought under each bar over its view, and the pixels
  inside the bar are read: there the bar is seen, not the element. Daniel's case (the strings' names over the pointer's
  coordinates) and the side highlighted over every bar were red on r34-unita, and so were the 3D marks over the cube;
- the order is one scale, the theme's (`design.Stack`, `Theme.stack` in QML): in the QML of the plan and of the 3D view
  no `z:` is written by hand but the few listed here, each with its reason."""
import os
import re
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QImage

import _setup
from PySide6.QtQuick import QQuickItem
from _fixtures import capannone
from meridiana import i18n
from meridiana.app import jobs
from meridiana.gui.style import design
from quick.gestures import mouse, pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

QML = Path(__file__).resolve().parents[3] / 'src/meridiana/gui/qml/Meridiana'
# the files whose `z:` decide what stands over what between the drawing and the bars over a view
VIEW_FILES = [*sorted((QML / 'Plan').glob('*.qml')), *sorted((QML / 'View3D').glob('*.qml')),
              QML / 'Shell/PlanHost.qml', QML / 'Shell/View3DHost.qml', QML / 'Checks/SceneMarks.qml',
              QML / 'Properties/SideHighlight.qml']
# the `z:` written by hand that stay, each inside its own item and none between the drawing and a bar
LOCAL_Z = {
    ('MapLayer.qml', 'zoom'): 'the map tiles of each zoom over the coarser ones, inside the map layer',
    ('StringLabels.qml', '3'): 'the name under the pointer over the other names, inside the strings\' layer',
}
# a share of the element seen inside the bar: 0 under an opaque bar, the bar's transparency under a glass one
# (overlay.glass is 78 % opaque: about 0,2), 1 over it
OVER = .5


def project():
    """The shed of the fixtures, laid, with six strings on two inverters, as in Daniel's capture."""
    p = capannone()
    results, _keys, _ = jobs.layout_of(p)
    sid = p.subfields[0].id
    modules = results[sid].modules
    per = len(modules) // 6
    p.energy['strings'] = {'runs': [{'inverter': 1 + i // 3, 'mppt': 1,
                                     'modules': [sid + '/' + m.key for m in modules[i*per:(i+1)*per]]}
                                    for i in range(6)]}
    return p


def items(root):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        out.append(node)
        pending.extend(c for c in node.childItems() if isinstance(c, QQuickItem))  # on Linux PySide hands back a child typed QMetaObject now and then: items only
    return out


def pixels(image):
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    w, h = image.width(), image.height()
    rows = np.frombuffer(image.constBits(), np.uint8, count=image.sizeInBytes()).reshape(h, image.bytesPerLine())
    return rows[:, :w * 4].reshape(h, w, 4)[:, :, :3].astype(np.int32).copy()


class Sovrapposizioni(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        from meridiana.gui.application import QuickWindow, create_app
        create_app()
        i18n.setup('it')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project(), Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.session = cls.host.bridge.session
        results, keys, _ = jobs.layout_of(cls.session.project)
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1400, 860)
        pump(200)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    # what is on screen

    def find(self, name, visible=True):
        found = [i for i in items(self.win.contentItem()) if i.objectName() == name and (i.isVisible() or not visible)]
        return found[0] if found else None

    def of_class(self, root, prefix):
        return [i for i in items(root) if i.metaObject().className().startswith(prefix) and i.isVisible()]

    def show_mark(self):
        """A check's mark on the building, shown and still there a second later. The checks computed once more (the
        phase or the layout ask for them, and their «busy» may not be on yet when it is read) replace the items shown
        from here, and with them the marks (on the merged r34-unita, 14/11/2026, 0,6 s after: «already deleted»): the
        mark is shown again until it stays."""
        from meridiana.core.rules.checks import Item
        checks = self.host.parts.controllers['checks']
        inspectors = self.host.parts.controllers['inspectors']
        building = self.session.project.buildings[0].id
        extra = Item('warn', 'roof', 'Roof detail', target=('building', building))
        for _ in range(6):
            wait_for(lambda: not checks.busy, 15)
            checks.show_items([*[i for i in checks.items if i is not extra], extra])
            pump(1000)
            if extra in checks.items and any(m['oid'] == building for m in inspectors.marks3d):
                return building
        self.fail('the checks\' mark never stayed')

    def grab(self):
        pump(40)
        image = self.win.grabWindow()
        return pixels(image), image.devicePixelRatio()

    def seen(self, bar, element):
        """How much of the element is seen inside the bar, where both of them draw: (pixels, share). A share of 0 is
        the bar alone, 1 the element over it. Four pictures, the bar and the element shown or not by their opacity
        (their places and the layout of the rest do not change)."""
        bar_opacity, element_opacity = bar.opacity(), element.opacity()

        def shot(b, e):
            bar.setOpacity(bar_opacity if b else 0)
            element.setOpacity(element_opacity if e else 0)
            return self.grab()
        try:
            (none, dpr), (alone, _), (under, _), (both, _) = shot(0, 0), shot(1, 0), shot(0, 1), shot(1, 1)
        finally:
            bar.setOpacity(bar_opacity)
            element.setOpacity(element_opacity)
        box = bar.mapRectToScene(bar.boundingRect())
        # inside the bar's rounded ends (a radius up to half its height: 0,15 of it from each side, and a pixel)
        inset = .15 * min(box.width(), box.height()) + 1
        x0, y0 = int((box.left() + inset) * dpr), int((box.top() + inset) * dpr)
        x1, y1 = int((box.right() - inset) * dpr), int((box.bottom() - inset) * dpr)
        cut = [image[max(0, y0):y1, max(0, x0):x1] for image in (none, alone, under, both)]
        none, alone, under, both = cut

        def far(a, b):
            return np.abs(a - b).sum(axis=2)
        where = (far(under, none) > 60) & (far(alone, none) > 60)
        to_bar, to_element = far(both, alone)[where].sum(), far(both, under)[where].sum()
        return int(where.sum() / (dpr * dpr)), float(to_bar / max(1, to_bar + to_element))

    def check(self, bars, elements, bring):
        """Each element under each bar: the failures, and the pairs that truly met (the guard is not empty). An
        element is found again after each move, and the pair tried again when its Repeater made its delegate anew
        in the middle of the pictures (the checks computed once more give new marks: «already deleted», 14/11/2026)."""
        failures, met = [], set()
        for bar_name, bar in bars:
            for element_name, finder in elements:
                for attempt in range(3):
                    try:
                        bring(finder(), bar)
                        element = finder()
                        self.assertIsNotNone(element, element_name)
                        count, share = self.seen(bar, element)
                        break
                    except RuntimeError as error:
                        if 'already deleted' not in str(error) or attempt == 2:
                            raise
                        pump(200)
                # met when at least 30 px of it are seen inside the bar, or half of the element when it is smaller:
                # R685 (Daniel 16/11/2026) made a corner's grip a point of Annotation.POINT = 4,5 px (it was 7), about
                # 16 px in all, which never reached 30
                if count < min(30, .5 * element.width() * element.height()):
                    continue
                met.add((bar_name, element_name))
                if share >= OVER:
                    failures.append(f'{element_name} over {bar_name}: {share:.2f} of it seen on {count} px')
        return failures, met

    # the plan

    def plan_bring(self, plan):
        def bring(element, bar):
            """The plan panned so that the element's middle is the bar's: the drawing and its marks move together."""
            if element.objectName() == 'property-side-highlight':
                a, b = element.property('a'), element.property('b')
                middle = plan.mapToScene(QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2))
            else:
                middle = element.mapToScene(QPointF(element.width() / 2, element.height() / 2))
            target = bar.mapToScene(QPointF(bar.width() / 2, bar.height() / 2))
            plan.setProperty('panX', plan.property('panX') + target.x() - middle.x())
            plan.setProperty('panY', plan.property('panY') + target.y() - middle.y())
            pump(30)
        return bring

    def plan_bars(self, plan):
        # the pointer on the plan, away from the bars, for its coordinates
        corner = plan.mapToScene(QPointF(plan.width() - 40, plan.height() / 2))
        mouse(self.app, self.win, QEvent.Type.MouseMove, corner, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
        pump(60)
        names = ('planViewBar', 'compass', 'scaleBar', 'planCursor', 'mapCredit')
        bars = [(name, self.find(name)) for name in names]
        self.assertFalse([name for name, bar in bars if bar is None], 'every bar over the plan is on screen')
        return bars

    def plan_ready(self, phase):
        self.win.setProperty('viewMode', 'plan')
        self.win.showPhase(phase)
        pump(300)
        plan = self.find('plan')
        self.assertIsNotNone(plan)
        # the map's tiles still to come would change the ground between the four pictures
        for layer in self.of_class(plan, 'MapLayer'):
            layer.setVisible(False)
        self.addCleanup(lambda: [layer.setVisible(True) for layer in self.of_class(plan, 'MapLayer')])
        return plan

    def test_the_strings_and_the_checks_marks_stand_under_the_bars_of_the_plan(self):
        """Daniel's case: in the Plant the strings' names passed over the pointer's coordinates."""
        plan = self.plan_ready('plant')
        self.show_mark()
        wait_for(lambda: bool(self.host.plan.marks), 5)
        pump(100)
        bars = self.plan_bars(plan)

        def string():
            # a string's name near the modules, its inverter's pill from far (R707): the strings' labels
            found = [i for i in items(plan) if i.isVisible() and (i.objectName() == 'stringLabel-name-0'
                                                                  or i.objectName().startswith('stringLabel-inverter-'))]
            return found[0] if found else None

        def mark():
            found = [i for i in plan.childItems() if i.metaObject().className().startswith('PlanSymbol') and i.isVisible()]
            return found[0] if found else None
        self.assertIsNotNone(string(), 'the strings\' names are on the plan')
        self.assertIsNotNone(mark(), 'a check\'s mark is on the plan')
        failures, met = self.check(bars, [('a string\'s name', string), ('a check\'s mark', mark)],
                                   self.plan_bring(plan))
        self.assertIn(('planCursor', 'a string\'s name'), met, 'Daniel\'s case was truly tried')
        self.assertEqual({name for name, _ in bars}, {bar for bar, _ in met}, 'each bar met an element')
        self.assertFalse(failures, '\n'.join(failures))

    def test_the_selection_s_marks_stand_under_the_bars_of_the_plan(self):
        """The side highlighted from the properties (PlanHost), a side's pill and a corner's grip."""
        plan = self.plan_ready('model')
        building = self.session.project.buildings[0].id
        self.session.select('building', building)
        self.host.plan.setTool('select')
        self.host.parts.controllers['inspectors'].highlight_side('building', building, 0)
        pump(200)
        bars = self.plan_bars(plan)
        elements = [('the side highlighted', lambda: self.find('property-side-highlight')),
                    ('a side\'s pill', lambda: self.find('sidePill0')), ('a grip', lambda: self.find('vertexGrip0'))]
        self.assertFalse([name for name, finder in elements if finder() is None], 'the selection\'s marks are on the plan')
        failures, met = self.check(bars, elements, self.plan_bring(plan))
        self.assertEqual({'the side highlighted', 'a side\'s pill', 'a grip'}, {e for _, e in met}, 'each element met a bar')
        self.assertFalse(failures, '\n'.join(failures))

    # the 3D view

    def test_the_checks_marks_stand_under_the_bars_of_the_3d_view(self):
        self.win.showPhase('model')
        self.win.setProperty('viewMode', '3d')
        pump(400)
        view = self.find('viewport3d')
        self.assertIsNotNone(view, 'the 3D view is on screen')
        building = self.show_mark()

        def mark():
            found = [i for i in items(view) if i.objectName() == 'scene-mark-building-' + building and i.isVisible()]
            return found[0] if found else None
        wait_for(lambda: mark() is not None, 10)
        bars = [('the view cube', self.of_class(view, 'ViewCube')), ('the tools', self.of_class(view, 'SceneToolbar')),
                ('the sun\'s bar', self.of_class(view, 'SunBar'))]
        self.assertFalse([name for name, found in bars if not found], 'every bar over the 3D view is on screen')
        bars = [(name, found[0]) for name, found in bars]

        def bring(element, bar):
            """The mark moved under the bar (it follows the camera, which is not what is tried here)."""
            target = element.parentItem().mapFromScene(bar.mapToScene(QPointF(bar.width() / 2, bar.height() / 2)))
            element.setProperty('x', target.x() - element.width() / 2)
            element.setProperty('y', target.y() - element.height() / 2)
            pump(30)
        failures, met = self.check(bars, [('a check\'s mark', mark)], bring)
        self.assertIn(('the view cube', 'a check\'s mark'), met)
        self.assertIn(('the tools', 'a check\'s mark'), met)
        self.assertFalse(failures, '\n'.join(failures))


class OneScale(unittest.TestCase):
    """The order between the drawing and the bars is the theme's scale, not numbers written in each file."""

    def test_the_scale_goes_from_the_drawing_to_the_dialogs(self):
        s = design.Stack
        self.assertLess(s.DRAWING, s.MARK)
        self.assertLess(s.MARK, s.LABEL)
        self.assertLess(s.LABEL, s.VIEW_BAR)
        self.assertLess(s.VIEW_BAR, s.VIEW_FRAME)
        self.assertLess(s.VIEW_FRAME, s.DIALOG)

    def test_the_overlay_s_scale_puts_meridio_over_the_windows_and_under_the_menus(self):
        # R628 (Daniel 15/11/2026: «non mi piace il fatto che non sia utilizzabile meridio» with a window open): in Qt's
        # overlay the popups stand by their z; Meridio's stage over the windows, his own window over him, the menus and
        # tooltips over them all, the «what's this» pointer over everything. Study 50: the fade of a page comes over
        # the page and the windows and under Meridio, who stays as he is while the page changes (over File too)
        s = design.Stack
        order = [s.WINDOW, s.TRANSITION, s.ASSISTANT, s.ASSISTANT_WINDOW, s.POPUP, s.PICKER]
        self.assertEqual(order, sorted(set(order)))

    def test_the_popups_take_their_step_by_name(self):
        controls = QML / 'Controls'
        for name, step in (('Dialog.qml', 'WINDOW'), ('Popup.qml', 'POPUP'), ('Menu.qml', 'POPUP'),
                           ('ToolTip.qml', 'POPUP')):
            with self.subTest(name=name):
                self.assertRegex((controls / name).read_text(encoding='utf-8'), r'\bz:\s*Theme\.stack\.' + step + r'\b')
        workbench = (QML / 'Shell' / 'Workbench.qml').read_text(encoding='utf-8')
        self.assertRegex(workbench, r'id: assistantStage[\s\S]{0,200}z: Theme\.stack\.ASSISTANT\b')

    def test_no_z_by_hand_in_the_plan_and_the_3d_view(self):
        written = re.compile(r'(?:^|[;{]\s*)z\s*:\s*([^;\n}]+)', re.MULTILINE)
        found = []
        for path in VIEW_FILES:
            text = path.read_text(encoding='utf-8')
            for match in written.finditer(text):
                value = match.group(1).strip()
                if value.startswith('Theme.stack.') or (path.name, value) in LOCAL_Z:
                    continue
                line = text.count('\n', 0, match.start(1)) + 1
                found.append(f'{path.relative_to(QML)}:{line}: z: {value}')
        self.assertFalse(found, 'a z written by hand where the theme\'s scale decides (Theme.stack, design.Stack):\n'
                         + '\n'.join(found))

    def test_the_local_ones_are_still_there(self):
        # a z listed as local and gone is a line of LOCAL_Z to take away
        for (name, value), _why in LOCAL_Z.items():
            path = next(p for p in VIEW_FILES if p.name == name)
            self.assertRegex(path.read_text(encoding='utf-8'), r'\bz\s*:\s*' + re.escape(value) + r'\b', name)


if __name__ == '__main__':
    unittest.main()
