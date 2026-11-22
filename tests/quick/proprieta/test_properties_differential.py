"""R389: every field of the Properties edited through the Quick adapter; after each, the whole project and the undo
the Widgets' fields gave for the same edits (recorded on 10/11/2026, quick/aiuti/riferimenti.py)."""
import copy
import unittest

import _setup
from _fixtures import capannone_rho

from meridiana import i18n
from meridiana.core.model import model
from meridiana.gui.backend.properties import PropertiesBackend
from meridiana.app.session import ProjectSession
from quick.aiuti import riferimenti
from quick.aiuti.differential import undo_snapshot


setUpModule = _setup.keep_global_state


class PropertyDifferentialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        i18n.setup('en')
        # the project as a window opens it: saved and read again
        project = model.Project.from_json(copy.deepcopy(capannone_rho().to_json()))
        self.backend = PropertiesBackend(ProjectSession(project))
        self.addCleanup(self.backend.close)

    def test_widgets_and_quick_edit_full_project_identically(self):
        b = self.backend
        # R413 keeps the ridge by default, in Quick only: the record has the eave kept, what the Widgets did
        for building in b.session.project.buildings:
            building.roof.keep_eave = True

        def done():
            riferimenti.check(self, dict(project=riferimenti.project(b.session.project), undo=undo_snapshot(b.session)))

        def select(kind, oid):
            b.session.select(kind, oid)
            done()

        def edit(key, value):
            self.assertTrue(b.commit(key, value), b.error)
            done()

        select('site', '')
        edit('name', '  Rho modificato  ')
        edit('network.pod', 'IT001234567890')
        edit('network.voltage_v', 20000)
        edit('network.phases', '3')
        edit('rules.public', True)
        select('building', 'b1')
        edit('height', 11)
        edit('side.0', 44)
        edit('roof.type', 'gable')
        edit('roof.tilt', 25)
        edit('roof.percent', 35)
        edit('roof.ridge_height', 15)
        edit('fire.activity', 75)
        edit('fire.category', 'B')
        select('subfield', 's1')
        edit('name', 'Ovest')
        edit('params.stack', 3)
        edit('params.gap', .04)
        edit('params.pitch_mode', 'gcr')
        edit('params.gcr', .6)
        edit('params.pitch_mode', 'value')
        edit('params.pitch', 4.2)
        select('exclusion', 'e1')
        edit('height', 2.1)
        edit('clearance', .7)
        b.undo()
        done()
        b.redo()
        done()


if __name__ == '__main__':
    unittest.main()
