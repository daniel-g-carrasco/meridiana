"""R631 (Daniel 15/11/2026, the Plant panel beside Properties on his laptop: «come mai i margini della scheda destra, con
il posizionamento della barra di scorrimento, sono molto diversi da quella in Impianto? dove sarebbe l'armonizzazione e
la centralizzazione richiesta?»): the side panels have one body, M.PanelPage.

A. On the real window, in every phase and every section of the Plant: the sections of every side panel stand at the
   same margins from the card (within 1 px), the panel has one vertical scroll at most, it is its page (no bar inside a
   section, R601), and its bar stands at the same place.
B. In the files: a side panel's body is an M.PanelPage and builds no frame of its own (no ScrollPage, Flickable or
   margins of its own); what it lays in its sections scrolls nothing; the panels that are not made of sections are
   listed with their reason.

    python -m unittest quick.shell.test_pannelli_r631
"""
import os
import re
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QPointF
from meridiana import i18n
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import pump, wait_for

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')       # as test_plant_side.py, for the plant's jobs

QML = Path(__file__).resolve().parents[3] / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana'
PANELS = ('rightPanel', 'leftPanel', 'checksPanel')

# The bodies of the side panels: each is an M.PanelPage (the Plant's, Properties', the data of Production,
# Consumption and Balance, Deliverables, and the shell's own Properties when no part gives one).
BODIES = ('Plant/PlantSide.qml', 'Properties/PropertiesPage.qml', 'Charts/ResultInspector.qml',
          'Report/ReportInspector.qml', 'Shell/PropertiesPanel.qml')
# What those bodies lay in their sections, as wide as the page: no scroll and no margins of their own. A window opened
# from them scrolls its own body (R607): the ListView of the datasheet's window in PlantInverters.
CONTENTS = {'Properties/PropertyForm.qml': 0, 'Charts/ResultForm.qml': 0, 'Plant/PlantInverters.qml': 1}
# The files the shell loads into a side panel (the parts' sources, Workbench.qml), each with the body it is made of, or
# the reason it has none.
HOSTS = {
    'Plant/PlantSide.qml': 'Plant/PlantSide.qml',
    'Properties/PropertiesHost.qml': 'Properties/PropertiesPage.qml',
    'Charts/ProductionInspector.qml': 'Charts/ResultInspector.qml',
    'Charts/ConsumptionInspector.qml': 'Charts/ResultInspector.qml',
    'Charts/EconomicsInspector.qml': 'Charts/ResultInspector.qml',
    'Report/WorkbenchReportInspector.qml': 'Report/ReportInspector.qml',
    'Shell/PropertiesPanel.qml': 'Shell/PropertiesPanel.qml',
}
NOT_SECTIONS = {
    'ProjectTree/ProjectTreeHost.qml': 'the project tree is a list (M.Tree): one scroll, its own, and no sections',
    'Checks/ChecksHost.qml': 'the checks are a list (a ListView with M.ScrollBar, rule 2): one scroll, no sections',
    'Charts/InactiveInspector.qml': 'not a body: the binding that keeps a hidden inspector laid out (charts_part.py)',
}
# a frame of its own: a page that scrolls, the margins of a page (leftMargin, rightMargin) or round the whole body
FRAME = re.compile(r'\bM\.ScrollPage\b|\bFlickable\s*\{|\bScrollView\b|\banchors\.margins\s*:'
                   r'|(?<!anchors\.)\b(?:left|right)Margin\s*:')


def strip_comments(text):
    return '\n'.join(line.split('//', 1)[0] for line in text.splitlines())


def walk(node):
    if not node.isVisible() or node.width() <= 0 or node.height() <= 0:
        return
    yield node
    for child in node.childItems():
        yield from walk(child)


def scrolls_vertically(o):
    meta = o.metaObject()
    if meta.indexOfProperty('contentY') < 0 or meta.indexOfProperty('flickableDirection') < 0:
        return False
    if o.property('interactive') is False:
        return False
    return o.property('contentHeight') > o.property('height') + 1


def inside(node, test):
    parent = node.parentItem()
    while parent is not None:
        if test(parent):
            return True
        parent = parent.parentItem()
    return False


def is_section(o):
    return o.property('sectionControl') is True


class Window(unittest.TestCase):
    """A. The panels as drawn."""

    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('en')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light', 'reducedMotion': True})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        # low enough that the Plant's Modules and Properties need their scroll
        cls.win.resize(1400, 760)
        cls.win.show()
        cls.plant = cls.host.parts.controllers['plant']
        cls.actions = cls.host.parts.controllers['plantActions']

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def panels(self):
        return [o for o in walk(self.win.contentItem()) if o.objectName() in PANELS and o.property('panelId')]

    def measure(self, card, scene, out):
        items = list(walk(card))
        sections = [o for o in items if is_section(o) and not o.property('nested') and o.property('framed') is not False]
        scrollers = [o for o in items if scrolls_vertically(o)]
        where = f'{scene} {card.objectName()}'
        self.assertLessEqual(len(scrollers), 1, f'{where}: more than one scroll {[s.objectName() for s in scrollers]}')
        for s in scrollers:
            self.assertFalse(inside(s, is_section), f'{where}: a scroll inside a section ({s.objectName()})')
            self.assertFalse(inside(s, scrolls_vertically), f'{where}: a scroll inside a scroll')
        if not sections:
            return
        if scrollers:
            out.setdefault('scrolling', set()).add(where)
            page = scrollers[0].parentItem()
            self.assertTrue(page.property('panelBody'), f'{where}: the panel scrolls with something else than M.PanelPage')
            bar = next((o for o in items if 'ScrollBar' in o.metaObject().className() and o.property('flickable') == scrollers[0]), None)
            self.assertIsNotNone(bar, where)
            self.assertFalse(inside(bar, is_section), f'{where}: the bar is inside a section')
            out.setdefault('bar', {})[where] = round(card.width() - bar.mapToItem(card, QPointF(bar.width(), 0)).x(), 1)
        left = min(s.mapToItem(card, QPointF(0, 0)).x() for s in sections)
        right = min(card.width() - s.mapToItem(card, QPointF(s.width(), 0)).x() for s in sections)
        out.setdefault('left', {})[where] = round(left, 1)
        out.setdefault('right', {})[where] = round(right, 1)

    def test_every_side_panel_has_the_same_body(self):
        out = {}
        for phase in ('model', 'plant', 'production', 'consumption', 'economics', 'report'):
            self.host.shell.trigger('phase_' + phase)
            pump(900)
            scenes = [(phase, None)]
            if phase == 'plant':
                wait_for(lambda: not self.plant.busy and self.plant.units, 60)
                scenes = [('plant ' + key, key) for key in ('panels', 'inverter', 'storage')]
            for scene, key in scenes:
                if key:
                    self.actions.openSection(key)
                    pump(700)
                found = self.panels()
                self.assertTrue(any(p.objectName() == 'rightPanel' for p in found), scene)
                for card in found:
                    self.measure(card, scene, out)
        # the sections were measured where they are made of sections, and the panel did scroll where it had to
        for scene in ('model rightPanel', 'plant panels rightPanel', 'plant inverter rightPanel',
                      'production rightPanel', 'economics rightPanel'):
            self.assertIn(scene, out['left'])
        self.assertIn('plant panels rightPanel', out['scrolling'])
        self.assertIn('model rightPanel', out['scrolling'])
        for side in ('left', 'right', 'bar'):
            values = out[side]
            low, high = min(values.values()), max(values.values())
            self.assertLessEqual(high - low, 1, f'{side}: {values}')


class Files(unittest.TestCase):
    """B. No panel builds its frame by itself."""

    def read(self, name):
        return strip_comments((QML / name).read_text(encoding='utf-8'))

    def test_a_panels_body_is_a_panel_page_and_builds_no_frame_of_its_own(self):
        for name in BODIES:
            text = self.read(name)
            self.assertTrue('M.PanelPage' in text, f'{name} is not an M.PanelPage')
            self.assertEqual(FRAME.findall(text), [], name)

    def test_what_a_body_lays_in_its_sections_scrolls_nothing(self):
        for name, windows in CONTENTS.items():
            text = self.read(name)
            self.assertEqual(FRAME.findall(text) + re.findall(r'\bM\.PanelPage\b', text), [], name)
            self.assertEqual(len(re.findall(r'\bListView\s*\{', text)), windows, name)

    def test_every_file_the_shell_puts_in_a_side_panel_is_known(self):
        hosts = {str(p.relative_to(QML)).replace(os.sep, '/') for p in QML.glob('*/*Inspector.qml')}
        hosts |= {'Plant/PlantSide.qml', 'Properties/PropertiesHost.qml', 'Shell/PropertiesPanel.qml',
                  'ProjectTree/ProjectTreeHost.qml', 'Checks/ChecksHost.qml'}
        unknown = sorted(h for h in hosts if h not in HOSTS and h not in NOT_SECTIONS and h not in BODIES)
        self.assertEqual(unknown, [], 'a side panel not in HOSTS (its body) nor in NOT_SECTIONS (with its reason)')
        for host, body in HOSTS.items():
            self.assertIn(body, BODIES, host)
            self.assertEqual(FRAME.findall(self.read(host)), [], host)


if __name__ == '__main__':
    unittest.main()
