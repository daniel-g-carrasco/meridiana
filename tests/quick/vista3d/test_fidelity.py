"""R96/R359/R360/R365: the live Quick data against what the Widgets' sun bar said (recorded on 10/11/2026,
quick/aiuti/riferimenti.py)."""
from pathlib import Path
import tempfile
import unittest

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from meridiana import i18n
from meridiana.app import jobs
from meridiana.core.model import model
from meridiana.gui.backend.scene import SceneBackend
from meridiana.app.session import ProjectSession
from quick.aiuti import riferimenti


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

    def test_initial_design_day_and_apparent_sun_match_widgets(self):
        actual = self.backend.sunData
        riferimenti.check(self, {key: actual[key] for key in ('month', 'day', 'hour', 'elevation', 'short',
                                                               'description')}, relative=1e-7)

    def test_play_day_matches_ten_minute_step_and_sunrise_wrap(self):
        self.backend.setSun(2026, 12, 21, 0)
        self.backend.playSun(True)
        hours = [self.backend.sunData['hour']]
        self.backend.stepSun()
        hours.append(self.backend.sunData['hour'])
        riferimenti.check(self, hours)

    def test_the_hour_rests_on_ten_minutes(self):
        """Daniel 17/11/2026: «io terrei 10 minuti, al minuto è troppo granulare»: the slider, the wheel and Play all
        on the same ten-minute grid."""
        self.backend.setSun(2026, 7, 10, (14 * 60 + 37) / 60)
        self.assertEqual(self.backend.sunData['clock'], '14:40')
        self.backend.stepSun()
        self.assertEqual(self.backend.sunData['clock'], '14:50')

    def test_site_change_resets_to_design_but_rename_keeps_chosen_hour(self):
        self.backend.setSun(2026, 7, 10, 15)
        self.session.edit('Rename', lambda p: setattr(p, 'name', 'Renamed'))
        self.assertEqual(self.backend.sunData['hour'], 15)
        self.session.edit('Site', lambda p: setattr(p.site, 'lon', p.site.lon + 2))
        riferimenti.check(self, [self.backend.sunData['day'], self.backend.sunData['hour']])

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
                # through session.edit, as the program changes it: a write behind its back leaves the jobs' photo behind
                field = model.SubField('s1','Field',[[0,0],[10,0],[10,8],[0,8]],filled=False,manual=manual,
                                       removed=['r0c0'])
                self.session.edit('Field', lambda p, field=field: setattr(p, 'subfields', [field]))
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
