"""sintetico_impianto.py (21/11/2026, R711): a wholly synthetic plant for the probes and the tests, written to a file:
four flat roofs, `--strings` strings of `--per-string` modules (2000 by default) on inverters of 10 inputs, as
tests/_fixtures.synthetic_plant makes it (the same project at every run; no client data).

    python tools/sintetico_impianto.py <out.meridiana> [--strings 80] [--per-string 25]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--strings', type=int, default=80)
    ap.add_argument('--per-string', type=int, default=25)
    args = ap.parse_args()
    from _fixtures import synthetic_plant
    project = synthetic_plant(args.strings, args.per_string)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    project.save(args.out)
    print(args.out, args.strings * args.per_string, 'modules', args.strings, 'strings')


if __name__ == '__main__':
    main()
