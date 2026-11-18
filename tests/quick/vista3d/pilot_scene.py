"""The shared pilot with semantic targets for the two implementations of the 3D view."""
from pathlib import Path
import json
import sys

from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent, QPainter

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'))
import quick_pilot as pilot  # noqa: E402

original_target, original_perform = pilot.find_target, pilot.perform


def target(window, text, engine):
    if not text.startswith('@'):
        return original_target(window,text,engine)
    if engine == 'widgets':
        obj = window.view3d
        if text == '@cube-menu':
            return obj.cube,QPointF(obj.cube.width()-9,obj.cube.height()-8)
        if text == '@sun-day':
            obj=window.sunbar.day
            return obj,QPointF(obj.width()-10,obj.height()/2)
        elif text == '@fit':
            obj=next(b for a,b in obj.viewbar.buttons.items() if any(s.toString()=='F' for s in a.shortcuts()))
        return obj,QPointF(obj.rect().center())
    obj=window.findChild(QObject,{'@scene':'sceneInput','@cube-menu':'viewCube','@sun-day':'sunDay','@fit':'sceneFit'}[text])
    point=QPointF(obj.width()-9,obj.height()-8) if text=='@cube-menu' else QPointF(obj.width()/2,obj.height()/2)
    return window,obj.mapToScene(point)


def perform(app, window, engine, step, last):
    if engine == 'widgets' and step['action'] == 'snapshot':
        original_grab=window.grab
        def with_popups():
            picture=original_grab()
            painter=QPainter(picture)
            for popup in app.topLevelWidgets():
                kind=popup.windowFlags() & Qt.WindowType.WindowType_Mask
                if popup.isVisible() and kind in (Qt.WindowType.Popup,Qt.WindowType.ToolTip):
                    painter.drawPixmap(window.mapFromGlobal(popup.mapToGlobal(popup.rect().topLeft())),popup.grab())
            painter.end()
            return picture
        window.grab=with_popups
    if engine == 'widgets' and step['action'] == 'key' and app.activePopupWidget() is not None:
        popup=app.activePopupWidget()
        key=QKeySequence(step['key'])[0]
        for event in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
            app.sendEvent(popup,QKeyEvent(event,key.key(),key.keyboardModifiers()))
        return last
    if engine == 'quick':
        # quick_pilot disables the reference mascot's animation. Freeze the
        # same preference here so photographs compare the settled placement.
        if step['action'] == 'snapshot':
            window.findChild(QObject,'assistantLayer').setProperty('animated',False)
        def record():
            from quick.vista3d._fidelity_support import data
            layer=window.findChild(QObject,'assistantLayer')
            view=window.findChild(QObject,'viewport3d')
            host=window.findChild(QObject,'assistantHost')
            home=host.property('homeItem')
            print('scene-state '+json.dumps({'step':step,'phase':window.property('phase'),
                'avatar':[layer.property('avatarX'),layer.property('avatarY')],
                'home':home.objectName() if home else None,'homeRect':layer.property('homeRect').getRect(),
                'temporary':layer.property('temporary'),'opened':layer.property('opened'),
                'camera':data(view,'cameraState'),'navigation':view.property('navigationStyle'),
                'sceneRect':view.mapRectToScene(view.boundingRect()).getRect()}),flush=True)
        QTimer.singleShot(max(0,step.get('wait',400)-50),record)
    if step['action'] != 'drag3d':
        return original_perform(app,window,engine,step,last)
    surface, start=target(window,'@scene',engine)
    button=Qt.MouseButton.MiddleButton
    mods=Qt.KeyboardModifier.ShiftModifier if step.get('orbit') else Qt.KeyboardModifier.NoModifier
    delta=QPointF(*step.get('delta',[75,25]))
    def send(kind,point,buttons):
        changed = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else button
        app.sendEvent(surface,QMouseEvent(kind,point,point,QPointF(surface.mapToGlobal(point.toPoint())),changed,buttons,mods))
    send(QEvent.Type.MouseButtonPress,start,button)
    for i in range(1,17):
        send(QEvent.Type.MouseMove,start+delta*(i/16),button)
        pilot.pump(16)
    send(QEvent.Type.MouseButtonRelease,start+delta,Qt.MouseButton.NoButton)
    return surface.mapToGlobal((start+delta).toPoint())


if __name__ == '__main__':
    pilot.find_target, pilot.perform, pilot.__file__ = target,perform,__file__
    pilot.main()
