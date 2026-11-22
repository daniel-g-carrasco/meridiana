"""R598, study 48 chapter 6 step 0, «the photo for every job»: after a change of the project, the jobs it starts (the
layout, the checks, the plant) take the session's photo, a reference, and make their project where they run. On the
window's thread no copy of the project is made but the two snapshots of the change itself (session.edit, and
session.amend when the strings follow the layout): those are the photo. And what the jobs give back is the changed
project's. The window is the real one, off screen."""
import copy
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import clear_sky_meteo, mixed, write_cache
from meridiana.app import jobs
from meridiana.app import session as session_module
from meridiana.app.session import ProjectSession, photo_of, project_from
from meridiana.core.model import model
from meridiana.gui.application import QuickWindow, create_app


def callers(depth: int = 6) -> tuple:
    frame, names = sys._getframe(2), []
    while frame is not None and len(names) < depth:
        names.append(frame.f_code.co_name)
        frame = frame.f_back
    return tuple(names)


class PhotoForTheJobs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)
        write_cache(clear_sky_meteo(), cls.cache)
        cls.host = QuickWindow(mixed(), cls.cache, theme={'theme': 'light'})
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()
        cls.host.bridge.recompute()         # as the program at its start (application.main): the year, the layouts

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def idle(self) -> bool:
        from PySide6.QtCore import QThreadPool
        bridge = self.host.bridge
        return (not bridge.busy and bridge._layout is None and not bridge.session.telling()
                and bridge.session.layouts_answer() and QThreadPool.globalInstance().activeThreadCount() == 0
                and bridge.pool.activeThreadCount() == 0 and not bridge.checks_feed.busy())

    def test_a_change_starts_its_jobs_on_the_photo_without_a_copy(self):
        session = self.host.bridge.session
        self.assertTrue(_setup.wait_for(self.idle, 180000), 'the opening of the window has ended')
        sf = session.project.subfields[0]
        laid = len(session.results[sf.id].modules)
        main = threading.main_thread()
        copies, photos = [], []
        real_photo_of, real_deepcopy, real_photo = session_module.photo_of, copy.deepcopy, ProjectSession.photo

        def counted_photo_of(project):
            if threading.current_thread() is main:
                copies.append(('photo_of',) + callers())
            return real_photo_of(project)

        def counted_deepcopy(x, memo=None, _nil=[]):      # noqa: B006 (copy.deepcopy's own signature)
            if isinstance(x, model.Project) and threading.current_thread() is main:
                copies.append(('deepcopy',) + callers())
            return real_deepcopy(x, memo)

        def counted_photo(self_):
            if threading.current_thread() is main:
                photos.append(callers(1)[0])
            return real_photo(self_)

        def made_by_the_change(call):       # the undo's snapshots of the change: they are the photo
            return call[0] == 'photo_of' and call[1] == 'snapshot' and call[2] in ('edit', 'amend')

        # the guard of the suite compares every photo with a snapshot of its own: off, or it would be counted
        with mock.patch.object(session_module, 'CHECK_PHOTO', False), \
                mock.patch.object(session_module, 'photo_of', counted_photo_of), \
                mock.patch('copy.deepcopy', counted_deepcopy), \
                mock.patch.object(ProjectSession, 'photo', counted_photo):
            session.edit('Shrink the sub-field', lambda p: setattr(p.subfields[0], 'ring',
                                                                   [[1, 1], [20, 1], [20, 19], [1, 19]]))
            self.assertTrue(_setup.wait_for(self.idle, 180000), 'the layout of the change came back')
        print(f'\nphotos taken by the jobs: {photos}\ncopies on the window\'s thread: {copies}', file=sys.stderr)
        self.assertTrue(photos, 'the change started its jobs')
        self.assertIn('request_of', photos, 'the layout of the change took the photo')
        self.assertEqual([c for c in copies if not made_by_the_change(c)], [],
                         'no copy of the project on the window\'s thread but the change\'s own')
        self.assertLessEqual(len(copies), 4, 'the change and, at most, the strings that follow its layout')
        # what came back is the changed project's: the layout of the project as it is now, laid here for the test
        now, _keys, _laid = jobs.layout_of(project_from(photo_of(session.project)))
        self.assertLess(len(session.results[sf.id].modules), laid, 'the smaller sub-field has fewer modules')
        self.assertEqual([m.key for m in session.results[sf.id].modules], [m.key for m in now[sf.id].modules])
        self.assertEqual(session.layout_keys, session.expected_layout_keys())


if __name__ == '__main__':
    unittest.main()
