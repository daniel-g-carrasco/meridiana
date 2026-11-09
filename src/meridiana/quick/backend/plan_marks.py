"""Vector symbols and checks' marks for Quick; all geometry stays in symbol_shapes."""

from ... import symbol_shapes
from ...i18n import number


def symbol_record(name: str, dark: bool = False) -> dict:
    """A symbol for QML: its tone, its palette and its track with the sign cut out (R464), ground and sign in one
    path filled even-odd; `sign` is what is painted over it, only the forbidden's bar, in the ground's tone."""
    _tone, ground, sign = symbol_shapes.SHAPES[name]
    colour = symbol_shapes.colour(name, dark)
    return dict(name=name, ground=symbol_shapes.cut(name), sign=sign if name == 'forbidden' else '', colour=colour,
                signColour=colour, evenOdd=True, dark=dark)


def symbol_catalogue(dark: bool = False) -> dict:
    return {name: symbol_record(name, dark) for name in symbol_shapes.NAMES}


def marks_scene(marks) -> list[dict]:
    """Core marks (East, North, level, count, target) to scene metres (East, minus North).

    A view keeps the light symbol palette in both UI themes, as the Widgets plan does (R16).
    Count text follows the active locale. The input is never changed.
    """
    out = []
    for mark in marks:
        if isinstance(mark, dict):
            x, y, level, count, target = (mark[key] for key in ('x', 'y', 'level', 'count', 'target'))
        else:
            x, y, level, count, target = mark
        row = symbol_record(symbol_shapes.LEVEL.get(level, 'info'))
        row.update(x=x, y=-y, level=level, count=count, countText=number(count, 0), target=list(target))
        out.append(row)
    return out
