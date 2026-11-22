"""R607 (Daniel 14/11/2026, the window «Importa un modello IFC»): «lavoriamo sulla centralizzazione della finestra fatta
bene e replicabile». The common window (M.Dialog) and the common row of a job (M.WorkRow), measured as they are drawn:

- the job's row is made of columns: nothing moves when the phase or the percentage changes, the phase is cut with its
  whole text in the tooltip, the texts sit on one baseline, and the row lines up with the window's title and with its
  buttons; the bar is a thread (the sketches of r35-pillole, Daniel: «il filo grigio (A) ma con le parole sopra e la
  barra sotto (tipo in C)»), 2 px high, under the words and as wide as the row; in the status bar's form (`inline`)
  one line, the thread taking the room the words leave;
- one «Cancel» while a job runs in a window: the window's own; outside a window the row keeps its own;
- the head: the title and a subtitle of one line (the file's short name; the whole path in the tooltip); the pointer
  over the head is the four arrows of what moves, as on the panels' titles;
- the buttons of the window's row stand on one baseline, the last at the window's margin.

«Aligned» is within one pixel of the device.

    python -m unittest quick.shell.test_finestre_r607
"""
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import i18n
from meridiana.gui.backend.controls import install_controls

setUpModule = _setup.keep_global_state

LONG = 'C:/Progetti/Studio/30_Esecutivo/10_BIM/04_File utili/Clash Detection/20261029/ifc/Edificio_A_9001_R25_Stato di progetto.ifc'
SHORT = 'Edificio_A_9001_R25_Stato di progetto'


def row(phase, fraction, left=''):
    return {'id': 7, 'slot': 'ifc_read', 'title': 'Lettura del modello IFC', 'phase': phase, 'determinate': True,
            'fraction': fraction, 'percent': f'{round(100 * fraction)} %', 'left': left, 'cancellable': True,
            'state': 'running'}


class Window(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        i18n.setup('it')
        engine = self.engine = QQmlApplicationEngine()
        self.addCleanup(engine.deleteLater)
        install_controls(engine, {'theme': 'light'})
        engine.loadData(b'''import QtQuick
import QtQuick.Layouts
import Meridiana.Controls as M
Window { id: top; width: 1000; height: 800; visible: true
    property var job: ({})
    property string subtitle: ""
    M.Dialog { objectName: "probe"; title: "Importa un modello IFC"; subtitle: top.subtitle; subtitleTip: "''' + LONG.encode() + b'''"
        implicitWidth: 680; acceptText: "Aggiungi il modello"; acceptEnabled: false; rejectText: "Annulla"
        ColumnLayout { M.WorkRow { objectName: "inside"; Layout.fillWidth: true; row: top.job; cancelText: "Annulla"; leftWidest: "circa 99 min" } } }
    M.WorkRow { objectName: "outside"; inline: true; width: 900; y: 10; row: top.job; cancelText: "Annulla"; leftWidest: "circa 99 min" }
}''')
        self.assertTrue(engine.rootObjects())
        self.window = engine.rootObjects()[0]
        self.dialog = self.window.findChild(QObject, 'probe')
        self.window.setProperty('job', row('preparazione', 0.0))
        QMetaObject.invokeMethod(self.dialog, 'open', Qt.ConnectionType.DirectConnection)
        _setup.wait_for(lambda: self.dialog.property('opened'), 3000)
        self.polish()
        self.dpr = self.window.devicePixelRatio()

    def items(self):
        out, pending = [], [self.window.contentItem()]
        while pending:
            o = pending.pop()
            out.append(o)
            pending.extend(o.childItems())
        return out

    def named(self, name, under=None):
        found = [o for o in (self.under(under) if under else self.items()) if o.objectName() == name and self.shown(o)]
        return found[0] if found else None

    def under(self, item):
        out, pending = [], [item]
        while pending:
            o = pending.pop()
            out.append(o)
            pending.extend(o.childItems())
        return out

    @staticmethod
    def shown(o):
        while o is not None:
            if not o.isVisible():
                return False
            o = o.parentItem()
        return True

    def box(self, item):
        p = item.mapToScene(QPointF(0, 0))
        return [p.x() * self.dpr, p.y() * self.dpr, item.width() * self.dpr, item.height() * self.dpr]

    def baseline(self, item):
        return item.mapToScene(QPointF(0, item.property('baselineOffset'))).y() * self.dpr

    def hover_tip(self, item):
        """The text of the tooltip shown with the pointer over `item` (None when none shows)."""
        tips = [o for o in item.findChildren(QObject) if o.metaObject().indexOfProperty('delay') >= 0]
        p = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        QTest.mouseMove(self.window, QPoint(int(p.x()), int(p.y())))
        if not _setup.wait_for(lambda: any(t.property('visible') for t in tips), 3000):
            return None
        return next(t.property('text') for t in tips if t.property('visible'))

    def columns(self, where='inside'):
        r = self.named(where)
        return {name: self.box(self.named(name, r)) for name in ('workText', 'workPhase', 'workBar', 'workPercent', 'workLeft')}

    def polish(self):
        """The layouts laid out now (what the next frame would do), without a wait of a fixed time."""
        self.app.processEvents()
        for item in self.items():
            item.ensurePolished()

    def settle(self, job):
        self.window.setProperty('job', job)
        self.polish()

    def test_r607_nothing_of_the_row_moves_when_the_phase_or_the_percentage_changes(self):
        for where in ('inside', 'outside'):
            with self.subTest(where=where):
                self.steady(where)

    def steady(self, where):
        self.settle(row('preparazione', 0.0))
        first = self.columns(where)
        for job in (row('lettura del file, con più processi insieme, e poi i tetti e gli ostacoli', 0.07),
                    row('tetti', 0.42), row('tetti', 0.43, 'circa 40 s'), row('x', 1.0, 'circa 12 min'),
                    row('', 0.5), row('preparazione', 0.0)):
            self.settle(job)
            now = self.columns(where)
            for name in first:
                for a, b in zip(first[name], now[name], strict=True):
                    self.assertLessEqual(abs(a - b), 1, (job['phase'], job['percent'], name, first[name], now[name]))

    def test_r607_the_phase_is_cut_and_whole_in_its_tooltip_and_the_bar_has_the_room_left(self):
        self.settle(row('lettura del file, con più processi insieme, e poi i tetti, gli ostacoli, i solai interni e il terreno', 0.07))
        phase = self.named('workPhase', self.named('inside'))
        self.assertTrue(phase.property('truncated'))
        self.assertEqual(self.hover_tip(phase), phase.property('text'), 'the phase whole in its tooltip')
        outside = self.named('outside')
        self.assertTrue(self.named('workPhase', outside).property('truncated'))
        bar = self.named('workBar', outside)
        self.assertGreater(bar.width(), 120 + 40, 'in one line the thread takes the room the words leave, not 120 only')

    def test_r607_the_thread_is_2_px_under_the_words_as_wide_as_the_row(self):
        self.settle(row('tetti', 0.42))
        inside = self.named('inside')
        bar = self.named('workBar', inside)
        self.assertLessEqual(abs(self.box(bar)[3] - 2 * self.dpr), 1, 'the thread is 2 px high')
        lowest = max(self.box(self.named(n, inside))[1] + self.box(self.named(n, inside))[3]
                     for n in ('workText', 'workPhase', 'workPercent'))
        self.assertGreaterEqual(self.box(bar)[1], lowest, 'the thread is under the words')
        self.assertLessEqual(abs(self.box(bar)[0] - self.box(inside)[0]), 1)
        self.assertLessEqual(abs(self.box(bar)[2] - self.box(inside)[2]), 1, 'as wide as the row')
        fill = next(o for o in self.under(bar) if o.objectName() == 'progressFill')
        self.assertLessEqual(abs(fill.width() - 0.42 * bar.width()), 1)
        outside = self.named('outside')
        thread = self.named('workBar', outside)
        self.assertLessEqual(abs(self.box(thread)[3] - 2 * self.dpr), 1, 'the same thread in one line')
        text = self.named('workText', outside)
        middle = self.box(text)[1] + self.box(text)[3] / 2
        self.assertLessEqual(abs(self.box(thread)[1] + self.box(thread)[3] / 2 - middle), 2, 'in the middle of the line')

    def test_r607_the_row_lines_up_with_the_title_and_the_buttons_and_on_one_baseline(self):
        self.settle(row('tetti', 0.42))
        inside = self.named('inside')
        title = self.named('dialogTitle')
        self.assertLessEqual(abs(self.box(inside)[0] - self.box(title)[0]), 1)
        buttons = self.named('dialogButtons')
        self.assertLessEqual(abs(self.box(inside)[0] + self.box(inside)[2] - (self.box(buttons)[0] + self.box(buttons)[2])), 1)
        lines = [self.baseline(self.named(n, inside)) for n in ('workText', 'workPhase', 'workPercent')]
        self.assertLessEqual(max(lines) - min(lines), 1, lines)

    def test_r607_one_cancel_while_a_job_runs_in_a_window(self):
        inside, outside = self.named('inside'), self.named('outside')
        self.assertIsNone(self.named('workCancel', inside), 'the row in a window has no Cancel of its own')
        self.assertEqual(self.named('dialogReject').property('text'), 'Annulla')
        self.assertIsNotNone(self.named('workCancel', outside), 'outside a window the row keeps its Cancel')
        cancels = [o for o in self.under(self.dialog.property('background').parentItem())
                   if self.shown(o) and o.metaObject().indexOfProperty('flat') >= 0 and o.property('text') == 'Annulla']
        self.assertEqual(len(cancels), 1)

    def test_r607_the_buttons_of_the_window_stand_on_one_baseline_the_last_at_the_margin(self):
        frame = self.dialog.property('background')
        labels = []
        for name in ('dialogAccept', 'dialogReject'):
            button = self.named(name)
            label = next(o for o in self.under(button) if o is not button and o.property('text') == button.property('text')
                         and o.metaObject().indexOfProperty('baselineOffset') >= 0)
            labels.append(self.baseline(label))
            self.assertEqual(self.box(button)[3], self.box(self.named('dialogReject'))[3])
        self.assertLessEqual(abs(labels[0] - labels[1]), 1, labels)
        buttons = self.named('dialogButtons')
        pad = 16 * self.dpr
        self.assertLessEqual(abs(self.box(frame)[0] + self.box(frame)[2] - pad - (self.box(buttons)[0] + self.box(buttons)[2])), 1)

    def test_r607_the_head_a_title_and_a_subtitle_of_one_line_with_the_path_in_its_tooltip(self):
        # long enough to be cut with any font: three times SHORT fitted in the head with FreeType's narrower advances
        self.window.setProperty('subtitle', ' '.join([SHORT] * 6))
        self.polish()
        sub = self.named('dialogSubtitle')
        self.assertIsNotNone(sub)
        self.assertEqual(sub.property('lineCount'), 1)
        self.assertTrue(sub.property('truncated'))
        self.assertEqual(self.hover_tip(sub), LONG, 'the whole path in the tooltip, the head that carries over it')
        title = self.named('dialogTitle')
        self.assertLessEqual(abs(self.box(sub)[0] - self.box(title)[0]), 1)

    def test_r607_the_pointer_over_the_head_is_the_four_arrows(self):
        self.window.setProperty('subtitle', SHORT)
        self.polish()
        carry = self.named('dialogCarry')
        self.assertEqual(carry.property('cursorShape'), Qt.CursorShape.SizeAllCursor)
        head = self.box(carry)
        for name in ('dialogTitle', 'dialogSubtitle'):
            b = self.box(self.named(name))
            self.assertTrue(head[1] <= b[1] and b[1] + b[3] <= head[1] + head[3] + 1, name)


class ShortName(unittest.TestCase):
    """The window names the file it reads by the program's short name (core/model/imported.file_stem)."""

    def test_r607_the_file_read_is_named_short_and_kept_whole_for_the_tooltip(self):
        _setup.qt_or_skip()
        from meridiana.app.platform.config import Config
        from meridiana.app.session import ProjectSession
        from meridiana.core.model import model
        from meridiana.gui.backend.dialogs import DialogsBackend
        backend = DialogsBackend(ProjectSession(model.Project()), Config(network_tiles=False, network_geocoding=False))
        self.addCleanup(backend.deleteLater)
        backend.open('ifc')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Edificio A R25.rvt'
            path.write_bytes(b'not at all' * 100)
            backend.readFile(str(path))
        self.assertEqual(backend.state['fileShort'], 'Edificio A R25')
        self.assertEqual(backend.state['fileName'], str(path))


if __name__ == '__main__':
    unittest.main()
