"""Ink measurements on a window grab, in logical pixels, including fractional DPRs."""
import math

import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtCore import QRectF
from shiboken6 import isValid


def items(root):
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        pending.extend(node.childItems())


def painted_items(root):
    """Retained phase/File pages at opacity zero have no painted descendants.

    Prune those branches before walking thousands of cached fields. Do not prune
    at clipping edges: a partly clipped control can be the overflow we must find.
    """
    pending = [root]
    while pending:
        node = pending.pop()
        if not isValid(node) or not node.isVisible() or node.opacity() < .99:
            continue
        yield node
        pending.extend(node.childItems())


def kind(node):
    return node.metaObject().className().split('_')[0] if isValid(node) else ''


def rect(node):
    return node.mapRectToScene(QRectF(0, 0, node.width(), node.height()))


def visible(node, window):
    """Fully in the viewport: partial rows at a scroll boundary are intentional."""
    if not isValid(node):
        return False
    box = rect(node)
    if not node.isVisible() or box.width() < 1 or box.height() < 1:
        return False
    area = window.contentItem().boundingRect()
    parent = node
    while parent:
        if parent.opacity() < .99:
            return False
        if parent.clip():
            area = area.intersected(rect(parent))
        parent = parent.parentItem()
    return area.adjusted(-.5, -.5, .5, .5).contains(box)


def pixels(image):
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    a = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine())
    return a[:, :image.width() * 4].reshape(image.height(), image.width(), 4)[:, :, :3].astype(np.int16).copy()


def drawn_ratio(image, window):
    """Qt 6.12 offscreen returns physical pixels but marks grabWindow() as DPR 1.

    At QT_SCALE_FACTOR=2.5 a 500 x 300 window is 1250 x 750 pixels with DPR metadata 1.
    Derive the ratio from the actual framebuffer, and check that both axes agree.
    """
    ratio = image.width() / window.width()
    assert abs(image.height() / window.height() - ratio) < .01
    return ratio


def ink(mask, box, dpr, first=False):
    """Bounds of the actual changed pixels; first=True takes the first painted text line."""
    x, y = max(0, math.floor(box.x() * dpr)), max(0, math.floor(box.y() * dpr))
    part = mask[y:math.ceil(box.bottom() * dpr), x:math.ceil(box.right() * dpr)]
    rows = np.flatnonzero(part.any(axis=1))
    if not len(rows):
        return None
    if first:
        gaps = np.flatnonzero(np.diff(rows) > max(2, 2 * dpr))
        if len(gaps):
            rows = rows[:gaps[0] + 1]
    return (y + (rows[0] + rows[-1]) / 2) / dpr


def description(node):
    path = []
    while node:
        if node.objectName():
            path.append(node.objectName())
        node = node.parentItem()
    return '/'.join(reversed(path))


def control_overflow(node, window):
    """Horizontal panel overflow, even if a clipping parent hides the protruding part.

    Vertical overflow in a scrollable page is intentional; fixed controls must fit both axes.
    """
    if not isValid(node) or not node.isVisible():
        return 0, node
    parent, panel, scrolling = node.parentItem(), window.contentItem(), False
    while parent:
        if parent.opacity() < .99:
            return 0, node
        scrolling |= parent.metaObject().indexOfProperty('contentY') >= 0
        if kind(parent) == 'DockPanel' or parent.objectName() == 'fileRight':
            panel = parent
            break
        parent = parent.parentItem()
    box, room = rect(node), rect(panel)
    excess = max(0, room.left()-box.left(), box.right()-room.right())
    if not scrolling:
        excess = max(excess, room.top()-box.top(), box.bottom()-room.bottom())
    return excess, panel
