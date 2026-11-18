"""R389 differential journeys using the existing Widgets handlers and Quick slots."""
import copy
import unittest

import _setup
from _fixtures import capannone, inverter_record
from quick.parity.differential import Adapter, WidgetsAdapter, canonical_project, compare, normalized, undo_snapshot
from meridiana import model
from meridiana.i18n import _
from meridiana.session import ProjectSession
from meridiana.quick.backend.plant import PlantBackend

setUpModule = _setup.keep_global_state


class PlantParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def exercise(self, project):
        w = _setup.window(self, project)
        old = WidgetsAdapter(w, self.app)
        old.wait()
        session = ProjectSession(model.Project.from_json(copy.deepcopy(w.session.snapshot()), check=False))
        session.results, session.layout_keys = dict(w.session.results), dict(w.session.layout_keys)
        new = PlantBackend(session)
        self.addCleanup(new.close)
        def settled():
            self.assertTrue(_setup.wait_until(self.app, lambda: not new.busy, 60), new.message)
        settled()
        def observe(session, state):
            return dict(project=canonical_project(session.project), undo=undo_snapshot(session),
                        strings=normalized(state.strings), inputs=normalized(state.inputs),
                        checks=normalized(state.checks), left=normalized(state.left))
        quick = Adapter('Quick', {}, lambda: observe(session, new.state), settled)
        steps = [
            ('add', lambda: w._add_inverter(inverter_record(), _('Add an inverter from the catalogue')),
             lambda: new.addInverter(inverter_record())),
            ('second', lambda: w._add_inverter(inverter_record(model='AC-B'), _('Add an inverter from the catalogue')),
             lambda: new.addInverter(inverter_record(model='AC-B'))),
            ('draw', lambda: old.manual_strings(1, 1, 20),
             lambda: new.commitString(1, 1, [f'{sid}/{m.key}' for sid, layout in session.good_results().items()
                                            for m in layout.modules][:20], -1)),
            ('rename', lambda: w._unit_renamed(1, 'Tetto A'), lambda: new.renameUnit(1, 'Tetto A')),
            ('move inverter', lambda: w._unit_moved(1, 1), lambda: new.moveUnit(1, 1)),
            ('move string', lambda: w._move_string(0, 2, 2), lambda: new.moveString(0, 2, 2)),
            ('undo move', w.undo.undo, new.undo),
            ('redo move', w.undo.redo, new.redo),
            ('remove inverter', lambda: w._unit_removed(2), lambda: new.removeUnit(2, False)),
            ('undo removal', w.undo.undo, new.undo),
            ('delete string', lambda: w._delete_string(0), lambda: new.deleteString(0)),
            ('undo deletion', w.undo.undo, new.undo),
        ]
        for title, widgets_command, quick_command in steps:
            with self.subTest(step=title):
                widgets_command()
                old.wait()
                quick_command()
                quick.settle()
                differences = compare(observe(w.session, w.plant_state), quick.observe())
                self.assertEqual(differences, [], str(differences[:5]))

    def test_fixture_same_project_checks_strings_and_undo_after_every_command(self):
        self.exercise(capannone())

    def test_rho_same_project_checks_strings_and_undo_after_every_command(self):
        p, _message = model.Project.load(_setup.ROOT / 'docs/quick/compat/fixtures/rho.meridiana')
        # Keep Rho geometry and modules. Both frontends receive the same explicit empty wiring.
        p.energy.pop('inverter', None)
        p.energy.pop('inverter_count', None)
        p.energy['inverters'] = []
        p.energy['strings'] = {'auto': False, 'runs': []}
        self.exercise(p)


if __name__ == '__main__':
    unittest.main()
