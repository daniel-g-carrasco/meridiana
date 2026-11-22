"""The pixel guard must reject a five-pixel displacement, even with unchanged item sizes."""
import unittest

import numpy as np
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

import _setup
from quick.aiuti.alignment import control_overflow, drawn_ratio, ink, items, kind, pixels, rect


def setUpModule():
    _setup.keep_global_state()


class PixelGuard(unittest.TestCase):
    def test_real_wrapped_controls_and_a_displaced_indicator(self):
        _setup.quick_app()
        engine = QQmlApplicationEngine()
        from meridiana.gui.backend.controls import install_controls
        install_controls(engine)
        engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Controls as M
Window { visible: true; width: 240; height: 160; color: "white"
 Column { width: 180
  M.CheckBox { width: parent.width; text: "A long caption that wraps over more than one line" }
  M.RadioButton { width: parent.width; text: "Another caption that wraps over more than one line" }
 }
}''')
        self.addCleanup(delete, engine)
        window = engine.rootObjects()[0]
        self.assertIsInstance(window, QQuickWindow)
        self.addCleanup(window.close)
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        for control in [n for n in items(window.contentItem()) if kind(n) in ('CheckBox', 'RadioButton')]:
            with self.subTest(kind=kind(control)):
                indicator, text = control.property('indicator'), control.property('contentItem')

                def delta(indicator=indicator, text=text):
                    QTest.qWait(20)
                    image = window.grabWindow()
                    before = pixels(image)
                    indicator.setOpacity(0)
                    text.setOpacity(0)
                    QTest.qWait(20)
                    mask = np.abs(before - pixels(window.grabWindow())).sum(axis=2) > 60
                    indicator.setOpacity(1)
                    text.setOpacity(1)
                    words = rect(text)
                    words.setLeft(words.left() + text.property('leftPadding'))
                    ratio = drawn_ratio(image, window)
                    a = ink(mask, rect(indicator), ratio)
                    b = ink(mask, words, ratio, first=True)
                    self.assertIsNotNone(a)
                    self.assertIsNotNone(b)
                    return a-b

                self.assertLessEqual(abs(delta()), 1.5)
                y = indicator.y()
                # The former implementation centred the indicator over the whole wrapped block.
                indicator.setY((control.height() - indicator.height()) / 2)
                self.assertGreater(abs(delta()), 1.5)
                indicator.setY(y+5)
                self.assertGreater(abs(delta()), 3.5)
                indicator.setY(y)
                width = control.width()
                control.setWidth(window.width()+20)
                self.assertGreater(control_overflow(control, window)[0], 1.5)
                control.setWidth(width)

    def test_wrapped_labels_use_the_ink_of_the_first_and_last_lines(self):
        _setup.quick_app()
        from meridiana.gui.backend.controls import install_controls
        engine = QQmlApplicationEngine()
        install_controls(engine)
        engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Controls as M
Window { visible: true; width: 240; height: 180; color: "white"
 Column {
  Repeater { model: ["Progetto", "Codice della pratica di connessione", "Moduli per tavola, in altezza", "Caption\\ngyp tails"]
   Item { width: 180; height: Math.max(28, caption.implicitHeight)
    M.Label { id: caption; objectName: "caption"; width: 140; text: modelData; wrapMode: Text.Wrap
      y: parent.height / 2 - M.ControlMetrics.textMiddleOffset(caption) }
   }
  }
 }
}''')
        self.addCleanup(delete, engine)
        window = engine.rootObjects()[0]
        self.addCleanup(window.close)
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        for label in [n for n in items(window.contentItem()) if n.objectName() == 'caption']:
            with self.subTest(text=label.property('text')):
                QTest.qWait(20)
                image = window.grabWindow()
                before = pixels(image)
                label.setOpacity(0)
                QTest.qWait(20)
                mask = np.abs(before - pixels(window.grabWindow())).sum(axis=2) > 60
                label.setOpacity(1)
                middle = ink(mask, rect(label), drawn_ratio(image, window))
                self.assertIsNotNone(middle)
                self.assertAlmostEqual(middle, rect(label.parentItem()).center().y(), delta=1.5)
