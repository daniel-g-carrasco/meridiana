"""The one bar of the heavy jobs in the status bar (R598, docs/studio/48-lavori-pesanti.md, chapters 4 and 5): one job
and two, Cancel, the year adopted from shell_compute, and the guard of the window while a job runs in its process."""
import tempfile
import time
import unittest
from pathlib import Path

import shiboken6
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem

import _setup
from _fixtures import capannone
from meridiana.app.work import sample
from meridiana.gui.application import QuickWindow, create_app
from meridiana.i18n import _
from quick.aiuti.finestra_libera import settled, window_stays_free
from quick.gestures import click, item, point
from quick.aiuti.tempi import timed


class WorkBar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone(), Path(cls.folder.name), theme={'theme': 'light'})
        cls.work = cls.host.work
        cls.center = cls.work.center
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.assertTrue(_setup.wait_for(lambda: not self.host.bridge.busy and not self.work.rows, 60000),
                        'the opening of the window has ended')

    def tearDown(self):
        for row in list(self.center.rows()):
            handle = self.center.find(row['id'])
            if handle is not None and not handle.adopted:
                self.center.cancel(handle)

    def bar(self, name='statusProgress'):
        return item(self.win, name)

    def submit(self, request=None, slot=None):
        got = {'partial': [], 'done': []}
        handle = self.center.submit(sample.kind(), request or {'steps': 60, 'pause': 0.05}, slot=slot,
                                    on_partial=lambda k, d: got['partial'].append(k),
                                    on_done=lambda r, stale: got['done'].append(r))
        return handle, got

    def test_one_job_shows_past_the_wait_with_what_it_does_its_bar_and_cancel(self):
        start = time.perf_counter()
        handle, _got = self.submit()
        self.assertFalse(self.bar().isVisible(), 'not before Theme.motion.PATIENCE')
        self.assertTrue(_setup.wait_for(lambda: self.bar().isVisible()))
        self.assertGreaterEqual(time.perf_counter() - start, 0.29)
        self.assertEqual(self.bar('statusProgressText').property('text'), _('Counting'))
        self.assertFalse(self.bar('statusProgressPhase').isVisible(), 'a phase that is the title is not said twice')
        self.assertTrue(_setup.wait_for(lambda: self.bar('statusProgressBar').property('value') > 0))
        self.assertFalse(self.bar('statusProgressBar').property('indeterminate'))
        self.assertTrue(self.bar('statusProgressPercent').property('text').endswith(' %'))
        self.assertTrue(self.bar('statusProgressCancel').isVisible())
        self.assertFalse(self.bar('statusProgressMore').isVisible())
        # Cancel: the bar goes at once, the job's process stops after
        cancel = self.bar('statusProgressCancel')
        clicked = time.perf_counter()
        click(self.app, self.win, point(cancel))
        self.assertEqual(handle.state, 'cancelled')
        self.assertFalse(self.bar().isVisible(), 'gone with the click, not with the process')
        self.assertLess(time.perf_counter() - clicked, 0.05)

    def test_two_jobs_the_first_and_a_pill_that_opens_the_others(self):
        first, _got = self.submit(slot='first')
        second, _got2 = self.submit(slot='second')
        self.assertTrue(_setup.wait_for(lambda: self.bar().isVisible() and len(self.work.rows) == 2))
        pill = self.bar('statusProgressMore')
        self.assertTrue(pill.isVisible())
        # laid out (the Row places a child shown at its next polish): beside the first row's Cancel
        cancel = self.bar('statusProgressCancel')
        self.assertTrue(_setup.wait_for(lambda: point(pill).x() > point(cancel).x() + cancel.width() / 2))
        self.assertEqual(pill.property('text'), '1')
        listing = self.bar('statusProgressList')
        self.assertFalse(listing.property('opened'))
        click(self.app, self.win, point(pill))
        self.assertTrue(_setup.wait_for(lambda: listing.property('opened')))
        rows = [i for i in every_item(self.win) if i.objectName() == 'workCancel' and i.isVisible()]
        self.assertEqual(len(rows), 1, 'one row in the list: the other job')
        click(self.app, self.win, point(rows[0]))
        self.assertEqual(second.state, 'cancelled')
        self.assertEqual(first.state in ('waiting', 'running'), True)
        self.assertTrue(_setup.wait_for(lambda: not listing.property('opened')))
        self.assertFalse(pill.isVisible())

    def test_the_bar_says_the_job_its_phase_its_percentage_and_the_time_left(self):
        now = [1000.0]
        clock, self.center.clock = self.center.clock, lambda: now[0]
        self.addCleanup(setattr, self.center, 'clock', clock)
        handle = self.center.adopt('Sun map', cancel=lambda: None, slot='adopted')
        self.addCleanup(handle.end)
        handle.progress(0, 100, 'preview')
        self.assertTrue(_setup.wait_for(lambda: self.bar().isVisible()))
        self.assertEqual(self.bar('statusProgressText').property('text'), _('Sun map'))
        self.assertEqual(self.bar('statusProgressPhase').property('text'), _('preview'))
        self.assertTrue(self.bar('statusProgressPhase').isVisible())
        # R607: the column of the time is kept empty while there is none (the time that comes moves nothing)
        self.assertEqual(self.bar('statusProgressLeft').property('text'), '', 'no time before 5 s of data: none made up')
        now[0] += 6
        handle.progress(60, 100, 'finest tiles')
        self.assertTrue(_setup.wait_for(lambda: self.bar('statusProgressLeft').property('text') != ''))
        self.assertEqual(self.bar('statusProgressLeft').property('text'), '· ' + _('about {n} s').format(n=4))
        self.assertEqual(self.bar('statusProgressPhase').property('text'), _('finest tiles'))
        self.assertEqual(self.bar('statusProgressPercent').property('text'), '60 %')
        # the phase is the part that gives way in a narrow window, never the percentage, the time or Cancel
        try:
            self.win.resize(800, 900)
            help_button = self.bar('statusHelp')
            cancel = self.bar('statusProgressCancel')
            self.assertTrue(_setup.wait_for(lambda: self.win.width() == 800
                                            and right(cancel) <= point(help_button).x() - help_button.width() / 2))
            for name in ('statusProgressText', 'statusProgressPercent', 'statusProgressLeft', 'statusProgressCancel'):
                part = self.bar(name)
                self.assertTrue(part.isVisible(), name)
                self.assertLessEqual(right(part), 800, name)
                if part.property('truncated') is not None:
                    self.assertFalse(part.property('truncated'), name)
        finally:
            self.win.resize(1400, 900)
            settled(self.win)               # the window laid out again before the next test (the guard) measures

    def test_a_page_shows_the_row_of_its_own_job_by_its_slot(self):
        component = QQmlComponent(self.host.engine)
        component.setData(b'import QtQuick\nimport Meridiana.Controls as M\nM.WorkRow { row: work.slots.mine }',
                          QUrl('file:///work_row_of_a_page.qml'))
        row = component.create()
        self.assertIsNotNone(row, component.errorString())
        QQmlEngine.setObjectOwnership(row, QQmlEngine.ObjectOwnership.CppOwnership)
        row.setParentItem(self.win.contentItem())      # in a page of the window
        self.addCleanup(lambda: shiboken6.isValid(row) and (row.setParentItem(None), row.deleteLater()))
        self.assertFalse(row.property('visible'), 'no job in the slot: the row is hidden')
        handle, _got = self.submit(slot='mine')
        self.assertTrue(_setup.wait_for(lambda: 'mine' in self.work.slots))
        self.assertEqual(self.work.slots['mine']['id'], handle.id)
        self.assertTrue(row.property('visible'), (row.property('row'), row.property('job'), self.host.warnings[-3:]))
        self.assertEqual(row.findChild(QQuickItem, 'workText').property('text'), _('Counting'))
        self.center.cancel(handle)
        self.assertTrue(_setup.wait_for(lambda: not row.property('visible')))
        self.assertNotIn('mine', self.work.slots)

    def test_the_year_is_adopted_and_cancelled_from_the_same_bar(self):
        bridge = self.host.bridge
        step = _('Production: {what} ({n} of {total})').format(what='the sun', n=2, total=8)
        bridge._busy, bridge._progress = True, {'fraction': 0.25, 'text': step}
        bridge.progressChanged.emit()
        bridge.stateChanged.emit()
        self.assertTrue(_setup.wait_for(lambda: self.bar().isVisible()))
        self.assertEqual(self.bar('statusProgressText').property('text'), _('Production'))
        phase = self.bar('statusProgressPhase').property('text')
        self.assertTrue(phase.startswith('the sun (2 ') and phase.endswith(' 8)'), phase)
        self.assertEqual(self.bar('statusProgressPercent').property('text'), '25 %')
        self.assertAlmostEqual(self.bar('statusProgressBar').property('value'), 0.25)
        click(self.app, self.win, point(self.bar('statusProgressCancel')))
        self.assertFalse(bridge.computing, 'the bar\'s Cancel is the year\'s cancelCompute')
        self.assertTrue(_setup.wait_for(lambda: not self.bar().isVisible()))
        self.assertEqual(self.center.rows(), [])

    def test_a_real_year_shows_in_the_one_bar(self):
        bridge = self.host.bridge
        bridge.recompute()
        self.assertTrue(_setup.wait_for(lambda: any(r['slot'] == 'year' and r['title'] in (_('Production'), _('Computing…'))
                                                    for r in self.work.rows), 10000))
        self.assertTrue(_setup.wait_for(lambda: not bridge.busy, 120000), bridge.error)
        self.assertTrue(_setup.wait_for(lambda: not self.work.rows, 5000))

    @timed('no call of the window over its few ms')
    def test_the_window_stays_free_while_a_job_runs_in_its_process(self):
        settled(self.win)                   # the window still from the tests before (study 48, chapter 5)
        with window_stays_free(self.center) as seen:
            _handle, got = self.submit({'steps': 30, 'pause': 0.03})
            self.assertTrue(_setup.wait_for(lambda: got['done'], 30000))
        self.assertGreater(seen.calls, 30, seen)
        print(f'\n  guard, sample job in a process: {seen}')
        # the guard is red when one delivery on the window's thread takes 20 ms
        with self.assertRaises(AssertionError) as caught:
            with window_stays_free(self.center, strict=True):
                got = {'done': []}
                self.center.submit(sample.kind(), {'steps': 5, 'pause': 0.02}, on_partial=lambda k, d: work(0.02),
                                   on_done=lambda r, stale: got['done'].append(r))
                self.assertTrue(_setup.wait_for(lambda: got['done'], 30000))
        self.assertIn('count.on_partial', str(caught.exception))
        print(f'  guard, 20 ms on the window: {caught.exception}')

    def test_what_is_left_waiting_comes_after_a_rest_not_after_a_period_each(self):
        """The pieces of a result (the views told of a layout one by one): the next turn as soon as the window has
        had as long as the last one took, not a period later (seventeen pieces 50 ms apart: the deletion ended
        0,56 s later than before the jobs, measured on screen)."""
        from meridiana.gui.backend import work as work_backend
        self.assertEqual(work_backend.rest_after(0.5), work_backend.REST_MS)
        self.assertEqual(work_backend.rest_after(12.0), 12)
        self.assertEqual(work_backend.rest_after(400.0), work_backend.PERIOD_MS)
        settled(self.win)
        at = []

        def piece():                        # over a turn's budget: one piece a turn
            work(0.004)
            at.append(time.perf_counter())
        for index in range(8):
            self.center.piece(f'rest.{index}', piece)
        self.assertTrue(_setup.wait_for(lambda: len(at) == 8, 10000))
        gaps = sorted((b - a) * 1000 for a, b in zip(at, at[1:], strict=False))
        self.assertLess(gaps[len(gaps) // 2], work_backend.PERIOD_MS / 2, gaps)


def right(part):
    """The right edge of an item in the window."""
    return point(part).x() + part.width() / 2


def work(seconds):
    """`seconds` of computation on the calling thread (the window's, in the red case of the guard)."""
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        pass


def every_item(window):
    out, pending = [], [window.contentItem()]
    while pending:
        node = pending.pop()
        out.append(node)
        pending.extend(node.childItems())
    overlay = window.contentItem().parentItem()
    if overlay is not None:
        pending = list(overlay.childItems())
        while pending:
            node = pending.pop()
            if node not in out:
                out.append(node)
                pending.extend(node.childItems())
    return out


if __name__ == '__main__':
    unittest.main()
