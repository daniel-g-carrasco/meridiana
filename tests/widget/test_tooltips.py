"""The tooltips (ui/popups.py, R162; Daniel, 25/10/2026: «Anche il tooltip non è stato armonizzato, e almeno su Linux
c'entra proprio poco, ma sia su Windows che su Linux è da dargli una larghezza massima in cui il testo va in colonna.
Sarebbe anche bello dare una bella formattazione ai contenuti come fanno programmi tipo VS Code»): «Name (key)» and
the explanation laid out apart, wrapped at a width, Qt's own label whoever asks for it. PySide6 and a display
(offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Tooltips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_name_the_key_and_the_explanation_apart(self):
        from meridiana.ui import popups
        ink, ground = "#f8f7f4", "#1e1c19"
        one = popups.tip_html("Modello (Ctrl+1)", ink, ground)
        self.assertIn("Modello", one)
        self.assertIn(">Ctrl+1</span>", one)                       # the key apart, muted
        self.assertNotIn("font-weight:600;\">Modello", one)          # one line: not a title
        two = popups.tip_html("Calcola (F5)\nSimula un anno ora per ora", ink, ground)
        self.assertIn("font-weight:600", two)                       # a name over an explanation: semibold
        self.assertIn("Simula un anno ora per ora</p>", two)
        self.assertEqual(two.count("<p "), 2)
        words = popups.tip_html("Esporta (PDF)", ink, ground)       # words in brackets are not a key
        self.assertIn("Esporta (PDF)", words)
        self.assertIn("&lt;", popups.tip_html("a < b", ink, ground))
        rich = "<b>già</b> ricco"
        self.assertEqual(popups.tip_html(rich, ink, ground), rich)

    def test_qts_own_label_is_laid_out_wrapped_at_the_width_whoever_shows_it(self):
        from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer
        from PySide6.QtWidgets import QApplication, QLabel, QToolTip, QWidget

        from meridiana.ui import popups

        def pump(seconds):
            loop = QEventLoop()
            QTimer.singleShot(int(seconds * 1000), loop.quit)
            loop.exec()

        popups.install(self.app)
        w = QWidget()
        self.addCleanup(w.deleteLater)
        w.resize(400, 300)
        w.show()
        pump(0.1)
        sizes = {}
        for text in ("Modello (Ctrl+1)", "Calcola la producibilità (F5)\nSimula un anno ora per ora con il meteo "
                     "del sito e le ombre dei moduli, poi riempie le pagine Producibilità, Consumi e Bilancio"):
            QToolTip.showText(w.mapToGlobal(QPoint(40, 40)), text, w)
            pump(0.2)
            label = next(x for x in QApplication.topLevelWidgets() if isinstance(x, QLabel)
                         and x.windowType() == Qt.WindowType.ToolTip and x.isVisible())
            self.assertEqual(label.text(), text)                    # Qt's identity remains the original text
            self.assertIn("<p ", label.property(popups._LAID)[2])    # the separate document owns rich formatting
            sizes[text[:7]] = (label.width(), label.height(), label.wordWrap())
            QToolTip.hideText()
            pump(0.4)
        width, height, wrapped = sizes["Modello"]
        self.assertFalse(wrapped)
        self.assertLess(width, popups.TIP_WIDTH)
        width, height, wrapped = sizes["Calcola"]
        self.assertTrue(wrapped)                                    # in a column, not across the screen (R162)
        self.assertEqual(width, popups.TIP_WIDTH)                    # and Qt's second measure set back (QTBUG-64550)
        self.assertGreater(height, 3 * sizes["Modello"][1] // 2)


if __name__ == "__main__":
    unittest.main()
