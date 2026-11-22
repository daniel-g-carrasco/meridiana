"""Grab an item on offscreen RHI, where grabWindow can return a black buffer."""
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickWindow  # noqa: F401  register the window wrapper before creating a QML root

from _setup import wait_until


def grab_item(item):
    result = item.grabToImage()
    ready = []
    result.ready.connect(lambda: ready.append(True))
    if not wait_until(QGuiApplication.instance(), lambda: bool(ready)):
        raise AssertionError('The item capture did not finish')
    image = result.image()
    if image.isNull():
        raise AssertionError('The item capture is empty')
    # the ratio of the screens, not item.window(): on Linux the window's wrapper it makes outlives the window its
    # engine deletes, and the cyclic collector took the process down on it (a segmentation fault in a later test)
    image.setDevicePixelRatio(QGuiApplication.instance().devicePixelRatio())
    return image
