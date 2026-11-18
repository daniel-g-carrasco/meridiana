"""Install all result pages and their inspectors into the real workbench."""
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent

from .parts import Part, QML, attach
from .charts_controller import install_results
from .charts_editor import ResultEditor


def install(engine, session, cache, window):
    results = install_results(engine, bridge=window.bridge)
    results.actionRequested.connect(window.shell.trigger)
    controllers = {'results': results}
    sources = {'storage': QML / 'Charts/StoragePage.qml', 'productionTrailing': QML / 'Charts/ProductionStrip.qml'}
    for phase, title in (('production', 'Production'), ('consumption', 'Consumption'), ('economics', 'Economics')):
        editor = ResultEditor(session, phase, engine)
        editor.actionRequested.connect(window.shell.trigger)
        controllers[phase + 'Editor'] = editor
        engine.rootContext().setContextProperty(phase + 'Editor', editor)
        sources[phase] = QML / f'Charts/{title}Page.qml'
        sources[phase + '_properties'] = QML / f'Charts/{title}Inspector.qml'

    def close():
        for controller in controllers.values():
            controller.close()

    def import_curve():
        window.shell.trigger('phase_consumption')
        controllers['consumptionEditor'].openImport()

    def bind(root):
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML / 'Charts/InactiveInspector.qml')))
        if component.isError():
            raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
        # Local integration adapter until the shell freezes its retained hidden pages itself: a guard under every
        # inspector's loader, found by a walk in QML (parts._WALK says why not from Python).
        attach(engine, root.contentItem(), 'propertiesPartLoader', component, {'panel': '@item'})

    return Part('results', sources=sources, controllers=controllers, close=close, bind=bind,
                commands={'import_curve': import_curve})
