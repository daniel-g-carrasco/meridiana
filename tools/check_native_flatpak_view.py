"""Check an installed native Flatpak view in an isolated self-test window.

Run inside the Flatpak with PYTHONPATH=/app/share/meridiana and an exposed output
parent directory. --output-dir must name a new directory. The probe temporarily
wraps methods in its own process; it never modifies installed application files,
real preferences, the compositor, or other windows. It selects the existing 3D
view action and verifies a rendered image followed by a 30-degree camera orbit.
"""
# ruff: noqa: E402
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from meridiana.ui import selftest

selftest.isolate(Path(tempfile.mkdtemp(prefix='meridiana-frame-probe-')))
from PySide6.QtCore import QTimer
from meridiana.ui.quick_image import QuickImage
from meridiana.ui.waiting import Skeleton3D

started = time.monotonic()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', required=True, type=Path,
                    help='a new output directory below a path exposed to the sandbox')
args = parser.parse_args()
folder = args.output_dir.resolve()
folder.mkdir(parents=False, exist_ok=False)
orbit_checks = []


def emit(event, **values):
    print('PROBE ' + json.dumps(dict(event=event, seconds=round(time.monotonic()-started, 6), **values)), flush=True)


def state(view):
    handle = view.window().windowHandle()
    return dict(visible=view.isVisible(), exposed=handle.isExposed() if handle else None,
                view_size=[view.width(), view.height()], image_null=view.image.isNull(),
                image_size=[view.image.width(), view.image.height()], dirty=view.dirty, stale=view.stale,
                frames=getattr(view, 'probe_frames', 0), after_rendering=getattr(view, 'probe_after', 0),
                frame_swapped=getattr(view, 'probe_swapped', 0),
                window_size=[view.window().width(), view.window().height()],
                split_sizes=view.window().split.sizes() if hasattr(view.window(), 'split') else None,
                parents=[dict(kind=type(parent).__name__, visible=parent.isVisible(),
                              size=[parent.width(), parent.height()])
                         for parent in [view.parentWidget(), view.window()] if parent is not None])


original_init = QuickImage.__init__
original_render = QuickImage._render
original_done = Skeleton3D.done


def initialise(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    self.probe_frames = self.probe_after = self.probe_swapped = 0

    def after():
        self.probe_after += 1
        if self.probe_after <= 3:
            emit('afterRendering', **state(self))

    def swapped():
        self.probe_swapped += 1
        if self.probe_swapped <= 3:
            emit('frameSwapped', **state(self))

    self.quick.afterRendering.connect(after)
    self.quick.frameSwapped.connect(swapped)
    emit('graphics_initialised', backend=self.rhi.backendName() if self.rhi else None, **state(self))


def _render(self):
    self.probe_frames += 1
    sample = self.probe_frames <= 4
    if sample:
        emit('render_enter', **state(self))
    then = time.monotonic()
    original_render(self)
    if sample:
        emit('render_return', duration=round(time.monotonic()-then, 6), **state(self))
    if not self.image.isNull() and not getattr(self, 'probe_saved', False):
        self.probe_saved = True
        raw = self.image.constBits().tobytes()
        emit('first_nonempty_image', sha256=hashlib.sha256(raw).hexdigest(), **state(self))
        self.image.save(str(folder / 'first-frame.png'))
        first_hash = hashlib.sha256(raw).hexdigest()
        first_frames = self.probe_frames

        def orbit():
            backend = self.backend
            emit('orbit_requested', bearing=backend.camera.bearing(), elevation=backend.camera.elevation())
            backend.orient(backend.camera.bearing()+30, backend.camera.elevation())

            def compare():
                current_hash = hashlib.sha256(self.image.constBits().tobytes()).hexdigest()
                changed = current_hash != first_hash and self.probe_frames > first_frames
                orbit_checks.append(changed)
                emit('orbit_image_check', changed=changed, sha256=current_hash, **state(self))
                self.image.save(str(folder / 'orbit.png'))
            QTimer.singleShot(800, self, compare)
        QTimer.singleShot(100, self, orbit)


def done(self, why):
    emit('skeleton_done', why=why, timer_ms=self.timer.interval(), **state(self.view))
    original_done(self, why)


QuickImage.__init__ = initialise
QuickImage._render = _render
Skeleton3D.done = done
from meridiana.ui.window import MainWindow
original_show = MainWindow.show

def show(self):
    original_show(self)
    def enable_3d():
        emit('explicit_3d_requested', **state(self.view3d))
        self._view_mode('3d')
        emit('explicit_3d_selected', **state(self.view3d))
    QTimer.singleShot(100, self, enable_3d)

MainWindow.show = show
emit('environment', wayland=os.environ.get('WAYLAND_DISPLAY'))
result = selftest.main([str(folder / 'self-test.txt')])
emit('exit', result=result, orbit_checks=orbit_checks)
if not orbit_checks or not all(orbit_checks):
    result = 2
sys.exit(result)
