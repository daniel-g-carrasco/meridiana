"""R377/R389: native photographs (once beside the Widgets' panel), both themes and true viewport sizes."""
import copy
import os
from pathlib import Path
import unittest

import _setup
from _fixtures import capannone_rho
from PySide6.QtCore import QPoint, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import i18n
from meridiana.core.model import model
from meridiana.gui.backend.properties import PropertiesBackend, install_properties
from meridiana.app.session import ProjectSession
from quick.aiuti.realwindow import PythonCalls, native_app


@unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_NATIVE') == '1', 'Native GPU evidence is opt-in')
class PropertiesPhotos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        native_app()

    def test_photos_and_scroll_have_no_per_frame_python_work(self):
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtCore import QPointF
        from shiboken6 import delete
        i18n.setup('it')
        project = capannone_rho()
        project.props.append(model.Prop(id='p1', kind='hedge'))
        backend = PropertiesBackend(ProjectSession(copy.deepcopy(project)))
        engine = QQmlApplicationEngine()
        theme = install_properties(engine, backend)
        warnings = []
        engine.warnings.connect(lambda messages: warnings.extend(str(m) for m in messages))
        engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.Properties
Window { visible: true; width: 1366; height: 900; flags: Qt.Window | Qt.FramelessWindowHint
    color: Theme.colors.panel
    PropertiesPage { objectName: "page"; width: 380; height: parent.height; backend: propertiesBackend }
}''')
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        folder = Path('build/quick-foto/proprieta')
        folder.mkdir(parents=True, exist_ok=True)
        try:
            for mode in ('light', 'dark'):
                theme.configure(dict(theme=mode))
                for kind, oid in [('site', ''), ('building', 'b1'), ('subfield', 's1'), ('exclusion', 'e1'), ('prop', 'p1')]:
                    backend.session.select(kind, oid)
                    for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
                        window.resize(width, height)
                        QTest.qWait(180)
                        self.assertEqual((window.width(), window.height()), (width, height))
                        quick = window.grabWindow()
                        dpr = window.devicePixelRatio()
                        self.assertEqual((quick.width(), quick.height()), (round(width*dpr), round(height*dpr)))
                        quick.setDevicePixelRatio(dpr)
                        stem = f'properties-{kind}-{mode}-{width}x{height}-x{dpr:g}'
                        self.assertTrue(quick.save(str(folder / (stem + '.png'))))
            backend.session.select('site', '')
            theme.configure(dict(textSize='large'))
            page = window.findChild(type(window.contentItem()), 'page')
            self.assertIsNotNone(page)
            page.setWidth(260)
            QTest.qWait(180)
            window.grabWindow().save(str(folder / f'properties-narrow-large-x{window.devicePixelRatio():g}.png'))
            with PythonCalls(files=[Path(__file__).parents[3] / 'src/meridiana/gui/backend/properties.py']) as calls:
                for _ in range(8):
                    event = QWheelEvent(QPointF(180, 400), QPointF(180, 400), QPoint(), QPoint(0, -120),
                                        Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
                    self.app.sendEvent(window, event)
                    QTest.qWait(10)
            self.assertEqual(sum(calls.calls.values()), 0, calls.calls)
            self.assertFalse(warnings, warnings)
        finally:
            backend.close()
            window.close()
            delete(window)
            delete(engine)


if __name__ == '__main__':
    unittest.main()
