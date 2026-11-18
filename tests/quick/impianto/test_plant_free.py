"""R522 in the Plant: inverters and strings for the modules in no string only (Daniel 07/11/2026). A shed with a flat roof
strung in part by hand, and a second building with a gable roof whose two faces are other sub-fields: the proposal
touches only the free modules, the designer's strings and inverter stay byte for byte, one undo step; the window's
option comes on by itself with the number; the plan's menu in Plant has the command."""
import copy
import json
import time
import unittest

import _setup  # noqa: F401  isolate the user's profile before loading Qt
from _fixtures import capannone, inverter_record
from PySide6.QtWidgets import QApplication

from meridiana import jobs, model
from meridiana.energy import sizing
from meridiana.session import ProjectSession
from meridiana.quick.backend.plant import PlantBackend


def site() -> model.Project:
    p = capannone()
    p.buildings.append(model.Building(id="b9", name="Magazzino", footprint=[[50, 0], [60, 0], [60, 14], [50, 14]],
                                      height=6.0, roof=model.Roof(type="gable", tilt=15.0)))
    for sfid, side, x0, x1 in (("w9", 3, 50.4, 54.6), ("e9", 1, 55.4, 59.6)):
        p.subfields.append(model.SubField(id=sfid, name="Ovest" if side == 3 else "Est",
                                          ring=[[x0, 0.4], [x1, 0.4], [x1, 8.4], [x0, 8.4]], building="b9", pitch=side,
                                          params={"mounting": "coplanar"}, filled=True))
    return p


def records() -> list:
    return [inverter_record(model="AC-10K", ac_power_nominal_w=10000),
            inverter_record(),
            inverter_record(model="AC-50K", ac_power_nominal_w=50000, mppt_count=6,
                            dc_current_max_per_mppt_a=[26] * 6, dc_isc_max_per_mppt_a=[40] * 6)]


def dump(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


class FreeModulesInThePlant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.project = site()
        cls.results, cls.keys, _ = jobs.layout_of(cls.project)

    def setUp(self):
        self.session = ProjectSession(copy.deepcopy(self.project))
        self.session.results, self.session.layout_keys = self.results, self.keys
        self.backend = PlantBackend(self.session)
        self.addCleanup(self.backend.close)
        self.wait()

    def wait(self, seconds=120):
        until = time.monotonic() + seconds
        while self.backend.busy and time.monotonic() < until:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertFalse(self.backend.busy, self.backend.message)

    def by_hand(self):
        self.backend.addInverter(inverter_record())
        self.wait()
        sud = next(sf.id for sf in self.project.subfields if sf.name == "Sud")
        keys = [f"{sud}/{m.key}" for m in self.results[sud].modules]
        self.backend.commitString(1, 1, keys[:20], -1)
        self.wait()
        self.backend.commitString(1, 2, keys[20:40], -1)
        self.wait()
        return sum(len(r.modules) for r in self.results.values() if not isinstance(r, Exception)) - 40

    def test_the_proposal_touches_only_the_free_modules_and_undoes_in_one_step(self):
        free = self.by_hand()
        self.assertGreater(free, 40)
        self.assertEqual(self.backend.freeModules, free)
        energy = self.session.project.energy
        runs, entries = dump(energy["strings"]["runs"]), dump(energy["inverters"])
        before = self.session.snapshot()
        self.backend.startSizingFree("Acme", records())
        self.wait()
        result = self.backend._sizing_result
        self.assertIsNotNone(result, self.backend.message)
        self.assertEqual(result.free, free)
        energy = self.session.project.energy
        self.assertEqual(dump(energy["strings"]["runs"][:2]), runs)      # the designer's strings, byte for byte
        self.assertEqual(dump(energy["inverters"][:1]), entries)          # his inverter too
        self.assertEqual(result.mode, sizing.FREE_NEW)                     # 2 MPPT both taken: inverters added
        self.assertGreater(len(energy["inverters"]), 1)
        self.assertEqual(self.backend.freeModules, 0)
        self.assertFalse(self.backend.state.left)
        laid = sum(len(r.modules) for r in self.results.values() if not isinstance(r, Exception))
        self.assertEqual(sum(len(r["modules"]) for r in energy["strings"]["runs"]), laid)
        self.assertEqual(len({k for r in energy["strings"]["runs"] for k in r["modules"]}), laid)
        sub_fields = {k.partition("/")[0] for r in energy["strings"]["runs"][2:] for k in r["modules"]}
        self.assertTrue({"w9", "e9"} <= sub_fields)                       # the other sub-fields, the other faces
        self.assertIn("added for the", self.backend.message)
        self.backend.undo()
        self.wait()
        self.assertEqual(self.session.snapshot(), before)                  # one undo step

    def test_the_free_inputs_when_the_inverter_has_them(self):
        self.backend.addInverter(records()[2])                             # 50 kW, 6 MPPT
        self.wait()
        sud = next(sf.id for sf in self.project.subfields if sf.name == "Sud")
        keys = [f"{sud}/{m.key}" for m in self.results[sud].modules]
        self.backend.commitString(1, 1, keys[:20], -1)
        self.wait()
        before = dump(self.session.project.energy["strings"]["runs"])
        free = self.backend.freeModules
        self.backend.startSizingFree("Acme", records())
        self.wait()
        result = self.backend._sizing_result
        self.assertIsNotNone(result, self.backend.message)
        energy = self.session.project.energy
        self.assertEqual(dump(energy["strings"]["runs"][:1]), before)
        # its free inputs take the free modules, or as many as they can with valid strings (the rest on inverters added)
        self.assertIn(result.mode, (sizing.FREE_INPUTS, sizing.FREE_BOTH))
        self.assertTrue(any(r["inverter"] == 1 for r in result.new_runs))
        self.assertIn("go on free inputs of the inverters there are", self.backend.message)
        self.assertEqual(self.backend.freeModules, 0, (free, self.backend.message))

    def test_the_option_comes_on_by_itself(self):
        from meridiana.quick.backend.plant_part import PlantActions

        class Host:
            plan = None

            class shell:
                @staticmethod
                def trigger(_name):
                    pass

        class Catalog:
            class chosen:
                connect = staticmethod(lambda *_a: None)

            class importRequested:
                connect = staticmethod(lambda *_a: None)

        actions = PlantActions(self.backend, Catalog(), Host())
        actions.open('sizing')
        self.assertFalse(actions.onlyFree)                                 # nothing strung: the whole plant
        actions.proposal(True)
        self.assertTrue(actions.replace)
        self.by_hand()
        actions.open('sizing')
        self.assertTrue(actions.onlyFree)
        actions.proposal(True)
        self.assertFalse(actions.replace)                                  # «only the n modules in no string»
        actions.dismiss()
        actions.sizingFree()
        self.assertTrue(actions.onlyFree)
        self.assertEqual(actions.dialog, 'sizing')


class TheMenu(unittest.TestCase):
    def test_the_plan_menu_in_plant_has_the_command(self):
        from meridiana.quick.backend import plan_menu

        class Editor:
            selection = ('', '')
            selected_module = ('', '')
            draft = None
            phase = 'plant'
            results = {}
            swept = ()

            def _rid(self, *_a):
                return ''

            def clip_target(self):
                return False

            def can_paste(self):
                return False

        class Controller:
            editor = Editor()
            tool = 'select'
            _context_host = ''
            _context_side = None

            class drawing:
                points = []

        commands = [e['command'] for e in plan_menu.entries(Controller())]
        self.assertIn('propose_free', commands)
        Controller.editor.phase = 'model'
        self.assertNotIn('propose_free', [e['command'] for e in plan_menu.entries(Controller())])



class TheWindows(unittest.TestCase):
    """The real Quick window, offscreen, in Italian: the option with its number, on by itself, and the plan's menu."""

    @classmethod
    def setUpClass(cls):
        import os
        import tempfile
        from pathlib import Path
        from meridiana import i18n
        from meridiana.quick.app import QuickWindow, create_app
        from quick.gestures import wait_for
        from quick.parity.differential import connected_fixture
        if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
            os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()                  # 80 modules in 4 strings by hand, the others free
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light', 'accent': 'indigo', 'backgrounds': 'grey'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.plant = cls.host.parts.controllers['plant']
        cls.actions = cls.host.parts.controllers['plantActions']
        cls.host.shell.trigger('phase_plant')
        wait_for(lambda: not cls.plant.busy and cls.plant.units, 60)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def tearDown(self):
        from quick.gestures import pump
        self.actions.dismiss()
        pump(150)

    def items(self):
        pending = [self.win.contentItem()]
        while pending:
            current = pending.pop()
            yield current
            pending.extend(current.childItems())

    def test_the_sizing_window_has_the_option_on_with_the_number(self):
        from quick.gestures import pump
        free = self.plant.freeModules
        self.assertGreater(free, 0)
        self.actions.open('sizing')
        pump(300)
        box = next(i for i in self.items() if i.objectName() == 'sizing-only-free')
        self.assertTrue(box.isVisible())
        self.assertTrue(box.property('checked'))
        self.assertEqual(box.property('text'), f'Solo i {free} moduli scollegati')

    def test_the_stringing_window_says_the_number_and_chooses_it(self):
        from quick.gestures import pump
        free = self.plant.freeModules
        self.actions.proposal(True)
        pump(300)
        self.assertFalse(self.actions.replace)
        shown = [i.property('text') for i in self.items() if isinstance(i.property('text'), str)]
        self.assertTrue(any(t == f'solo i {free} moduli scollegati' for t in shown), [t for t in shown if 'moduli' in t])

    def test_the_plan_menu_opens_the_sizing_with_the_option(self):
        from quick.gestures import pump
        from meridiana.quick.backend import plan_menu
        controller = self.host.parts.controllers['plan']
        texts = [e['text'] for e in plan_menu.entries(controller)]
        self.assertIn('Proponi inverter e stringhe per i moduli scollegati', texts)
        plan_menu.execute(controller, 'propose_free')
        pump(200)
        self.assertEqual(self.actions.dialog, 'sizing')
        self.assertTrue(self.actions.onlyFree)

    def test_the_free_sizing_lists_the_preferred_makers_only(self):
        # R522, Daniel 07/11/2026 sera: «solo marche preferite»
        from quick.gestures import pump, wait_for
        self.plant.loadMakers()
        wait_for(lambda: self.plant.makers, 60)
        preferred = {m['label'] for m in self.plant.makers if m['preferred']}
        self.assertIn('Huawei', preferred)
        self.assertLess(len(preferred), len(self.plant.makers))
        self.actions.open('sizing')
        pump(300)
        rows = {i.objectName()[len('maker-row-'):] for i in self.items()
                if i.objectName().startswith('maker-row-') and i.isVisible()}
        self.assertTrue(rows and rows <= preferred, rows - preferred)
        words = next(i for i in self.items() if i.objectName() == 'sizing-free-preferred')
        self.assertTrue(words.isVisible())
        self.assertIn('25 secondi', words.property('text'))
        box = next(i for i in self.items() if i.objectName() == 'sizing-only-free')
        box.setProperty('checked', False)
        pump(200)
        rows = {i.objectName() for i in self.items() if i.objectName().startswith('maker-row-') and i.isVisible()}
        self.assertFalse(words.isVisible())
        self.assertTrue(rows - {f'maker-row-{m}' for m in preferred})  # the others again
        other = next(m['label'] for m in self.plant.makers if not m['preferred'])
        self.plant.sizeInvertersFor(other, True)
        self.assertFalse(self.plant.searching)
        self.assertIn(other, self.plant.message)

    def test_the_choice_is_explained_with_its_alternatives_r22(self):
        # R522 r22-impianto: after the proposal Impianto says why (the ratio of the whole plant and of each inverter)
        # and lists the other valid proposals, each with «Usa questa»
        from quick.gestures import pump, wait_for
        before = self.plant.session.snapshot()

        def back():
            self.plant.dismissSizing()
            while self.plant.session.snapshot() != before and self.plant.canUndo:
                self.plant.undo()
                wait_for(lambda: not self.plant.busy, 60)
        self.addCleanup(back)
        self.plant.startSizingFree('Huawei', None)
        wait_for(lambda: not self.plant.searching and not self.plant.busy, 90)
        pump(300)
        result = getattr(self.plant, '_sizing_result', None)
        self.assertIsNotNone(result, self.plant.message)
        if self.actions.property('section') != 'inverter':
            self.actions.toggleSection('inverter')      # where «Scegli automaticamente» is
        pump(600)

        def shown(name):    # the page on screen (a page the side panel left behind keeps its items, hidden)
            return [i for i in self.items() if i.objectName() == name and i.isVisible()]
        self.assertEqual(len(shown('plant-free-choice')), 1)
        why = shown('plant-free-why')[0].property('text')
        self.assertIn('per inverter', why)
        self.assertIn('Rapporto DC/AC', why)
        if result.alternatives:
            self.assertIn('impianto intero', shown('plant-free-alternative0')[0].property('text'))
            self.assertEqual(shown('plant-free-use0')[0].property('text'), 'Usa questa')
        self.assertEqual(len(shown('plant-free-close')), 1)
        self.plant.dismissSizing()
        pump(150)
        self.assertEqual(shown('plant-free-choice'), [])

    def test_the_search_shows_its_seconds_and_stop_keeps_the_best(self):
        # R522: the progress of the time limit, and «Interrompi» that keeps the best proposal found
        from quick.gestures import pump, wait_for
        self.assertEqual(self.plant.searchSeconds, -1.0)
        self.assertEqual(self.plant.searchLimit, sizing.FREE_SECONDS)
        before = self.plant.session.snapshot()
        real = sizing.choose_free

        def slow(*args, enough=None, **kw):      # a big roof: the search runs until «Stop»
            self.plant._search.enough.wait(30)   # set before the pool runs it
            return real(*args, **kw)            # what was found until «Stop»: here the whole search
        sizing.choose_free = slow
        self.addCleanup(setattr, sizing, 'choose_free', real)

        def back():
            if self.plant.session.snapshot() != before:
                self.plant.undo()
                wait_for(lambda: not self.plant.busy, 60)
        self.addCleanup(back)
        self.plant.startSizingFree('Huawei', None)
        self.assertTrue(self.plant.searching)
        pump(600)
        self.assertGreaterEqual(self.plant.searchSeconds, 0.0)
        bar = next(i for i in self.items() if i.objectName() == 'plant-search-progress')
        stop = next(i for i in self.items() if i.objectName() == 'plant-search-stop')
        self.assertTrue(bar.isVisible() and stop.isVisible())
        self.assertEqual(stop.property('text'), 'Interrompi')
        self.plant.stopSearch()
        wait_for(lambda: not self.plant.searching, 60)
        self.assertEqual(self.plant.searchSeconds, -1.0)
        self.assertFalse(bar.isVisible())
        result = getattr(self.plant, '_sizing_result', None)
        self.assertIsNotNone(result, self.plant.message)               # the best found, applied
        self.assertTrue(result.ok)
        self.plant.undo()
        wait_for(lambda: not self.plant.busy, 60)
        self.assertEqual(self.plant.session.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
