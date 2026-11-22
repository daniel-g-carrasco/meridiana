"""Daniel 17/11/2026, on «Activity subject to control» and «Fire-resistant roof slab» in Properties: the box sat about
five pixels lower than its words («hai visto questo? ogni volta che mi giro, trovo altri problemi»). The panel's check
swaps the control's label for a readable text, which wrote at the top of a 28 px row while the box sat in its middle.
Measured on the pixels drawn: the box and its words share the same middle line."""
import unittest

import _setup


def setUpModule():
    _setup.keep_global_state()


class BoxBesideItsWords(unittest.TestCase):

    def test_the_box_and_its_words_share_the_middle_line(self):
        from _fixtures import capannone
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtTest import QTest
        from shiboken6 import delete
        from meridiana.app.session import ProjectSession
        from meridiana.gui.backend.properties import PropertiesBackend, install_properties
        _setup.quick_app()
        session = ProjectSession(capannone())
        session.select('building', session.project.buildings[0].id)
        backend = PropertiesBackend(session)
        self.addCleanup(backend.close)
        engine = QQmlApplicationEngine()
        install_properties(engine, backend)
        engine.loadData(b"""import QtQuick
import QtQuick.Window
import Meridiana.Properties
Window { visible: true; width: 420; height: 1400; color: "white"
 PropertiesPage { anchors.fill: parent; backend: propertiesBackend }
}""")
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        self.addCleanup(delete, engine)
        self.addCleanup(window.close)
        self.assertTrue(QTest.qWaitForWindowExposed(window))

        def checks():
            found, pending = [], [window.contentItem()]
            while pending:
                item = pending.pop()
                if item.objectName().startswith('editor:fire.') and item.property('checkState') is not None:
                    found.append(item)
                pending.extend(item.childItems())
            return found

        self.assertTrue(_setup.wait_for(lambda: len(checks()) >= 2, 2000))
        QTest.qWait(200)
        image = window.grabWindow()
        dpr = image.devicePixelRatio()
        for box in checks():
            with self.subTest(check=box.objectName()):
                indicator = box.property('indicator')
                words = box.property('contentItem')
                top = box.mapToScene(box.boundingRect().topLeft())
                height = box.height()
                background = image.pixelColor(int((top.x() + box.width() - 2) * dpr), int((top.y() + 1) * dpr))

                def middle(left, right, top=top, height=height, background=background):
                    rows = []
                    for y in range(int(top.y() * dpr), int((top.y() + height) * dpr)):
                        for x in range(int(left * dpr), int(right * dpr)):
                            c = image.pixelColor(x, y)
                            if abs(c.red() - background.red()) + abs(c.green() - background.green()) \
                                    + abs(c.blue() - background.blue()) > 60:
                                rows.append(y)
                                break
                    self.assertTrue(rows, 'nothing drawn')
                    return (rows[0] + rows[-1]) / 2 / dpr

                box_middle = middle(top.x(), top.x() + indicator.width())
                start = top.x() + words.property('leftPadding')
                words_middle = middle(start, start + 120)
                self.assertAlmostEqual(box_middle, words_middle, delta=1.5)


if __name__ == '__main__':
    unittest.main()
