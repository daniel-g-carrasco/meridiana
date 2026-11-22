"""Inactive inverters take one row; the selected inverter stays readable; an error folds like the others (R687)."""
import copy
import unittest

import _setup
from PySide6.QtCore import QMetaObject
from quick.aiuti.differential import connected_fixture
from quick.gestures import click, item, point, pump
from quick.impianto.panel_fixture import PanelFixture

setUpModule = _setup.keep_global_state


class Folding(unittest.TestCase):
    def setUp(self):
        project = connected_fixture()
        project.energy['inverters'][0]['count'] = 3
        self.panel = PanelFixture(project)
        self.addCleanup(self.panel.close)

    def card(self, number):
        return item(self.panel.window, f'inverter-card-{number}')

    def test_only_the_working_inverter_starts_expanded(self):
        self.panel.backend.selectUnit(1)
        pump(250)
        self.assertTrue(self.card(1).property('expanded'))
        self.assertFalse(self.card(3).property('expanded'))
        row = item(self.panel.window, 'inverter-header-3')
        self.assertEqual(self.card(3).height(), row.height())
        self.assertLess(row.height(), 50)

    def test_same_header_opens_and_closes_without_editing_project(self):
        before = copy.deepcopy(self.panel.session.project.to_json())
        row = item(self.panel.window, 'inverter-header-3')
        click(self.panel.app, self.panel.window, point(row))
        pump(250)
        self.assertTrue(self.card(3).property('expanded'))
        self.assertGreater(self.card(3).height(), row.height())
        click(self.panel.app, self.panel.window, point(row))
        pump(250)
        self.assertFalse(self.card(3).property('expanded'))
        self.assertEqual(self.panel.session.project.to_json(), before)

    def test_switching_working_inverter_resets_manual_folds(self):
        self.panel.backend.selectUnit(3)
        pump(250)
        self.assertTrue(self.card(3).property('expanded'))
        self.panel.backend.selectUnit(1)
        pump(250)
        self.assertFalse(self.card(3).property('expanded'))

    def test_a_failure_folds_like_the_others(self):
        # R687 (Daniel 16/11/2026: «il primo inverter rimane sempre esteso»): an inverter with an error starts folded
        # like the others, its red mark says it; a click opens it and closes it again.
        self.panel.session.edit('Lower voltage limit', lambda p: p.energy['inverters'][0]['record'].update(
            dc_voltage_max_v=100))
        self.panel.settle()
        self.panel.backend.selectUnit(3)
        pump(250)
        self.assertEqual(self.panel.backend.units[0]['level'], 'fail')
        self.assertFalse(self.card(1).property('expanded'))
        header = item(self.panel.window, 'inverter-header-1')
        click(self.panel.app, self.panel.window, point(header))
        pump(250)
        self.assertTrue(self.card(1).property('expanded'))
        # the second click as the header's own handler takes it: synthetic clicks carry no time, so two of them
        # always make a double click (a rename) for Qt's tap handler
        QMetaObject.invokeMethod(self.card(1), 'toggle')
        pump(250)
        self.assertFalse(self.card(1).property('expanded'))

    def test_hidden_controls_are_disabled_and_reduced_motion_is_immediate(self):
        self.panel.engine._meridiana_theme_tokens.configure({'reducedMotion': True})
        card = self.card(3)
        self.assertFalse(item(self.panel.window, 'inverter-name-3').isEnabled())
        click(self.panel.app, self.panel.window, point(item(self.panel.window, 'inverter-header-3')))
        pump(10)
        self.assertGreater(card.height(), item(self.panel.window, 'inverter-header-3').height())
