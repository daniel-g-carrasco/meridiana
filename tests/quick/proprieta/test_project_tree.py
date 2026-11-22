"""R30/R64/R67/R73/R136/R269/R389: project tree state and command parity."""
import copy
import unittest

import _setup
from _fixtures import capannone_rho
from meridiana.app import jobs
from meridiana.core.model import model
from meridiana.gui.backend.project_tree import ProjectTreeBackend
from meridiana.app.session import ProjectSession


class ProjectTreeTest(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(capannone_rho())
        self.backend = ProjectTreeBackend(self.session)
        self.addCleanup(self.backend.close)

    def test_groups_counts_selection_and_row_selection(self):
        # R575: the sub-field and the exclusions under their building, closed at first
        self.assertEqual([(r['kind'], r['oid'], r['depth']) for r in self.backend.rows],
                         [('site', '', 0), ('group', 'building', 0), ('building', 'b1', 1)])
        self.assertEqual([(r['oid'], r['count']) for r in self.backend.rows if r['group']], [('building', 1)])
        self.backend.select('building', 'b1')
        self.assertEqual(self.session.selection, ('building', 'b1'))
        self.backend.select('group', 'building')
        self.assertEqual(self.session.selection, ('building', 'b1'))
        self.session.select('row', 's1/r2')
        self.assertEqual((self.backend.selectionKind, self.backend.selectionId), ('subfield', 's1'))
        self.assertIn(('subfield', 's1'), [(r['kind'], r['oid']) for r in self.backend.rows])
        self.session.select('exclusion', 'e2')
        self.assertEqual(self.backend.selectionId, 'e2')
        self.assertEqual([(r['kind'], r['oid'], r['depth']) for r in self.backend.rows][2:],
                         [('building', 'b1', 1), ('subfield', 's1', 2), ('fold', 'exclusions:b1', 2),
                          ('exclusion', 'e2', 3), ('exclusion', 'e1', 3)])     # by name: «Roof plant» before «Smoke vent»

    def test_layout_tail_stale_error_and_no_layout_for_rename(self):
        self.backend.trigger('fill', 'subfield', 's1')
        results, keys, _ = jobs.layout_of(self.session.project)
        self.session.results, self.session.layout_keys = results, keys
        self.session.changed('layout:s1')
        row = lambda: next(r for r in self.backend.rows if r['kind'] == 'subfield')
        self.assertEqual(row()['state'], 'ok')
        self.assertIn(str(results['s1'].count), row()['tail'])
        # R665: a sub-field says its modules and their kWp
        kw = results['s1'].count * self.session.project.module_of(self.session.project.subfields[0]).power_kw
        self.assertEqual(row()['value'], f"{results['s1'].count} · {kw:.1f} kWp")
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

    def test_no_marks_of_the_checks_and_group_does_not_select(self):
        # R604: the tree no longer shows how many checks each object has, failing layouts included; a refresh does not
        # gather the checks and a change of the checks does not rebuild it
        self.backend.trigger('fill', 'subfield', 's1')
        self.session.results['s1'] = ValueError('layout failed')
        self.session.layout_keys['s1'] = self.session.project.layout_key(self.session.project.subfields[0])
        self.backend.setOpen('building:b1', True)
        self.backend.setOpen('exclusions:b1', True)
        rows = self.backend.rows
        self.assertEqual({r['kind'] for r in rows}, {'site', 'group', 'building', 'subfield', 'fold', 'exclusion'})
        self.assertEqual([r for r in rows if any(k.startswith('mark') for k in r)], [])
        self.assertEqual(next(r for r in rows if r['kind'] == 'subfield')['state'], 'error')     # its own symbol stays
        for gone in ('set_checks', 'activateMark', 'markWidth', 'checksRequested', 'checksManyRequested'):
            self.assertFalse(hasattr(self.backend, gone), gone)
        made = []
        self.backend.changed.connect(lambda: made.append(1))
        self.session.changed('checks')
        self.assertEqual(made, [])
        self.backend.select('group', 'building')                 # a group's row is not chosen
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
        # R564: the menus say what the panel says (layout_commands.entries): an empty sub-field by hand is filled
        # again with its rows, «Lay again automatically» is for one laid
        self.assertNotIn('relayout', [a['id'] for a in self.backend.actions('subfield', 's1')])
        self.assertTrue(self.backend.trigger('fill', 'subfield', 's1'))
        self.assertTrue(self.session.project.subfields[0].filled and self.session.project.subfields[0].manual)
        self.assertTrue(self.backend.trigger('relayout', 'subfield', 's1'))
        self.assertFalse(self.session.project.subfields[0].manual)
        self.backend.undo()
        self.assertTrue(self.session.project.subfields[0].manual)


class ProjectTreeParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_real_widgets_commands_match_quick_project_undo_and_selection(self):
        # after every command, the project, the undo and the selection the Widgets had (recorded on 10/11/2026)
        from quick.aiuti import riferimenti
        from quick.aiuti.differential import undo_snapshot
        from meridiana.core.model import model
        project = capannone_rho()
        b = ProjectTreeBackend(ProjectSession(model.Project.from_json(copy.deepcopy(project.to_json()))))
        self.addCleanup(b.close)
        steps = [lambda: b.select('building', 'b1'), lambda: b.rename(*b.session.selection, 'New building'),
                 b.undo, b.redo, lambda: b.trigger('duplicate', *b.session.selection),
                 lambda: b.trigger('delete', *b.session.selection), b.undo, b.redo]
        for step in steps:
            step()
            riferimenti.check(self, {'project': riferimenti.project(b.session.project),
                                     'undo': undo_snapshot(b.session), 'selection': tuple(b.session.selection)})

setUpModule = _setup.keep_global_state
