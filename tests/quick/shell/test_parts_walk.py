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
import sys
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QMetaObject
from PySide6.QtQuick import QQuickItem

from _fixtures import capannone
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import pump


def setUpModule():
    _setup.keep_global_state()


class ItemsWalkedInQml(unittest.TestCase):
    def test_a_stale_wrapper_among_the_children_breaks_nothing(self):
        _setup.qt_or_skip()
        create_app()
        original = QQuickItem.childItems

        def with_stale(item):
            return list(original(item)) + [QMetaObject()]

        def walk(root):
            pending, items = [root], []
            while pending:
                node = pending.pop()
                items.append(node)
                pending.extend(original(node))
            return items

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
                    loaders = [i for i in walk(host.window.contentItem()) if i.objectName() == 'propertiesPartLoader']
                    self.assertTrue(loaders)
                    guarded = [p for p in loaders if any('InactiveInspector' in c.metaObject().className()
                                                         for c in p.children())]
                    self.assertEqual(len(guarded), len(loaders), 'every inspector loader of the start has its guard')
                    host.window.show()
                    host.shell.trigger('phase_plant')
                    pump(400)
                    host.shell.trigger('phase_model')
                    pump(400)
                    marks = [i for i in walk(host.window.contentItem()) if i.objectName() in ('stale-compute', 'stale-fill')]
                    self.assertTrue(marks, 'the stale marks of the bar are made')
                    for m in marks:             # a change of phase adds none to a tool that has one
                        same = [k for k in original(m.parentItem()) if k.objectName() == m.objectName()]
                        self.assertEqual(len(same), 1, m.parentItem().objectName())
                finally:
                    host.close()
                    pump(50)
        finally:
            QQuickItem.childItems = original
            sys.excepthook = hook
        self.assertEqual(errors, [])

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
        self.assertEqual([n for n, m in zip(names, kept) if shiboken6.isValid(m) and '_QML' in n], [])
        self.assertEqual(shiboken6.isValid(static), static_was)
        self.assertTrue(shiboken6.isValid(root))


if __name__ == '__main__':
    unittest.main()
