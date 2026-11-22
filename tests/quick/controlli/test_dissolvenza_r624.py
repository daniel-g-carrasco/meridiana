"""R624: the soft ends of the areas that scroll are the content's own transparency, short and without a step, on any
content (Daniel 15/11/2026: «ci sono ancora problemi con sta cappero di sfocatura... facciamola carina»; «la sfumatura
deve essere una trasparenza gradiente del contenuto»).

His two pictures, reproduced here: the Checks scrolled half way, where the old veil (the panel's colour over rows on
the card's colour, inset by one pixel, nearly gone two pixels in) left the edge row of the title and of the red sign
whole, a hard cut; the report's white sheet in the dark theme, where the old veil of a page (24 px, nearly opaque for
half of them) was a dark band with a kink. And a page of text, the first step of the scrolling (R590), the bottom edge.

How it is read (quick/aiuti/dissolvenza.py): three pictures of the same window, as drawn, without soft ends, the ground
alone; the opacity of the content row by row from the edge. The dissolve is a shader on a layer (Controls/EdgeFades.qml,
Controls/edgefade.frag): Qt's software renderer, the one off screen, draws no shader, so the pictures are made in a
process of their own on a graphics API (QT_QUICK_BACKEND=rhi; Direct3D 11 on Windows, the window never shown); the test
is skipped where Qt has none. Off screen, in this process, the content stays whole: that is tested here too.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NO_RHI = 3
FADE = 16                   # design.Size.FADE

REPORT = b'''
import QtQuick
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 700; height: 340; color: Theme.colors.panel
    C.ScrollView {
        id: preview; objectName: "area"; x: 20; y: 30; width: 660; height: 300; clip: true
        C.ScrollBar.vertical: M.ScrollBar { parent: preview; x: preview.width - width; height: preview.height }
        Column {
            width: preview.availableWidth; topPadding: Theme.space.L; spacing: Theme.space.XL
            Repeater { model: 3
                Rectangle { objectName: "sheet" + index; width: 600; height: 820; color: "white"
                    anchors.horizontalCenter: parent.horizontalCenter
                    Rectangle { x: 50; y: 6; width: 160; height: 44; color: "white"; border.color: "#cccccc" }
                    Rectangle { x: 50; y: 56; width: 500; height: 1; color: "black" }
                    Column { x: 50; y: 70; spacing: 8
                        Repeater { model: 40; Text { text: "Relazione tecnica, riga " + index; color: "#222222" } } } } } } }
}'''
PAGE = b'''
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 360; height: 300; color: Theme.colors.panel
    M.Section {
        x: 10; y: 10; width: 340; title: "Pannelli"; density: "flush"
        M.ScrollPage {
            objectName: "area"; width: parent.width; height: 220; spacing: 0
            Repeater { model: 30; Rectangle { width: 200; height: 20; color: index % 2 ? Theme.colors.text : Theme.colors.accent } }
        }
    }
}'''
CHECKS = b'import QtQuick\nimport Meridiana.Checks\nChecksPage { backend: checksBackend }'


def setUpModule():
    import _setup
    _setup.keep_global_state()


def render(out: Path) -> int:
    """The process of the pictures: each case's opacity row by row (cases.json)."""
    from PySide6.QtCore import QObject, QPointF, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
    app = QGuiApplication(['r624'])
    from meridiana.i18n import setup
    setup('en')
    from meridiana.gui.backend.controls import install_controls
    from quick.aiuti import dissolvenza

    def pump(_ms=0):
        # a window never shown draws no frame by itself: the bindings follow at once (no motion: reducedMotion) and
        # the lists are laid out by the next grab; what is queued is turned here, nothing is waited for
        for _ in range(3):
            app.processEvents()

    def items(item):
        yield item
        for child in item.childItems():
            yield from items(child)

    def named(root, name):
        return next(it for it in items(root) if it.objectName() == name)

    def grab(window):
        window.grabWindow()          # a window never shown lays out (polishes) its lists when it is drawn
        app.processEvents()
        return window.grabWindow()

    cases = {}
    for theme in ('dark', 'light'):
        for scene in ('verifiche', 'relazione', 'pagina'):
            if scene == 'relazione' and theme == 'light':
                continue                         # a white sheet on a light ground: nothing to see either way
            engine = QQmlEngine()
            backend = None
            if scene == 'verifiche':
                from _fixtures import capannone
                from meridiana.app.session import ProjectSession
                from meridiana.core.rules import checks
                from meridiana.gui.backend.checks import ChecksBackend, install_checks
                backend = ChecksBackend(ProjectSession(capannone()))
                backend.feed.cancel()
                detail = 'With three or more strings on an input the reverse current of the others can exceed it.'
                backend.show_items([checks.Item('fail', 'strings', f'Inverter 1: input {n}: protection of the strings',
                                                'CEI 64-8/7:2024', ('phase', 'plant'), detail=detail) for n in range(1, 4)]
                                   + [checks.Item('warn', 'layout', f'Check {n}', 'Source', ('site',), detail=detail)
                                      for n in range(11)])
                install_checks(engine, backend, {'theme': theme, 'reducedMotion': True})
                data, size = CHECKS, (1000, 300)
            else:
                install_controls(engine, dict(theme=theme, reducedMotion=True))
                data, size = (REPORT if scene == 'relazione' else PAGE), None
            component = QQmlComponent(engine)
            component.setData(data, QUrl.fromLocalFile(str(out / f'{scene}.qml')))
            root = component.create()
            if root is None:
                print(component.errorString())
                return 1
            root.setParent(engine)
            window = QQuickWindow()
            if size:
                root.setWidth(size[0])
                root.setHeight(size[1])
            window.resize(int(root.width()), int(root.height()))
            root.setParentItem(window.contentItem())
            first = grab(window)
            api = window.rendererInterface().graphicsApi()
            # no graphics API: the software renderer, or an RHI that could not be made (Linux without a GPU: the
            # window still names OpenGL, its picture is empty)
            if first.isNull() or api in (QSGRendererInterface.GraphicsApi.Software, QSGRendererInterface.GraphicsApi.Unknown):
                return NO_RHI
            if backend is not None:
                for k in range(3):
                    backend.toggleDetail(k)
                pump(150)
                grab(window)
            if scene == 'verifiche':
                flick = root.findChild(QObject, 'checks-list')
                positions = {'meta': named(root, 'checks-row-1').y() + 15}
            else:
                flick = root.findChild(QObject, 'area').property('contentItem')
                positions = ({'foglio': named(root, 'sheet1').y() + 4} if scene == 'relazione'
                             else {'meta': 33, 'primo-passo': 10})       # the page's air (6) and 4 px of rows past the edge
            here = flick.mapToScene(QPointF(0, 0))
            fades = [it for it in items(root) if it.metaObject().className().startswith('EdgeFades')
                     and abs(it.mapToScene(QPointF(0, 0)).y() - here.y()) < .5 and abs(it.height() - flick.height()) < .5]
            dpr = window.devicePixelRatio()
            x0 = int(here.x() * dpr) + 2
            x1 = int((here.x() + flick.width() - (0 if scene == 'pagina' else 14)) * dpr) - 2
            top, bottom = int(round(here.y() * dpr)), int((here.y() + flick.height()) * dpr) - 1
            rows = int(FADE * dpr * 1.5) + 6
            for where, y in positions.items():
                flick.setProperty('contentY', y)
                pump(150)
                drawn = grab(window)
                for f in fades:
                    f.setProperty('flickable', None)
                pump(100)
                bare = grab(window)
                flick.setVisible(False)
                pump(100)
                ground = grab(window)
                flick.setVisible(True)
                for f in fades:
                    f.setProperty('flickable', flick)
                pump(100)
                name = f'{scene}-{theme}-{where}'
                cases[name + '-alto'] = dict(band=min(FADE, y) * dpr, alpha=dissolvenza.opacity(drawn, bare, ground, x0, x1, top, rows))
                if scene == 'pagina' and where == 'meta':
                    cases[name + '-basso'] = dict(band=FADE * dpr, alpha=dissolvenza.opacity(
                        drawn, bare, ground, x0, x1, bottom, rows, downward=False))
                drawn.save(str(out / f'{name}.png'))
            window.close()
            window.deleteLater()
            if backend is not None:
                backend.close()
            pump(50)
    (out / 'cases.json').write_text(json.dumps(cases), encoding='utf-8')
    return 0


class Drawn(unittest.TestCase):
    """The pictures made on a graphics API, judged here."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='rhi', QSG_RENDER_LOOP='basic',
                   QT_SCALE_FACTOR='2', PYTHONDONTWRITEBYTECODE='1')
        if sys.platform == 'win32':
            env.setdefault('QSG_RHI_BACKEND', 'd3d11')
        done = subprocess.run([sys.executable, '-m', 'quick.controlli.test_dissolvenza_r624', '--render', cls.folder.name],
                              cwd=ROOT / 'tests', env=env, capture_output=True, text=True, timeout=600)
        if done.returncode == NO_RHI:
            raise unittest.SkipTest('Qt Quick has no graphics API here: the dissolve is not drawn')
        if done.returncode != 0:
            raise AssertionError(done.stdout[-3000:] + done.stderr[-3000:])
        cls.cases = json.loads((Path(cls.folder.name) / 'cases.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def judged(self, name):
        from quick.aiuti import dissolvenza
        case = self.cases[name]
        return dissolvenza.judge(case['alpha'], case['band'])

    def test_the_checks_scrolled_half_way_dissolve_without_a_cut(self):
        for theme in ('dark', 'light'):
            with self.subTest(theme=theme):
                self.assertEqual(self.judged(f'verifiche-{theme}-meta-alto'), [])

    def test_the_report_sheet_in_the_dark_theme_dissolves_short_and_smooth(self):
        self.assertEqual(self.judged('relazione-dark-foglio-alto'), [])

    def test_a_page_dissolves_at_both_edges(self):
        for name in ('pagina-dark-meta-alto', 'pagina-dark-meta-basso', 'pagina-light-meta-alto', 'pagina-light-meta-basso'):
            with self.subTest(name):
                self.assertEqual(self.judged(name), [])

    def test_the_first_step_of_the_scrolling_leaves_nothing_cut_at_the_edge(self):
        # R590: the rows 4 px past the edge (after the page's air): under a dissolve, nothing of them at the edge
        from quick.aiuti import dissolvenza
        for theme in ('dark', 'light'):
            alpha = self.cases[f'pagina-{theme}-primo-passo-alto']['alpha']
            first = next(v for v in alpha if v is not None)
            self.assertLessEqual(first, dissolvenza.EDGE, (theme, alpha[:12]))


class OffScreen(unittest.TestCase):
    """In this process Qt draws with its software renderer, which has no shader: the content stays whole, never black
    or empty, and the soft ends only say where they would be."""

    def test_the_content_stays_whole_and_the_ends_follow_the_scrolling(self):
        import _setup
        from PySide6.QtCore import QObject, QUrl
        from PySide6.QtQuick import QQuickView
        from meridiana.gui.backend.controls import install_controls
        from quick.gestures import pump
        _setup.qt_or_skip()
        view = QQuickView()
        install_controls(view.engine(), dict(theme='dark', reducedMotion=True))
        with tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False) as file:
            file.write(PAGE)
        try:
            view.setSource(QUrl.fromLocalFile(file.name))
            self.assertIsNotNone(view.rootObject(), view.errors())
            view.show()
            pump(200)
            page = view.rootObject().findChild(QObject, 'area')
            flick = page.property('contentItem')
            fades = view.rootObject().findChild(QObject, 'edgeFades')
            self.assertEqual((fades.property('topBand'), fades.property('bottomBand')), (0, FADE), 'at rest at the top')
            for y, top in ((4, 4), (60, FADE)):
                flick.setProperty('contentY', y)
                pump(60)
                self.assertEqual(fades.property('topBand'), top, 'as tall as the content gone past the edge (R590)')
            self.assertFalse(fades.property('active'), 'no layer where no shader is drawn')
            drawn = view.grabWindow()
            fades.setProperty('flickable', None)
            pump(60)
            self.assertEqual(drawn, view.grabWindow(), 'off screen the content is drawn whole')
        finally:
            view.close()
            view.deleteLater()
            pump(20)
            os.unlink(file.name)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--render':
        sys.exit(render(Path(sys.argv[2])))
    unittest.main()
