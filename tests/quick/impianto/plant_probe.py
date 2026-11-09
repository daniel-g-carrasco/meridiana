"""Diagnostic event-loop probe for native rendering and Python workers."""
import sys
import time
import traceback
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone, inverter_record
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent
from PySide6.QtQuick import QQuickWindow
from meridiana import jobs
from meridiana.session import ProjectSession
from meridiana.quick.backend.plant import create_page, PAGE_URL

app = QApplication([])
p = capannone()
p.energy = {'inverters': [{'record': inverter_record(), 'count': 1, 'name': ''}]}
s = ProjectSession(p)
s.results, s.layout_keys, _laid = jobs.layout_of(p)
engine = QQmlEngine()
b = create_page(engine, s)
component = QQmlComponent(engine, PAGE_URL)
root = component.create()
window = QQuickWindow()
window.resize(1366, 900)
root.setParentItem(window.contentItem())
window.show()
started = time.monotonic()


def report():
    print('elapsed', time.monotonic() - started, 'busy', b.busy, flush=True)
    dest = Path('build/quick-foto/impianto/probe-stack.txt')
    dest.write_text('\n'.join(str(tid) + '\n' + ''.join(traceback.format_stack(frame))
                              for tid, frame in sys._current_frames().items()), encoding='utf-8')
    if not b.busy:
        window.grabWindow().save('build/quick-foto/impianto/probe.png')
        app.quit()


timer = QTimer()
timer.timeout.connect(report)
timer.start(2000)
QTimer.singleShot(30000, app.quit)
app.exec()
b.close()
