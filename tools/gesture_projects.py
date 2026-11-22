"""Wholly invented, seeded PV scenes and the preparation of the open IFC corpus."""
import argparse
import math
from pathlib import Path
import random
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


def rectangle(x, y, w, h):
    return [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]


def generate(modules=100, seed=1, campus=False):
    from meridiana.core.model import model
    rng = random.Random(seed)
    count = 6 if campus else max(1, math.ceil(modules/500))
    project = model.Project(name='Synthetic data campus' if campus else 'Synthetic PV scene',
                            bim_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f'meridiana:synthetic:{seed}:{modules}:{campus}')),
                            created='2026-01-01T00:00:00', modified='2026-01-01T00:00:00')
    project.site = model.Site(lat=45.5226, lon=9.03, address='Synthetic plain, recorded weather test coordinates')
    project.variants[0]['note'] = f'Wholly synthetic geometry, seed {seed}. No client data. CC0-1.0.'
    remaining = modules
    for index in range(count):
        per = math.ceil(remaining/(count-index))
        side = max(32, math.ceil(math.sqrt(per*9))+12)
        x, y = index % 3*(side+40), index//3*(side+50)
        building = model.Building(id=f'b{index+1}', name=f'Data hall {chr(65+index)}' if campus else f'Building {index+1}',
                                  footprint=rectangle(x, y, side, side), height=rng.uniform(10, 18), parapet=.8)
        project.buildings.append(building)
        if campus:
            building.fire = model.Fire(subject=True)
            project.fire_bands(building.id, width=1.0)
        for j in range(8 if campus else 2):
            ox, oy = x+rng.uniform(5, side-8), y+rng.uniform(5, side-8)
            project.exclusions.append(model.ExclusionItem(id=project.new_id('e'), building=building.id,
                ring=rectangle(ox, oy, 2, 2), kind=('plant', 'skylight', 'chimney', 'vent')[j % 4], height=1+j*.3))
        # Divide large roofs into independent filled strips, with access aisles between them.
        strips = 4 if campus else 1
        for j in range(strips):
            target = math.ceil(per/(strips-j))
            sf = model.SubField(id=project.new_id('s'), name=f'Roof {index+1}.{j+1}', building=building.id,
                ring=rectangle(x+2+j*(side-4)/strips, y+2, (side-4)/strips-1.2, side-4), filled=True,
                params={'tilt': 10., 'shade_free': False})
            project.subfields.append(sf)
            result = project.fill(sf)
            if len(result.modules) < target:
                raise RuntimeError(f'generator roof capacity {len(result.modules)} below {target}')
            sf.removed = [m.key for m in result.modules[target:]]
            per -= target
            remaining -= target
    if campus:
        for i, name in enumerate(('Office', 'Power plant', 'Generator hall', 'Parking canopy A', 'Parking canopy B')):
            project.buildings.append(model.Building(id=project.new_id('b'), name=name,
                footprint=rectangle(i*60, -50, 48, 20), height=5 if i > 2 else 9, parapet=.5))
    return project


def wire(project):
    """The application's automatic sizing/stringing, on a public synthetic inverter record."""
    from meridiana.app import jobs
    from meridiana.core.energy import plant, sizing, stringing
    results, _, _ = jobs.layout_of(project)
    errors = {key: str(value) for key, value in results.items() if isinstance(value, Exception)}
    if errors:
        raise RuntimeError(f'layout errors: {errors}')
    if not any(getattr(r, 'modules', []) for r in results.values()):
        raise RuntimeError(f'empty layouts: buildings={len(project.buildings)}, subfields={len(project.subfields)}, '
                           f'exclusions={len(project.exclusions)}, '
                           f'roofs={[(b.roof.type, len(b.pitches())) for b in project.buildings]}, '
                           f'capacity={[(s.id, len(results.get(s.id).modules)) for s in project.subfields if s.id in results]}')
    # A neutral test datasheet, with explicit numeric limits; no manufacturer data or network.
    record = dict(manufacturer='Synthetic', model='SYN-100K', ac_power_nominal_w=100000, efficiency_euro_pct=98.,
                  dc_voltage_max_v=1100, mppt_voltage_min_v=200, mppt_voltage_max_v=1000, mppt_count=10,
                  dc_current_max_per_mppt_a=[26]*10, dc_isc_max_per_mppt_a=[40]*10)
    entries, runs = [], []
    # Independent roofs keep the search bounded even for a 15000-module campus.
    for group in plant.groups_of(project, results):
        candidate = dict(record)
        if len(group.placed) < 20:
            candidate.update(model='SYN-small', ac_power_nominal_w=max(400, len(group.placed)*400),
                             mppt_voltage_min_v=20, mppt_count=1, dc_current_max_per_mppt_a=[26], dc_isc_max_per_mppt_a=[40])
        result = sizing.choose(project, [group], [candidate], 1.2,
                               search=stringing.SearchBudget(deadline=time.monotonic()+10))
        if not result.ok:
            raise RuntimeError('automatic sizing failed: '+result.reason)
        offset = sum(e['count'] for e in entries)
        entries.extend(result.entries)
        runs.extend(dict(run, inverter=run['inverter']+offset) for run in result.runs)
    project.energy['inverters'] = entries
    project.energy['strings'] = dict(auto=False, runs=runs)
    return dict(modules=sum(len(r.modules) for r in results.values()), inverters=sum(e['count'] for e in entries),
                strings=len(runs))


def prepare_open(args):
    """Use the same dialog command, process reader, placement choice and accept path as a user."""
    import json
    import tempfile
    import time
    from types import SimpleNamespace
    from gesture_bench import sha256, write_new
    from gesture_bench_qt import initialize
    from open_ifc import MODELS
    init = SimpleNamespace(source_root=ROOT, live=False, platform='offscreen', backend='software', api='d3d11', scale=None)
    _, setup, app, _ = initialize(init)
    from meridiana.core.model import model
    from meridiana.gui.application import QuickWindow
    from meridiana.gui.sample import recorded_weather
    reports = []
    for item in MODELS:
        if args.key and args.key != item['key']:
            continue
        source = args.open_root/item['key']/item['filename']
        output = source.with_name(source.stem+args.revision+'.meridiana')
        if output.exists():
            raise FileExistsError(output)
        before = sha256(source)
        with tempfile.TemporaryDirectory(prefix='meridiana-open-ifc-') as folder:
            project = model.Project(name=item['key'])
            project.site = model.Site(lat=45.5226, lon=9.03, address='Recorded weather test coordinates, not the IFC location')
            project.variants[0]['note'] = item['attribution']+' PV layout added with Meridiana, recorded weather at test coordinates.'
            from meridiana.app.platform import config
            config.save(config.Config(network_tiles=False, network_pvgis=False),
                        Path(folder)/'quick-profile/config/config.json')
            host = QuickWindow(project, Path(folder), real_views=True)
            try:
                host.plan.configureMaps({'offline': True})
                host.bridge.configure_background(enabled=False)
                dialog = host.parts.controllers['dialogs']
                host.shell.trigger('import_ifc')
                started = time.perf_counter()
                dialog.readFile(str(source))
                if not setup.wait_until(app, lambda dialog=dialog: not dialog.busy and (dialog.state.get('ifcRead') or dialog.state.get('error')), args.timeout):
                    raise TimeoutError('IFC reader exceeded budget')
                read_s = time.perf_counter()-started
                dialog.setValue('how', 'origin')
                if not setup.wait_until(app, lambda dialog=dialog: not dialog.busy, args.timeout) or not dialog.state.get('valid'):
                    raise RuntimeError(str(dialog.status))
                listing = (dialog._ifc_found or {}).get('listing', {})
                if not dialog.accept():
                    raise RuntimeError('import accept failed')
                if not setup.wait_until(app, lambda project=project: len(project.buildings) > 0, 30):
                    raise RuntimeError('import did not add buildings')
                host.bridge.session.edit('Prepare benchmark PV roofs', populate_roofs)
                import copy
                wired = copy.deepcopy(project)
                counts = wire(wired)
                host.bridge.session.edit('Automatically size and string benchmark PV', lambda p, wired=wired: setattr(p, 'energy', wired.energy))
                recorded_weather(project, Path(folder), ROOT/'tests/calcoli/riferimenti/pvgis53-tmy-rho.json.gz')
                host.bridge.recompute()
                if not setup.wait_until(app, lambda host=host: not host.bridge.busy and bool(host.bridge.session.energy.get('sim')), 900):
                    raise TimeoutError('recorded energy year did not finish: '+str(host.bridge.error))
                preserve_mesh(project, output)
                project.save(output, Path(folder))
                reports.append(dict(key=item['key'], read_s=read_s, total_s=time.perf_counter()-started,
                                    listing=listing, project_sha256=sha256(output), **counts))
            except Exception as error:
                reports.append(dict(key=item['key'], total_s=time.perf_counter()-started, error=str(error)))
                snapshot = args.out.with_name(args.out.stem+'-'+item['key']+'-partial.meridiana')
                if not snapshot.exists():
                    project.save(snapshot, Path(folder))
            finally:
                host.close()
                app.processEvents()
        if before != sha256(source):
            raise AssertionError('IFC source changed')
        print(json.dumps(reports[-1]), flush=True)
    write_new(args.out, json.dumps(reports, indent=2))


def populate_roofs(project):
    from shapely.geometry import Polygon
    from meridiana.core.model import model
    for building in project.buildings:
        for i, pitch in enumerate(building.pitches()):
            if pitch.tilt > 50:
                continue
            shape = Polygon(pitch.ring).buffer(-.4)
            shapes = list(shape.geoms) if shape.geom_type == 'MultiPolygon' else [shape]
            for polygon in shapes:
                if polygon.is_empty or polygon.area < 6:
                    continue
                sf = model.SubField(id=project.new_id('s'), name=f'PV roof {len(project.subfields)+1}',
                    building=building.id, pitch=i, ring=[list(pt) for pt in list(polygon.exterior.coords)[:-1]],
                    filled=True, params={'mounting': 'coplanar', 'tilt': 0., 'edge': .1, 'shade_free': False})
                result = project.fill(sf)
                if result.modules:
                    project.subfields.append(sf)


def preserve_mesh(project, output):
    """Keep the imported context beside the benchmark project, outside the temporary profile."""
    import shutil
    reference = project.resources.get('ifc_reference') or {}
    context = reference.get('context') or {}
    if context.get('mesh'):
        source = Path(context['mesh'])
        target = output.with_suffix('.mesh.npz')
        if target.exists():
            raise FileExistsError(target)
        shutil.copyfile(source, target)
        context['mesh'] = str(target.resolve())


def viewer_project(found):
    """A neutral anchor lets the existing viewer show a raw mesh even when no editable roofs were found."""
    from meridiana.app.exchange import ifc_import
    from meridiana.core.model.model import Building, Project
    project = Project(name='Synthetic IFC raw geometry')
    anchor = Building(id='b1', name='Viewer anchor, not an imported roof', footprint=rectangle(0, 0, 1, 1), height=.1)
    project.buildings.append(anchor)
    place = ifc_import.place_of(found)
    frame = ifc_import.Frame(found, place, 'origin', project.site)
    reference = ifc_import.reference(found, place, frame, 'origin', 'Synthetic IFC CC0-1.0')
    reference.update(buildings={anchor.id: 0.}, anchor=dict(building=anchor.id, footprint=anchor.footprint))
    project.resources['ifc_reference'] = reference
    project.variants[0]['note'] = 'CC0-1.0 synthetic geometry. Viewer anchor only; no editable roofs imported.'
    return project


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--modules', type=int, default=100)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--campus', action='store_true')
    p.add_argument('--open-root', type=Path)
    p.add_argument('--key', choices=('tuwien-zdb-reale', 'tuwien-zdb-prova'))
    p.add_argument('--revision', default='', help='New project suffix, for example _R01; never overwrite an existing project')
    p.add_argument('--timeout', type=float, default=300)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    if args.open_root:
        prepare_open(args)
    else:
        import tempfile
        sys.path.insert(0, str(ROOT/'tests'))
        import _setup
        from gesture_bench import isolate_profile
        isolate_profile(_setup)
        project = generate(args.modules, args.seed, args.campus)
        print(wire(project))
        with tempfile.TemporaryDirectory() as folder:
            project.save(args.out, Path(folder))
