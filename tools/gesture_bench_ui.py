"""Repeatable UI stress actions on the complete window, through Qt input and application commands."""
import math

from gesture_bench_core import gesture_steps
from gesture_bench_qt import Input, camera, find, variant

PHASES = ('model', 'plant', 'production', 'consumption', 'economics', 'report')


def evaluate(item, expression):
    from PySide6.QtQml import QQmlEngine, QQmlExpression
    query = QQmlExpression(QQmlEngine.contextForObject(item), item, expression)
    value = query.evaluate()
    if query.hasError():
        raise RuntimeError(query.error().toString())
    return variant(value[0] if isinstance(value, tuple) else value)


def numeric_state(host, view, target=None, kind=None):
    if kind == 'zoom-measures':
        return camera(view)
    state = {}
    if kind in ('resize', 'resize-meridio'):
        state.update(width=host.window.width(), height=host.window.height())
    names = ('leftPanel', 'checksPanel') if kind == 'cards' else ('assistantCharacter',) if kind == 'meridio' else ()
    # Match only the state controlled by this action. An unrelated fade/idle animation
    # must not prevent recognizing the first frame which shows a phase or a scroll.
    for name in names:
        obj = find(host.window, name)
        if obj is not None:
            for prop in ('x', 'y', 'width', 'height'):
                value = obj.property(prop)
                if isinstance(value, (int, float)):
                    state[name+'.'+prop] = value
    if target is not None and kind in ('report-scroll', 'table-scroll'):
        value = target.property('contentY')
        if value is not None:
            state['contentY'] = value
    phase = host.window.property('phase') or host.window.property('currentPhase')
    if phase in PHASES and kind == 'phases':
        state['phase'] = PHASES.index(phase)
    return state


class UIInput(Input):
    def __init__(self, app, host, view, kind):
        super().__init__(app, host, view)
        self.kind = kind
        self.last_phase = -1
        self.size = host.window.width(), host.window.height()

    def send(self, step):
        from PySide6.QtCore import QPointF
        action = step['action']
        if action == 'phases':
            index = int(step['progress']*(len(PHASES)-1))
            if index != self.last_phase:
                self.window.showPhase(PHASES[index])
                self.last_phase = index
        elif action in ('resize', 'resize-meridio'):
            # Keep the top left fixed on the secondary screen.
            amount = .5-.5*math.cos(2*math.pi*step['progress'])
            self.window.resize(round(self.size[0]-220*amount), round(self.size[1]-120*amount))
        elif action == 'card-resize-start':
            handle = find(self.window, 'leftResizeHandle')
            if handle is None:
                raise RuntimeError('left panel resize handle is absent')
            self.center = handle.mapToScene(QPointF(handle.width()/2, handle.height()/2))
            super().send(dict(action='press', button='left', x=0, y=0))
        else:
            super().send(step)


def prepare(app, host, view, kind, seed, rate, duration, setup):
    target = view
    if kind in ('resize-meridio', 'meridio'):
        layer = find(host.window, 'assistantLayer')
        if layer is None or not layer.property('opened'):
            host.shell.trigger('assistant')
        setup.turn_events(app, 600)
    if kind == 'cards':
        host.shell.trigger('default_layout')
        setup.turn_events(app, 500)
        target = find(host.window, 'checksTitleDrag')
    elif kind == 'meridio':
        target = find(host.window, 'assistantCharacter') or find(host.window, 'assistantTitle')
    elif kind == 'report-scroll':
        host.window.showPhase('report')
        if not setup.wait_until(app, lambda: find(host.window, 'reportPreview') is not None, 120):
            raise TimeoutError('report preview not available')
        preview = find(host.window, 'reportPreview')
        target = preview.property('contentItem')
        if not setup.wait_until(app, lambda: float(target.property('contentHeight') or 0) > target.height()+20, 180):
            raise TimeoutError('report pages did not become scrollable')
        report = host.parts.controllers['report']
        if not setup.wait_until(app, lambda: not report.busy and report.pageCount > 0, 180):
            raise TimeoutError('report page publication did not finish before the scroll benchmark')
        setup.turn_events(app, 800)
    elif kind == 'table-scroll':
        host.window.showPhase('plant')
        if not setup.wait_until(app, lambda: host.window.property('phase') == 'plant', 30):
            raise TimeoutError('plant phase not shown')
        panel = find(host.window, 'rightPanel')
        panel.setProperty('opened', True)
        evaluate(find(host.window, 'workspace'), 'selectPanel("properties")')
        setup.turn_events(app, 500)
        actions = host.parts.controllers['plantActions']
        actions.openSection('inverter')
        actions.setStringsView('table')
        if not setup.wait_until(app, lambda: find(host.window, 'stringsHorizontalScroll') is not None, 30):
            raise TimeoutError(f'string table not available: phase={host.window.property("phase")}, '
                               f'panel_visible={panel.isVisible()}, section={actions.section}, '
                               f'inspector={find(host.window, "plant-inspector") is not None}, '
                               f'inverters={find(host.window, "plant-inverters") is not None}')
        table = find(host.window, 'stringsHorizontalScroll')
        target = table
        # The user's string table expands to its whole height inside the plant panel.
        # Its enclosing panel scrolls vertically; do not accidentally benchmark the project tree.
        while target is not None:
            height = target.property('contentHeight')
            if height is not None and float(height) > target.height()+10:
                break
            target = target.parentItem()
        if target is not None:
            from PySide6.QtCore import QPointF
            content = target.property('contentItem')
            top = table.mapToItem(content, QPointF()).y()
            target.setProperty('contentY', max(0, min(top-50, float(target.property('contentHeight'))-target.height())))
        setup.turn_events(app, 500)
    elif kind == 'zoom-measures':
        from meridiana.app.view.measure_tool import Measure, Probe
        host.measure.tool.measures[:] = [Measure(1, 'distance', (Probe((0, 0, 20)), Probe((24, 0, 20))))]
        host.measure._changed()
        setup.turn_events(app, 400)
    if target is None:
        raise RuntimeError(f'{kind}: target not available')
    sender = UIInput(app, host, target, kind)
    if kind in ('cards', 'meridio'):
        steps = gesture_steps('drag', seed, rate, duration)
        for step in steps:
            step['button'] = 'left'
            if 'x' in step:
                step['x'] *= 3
                step['y'] -= step['x']*.5
        if kind == 'cards':
            at = steps[-1]['at_ms']+500
            steps += [dict(action='card-resize-start', at_ms=at)]
            steps += [dict(action='move', button='left', x=i*4, y=0, at_ms=at+i*20) for i in range(1, 21)]
            steps += [dict(action='release', button='left', x=80, y=0, at_ms=at+420)]
    elif kind in ('report-scroll', 'table-scroll'):
        steps = gesture_steps('scroll', seed, rate, duration)
        # Scroll down, then up; reserve horizontal deltas for view panning tests.
        for step in steps:
            step['dy'] = -step.get('dy', 0)*5
            step['dx'] = 0
        at = steps[-1]['at_ms']+250
        steps += [dict(action='wheel', angle=-120, at_ms=at+i*75) for i in range(8)]
    elif kind == 'zoom-measures':
        steps = gesture_steps('wheel', seed, rate, duration)
    else:
        steps = gesture_steps(kind, seed, rate, max(duration, 2) if kind == 'phases' else duration)
    return sender, steps, lambda: numeric_state(host, view, target, kind)
