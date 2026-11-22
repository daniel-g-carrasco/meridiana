"""R555 (6), again on 14/11/2026 (Daniel: «avevo richiesto che la barra degli strumenti del 3d ... non avesse bordo basso
così alto e fosse uguale al suo bordo alto verso la vista 3d»): on the window as it is drawn, the sun bar's controls
stand as far from the 3D drawing above them as from the frame's line under them. The bar has the panel's ground, the
same as the room the views' card leaves under the 3D: before, 4 pixels above and 9 below (its own air, and under it the
card's room too).

Read on the pixels of a column through the day's field: the last row of the 3D drawing, the field's first and last
rows, the card's line. Equal within one device pixel, in the side-by-side views and in the 3D alone."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QPointF

import _setup
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import pump

setUpModule = _setup.keep_global_state


def same(c, g, tolerance=3):
    return max(abs(c.red() - g.red()), abs(c.green() - g.green()), abs(c.blue() - g.blue())) <= tolerance


class SunBarRoom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1920, 1000)          # wide: the plan and the 3D side by side (offscreen: after show)
        pump(400)
        cls.win.showPhase('model')
        pump(1200)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        cls.folder.cleanup()

    def find(self, name):
        pending = [self.win.contentItem()]
        while pending:
            o = pending.pop()
            if o.objectName() == name and o.isVisible():
                return o
            pending.extend(o.childItems())
        return None

    def rows(self):
        from meridiana.gui.capture import grab
        bar, day = self.find('sunBar'), self.find('sunDay')
        if bar is None or day is None:
            raise StopIteration     # not shown yet
        image = grab(self.win)
        d = image.devicePixelRatio()
        ground = bar.property('color')
        x = int((day.mapToScene(QPointF(day.width() / 2, 0)).x()) * d)
        top = int((bar.mapToScene(QPointF(0, 0)).y() - 6) * d)
        column = [(y, image.pixelColor(x, y)) for y in range(top, image.height())]
        i = next(k for k, (_y, c) in enumerate(column) if same(c, ground))
        j = next(k for k in range(i, len(column)) if not same(column[k][1], ground))
        k = next(k for k in range(j, len(column)) if same(column[k][1], ground))
        m = next(n for n in range(k, len(column)) if not same(column[n][1], ground))
        view_end, field_top, field_bottom, line = column[i - 1][0], column[j][0], column[k - 1][0], column[m][0]
        return field_top - view_end - 1, line - field_bottom - 1, d

    def drawn(self):
        """The 3D drawn above the bar (its first frames show the panel's ground there) and the layout settled: two
        readings in a row the same."""
        try:
            first = self.rows()
        except StopIteration:
            return False
        pump(100)
        try:
            return first[0] > 0 and self.rows() == first
        except StopIteration:
            return False

    def check(self, where):
        self.assertTrue(_setup.wait_until(self.app, self.drawn), f'{where}: the 3D was not drawn above the bar')
        above, below, d = self.rows()
        self.assertGreater(above, 0, where)
        self.assertLessEqual(abs(above - below), 1, f'{where}: {above} device pixels above the bar\'s controls, {below} below')

    def test_the_bar_has_as_much_room_above_its_controls_as_below(self):
        for mode in ('both', '3d'):
            self.host.shell.viewModeRequested.emit(mode)      # the commands «Plan and 3D» and «3D» (view_both, view_3d)
            pump(600)
            self.check('views ' + mode)


if __name__ == '__main__':
    unittest.main()
