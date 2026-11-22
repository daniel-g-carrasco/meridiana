"""Opt-in native Qt timing fallback when QRhiSwapChain is not exposed by the binding."""
import sys
import time

from gesture_bench_core import parse_qsg_message


class NativeTimings:
    def __init__(self):
        from PySide6.QtCore import QLoggingCategory, qInstallMessageHandler
        self.rows = []
        self.previous = qInstallMessageHandler(self.message)
        QLoggingCategory.setFilterRules('qt.scenegraph.time.*=false\nqt.scenegraph.time.renderloop=true')

    def message(self, kind, context, message):
        fields = parse_qsg_message(message)
        if 'device loss' in message.lower() or 'device lost' in message.lower():
            self.rows.append(dict(record='graphics_error', t_ns=time.perf_counter_ns(), message=message))
        if fields:
            self.rows.append(dict(record='native_timing', t_ns=time.perf_counter_ns(), **fields))
        elif not context.category.startswith('qt.scenegraph.time.'):
            if self.previous:
                self.previous(kind, context, message)
            else:
                sys.stderr.write(message+'\n')

    def merge(self, rows):
        frames = [r for r in rows if r['record'] == 'frame']
        for native in self.rows:
            if native['record'] == 'graphics_error':
                rows.append(dict(native, version=2))
                continue
            if 'gpu_ms' in native:
                frame = next((r for r in reversed(frames) if r['t_ns'] <= native['t_ns']), None)
            else:
                frame = next((r for r in reversed(frames) if r.get('sync_ns', r['t_ns']) <= native['t_ns']), None)
            if frame is not None:
                frame.update({k: v for k, v in native.items() if k not in ('record', 't_ns')})
                frame['native_timing_resolution_ms'] = 1
        self.rows.clear()

    def suspend(self):
        from PySide6.QtCore import QLoggingCategory, qInstallMessageHandler
        # No Python logging callback may remain on the render thread during grabWindow.
        QLoggingCategory.setFilterRules('qt.scenegraph.time.*=false')
        qInstallMessageHandler(self.previous)

    def resume(self):
        from PySide6.QtCore import QLoggingCategory, qInstallMessageHandler
        qInstallMessageHandler(self.message)
        QLoggingCategory.setFilterRules('qt.scenegraph.time.*=false\nqt.scenegraph.time.renderloop=true')

    def close(self):
        self.suspend()
