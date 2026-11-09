"""Plan journeys on both complete windows, using the shared pilot and local Qt events."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('QSG_RENDER_LOOP', 'threaded')
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import quick_pilot as pilot  # noqa: E402
from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent, QKeySequence, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from quick.gestures import item, pump  # noqa: E402

original = pilot.perform
counter = 0


def perform(app, window, engine, step, last):
    global counter
    view = item(window, 'plan') if engine == 'quick' else window.plan
    action = step['action']
    if action == 'prepare_plan':
        if engine == 'quick':
            window.setProperty('viewMode', 'plan')
            backend = view.property('backend')
            backend.configureMaps({'source': 'none', 'offline': True})
            backend.setTool('select')
            if os.environ.get('R13_TRACE_SIDE'):
                def trace_side():
                    print('SIDE',backend.sideEditing,dict(backend.calls),
                          window.activeFocusItem().objectName() if window.activeFocusItem() else '',flush=True)
                backend.stateChanged.connect(trace_side)
        else:
            app.setActiveWindow(window)
            window.commands['view_plan'].trigger()
            view.setFocus()
        pump(500)
        view.fit() if engine == 'quick' else window._fit()
    elif action.startswith('plan_'):
        if engine == 'quick':
            target = window
            p = view.screen(*step['point'])
            pos = view.mapToScene(p)
        else:
            target = view.viewport()
            pos = QPointF(view.mapFromScene(QPointF(step['point'][0], -step['point'][1])))
        start = QPointF(target.mapFromGlobal(last))
        for i in range(1, 13):
            pilot.send_mouse(app, target, start+(pos-start)*(i/12), QEvent.Type.MouseMove)
            pump(12)
        if action != 'plan_hover':
            button = Qt.RightButton if action == 'plan_menu' else Qt.LeftButton
            pilot.send_mouse(app,target,pos,QEvent.Type.MouseButtonPress,button,button)
            pilot.send_mouse(app,target,pos,QEvent.Type.MouseButtonRelease,button)
            if action == 'plan_double':
                QTest.mouseDClick(target,button,Qt.NoModifier,pos.toPoint())
                QTest.mouseRelease(target,button,Qt.NoModifier,pos.toPoint())
        last = target.mapToGlobal(pos.toPoint())
    elif action == 'key':
        sequence = QKeySequence(step['key'])[0]
        target = (app.activePopupWidget() or app.focusWidget() or window) if engine == 'widgets' else window
        for kind in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
            app.sendEvent(target,QKeyEvent(kind,sequence.key(),sequence.keyboardModifiers(),step.get('text','')))
    else:
        if isinstance(step.get('target'),dict):
            step = {**step, 'target': step['target'][engine]}
        last = original(app,window,engine,step,last)
    pump(step.get('wait',400))
    if engine == 'quick':
        capture = window.grabWindow()
        p = view.mapToScene(QPointF(0,0))
        rect = (p.x(),p.y(),view.width(),view.height())
        tool = view.property('backend').tool
        camera = {k:view.property(k) for k in ('zoom','panX','panY','bearing','fitted')}
        camera.update(sideEditing=view.property('backend').sideEditing,
                      calls=dict(view.property('backend').calls),
                      focus=window.activeFocusItem().objectName() if window.activeFocusItem() else '')
    else:
        capture = window.grab().toImage()
        popup = app.activePopupWidget()
        if popup is not None:
            painter = QPainter(capture)
            painter.drawPixmap(window.mapFromGlobal(popup.mapToGlobal(popup.rect().topLeft())), popup.grab())
            painter.end()
        p = view.viewport().mapTo(window,view.viewport().rect().topLeft())
        rect = (p.x(),p.y(),view.viewport().width(),view.viewport().height())
        tool = view.tool
        matrix = view.viewportTransform()
        camera = dict(zoom=matrix.m11(),panX=matrix.dx(),panY=matrix.dy())
    if 'tool' in step:
        assert tool == step['tool'], (engine,step,tool)
    if action == 'plan_double':
        editing = view.property('backend').sideEditing if engine == 'quick' else view.editing_side is not None
        assert editing, (engine, 'Double click must open the side field', camera)
    out = Path(sys.argv[sys.argv.index('--out')+1])
    dpr = capture.devicePixelRatio()
    crop = capture.copy(*(round(x*dpr) for x in rect))
    crop.save(str(out/f'{counter:02}-{engine}-plan.png'))
    capture.save(str(out/f'{counter:02}-{engine}-with-popup.png'))
    for name, box in {'bar':(0,0,430,100), 'centre':(max(0,rect[2]/2-160),max(0,rect[3]/2-120),320,240)}.items():
        zone = crop.copy(*(round(x*dpr) for x in box))
        zone.scaled(zone.width()*2,zone.height()*2).save(str(out/f'{counter:02}-{engine}-{name}-200.png'))
    (out/f'{counter:02}-{engine}-plan.json').write_text(json.dumps({'rect':rect,'tool':tool,'camera':camera}),encoding='utf-8')
    counter += 1
    return last


pilot.perform = perform

if __name__ == '__main__':
    # The shared pilot launches its own path for "both". Run each engine explicitly.
    pilot.main()
