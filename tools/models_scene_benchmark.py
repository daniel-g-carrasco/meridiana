"""Photograph baked assets and measure QML frame times in a real Direct3D 11 window."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

import numpy as np  # noqa: E402
from PySide6.QtCore import QTimer, QSize  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlExpression, QQmlEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from meridiana import i18n, jobs, model  # noqa: E402
from meridiana.quick.backend.scene_assets import catalog  # noqa: E402
from meridiana.quick.backend.scene_host import SceneWindow  # noqa: E402
from meridiana.session import ProjectSession  # noqa: E402


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--mode',choices=['stress','gallery','humans'],default='stress')
    parser.add_argument('--dark',action='store_true')
    parser.add_argument('--frames',type=int,default=240)
    parser.add_argument('--no-shadows',action='store_true',help='Diagnostic comparison, not the acceptance run')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    os.environ['QML_DISABLE_DISK_CACHE']='1'
    os.environ['QT_DISABLE_SHADER_DISK_CACHE']='1'
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
    QQuickStyle.setStyle('Basic')
    app=QGuiApplication([]); i18n.setup('it')
    p=model.Project(name='Prova modelli CC0')
    overrides={}
    if args.mode=='stress':
        for i in range(200):
            p.props.append(model.Prop(f'c{i}',kind='compact',at=[(i%20)*5,(i//20)*4],rotation=0))
            p.props.append(model.Prop(f'h{i}',kind='adult',at=[(i%20)*5+2,(i//20)*4+2]))
        p.buildings.append(model.Building('b1','Capannone',[[0,45],[40,45],[40,65],[0,65]],height=9.5))
        p.subfields.append(model.SubField('s1','Sud',[[1,46],[39,46],[39,64],[1,64]],building='b1',
                                         params={'tilt':15.},filled=True))
    else:
        records=[r for r in catalog(active_only=True) if ('_standing' in r['key'] or '_walking' in r['key']) == (args.mode=='humans')]
        for i,record in enumerate(records):
            key=record['key']; oid=f'p{i}'
            # The gallery uses each asset's proportions and an illustrative physical height.
            height=1.75 if args.mode=='humans' else min(7.,float(record['default_height_m']))
            bounds=record['bounds']
            if isinstance(bounds,dict): extent=np.asarray(bounds['max'])-np.asarray(bounds['min'])
            else: extent=np.asarray(bounds[1])-np.asarray(bounds[0])
            p.props.append(model.Prop(oid,kind='adult' if args.mode=='humans' else 'other',
                                      at=[(i%8)*(2 if args.mode=='humans' else 10),(i//8)*(3 if args.mode=='humans' else 14)],
                                      height=height,width=float(extent[0]*height),length=float(extent[2]*height)))
            overrides[oid]=key
    session=ProjectSession(p)
    results,keys,_=jobs.layout_of(p,{})
    session.layout_done(session.generation,results,keys)
    started=time.perf_counter()
    host=SceneWindow(session,args.out/'instances',1600,960,args.dark)
    host.window.setMinimumSize(QSize(1600,960))
    host.backend.asset_overrides=overrides
    host.backend.rebuild()
    upload_ms=(time.perf_counter()-started)*1000
    host.view.setProperty('reducedMotion',True)
    host.view.setProperty('shadows',not args.no_shadows)

    def js(code):
        expression=QQmlExpression(QQmlEngine.contextForObject(host.view),host.view,code)
        result=expression.evaluate()
        if expression.hasError(): raise RuntimeError(expression.error().toString())
        return result[0] if isinstance(result,tuple) else result

    def shot(name):
        image=host.window.grabWindow()
        if image.isNull(): raise RuntimeError('Empty native frame')
        if (image.width(),image.height()) != (round(1600*host.window.devicePixelRatio()),round(960*host.window.devicePixelRatio())):
            raise RuntimeError('The desktop resized the requested capture')
        image.save(str(args.out/f'{name}.png'))

    host.window.show()
    phase=[0]
    call_start={}
    def advance():
        if phase[0]==0:
            js('fitScene()'); phase[0]=1; QTimer.singleShot(250,advance)
        elif phase[0]==1:
            shot('far')
            if args.mode=='stress':
                # An unchanged QML frame counter and callbacks prove content remains present.
                call_start.update(host.backend.calls)
                phase[0]=2; host.view.setProperty('benchmark',True); QTimer.singleShot(250,advance)
            else:
                js('cameraState = ({position: cameraState.position.map((v,i)=>cameraState.target[i]+(v-cameraState.target[i])*0.55), rotation:cameraState.rotation,target:cameraState.target,fov:60,ortho:false})')
                phase[0]=3; QTimer.singleShot(250,advance)
        elif phase[0]==2:
            if host.view.property('renderedFrames')<args.frames:
                QTimer.singleShot(250,advance); return
            host.view.setProperty('benchmark',False)
            shot('after-orbit')
            times=np.asarray(json.loads(js('JSON.stringify(frameTimes)')),float)
            measured=times[30:]
            call_delta={key:value-call_start.get(key,0) for key,value in host.backend.calls.items()
                        if value != call_start.get(key,0)}
            report={'platform':app.platformName(),'backend':str(host.window.rendererInterface().graphicsApi()),
                    'render_loop':os.environ.get('QSG_RENDER_LOOP','default'),'scale':host.window.devicePixelRatio(),
                    'logical_size':[host.window.width(),host.window.height()],
                    'pixel_size':[round(host.window.width()*host.window.devicePixelRatio()),round(host.window.height()*host.window.devicePixelRatio())],
                    'upload_ms':upload_ms,'shadows':not args.no_shadows,'cars':200,'people':200,'modules':host.backend.moduleCount,
                    'shared_geometries':len(host.backend._asset_geometry),'groups':len(host.backend.decorations),
                    'frames':len(measured),'median_ms':float(np.median(measured)),
                    'p95_ms':float(np.percentile(measured,95)),'max_ms':float(measured.max()),
                    'over_30_ms':int((measured>30).sum()),'frame_times_ms':times.tolist(),
                    'python_calls_during_orbit':call_delta,'warnings':host.warnings,
                    'scope':'QML frame intervals in a real D3D11 window on the separate desktop; physical monitor presentation not observed'}
            (args.out/'timing.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in report.items() if k!='frame_times_ms'}))
            js('cameraState = ({position: cameraState.position.map((v,i)=>cameraState.target[i]+(v-cameraState.target[i])*0.55), rotation:cameraState.rotation,target:cameraState.target,fov:60,ortho:false})')
            phase[0]=3; QTimer.singleShot(250,advance)
        else:
            shot('near')
            (args.out/'scene.json').write_text(json.dumps({'mode':args.mode,'models':overrides,'warnings':host.warnings,
                                                          'platform':app.platformName(),'backend':str(host.window.rendererInterface().graphicsApi()),
                                                          'scale':host.window.devicePixelRatio()},indent=2),encoding='utf-8')
            app.quit()
    QTimer.singleShot(900,advance)
    # A finite hard timeout makes a render-loop regression visible to automation.
    QTimer.singleShot(60000,app.quit)
    app.exec(); host.close(); app.processEvents()
    if host.warnings: return 1
    return 0 if (args.out/('timing.json' if args.mode=='stress' else 'scene.json')).exists() else 2


if __name__=='__main__': raise SystemExit(main())
