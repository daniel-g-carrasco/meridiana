"""R30/R64/R67/R73/R136/R269/R389: project tree state and command parity."""
import copy
import unittest

import _setup
from _fixtures import capannone_rho
from meridiana import checks, jobs, model
from meridiana.quick.backend.project_tree import ProjectTreeBackend
from meridiana.session import ProjectSession


class ProjectTreeTest(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(capannone_rho())
        self.backend = ProjectTreeBackend(self.session)
        self.addCleanup(self.backend.close)

    def test_groups_counts_selection_and_row_selection(self):
        self.assertEqual([(r['oid'], r['count']) for r in self.backend.rows if r['group']],
                         [('building', 1), ('subfield', 1), ('exclusion', 2)])
        self.backend.select('building', 'b1')
        self.assertEqual(self.session.selection, ('building', 'b1'))
        self.backend.select('group', 'subfield')
        self.assertEqual(self.session.selection, ('building', 'b1'))
        self.session.select('row', 's1/r2')
        self.assertEqual((self.backend.selectionKind, self.backend.selectionId), ('subfield', 's1'))
        self.session.select('exclusion', 'e2')
        self.assertEqual(self.backend.selectionId, 'e2')

    def test_layout_tail_stale_error_and_no_layout_for_rename(self):
        self.backend.trigger('fill', 'subfield', 's1')
        results, keys, _ = jobs.layout_of(self.session.project)
        self.session.results, self.session.layout_keys = results, keys
        self.session.changed('layout:s1')
        row = lambda: next(r for r in self.backend.rows if r['kind'] == 'subfield')
        self.assertEqual(row()['state'], 'ok')
        self.assertIn(str(results['s1'].count), row()['tail'])
        before = copy.deepcopy(keys)
        self.backend.rename('subfield', 's1', 'New name')
        self.assertEqual(self.session.layout_keys, before)
        # The existing core includes the name in layout_key: preserve its state.
        self.assertEqual(row()['state'], self.session.layout_state(self.session.project.subfields[0]))
        self.session.edit('geometry', lambda p: setattr(p.buildings[0], 'height', 12))
        self.assertEqual(row()['state'], 'stale')
        self.session.results['s1'] = ValueError('layout failed')
        self.session.layout_keys['s1'] = self.session.project.layout_key(self.session.project.subfields[0])
        self.session.changed('layout:s1')
        self.assertEqual(row()['state'], 'error')

    def test_mark_aggregates_click_and_group_does_not_select(self):
        items = [checks.Item('warn', 'layout', 'Warning', target=('subfield', 's1')),
                 checks.Item('fail', 'layout', 'Failure', target=('subfield', 's1'))]
        self.backend.set_checks(items)
        rows = {(r['kind'], r['oid']): r for r in self.backend.rows}
        for target in [('site', ''), ('group', 'subfield'), ('subfield', 's1')]:
            self.assertEqual((rows[target]['markLevel'], rows[target]['markCount']), ('fail', 2))
        calls = []
        self.backend.checksRequested.connect(lambda *args: calls.append(args))
        self.backend.activateMark('group', 'subfield')
        self.assertEqual(self.session.selection, ('site', ''))
        self.assertEqual(calls[0][:2], ('group', 'subfield'))
        self.backend.activateMark('subfield', 's1')
        self.assertEqual(self.session.selection, ('subfield', 's1'))

    def test_mutations_undo_and_building_children(self):
        self.session.project.props.append(model.Prop(id='o1', kind='person', at=[2, 2], building='b1'))
        self.backend.refresh()
        self.assertTrue(any(r['kind'] == 'prop' for r in self.backend.rows))
        before = self.session.snapshot()
        self.backend.trigger('delete', 'building', 'b1')
        self.assertFalse(self.session.project.buildings)
        self.assertFalse(self.session.project.subfields)
        self.assertFalse(self.session.project.exclusions)
        self.assertFalse(self.session.project.props)
        self.backend.undo()
        restored = self.session.snapshot()
        before.pop('modified', None); restored.pop('modified', None)
        self.assertEqual(restored, before)
        self.backend.redo()
        self.assertFalse(self.session.project.buildings)

    def test_variants_copy_switch_rename_delete_and_undo(self):
        first = self.session.project.variant
        self.backend.newVariant('Second')
        second = self.session.project.variant
        self.backend.rename('subfield', 's1', 'Changed')
        self.backend.switchVariant(first)
        self.assertEqual(self.session.project.subfields[0].name, 'Sud')
        self.backend.renameVariant(second, 'Other')
        self.backend.deleteVariant(second)
        self.assertEqual(len(self.backend.variants), 1)
        self.backend.undo()
        self.assertEqual(self.backend.variants[-1]['name'], 'Other')
        self.backend.switchVariant(second)
        self.assertEqual(self.session.project.subfields[0].name, 'Changed')
        self.backend.deleteVariant(second)
        self.assertEqual(len(self.backend.variants), 2)

    def test_all_object_context_commands_and_pitch_creation(self):
        commands = {a['id'] for a in self.backend.actions('building', 'b1') if not a['separator']}
        self.assertEqual(commands, {'properties', 'frame', 'pitches', 'rename', 'duplicate', 'square', 'delete'})
        self.assertEqual(self.backend.actions('group', 'building'), [])
        self.backend.trigger('pitches', 'building', 'b1')
        self.assertEqual(len(self.session.project.subfields), 2)
        self.assertEqual(self.session.project.subfields[-1].building, 'b1')
        self.backend.trigger('duplicate', 'exclusion', 'e1')
        self.assertEqual(len(self.session.project.exclusions), 3)
        self.assertEqual(self.session.selection[0], 'exclusion')
        self.assertFalse(self.backend.rename('building', 'b1', '  '))

    def test_manual_explode_empty_refill_relayout_and_undo(self):
        self.backend.trigger('fill', 'subfield', 's1')
        results, keys, _ = jobs.layout_of(self.session.project)
        self.session.results, self.session.layout_keys = results, keys
        self.assertTrue(self.backend.trigger('explode', 'subfield', 's1'))
        self.assertTrue(self.session.project.subfields[0].manual)
        self.backend.trigger('empty', 'subfield', 's1')
        self.assertFalse(self.session.project.subfields[0].filled)
        self.backend.trigger('relayout', 'subfield', 's1')
        self.assertFalse(self.session.project.subfields[0].manual)
        self.backend.undo()
        self.assertTrue(self.session.project.subfields[0].manual)


class ProjectTreeParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_real_widgets_commands_match_quick_project_undo_and_selection(self):
        from quick.parity.differential import Adapter, canonical_project, run_scenario, undo_snapshot
        from meridiana.paths import Paths
        import tempfile
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name)
        paths = Paths(**{k: folder / k for k in ('config', 'state', 'data', 'cache')})
        w = _setup.window(self, capannone_rho(), paths=paths)
        b = ProjectTreeBackend(ProjectSession(copy.deepcopy(w.project)))
        self.addCleanup(b.close)

        def observe(session):
            return {'project': canonical_project(session.project), 'undo': undo_snapshot(session),
                    'selection': tuple(session.selection)}

        left = Adapter('Widgets', {'select': w._select, 'rename': lambda value: w._rename(*w.selection, name=value),
                                   'delete': w._delete, 'duplicate': lambda: w._duplicate(*w.selection),
                                   'undo': w.undo.undo, 'redo': w.undo.redo}, lambda: observe(w.session))
        right = Adapter('Quick', {'select': b.select, 'rename': lambda value: b.rename(*b.session.selection, value),
                                  'delete': lambda: b.trigger('delete', *b.session.selection),
                                  'duplicate': lambda: b.trigger('duplicate', *b.session.selection),
                                  'undo': b.undo, 'redo': b.redo}, lambda: observe(b.session))
        steps = [{'command': 'select', 'args': {'kind': 'building', 'oid': 'b1'}},
                 {'command': 'rename', 'args': {'value': 'New building'}}, {'command': 'undo'}, {'command': 'redo'},
                 {'command': 'duplicate'}, {'command': 'delete'}, {'command': 'undo'}, {'command': 'redo'}]
        result = run_scenario({'id': 'tree-R389', 'observations': ['project', 'undo', 'selection'], 'steps': steps}, left, right)
        self.assertEqual(result['status'], 'equal', result)


setUpModule = _setup.keep_global_state
