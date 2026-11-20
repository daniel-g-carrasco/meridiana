"""The parts look for their items without walking the window's items from Python.

On r20-unita `QuickWindow(...)` failed now and then in the suite at `charts_part.bind`: `item.childItems()` handed back
a `PySide6.QtCore.QMetaObject` among the items (AttributeError: no `childItems`). PySide keeps a wrapper for every
C++ address it has handed to Python: a dynamic QMetaObject of a QML object (asked by `metaObject()` in the tests) can
outlive its object, and a new item born at the same address comes back as that wrapper. The window's 15 000 items,
each handed to Python, met such an address sometimes. The walks of `charts_part` (the inspectors' guards) and of
`plant_part` (the stale marks of «Calcola» and «Posa») are now done in QML, where no wrapper is made.

The test hands back such a wrapper among the children of every item, as PySide did, and the window must still be
built, the guards and the marks made.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QMetaObject, QObject
from PySide6.QtQuick import QQuickItem

from _fixtures import capannone
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import pump, wait_for


def setUpModule():
    _setup.keep_global_state()


class ItemsWalkedInQml(unittest.TestCase):
    def test_a_stale_wrapper_among_the_children_breaks_nothing(self):
        _setup.qt_or_skip()
        create_app()
        original = QQuickItem.childItems

        def with_stale(item):
            return list(original(item)) + [QMetaObject()]

        def visual_items(root):
            pending = [root]
            while pending:
                item = pending.pop()
                if isinstance(item, QQuickItem):
                    yield item
                    pending.extend(original(item))

        def visible_tools(host, command):
            return [i for i in visual_items(host.window.contentItem())
                    if i.objectName() == f'tool_{command}' and i.isVisible()]

        def check_stale_mark(host, command):
            wait_for(lambda: bool(visible_tools(host, command)))
            self.assertEqual(len(visible_tools(host, command)), 1, command)
            tool = visible_tools(host, command)[0]
            marks = [item for item in original(tool)
                     if isinstance(item, QQuickItem) and item.objectName() == f'stale-{command}']
            self.assertEqual(len(marks), 1, tool.objectName())

        errors = []
        hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: errors.append(f'{kind.__name__}: {value}')
        QQuickItem.childItems = with_stale
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
                host = QuickWindow(capannone(), Path(temporary), real_views=True)
                try:
                    # the stale wrapper is there for any walk from Python (on r20-unita: AttributeError at bind)
                    self.assertTrue(any(isinstance(k, QMetaObject) for k in host.window.contentItem().childItems()))
                    loaders = [i for i in visual_items(host.window.contentItem())
                               if i.objectName() == 'propertiesPartLoader']
                    self.assertTrue(loaders)
                    for loader in loaders:
                        self.assertTrue(any('InactiveInspector' in child.metaObject().className()
                                            for child in loader.children() if isinstance(child, QObject)))
                    host.window.show()
                    host.window.resize(1600, 960)
                    host.shell.trigger('phase_plant')
                    check_stale_mark(host, 'fill')
                    host.shell.trigger('phase_production')
                    check_stale_mark(host, 'compute')
                    host.shell.trigger('phase_plant')
                    check_stale_mark(host, 'fill')
                finally:
                    host.close()
                    pump(50)
        finally:
            QQuickItem.childItems = original
            sys.excepthook = hook
        self.assertEqual(errors, [])

    @unittest.skipUnless(os.name == "nt", "QuickWindow can identify dynamic QMetaObject wrappers on Windows only")
    def test_the_meta_objects_handed_to_python_go_with_the_window(self):
        # 07/11/2026: three tests of test_interfaccia_r19 met such a wrapper in the shell folder; PySide keeps a
        # QMetaObject wrapper valid after its QML object is gone, QuickWindow.close makes them invalid
        import shiboken6
        _setup.qt_or_skip()
        create_app()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
            host = QuickWindow(capannone(), Path(temporary), real_views=True)
            kept = [i.metaObject() for i in host.window.contentItem().childItems()]
            names = [m.className() for m in kept]
            self.assertTrue(any('_QML' in n for n in names), names)
            # a class's own stays as it was (in a long run PySide itself may have made QQuickItem's invalid already:
            # seen after test_interfaccia_r18, before any of these closes), and so does the static one of a C++ class
            # PySide does not have (QQuickRootItem's, in Qt's library)
            static = QQuickItem.staticMetaObject
            static_was = shiboken6.isValid(static)
            root = host.window.contentItem().metaObject()
            self.assertNotIn('_QML', root.className())
            host.close()
            pump(50)
        self.assertEqual([n for n, m in zip(names, kept, strict=True) if shiboken6.isValid(m) and '_QML' in n], [])
        self.assertEqual(shiboken6.isValid(static), static_was)
        self.assertTrue(shiboken6.isValid(root))


if __name__ == '__main__':
    unittest.main()
