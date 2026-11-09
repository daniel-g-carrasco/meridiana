"""Guard of the symbols (R518, Daniel 07/11/2026: «tutti i simboli vanno centralizzati»): no Unicode character used as
an icon inside a text of the QML (a star, an arrow, a check, a box): a symbol is an M.Icon, drawn by the icon provider
(quick/backend/controls.py, ui/icons.py, ui/symbols.py), with its name, size and colour from the theme. Those glyphs
are not in the program's font: where Qt finds no other font with them they come out as an empty box (the stars of
«Dimensiona l'inverter da solo», the arrow of the map sources' combo, offscreen captures of 07/11).

The ones still there are listed in KNOWN with docs/quick/stato/r20-finestre.md, for the general reordering after the
merge: the test fails on any new one, and on a known one that is gone (remove it from KNOWN).

    python -m unittest quick.sistema.test_simboli
    python tests/quick/sistema/test_simboli.py          (prints the census)
"""
import re
import sys
import unittest
from pathlib import Path

QML = Path(__file__).resolve().parents[3] / 'src' / 'meridiana' / 'quick' / 'qml' / 'Meridiana'
# «•» is not in it: the bullet of a list is typography, text like the «–» of a missing value (regola 4, R21-F3)
ICON_CHARS = set('★☆⌄▾▸▴▿▯✓✔✕✖×⋯⋮⌃⏷⏵➜←→↑↓›‹●○◆◇■□▲▼▶◀⚠ⓘ−')
STRING = re.compile(r'"([^"]*)"')

# file: characters still used there as icons (07/11/2026, r20-finestre); to be converted to M.Icon
KNOWN = {}                                  # emptied by R21-F3 (07/11/2026): every symbol is an M.Icon


def census():
    found = {}
    for path in sorted(QML.rglob('*.qml')):
        rel = path.relative_to(QML).as_posix()
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('//')[0] if not line.lstrip().startswith('//') else ''
            for match in STRING.finditer(code):
                text = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), match.group(1))
                hit = ICON_CHARS & set(text)
                if hit:
                    found.setdefault(rel, []).append((number, ''.join(sorted(hit)), match.group(1)[:50]))
    return found


class Symbols(unittest.TestCase):
    def test_no_new_unicode_icon_in_a_text(self):
        found = census()
        new = {f: [(n, c) for n, c, _t in rows if not set(c) <= set(KNOWN.get(f, ''))] for f, rows in found.items()}
        self.assertEqual({f: v for f, v in new.items() if v}, {}, 'an icon written as a character: use M.Icon')

    def test_the_known_ones_are_still_there(self):
        found = census()
        gone = {f: c for f, c in KNOWN.items() if not set(c) <= {x for _n, cs, _t in found.get(f, []) for x in cs}}
        self.assertEqual(gone, {}, 'converted: take them out of KNOWN')


    def test_one_help_mark(self):
        """R21-F3 (Daniel 07/11/2026): one «?» in the program, Controls/HelpMark (the round circle-question-mark): no
        other button with a «?» for text, no other circle-question-mark drawn outside it."""
        found = []
        for path in sorted(QML.rglob('*.qml')):
            rel = path.relative_to(QML).as_posix()
            if rel == 'Controls/HelpMark.qml':
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                code = line.split('//')[0]
                # the commands «Aiuto» are not marks: the status bar's button (a bar's icon among the others) and the
                # File page's entry, with the same icon as their command
                if 'statusHelp' in code or 'help:"circle-question-mark"' in code:
                    continue
                if re.search(r'text:\s*"\?"', code) or 'circle-question-mark' in code:
                    found.append(f'{rel}:{number}')
        self.assertEqual(found, [], 'a help mark of its own: use M.HelpMark')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'census':
        for f, rows in census().items():
            for n, c, t in rows:
                print(f'{f}:{n} | {c} | {t}')
    else:
        unittest.main()
