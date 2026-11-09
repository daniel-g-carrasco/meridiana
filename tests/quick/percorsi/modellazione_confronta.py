"""Read the two JSON files of a modelling journey and print what differs, step by step.

    python tests/quick/percorsi/modellazione_confronta.py <folder> <journey> [--all]
A difference already printed at an earlier step is not repeated; --all writes every step.
"""
import json
from pathlib import Path
import sys


def brief(state):
    return (f"edif {len(state['buildings'])} falde {sum(len(b['pitches']) for b in state['buildings'])} "
            f"sc {len(state['subfields'])} escl {len(state['exclusions'])} mod {state['modules']} "
            f"kWp {state['kwp']} str {state['strings']['runs']}/{state['strings']['modules']} "
            f"chk {state.get('checks', state.get('checks_error'))} tool {state['tool']} kWh {state.get('energy_kwh')}")


def drift(a, b, path=''):
    """Numbers differ only if by more than a snap of the pointer, 0.5 m on the plan."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            out += drift(a.get(key), b.get(key), f'{path}.{key}')
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f'{path}: {len(a)} contro {len(b)} elementi']
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += drift(x, y, f'{path}[{i}]')
        return out
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        limit = .5 if ('footprint' in path or 'ring' in path) else 1e-6
        return [] if abs(a-b) <= limit else [f'{path}: {a} contro {b}']
    return [] if a == b else [f'{path}: {str(a)[:120]} contro {str(b)[:120]}']


def compare(folder, journey):
    quick = json.loads((Path(folder)/f'{journey}-quick.json').read_text(encoding='utf8'))
    widgets = json.loads((Path(folder)/f'{journey}-widgets.json').read_text(encoding='utf8'))
    rows = []
    for n in range(max(len(quick), len(widgets))):
        q = quick[n] if n < len(quick) else None
        w = widgets[n] if n < len(widgets) else None
        label = (q or w)['label']
        if q is None or w is None:
            rows.append((label, 'manca in ' + ('Quick' if q is None else 'Widgets'), []))
            continue
        ignore = {'label', 'note', 'undo', 'settled', 'checks_text'}
        differences = drift({k: v for k, v in q.items() if k not in ignore}, {k: v for k, v in w.items() if k not in ignore})
        rows.append((label, brief(q)+' || '+brief(w) if differences else brief(q), differences))
    return rows


if __name__ == '__main__':
    seen = set()
    every = '--all' in sys.argv
    for label, text, differences in compare(sys.argv[1], sys.argv[2]):
        new = [d for d in differences if every or d not in seen]
        seen.update(differences)
        if every or new or not differences:
            print(f'[{label}] {"UGUALE" if not differences else "DIVERSO"} {text if every else text[:190]}')
        for d in new[:8]:
            print('    '+d)
