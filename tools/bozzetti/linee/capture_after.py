"""Capture the real program after the annotation migration, without saving its project."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PySide6.QtQml import QQmlEngine, QQmlExpression

from capture import QuickWindow, Project, QObject, create_app, grab, save, settle, wait
from meridiana.app.view.measure_tool import Measure, Probe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--theme', choices=('light', 'dark'), required=True)
    parser.add_argument('--scale', type=float, required=True)
    parser.add_argument('--revision', default='-R01')
    parser.add_argument('--hide-background', action='store_true', help='Diagnostic capture without the map layer')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(args.project.read_bytes()).hexdigest()
    project, _ = Project.load(args.project)
    app = create_app()
    host = QuickWindow(project, args.out / f'profile-{args.theme}-{args.scale:g}', real_views=True,
                       theme={'theme': args.theme, 'reducedMotion': True})
    try:
        host.plan.configureMaps({'offline': True, 'source': 'pcn', 'veil': 0})
        host.plan.maps.loader.cache_dir = args.cache / 'tiles'
        host.window.resize(1920, 1080)
        host.window.show()
        settle(app, 3)
        host.window.resize(1920, 1080)
        settle(app, 1)
        host.shell.trigger('phase_model')
        host.window.setProperty('viewMode', 'plan')
        settle(app, 2)
        plan = host.window.findChild(QObject, 'plan')
        plan.fit()
        building = project.buildings[0]
        host.plan.editor.select('building', building.id)
        ring = building.footprint
        height = building.height
        # Real session measurements, not drawings superimposed on a screenshot.
        points = [Probe((p[0], p[1], height)) for p in ring[:3]]
        host.measure.tool.measures[:] = [Measure(1, 'distance', tuple(points))]
        host.measure._changed()
        settle(app, 4)
        if args.hide_background:
            for child in plan.childItems():
                source = child.property('source')
                if hasattr(source, 'toString') and source.toString().endswith('MapLayer.qml'):
                    child.setVisible(False)
            settle(app, 1)
        records = []
        for name in ('plan', '3d'):
            host.window.setProperty('viewMode', name)
            settle(app, 3)
            item = plan if name == 'plan' else host.window.findChild(QObject, 'viewport3d')
            if name == '3d':
                item.fitScene()
                settle(app, 2)
                wait(app, lambda item=item: not item.property("sceneMeasure").property("annotationPending"), 30)
            target = args.out / f'{name}-{args.theme}-{args.scale:g}{args.revision}.png'
            image = grab(app, item, args.scale)
            save(image, target)
            records.append({'file': target.name, 'width': image.width(), 'height': image.height(),
                            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
            if name == 'plan':
                expression = QQmlExpression(QQmlEngine.contextForObject(plan), plan, '''JSON.stringify((function walk(item) {
                    let out=[];
                    if(item.rendererType !== undefined) out.push({name:item.objectName,type:item.toString(),visible:item.visible,
                        status:item.status,renderer:item.rendererType,paths:item.data.length,
                        pens:Array.from(item.data).filter(p=>p.strokeWidth!==undefined).map(p=>({width:p.strokeWidth,
                            ink:p.strokeColor.toString(),fill:p.fillColor.toString(),scale:p.viewScale,
                            surface:!!p.surface,software:p.software})),
                        model:item.modelData || null});
                    for(let child of item.children) out=out.concat(walk(child));
                    return out;
                })(plan))''')
                states = expression.evaluate()
                records[-1]['shapes'] = json.loads(states[0] if isinstance(states, tuple) else states)
                records[-1]['objects'] = len(host.plan.objects)
                records[-1]['zoom'] = plan.property('zoom')
        report = {'images': records, 'project_sha256': before, 'warnings': host.warnings,
                  'loaded_tiles': len(host.plan.maps.state.loaded), 'platform': app.platformName()}
        target = args.out / f'manifest-{args.theme}-{args.scale:g}{args.revision}.json'
        if target.exists():
            raise FileExistsError(target)
        target.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        host.close()
    if hashlib.sha256(args.project.read_bytes()).hexdigest() != before:
        raise RuntimeError('The source project changed')


if __name__ == '__main__':
    main()
