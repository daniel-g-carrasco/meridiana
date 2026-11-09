"""Shell commands reuse the core's catalogues and transaction boundary (R389)."""
import tempfile
import unittest
from pathlib import Path

from _fixtures import capannone
from meridiana import phases, shortcuts
from meridiana.quick.app import create_app
from meridiana.quick.bridge import Bridge
from meridiana.quick.backend.shell import ShellController


class ShellBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bridge = Bridge(capannone(), Path(self.temp.name))
        self.addCleanup(self.bridge.close)
        self.shell = ShellController(self.bridge)

    def test_phases_and_tools_are_the_catalogue_not_a_second_definition(self):
        self.assertEqual([p['id'] for p in self.shell.phases], phases.ids())
        for actual, expected in zip(self.shell.phases, phases.phases(), strict=True):
            self.assertEqual(actual['title'], expected.title)
            self.assertEqual([t['command'] for g in actual['groups'] for t in g['tools']],
                             [t.command for t in expected.tools()])
        self.assertEqual(set(self.shell.command_ids), {c.id for c in shortcuts.commands()})

    def test_variant_creation_switching_and_undo_are_real_project_edits(self):
        base = self.bridge.session.project.variant
        self.shell.trigger('new_variant')
        added = self.bridge.session.project.variant
        self.assertNotEqual(base, added)
        self.assertEqual(len(self.shell.variants), 2)
        self.shell.chooseVariant(base)
        self.assertEqual(self.bridge.session.project.variant, base)
        self.bridge.undo()
        self.assertEqual(self.bridge.session.project.variant, added)
        self.bridge.undo()
        self.assertEqual(len(self.shell.variants), 1)

    def test_unimplemented_command_is_explicit_and_can_be_registered(self):
        self.assertFalse(self.shell.available('import_ifc'))
        self.assertFalse(self.shell.trigger('import_ifc'))
        calls = []
        self.shell.register_command('import_ifc', lambda: calls.append('ifc'))
        self.assertTrue(self.shell.available('import_ifc'))
        self.assertTrue(self.shell.trigger('import_ifc'))
        self.assertEqual(calls, ['ifc'])

    def test_shortcuts_and_tooltips_use_translated_catalogue(self):
        model = self.shell.phases[0]
        self.assertEqual(model['title'], 'Modellazione')
        select = model['groups'][0]['tools'][0]
        self.assertEqual(select['label'], 'Seleziona')
        self.assertIn('V', select['tip'])

    def test_check_groups_and_filters_keep_core_order_and_targets(self):
        from meridiana.checks import Item
        self.bridge._checks = [vars(Item('ok','layout','Passed',target=('building','b1'))),
                               vars(Item('warn','production','Review',target=('phase','production'))),
                               vars(Item('info','rules','Explain',target=('building','b1')))]
        groups = self.shell.checkGroups('level', [], 'model', False, False)
        self.assertEqual([g['level'] for g in groups], ['warn','info','ok'])
        self.assertTrue(groups[-1]['closed'])
        self.bridge.select('building','b1','')
        groups = self.shell.checkGroups('object', ['info'], 'model', True, True)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['text'], 'Capannone')
        self.assertEqual(groups[0]['rows'][0]['text'], 'Explain')
        self.assertEqual(sum(c['count'] for c in self.shell.checkCounts), 3)
