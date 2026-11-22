"""The strings' dots as the plan draws them since R706: one layer of the drawing (`dotsBatch`), not an item each."""
import re


def dots_layer(plan, name=None):
    """The layer of the dots on show, found among the plan's items: a dot on each module (`dotsBatch`) or, between
    the scale of the strings and that of the modules, each string's first (`headsBatch`, R707); `name`: that one."""
    found, pending = {}, [plan]
    while pending:
        item = pending.pop()
        if item.objectName() in ('dotsBatch', 'headsBatch'):
            found[item.objectName()] = item
        pending.extend(item.childItems())
    if 'dotsBatch' not in found:
        raise AssertionError('the plan has no layer of the dots')
    if name:
        return found[name]
    heads = found.get('headsBatch')
    return heads if heads is not None and heads.property('shown') and not found['dotsBatch'].property('shown') else found['dotsBatch']


def drawn_dots(plan):
    """Where each dot is drawn, in the scene's metres (East, minus North): every stroke of the layer's paths, put
    back from the corner its path is written from."""
    out = []
    layer = dots_layer(plan)
    if not layer.isVisible() or not layer.property('shown'):    # kept at every scale (R706), shown by level (R707)
        return out
    for path in layer.property('paths'):
        for x, y in re.findall(r'M(-?[\d.e+-]+),(-?[\d.e+-]+)', path['path']):
            out.append((path.get('x', 0.) + float(x), path.get('y', 0.) + float(y)))
    return out


def assert_dots_follow(case, plan, records):
    """One dot drawn for each record of the backend, where the record says, as wide as the theme's point."""
    drawn = sorted(drawn_dots(plan))
    wanted = sorted((float(r['x']), -float(r['y'])) for r in records)
    case.assertEqual(len(drawn), len(wanted))
    for (x, y), (wx, wy) in zip(drawn, wanted, strict=True):
        # written with six figures from the corner of a square of 64 m: a tenth of a millimetre
        case.assertAlmostEqual(x, wx, delta=2e-4)
        case.assertAlmostEqual(y, wy, delta=2e-4)
    case.assertEqual(dots_layer(plan).property('pen'), 4.5)
