"""R523 (Daniel 07/11/2026): with no sub-field selected, the Plant's «Panels» shows and changes the defaults of the next
sub-fields, and says so; with one selected, that sub-field, with «Use as defaults» and «Apply the defaults». The
sub-fields already drawn do not change with the defaults; the one drawn next, and its preview, take them."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from meridiana import i18n, manual, model
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import item, pump, wait_for

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def project():
    p = model.Project(name='Prova posa')
    p.site = model.Site(lat=45.52, lon=9.04, address='Rho (MI)')
    p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, fire=model.Fire(subject=True)))
    sf = p.new_subfield('s1', 'Esistente', [[2, 13], [14, 13], [14, 18], [2, 18]], 'b1', None)
    p.add_subfield(sf)
    manual.make_flush(p, sf)
    return p


def within(root, name):
    stack = [root]
    while stack:
        node = stack.pop()
        if node.objectName() == name and node.isVisible():
            return node
        stack.extend(node.childItems())
    return None


class Defaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project(), Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light', 'accent': 'indigo', 'backgrounds': 'grey'})
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.session = cls.host.bridge.session
        cls.panels = cls.host.parts.controllers['plantPanels']
        cls.actions = cls.host.parts.controllers['plantActions']
        cls.host.shell.trigger('phase_plant')
        pump(500)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.session.select('site', '')
        self.actions.openSection('panels')
        pump(400)

    def test_without_a_selection_the_panel_says_and_shows_the_defaults(self):
        self.assertEqual(self.panels.kind, 'defaults')
        side = item(self.win, 'plant-inspector')
        heading = within(side, 'plant-panels-heading')
        self.assertEqual(heading.property('text'), 'Predefinite per i prossimi sottocampi')
        wait_for(lambda: within(side, 'editor:params.mounting') is not None, 10)
        for name in ('editor:params.mounting', 'editor:module', 'editor:params.portrait', 'editor:params.gap',
                     'editor:params.pitch_mode', 'editor:fire_bands', 'action:defaults_profile'):
            self.assertIsNotNone(within(side, name), name)

    def test_a_default_changed_moves_no_sub_field_and_undoes(self):
        before = model._subfield_json(self.session.project.subfields[0])
        self.assertTrue(self.panels.commit('params.gap', '0,1'))
        self.assertTrue(self.panels.commit('params.mounting', 'east_west'))
        self.assertEqual(self.session.project.layout_defaults, {'params': {'gap': 0.1, 'mounting': 'east_west'}})
        self.assertEqual(model._subfield_json(self.session.project.subfields[0]), before)
        self.assertEqual(self.panels.field('params.gap').data['value'], 0.1)
        self.session.undo.undo()
        self.session.undo.undo()
        self.assertEqual(self.session.project.layout_defaults, {})

    def test_the_sub_field_drawn_next_takes_them_and_its_preview_too(self):
        self.assertTrue(self.panels.commit('params.portrait', False))
        self.assertTrue(self.panels.commit('params.mounting', 'east_west'))
        plan = self.host.plan
        ring = [[18, 2], [36, 2], [36, 9], [18, 9]]
        drawing = plan.drawing                  # the preview while drawing: the core's grid with the defaults
        keep = drawing.tool, drawing.options, drawing.project
        drawing.tool, drawing.options, drawing.project = 'subfield', {}, self.session.project
        try:
            shown = drawing.grid_values(ring)
        finally:
            drawing.tool, drawing.options, drawing.project = keep
        draft = self.session.project.new_subfield('_d', '', ring, 'b1', None)
        self.assertEqual(draft.params['mounting'], 'east_west')
        self.assertEqual(shown['count'], len(manual.corners(self.session.project, draft,
                                                            manual.grid(self.session.project, draft))))
        self.assertGreater(shown['count'], 0)
        plan.editor.apply_command(dict(type='polygon', tool='subfield', ring=ring, spec={}))
        drawn = self.session.project.subfields[-1]
        self.assertEqual((drawn.params['mounting'], drawn.params['portrait']), ('east_west', False))
        self.assertTrue(drawn.flush)
        self.assertEqual(self.session.project.subfields[0].params.get('mounting'), 'tilted_anchored')
        self.session.undo.undo()
        self.session.undo.undo()
        self.session.undo.undo()
        self.assertEqual(len(self.session.project.subfields), 1)

    def test_with_a_sub_field_selected_the_panel_is_its_own_and_gives_and_takes_the_defaults(self):
        self.session.select('subfield', 's1')
        pump(400)
        self.assertEqual(self.panels.kind, 'subfield')
        side = item(self.win, 'plant-inspector')
        self.assertEqual(within(side, 'plant-panels-heading').property('text'), 'Sottocampo «Esistente»')
        wait_for(lambda: within(side, 'action:defaults_take') is not None, 10)
        self.assertIsNotNone(within(side, 'action:defaults_apply'))
        self.session.project.subfields[0].params['gap'] = 0.05
        self.panels.trigger('defaults_take')
        self.assertEqual(self.session.project.layout_defaults, {'module': 'generic-450',
                                                                'params': {'alignment': 'aligned', 'gap': 0.05}})
        self.session.undo.undo()
        self.panels.trigger('defaults_apply')
        self.assertEqual(self.session.project.subfields[0].params, {'mounting': 'tilted_anchored',
                                                                    'alignment': 'aligned'})
        self.session.undo.undo()


if __name__ == '__main__':
    unittest.main()
