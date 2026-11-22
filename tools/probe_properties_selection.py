"""Record real-time selection frames in the actual offscreen workbench.

The project and recordings stay outside the repository. Import the test setup
before Qt to isolate all profile writes from the user's settings.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import _setup  # noqa: E402
from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from meridiana.core.model.model import Project  # noqa: E402
from meridiana.gui.application import QuickWindow, create_app  # noqa: E402


def items(item):
    yield item
    for child in item.childItems():
        yield from items(child)


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def record(host, action, duration=1800):
    page = next(i for i in items(host.window.contentItem()) if i.objectName() == 'properties-page')
    backend = host.parts.controllers['properties']
    forms = next(i for i in items(page) if i.objectName() == 'currentForm')
    frames, beats = [], []
    start = last = time.perf_counter()

    def beat():
        nonlocal last
        now = time.perf_counter()
        beats.append((now - last) * 1000)
        last = now

    def frame():
        holders = [i for i in forms.childItems() if i.property('key') is not None]
        visible = [i for i in holders if i.isVisible() and i.opacity() > .001]
        sections = [dict(title=i.property('title'), y=i.y(), opacity=i.opacity())
                    for h in visible for loader in h.childItems() for form in loader.childItems()
                    for i in form.childItems() if i.isVisible() and i.property('sectionControl') is True]
        frames.append(dict(ms=(time.perf_counter() - start) * 1000,
                           shown=page.property('shownForm'), wanted=backend.currentForm,
                           forms=[dict(key=i.property('key'), opacity=i.opacity(),
                                       y=i.y(), leaving=i.property('leaving')) for i in visible],
                           sections=sections))

    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(beat)
    timer.start()
    host.window.frameSwapped.connect(frame)
    action()
    wait(duration)
    host.window.frameSwapped.disconnect(frame)
    timer.stop()
    bad = [f for f in frames if len(f['forms']) > 1]
    unfinished = [f['ms'] for f in frames if f['shown'] != f['wanted'] or len(f['forms']) != 1
                  or any(h['leaving'] for h in f['forms'])]
    ready = next((f['ms'] for f in frames if f['ms'] > max(unfinished, default=-1)
                  and f['shown'] == f['wanted'] and len(f['forms']) == 1), None)
    return dict(finished_ms=ready, overlapping_frames=len(bad),
                longest_event_loop_gap_ms=max(beats, default=0), frames=frames)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    app = _setup.qt_or_skip()
    create_app()
    project, notice = Project.load(args.project)
    host = QuickWindow(project, args.output.parent / 'cache', real_views=True)
    try:
        host.window.resize(1586, 904)
        host.window.show()
        wait(3000)
        host.window.showPhase('model')
        host.window.setProperty('viewMode', 'both')
        wait(1500)
        session = host.bridge.session
        buildings = project.buildings[:3]
        gestures = [('empty', lambda: session.select('site', ''))]
        gestures += [('building', lambda: host.plan.editor.select('building', buildings[0].id)),
                     ('escape', lambda: host.plan.key('Escape'))]
        gestures += [(f'building_{index + 2}', lambda b=b: host.plan.editor.select('building', b.id))
                     for index, b in enumerate(buildings[1:])]
        if project.subfields:
            gestures += [('subfield', lambda: host.plan.editor.select('subfield', project.subfields[0].id))]
        result = dict(project_notice=notice, platform='offscreen',
                      base='abde90d8', gestures={})
        for name, action in gestures:
            result['gestures'][name] = record(host, action)
            print(name, {k: v for k, v in result['gestures'][name].items() if k != 'frames'}, flush=True)
        args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print('QML warnings:', host.warnings, flush=True)
    finally:
        host.close()
        app.processEvents()


if __name__ == '__main__':
    main()
