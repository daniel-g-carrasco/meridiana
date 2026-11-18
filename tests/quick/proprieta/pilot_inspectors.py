"""Extend the shared pilot with tree items and text, using only local Qt events."""
import importlib.util
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItemIterator

spec = importlib.util.spec_from_file_location('shared_pilot', Path(__file__).resolve().parents[3] / 'tools/quick_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
original_find, original_perform = pilot.find_target, pilot.perform


def find_target(window, text, engine):
    if text.startswith('value:'):
        return original_find(window, text[6:] if engine == 'widgets' else 'editor:name', engine)
    if text.startswith('tree:'):
        label = text[5:]
        if engine == 'widgets':
            for tree in window.findChildren(QTreeWidget):
                if not tree.isVisible():
                    continue
                iterator = QTreeWidgetItemIterator(tree)
                while iterator.value():
                    item = iterator.value()
                    if any(pilot.normal(item.text(column)) == label for column in range(tree.columnCount())):
                        tree.scrollToItem(item)
                        return tree.viewport(), QPointF(tree.visualItemRect(item).center())
                    iterator += 1
        else:
            pending = [window.contentItem()]
            while pending:
                item = pending.pop()
                pending.extend(item.childItems())
                if item.objectName().startswith('tree-row-') and item.isVisible():
                    data = item.property('modelData')
                    if hasattr(data, 'toVariant'):
                        data = data.toVariant()
                    if data['label'] == label:
                        return window, item.mapToScene(QPointF(item.width()/2, item.height()/2))
        raise AssertionError('Missing tree row: ' + label)
    return original_find(window, text, engine)


def perform(app, window, engine, step, last):
    if not getattr(window, '_inspectors_pilot_prepared', False):
        if engine == 'quick':
            from PySide6.QtQml import qmlContext
            tokens = qmlContext(window).contextProperty('themeTokens')
            tokens.configure(dict(accent='indigo', backgrounds='grey', font='plex'))
        # Initial layout/check jobs must finish before comparing the first state.
        pilot.pump(2000)
        window._inspectors_pilot_prepared = True
    if engine == 'widgets' and step['action'] == 'click':
        target, _ = find_target(window, step['target'], engine)
        # sendEvent bypasses the platform's pointer-to-focus dispatch.
        target.setFocus(Qt.FocusReason.MouseFocusReason)
    if step['action'] == 'type':
        target = (app.focusWidget() or window) if engine == 'widgets' else window
        for character in step['text']:
            if engine == 'widgets':
                QTest.keyClicks(target, character)
            else:
                QTest.keyClick(target, character)
    else:
        last = original_perform(app, window, engine, step, last)
    if engine == 'quick':
        # The isolated desktop can defer rendering until readback. Compare
        # settled states; the separate R377 recorder tests every transition frame.
        for _ in range(15):
            pilot.pump(40)
            window.grabWindow()
    return last


pilot.find_target, pilot.perform = find_target, perform

if __name__ == '__main__':
    # The shared main launches __file__ for both children. Point it at this
    # adapter so the same tree/text actions are available in either process.
    pilot.__file__ = __file__
    pilot.main()
