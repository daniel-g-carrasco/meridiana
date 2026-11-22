"""R664 (Daniel 16/11/2026, the four counts at the head of the Checks: «di questi tre tasti è poco evidente quando sono
attivi e quando disattivi»; «This phase» and «This object»: «non dovrebbero essere linguette ma tasti»). A count is a
toggle of its level: on (shown) tinted with its tone, off on the bar's ground with a neutral hair and its number muted;
nought to count, faded and not a button. The two scopes are two common buttons that stay pressed while on, without the
frame of a choice."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtGui import QColor

import _setup
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


class Counts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1400, 860)
        cls.win.show()
        pump(800)
        cls.host.bridge.request_checks()
        wait_for(lambda: not cls.host.bridge.checks_feed.busy())
        cls.win.runCommand('focus_checks')
        pump(500)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def find(self, name):
        pending = [self.win.contentItem()]
        while pending:
            o = pending.pop()
            if o.objectName() == name and o.isVisible():
                return o
            pending.extend(o.childItems())
        return None

    def test_on_and_off_differ_in_their_ground(self):
        checks = self.host.parts.controllers['checks']
        self.assertEqual(checks.shownLevels, ['fail', 'warn', 'info', 'ok'], 'no filter: every level shown')
        counts = checks.counts
        lit = [lv for lv in ('fail', 'warn', 'info', 'ok') if counts.get(lv)]
        self.assertTrue(lit, 'some checks to count')
        level = lit[0]
        pill = self.find('checks-filter-' + level)
        self.assertTrue(pill.property('checked'))
        on = QColor(pill.property('color'))
        self.assertGreater(on.alpha(), 0, 'on: its tone\'s ground')
        checks.toggleLevel(level)
        pump(150)
        self.assertNotIn(level, checks.shownLevels, 'a click on a lit count hides its level')
        self.assertFalse(pill.property('checked'))
        off = QColor(pill.property('color'))
        self.assertEqual(off.alpha(), 0, 'off: the bar\'s ground, no tint')
        self.assertIn('«', pill.property('tip'))
        for other in lit[1:]:
            checks.toggleLevel(other)
        pump(150)
        self.assertEqual(checks.shownLevels, [lv for lv in ('fail', 'warn', 'info', 'ok') if lv not in lit],
                         'every level with checks hidden is not read as no filter')
        for lv in lit:
            checks.toggleLevel(lv)
        pump(150)
        self.assertEqual(checks.shownLevels, ['fail', 'warn', 'info', 'ok'], 'all shown again: no filter')
        for lv in ('fail', 'warn', 'info', 'ok'):
            if not counts.get(lv):
                with self.subTest(nought=lv):
                    self.assertFalse(self.find('checks-filter-' + lv).isEnabled(), 'nought to count: not a button')

    def test_the_scopes_are_two_buttons(self):
        scopes = self.find('checks-scopes')
        self.assertIsNotNone(scopes)
        self.assertFalse(scopes.metaObject().className().startswith('QQuickRectangle'), 'no frame round the two')
        for name in ('checks-phase', 'checks-object'):
            button = self.find(name)
            self.assertTrue(button.property('flat'))
            self.assertTrue(button.metaObject().className().startswith('Button'), 'the common button')


if __name__ == '__main__':
    unittest.main()
