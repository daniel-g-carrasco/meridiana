"""Reproducible Widgets/Quick viewport photographs, with an identical camera and mesh."""
import argparse
import json
import os
from pathlib import Path
import tempfile

import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QLocale, QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QAction
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from meridiana import camera, config, i18n, jobs, mesh, model, viewaids, view_colours
from meridiana.session import ProjectSession
from quick.vista3d._fidelity_support import click, data, js, settle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('widgets', 'quick'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--theme', default='light')
    parser.add_argument('--width', type=int, default=800)
    parser.add_argument('--height', type=int, default=600)
    parser.add_argument('--large', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    os.environ['QT_DISABLE_SHADER_DISK_CACHE'] = '1'
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
    QQuickStyle.setStyle('Basic')
    app = QApplication([])
    i18n.setup('it')
    QLocale.setDefault(QLocale('it_IT'))
    p = model.Project(name='Confronto vista 3D')
    p.buildings = [model.Building('b1','Capannone',[[0,0],[40,0],[40,20],[0,20]],height=9.5)]
    p.subfields = [model.SubField('s1','Copertura',[[1,1],[39,1],[39,19],[1,19]],building='b1',
                                 params={'tilt':15.},filled=True)]
    session = ProjectSession(p)
    results, keys, _ = jobs.layout_of(p, {})
    session.layout_done(session.generation, results, keys)
    triangles, table, _ = mesh.project_scene(p, results)
    with tempfile.TemporaryDirectory(dir=args.out) as tmp:
        if args.engine == 'widgets':
            from meridiana.ui import design, icons
            from meridiana.ui.theme import Theme
            from meridiana.ui.sunbar import SunBar
            from meridiana.ui.viewbar import ViewBar
            from meridiana.ui.view3d import View3D
            design.set_text_size('large' if args.large else 'medium')
            theme = Theme(config.Config(theme=args.theme, font='plex', accent='indigo', backgrounds='grey',
                                        text_size='large' if args.large else 'medium'), app=app)
            window = QWidget()
            window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            layout = QVBoxLayout(window)
            layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
            view, sun = View3D(window), SunBar(window)
            layout.addWidget(view, 1); layout.addWidget(sun)
            actions = []
            for key, word in [('fit','Inquadra'),('zoom_in','Avvicina'),('zoom_out','Allontana')]:
                action = QAction(icons.icon(key), word, window)
                actions.append(action)
            view.viewbar = ViewBar(view,[actions]); view.viewbar.set_colours(theme.tokens)
            view.cube.set_colours(theme.tokens)
            sun.sunChanged.connect(view.set_sun)
            sun.set_site(p.site.lat,p.site.lon,p.sun_window)
            view.show_scene(triangles,table,fit=True)
            window.resize(args.width,args.height); window.show(); settle(app,.5)
            # The same frozen geometry/camera on both renderers; world bounds exclude the ground.
            lo, hi = triangles[0].min(0),triangles[0].max(0)
            cam = camera.Camera(rotation=camera.look(30,-35))
            cam.fit((lo+hi)/2,float(np.linalg.norm(hi-lo)/2+2),args.width/view.height())
            view.backend.camera=cam; view.backend.cameraChanged.emit(); view.update()
            geometry = {'sceneHeight':view.height(),'sunHeight':sun.height(),
                        'toolbar':[view.viewbar.x(),view.viewbar.y(),view.viewbar.width(),view.viewbar.height()],
                        'cube':[view.cube.x(),view.cube.y(),view.cube.width(),view.cube.height()],
                        'sunChildren':[[type(c).__name__,c.x(),c.y(),c.width(),c.height()] for c in (sun.play,sun.day,sun.hour,sun.clock,sun.short,sun.design)]}
            state = {k:getattr(cam,k).tolist() for k in ('position','rotation','target')} | {'fov':cam.fov,'ortho':cam.ortho}
            sun_state={'year':2026,'month':sun.day.date().month(),'day':sun.day.date().day(),'hour':sun.hour.value()/6}
            (args.out/'reference.json').write_text(json.dumps({'camera':state,'sun':sun_state,'geometry':geometry}),encoding='utf-8')
            def select(on):
                view.set_outline(viewaids.outline(p,results,'building','b1') if on else [],[],view_colours.kind_colour('building'))
                view._changed()
            def gizmo():
                view.backend.set_gizmo([20,9.5,-10])
                view._changed()
            def calendar_shot():
                QTest.mouseClick(sun.day,Qt.MouseButton.LeftButton,pos=QPoint(sun.day.width()-10,sun.day.height()//2))
                settle(app,.2)
                widget=sun.day.calendarWidget()
                geometry['calendar']=[widget.width(),widget.height()]
                geometry['calendarControls']={name:[obj.mapTo(widget,QPoint(0,0)).x(),obj.mapTo(widget,QPoint(0,0)).y(),obj.width(),obj.height()]
                    for name in ('qt_calendar_prevmonth','qt_calendar_monthbutton','qt_calendar_yearbutton','qt_calendar_nextmonth')
                    if (obj:=widget.findChild(QWidget,name)) is not None}
                return widget.grab().toImage()
            def grab():
                return window.grab().toImage()
            def close():
                window.close(); window.deleteLater()
        else:
            from meridiana.quick.backend.scene_host import SceneWindow
            host=SceneWindow(session,tmp,args.width,args.height,args.theme=='dark')
            host.theme.configure({'textSize':'large' if args.large else 'medium'})
            window,view=host.window,host.view
            window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            window.show();settle(app,.5)
            reference=json.loads((args.out/'reference.json').read_text(encoding='utf-8'))
            view.setProperty('reducedMotion',True)
            js(view,'userMoved=true; cameraState='+json.dumps(reference['camera']))
            host.backend.setSun(**reference['sun'])
            geometry=data(view,'({sceneHeight:sceneHeight,sunHeight:sunBarHeight,camera:cameraState})')
            from PySide6.QtCore import QObject
            geometry['controls'] = {name: data(window.findChild(QObject, name), '[x,y,width,height]')
                                    for name in ('sceneToolbar','sunPlay','sunDay','sunHour','sunClock','sunPosition','sunDesign')}
            def select(on):
                session.select('building','b1') if on else session.select('site','')
            def gizmo():
                view.setProperty('moveMode',True)
            def calendar_shot():
                day=window.findChild(QObject,'sunDay')
                xy=data(day,'[mapToItem(null,width/2,height/2).x,mapToItem(null,width/2,height/2).y]')
                click(window,*xy); settle(app,.2)
                popup=window.findChild(QObject,'sunCalendar')
                x,y=data(popup,'[contentItem.mapToItem(null,0,0).x,contentItem.mapToItem(null,0,0).y]')
                w,h=popup.property('width'),popup.property('height')
                geometry['calendar']=[w,h]
                d=window.devicePixelRatio()
                return window.grabWindow().copy(QRect(round((x-4)*d),round((y-4)*d),round(w*d),round(h*d)))
            def grab():
                return window.grabWindow()
            close=host.close
        for selected in (False,True):
            select(selected);settle(app,.4)
            image=grab()
            if image.isNull():
                raise RuntimeError('Empty image')
            name=f'{args.engine}-'+('selected' if selected else 'normal')
            image.save(str(args.out/(name+'.png')))
        gizmo(); settle(app,.3)
        grab().save(str(args.out/(args.engine+'-gizmo.png')))
        calendar_shot().save(str(args.out/(args.engine+'-calendar.png')))
        (args.out/(args.engine+'.json')).write_text(json.dumps(geometry,indent=2),encoding='utf-8')
        close()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.processEvents()


if __name__ == '__main__':
    main()
