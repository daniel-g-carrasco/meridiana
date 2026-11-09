"""R96/R359/R360/R365: compare the live Quick data with the Widgets reference."""
from pathlib import Path
import tempfile
import unittest

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from meridiana import i18n, jobs, model
from meridiana.quick.backend.scene import SceneBackend
from meridiana.session import ProjectSession
from meridiana.ui.sunbar import SunBar


class SunFidelityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        i18n.setup('it')
        QLocale.setDefault(QLocale('it_IT'))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.session = ProjectSession(model.Project())
        self.backend = SceneBackend(self.session, Path(self.tmp.name))
        self.addCleanup(self.backend.close)
        self.reference = SunBar()
        p = self.session.project
        self.reference.set_site(p.site.lat, p.site.lon, p.sun_window)
        self.addCleanup(self.reference.deleteLater)

    def test_initial_design_day_and_apparent_sun_match_widgets(self):
        actual = self.backend.sunData
        self.assertEqual((actual['month'], actual['day']),
                         (self.reference.day.date().month(), self.reference.day.date().day()))
        self.assertAlmostEqual(actual['hour'], self.reference.hour.value() / 6)
        self.assertAlmostEqual(actual['elevation'], self.reference.position().apparent)
        self.assertEqual(actual['short'], self.reference.short.text())
        self.assertEqual(actual['description'], self.reference.words.text())

    def test_play_day_matches_ten_minute_step_and_sunrise_wrap(self):
        self.backend.setSun(2026, 12, 21, 0)
        self.reference.hour.setValue(0)
        self.reference._toggle(True)
        self.backend.playSun(True)
        self.assertAlmostEqual(self.backend.sunData['hour'], self.reference.hour.value() / 6)
        self.reference._tick()
        self.backend.stepSun()
        self.assertAlmostEqual(self.backend.sunData['hour'], self.reference.hour.value() / 6)
        self.reference.timer.stop()

    def test_site_change_resets_to_design_but_rename_keeps_chosen_hour(self):
        self.backend.setSun(2026, 7, 10, 15)
        self.session.edit('Rename', lambda p: setattr(p, 'name', 'Renamed'))
        self.assertEqual(self.backend.sunData['hour'], 15)
        self.session.edit('Site', lambda p: setattr(p.site, 'lon', p.site.lon + 2))
        p = self.session.project
        self.reference.set_site(p.site.lat, p.site.lon, p.sun_window)
        self.assertEqual(self.backend.sunData['day'], self.reference.day.date().day())
        self.assertAlmostEqual(self.backend.sunData['hour'], self.reference.hour.value() / 6)

    def test_bad_date_leaves_sun_in_place_and_reports_error(self):
        old = dict(self.backend.sunData)
        self.backend.setSun(2026, 2, 31, 12)
        self.assertEqual(self.backend.sunData, old)
        self.assertTrue(self.backend.error)

    def test_context_commands_edit_the_same_session_and_undo(self):
        p=self.session.project
        p.buildings.append(model.Building('b1','Shed',[[0,0],[10,0],[10,8],[0,8]],height=5))
        self.backend.rebuild()
        self.session.select('building','b1')
        self.assertIn('duplicate',[a['key'] for a in self.backend.contextActions])
        before=self.session.snapshot()
        self.backend.contextCommand('duplicate','')
        self.assertEqual(len(self.session.project.buildings),2)
        self.session.undo.undo()
        self.assertEqual(self.session.snapshot(),before)
        self.session.select('building','b1')
        self.backend.contextCommand('rename','Named')
        self.assertEqual(self.session.project.building('b1').name,'Named')
        self.session.undo.undo()
        self.backend.contextCommand('delete','')
        self.assertFalse(self.session.project.buildings)
        self.session.undo.undo()
        self.assertEqual(self.session.snapshot(),before)

    def test_row_menu_and_relayout_use_the_existing_layout_rules(self):
        p = self.session.project
        p.subfields = [model.SubField('s1','Field',[[0,0],[30,0],[30,20],[0,20]],filled=True)]
        results, keys, _skipped = jobs.layout_of(p,{})
        self.session.layout_done(self.session.generation,results,keys)
        module = results['s1'].modules[0]
        self.session.select('subfield','s1',('s1',module.key))
        actions = [a['key'] for a in self.backend.contextActions]
        self.assertIn('select_row',actions)
        self.assertIn('explode_row',actions)
        self.assertNotIn('turn_row',actions)
        before = self.session.snapshot()
        self.backend.contextCommand('explode_row','')
        self.assertFalse(self.backend.error)
        self.assertTrue(self.session.project.subfields[0].manual)
        self.session.undo.undo()
        self.assertEqual(self.session.snapshot(),before)
        self.session.select('subfield','s1')
        self.backend.contextCommand('explode','')
        self.assertTrue(self.session.project.subfields[0].manual)
        self.backend.contextCommand('relayout','')
        self.assertFalse(self.session.project.subfields[0].manual)
        self.assertEqual(self.session.project.subfields[0].rows,[])
        self.assertEqual(self.session.project.subfields[0].removed,[])
        self.assertFalse(self.backend.error)

    def test_fill_restores_automatic_modules_but_keeps_manual_omissions(self):
        for manual in (False,True):
            with self.subTest(manual=manual):
                self.session.project.subfields = [model.SubField('s1','Field',[[0,0],[10,0],[10,8],[0,8]],
                                                               filled=False,manual=manual,removed=['r0c0'])]
                self.session.select('subfield','s1')
                before=self.session.snapshot()
                self.backend.contextCommand('fill','')
                field=self.session.project.subfields[0]
                self.assertTrue(field.filled)
                self.assertEqual(field.removed,['r0c0'] if manual else [])
                self.session.undo.undo()
                self.assertEqual(self.session.snapshot(),before)


if __name__ == '__main__':
    unittest.main()
