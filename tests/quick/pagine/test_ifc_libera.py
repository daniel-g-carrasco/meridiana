"""The guard of the window applied to the IFC import (R598, study 48 chapter 6 step 2): from the file chosen in the
dialog to «Add the model» and the model's true geometry in the 3D, the calls of the reading on the window's thread
(the job's deliveries, the answer put back together, the dialog given what was read: `ifc_read.*`) stay under 5 ms.
The window is the real one, off screen, with the real bridge of the jobs. «Add the model» (passo 2): the gesture itself
(`dialog.add_model`) stays under 5 ms, every view hears the import and the body selected a piece each, in order, the
model is taken in hand after them, and one undo takes it all back; the views' pieces are printed with their numbers."""
import tempfile
import unittest
from pathlib import Path

import _setup
from meridiana.core.model import model
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import window_stays_free

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "ifc" / "vetrata-inclinata.ifc"


class IfcImportFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)
        project = model.Project(site=model.Site(lat=45.53, lon=9.04, address="45.53, 9.04"))
        cls.host = QuickWindow(project, cls.cache, theme={'theme': 'light'}, real_views=True)
        cls.work = cls.host.work
        cls.center = cls.work.center
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()
        # the 3D on show (R598: one not on show makes nothing); off screen this window has room for one view at a time
        cls.win.setProperty('viewMode', '3d')

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def test_the_window_stays_free_from_the_reading_to_the_model_in_the_3d(self):
        self.assertTrue(_setup.wait_for(lambda: not self.host.bridge.busy and not self.work.rows, 120000),
                        'the opening of the window has ended')
        part = self.host.parts.controllers['filePart']
        part.openDialog('ifc')
        backend = part.dialogs
        self.assertIs(backend.center, self.center)                  # the window's one center: its one bar
        session = self.host.bridge.session
        rows = []
        self.center.subscribe(lambda: rows.extend(r['slot'] for r in self.center.rows()))
        with window_stays_free(self.center, call_ms=5, beat_ms=None, only=('ifc_read',)) as seen:
            backend.readFile(str(SAMPLE))
            self.assertTrue(_setup.wait_for(lambda: backend.state.get('ifcRead') or backend.status, 300000),
                            backend.status)
            backend.setValue('how', 'origin')
            self.assertTrue(_setup.wait_for(lambda: not backend.busy and backend.state.get('valid'), 120000),
                            backend.status)
        self.assertIn('ifc_read', rows)                             # the reading showed in the jobs' bar
        print(f"\nIFC import, the reading: {seen}; above 5 ms, not this step's: {seen.over(5)}")

        # «Add the model» (passo 2): the gesture adds the bodies as one step and ends; every view hears the import and
        # the body selected a piece each on the window's turns (the plan and the 3D first), the model is taken in hand
        # once they have, and Ctrl+Z takes the whole import back
        heard = []
        real = list(session.listeners)

        def spy(listener):
            def told(topics):
                heard.append((getattr(listener, '__qualname__', repr(listener)), set(topics)))
                listener(topics)
            told.__qualname__ = getattr(listener, '__qualname__', repr(listener))
            return told
        spies = {id(x): spy(x) for x in real}
        at_once = list(session._at_once)
        session.listeners[:] = [spies[id(x)] for x in real]
        session._at_once[:] = [spies.get(id(x), x) for x in at_once]
        placed = []
        backend.modelPlaced.connect(lambda: placed.append(len(heard)))
        try:
            with window_stays_free(self.center, call_ms=5, beat_ms=None, only=('dialog.add_model',)) as added:
                self.assertTrue(backend.accept())
                self.assertTrue(session.project.buildings)
                self.assertEqual(session.selection[0], 'building')
                self.assertTrue(session.telling(), 'the views follow on the window\'s turns, not in the gesture')
                scene = self.host.scene
                self.assertTrue(_setup.wait_for(lambda: not session.telling() and placed, 120000))
                self.assertTrue(_setup.wait_for(lambda: bool(scene.context._pieces), 120000), scene.context.error)
        finally:
            session.listeners[:] = real
            session._at_once[:] = at_once
        print(f"IFC import, «Add the model»: {added}; above 5 ms, the views' pieces: {added.over(5)}")
        self.assertEqual(added.call_name, 'dialog.add_model', 'the gesture timed by the center')
        names = [name for name, _t in heard]
        for listener in real:
            name = getattr(listener, '__qualname__', repr(listener))
            mine = [topics for n, topics in heard if n == name]
            self.assertTrue(mine and 'project:geometry' in mine[0], f'{name} heard the import first: {mine}')
            self.assertTrue(any('selection' in t for t in mine), f'{name} heard the body selected: {mine}')
        first = [getattr(x, '__qualname__', '') for x in at_once]
        self.assertEqual(set(names[:len(first)]), set(first), 'the plan and the 3D first')
        self.assertEqual(placed, [len(heard)], 'the model taken in hand once every view has heard')
        count = session.undo.count()
        session.undo.undo()
        self.assertEqual(session.project.buildings, [], 'Ctrl+Z takes the whole import back')
        self.assertEqual(session.undo.count(), count)


if __name__ == '__main__':
    unittest.main()
