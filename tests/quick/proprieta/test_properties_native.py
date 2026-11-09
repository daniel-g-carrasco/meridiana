"""R377/R389: native photographs beside Widgets, both themes and true viewport sizes."""
import copy
import os
from pathlib import Path
import unittest

import _setup
from _fixtures import capannone_rho
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import config, i18n, model
from meridiana.quick.backend.properties import PropertiesBackend, install_properties
from meridiana.session import ProjectSession
from quick.parity.realwindow import PythonCalls, native_app


@unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_NATIVE') == '1', 'Native GPU evidence is opt-in')
class PropertiesPhotos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        native_app()

    def test_photos_and_scroll_have_no_per_frame_python_work(self):
        from meridiana.ui.properties import Properties
        from meridiana.ui.theme import Theme
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtCore import QPointF
        from shiboken6 import delete
        i18n.setup('it')
        widget_theme = Theme(config.Config(theme='light', accent='indigo', backgrounds='grey', font='plex', background='none'), app=self.app)
        widget_theme.apply()
        project = capannone_rho()
        project.props.append(model.Prop(id='p1', kind='hedge'))
        backend = PropertiesBackend(ProjectSession(copy.deepcopy(project)))
        widget = Properties()
        widget.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        widget.resize(380, 900)
        widget.show()
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
                widget_theme.cfg.theme = mode
                widget_theme.applied = None
                widget_theme.apply()
                for kind, oid in [('site', ''), ('building', 'b1'), ('subfield', 's1'), ('exclusion', 'e1'), ('prop', 'p1')]:
                    backend.session.select(kind, oid)
                    if kind == 'site':
                        widget.show_site(project, False)
                    elif kind == 'building':
                        widget.show_building(project.buildings[0])
                    elif kind == 'subfield':
                        widget.show_subfield(project, project.subfields[0], None)
                    elif kind == 'exclusion':
                        widget.show_exclusion(project.exclusions[0])
                    else:
                        widget.show_prop(project.props[0])
                    for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
                        window.resize(width, height)
                        widget.resize(380, height)
                        QTest.qWait(180)
                        self.assertEqual((window.width(), window.height()), (width, height))
                        quick = window.grabWindow()
                        dpr = window.devicePixelRatio()
                        self.assertEqual((quick.width(), quick.height()), (round(width*dpr), round(height*dpr)))
                        quick.setDevicePixelRatio(dpr)
                        stem = f'properties-{kind}-{mode}-{width}x{height}-x{dpr:g}'
                        self.assertTrue(quick.save(str(folder / (stem + '.png'))))
                        old = widget.grab().toImage()
                        old.setDevicePixelRatio(widget.devicePixelRatioF())
                        compared = QImage(round(780*dpr), round(height*dpr), QImage.Format.Format_RGB32)
                        compared.setDevicePixelRatio(dpr)
                        compared.fill(theme.colors['panel'])
                        painter = QPainter(compared)
                        painter.drawImage(QPoint(0, 0), old)
                        cropped = quick.copy(0, 0, round(380*dpr), quick.height())
                        cropped.setDevicePixelRatio(dpr)
                        painter.drawImage(QPoint(400, 0), cropped)
                        painter.end()
                        self.assertTrue(compared.save(str(folder / (stem + '-widgets-quick.png'))))
            backend.session.select('site', '')
            theme.configure(dict(textSize='large'))
            page = window.findChild(type(window.contentItem()), 'page')
            self.assertIsNotNone(page)
            page.setWidth(260)
            QTest.qWait(180)
            window.grabWindow().save(str(folder / f'properties-narrow-large-x{window.devicePixelRatio():g}.png'))
            with PythonCalls(files=[Path(__file__).parents[3] / 'src/meridiana/quick/backend/properties.py']) as calls:
                for _ in range(8):
                    event = QWheelEvent(QPointF(180, 400), QPointF(180, 400), QPoint(), QPoint(0, -120),
                                        Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
                    self.app.sendEvent(window, event)
                    QTest.qWait(10)
            self.assertEqual(sum(calls.calls.values()), 0, calls.calls)
            self.assertFalse(warnings, warnings)
        finally:
            backend.close()
            widget.close()
            delete(widget)
            window.close()
            delete(window)
            delete(engine)


if __name__ == '__main__':
    unittest.main()
