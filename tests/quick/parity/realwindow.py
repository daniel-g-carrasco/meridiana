"""Native Quick frame harness. No desktop input or physical cursor movement.

Readback perturbs timings: this is evidence of rendered content, not a display
latency benchmark. Slots run on the GUI thread after frameSwapped; grabWindow
does a synchronized extra render. Signals are blocked during that readback to
avoid recursively measuring our own captures. See docs/quick/compat/prove-native.md.
"""
import json
import os
import sys
import time
import unittest
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QRect, Qt, Slot
from PySide6.QtGui import QGuiApplication, QImage, QWindow
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtTest import QTest

from quick.parity.geometry import capture_quick


def native_app():
    """Select D3D11 only for the explicitly requested Windows native run."""
    if os.environ.get('MERIDIANA_QUICK_NATIVE') != '1':
        raise unittest.SkipTest('Set MERIDIANA_QUICK_NATIVE=1 for native GPU evidence')
    if os.environ.get('QT_QPA_PLATFORM', '').split(':')[0] in ('offscreen', 'minimal'):
        raise unittest.SkipTest('Offscreen/minimal cannot provide native frame evidence')
    if sys.platform == 'win32':
        os.environ['QSG_RHI_BACKEND'] = 'd3d11'
        if QGuiApplication.instance() is None:
            QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
    app = QGuiApplication.instance() or QGuiApplication(['quick-native-parity'])
    require_native(app)
    return app


def require_native(app):
    if app.platformName() in ('offscreen', 'minimal'):
        raise unittest.SkipTest('Offscreen/minimal is not native GPU evidence')


@dataclass
class Frame:
    index: int
    timestamp: float
    image: QImage
    geometry: dict
    unexpected_windows: tuple


def _visible_windows():
    return [window for window in QGuiApplication.topLevelWindows() if window.isVisible()]


class FrameRecorder(QObject):
    """Capture swaps, named visual rectangles and every unexpected QWindow Show.

    ``allowed_windows`` is an explicit allowlist for a scenario's intentional
    popup. Existing visible windows form the baseline; hidden old windows do not.
    The event filter catches even a window shown then hidden between two frames.
    """
    def __init__(self, window, *, names=(), allowed_windows=()):
        super().__init__()
        self.window = window
        self.names = tuple(names)
        self.allowed = set(allowed_windows)
        self.frames = []
        self.unexpected_windows = []
        self.errors = []
        self.active = False
        self.capturing = False
        self.api = ''

    def __enter__(self):
        require_native(QGuiApplication.instance())
        self.baseline = set(_visible_windows()) | {self.window} | self.allowed
        self.active = True
        QGuiApplication.instance().installEventFilter(self)
        self.window.frameSwapped.connect(self._frame, Qt.ConnectionType.QueuedConnection)
        self.window.update()
        return self

    def __exit__(self, *exc):
        self.active = False
        self.window.frameSwapped.disconnect(self._frame)
        QGuiApplication.instance().removeEventFilter(self)
        if self.errors and not exc[0]:
            raise AssertionError('Frame capture failed: ' + '; '.join(self.errors))

    def eventFilter(self, watched, event):
        if self.active and event.type() == QEvent.Type.Show and isinstance(watched, QWindow):
            if watched not in self.baseline:
                label = watched.objectName() or watched.title() or watched.metaObject().className()
                self.unexpected_windows.append(label)
        return False

    @Slot()
    def _frame(self):
        if not self.active or self.capturing:
            return
        self.capturing = True
        previous = self.window.blockSignals(True)
        try:
            image = self.window.grabWindow()
            self.api = self.window.rendererInterface().graphicsApi().name
            if sys.platform == 'win32' and self.api != 'Direct3D11':
                self.errors.append('Expected native Direct3D11, got ' + self.api)
            snapshot = capture_quick(self.window)
            rects = {row['id']: row['rect'] for row in snapshot['widgets'] if row['id'] in self.names}
            self.frames.append(Frame(len(self.frames), time.perf_counter(), image, rects,
                                     tuple(self.unexpected_windows)))
        except (RuntimeError, ValueError, TypeError) as error:
            self.errors.append(str(error))
        finally:
            self.window.blockSignals(previous)
            self.capturing = False

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        metadata = {'capture': 'QQuickWindow.frameSwapped -> grabWindow', 'frames': len(self.frames),
                    'platform': QGuiApplication.platformName(), 'api': self.api,
                    'dpr': self.window.devicePixelRatio(), 'errors': self.errors,
                    'unexpected_windows': self.unexpected_windows,
                    'timing_caveat': 'Readback perturbs timing; timestamps are GUI readback times, not presentation times.',
                    'records': []}
        for frame in self.frames:
            filename = f'frame-{frame.index:04d}.png'
            target = directory / filename
            if target.exists():
                raise FileExistsError(target)
            if not frame.image.save(str(target)):
                raise OSError('Cannot save native frame ' + str(target))
            metadata['records'].append({'index': frame.index, 'timestamp': frame.timestamp,
                                        'image': filename, 'geometry': frame.geometry,
                                        'unexpected_windows': frame.unexpected_windows})
        with (directory / 'frames.json').open('x', encoding='utf-8') as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)
        return metadata

    def assert_valid(self, **checks):
        """Include transient Show events occurring after the last captured frame."""
        if self.errors:
            raise AssertionError('Frame capture failed: ' + '; '.join(self.errors))
        if self.unexpected_windows:
            raise AssertionError('Unexpected top-level: ' + repr(self.unexpected_windows))
        assert_frames(self.frames, **checks)


def wait_frames(recorder, count, timeout=5000):
    deadline = time.perf_counter() + timeout/1000
    while len(recorder.frames) < count and time.perf_counter() < deadline:
        recorder.window.update()
        QTest.qWait(10)
        if recorder.errors:
            raise AssertionError('; '.join(recorder.errors))
    if len(recorder.frames) < count:
        raise AssertionError(f'Only {len(recorder.frames)} native frames, expected {count}')


def _colors(image):
    import numpy as np
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return np.frombuffer(image.constBits(), dtype=np.uint8).reshape(image.height(), image.width(), 4).copy()


def assert_frames(frames, *, stable=None, regions=None, minimum_ink=0.005):
    """Reject blank frames, missing mandatory content, jumps and transient windows.

    Regions are logical rectangles expected to contain contrasting content in
    every frame, with at least 0.5% non-background pixels (configurable explicitly).
    The dominant RGB is the background; this also works with dark themes.
    Stable named items must remain present and within their per-frame logical
    delta budget. Do not include intentionally moving items in ``stable``.
    """
    import numpy as np
    if not frames:
        raise AssertionError('No frames captured')
    if not 0 < minimum_ink <= 1:
        raise ValueError('minimum_ink must be in (0, 1]')
    previous = None
    for frame in frames:
        if frame.unexpected_windows:
            raise AssertionError(f'Unexpected top-level at frame {frame.index}: {frame.unexpected_windows}')
        if frame.image.isNull():
            raise AssertionError(f'Null/blank frame {frame.index}')
        data = _colors(frame.image)
        if np.all(data[:, :, :3] == data[0, 0, :3]) or not np.any(data[:, :, 3]):
            raise AssertionError(f'Uniform/blank frame {frame.index}')
        for name, rect in (regions or {}).items():
            dpr = frame.image.devicePixelRatio()
            logical = QRect(*(round(value*dpr) for value in rect))
            if logical.isEmpty() or not frame.image.rect().contains(logical):
                raise ValueError('Required region outside screenshot: ' + name)
            region = data[logical.y():logical.y()+logical.height(), logical.x():logical.x()+logical.width(), :3]
            _, counts = np.unique(region.reshape(-1, 3), axis=0, return_counts=True)
            ink = 1 - float(counts.max())/counts.sum()
            if ink < minimum_ink:
                raise AssertionError(f'Disappearing/empty region {name} at frame {frame.index}: ink={ink:.6f}')
        for name, limit in (stable or {}).items():
            if limit < 0:
                raise ValueError('Negative movement budget: ' + name)
            if name not in frame.geometry:
                raise AssertionError(f'Required item disappeared: {name} at frame {frame.index}')
            if previous and name in previous.geometry:
                delta = max(abs(a-b) for a, b in zip(previous.geometry[name], frame.geometry[name], strict=True))
                if delta > limit:
                    raise AssertionError(f'Unexpected jump of {name} at frame {frame.index}: {delta} > {limit}')
        previous = frame


class PythonCalls:
    """Profile actual Python entries, independent of a cooperative bridge counter.

    Default scope is all meridiana modules on the GUI thread. Explicit file paths
    are useful for a fault injection. Worker threads are not a continuous gesture
    callback and are intentionally outside this probe.
    """
    def __init__(self, *, files=()):
        self.files = {str(Path(path).resolve()).casefold() for path in files}
        self.calls = Counter()
        self.entries = Counter()

    def _profile(self, frame, event, arg):
        if event != 'call':
            return
        module = frame.f_globals.get('__name__', '')
        filename = frame.f_code.co_filename
        if (self.files and str(Path(filename).resolve()).casefold() in self.files) or (
                not self.files and (module == 'meridiana' or module.startswith('meridiana.'))):
            self.calls[frame.f_code.co_name] += 1
            self.entries[f'{module}:{frame.f_code.co_name}:{frame.f_code.co_firstlineno}'] += 1

    def __enter__(self):
        self.previous = sys.getprofile()
        if self.previous is not None:
            raise RuntimeError('A Python profiler is already active')
        sys.setprofile(self._profile)
        return self

    def __exit__(self, *exc):
        sys.setprofile(self.previous)

    def assert_no_calls(self):
        if self.calls:
            raise AssertionError('Python called during continuous gesture: ' + repr(dict(self.entries)))
