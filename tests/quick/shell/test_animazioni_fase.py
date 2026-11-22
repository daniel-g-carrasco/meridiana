"""Daniel 21/11/2026: «vorrei togliere le animazioni tra il passaggio dalle fasi: quelle dello scorrimento della
linguetta e quelle di comparsa e ricomparsa dei contenuti. È possibile avere un'impostazione per attivarle e
disattivarle?».

The setting «phase_animations» (Appearance, off by default, the same key as the template's kit) is the theme's one
constant Theme.phaseMotion, false as well when less motion is asked. Off, a change of phase is immediate: from its
first frame nothing is leaving, every page is shown whole or not at all and the tab's marker stands on the new tab;
on, the change fades and slides as before. The other animations (menus, tips, scroll bars) do not read it.

    python -m unittest quick.shell.test_animazioni_fase
"""
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import synthetic_plant

FRAMES = 10


class TheSetting(unittest.TestCase):
    def setUp(self):
        from meridiana.app.platform import config
        from meridiana.gui.backend.settings import SettingsBackend
        from meridiana.gui.backend.tokens import ThemeTokens
        self.app = _setup.qt_or_skip()
        self.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = Path(self.folder.name) / 'config.json'
        self.theme = ThemeTokens()
        self.backend = SettingsBackend(config.Config(), self.path, theme=self.theme)

    def tearDown(self):
        self.folder.cleanup()

    def test_off_by_default_saved_and_at_once(self):
        from meridiana.app.platform import config
        from meridiana.gui.backend.settings_schema import SECTIONS
        self.assertIn('phase_animations', SECTIONS['appearance'])
        self.assertFalse(self.backend.values['phase_animations'])
        self.assertFalse(self.theme.property('phaseMotion'))
        self.assertTrue(self.backend.setValue('phase_animations', True))
        self.assertTrue(self.theme.property('phaseMotion'))
        self.assertTrue(config.load(self.path).extra['phase_animations'])
        # less motion asked: off whatever the setting says
        self.assertTrue(self.backend.setValue('reduced_motion', True))
        self.assertFalse(self.theme.property('phaseMotion'))
        self.assertTrue(self.backend.setValue('reduced_motion', False))
        self.assertTrue(self.backend.setValue('phase_animations', False))
        self.assertFalse(self.theme.property('phaseMotion'))
        self.assertFalse(self.backend.setValue('phase_animations', 'yes'))


class PhaseFrames(unittest.TestCase):
    """The frames of a change of phase, read as they are drawn (afterAnimating), with the setting off and on."""

    @classmethod
    def frames_of(cls, animated):
        from PySide6.QtCore import QObject
        from meridiana.gui.application import QuickWindow, create_app
        app = _setup.qt_or_skip()
        create_app()
        folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        host = QuickWindow(synthetic_plant(), Path(folder.name), real_views=True,
                           theme={'theme': 'light', 'phaseAnimations': animated})
        window = host.window
        window.resize(1400, 900)
        window.show()
        _setup.turn_events(app, 1500)
        seen = {}
        try:
            for phase in ('plant', 'production', 'model', 'plant'):
                window.showPhase(phase)             # each page made once first
                _setup.turn_events(app, 800)
            window.showPhase('model')
            _setup.turn_events(app, 800)
            outline = window.findChild(QObject, 'phaseOutline')
            # every body that comes and goes with the phase (Controls/PhaseFade.qml): the bar's groups, the pages,
            # the inspectors, the cards
            fades = [o for o in window.findChildren(QObject) if o.metaObject().className().startswith('PhaseFade')]
            targets = [f.property('target') for f in fades]
            targets = [t for t in targets if t is not None]
            assert len(targets) >= 5, len(targets)
            for phase in ('plant', 'production', 'model'):
                frames = []

                def frame(frames=frames):
                    if len(frames) < FRAMES:
                        frames.append(dict(leaving=window.property('leavingPhase'),
                                           marker=round(outline.property('tx'), 1),
                                           opacities=sorted({round(t.property('opacity'), 2) for t in targets
                                                             if t.property('visible')})))
                window.afterAnimating.connect(frame)
                try:
                    window.showPhase(phase)
                    _setup.wait_until(app, lambda frames=frames: len(frames) >= FRAMES, 10)
                finally:
                    window.afterAnimating.disconnect(frame)
                _setup.turn_events(app, 600)
                final = round(outline.property('tx'), 1)          # where the marker rests
                seen[phase] = (frames, final, window.property('leavingPhase'))
        finally:
            host.close()
            folder.cleanup()
        return seen

    def test_off_the_first_frame_is_the_last(self):
        for phase, (frames, final, _left) in self.frames_of(False).items():
            self.assertTrue(frames, phase)
            for i, f in enumerate(frames):
                self.assertEqual(f['leaving'], '', (phase, i, f))
                self.assertEqual(f['marker'], final, (phase, i, f))
                # whole or not at all (0: the views kept up under a page that is not theirs, `retained`)
                self.assertTrue(set(f['opacities']) <= {0.0, 1.0}, (phase, i, f))

    def test_on_it_fades_and_slides_as_before(self):
        # the fade itself is an OpacityAnimator, on the render thread: its steps do not show in the property; the
        # page left still drawn (leavingPhase) is what starts it
        moved = 0
        for phase, (frames, final, left) in self.frames_of(True).items():
            self.assertEqual(left, '')                       # over once the fade has run
            self.assertTrue(frames[0]['leaving'], phase)
            moved += any(f['marker'] != final for f in frames)
        self.assertEqual(moved, 3)


if __name__ == '__main__':
    unittest.main()
