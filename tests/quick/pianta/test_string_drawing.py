"""R467: the string being drawn by hand and the string labels, pure scene and installed window."""
import math
import unittest

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtTest import QTest

import _setup
from meridiana.app.session import ProjectSession
from meridiana.gui.backend.plan_edit import PlanEditor
from quick.aiuti.puntini import assert_dots_follow, dots_layer
from quick.pianta import test_edit
from quick.pianta import test_edit_window as edit

setUpModule = edit.setUpModule


def rows_of(result):
    rows = {}
    for m in result.modules:
        rows.setdefault(round(m.centre[1], 3), []).append(m)
    return [sorted(r, key=lambda m: m.centre[0]) for _y, r in sorted(rows.items())]


class DraftScene(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(test_edit.project())
        self.editor = PlanEditor(self.session)
        self.result = self.session.project.fill(self.session.project.subfields[0])
        self.editor.set_results({"s1": self.result})
        self.editor.set_phase("plant")
        self.row = rows_of(self.result)[0][:4]

    def draft_of(self, count):
        e = self.editor
        e.start_draft()
        for m in self.row[:count]:
            e.click(m.centre)
        return e.wiring_scene(.02)

    def test_draft_modules_look_like_a_finished_string_and_only_the_last_is_outlined(self):
        scene = self.draft_of(3)
        fills = [o for o in scene["objects"] if o.get("draft") and o["kind"] == "string_fill"]
        self.assertEqual(len(fills), 3)
        self.assertEqual({o["stroke"] for o in fills}, {"transparent"}, "no outline on every module")
        self.assertEqual({o["fill"][-2:] for o in fills}, {f"{140:02x}"}, "the alpha of a finished string")
        current = [o for o in scene["objects"] if o["kind"] == "string_current"]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["fill"], "transparent")
        last = self.row[2].corners
        self.assertEqual(current[0]["points"], [[float(x), -float(y)] for x, y in last])
        red = [o["points"] for o in scene["objects"] if o["kind"] == "unwired"]
        for m in self.row[:3]:
            self.assertNotIn([[float(x), -float(y)] for x, y in m.corners], red, "being wired: not red")

    def test_draft_shows_its_direction_with_one_arrow_for_each_leg(self):
        scene = self.draft_of(3)
        arrows = [o for o in scene["objects"] if o["kind"] == "string_arrow"]
        self.assertEqual(len(arrows), 2)
        for arrow, (a, b) in zip(arrows, zip(self.row, self.row[1:], strict=False), strict=False):
            tip = arrow["points"][0]
            ax, ay, bx, by = a.centre[0], -a.centre[1], b.centre[0], -b.centre[1]
            self.assertLess(math.dist(tip, (bx, by)), math.dist(tip, (ax, ay)), "the tip points to the next module")
            self.assertTrue(arrow["closed"])

    def test_numbers_carry_the_string_direction(self):
        scene = self.draft_of(3)
        numbers = [x for x in scene["labels"] if x["kind"] == "number" and x.get("draft")]
        self.assertEqual([x["number"] for x in numbers], [1, 2, 3])
        a, b = self.row[0].centre, self.row[2].centre
        along = ((b[0]-a[0]) / math.dist(a, b), (b[1]-a[1]) / math.dist(a, b))
        for x in numbers:
            self.assertAlmostEqual(math.hypot(x["dirX"], x["dirY"]), 1.0)
            self.assertAlmostEqual(x["dirX"]*along[0]+x["dirY"]*along[1], 1.0, places=6)

    def test_a_finished_chosen_string_gets_arrows_too_the_others_do_not(self):
        rows = rows_of(self.result)
        self.session.project.energy["strings"] = {"runs": [
            {"inverter": 1, "mppt": 1, "modules": ["s1/" + m.key for m in rows[0][:4]]},
            {"inverter": 1, "mppt": 2, "modules": ["s1/" + m.key for m in rows[1][:4]]}]}
        self.editor.chosen_string = 0
        arrows = [o for o in self.editor.wiring_scene(.02)["objects"] if o["kind"] == "string_arrow"]
        self.assertEqual(len(arrows), 3)
        self.assertEqual({o["run"] for o in arrows}, {0})


def covers(rect, centre, radius=4.0):
    qx = min(max(centre.x(), rect.left()), rect.right())
    qy = min(max(centre.y(), rect.top()), rect.bottom())
    return (qx-centre.x())**2 + (qy-centre.y())**2 < radius**2


class LabelsWindow(unittest.TestCase):
    setUp = edit.EditWindowTest.setUp
    tearDown = edit.EditWindowTest.tearDown
    visual = edit.EditWindowTest.visual

    def descendants(self, item):
        for child in item.childItems():
            yield child
            yield from self.descendants(child)

    def strings(self, count=8):
        rows = rows_of(self.result)
        self.session.edit('String fixture', lambda p: p.energy.update(strings={'runs': [
            {'inverter': 1, 'mppt': 1 + i, 'modules': ['s1/' + m.key for m in rows[i][:count]]} for i in range(3)]}))
        self.controller.setPhase('plant')
        return rows

    def dots(self):
        return [self.plan.screen(d['x'], d['y']) for d in self.controller.dots]

    def labels(self, kind):
        out = []
        for o in self.descendants(self.plan):
            if o.objectName().startswith(f'stringLabel-{kind}-'):
                out.append(o)
        return out

    def test_r514_the_state_disc_has_its_room_and_both_ends_are_alike(self):
        self.strings()
        c = self.controller
        c.set_string_details(c._module_tips, c._module_tip_default, c.editor.string_optimizers, {0: 'fail', 1: 'warn', 2: 'fail'})
        for zoom, kind in ((64, 'near'), (3, 'far')):
            self.plan.setProperty('zoom', zoom)
            self.plan.setProperty('panX', 300)
            self.plan.setProperty('panY', 500)
            QTest.qWait(250)
            # R707: from far the strings' names give way to one pill for each inverter, with its state alone
            pills = [o for o in self.labels('inverter' if kind == 'far' else 'name') if o.width() > o.height() and o.isVisible()]
            self.assertTrue(pills, kind)
            if kind == 'far':
                self.assertFalse([o for o in self.labels('name') if o.isVisible()], 'no name of a string from far')
            for pill in pills:
                parts = list(pill.childItems())
                dot = next((o for o in parts if o.metaObject().className() == 'QQuickRectangle' and o.isVisible()
                            and o.width() == o.height() and o.width() < pill.height()), None)
                self.assertEqual(dot is None, kind == 'far', 'a string has its colour in a disc, an inverter has none')
                text = next(o for o in parts if o.metaObject().className() == 'QQuickText')
                mark = next(o for o in parts if o.metaObject().className().startswith('PlanSymbol') and o.isVisible())
                h = pill.height()
                gap = pill.width() - mark.x() - mark.width()
                self.assertAlmostEqual(mark.y(), (h - mark.height()) / 2, delta=.01, msg=kind)       # in the middle
                self.assertAlmostEqual(gap, mark.y(), delta=.01, msg=kind)                          # round the end
                # R577: both ends alike means each mark in the centre of its round end (the dot is smaller than the
                # disc: as far from the edge as the disc, it stood 3 px off the centre)
                if dot is not None:
                    self.assertAlmostEqual(dot.x() + dot.width() / 2, h / 2, delta=.01, msg=kind)
                self.assertAlmostEqual(mark.x() + mark.width() / 2, pill.width() - h / 2, delta=.01, msg=kind)
                end = text.x() + text.property('contentWidth')
                self.assertLessEqual(end, mark.x() + .01, (kind, text.property('text'), end, mark.x()))   # never under

    def test_r580_the_strings_lines_lie_over_the_outlines_of_what_is_chosen(self):
        # the outline of a chosen sub-field cut the lines of its strings: the outlines of the selection and of the
        # hover lie over the strings' fills (a chosen module shows) and under their lines
        self.strings()
        layer = self.visual('worldLayer')
        self.assertIsNotNone(layer)
        order = [o.objectName() for o in layer.childItems()]
        marks = order.index('highlightLayer')
        for name in ('wireFills', 'unwiredBatch', 'draftFills'):
            self.assertLess(order.index(name), marks, name)
        for name in ('wiresBatch', 'optimizerBatch', 'draftWires', 'draftBand'):
            self.assertGreater(order.index(name), marks, name)

    def test_labels_lie_over_every_dot_and_cover_none(self):
        self.strings()
        self.controller.chooseString(1)
        for angle in (0, 30, 115):
            for zoom in (40, 64):
                self.plan.setProperty('bearing', angle)
                self.plan.setProperty('zoom', zoom)
                self.plan.setProperty('panX', 300)
                self.plan.setProperty('panY', 500)
                # the labels are laid out at the settled zoom, 300 ms after the last change (R541): wait for it,
                # not for a fixed time (read before it, a label only scaled could still lie on a dot)
                self.assertTrue(_setup.wait_until(edit.APP, lambda z=zoom: abs(self.plan.property('settledZoom') - z) < 1e-6,
                                                  5.0), (angle, zoom))
                # then the names laid out for that zoom: the chosen string's three (a fixed 50 ms read, under load,
                # the names of every string still shown before the layout)
                self.assertTrue(_setup.wait_until(edit.APP, lambda: len(self.labels('name')) == 3, 5.0),
                                (angle, zoom, len(self.labels('name'))))
                # and the numbers laid out with them: under load they came a turn after the names (a number of the
                # layout before over a dot, once on Windows); a number that stays on a dot still fails below
                def hits():
                    dots = self.dots()
                    return [d for label in self.labels('name') + self.labels('number')
                            for d in dots if covers(label.mapRectToScene(QRectF(0, 0, label.width(), label.height())), d)]
                _setup.wait_until(edit.APP, lambda: not hits(), 3.0)
                dots = self.dots()
                self.assertTrue(dots)
                # R706: the dots are a layer of the drawing; the labels' layer stands over the drawing's
                assert_dots_follow(self, self.plan, self.controller.dots)
                dot_items = [dots_layer(self.plan)]
                def layer(item):
                    while item.parentItem() is not self.plan:
                        item = item.parentItem()
                    return item
                names, numbers = self.labels('name'), self.labels('number')
                self.assertEqual(len(names), 3, (angle, zoom))
                self.assertTrue(numbers)
                for label in names + numbers:
                    self.assertGreater(layer(label).z(), max(layer(d).z() for d in dot_items), 'labels over the dots')
                    rect = label.mapRectToScene(QRectF(0, 0, label.width(), label.height()))
                    hit = [d for d in dots if covers(rect, d)]
                    self.assertEqual(hit, [], (label.objectName(), angle, zoom, rect))
        self.assertFalse(self.warnings, self.warnings)

    def test_numbers_stay_next_to_their_module(self):
        rows = self.strings(count=6)
        self.controller.chooseString(0)
        self.plan.setProperty('zoom', 64)
        QTest.qWait(180)
        for label in self.labels('number'):
            record = label.property('modelData')
            if hasattr(record, 'toVariant'):
                record = record.toVariant()
            module = rows[0][record['item']['number']-1]
            centre = self.plan.screen(*module.centre)
            actual = label.mapToScene(QPointF(label.width()/2, label.height()/2))
            self.assertLess((centre-actual).manhattanLength(), 40)

    def test_r555_a_name_is_the_sides_pill_and_gives_way_in_one_manner(self):
        # R555 (14) (Daniel 09/11/2026: «a un certo zoom le pillole delle stringhe perdono i segni a destra senza motivo
        # (lo spazio guadagnato è quasi nullo); più simili a quelle delle quote dei lati»). Before: between 6 and 14 px
        # a module the name lost its state for 3 px (70 -> 67), 22 px high against the sides' 19, and under 6 px it
        # was a bare disc of 12 px of its own drawing.
        self.strings()
        c = self.controller
        c.set_string_details(c._module_tips, c._module_tip_default, c.editor.string_optimizers, {0: 'ok', 1: 'warn', 2: 'fail'})
        size = c.property('moduleSize')
        widths, line = {}, None
        for level, pixels in (('near', 20), ('mid', 9), ('far', 4)):
            self.plan.setProperty('zoom', pixels / size)
            self.plan.setProperty('panX', 300)
            self.plan.setProperty('panY', 500)
            layer = next(o for o in self.descendants(self.plan) if o.objectName() == 'stringLabels')
            # laid out at the settled zoom: the level of this zoom, its names there
            # R707: a name for each string from the strings' scale; below it one pill for each inverter (the three
            # strings are one inverter's: one pill), with how many strings it has, and from far its name alone
            kind = 'name' if level == 'near' else 'inverter'
            _setup.wait_until(edit.APP, lambda layer=layer, level=level, kind=kind: layer.property('level') == level and any(
                o.isVisible() for o in self.labels(kind)), 5)
            self.assertEqual(layer.property('level'), level)
            line = layer.property('line')
            names = [o for o in self.labels(kind) if o.isVisible()]
            self.assertEqual(len(names), 3 if level == 'near' else 1, level)
            if level != 'near':
                self.assertFalse([o for o in self.labels('name') if o.isVisible()], level)
                said = names[0].property('value')
                self.assertEqual(('·' in said, said.startswith('Inverter 1')), (level == 'mid', True), said)
            for pill in names:
                kinds, meta = [], pill.metaObject()
                while meta is not None:
                    kinds.append(meta.className())
                    meta = meta.superClass()
                self.assertTrue(any(k.startswith('LengthPill') for k in kinds), ('the sides\' pill', kinds))
                self.assertAlmostEqual(pill.height(), line, delta=.01, msg=level)
                marks = [o for o in pill.childItems() if o.metaObject().className().startswith('PlanSymbol')
                         and o.isVisible()]
                widths.setdefault(level, set()).add(round(pill.width(), 2))
                self.assertEqual(len(marks), 1, f'{level}: the state at the end of the name')
        self.assertGreater(min(widths['mid']), max(widths['far']), 'from far the inverter says its name alone')
        self.assertFalse(self.warnings, self.warnings)


if __name__ == "__main__":
    unittest.main()
