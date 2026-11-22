"""Vector symbols and checks' marks for Quick; all geometry stays in symbol_shapes."""

from meridiana.app.interface import symbol_shapes
from meridiana.i18n import number


def symbol_record(name: str, dark: bool = False) -> dict:
    """A symbol for QML: its tone, its palette, its ground and its sign painted over it, white (Daniel 14/11/2026, as
    R330); the forbidden's bar is of the ground's tone, its ring filled even-odd."""
    _tone, ground, sign = symbol_shapes.SHAPES[name]
    colour = symbol_shapes.colour(name, dark)
    forbidden = name == 'forbidden'
    return dict(name=name, ground=ground, sign=sign, colour=colour,
                signColour=colour if forbidden else symbol_shapes.LIGHT_SIGN, evenOdd=forbidden, dark=dark)


WORST = ("fail", "warn", "info", "ok")          # core.rules.checks.LEVELS, the worst first


def marks_summary(scene: list[dict]) -> dict:
    """The checks' marks from far, summed up on the site's drop (R714): the worst one's symbol and the number of
    checks of every mark; {} without marks."""
    if not scene:
        return {}
    worst = min(scene, key=lambda m: WORST.index(m['level']) if m['level'] in WORST else len(WORST))
    count = sum(int(m.get('count') or 1) for m in scene)
    row = symbol_record(symbol_shapes.LEVEL.get(worst['level'], 'info'))
    row.update(level=worst['level'], count=count, countText=number(count, 0))
    return row


def symbol_catalogue(dark: bool = False) -> dict:
    return {name: symbol_record(name, dark) for name in symbol_shapes.NAMES}


def marks_scene(marks) -> list[dict]:
    """Core marks (East, North, level, count, target[, tip]) to scene metres (East, minus North); `tip` the words of
    its checks for the tooltip (R641, viewaids.mark_tip).

    A view keeps the light symbol palette in both UI themes, as the Widgets plan does (R16).
    Count text follows the active locale. The input is never changed.
    """
    out = []
    for mark in marks:
        if isinstance(mark, dict):
            x, y, level, count, target = (mark[key] for key in ('x', 'y', 'level', 'count', 'target'))
            tip = mark.get('tip', '')
        else:
            x, y, level, count, target, *rest = mark
            tip = rest[0] if rest else ''
        row = symbol_record(symbol_shapes.LEVEL.get(level, 'info'))
        row.update(x=x, y=-y, level=level, count=count, countText=number(count, 0), target=list(target), tip=tip)
        out.append(row)
    return out
