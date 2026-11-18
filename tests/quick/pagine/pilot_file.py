"""File journeys using the shared pilot, with scoped labels for File's categories."""
from pathlib import Path
import sys

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QWidget

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
import quick_pilot as pilot  # noqa: E402

original_find = pilot.find_target
original_perform = pilot.perform


def perform(app, window, engine, step, last):
    if step['action'] == 'key':
        from PySide6.QtGui import QKeySequence
        from PySide6.QtTest import QTest
        sequence = QKeySequence(step['key'])[0]
        target = (app.focusWidget() or window) if engine == 'widgets' else window
        QTest.keyClick(target, sequence.key(), sequence.keyboardModifiers())
        return last
    result = original_perform(app, window, engine, step, last)
    if engine == 'quick' and window.property('fileOpen'):
        from quick.pagine.test_fidelity import find_item
        from PySide6.QtTest import QTest
        import _setup
        right = find_item(window.contentItem(), 'fileRight')
        if right is not None:
            assert _setup.wait_until(app, lambda: not right.parentItem().property('changing') and right.opacity() > 0.999, seconds=10)
            QTest.qWait(40)
    return result


def find_target(window, text, engine):
    if engine == 'widgets':
        page = window.file_page
        scope = page if page.isVisible() else window
        for obj in scope.findChildren(QWidget):
            label = getattr(obj, 'text', '')
            label = label() if callable(label) else label
            if obj.isVisible() and (obj.objectName() == text or pilot.normal(label) == text):
                return obj, QPointF(obj.rect().center())
        # The phase tabs have their own drawn labels.
        from PySide6.QtWidgets import QTabBar
        for tab in window.findChildren(QTabBar):
            for index in range(tab.count()):
                if tab.isVisible() and pilot.normal(tab.tabText(index)).partition(' ')[2] == text:
                    return tab, QPointF(tab.tabRect(index).center())
        raise AssertionError(f'widgets: no visible control {text!r}')
    if window.property('fileOpen'):
        from quick.pagine.test_fidelity import find_item
        page = find_item(window.contentItem(), 'fileNavigation')
        pending = [page] if page is not None else []
        while pending:
            obj = pending.pop(0)
            pending.extend(obj.childItems())
            if obj.isVisible() and (obj.objectName() == text or pilot.normal(obj.property('text')) == text):
                return window, obj.mapToScene(QPointF(obj.width()/2, obj.height()/2))
    target, point = original_find(window, text, engine)
    if engine == 'quick' and text == 'File':
        # Meridio's first-run character currently covers the centre of File.
        # Use the uncovered right end of the same button, with real mouse events.
        from quick.pagine.test_fidelity import find_item
        button = find_item(window.contentItem(), 'fileButton')
        if button is not None:
            point = button.mapToScene(QPointF(button.width() - 5, button.height() / 2))
    return target, point


pilot.find_target = find_target
pilot.perform = perform

if __name__ == '__main__':
    # Both engines must run this adapter, including subprocesses of the pilot.
    pilot.__file__ = __file__
    pilot.main()
