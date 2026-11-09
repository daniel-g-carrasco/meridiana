"""R377/R389: real Session edits and the Widgets' field contracts."""
import copy
import unittest

from _fixtures import capannone
from meridiana.session import ProjectSession


class PropertiesTest(unittest.TestCase):
    def setUp(self):
        from meridiana.quick.backend.properties import PropertiesBackend
        self.session = ProjectSession(capannone())
        self.backend = PropertiesBackend(self.session)
        self.addCleanup(self.backend.close)

    def select_building(self):
        self.session.select('building', self.session.project.buildings[0].id)

    def test_quantity_edits_and_undo_are_one_step(self):
        self.select_building()
        original = self.session.project.buildings[0].height
        self.assertTrue(self.backend.commit('height', '8 m + 30 cm'))
        self.assertAlmostEqual(self.session.project.buildings[0].height, 8.3)
        self.assertEqual(self.session.undo.count(), 1)
        self.backend.undo()
        self.assertEqual(self.session.project.buildings[0].height, original)
        self.backend.redo()
        self.assertEqual(self.session.project.buildings[0].height, 8.3)

    def test_invalid_quantities_leave_project_and_undo_untouched(self):
        self.select_building()
        before = self.session.snapshot()
        for text in ('oops', '0.1 m', '400 m', '2 deg', 'nan'):
            self.assertFalse(self.backend.commit('height', text), text)
            self.assertEqual(self.session.snapshot(), before)
            self.assertEqual(self.session.undo.count(), 0)
            self.assertTrue(self.backend.error)

    def test_same_shape_reuses_fields_but_selection_invalidates_drafts(self):
        self.select_building()
        old = self.backend.field('height')
        epoch = self.backend.epoch
        other = copy.deepcopy(self.session.project.buildings[0])
        other.id = 'second'
        other.height = 15
        self.session.project.buildings.append(other)
        self.session.select('building', other.id)
        self.assertIs(self.backend.field('height'), old)
        self.assertEqual(old.data['value'], 15)
        self.assertFalse(self.backend.commit('height', '22', epoch))
        self.assertEqual(other.height, 15)

    def test_roof_change_updates_shape_and_rejects_low_ridge(self):
        self.select_building()
        self.assertTrue(self.backend.commit('roof.type', 'gable'))
        building = self.session.project.buildings[0]
        self.assertIsNotNone(self.backend.field('roof.ridge_height'))
        self.assertFalse(self.backend.commit('roof.ridge_height', str(building.height)))
        self.assertTrue(self.backend.commit('roof.ridge_height', str(building.height + 2)))
        self.assertTrue(self.backend.commit('roof.percent', '40'))
        self.assertIsNone(building.roof.ridge_height)

    def test_vvf_activity_and_categories_are_coherent(self):
        from meridiana import vvf_activities as vvf
        self.select_building()
        self.assertTrue(self.backend.commit('fire.activity', 75))
        fire = self.session.project.buildings[0].fire
        self.assertTrue(fire.subject)
        self.assertEqual(fire.activity, 75)
        allowed = [c for c in vvf.CATEGORIES if vvf.activity(75).category_text(c)]
        self.assertTrue(self.backend.commit('fire.category', allowed[0]))
        self.assertTrue(self.backend.commit('fire.subject', False))
        self.assertEqual((fire.subject, fire.activity, fire.category), (False, 0, ''))

    def test_site_network_sync_and_names(self):
        self.assertTrue(self.backend.commit('name', '  Test  '))
        self.assertEqual(self.session.project.name, 'Test')
        self.assertTrue(self.backend.commit('name', '   '))
        self.assertEqual(self.session.project.name, 'Test')
        self.assertTrue(self.backend.commit('network.voltage_v', '20000'))
        self.assertEqual(self.session.project.network.voltage_v, 20000)
        self.assertTrue(self.backend.commit('reserved', True))
        self.assertTrue(self.backend.commit('consent.tiles', True))
        self.assertIn('tiles', self.session.project.network_consent)

    def test_subfield_gates_and_sun_window(self):
        sf = self.session.project.subfields[0]
        self.session.select('subfield', sf.id)
        self.assertFalse(self.backend.commit('params.azimuth', 22))
        self.assertTrue(self.backend.commit('automatic', False))
        self.assertTrue(self.backend.commit('params.azimuth', '22°'))
        self.assertEqual(sf.params['azimuth'], 22)
        self.assertTrue(self.backend.commit('params.mounting', 'ground'))
        self.assertTrue(self.backend.commit('params.pitch_mode', 'sun'))
        self.assertTrue(self.backend.commit('window.day', '15'))
        self.assertEqual(sf.params['window']['day'], 15)
        self.backend.trigger('sun_all')
        self.assertEqual(self.session.project.sun_window['day'], 15)
        self.assertNotIn('window', sf.params)

    def test_numeric_locale_matches_widgets_group_separators(self):
        from meridiana import i18n
        old = i18n.language()
        self.addCleanup(i18n.setup, old)
        for language, text in [('en', '1,000 V'), ('it', '1.000 V')]:
            i18n.setup(language)
            self.assertTrue(self.backend.commit('network.voltage_v', text))
            self.assertEqual(self.session.project.network.voltage_v, 1000)

    def test_support_plane_edit_preserves_elevation_at_area_centre(self):
        from meridiana.quick.backend.properties_schema import support_reference
        sf = self.session.project.subfields[0]
        self.session.select('subfield', sf.id)
        self.assertTrue(self.backend.commit('support.enabled', True))
        self.assertTrue(self.backend.commit('support.z0', '12 m'))
        self.assertTrue(self.backend.commit('support.tilt', '20°'))
        x, y = support_reference(self.session.project, sf)
        self.assertAlmostEqual(sf.support.surface().z(x, y), 12)
        self.backend.undo()
        self.assertEqual(self.session.project.subfields[0].support.tilt, 0)

    def test_free_roof_numbers_remove_corner_heights_and_validate_ridge(self):
        from meridiana.model import Roof
        b = self.session.project.buildings[0]
        b.roof = Roof(type='free', free_pitches=[dict(ring=[[0, 0], [10, 0], [10, 5], [0, 5]],
            eave_side=0, eave=4., tilt=20., z=[4., 4., 5., 5.])])
        self.select_building()
        self.assertFalse(self.backend.commit('free.0.ridge', '3m'))
        self.assertTrue(self.backend.commit('free.0.percent', '40'))
        self.assertNotIn('z', b.roof.free_pitches[0])
        self.backend.trigger('free.0.swap')
        self.assertEqual(b.roof.free_pitches[0]['eave_side'], 2)

    def test_relayout_confirmation_cannot_apply_to_another_selection_or_project(self):
        sf = self.session.project.subfields[0]
        sf.manual = True
        self.session.select('subfield', sf.id)
        self.backend.trigger('relayout')
        self.assertTrue(self.backend.confirmation)
        self.session.select('site', '')
        self.assertFalse(self.backend.confirm('accept'))
        self.assertTrue(sf.manual)
        self.session.select('subfield', sf.id)
        self.backend.trigger('relayout')
        self.backend.commit('name', 'Changed since the confirmation')
        self.assertFalse(self.backend.confirm('accept'))
        self.assertTrue(sf.manual)
        self.backend.trigger('relayout')
        self.assertTrue(self.backend.confirm('accept'))
        self.assertFalse(sf.manual)
        self.backend.undo()
        self.assertTrue(self.session.project.subfields[0].manual)


if __name__ == '__main__':
    unittest.main()


class FormsKeptTest(unittest.TestCase):
    """One form for each shape, kept alive (06/11/2026): back on a shape already seen, the same fields are shown
    again with their values changed, and QML is told of a new form only once per shape."""

    def setUp(self):
        from meridiana.quick.backend.properties import PropertiesBackend
        self.session = ProjectSession(capannone())
        self.backend = PropertiesBackend(self.session)
        self.addCleanup(self.backend.close)
        self.added = []
        self.backend.formAdded.connect(self.added.append)

    def test_a_shape_seen_again_keeps_its_fields_and_adds_no_form(self):
        site = self.backend.currentForm
        site_field = self.backend.field('name') if 'name' in self.backend._fields else None
        self.session.select('building', self.session.project.buildings[0].id)
        building = self.backend.currentForm
        height = self.backend.field('height')
        self.assertNotEqual(site, building)
        self.assertEqual(len(self.added), 1)
        self.session.select('site', '')
        self.assertEqual(self.backend.currentForm, site)
        if site_field is not None:
            self.assertIs(self.backend.field('name'), site_field)
        self.session.select('building', self.session.project.buildings[0].id)
        self.assertEqual(self.backend.currentForm, building)
        self.assertIs(self.backend.field('height'), height)
        self.assertEqual(len(self.added), 1)
        self.assertEqual(set(self.backend.formKeys), {site, building})
        self.assertEqual([s['key'] for s in self.backend.formSections(building)],
                         [s['key'] for s in self.backend.sections])
