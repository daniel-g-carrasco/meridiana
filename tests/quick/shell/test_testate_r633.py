"""R633 (Daniel 15/11/2026, the Plant's panel, sketch B: «testate sempre in vista: da gestire però bene come nel resto la
sfumatura, e che la forma delle testate rimanga quella quando si scorre verso il basso ... lo renderei un comportamento
generale per queste schede (schede di destra), centralizziamo e unifichiamo»; «il margine risultante destro tra
sottoscheda e scheda vorrei che fosse lo stesso a sinistra, di modo che le sottoschede siano centrate nella scheda»).

A. On a panel's page (M.PanelPage) off screen: the head of a section that leaves the page at the top stays at the top,
   the heads of the sections under the page wait at the bottom, stacked with the page's air and gaps; the content
   dissolves from their edge (EdgeFades' insets), never over a head in its place; at most a quarter of the page at
   each edge (ControlMetrics.heldShare), the farthest heads scroll away; a click on a held head opens or closes its
   section and brings it into view; the wheel over a held head scrolls the page; Tab reaches the sections' own heads
   only; groups inside a section, and pages that are not a panel's, hold nothing.
B. Drawn on a graphics API (Direct3D 11 on Windows, in a process of its own, as test_dissolvenza_r624): a held head is
   the same at the pixel as the same head in its place, nothing of the content shows under the held heads, and the
   dissolve starts at their edge with the shape of every other (quick/aiuti/dissolvenza.py).
C. On the real window, every side panel made of an M.PanelPage: the bar's thumb as far from the sections as from the
   card's right side, and the sections as far from the card's left side as all that room: centred in the card (R637:
   ControlMetrics.cardMargin round the content on the four sides, the thumb in the right margin, 3 + 6 + 3).

    python -m unittest quick.shell.test_testate_r633
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
AIR = 0                     # M.PanelPage's air (R637: the card's margin is round the page, none inside it)

# a panel's page: an open section with a long body, two more open, two closed at the end (as the Plant's Inverter and
# Storage); rows of two colours, so that a dissolve can be read on them
PANEL = '''
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 360; height: %(height)d; color: Theme.colors.panel
    M.PanelPage {
        objectName: "page"; anchors.fill: parent
        Repeater {
            model: %(count)d
            M.Section {
                required property int index
                objectName: "section" + index
                width: parent.width; title: "Sezione " + index; density: "form"
                headName: "head" + index; helpId: index === 1 ? "site" : ""
                _open: index < %(open)d
                Column {
                    width: parent.width
                    Repeater { model: %(rows)d
                        Rectangle { width: parent.width; height: 20; color: index %% 2 ? Theme.colors.text : Theme.colors.accent } }
                    M.Section { objectName: "group"; width: parent.width; title: "Gruppo"
                        Rectangle { width: parent.width; height: 40; color: Theme.colors.field } }
                }
            }
        }
    }
}'''


def panel(height=480, count=4, open_=2, rows=20):
    return PANEL % dict(height=height, count=count, open=open_, rows=rows)


def setUpModule():
    import _setup
    _setup.keep_global_state()


def items(item):
    yield item
    for child in item.childItems():
        yield from items(child)


def named(root, name):
    found = next((it for it in items(root) if it.objectName() == name), None)
    if found is None:
        raise AssertionError('missing ' + name)
    return found


def render(out: Path) -> int:
    """The process of the pictures, on a graphics API: the held heads and the dissolve under them (cases.json)."""
    from PySide6.QtCore import QPointF, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
    app = QGuiApplication(['r633'])
    from meridiana.i18n import setup
    setup('en')
    from meridiana.gui.backend.controls import install_controls
    from quick.aiuti import dissolvenza

    def pump():
        for _ in range(3):
            app.processEvents()

    def grab(window):
        window.grabWindow()
        app.processEvents()
        return window.grabWindow()

    def crop(image, item, dpr):
        at = item.mapToScene(QPointF(0, 0))
        return image.copy(int(round(at.x() * dpr)), int(round(at.y() * dpr)), int(round(item.width() * dpr)),
                          int(round(item.height() * dpr)))

    def differing(a, b):
        """How many pixels differ, and by how much at most (levels of 255 on a channel)."""
        if a.size() != b.size():
            return [-1, 255]
        count, most = 0, 0
        for y in range(a.height()):
            for x in range(a.width()):
                p, q = a.pixel(x, y), b.pixel(x, y)
                if p != q:
                    count += 1
                    most = max(most, *(abs((p >> s & 255) - (q >> s & 255)) for s in (0, 8, 16)))
        return [count, most]

    cases = {}
    for theme in ('dark', 'light'):
        engine = QQmlEngine()
        install_controls(engine, dict(theme=theme, reducedMotion=True))
        component = QQmlComponent(engine)
        component.setData(panel().encode(), QUrl.fromLocalFile(str(out / 'panel.qml')))
        root = component.create()
        if root is None:
            print(component.errorString())
            return 1
        root.setParent(engine)
        window = QQuickWindow()
        window.resize(int(root.width()), int(root.height()))
        root.setParentItem(window.contentItem())
        first = grab(window)
        # no graphics API: the software renderer, or an RHI that could not be made (Linux without a GPU: the window
        # still names OpenGL, its picture is empty)
        if first.isNull() or window.rendererInterface().graphicsApi() in (QSGRendererInterface.GraphicsApi.Software,
                                                                          QSGRendererInterface.GraphicsApi.Unknown):
            return NO_RHI
        dpr = window.devicePixelRatio()
        page = named(root, 'page')
        flick = page.property('contentItem')
        held = named(root, 'heldHeads')
        fades = next(it for it in items(root) if it.objectName() == 'edgeFades')
        heads = {k: named(root, f'head{k}') for k in range(4)}
        end = flick.property('contentHeight') - flick.height()
        # the same head in its place and held at the same place of the page: the first at the top (open), the last two
        # at the bottom (closed): at rest at the top, held when scrolled half way, in their places at the end
        flick.setProperty('contentY', 0)
        pump()
        rest = grab(window)
        places = {k: crop(rest, heads[k], dpr) for k in (0,)}
        held_at_rest = {k: crop(rest, named(root, f'held:head{k}'), dpr) for k in (2, 3)}
        flick.setProperty('contentY', end)
        pump()
        last = grab(window)
        places.update({k: crop(last, named(root, f'section{k}'), dpr) for k in (2, 3)})
        middle = 300
        flick.setProperty('contentY', middle)
        pump()
        drawn = grab(window)
        held_middle = crop(drawn, named(root, 'held:head0'), dpr)
        cases[f'{theme}-pixels'] = {'top': differing(places[0], held_middle),
                                    'bottom': [differing(places[k], held_at_rest[k]) for k in (2, 3)],
                                    'sizes': [places[0].width(), places[0].height(), held_middle.width(), held_middle.height()]}
        places[0].save(str(out / f'{theme}-in-place.png'))
        held_middle.save(str(out / f'{theme}-held.png'))
        # the frame of the open section held at the top: its left side inside the dissolve under the head and half way
        # down the page, and its foot closed over the heads held at the bottom, the colour of its line (no dissolve)
        top_inset, bottom_inset = held.property('topInset'), held.property('bottomInset')
        side = named(root, 'frame:head0')
        corner = side.mapToScene(QPointF(0, 0))
        column = int((corner.x() + .5) * dpr)
        page_top = flick.mapToScene(QPointF(0, 0)).y()

        def colour(x, y, image=drawn, dpr=dpr):
            return image.pixel(x, int(y * dpr))
        cases[f'{theme}-frame'] = {
            'band': [colour(column, page_top + top_inset + r + .5) for r in range(FADE)],
            'middle': colour(column, page_top + flick.height() / 2),
            'foot': colour(int((corner.x() + side.width() / 2) * dpr), corner.y() + side.height() - .5)}
        # the dissolve from the held heads' edges: as drawn, without the dissolve, the ground alone
        top_room, bottom_room = held.property('topRoom'), held.property('bottomRoom')
        fades.setProperty('flickable', None)
        pump()
        bare = grab(window)
        flick.setOpacity(0)          # not hidden: a hidden page has no section on show, and no held head
        pump()
        ground = grab(window)
        flick.setOpacity(1)
        fades.setProperty('flickable', flick)
        pump()
        here = flick.mapToScene(QPointF(0, 0))
        x0, x1 = int(here.x() * dpr) + 4, int((here.x() + flick.width()) * dpr) - 4
        top = int(round((here.y() + top_inset) * dpr))
        bottom = int(round((here.y() + flick.height() - bottom_inset) * dpr)) - 1
        rows = int(FADE * dpr * 1.5) + 6
        cases[f'{theme}-under-top'] = dict(band=min(FADE, top_room) * dpr, alpha=dissolvenza.opacity(
            drawn, bare, ground, x0, x1, top, rows))
        cases[f'{theme}-under-bottom'] = dict(band=min(FADE, bottom_room) * dpr, alpha=dissolvenza.opacity(
            drawn, bare, ground, x0, x1, bottom, rows, downward=False))
        # under the held heads, their air and their gaps: nothing of the content
        cases[f'{theme}-hidden'] = dissolvenza.opacity(drawn, bare, ground, x0, x1, int(round(here.y() * dpr)),
                                                       int(round(top_inset * dpr)))
        cases[f'{theme}-hidden-bottom'] = dissolvenza.opacity(drawn, bare, ground, x0, x1,
                                                              int((here.y() + flick.height()) * dpr) - 1,
                                                              int(round(bottom_inset * dpr)), downward=False)
        drawn.save(str(out / f'{theme}-drawn.png'))
        window.close()
        window.deleteLater()
        pump()
    (out / 'cases.json').write_text(json.dumps(cases), encoding='utf-8')
    return 0


class Drawn(unittest.TestCase):
    """B. The pictures made on a graphics API, judged here."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='rhi', QSG_RENDER_LOOP='basic',
                   QT_SCALE_FACTOR='2', PYTHONDONTWRITEBYTECODE='1')
        if sys.platform == 'win32':
            env.setdefault('QSG_RHI_BACKEND', 'd3d11')
        done = subprocess.run([sys.executable, '-m', 'quick.shell.test_testate_r633', '--render', cls.folder.name],
                              cwd=ROOT / 'tests', env=env, capture_output=True, text=True, timeout=600)
        if done.returncode == NO_RHI:
            raise unittest.SkipTest('Qt Quick has no graphics API here: the held heads are drawn without the dissolve')
        if done.returncode != 0:
            raise AssertionError(done.stdout[-3000:] + done.stderr[-3000:])
        cls.cases = json.loads((Path(cls.folder.name) / 'cases.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_a_held_head_is_the_same_at_the_pixel_as_in_its_place(self):
        # In its place the head is drawn through the page's layer (EdgeFades), an 8-bit texture of premultiplied
        # colours: a few pixels of the rounded corners' antialiasing come out one level off (measured 15/11/2026 on
        # Direct3D 11 at scale 2: 2 to 8 pixels of 656 x 50, one level of 255). Nothing else may differ.
        for theme in ('dark', 'light'):
            case = self.cases[f'{theme}-pixels']
            with self.subTest(theme=theme):
                for where, (count, most) in [('top', case['top'])] + [('bottom', b) for b in case['bottom']]:
                    self.assertLessEqual(most, 1, f'{where}: {case}')
                    self.assertLessEqual(count, 16, f'{where}: {case}')

    def test_the_frame_never_dissolves(self):
        # R633 (Daniel: «perché la dissolvenza prende pure il bordo della sottoscheda?»): the side of the frame inside the
        # dissolve under the held head, half way down, and its foot closed over the heads held at the bottom: one colour
        def levels(a, b):
            return max(abs((a >> s & 255) - (b >> s & 255)) for s in (0, 8, 16))
        for theme in ('dark', 'light'):
            case = self.cases[f'{theme}-frame']
            with self.subTest(theme=theme):
                self.assertLessEqual(max(levels(v, case['middle']) for v in case['band']), 1, case)
                self.assertLessEqual(levels(case['foot'], case['middle']), 1, case)

    def test_the_content_dissolves_from_the_held_heads_edge(self):
        from quick.aiuti import dissolvenza
        for theme in ('dark', 'light'):
            for edge in ('top', 'bottom'):
                case = self.cases[f'{theme}-under-{edge}']
                with self.subTest(theme=theme, edge=edge):
                    self.assertEqual(dissolvenza.judge(case['alpha'], case['band']), [])

    def test_nothing_of_the_content_under_the_held_heads(self):
        from quick.aiuti import dissolvenza
        for theme in ('dark', 'light'):
            for name in ('hidden', 'hidden-bottom'):
                seen = [v for v in self.cases[f'{theme}-{name}'] if v is not None]
                with self.subTest(theme=theme, edge=name):
                    self.assertTrue(seen, 'rows with content off the ground')
                    self.assertLessEqual(max(seen), dissolvenza.EDGE)


class OffScreen(unittest.TestCase):
    """A. The behaviour, off screen (no shader: the content is not hidden under the heads, the numbers say where)."""

    @classmethod
    def setUpClass(cls):
        import _setup
        cls.app = _setup.qt_or_skip()

    def scene(self, qml, theme='dark'):
        from PySide6.QtCore import QUrl
        from PySide6.QtQuick import QQuickView
        from meridiana.gui.backend.controls import install_controls
        from quick.gestures import pump
        view = QQuickView()
        install_controls(view.engine(), dict(theme=theme, reducedMotion=True))
        warnings = []
        view.engine().warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        with tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False) as file:
            file.write(qml.encode())
        self.addCleanup(os.unlink, file.name)
        view.setSource(QUrl.fromLocalFile(file.name))
        self.assertIsNotNone(view.rootObject(), view.errors())
        view.show()
        pump(100)

        def close():
            view.close()
            view.deleteLater()
            pump(20)
            self.assertEqual([w for w in warnings if 'HeldHeads' in w or 'Section' in w], [])
        self.addCleanup(close)
        root = view.rootObject()
        page = named(root, 'page')
        return view, root, page, page.property('contentItem'), named(root, 'heldHeads')

    @staticmethod
    def scroll(flick, y):
        from quick.gestures import pump
        flick.setProperty('contentY', y)
        pump(30)

    @staticmethod
    def y_in(item, ref):
        from PySide6.QtCore import QPointF
        return item.mapToItem(ref, QPointF(0, 0)).y()

    def copy(self, root, k):
        return named(root, f'held:head{k}')

    def test_at_rest_the_heads_below_the_page_wait_at_its_bottom(self):
        _view, root, _page, flick, held = self.scene(panel())
        self.assertFalse(self.copy(root, 0).isVisible(), 'the first head is in its place')
        H, air, gap = flick.height(), AIR, 6
        three, two = self.copy(root, 3), self.copy(root, 2)
        self.assertTrue(three.isVisible() and two.isVisible())
        self.assertAlmostEqual(self.y_in(three, flick) + three.height(), H - air, delta=.5)
        self.assertAlmostEqual(self.y_in(two, flick) + two.height() + gap, self.y_in(three, flick), delta=.5)
        # the first section, cut over the held heads, hides what scrolls from the gap above them down
        self.assertAlmostEqual(held.property('bottomInset'), H - self.y_in(self.copy(root, 1), flick) + gap, delta=.5)
        self.assertEqual(held.property('topInset'), 0)

    def test_the_head_that_leaves_the_page_stays_at_its_top(self):
        _view, root, _page, flick, held = self.scene(panel())
        self.scroll(flick, 300)
        first = self.copy(root, 0)
        self.assertTrue(first.isVisible())
        self.assertAlmostEqual(self.y_in(first, flick), AIR, delta=.5)
        self.assertAlmostEqual(held.property('topInset'), AIR + first.height(), delta=.5)
        own = named(root, 'head0')
        self.assertEqual((first.width(), first.height()), (own.width(), own.height()), 'the head of an open section')
        self.assertLess(self.y_in(own, flick), AIR + 1, 'its own head has gone past the top')

    def frame(self, root, k):
        return named(root, f'frame:head{k}')

    def test_the_frame_is_whole_from_the_head_to_the_edge_seen_and_closes_there(self):
        # R633 (Daniel: «perché la dissolvenza prende pure il bordo della sottoscheda?»): the page draws the frames of its
        # sections outside what scrolls (no frame of the section in the dissolving layer), from the head to its foot or to
        # the edge seen; the head's band is square while the body is seen under it
        _view, root, page, flick, held = self.scene(panel())
        self.assertIs(named(root, 'section0').property('framedByPage'), True)
        own = [it for it in items(flick) if it.metaObject().className().startswith('QQuickRectangle') and it.isVisible()
               and it.parentItem() is not None and it.parentItem().metaObject().className().startswith('SectionHead')]
        self.assertEqual(own, [], 'no frame of a section of the page inside what scrolls')
        gap = 6
        first = self.frame(root, 0)
        self.assertAlmostEqual(self.y_in(first, flick), AIR, delta=.5)
        self.assertAlmostEqual(self.y_in(first, flick) + first.height(), self.y_in(self.copy(root, 1), flick) - gap, delta=.5,
                               msg='the open section closes over the heads held at the bottom')
        self.assertEqual(named(root, 'section0').property('foot'), named(root, 'section0').property('radius'))
        self.scroll(flick, 300)
        self.assertAlmostEqual(self.y_in(first, flick), self.y_in(self.copy(root, 0), flick), delta=.5,
                               msg='its sides start at the held head')
        # at the end the last section is in its place: its frame is the section's own
        self.scroll(flick, flick.property('contentHeight') - flick.height())
        last = named(root, 'section3')
        self.assertAlmostEqual(self.y_in(self.frame(root, 3), flick), self.y_in(last, flick), delta=.5)
        self.assertAlmostEqual(self.frame(root, 3).height(), last.height(), delta=.5)

    def test_r638_past_the_ends_the_frames_and_heads_follow_the_content(self):
        # R638 (Daniel 15/11/2026: «il rimbalzo che si ha quando si scorre oltre il limite fa sì che i bordi delle
        # sottoschede si sballino completamente»): past the top and the end (a drag, a flick) and while the rebound of
        # the wheel moves the content (its own shift, Rebound.qml), the frames stand on their sections, on whole pixels
        from PySide6.QtCore import QObject
        _view, root, _page, flick, _held = self.scene(panel())
        end = flick.property('contentHeight') - flick.height()

        def on_their_sections():
            for k in range(4):
                frame, section = self.frame(root, k), named(root, f'section{k}')
                if not frame.isVisible() or self.copy(root, k).isVisible():
                    continue
                with self.subTest(contentY=flick.property('contentY'), section=k):
                    self.assertAlmostEqual(self.y_in(frame, flick), self.y_in(section, flick), delta=.5)
                    self.assertEqual(self.y_in(frame, flick), round(self.y_in(frame, flick)), 'a whole pixel')
        self.scroll(flick, -40)
        self.assertFalse(self.copy(root, 0).isVisible(), 'past the top the first head is in its place, lower')
        self.assertAlmostEqual(self.y_in(self.frame(root, 0), flick), AIR + 40, delta=.5)
        on_their_sections()
        self.scroll(flick, end + 40)
        on_their_sections()
        from PySide6.QtCore import Qt
        shifts = root.findChildren(QObject, 'reboundShift', Qt.FindChildOption.FindChildrenRecursively)
        self.assertEqual(len(shifts), 1, 'one rebound for the page (two moved it twice as far as the bar said)')
        shift = shifts[0]
        for at, by in ((0, 12), (end, -12)):
            self.scroll(flick, at)
            shift.setProperty('y', by)
            self.app.processEvents()
            on_their_sections()
            first = self.frame(root, 0)
            if at == 0:
                self.assertAlmostEqual(self.y_in(first, flick), AIR + by, delta=.5, msg='the rebound moves the frame too')
            shift.setProperty('y', 0)

    def test_the_frames_never_jump_while_the_page_scrolls(self):
        _view, root, _page, flick, _held = self.scene(panel())
        end = int(flick.property('contentHeight') - flick.height())
        before = None
        worst = (0, None)
        for y in range(0, end + 1):
            self.scroll(flick, y) if y % 50 == 0 else flick.setProperty('contentY', y)
            self.app.processEvents()
            now = []
            for k in range(4):
                f = self.frame(root, k)
                now.append((self.y_in(f, flick), self.y_in(f, flick) + f.height(), named(root, f'section{k}').property('foot')))
            if before is not None:
                for a, b in zip(before, now, strict=True):
                    step = max(abs(p - q) for p, q in zip(a, b, strict=True))
                    if step > worst[0]:
                        worst = (step, (y, a, b))
            before = now
        self.assertLessEqual(worst[0], 1.01, f'a frame or a foot jumped: {worst}')

    def test_the_dissolve_starts_at_the_held_heads_and_never_fades_a_head_in_its_place(self):
        _view, root, _page, flick, held = self.scene(panel())
        fades = named(root, 'edgeFades')
        self.scroll(flick, 300)
        self.assertEqual(fades.property('topInset'), held.property('topInset'))
        self.assertEqual(fades.property('bottomInset'), held.property('bottomInset'))
        self.assertEqual(fades.property('topBand'), FADE, 'the content gone under the head: the whole band')
        # the next head 10 px under the first, held: the dissolve no taller than the room left above it
        second = named(root, 'section1')
        top = self.y_in(second, flick.property('contentItem')) - held.property('topInset') - 10
        self.scroll(flick, top)
        self.assertFalse(self.copy(root, 1).isVisible())
        self.assertLessEqual(fades.property('topBand'), 10.5)
        # just scrolled from the top: as tall as the content gone under the head
        self.scroll(flick, 4)
        self.assertEqual(fades.property('topBand'), 4)

    def test_at_most_a_quarter_of_the_page_at_each_edge(self):
        _view, root, _page, flick, held = self.scene(panel(height=320, count=9, open_=4, rows=12))
        H = flick.height()
        share = int(H / 4)
        for y in (0, 200, 400, 600, 800, 1000):
            self.scroll(flick, y)
            with self.subTest(contentY=y):
                self.assertLessEqual(held.property('topInset'), share + .5)
                # at the bottom the gap above the held heads hides the cut section's content too (its frame closes there)
                self.assertLessEqual(held.property('bottomInset'), share + 6 + .5)
                self.assertGreaterEqual(H - held.property('topInset') - held.property('bottomInset'), H / 2 - 7)
        # past the share the farthest head at the top has gone up out of the page, the nearest stays
        self.scroll(flick, flick.property('contentHeight') - H)
        shown = [k for k in range(9) if self.copy(root, k).isVisible()]
        self.assertTrue(shown)
        self.assertLess(self.y_in(self.copy(root, shown[0]), flick), AIR, 'the farthest is pushed out at the top')

    def test_a_click_on_a_held_head_opens_its_section_and_brings_it_into_view(self):
        from quick.gestures import click, point, pump
        view, root, _page, flick, _held = self.scene(panel())
        last = self.copy(root, 3)
        click(self.app, view, point(last))
        pump(60)
        section = named(root, 'section3')
        self.assertTrue(section.property('expanded'))
        self.assertFalse(self.copy(root, 3).isVisible(), 'the head in its place again')
        head = named(root, 'head3')
        self.assertGreaterEqual(self.y_in(head, flick), 0)
        self.assertLess(self.y_in(head, flick) + head.height(), flick.height() / 2, 'its section under it, in view')

    def test_a_click_on_the_held_head_of_an_open_section_closes_it_where_it_stands(self):
        from quick.gestures import click, point, pump
        view, root, _page, flick, _held = self.scene(panel())
        self.scroll(flick, 300)
        first = self.copy(root, 0)
        at = self.y_in(first, flick)
        click(self.app, view, point(first))
        pump(60)
        self.assertFalse(named(root, 'section0').property('expanded'))
        self.assertAlmostEqual(self.y_in(named(root, 'head0'), flick), at, delta=.5, msg='the head stays put')

    def test_the_wheel_over_a_held_head_scrolls_the_page(self):
        from quick.gestures import point, wheel
        view, root, _page, flick, _held = self.scene(panel())
        wheel(self.app, view, point(self.copy(root, 3)), notches=2)
        self.assertGreater(flick.property('contentY'), 0)

    def test_tab_reaches_the_sections_own_heads_and_never_a_copy(self):
        from PySide6.QtCore import Qt
        from quick.gestures import key
        view, root, _page, flick, _held = self.scene(panel())
        self.scroll(flick, 300)
        seen = []
        for _ in range(16):
            key(self.app, view, Qt.Key.Key_Tab)
            focused = view.activeFocusItem()
            seen.append(focused.objectName() if focused is not None else '')
        self.assertTrue({'head0', 'head1', 'head2', 'head3'} <= set(seen), seen)
        self.assertFalse([name for name in seen if name.startswith('held')], seen)
        for k in range(4):
            copy = named(self.copy(root, k), f'held-head{k}')
            self.assertEqual(copy.property('focusPolicy'), Qt.FocusPolicy.NoFocus)

    def test_groups_inside_a_section_and_pages_that_are_not_a_panels_hold_nothing(self):
        _view, root, _page, flick, _held = self.scene(panel())
        names = {it.objectName() for it in items(named(root, 'heldHeads'))}
        self.assertFalse([n for n in names if 'Gruppo' in n or 'group' in n], names)
        plain = panel().replace('M.PanelPage {', 'M.ScrollPage {')
        _view, root, _page, flick, held = self.scene(plain)
        self.scroll(flick, 300)
        self.assertEqual((held.property('topInset'), held.property('bottomInset')), (0, 0))
        self.assertFalse([it for it in items(held) if it.objectName().startswith('held:') and it.isVisible()])


class Margins(unittest.TestCase):
    """C. The real window: in every side panel the bar centred in the room at the sections' right, the sections
    centred in the card."""

    def test_the_bar_is_centred_at_the_right_and_the_sections_in_the_card(self):
        import _setup
        from PySide6.QtCore import QPointF
        from meridiana import i18n
        from meridiana.app import jobs
        from meridiana.gui.application import QuickWindow, create_app
        from quick.aiuti.differential import connected_fixture
        from quick.gestures import pump, wait_for
        if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
            os.environ.setdefault('QSG_RENDER_LOOP', 'basic')       # as test_plant_side.py, for the plant's jobs
        self.addCleanup(i18n.setup, i18n.language())
        _setup.qt_or_skip()
        create_app()
        i18n.setup('en')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(folder.cleanup)
        host = QuickWindow(project, Path(folder.name), real_views=True, theme={'theme': 'light', 'reducedMotion': True})
        self.addCleanup(host.close)
        host.bridge.accept_layout(host.bridge.session.generation, results, keys)
        win = host.window
        win.resize(1400, 760)
        win.show()
        plant, actions = host.parts.controllers['plant'], host.parts.controllers['plantActions']

        def shown(node):
            if not node.isVisible() or node.width() <= 0 or node.height() <= 0:
                return
            yield node
            for child in node.childItems():
                yield from shown(child)

        measured = {}
        for phase in ('model', 'plant', 'production', 'consumption', 'economics', 'report'):
            host.shell.trigger('phase_' + phase)
            pump(900)
            scenes = [(phase, None)]
            if phase == 'plant':
                wait_for(lambda: not plant.busy and plant.units, 60)
                scenes = [('plant ' + key, key) for key in ('panels', 'inverter', 'storage')]
            for scene, key in scenes:
                if key:
                    actions.openSection(key)
                    pump(700)
                card = next(o for o in shown(win.contentItem()) if o.objectName() == 'rightPanel' and o.property('panelId'))
                page = next(o for o in shown(card) if o.property('panelBody') is True)
                flick = page.property('contentItem')
                column = flick.property('contentItem').childItems()[0]      # the page's column: the sections' width
                bar = next(c for c in page.childItems() if 'ScrollBar' in c.metaObject().className())
                thumb = next(c for c in bar.childItems() if c.width() > 0)
                left = column.mapToItem(card, QPointF(0, 0)).x()
                right = column.mapToItem(card, QPointF(column.width(), 0)).x()
                at = thumb.mapToItem(card, QPointF(0, 0)).x()
                measured[scene] = {'left': round(left, 2), 'section_thumb': round(at - right, 2),
                                   'thumb': round(thumb.width(), 2), 'thumb_card': round(card.width() - at - thumb.width(), 2),
                                   'bar_shown': bar.isVisible()}
        self.assertIn('model', measured)
        self.assertIn('report', measured)
        self.assertTrue(any(m['bar_shown'] for m in measured.values()) and not all(m['bar_shown'] for m in measured.values()),
                        f'some panels scroll, some do not: {measured}')
        for scene, m in measured.items():
            with self.subTest(scene=scene):
                # R704: the card's own line (HAIR, 1) is the outermost pixel of the margin: the thumb is centred in the
                # air, so as much air on the section's side as on the line's
                self.assertAlmostEqual(m['section_thumb'], m['thumb_card'] - 1, delta=.5, msg=m)
                self.assertAlmostEqual(m['left'], m['section_thumb'] + m['thumb'] + m['thumb_card'], delta=.5, msg=m)
                # R637, R655, R704: the thumb centred in the card's margin, at rest (cardMargin 13: 4 + 4 + 4 + the line)
                self.assertAlmostEqual(m['section_thumb'], 4, delta=.5, msg=m)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--render':
        sys.exit(render(Path(sys.argv[2])))
    unittest.main()
