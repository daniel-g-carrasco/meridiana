"""Freeze the actual Rho pipeline output for equal Widgets/Quick photographs."""
import argparse
import pickle
import time
from pathlib import Path

from meridiana import jobs, model, i18n
from meridiana.energy.pipeline import compute
from meridiana.quick.sample import recorded_weather


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    i18n.setup('it')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    project = model.Project.load(args.project)[0]
    cache = args.output.parent / 'weather'
    assert recorded_weather(project, cache)
    results, keys, _errors = jobs.layout_of(project)
    start = time.perf_counter()
    energy = compute(project, results, cache, fetch=False,
                     progress=lambda *step: print(round(time.perf_counter()-start, 2), step, flush=True))
    assert energy.sim is not None and energy.load is not None and energy.econ is not None, energy
    with args.output.open('xb') as file:
        pickle.dump(dict(project=project, results=results, keys=keys, energy=energy.as_dict()), file)
    print('Computed actual year:', energy.basis, 'seconds:', time.perf_counter()-start, flush=True)


if __name__ == '__main__':
    main()
