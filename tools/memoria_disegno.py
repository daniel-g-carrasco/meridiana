"""memoria_disegno.py (20/11/2026, study 56): what the drawing paths cost in time and in the process' memory, without
a screen and without the window: the project read, its layouts, the plan's scene (scene_of), the plan's scene of the
strings at the scales a zoom passes (the one the window makes again when the wheel stops, R541), the 3D scene's
arrays (mesh.project_scene). One step at a time, each with its time and the process' memory (procmem) after it.

    python tools/memoria_disegno.py <project.meridiana> --out <file.json> [--repeat 3]

Synthetic projects only (tools/gesture_projects.py of r37-zoom-pianta). The project is read, never written; the
profile's folders are pointed to a temporary folder."""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import pickle
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
work = Path(tempfile.mkdtemp(prefix='meridiana-memoria-disegno-'))
for name in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'APPDATA', 'LOCALAPPDATA'):
    os.environ[name] = str(work / name.lower())
    Path(os.environ[name]).mkdir(parents=True, exist_ok=True)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from meridiana.core.compute import procmem  # noqa: E402

MIB = 1 << 20


def mib(n):
    return round((n or 0) / MIB, 1)


def step(rows, name, make):
    gc.collect()
    before = procmem.rss() or 0
    t = time.perf_counter()
    value = make()
    ms = round((time.perf_counter() - t) * 1000, 1)
    gc.collect()
    after = procmem.rss() or 0
    rows.append({'step': name, 'ms': ms, 'rss_mib': mib(after), 'delta_mib': mib(after - before)})
    print(rows[-1], flush=True)
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--repeat', type=int, default=3)
    args = ap.parse_args()
    rows = []
    out = {'project': args.project.name, 'rows': rows}
    step(rows, 'import', lambda: __import__('meridiana.app.jobs') and __import__('meridiana.gui.backend.plan_scene'))
    from meridiana.app import jobs
    from meridiana.app.view import plan_wiring
    from meridiana.core.geometry import mesh
    from meridiana.core.model.model import Project
    from meridiana.gui.backend import plan_scene

    project, _ = step(rows, 'load', lambda: Project.load(args.project))
    results, keys, _laid = step(rows, 'layout_of', lambda: jobs.layout_of(project))
    modules = sum(len(getattr(r, 'modules', [])) for r in results.values() if not isinstance(r, Exception))
    out['modules'] = modules
    for i in range(args.repeat):
        scene = step(rows, f'scene_of {i + 1}', lambda: plan_scene.scene_of(project, results))
    out['scene_of_pickle_mib'] = mib(len(pickle.dumps(scene, protocol=5)))
    out['scene_objects'] = len(scene.get('objects', []))

    # the strings at the scales of a zoom: module of 2, 5, 10, 20, 40, 100, 300 px and back
    options = {'mpp': 0.02, 'states': {}, 'tool': 'select', 'chosen': -1, 'optimizers': {}, 'partial': {}}
    view = plan_wiring.Strings(project, results, keys, options)
    wiring = plan_wiring.WiringScene()
    wiring._prepare(view)
    side = wiring.size
    out['module_side_m'] = side
    sizes = [2, 5, 10, 20, 40, 100, 300, 100, 40, 20, 10, 5, 2]
    kept = {}
    for px in sizes:
        mpp = side / px

        def build(mpp=mpp):
            return wiring.build(view, mpp, states={}, wiring_on=True)
        made = step(rows, f'wiring {px} px ({plan_wiring.level_of(px)})', build)
        key = (plan_wiring.level_of(px), round(math.log(mpp) / math.log(1.5)))
        if key not in kept:
            try:
                kept[key] = len(pickle.dumps({k: v for k, v in made.items() if k != 'objects'}, protocol=5))
            except (TypeError, pickle.PicklingError):
                kept[key] = None
    out['wiring_scene_pickle_mib'] = {f'{k[0]} {k[1]}': mib(v) for k, v in kept.items()}
    out['wiring_builds'] = wiring.builds

    for i in range(args.repeat):
        triangles, table, segments = step(rows, f'project_scene {i + 1}', lambda: mesh.project_scene(project, results))
    out['scene3d_mib'] = {'triangles': mib(sum(a.nbytes for a in triangles)), 'module_table': mib(table.nbytes),
                          'segments': mib(segments.nbytes), 'triangle_count': int(len(triangles[0]) // 3)}
    out['peak_mib'] = mib(procmem.peak())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding='utf-8')
    print({k: v for k, v in out.items() if k != 'rows'})


if __name__ == '__main__':
    main()
