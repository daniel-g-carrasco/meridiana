"""R389 journeys on the Plant's backend: after every command the project, the undo, the strings, the inputs, the
checks and what is left are those the Widgets window gave for the same commands (recorded on 10/11/2026, when the
Widgets went: quick/aiuti/riferimenti.py)."""
import copy
import unittest

import _setup
from _fixtures import capannone, inverter_record
from quick.aiuti import riferimenti
from quick.aiuti.differential import normalized, undo_snapshot
from meridiana.app import jobs
from meridiana.core.model import model
from meridiana.app.session import ProjectSession
from meridiana.gui.backend.plant import PlantBackend

setUpModule = _setup.keep_global_state


class PlantParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def exercise(self, project):
        # the project as a window opens it: saved and read again
        session = ProjectSession(model.Project.from_json(copy.deepcopy(project.to_json()), check=False))
        session.results, session.layout_keys, _errors = jobs.layout_of(session.project)
        new = PlantBackend(session)
        self.addCleanup(new.close)

        def settled():
            self.assertTrue(_setup.wait_until(self.app, lambda: not new.busy, 60), new.message)
        settled()

        def observe():
            state = new.state
            return dict(project=riferimenti.project(session.project), undo=undo_snapshot(session),
                        strings=normalized(state.strings), inputs=normalized(state.inputs),
                        checks=normalized(state.checks), left=normalized(state.left))
        steps = [
            ('add', lambda: new.addInverter(inverter_record())),
            ('second', lambda: new.addInverter(inverter_record(model='AC-B'))),
            ('draw', lambda: new.commitString(1, 1, [f'{sid}/{m.key}' for sid, layout in session.good_results().items()
                                                     for m in layout.modules][:20], -1)),
            ('rename', lambda: new.renameUnit(1, 'Tetto A')),
            ('move inverter', lambda: new.moveUnit(1, 1)),
            ('move string', lambda: new.moveString(0, 2, 2)),
            ('undo move', new.undo),
            ('redo move', new.redo),
            ('remove inverter', lambda: new.removeUnit(2, False)),
            ('undo removal', new.undo),
            ('delete string', lambda: new.deleteString(0)),
            ('undo deletion', new.undo),
        ]
        for title, command in steps:
            with self.subTest(step=title):
                command()
                settled()
                riferimenti.check(self, observe())

    def test_fixture_same_project_checks_strings_and_undo_after_every_command(self):
        self.exercise(capannone())

    def test_rho_same_project_checks_strings_and_undo_after_every_command(self):
        p, _message = model.Project.load(_setup.ROOT / 'docs/quick/compat/fixtures/rho.meridiana')
        # Rho's geometry and modules, with an explicit empty wiring
        p.energy.pop('inverter', None)
        p.energy.pop('inverter_count', None)
        p.energy['inverters'] = []
        p.energy['strings'] = {'auto': False, 'runs': []}
        self.exercise(p)


if __name__ == '__main__':
    unittest.main()
