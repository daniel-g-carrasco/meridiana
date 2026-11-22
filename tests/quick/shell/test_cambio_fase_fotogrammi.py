"""Daniel 21/11/2026, from Production into Plant: «per un attimo compare la mappa per esteso che copre il pannello
Progetto, e il gruppo "moduli posati" si posiziona sopra la mappa come se la finestra fosse in modalità compatta».

Two causes. During the fade of a phase change the workspace kept the places of the phase left (rememberPhase), the
centre's too: out of Production, where Project is not shown, the centre was the whole width and the map covered the
Project card coming in. And the Plant's summary in the bar is made by an asynchronous Loader: while it was being made it
was not shown, and the place above the plan (for a window too narrow for it) took it. Now a card coming in has its
place at once and the centre is the smaller of the two; the place above the plan waits for the bar's part.

The frames of each phase change are read as they are drawn (afterAnimating, on the window's thread): in none of them
the centre stands over a card of the phase, and in none of them, the window being wide, the summary is above the plan.
On a real screen (MERIDIANA_TEST_SCREEN), with the asynchronous Loaders, as the window runs; offscreen the second
cause does not show (the Loaders are synchronous there).

    python -m unittest quick.shell.test_cambio_fase_fotogrammi
"""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import synthetic_plant

PHASES = ("model", "plant", "production", "consumption", "economics", "report")
FRAMES = 12                     # the frames read after each change: the fade lasts Theme.motion.FAST
SHOTS = os.environ.get("MERIDIANA_PHASE_SHOTS", "")     # a folder: the first frames of each change saved there


def rect(item):
    from PySide6.QtCore import QPointF
    at = item.mapToScene(QPointF(0, 0))
    return (round(at.x()), round(at.y()), round(item.width()), round(item.height()))


class PhaseFrames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.gui.application import QuickWindow, create_app
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(synthetic_plant(), Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.window = cls.host.window
        cls.window.resize(1600, 960)
        cls.window.show()
        session = cls.host.bridge.session
        cls.host.bridge._ask_layout()
        _setup.wait_until(cls.app, lambda: cls.host.bridge._layout is None and not session.telling()
                          and session.layout_keys == session.expected_layout_keys(), 180)
        _setup.turn_events(cls.app, 1500)
        cls.frames = {}
        # every phase entered once first (its pages made), then the changes read: the defect is in every change
        for phase in PHASES[1:] + PHASES[:1]:
            cls.window.showPhase(phase)
            _setup.turn_events(cls.app, 1200)
        order = ["production", "plant", "consumption", "model", "economics", "plant", "report", "model",
                 "production", "model", "plant"]
        cls.width = cls.window.width()
        for phase in order:
            was = cls.window.property('phase')
            cls.frames[(was, phase)] = cls.change(phase)

    @classmethod
    def change(cls, phase):
        from PySide6.QtCore import QObject
        w = cls.window
        central, project = w.findChild(QObject, 'centralPanel'), w.findChild(QObject, 'leftPanel')
        above, bar = w.findChild(QObject, 'viewsTrailing'), w.findChild(QObject, 'phaseTrailing')
        seen = []

        def frame():
            if len(seen) >= FRAMES:
                return
            seen.append(dict(central=rect(central), project=rect(project) if project.isVisible() else None,
                             projectHere=bool(project.property('phaseAllowed')) and project.isVisible(),
                             above=bool(above.property('active')), bar=bar.isVisible(),
                             leaving=w.property('leavingPhase')))
            if SHOTS and len(seen) <= 4:
                folder = Path(SHOTS)
                folder.mkdir(parents=True, exist_ok=True)
                w.grabWindow().save(str(folder / f"{w.property('phase')}-{len(seen)}.png"))
        w.afterAnimating.connect(frame)
        try:
            w.showPhase(phase)
            _setup.wait_until(cls.app, lambda: len(seen) >= FRAMES, 10)
            _setup.turn_events(cls.app, 600)
        finally:
            w.afterAnimating.disconnect(frame)
        return seen

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def test_the_centre_never_covers_a_card_of_the_phase(self):
        for (was, now), seen in self.frames.items():
            self.assertTrue(seen, (was, now))
            for i, f in enumerate(seen):
                if f['projectHere']:
                    x, _y, w, _h = f['project']
                    self.assertGreaterEqual(f['central'][0], x + w, (was, now, i, f))

    def test_the_summary_is_never_above_the_plan_in_a_wide_window(self):
        if self.width < 1400:
            self.skipTest(f"the window is {self.width} px wide: the summary goes above the plan in a narrow one")
        for (was, now), seen in self.frames.items():
            if now not in ('plant', 'production'):
                continue
            for i, f in enumerate(seen):
                self.assertFalse(f['above'], (was, now, i, f))


if __name__ == '__main__':
    unittest.main()
