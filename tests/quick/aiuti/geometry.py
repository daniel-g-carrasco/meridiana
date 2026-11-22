"""The named items of a Quick window, read from its visual tree, in logical window pixels."""
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QFontInfo


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
