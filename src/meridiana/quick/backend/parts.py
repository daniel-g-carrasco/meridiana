"""One installation contract for the integrated Quick workbench.

Each backend/*_part.py exports install(engine, session, cache, window) -> Part.
Installation precedes QML loading; Part.bind runs after window.window exists.
The window argument is QuickWindow, owning bridge, shell and theme.
"""
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QUrl

QML = Path(__file__).resolve().parents[1] / 'qml' / 'Meridiana'

# The window's items are walked in QML, never from Python (tests/quick/shell/test_parts_walk.py): PySide keeps a
# wrapper for every C++ address handed to Python, and a QMetaObject wrapper (a QML object's dynamic meta-object, asked
# by metaObject()) can outlive its object; an item born later at the same address came back from childItems() as that
# QMetaObject (AttributeError at charts_part.bind on r20-unita, now and then in the suite). A walk in QML hands no item
# to Python. attach(root, name, component, properties, onlyOnce, childName): under root, every item named `name` (or
# one of a list of names) gets a component's object made with it as parent, with {properties}, where "@item" stands
# for the item and "@name" for its name without "tool_"; with onlyOnce, an item that has a child named childName
# ("@name" again replaced) already keeps it. The answer is "" or the component's error.
_WALK = b"""import QtQuick
QtObject {
    function attach(root, name, component, properties, onlyOnce, childName) {
        const pending = [root]
        while (pending.length) {
            const item = pending.pop()
            const kids = item.children
            for (let i = 0; i < kids.length; i++) pending.push(kids[i])
            if (typeof name === "string" ? item.objectName !== name : !name.includes(item.objectName)) continue
            const own = childName.replace("@name", item.objectName.replace(/^tool_/, ""))
            let present = false
            for (let i = 0; onlyOnce && i < kids.length; i++) present = present || kids[i].objectName === own
            if (present) continue
            const values = {}
            for (const key in properties)
                values[key] = properties[key] === "@item" ? item : properties[key] === "@name" ? item.objectName.replace(/^tool_/, "") : properties[key]
            if (!component.createObject(item, values)) return component.errorString() || ("not made under " + item.objectName)
        }
        return ""
    }
}
"""


def walker(engine):
    """The engine's QML walker (one per engine), see _WALK."""
    found = getattr(engine, '_meridiana_walker', None)
    if found is None:
        from PySide6.QtQml import QQmlComponent
        component = QQmlComponent(engine)
        component.setData(_WALK, QUrl('file:///meridiana-walk.qml'))
        found = component.create()
        if found is None:
            raise RuntimeError('; '.join(error.toString() for error in component.errors()))
        found.setParent(engine)
        engine._meridiana_walker = found
    return found


def attach(engine, root, name, component, properties, only_once=False, child_name=''):
    """Make a component's object under every item named `name` (or one of the names) below root, walking in QML."""
    from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject
    answer = QMetaObject.invokeMethod(walker(engine), 'attach', Q_RETURN_ARG('QVariant'), Q_ARG('QVariant', root),
                                      Q_ARG('QVariant', name), Q_ARG('QVariant', component),
                                      Q_ARG('QVariant', properties), Q_ARG('QVariant', only_once),
                                      Q_ARG('QVariant', child_name))
    if answer:
        raise RuntimeError(answer)


@dataclass
class Part:
    id: str
    sources: dict = field(default_factory=dict)
    controllers: dict = field(default_factory=dict)
    commands: dict = field(default_factory=dict)
    bind: Callable | None = None
    close: Callable | None = None


class Parts:
    def __init__(self, engine, session, cache, window):
        self.engine, self.session, self.cache, self.window = engine, session, cache, window
        self.installed = {}
        self.sources = {}
        self.controllers = {}
        self._closed = False

    def install(self, factory):
        part = factory(self.engine, self.session, self.cache, self.window)
        if not isinstance(part, Part):
            raise TypeError(f'{factory.__module__}.install must return Part')
        overlap = self.sources.keys() & part.sources.keys()
        if part.id in self.installed or overlap:
            raise ValueError(f'Duplicate part or place: {part.id}, {sorted(overlap)}')
        self.installed[part.id] = part
        self.sources.update(part.sources)
        self.controllers.update(part.controllers)
        return part

    def discover(self):
        """Deterministic discovery; a broken part fails loudly at startup."""
        # by the package's listing, not its files: the Windows package has no .py on disk (pkgutil reads its archive)
        import pkgutil
        package = import_module(__package__)
        for name in sorted(m.name for m in pkgutil.iter_modules(package.__path__) if m.name.endswith('_part')):
            module = import_module(f'{__package__}.{name}')
            self.install(module.install)

    def initial_properties(self):
        return {'partSources': {key: QUrl.fromLocalFile(str(Path(value).resolve()))
                                for key, value in self.sources.items()}}

    def bind(self):
        for part in self.installed.values():
            for command, handler in part.commands.items():
                self.window.shell.register_command(command, handler)
            if part.bind:
                part.bind(self.window.window)

    def close(self):
        if self._closed:
            return
        self._closed = True
        for part in reversed(list(self.installed.values())):
            if part.close:
                part.close()


def install_plan(engine, session, cache, window):
    from .plan import PlanController
    controller = PlanController(session, cache=cache, manage_layout=False)
    controller.install(engine)
    engine.rootContext().setContextProperty('planBackend', controller)
    window.plan = controller
    return Part('plan', sources={'plan': QML / 'Shell/PlanHost.qml'},
                controllers={'plan': controller}, close=controller.close)


def install_scene(engine, session, cache, window):
    from . import scene_host
    controller = scene_host.install(engine, session, cache)
    window.scene = controller
    return Part('scene', sources={'view3d': QML / 'Shell/View3DHost.qml'},
                controllers={'scene': controller}, close=controller.close)
