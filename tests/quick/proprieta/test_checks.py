"""Checks parity and real Quick gestures: R30, R125-130, R138, R153, R335, R345."""
import os
from pathlib import Path
import unittest

import _setup
from _fixtures import capannone
from PySide6.QtCore import QPoint, QPointF, QSize, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

from meridiana.core.rules import checks
from meridiana.app import jobs
from meridiana.app.interface import theme_colors
from meridiana.i18n import setup
from meridiana.app.checks_job import gather_session
from meridiana.gui.backend.checks import ChecksBackend, install_checks
from meridiana.app.session import ProjectSession
from quick.aiuti import riferimenti
from quick.aiuti.differential import canonical_project, normalized
from quick.aiuti.caratteri import GLYPH_PX

setUpModule = _setup.keep_global_state


def sample():
    return [checks.Item("fail", "layout", "Falda: errore di posa", "Riferimento della verifica", ("subfield", "s1"),
                        ("edit", "subfield", "s1", {"params.shade_free": True}), "Evita le ombre",
                        "Il dettaglio spiega il risultato e descrive come correggere la posa dei moduli."),
            checks.Item("warn", "strings", "Verificare le stringhe", "Fonte", ("phase", "plant"),
                        ("compute",), "Calcola", "Calcolare i risultati prima della consegna."),
            checks.Item("info", "rules", "Nota per la relazione", "Fonte della nota", ("site",), detail="Nota completa."),
            checks.Item("ok", "layout", "Verifica superata", target=("subfield", "s1"))]


def visual_item(root, name):
    if root.objectName() == name:
        return root
    for child in root.childItems():
        found = visual_item(child, name)
        if found is not None:
            return found
    return None


class ChecksTest(unittest.TestCase):
    def test_selecting_a_check_does_not_rebuild_the_view_controls(self):
        root, _window, _tokens = self.scene(900, 500)
        views = visual_item(root, 'checks-views')
        resets = []
        views.modelChanged.connect(lambda: resets.append(True))
        self.backend.selectRow(1)
        QTest.qWait(50)
        self.assertEqual(self.backend.currentIndex, 1)
        self.assertEqual(resets, [], 'Selecting a check leaves the grouping controls intact')

    def test_scrolling_does_not_read_the_full_python_rows_for_each_index(self):
        import sys
        self.backend.show_items([checks.Item('fail', 'layout', f'Check {i}') for i in range(160)])
        root, _window, _tokens = self.scene(900, 500)
        reads = []
        def count(frame, event, arg):
            if event == 'call' and frame.f_code.co_name == 'rows' and frame.f_code.co_filename.endswith('checks.py'):
                reads.append(1)
        previous = sys.getprofile()
        sys.setprofile(count)
        try:
            self.backend.selectRow(159)
            QTest.qWait(100)
        finally:
            sys.setprofile(previous)
        self.assertLessEqual(len(reads), 4, 'Scroll from the retained QML rows, without converting all Python rows repeatedly')
        view = visual_item(root, 'checks-list')
        self.assertEqual(self.backend.currentIndex, 159)
        self.assertGreater(view.property('contentY'), 0)

    def test_changing_delivery_view_keeps_the_same_check_delegate(self):
        self.backend.show_items([checks.Item('fail', 'layout', 'A check to fix', target=('site',))])
        root, _window, _tokens = self.scene(900, 500)
        before = visual_item(root, 'checks-row-0')
        self.assertIsNotNone(before)
        self.backend.setView('delivery')
        QTest.qWait(100)
        self.assertEqual(visual_item(root, 'checks-row-0'), before)
        self.backend.setView('level')
        QTest.qWait(100)
        self.assertEqual(visual_item(root, 'checks-row-0'), before)

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        setup("it")

    def setUp(self):
        self.session = ProjectSession(capannone())
        self.backend = ChecksBackend(self.session)
        self.backend.feed.cancel()          # the rows of the sample, not those of the job (it has not started yet)
        self.backend.show_items(sample(), [checks.Item("info", "defaults", "Valore predefinito")])
        self.addCleanup(self.backend.close)

    def test_gather_identical_core_and_live_plant(self):
        from meridiana.core.energy import system, plant
        results, _, _ = jobs.layout_of(self.session.project)
        project = self.session.project
        arrays = system.arrays_of(project, results)
        inverter = system.combined(system.inverters_of(project, sum(a.p_stc for a in arrays)))
        live = plant.build(project, results)
        expected = checks.gather(project, results, {}, inverter, bool(system.inverter_entries(project.energy)))
        expected += checks.plant_items(live)
        expected.sort(key=lambda item: checks.LEVELS.index(item.level))
        actual, _, notes = gather_session(project, results, {}, live)
        self.assertEqual(normalized(expected), normalized(actual))
        self.assertTrue(notes)

    def test_async_refresh_stale_result_and_dispose(self):
        self.backend.refresh()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, 30))
        self.assertFalse(self.backend.error)
        self.assertTrue(self.backend.items)
        # an answer that is not of the inputs in hand (here: of none) is never shown, and the checks are asked again
        feed = self.backend.feed
        wrong = dict(feed.result, items=[], extras=[], notes="wrong")
        feed._asked = None
        feed._done(wrong, False)
        self.assertTrue(self.backend.items)
        self.assertTrue(feed.busy(), "asked again")
        feed.cancel()
        self.backend.close()
        self.assertNotIn(self.backend._session_changed, self.session.listeners)

    def test_widget_filter_view_differential(self):
        # the rows the Widgets' Checks page showed for the same filters and views (recorded on 10/11/2026)
        def quick_snapshot():
            return sorted(row["itemIndex"] for row in self.backend.rows if not row["header"])
        for command, value in (("filter", ["fail", "warn"]), ("view", "object"), ("view", "area"), ("filter", []),
                               ("view", "delivery")):
            self.backend.setLevels(value) if command == "filter" else self.backend.setView(value)
            riferimenti.check(self, quick_snapshot())

    def test_detail_persists_filters_object_and_marks(self):
        self.backend.toggleDetail(0)
        self.backend.setView("area")
        self.assertTrue(next(row for row in self.backend.rows if row["itemIndex"] == 0)["expanded"])
        self.backend.setLevels(["warn"])
        self.assertEqual(self.backend.currentIndex, 1)
        self.backend.setLevels([])
        self.session.select("subfield", "s1")
        self.backend.setObjectOnly(True)
        self.assertEqual({r["itemIndex"] for r in self.backend.rows if not r["header"]}, {0, 3})
        self.assertEqual(next(m for m in self.backend.marks if m["kind"] == "subfield")["level"], "fail")
        self.backend.setObjectOnly(False)
        self.backend.setPhase("plant")
        self.backend.setPhaseOnly(True)
        self.assertEqual({r["itemIndex"] for r in self.backend.rows if not r["header"]},
                         set(checks.in_phase(self.backend.items, "plant")))

    def test_fix_preview_take_back_keep_and_intervening_edit(self):
        before = canonical_project(self.session.project)
        self.backend.requestFix(0)
        self.assertTrue(self.backend.preview["applied"])
        self.assertTrue(self.session.subfield("s1").params["shade_free"])
        self.backend.answerPreview(False)
        self.assertEqual(canonical_project(self.session.project), before)
        self.assertFalse(self.session.undo.can_redo())
        self.backend.requestFix(0)
        self.backend.answerPreview(True)
        self.assertTrue(self.session.undo.can_undo())
        self.session.undo.undo()
        self.backend.requestFix(0)
        self.session.edit("Rename", lambda p: setattr(p, "name", "New name"))
        self.assertFalse(self.backend.preview)
        self.backend.answerPreview(False)
        self.assertEqual(self.session.project.name, "New name")

    def test_compute_waits_for_confirmation_and_copy(self):
        called = []
        self.backend.computeRequested.connect(lambda: called.append(True))
        self.backend.requestFix(1)
        self.assertFalse(called)
        self.backend.answerPreview(False)
        self.assertFalse(called)
        self.backend.requestFix(1)
        self.backend.answerPreview(True)
        self.assertEqual(called, [True])
        self.backend.copyText(0)
        self.assertEqual(self.app.clipboard().text(), sample()[0].text + "\n" + sample()[0].detail + "\n" + sample()[0].source)

    def test_fill_relayout_energy_fixes_and_undo(self):
        # the project made ready through session.edit, as the program changes it: a project written behind the
        # session's back leaves its photo behind (MERIDIANA_CHECK_PHOTO, R598 step 2), and the fix's own edit says so
        def s1(project):
            return next(sf for sf in project.subfields if sf.id == "s1")

        def ready(project):
            s1(project).filled = False
            project.energy["strings"] = {"auto": True}
        self.session.edit("Ready", ready)
        fixes = [("action", "fill", "subfield", "s1"), ("action", "relayout", "subfield", "s1"),
                 ("energy", "strings", None)]
        for fix in fixes:
            if fix[1] == "relayout":
                self.session.edit("Manual", lambda p: setattr(s1(p), "manual", True))
            before = canonical_project(self.session.project)
            self.backend.show_items([checks.Item("warn", "layout", "Fix", fix=fix, fix_label="Fix")])
            self.backend.requestFix(0)
            self.assertTrue(self.backend.preview)
            self.backend.answerPreview(False)
            self.assertEqual(canonical_project(self.session.project), before)
            self.session._check_photo()         # the fix and its cancel leave the photo the project in hand

    def scene(self, width=1366, height=900, dark=False):
        engine = QQmlEngine()
        tokens = install_checks(engine, self.backend, {"theme": "dark" if dark else "light"})
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        component = QQmlComponent(engine)
        component.setData(b'import QtQuick\nimport Meridiana.Checks\nChecksPage { backend: checksBackend }', QUrl())
        self.assertFalse(component.isError(), "\n".join(e.toString() for e in component.errors()))
        root = component.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in component.errors()))
        root.setParent(engine)
        window = QQuickWindow()
        window.setMinimumSize(QSize(width, height))
        window.resize(width, height)
        root.setWidth(width)
        root.setHeight(height)
        root.setParentItem(window.contentItem())
        window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        # Windows constrains the initial show to the work area at high DPI.
        # An explicit resize after exposure preserves the requested test viewport.
        window.resize(width, height)
        QTest.qWait(100)

        def cleanup():
            window.close()
            delete(root)
            delete(window)
            delete(engine)
            self.assertEqual(warnings, [])
        self.addCleanup(cleanup)
        return root, window, tokens

    def test_real_quick_keyboard_and_pointer(self):
        root, window, _ = self.scene()
        view = root.findChild(type(root), "checks-list")
        self.assertIsNotNone(view)
        view.setProperty("currentIndex", 1)
        view.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        self.assertTrue(next(r for r in self.backend.rows if r["itemIndex"] == 0)["expanded"])
        shown = []
        self.backend.focusRequested.connect(shown.append)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(shown[-1], ["subfield", "s1"])
        before = canonical_project(self.session.project)
        QTest.keyClick(window, Qt.Key.Key_Period, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(self.backend.preview)
        drop = root.findChild(type(root), "checks-preview-drop")
        # Wait for the preview's layout to reach a rendered frame before hit testing it.
        frames = []
        window.frameSwapped.connect(lambda: frames.append(True))
        window.requestUpdate()
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(frames) and drop.isVisible(), 5))
        center = drop.mapToScene(drop.boundingRect().center())
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(round(center.x()), round(center.y())))
        self.assertFalse(self.backend.preview)
        self.assertEqual(canonical_project(self.session.project), before)

    def test_count_pill_pixels_and_click_filter(self):
        root, window, tokens = self.scene()
        pill = visual_item(root, "checks-filter-fail")
        pos = pill.mapToScene(QPointF(2, pill.height() / 2))
        image = window.grabWindow()
        dpr = image.devicePixelRatio()
        color = image.pixelColor(int((pos.x() + .5) * dpr), int((pos.y() + .5) * dpr))
        # R664: with no filter every level is shown, its count on: the level's tone at 19 % (status_pill.tints, "on")
        expected = QColor(theme_colors.mix(tokens.colors["window"], self.backend.symbols["fail"]["tone"], .19))
        for actual, target in zip(color.getRgb()[:3], expected.getRgb()[:3], strict=True):
            self.assertLessEqual(abs(actual - target), 2)
        center = pill.mapToScene(pill.boundingRect().center())
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(round(center.x()), round(center.y())))
        # R664: a click on a lit count hides its level (it was: shows that level alone)
        self.assertNotIn("fail", self.backend.shownLevels)
        self.assertNotIn("fail", [r["level"] for r in self.backend.rows if not r["header"]])

    def test_narrow_large_text_layout(self):
        root, window, tokens = self.scene(420, 640)
        tokens.configure({"textSize": "large"})
        self.backend.toggleDetail(0)
        QTest.qWait(50)
        for name in ("checks-filter-fail", "checks-object", "checks-notes"):
            item = visual_item(root, name)
            left = item.mapToScene(QPointF()).x()
            self.assertGreaterEqual(left, 0)
            self.assertLessEqual(left + item.width(), window.width())
        self.assertFalse(window.grabWindow().isNull())
        if os.environ.get("MERIDIANA_CHECKS_PHOTOS"):
            folder = Path("build/quick-foto/proprieta")
            folder.mkdir(parents=True, exist_ok=True)
            window.grabWindow().save(str(folder / "checks-narrow-large.png"))

    def test_empty_message_fits_after_wrapped_header(self):
        self.backend.show_items([])
        self.assertEqual(self.backend.emptyMessage, 'Ancora niente di calcolato.')
        root, window, tokens = self.scene(420, 220)
        tokens.configure({'textSize': 'large'})
        QTest.qWait(50)
        empty = root.findChild(type(root), 'checks-empty')
        top = empty.mapToScene(QPointF()).y()
        self.assertGreater(empty.height(), 12)
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(top + empty.height(), window.height())
        self.assertGreaterEqual(empty.parentItem().height(), empty.height())

    def test_title_groups_follow_widgets_wrapping_and_keep_copy_on_first_row(self):
        # where the Widgets' title bar put the same groups (recorded on 10/11/2026): within 2 px across, 1 down
        root, window, tokens = self.scene(1300, 300)
        window.setMinimumSize(QSize(0, 0))
        groups = [visual_item(root, name) for name in ('checks-views', 'checks-counts', 'checks-scopes', 'checks-notes')]
        for size in ('medium', 'large'):
            tokens.configure({'textSize': size})
            for width in (420, 900, 1300):
                with self.subTest(size=size, width=width):
                    root.setWidth(width); window.resize(width, 300)
                    QTest.qWait(30)
                    # the Widgets' wrap was DirectWrite's: with FreeType's advances the groups wrap at other widths
                    # (a group 440 px apart, not a pixel), so outside Windows only what follows is asserted
                    # (quick/aiuti/caratteri.py)
                    if not GLYPH_PX:
                        riferimenti.check(self, [group.x() for group in groups], absolute=2)
                        riferimenti.check(self, [group.y() for group in groups], absolute=1)
                    self.assertLess(groups[3].y(), 28, 'Copy stays beside Close, even when filters wrap')
                    boxes = [item.mapRectToScene(item.boundingRect()) for item in groups]
                    for i, box in enumerate(boxes):
                        self.assertTrue(all(not box.intersects(other) for other in boxes[i+1:]))
        self.backend.setLevels(['fail'])
        self.assertEqual(self.backend.emptyMessage, 'Nessuna verifica corrisponde a questo filtro.')

    def test_collapsed_groups_keep_source_column_width(self):
        root, window, _ = self.scene()
        width = root.property('sourceWidth')
        self.assertGreater(width, 0)
        for row in list(self.backend.rows):
            if row['header'] and row['expanded']:
                self.backend.toggleGroup(row['key'])
        _setup.wait_for(lambda: root.property('sourceWidth') == width, 5000)
        self.assertEqual(root.property('sourceWidth'), width)

    def test_group_and_row_share_widgets_symbol_and_text_columns(self):
        self.backend.show_items([checks.Item('fail', 'layout', 'Prima verifica')])
        root, _window, _ = self.scene(900, 260)
        title = visual_item(root, 'checks-text-0')
        group = visual_item(root, 'checks-group-text-level|fail')
        symbol = visual_item(root, 'checks-symbol-0')
        group_symbol = visual_item(root, 'checks-group-symbol-level|fail')
        self.assertIsNotNone(title)
        self.assertIsNotNone(group)
        self.assertLessEqual(abs(title.mapToScene(QPointF()).x()-group.mapToScene(QPointF()).x()), 1)
        self.assertLessEqual(abs(symbol.mapToScene(QPointF()).x()-group_symbol.mapToScene(QPointF()).x()), 1)

    def test_tooltips_match_widgets_destinations_and_filters(self):
        # the tooltips of the Widgets' Checks page (recorded on 10/11/2026)
        labels = {key: self.backend.labels[key] for key in ('phaseTip', 'objectTip', 'copyNotesTip')}
        eyes = [row['eyeTip'] for row in self.backend.rows if not row['header']]
        riferimenti.check(self, {'labels': labels, 'eyes': eyes})


    def test_group_card_border_continues_through_the_join_between_rows(self):
        self.backend.show_items([checks.Item('fail', 'layout', 'First'), checks.Item('fail', 'layout', 'Second')])
        root, window, _ = self.scene(900, 260)
        first, last = [visual_item(root, 'checks-row-' + str(n)) for n in (0, 1)]
        shot = window.grabWindow()
        dpr = shot.devicePixelRatio()
        top = first.mapToScene(QPointF()).y()
        left = first.mapToScene(QPointF()).x()
        bottom = last.mapToScene(QPointF(0, last.height())).y()
        def colour(x, y):
            return shot.pixelColor(int((x+.5)*dpr), int((y+.5)*dpr))
        # R637: the group's card as wide as the list (the card's margin round the list is the panel's)
        line = colour(left, top+10)
        card = colour(left+4, top+10)
        self.assertGreater(abs(line.lightness()-card.lightness()), 5)
        for y in range(round(top+8), round(bottom-8)):
            self.assertLessEqual(abs(colour(left, y).lightness()-line.lightness()), 3, f'Broken border at y={y}')

    def test_scroll_fades_follow_the_viewport_and_only_cover_hidden_content(self):
        self.backend.show_items([checks.Item('fail', 'layout', f'Verifica {n}') for n in range(24)])
        root, window, _ = self.scene(900, 260)
        # R624: the rows dissolve into the panel at an edge with more checks beyond it (the drawn shape, Daniel's
        # picture of the Checks scrolled half way: quick/controlli/test_dissolvenza_r624.py)
        view = visual_item(root, 'checks-list')
        fades = visual_item(root, 'edgeFades')
        self.assertIsNotNone(fades, 'the bar of the list brings the common soft ends')

        def ends():
            return fades.property('topBand') > 0, fades.property('bottomBand') > 0
        view.setProperty('contentY', 0)
        _setup.wait_for(lambda: ends() == (False, True), 5000)
        self.assertEqual(ends(), (False, True))
        anchor = fades.mapToScene(QPointF())
        view.setProperty('contentY', 80)
        _setup.wait_for(lambda: ends() == (True, True), 5000)
        self.assertEqual(ends(), (True, True))
        self.assertEqual(fades.mapToScene(QPointF()), anchor, 'the soft ends stay on the viewport, not on its content')
        self.assertEqual(fades.width(), view.width())
        view.setProperty('contentY', view.property('contentHeight') - view.height())
        _setup.wait_for(lambda: ends() == (True, False), 5000)
        self.assertEqual(ends(), (True, False))

    @unittest.skipUnless(os.environ.get("MERIDIANA_CHECKS_PHOTOS"), "Explicit native screenshot matrix")
    def test_native_screenshots(self):
        folder = Path("build/quick-foto/proprieta")
        folder.mkdir(parents=True, exist_ok=True)
        for dark in (False, True):
            for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
                with self.subTest(dark=dark, width=width):
                    root, window, tokens = self.scene(width, height, dark)
                    self.backend.toggleDetail(0)
                    QTest.qWait(100)
                    name = f"checks-{'dark' if dark else 'light'}-{width}-x{window.devicePixelRatio():g}"
                    image = window.grabWindow()
                    self.assertEqual((image.width(), image.height()),
                                     (round(width * image.devicePixelRatio()), round(height * image.devicePixelRatio())))
                    self.assertTrue(image.save(str(folder / (name + ".png"))))
                    window.close()


class GroupsStayInPlaceTest(unittest.TestCase):
    """R450 (Daniel, 05/11: «un miscuglio tra tutte le schede»): opening and closing the groups never draws a heading
    over the rows, never shows a row twice and every row shows its own check."""

    setUpClass = ChecksTest.__dict__['setUpClass']
    setUp, scene = ChecksTest.setUp, ChecksTest.scene

    def rows_on_screen(self, view):
        content = view.property('contentItem')      # a delegate taken away (index -1) waits for its deleteLater
        return sorted((d for d in content.childItems() if d.objectName().startswith('checks-') and d.isVisible() and d.property('index') >= 0),
                      key=lambda d: d.y())

    def test_toggling_groups_keeps_rows_apart_and_each_in_its_place(self):
        import random
        items = []
        for n in range(6):
            items += [checks.Item('fail', 'layout', f'Ombreggiamento {n}', 'Fonte lunga della verifica ' * 3,
                                  ('subfield', 's1'), detail='Dettaglio della verifica.'),
                      checks.Item('warn', 'energy', f'Producibilità: note di calcolo {n}', 'Fonte', ('site',)),
                      checks.Item('info', 'rules', f'Nota {n}', 'Fonte della nota', ('site',)),
                      checks.Item('ok', 'strings', f'Stringhe {n}', target=('phase', 'plant'))]
        self.backend.show_items(items)
        root, _window, _ = self.scene(900, 320)
        view = visual_item(root, 'checks-list')
        content = view.property('contentItem')
        chance = random.Random(450)
        for view_name in ('level', 'object', 'area'):
            self.backend.setView(view_name)
            QTest.qWait(40)
            for step in range(24):
                headers = [r for r in self.backend.rows if r['header']]
                # scrolled anywhere, as in a panel of a few rows: a group above the viewport changes too
                view.setProperty('contentY', chance.uniform(0, max(0, view.property('contentHeight') - view.height())))
                self.backend.toggleGroup(chance.choice(headers)['key'])
                QTest.qWait(chance.choice((0, 5, 40)))  # wait: random rests between the gestures, on purpose
                QTest.qWait(30)
                # the photo of 06/11: an opening arrow under the card, left of it: nothing of a row taken away is drawn
                gone = [d.objectName() for d in content.childItems()
                        if d.objectName().startswith('checks-') and d.isVisible() and d.property('index') < 0]
                self.assertEqual(gone, [], f'{view_name}, step {step}: rows taken away still drawn')
                shown = self.rows_on_screen(view)
                rows = self.backend.rows
                texts = []
                for delegate in shown:
                    data = delegate.property('modelData').toVariant() if hasattr(delegate.property('modelData'), 'toVariant') else delegate.property('modelData')
                    index = delegate.property('index')
                    self.assertLess(index, len(rows), (view_name, step))
                    want = rows[index]
                    self.assertEqual((data['header'], data.get('key'), data.get('itemIndex')),
                                     (want['header'], want.get('key'), want.get('itemIndex')),
                                     f'{view_name}, step {step}: row {index} shows another row')
                    texts.append((data['header'], data.get('key'), data.get('itemIndex')))
                self.assertEqual(len(texts), len(set(texts)), f'{view_name}, step {step}: a row shown twice')
                for above, below in zip(shown, shown[1:], strict=False):
                    self.assertGreaterEqual(below.y(), above.y() + above.height() - 0.5,
                                            f'{view_name}, step {step}: {below.objectName()} drawn over {above.objectName()}')
