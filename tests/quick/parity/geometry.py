"""Named Quick items against explicit Widgets IDs, in logical window pixels."""
import base64
import html
import json
import math
import re
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRectF
from PySide6.QtGui import QColor, QFont, QFontInfo, QImage


def capture_quick(window, *, scenario='', meta=None):
    """Read the visual tree, including delegates not in the QObject tree.

    Only objectName is a contract. Unnamed QML implementation details are not
    assigned positional identities that would silently match the wrong object.
    Padding means content margins for Controls; plain items have no content inset.
    Anchor margins are separate: they position the item, not its contents.
    """
    rows = []
    pending = [window.contentItem()]
    while pending:
        obj = pending.pop()
        pending.extend(reversed(obj.childItems()))
        if not obj.objectName() or not obj.isVisible():
            continue
        rect = obj.mapRectToScene(QRectF(0, 0, obj.width(), obj.height()))
        row = {'id': obj.objectName(), 'name': obj.objectName(),
               'class': obj.metaObject().className(),
               'rect': [rect.x(), rect.y(), rect.width(), rect.height()],
               'margins': [float(obj.property(key) or 0) for key in
                           ('leftPadding', 'topPadding', 'rightPadding', 'bottomPadding')]}
        font = obj.property('font')
        if isinstance(font, QFont):
            info = QFontInfo(font)
            row['font'] = {'family': info.family(), 'point_size': info.pointSizeF(),
                           'pixel_size': info.pixelSize(), 'weight': int(font.weight()), 'italic': font.italic()}
        colors = {}
        for key in ('color', 'backgroundColor'):
            color = obj.property(key)
            if isinstance(color, QColor):
                colors['text' if key == 'color' and obj.property('text') is not None else key] = color.name(QColor.NameFormat.HexArgb)
        # Controls paint through their visual delegates, not palette role objects.
        for property_name, role in (('contentItem', 'text'), ('background', 'background')):
            delegate = obj.property(property_name)
            if delegate is not None and hasattr(delegate, 'property'):
                color = delegate.property('color')
                if isinstance(color, QColor):
                    colors[role] = color.name(QColor.NameFormat.HexArgb)
        row['colors'] = colors
        text = obj.property('text')
        if text is not None:
            row['text'] = str(text)
        rows.append(row)
    return {'schema': 1, 'meta': dict(meta or {}, scenario=scenario, dpr=window.devicePixelRatio()), 'widgets': rows}


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_row(row):
    """Reject incomplete evidence before equality or intentional waivers are tried."""
    identity = row['id']
    for field in ('rect', 'margins'):
        values = row.get(field)
        if (not isinstance(values, (list, tuple)) or len(values) != 4 or
                not all(_finite_number(value) for value in values)):
            raise ValueError(f'Invalid or missing {field} for {identity}: expected four finite numbers')
    if row['rect'][2] < 0 or row['rect'][3] < 0:
        raise ValueError(f'Invalid rect for {identity}: negative dimensions')
    colors = row.get('colors')
    if not isinstance(colors, dict) or any(
            not isinstance(role, str) or not role or not isinstance(color, str) or
            not re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?', color)
            for role, color in colors.items()):
        raise ValueError(f'Invalid or missing colors for {identity}: expected named hexadecimal colors')
    if 'font' not in row:
        if 'text' in row:
            raise ValueError(f'Missing font for text-bearing item {identity}')
        return
    font = row['font']
    if not isinstance(font, dict):
        raise ValueError(f'Invalid font for {identity}: expected resolved font metrics')
    if (not isinstance(font.get('family'), str) or not font['family'].strip() or
            not isinstance(font.get('italic'), bool) or
            any(not _finite_number(font.get(key)) or font[key] <= 0
                for key in ('point_size', 'pixel_size', 'weight'))):
        raise ValueError(f'Invalid or incomplete font for {identity}: expected resolved finite metrics')


def _index(snapshot, identities):
    if snapshot.get('schema') != 1:
        raise ValueError('Unsupported snapshot schema')
    result = {}
    for row in snapshot['widgets']:
        identity = row['id']
        if identity not in identities:
            continue
        if identity in result:
            raise ValueError('Duplicate snapshot ID: ' + identity)
        _validate_row(row)
        result[identity] = row
    return result


def _rules(differences):
    for rule in differences:
        required = ('scenario', 'reference', 'quick', 'field', 'reason', 'request')
        if any(not isinstance(rule.get(k), str) or not rule[k].strip() for k in required):
            raise ValueError('Every intentional difference needs an exact scope, reason and request')
        if not re.fullmatch(r'R[1-9][0-9]*', rule['request']):
            raise ValueError('Intentional difference must cite a request R number')
        if '*' in ''.join(rule[k] for k in ('scenario', 'reference', 'quick', 'field')):
            raise ValueError('Wildcards cannot waive visual differences')
        if 'before' not in rule or 'after' not in rule:
            raise ValueError('Intentional difference must pin both values')
    return differences


def compare_snapshots(reference, actual, mapping, differences=(), *, tolerance=1.0):
    """Return unapproved differences. Mapping chooses the explicit contract scope.

    A mapping value can be an objectName or a dictionary with ``id`` and a
    ``colors`` role map (Widgets palette role -> captured QML color property).
    No nearest-neighbour matching, implicit exclusions or missing-field passes.
    """
    if not mapping:
        raise ValueError('An explicit nonempty mapping is required')
    if not 0 <= tolerance <= 1:
        raise ValueError('Logical tolerance must not exceed 1 px')
    targets = {spec if isinstance(spec, str) else spec['id'] for spec in mapping.values()}
    before, after = _index(reference, set(mapping)), _index(actual, targets)
    rules = _rules(differences)
    failures = []
    reference_meta, actual_meta = reference.get('meta', {}), actual.get('meta', {})
    scenario = reference_meta.get('scenario', reference_meta.get('state', ''))
    if actual_meta.get('scenario', actual_meta.get('state', '')) != scenario:
        raise ValueError('Snapshot scenarios do not match')
    for source, spec in mapping.items():
        target = spec if isinstance(spec, str) else spec['id']
        a, b = before.get(source), after.get(target)
        for field in ('missing',) if a is None or b is None else ('rect', 'margins', 'font', 'colors', 'text'):
            left, right = (a is not None, b is not None) if field == 'missing' else (a.get(field), b.get(field))
            if field == 'colors' and isinstance(spec, dict) and 'colors' in spec:
                if not spec['colors'] or any(k not in (left or {}) or v not in (right or {})
                                             for k, v in spec['colors'].items()):
                    raise ValueError('Mapped color role missing from snapshot: ' + source + ' -> ' + target)
                left = {k: left.get(k) for k in spec['colors']} if left is not None else None
                right = {k: right.get(v) for k, v in spec['colors'].items()} if right is not None else None
            equal = field != 'missing' and left == right
            if field in ('rect', 'margins') and left is not None and right is not None:
                equal = len(left) == len(right) == 4 and all(
                    math.isfinite(x) and math.isfinite(y) and abs(x-y) <= tolerance for x, y in zip(left, right, strict=True))
            if equal:
                continue
            issue = {'scenario': scenario, 'reference': source, 'quick': target,
                     'field': field, 'before': left, 'after': right}
            if not any(all(rule[k] == v for k, v in issue.items()) for rule in rules):
                failures.append(issue)
    return failures


def _data_url(image):
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, 'PNG'):
        raise ValueError('Could not encode comparison image')
    return 'data:image/png;base64,' + base64.b64encode(bytes(buffer.data())).decode('ascii')


def write_comparison(reference, actual, output, *, title, differences, metadata=None):
    """Self-contained HTML with unscaled sources and absolute RGB pixel delta.

    Device images must have identical dimensions and DPR. This is intentionally
    strict: rescaling a reference to make it fit hides missing pixels.
    """
    import numpy as np
    if reference.isNull() or actual.isNull():
        raise ValueError('Cannot compare a null screenshot')
    if reference.size() != actual.size() or reference.devicePixelRatio() != actual.devicePixelRatio():
        raise ValueError('Screenshots need the same device size and DPR')
    images = [im.convertToFormat(QImage.Format.Format_RGBA8888) for im in (reference, actual)]
    arrays = [np.frombuffer(im.constBits(), dtype=np.uint8).reshape(im.height(), im.width(), 4) for im in images]
    delta = np.abs(arrays[0][:, :, :3].astype(np.int16) - arrays[1][:, :, :3]).astype(np.uint8)
    pixels = np.any(delta != 0, axis=2)
    rgba = np.dstack((delta, np.full(pixels.shape, 255, dtype=np.uint8)))
    diff = QImage(rgba.data, reference.width(), reference.height(), rgba.strides[0], QImage.Format.Format_RGBA8888).copy()
    result = {'changed_pixels': int(pixels.sum()), 'total_pixels': int(pixels.size),
              'dpr': reference.devicePixelRatio(), 'device_size': [reference.width(), reference.height()]}
    pictures = ''.join('<figure><figcaption>' + label + '</figcaption><img alt="' + label +
                       '" src="' + _data_url(im) + '"></figure>' for label, im in
                       [('Widgets', reference), ('Quick', actual), ('Differenza pixel', diff)])
    details = html.escape(json.dumps({'pixels': result, 'geometry': differences, 'metadata': metadata or {}},
                                    ensure_ascii=False, indent=2))
    document = ('<!doctype html><html lang="it"><meta charset="utf-8"><title>' + html.escape(title) +
                '</title><style>body{font:15px system-ui;margin:24px;background:#f2f2f2;color:#222}'
                '.images{display:flex;gap:16px;overflow:auto}figure{margin:0;min-width:46vw}'
                'img{width:100%;height:auto}figcaption{font-weight:bold;padding:8px}pre{white-space:pre-wrap}'
                '</style><h1>' + html.escape(title) + '</h1><p>Immagini originali incorporate; '
                'differenza RGB assoluta, senza ricampionamento. Nero: pixel identici. '
                'Le differenze geometriche approvate non alterano questa immagine.</p><div class="images">' +
                pictures + '</div><h2>Misure e differenze non approvate</h2><pre>' + details + '</pre></html>')
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(document)
    return result
