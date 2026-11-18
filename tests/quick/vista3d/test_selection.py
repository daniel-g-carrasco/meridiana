"""3D selection parity with Widgets: module/row, roof surfaces and hierarchical Esc."""
from pathlib import Path
import tempfile
import unittest

import _setup
import numpy as np

from meridiana import jobs, model, viewaids
from meridiana.quick.backend.scene import SceneBackend
from meridiana.session import ProjectSession


setUpModule = _setup.keep_global_state


class SelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        project = model.Project()
        project.buildings = [model.Building('b', 'Roof', [[0, 0], [30, 0], [30, 20], [0, 20]], height=6)]
        project.subfields = [model.SubField('s', 'Panels', [[1, 1], [20, 1], [20, 18], [1, 18]],
                                           building='b', filled=True)]
        self.session = ProjectSession(project)
        results, keys, _ = jobs.layout_of(project, {})
        self.session.layout_done(self.session.generation, results, keys)
        self.scene = SceneBackend(self.session, Path(self.tmp.name))
        self.addCleanup(self.scene.close)

    def test_repeated_click_on_same_module_selects_row_then_module(self):
        # R529: another module of the same row is that module (as the hover shows); the module selected, its row
        modules = self.session.good_results()['s'].modules
        first = modules[0]
        same = next(i for i, m in enumerate(modules) if m.rid == first.rid and m.key != first.key)
        other = next(i for i, m in enumerate(modules) if m.rid != first.rid)
        before = self.scene.rebuilds
        self.scene.pick('modules', same, 0, 0, 0)
        self.assertEqual(self.session.selected_module, ('s', modules[same].key))
        self.scene.pick('modules', 0, 0, 0, 0)
        self.assertEqual(self.session.selected_module, ('s', first.key))
        self.scene.pick('modules', 0, 0, 0, 0)
        self.assertEqual(self.session.selection, ('row', 's/' + first.rid))
        self.assertEqual(self.session.selected_module, ('', ''))
        np.testing.assert_allclose(self.scene.selectionEdges,
                                   viewaids.outline(self.session.project, self.session.good_results(),
                                                    'row', 's/' + first.rid))
        self.scene.pick('modules', same, 0, 0, 0)
        self.assertEqual(self.session.selected_module, ('s', modules[same].key))
        self.scene.pick('modules', other, 0, 0, 0)
        self.assertEqual(self.session.selected_module, ('s', modules[other].key))
        self.assertEqual(self.scene.rebuilds, before)
        self.assertEqual(self.session.undo.count(), 0)

    def test_point_pick_priorities_module_empty_subfield_and_roof(self):
        project = self.session.project
        module = self.session.good_results()['s'].modules[0]
        x, north = module.centre
        self.scene.pick('buildings', -1, x, module.z, -north)
        self.assertEqual(self.session.selected_module, ('s', module.key))
        project.subfields.append(model.SubField('empty', 'Empty', [[22, 2], [28, 2], [28, 10], [22, 10]], building='b'))
        self.scene.rebuild()
        self.scene.pick('buildings', -1, 25, 6, -5)
        self.assertEqual(self.session.selection, ('subfield', 'empty'))
        self.assertEqual(self.session.selected_module, ('', ''))
        self.scene.pick('buildings', -1, 29, 6, -15)
        self.assertEqual(self.session.selection, ('building', 'b'))
        project.exclusions.append(model.ExclusionItem('e', [[24, 4], [26, 4], [26, 6], [24, 6]], building='b'))
        self.scene.rebuild()
        self.scene.pick('buildings', -1, 25, 7, -5)
        self.assertEqual(self.session.selection, ('exclusion', 'e'))

    def test_wall_uses_nearest_outline_and_only_inside_half_metre(self):
        project = self.session.project
        project.buildings.append(model.Building('next', 'Next', [[31, 0], [40, 0], [40, 20], [31, 20]], height=6))
        self.scene.rebuild()
        self.scene.pick('buildings', -1, 30.2, 3, -12)
        self.assertEqual(self.session.selection, ('building', 'b'))
        self.scene.pick('buildings', -1, -0.51, 3, -12)
        self.assertEqual(self.session.selection, ('site', ''))
        self.scene.pick('', -1, 10, 6, -10)
        self.assertEqual(self.session.selection, ('site', ''))

    def test_free_pitch_outside_footprint_selects_its_building_as_widgets(self):
        b = self.session.project.buildings[0]
        b.roof = model.Roof(type='free', free_pitches=[{'id': 'p', 'ring': [[32, 1], [36, 1], [36, 8], [32, 8]],
                                                      'eave_side': 0, 'eave': 6, 'tilt': 15}])
        self.session.project.subfields = []
        self.scene.rebuild()
        self.scene.pick('buildings', -1, 34, 7, -4)
        self.assertEqual(self.session.selection, ('building', 'b'))

    def test_escape_module_row_subfield_building_site_and_move_tool(self):
        self.scene.pick('modules', 0, 0, 0, 0)
        before = self.scene.rebuilds
        self.assertEqual(self.scene.escapeSelection(True), 'tool')
        self.assertTrue(self.session.selected_module[0])
        for expected in (('subfield', 's'), ('building', 'b'), ('site', '')):
            self.assertEqual(self.scene.escapeSelection(), 'selection')
            self.assertEqual(self.session.selection, expected)
            self.assertEqual(self.session.selected_module, ('', ''))
        self.assertEqual(self.scene.escapeSelection(), '')
        self.assertEqual(self.scene.rebuilds, before)
        self.session.select('row', 's/arbitrary-row')
        self.assertEqual(self.scene.escapeSelection(), 'selection')
        self.assertEqual(self.session.selection, ('subfield', 's'))

    def test_escape_cancels_preview_then_tool_without_leaving_vertex_selection(self):
        self.session.select('building', 'b')
        before = self.session.snapshot()
        old = self.scene.triangles[0].copy()
        self.scene.beginVertex(0, False)
        self.scene.previewVertex(2)
        self.assertEqual(self.scene.escapeSelection(True), 'edit')
        self.assertEqual(self.session.snapshot(), before)
        np.testing.assert_array_equal(self.scene.triangles[0], old)
        self.assertFalse(any(v['selected'] for v in self.scene.vertices))
        self.assertEqual(self.session.selection, ('building', 'b'))
        self.assertEqual(self.scene.escapeSelection(True), 'tool')
        self.scene.selectVertices([0, 1], False)
        self.assertEqual(self.scene.escapeSelection(False), 'vertices')
        self.assertFalse(any(v['selected'] for v in self.scene.vertices))
        self.assertEqual(self.session.selection, ('building', 'b'))
        self.assertEqual(self.session.undo.count(), 0)

    def test_escape_hosted_and_ground_objects_and_external_pitch_selection(self):
        p = self.session.project
        p.exclusions.append(model.ExclusionItem('e', [[2, 2], [3, 2], [3, 3], [2, 3]], building='b'))
        p.props.append(model.Prop('o', kind='broadleaf', at=[40, 30]))
        for selection, expected in ((('exclusion', 'e'), ('building', 'b')),
                                    (('prop', 'o'), ('site', '')),
                                    (('pitch', 'b:0'), ('building', 'b'))):
            self.session.select(*selection)
            self.assertEqual(self.scene.escapeSelection(), 'selection')
            self.assertEqual(self.session.selection, expected)

    def test_same_point_picks_and_escape_chain_as_hidden_widgets_plan(self):
        from meridiana.ui.plan import PlanView, to_scene

        p = self.session.project
        p.subfields.append(model.SubField('empty', 'Empty', [[22, 2], [28, 2], [28, 10], [22, 10]], building='b'))
        p.exclusions.append(model.ExclusionItem('e', [[24, 4], [26, 4], [26, 6], [24, 6]], building='b'))
        p.props.append(model.Prop('o', kind='broadleaf', at=[25, 5], building='b'))
        self.scene.rebuild()
        plan = PlanView(Path(self.tmp.name))
        self.addCleanup(_setup.dispose, plan)
        plan.show_project(p, self.session.good_results())
        module = self.session.good_results()['s'].modules[0]
        for east, north in (module.centre, (23, 9), (25, 5), (29, 17), (70, 80)):
            kind, oid, key = plan._pick(to_scene(east, north))
            self.session.select('site', '')
            self.scene.pick('buildings', -1, east, 7, -north)
            expected = ('subfield', oid) if kind == 'module' else (kind or 'site', oid)
            self.assertEqual(self.session.selection, expected)
            self.assertEqual(self.session.selected_module, (oid, key) if kind == 'module' else ('', ''))
        plan.set_selection('subfield', 's')
        plan.selected_module = ('s', module.key)
        self.session.select('subfield', 's', ('s', module.key))
        for _ in range(4):
            moved = plan.selection_back()
            self.assertEqual(self.scene.escapeSelection(), 'selection' if moved else '')
            self.assertEqual(self.session.selection, plan.selection)
            self.assertEqual(self.session.selected_module, plan.selected_module)


if __name__ == '__main__':
    unittest.main()
