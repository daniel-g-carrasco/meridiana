"""R461: the year computed again in the background when the changes stop; all the power where the year is shown.
Real processes, on a project without modules (its year ends at once with its remark)."""
from pathlib import Path
import pickle
import tempfile
import time
import unittest
from unittest import mock

from _fixtures import capannone
from meridiana import config, resources
from meridiana.quick.app import create_app
from meridiana.quick.backend import shell_compute
from meridiana.quick.backend.shell_compute import ShellBridge


class Held(shell_compute.Worker):
    """A year that stays on its way until it is stopped: its process is never told where its work is."""
    made = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Held.made.append(self)

    def start(self):
        pass


class BackgroundYear(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.folder.cleanup)
        self.bridge = ShellBridge(capannone(), Path(self.folder.name))
        self.addCleanup(self.bridge.close)
        self.bridge.configure_background(True, .5, 2, 3.0)
        self.bridge.recompute()
        self.assertTrue(self.wait(lambda: not self.bridge.busy))

    def wait(self, condition, seconds=90):
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(.01)
        return False

    def held(self):
        Held.made = []
        # a year in a process of its own (R478 keeps one for the session: tests/quick/shell/test_live_compute.py)
        for patcher in (mock.patch.object(shell_compute, 'Worker', Held),
                        mock.patch.object(shell_compute, 'live_compute', return_value=False)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def years(self):
        return [job for job in Held.made if job.year]

    def change(self, tilt):
        self.bridge.session.edit('tilt', lambda p: p.subfields[0].params.update(tilt=tilt))

    def test_after_a_wait_without_changes_the_year_starts_low_and_with_few_processes(self):
        self.held()
        with mock.patch.object(resources, 'on_battery', return_value=False):
            self.change(22.0)
            self.assertTrue(self.bridge.background_timer.isActive())
            self.assertFalse(self.years(), 'not at once: after the wait')
            self.assertTrue(self.wait(lambda: self.years(), 5))
            self.assertTrue(self.bridge.updating)
            # the Quick is always in Italian (i18n.setup('it')): the words of the catalogue, not the English
            from meridiana.i18n import _
            words = _('Updating in the background: {what} changed. The numbers are those of before.')
            self.assertIn(words.split('{what}')[0].strip(' ,:'), self.shell_text())
            self.assertEqual(self.years()[0].options, {'low': True, 'workers': 2})
            options = pickle.loads((self.years()[0].folder / 'input.bin').read_bytes())[5]
            self.assertEqual(options, {'low': True, 'workers': 2})

    def test_each_change_stops_it_and_starts_the_wait_again(self):
        self.held()
        with mock.patch.object(resources, 'on_battery', return_value=False):
            self.change(22.0)
            self.assertTrue(self.wait(lambda: self.years(), 5))
            job = self.years()[0]
            self.change(24.0)
            self.assertTrue(job.cancelled)
            self.assertFalse(self.bridge.busy)
            self.assertTrue(self.bridge.background_timer.isActive())

    def test_a_phase_that_shows_the_year_gives_it_all_the_power(self):
        self.held()
        with mock.patch.object(resources, 'on_battery', return_value=False):
            self.change(22.0)
            self.assertTrue(self.wait(lambda: self.years(), 5))
            background = self.years()[0]
            self.bridge.yearWanted()
            self.assertTrue(background.cancelled)
            self.assertTrue(self.bridge.busy)
            self.assertFalse(self.bridge.updating)
            full = self.years()[-1]
            self.assertEqual(full.options, {})
            self.change(26.0)
            self.assertFalse(full.cancelled, 'a full year goes on (R458)')

    def test_on_battery_it_waits_longer_and_uses_one_process_or_none(self):
        self.held()
        with mock.patch.object(resources, 'on_battery', return_value=True):
            self.change(22.0)
            self.assertEqual(self.bridge.background_timer.interval(), 1500)
            self.assertTrue(self.wait(lambda: self.years(), 8))
            self.assertEqual(self.years()[0].options['workers'], 1)
            self.bridge.configure_background(True, .5, 2, 0.0)
            self.change(23.0)
            self.assertFalse(self.bridge.background_timer.isActive())

    def shell_text(self):
        from meridiana.quick.backend.shell import ShellController
        return ShellController(self.bridge).yearState['text']

    def test_switched_off_nothing_starts_by_itself(self):
        self.bridge.configure_background(False)
        self.change(22.0)
        self.assertFalse(self.bridge.background_timer.isActive())

    def test_the_preferences_are_in_the_file(self):
        cfg = config.Config()
        self.assertEqual((cfg.background_year, cfg.background_year_wait_s, cfg.background_year_workers,
                          cfg.background_year_battery_factor), (True, 5.0, 2, 3.0))
        old = config.migrate({'version': 27}) if hasattr(config, 'migrate') else None
        if old is not None:
            self.assertTrue(old['background_year'])


if __name__ == "__main__":
    unittest.main()
