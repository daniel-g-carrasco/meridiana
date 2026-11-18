"""Markdown tables of the modelling journeys: one row per step, the two programs side by side.

    python tests/quick/percorsi/modellazione_tabella.py <folder> <journey> [<journey> ...]
Legend of a cell: buildings/pitches, sub-fields, exclusions, modules, kWp, strings/modules in strings, checks,
tool, year in kWh when computed. A row is «=» when the cells are equal.
"""
import json
from pathlib import Path
import sys


def cell(state):
    checks = state.get('checks') or {}
    tally = ' '.join(f'{k[0].upper()}{v}' for k, v in sorted(checks.items()))
    energy = state.get('energy_kwh') or {}
    year = energy.get('kwh') if isinstance(energy, dict) else None
    return (f"{len(state['buildings'])}/{sum(len(b['pitches']) for b in state['buildings'])} ed/fa, "
            f"{len(state['subfields'])} sc, {len(state['exclusions'])} es, {state['modules']} mod, {state['kwp']} kWp, "
            f"{state['strings']['runs']}/{state['strings']['modules']} str, {tally}, {state['tool']}"
            + (f', {year} kWh' if year else ''))


def table(folder, journey):
    load = lambda e: json.loads((Path(folder)/f'{journey}-{e}.json').read_text(encoding='utf8'))
    quick, widgets = load('quick'), load('widgets')
    by_label = {s['label']: s for s in widgets}
    rows = ['| Passo | Quick | Widgets |', '|---|---|---|']
    used = set()
    for state in quick:
        other = by_label.get(state['label'])
        used.add(state['label'])
        q = cell(state)
        w = '(passo non raggiunto)' if other is None else cell(other)
        rows.append(f"| {state['label']} | {q} | {'=' if q == w else w} |")
    for state in widgets:
        if state['label'] not in used:
            rows.append(f"| {state['label']} | (passo non raggiunto) | {cell(state)} |")
    return '\n'.join(rows)


if __name__ == '__main__':
    for name in sys.argv[2:]:
        print(f'\n### {name}\n\n{table(sys.argv[1], name)}')
