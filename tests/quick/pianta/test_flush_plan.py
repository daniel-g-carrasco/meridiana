"""The sub-field as its modules in the plan's backend (R445, R473): drawn with the Sub-field tool the modules show as
the outline is drawn and the sub-field is made of them; a side of it dragged (beginSide, dragSide, endSide) shows the
modules that would come and go as green and red ghosts with their count, and one undo gives the sub-field back; a side
of a building dragged stays parallel; the modules set aside on an obstacle are drawn red; the fire-brigade bands as
guides and as obstacles from the menu."""
import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from meridiana import model
from meridiana.quick.backend.plan import PlanController

APP = None


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication([])


class FlushPlan(unittest.TestCase):
    def setUp(self):
        p = model.Project(name='Flush')
        p.buildings.append(model.Building(id='b1', name='Roof', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                          fire=model.Fire(subject=True)))
        p.exclusions.append(model.ExclusionItem(id='e1', ring=[[18, 8], [22, 8], [22, 12], [18, 12]], kind='vent',
                                                building='b1'))
        self.p = p
        self.c = PlanController(p, manage_layout=False)
        self.c.viewSettled(-5, -5, 45, 25, 0.05, 1.0)
        self.c.setPhase('plant')

    def tearDown(self):
        self.c.close()

    def lay(self):
        self.c.session.results = {sf.id: self.p.fill(sf) for sf in self.p.subfields}
        self.c.editor.set_results(self.c.session.results)
        self.c.drawing.set_results(self.c.session.results)
        self.c.refresh()

    def draw(self, ring):
        self.c.setTool('subfield')
        for x, y in ring:
            self.c.pointer(x, y, 1, 0.05)        # Ctrl: no snap
            self.c.click(x, y, 1)
        self.c.pointer(ring[0][0], ring[0][1], 1, 0.05)
        self.c.click(ring[0][0], ring[0][1], 1)

    def test_drawing_shows_the_modules_and_makes_the_sub_field_of_them(self):
        self.c.setTool('subfield')
        for x, y in ((5, 3), (30, 3), (30, 15)):
            self.c.pointer(x, y, 1, 0.05)
            self.c.click(x, y, 1)
        self.c.pointer(5, 15, 1, 0.05)
        seen = self.c.preview
        self.assertEqual(seen['tool'], 'subfield')
        self.assertGreater(seen['modules']['count'], 50)              # tilted rows on a flat roof
        self.assertTrue(any('modul' in line for line in seen['card']['lines']))
        self.c.click(5, 15, 1)
        self.c.click(5, 3, 1)
        sf = self.p.subfields[0]
        self.assertTrue(sf.flush and sf.manual and sf.filled)
        self.assertEqual(len(sf.rows), 3)
        self.assertEqual(self.c.editor.selection, ('subfield', sf.id))
        self.assertEqual(self.c.tool, 'subfield')             # the tool stays, for the next one

    def test_fill_an_area_draws_the_sub_field_of_before(self):
        self.c.activateTool('subfield', {'fill': 'area'})
        for x, y in ((5, 3), (30, 3), (30, 15), (5, 15), (5, 3)):
            self.c.pointer(x, y, 1, 0.05)
            self.c.click(x, y, 1)
        sf = self.p.subfields[0]
        self.assertFalse(sf.flush or sf.manual)
        self.assertEqual(sf.ring, [[5, 3], [30, 3], [30, 15], [5, 15]])

    def test_a_side_dragged_shows_ghosts_with_their_count_and_one_undo_takes_it_back(self):
        self.draw([(5, 3), (30, 3), (30, 15), (5, 15)])
        self.lay()
        sf = self.p.subfields[0]
        self.c.editor.select('subfield', sf.id)
        self.c.refresh()
        east = max(x for x, _y in sf.ring)
        side = self.c.sideAt(east, 9.0, 0.05)
        self.assertGreaterEqual(side, 0)
        self.assertEqual(self.c.sideAt(east, max(y for _x, y in sf.ring), 0.05), -1)      # the corner wins
        self.assertEqual(self.c.sideAt(17.0, 9.0, 0.05), -1)                               # the middle: nothing
        before = {m.key: m.centre for m in self.c.session.results[sf.id].modules}
        self.c.beginSide(side, east, 9.0)
        self.assertEqual(self.c.tool, 'side')
        self.c.dragSide(east + 2.4, 9.0, 1)
        seen = self.c.preview
        self.assertEqual(seen['type'], 'side')
        rows = len(sf.rows)                                     # tilted rows on the flat roof: 3 of 21
        self.assertEqual((seen['added'], seen['removed']), (2 * rows, 0))
        self.assertEqual(len(seen['add']), 2 * rows)
        ghosts = [o for o in self.c.draftObjects if o['kind'] == 'ghost']
        self.assertEqual(len(ghosts), 2 * rows)
        self.assertIn(f'+{2 * rows}', ' '.join(seen['card']['lines']))
        self.c.dragSide(east - 1.0, 9.0, 1)
        seen = self.c.preview
        self.assertEqual((seen['added'], seen['removed']), (0, rows))
        self.c.endSide(east - 1.0, 9.0, 1)
        self.assertEqual(self.c.tool, 'select')
        self.assertEqual(self.c.error, '')
        self.lay()
        after = {m.key: m.centre for m in self.c.session.results[sf.id].modules}
        self.assertEqual(len(after), len(before) - rows)
        for key, centre in after.items():
            self.assertEqual(centre, before[key])
        self.assertLess(max(x for x, _y in sf.ring), east - 0.9)
        self.c.session.undo.undo()
        back = self.c.session.project.subfields[0]
        self.assertAlmostEqual(max(x for x, _y in back.ring), east, places=3)
        self.assertEqual({m.key for m in self.c.session.project.fill(back).modules}, set(before))

    def test_a_measure_typed_moves_the_side_by_that_much(self):
        self.draw([(5, 3), (30, 3), (30, 15), (5, 15)])
        self.lay()
        sf = self.p.subfields[0]
        self.c.editor.select('subfield', sf.id)
        self.c.refresh()
        north = max(y for _x, y in sf.ring)
        side = self.c.sideAt(17.0, north, 0.05)
        pitch = self.c.session.results[sf.id].pitch                 # one row more: a pitch, and a hair
        rows, places = len(sf.rows), len(sf.rows[0]['places'])
        self.c.beginSide(side, 17.0, north)
        typed = str(round(pitch + 0.05, 2)).replace('.', ',')
        for ch in typed:
            self.c.key(ch, ch, 0)
        self.assertIn(typed + '_', ' '.join(self.c.preview['card']['lines']))
        self.assertEqual(self.c.preview['added'], places)
        self.c.key('Return', '', 0)
        self.assertEqual(self.c.tool, 'select')
        self.assertEqual(len(self.c.session.project.subfields[0].rows), rows + 1)

    def test_escape_leaves_everything_as_it_was(self):
        self.draw([(5, 3), (30, 3), (30, 15), (5, 15)])
        self.lay()
        sf = self.p.subfields[0]
        self.c.editor.select('subfield', sf.id)
        self.c.refresh()
        ring = [list(q) for q in sf.ring]
        self.c.beginSide(self.c.sideAt(17.0, 3.0, 0.05), 17.0, 3.0)
        self.c.dragSide(17.0, 6.0, 1)
        self.c.key('Escape', '', 0)
        self.assertEqual(self.c.tool, 'select')
        self.assertEqual(sf.ring, ring)
        self.assertEqual(self.c.preview, {})

    def test_a_building_side_dragged_stays_parallel(self):
        self.c.setPhase('modelling')
        self.c.editor.select('building', 'b1')
        self.c.refresh()
        side = self.c.sideAt(40.0, 10.0, 0.05)
        self.assertEqual(side, 1)
        self.c.beginSide(side, 40.0, 10.0)
        self.c.dragSide(45.0, 12.0, 1)
        self.assertEqual(self.c.preview['rings'][0], [[0.0, 0.0], [45.0, 0.0], [45.0, 20.0], [0.0, 20.0]])
        self.c.endSide(45.0, 12.0, 1)
        self.assertEqual(self.p.buildings[0].footprint, [[0.0, 0.0], [45.0, 0.0], [45.0, 20.0], [0.0, 20.0]])
        self.c.session.undo.undo()
        self.assertEqual(self.c.session.project.buildings[0].footprint, [[0, 0], [40, 0], [40, 20], [0, 20]])

    def test_the_modules_on_the_vent_are_drawn_red_and_the_guides_are_on_the_plan(self):
        self.draw([(5, 3), (30, 3), (30, 15), (5, 15)])
        self.lay()
        kinds = [o['kind'] for o in self.c.objects]
        self.assertIn('blocked', kinds)
        self.assertEqual(kinds.count('fire_guide'), 2)
        red = next(o for o in self.c.objects if o['kind'] == 'blocked')
        self.assertEqual(len(red['points']), 4)

    def test_the_menu_adds_the_bands_as_obstacles(self):
        self.c.setPhase('modelling')
        self.c.contextAt(10.0, 10.0)
        commands = [r['command'] for r in self.c.contextItems if not r['separator']]
        self.assertIn('fire_bands', commands)
        self.c.contextCommand('fire_bands')
        self.assertEqual([e.kind for e in self.p.exclusions].count('band'), 4)
        self.c.contextCommand('fire_bands')
        self.assertEqual([e.kind for e in self.p.exclusions].count('band'), 4)
        self.c.session.undo.undo()
        self.assertEqual([e.kind for e in self.c.session.project.exclusions].count('band'), 0)


if __name__ == '__main__':
    unittest.main()
