"""R625 (Daniel 15/11/2026, Linux, «NON SI APRE LA SCHEDA INVERTER»): every section of the Plant panel shows what it
holds when opened, in the real window.

The failure itself (the Inverter section's body thrown away by Qt half made while the panel was warmed in the
background, Workbench.qml) was reproduced in the real window with the first start of Daniel's Rho, the year computed,
then the Plant phase and its Inverter section: offscreen and on Direct3D 11, about a minute each, too long for the
suite (the script and its runs: meridiana-prove/r35-pagina-vuota/guida.py). The mending, M.WholeLoader, is proved
on Qt's own failure in quick/controlli/test_whole_loader_r625.py."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import Q_ARG, QMetaObject
from PySide6.QtQml import QQmlExpression, qmlContext
from meridiana import i18n
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import item, pump, wait_for

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')       # as test_plant_side.py, for the plant's jobs

def status(loader):
    """A Loader's status (an enum PySide cannot convert), read through QML: 1 Ready, 2 Loading, 3 Error."""
    value, _undefined = QQmlExpression(qmlContext(loader), loader, "status").evaluate()
    return int(value)


def walk(node):
    yield node
    for child in node.childItems():
        yield from walk(child)


def loader_in(node):
    return next(n for n in walk(node) if n is not node and 'Loader' in n.metaObject().className())


class Sections(unittest.TestCase):
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
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.plant = cls.host.parts.controllers['plant']
        cls.actions = cls.host.parts.controllers['plantActions']
        cls.show('plant')
        wait_for(lambda: not cls.plant.busy and cls.plant.units, 60)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    @classmethod
    def show(cls, phase):
        QMetaObject.invokeMethod(cls.win, 'showPhase', Q_ARG('QVariant', phase))
        pump(300)

    def section(self, key):
        node = item(self.win, 'plant-section-' + key).parentItem()
        while node is not None and node.property('sectionControl') is not True:     # R633: the head is a SectionHead
            node = node.parentItem()
        return node

    def test_every_section_shows_what_it_holds_when_opened(self):
        self.show('plant')
        for key in ('panels', 'inverter', 'storage'):
            self.actions.openSection(key)
            pump(400)
            section = self.section(key)
            body = loader_in(section)
            self.assertEqual(status(body), 1, key)
            self.assertGreater(body.property('item').implicitHeight(), 20, key)
            head = item(self.win, 'plant-section-' + key)
            self.assertGreater(section.height(), head.height() + 20, key)


if __name__ == '__main__':
    unittest.main()
