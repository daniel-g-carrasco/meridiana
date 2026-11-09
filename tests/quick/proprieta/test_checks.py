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

from meridiana import checks, jobs, theme_colors
from meridiana.i18n import setup
from meridiana.quick.backend.checks import ChecksBackend, gather_session, install_checks, object_names
from meridiana.session import ProjectSession
from meridiana.ui.checks_page import ChecksPage
from quick.parity.differential import Adapter, canonical_project, normalized, run_scenario

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
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        setup("it")

    def setUp(self):
        self.session = ProjectSession(capannone())
        self.backend = ChecksBackend(self.session)
        self.backend._timer.stop()
        self.backend.show_items(sample(), [checks.Item("info", "defaults", "Valore predefinito")])
        self.addCleanup(self.backend.close)

    def test_gather_identical_core_and_live_plant(self):
        from meridiana.energy import system, plant
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
        self.backend._gathered(-1, ([], [], "wrong"), "")
        self.assertTrue(self.backend.items)
        self.backend.close()
        self.assertNotIn(self.backend._session_changed, self.session.listeners)

    def test_widget_filter_view_differential(self):
        widget = ChecksPage()
        self.addCleanup(lambda: delete(widget))
        widget.show_items(self.backend.items, self.backend.extras, object_names(self.session.project))
        widget._expand()

        def widget_snapshot():
            return {"items": sorted(n for n, row in widget.rows.items()
                                    if not row.isHidden() and row.parent().isExpanded())}

        def quick_snapshot():
            return {"items": sorted(row["itemIndex"] for row in self.backend.rows if not row["header"])}

        result = run_scenario({"id": "R130-R345-views-filters", "observations": ["items"], "steps": [
            {"command": "filter", "args": {"levels": ["fail", "warn"]}},
            {"command": "view", "args": {"view": "object"}},
            {"command": "view", "args": {"view": "area"}},
            {"command": "filter", "args": {"levels": []}},
            {"command": "view", "args": {"view": "delivery"}}]},
            Adapter("Widgets", {"filter": widget.set_levels, "view": widget.set_view}, widget_snapshot, widget._expand),
            Adapter("Quick", {"filter": self.backend.setLevels, "view": lambda view: self.backend.setView(view)}, quick_snapshot))
        self.assertEqual(result["status"], "equal", result)

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
        self.assertEqual(self.app.clipboard().text(), sample()[0].text + "\n" + sample()[0].detail)

    def test_fill_relayout_energy_fixes_and_undo(self):
        sf = self.session.subfield("s1")
        sf.filled = False
        fixes = [("action", "fill", "subfield", "s1"), ("action", "relayout", "subfield", "s1"),
                 ("energy", "strings", None)]
        self.session.project.energy["strings"] = {"auto": True}
        for fix in fixes:
            before = canonical_project(self.session.project)
            if fix[1] == "relayout":
                sf.manual = True
                before = canonical_project(self.session.project)
            self.backend.show_items([checks.Item("warn", "layout", "Fix", fix=fix, fix_label="Fix")])
            self.backend.requestFix(0)
            self.assertTrue(self.backend.preview)
            self.backend.answerPreview(False)
            self.assertEqual(canonical_project(self.session.project), before)
            sf = self.session.subfield("s1")

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
        QTest.keyClick(window, Qt.Key.Key_Period, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(self.backend.preview)
        drop = root.findChild(type(root), "checks-preview-drop")
        # The preview has just entered the layout. Click its polished position,
        # as a user does on the following frame, not its former hidden position.
        QTest.qWait(20)
        center = drop.mapToScene(drop.boundingRect().center())
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(round(center.x()), round(center.y())))
        self.assertFalse(self.backend.preview)

    def test_count_pill_pixels_and_click_filter(self):
        root, window, tokens = self.scene()
        pill = visual_item(root, "checks-filter-fail")
        pos = pill.mapToScene(QPointF(2, pill.height() / 2))
        image = window.grabWindow()
        dpr = image.devicePixelRatio()
        color = image.pixelColor(int((pos.x() + .5) * dpr), int((pos.y() + .5) * dpr))
        expected = QColor(theme_colors.mix(tokens.colors["window"], self.backend.symbols["fail"]["tone"], .10))
        for actual, target in zip(color.getRgb()[:3], expected.getRgb()[:3], strict=True):
            self.assertLessEqual(abs(actual - target), 2)
        center = pill.mapToScene(pill.boundingRect().center())
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(round(center.x()), round(center.y())))
        self.assertEqual(self.backend.levels, ["fail"])
        self.assertEqual([r["itemIndex"] for r in self.backend.rows if not r["header"]], [0])

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
        from meridiana.ui.title_tools import TitleTools

        class Hint:
            def __init__(self, width, height, minimum):
                self.size = QSize(round(width), round(height))
                self.minimum = QSize(round(minimum), round(height))
            def isHidden(self):
                return False
            def sizeHint(self):
                return self.size
            def minimumSizeHint(self):
                return self.minimum

        root, window, tokens = self.scene(1300, 300)
        window.setMinimumSize(QSize(0, 0))
        tools = visual_item(root, 'checks-tools')
        groups = [visual_item(root, name) for name in ('checks-views', 'checks-counts', 'checks-scopes', 'checks-notes')]
        oracle = TitleTools()
        self.addCleanup(oracle.deleteLater)
        for size in ('medium', 'large'):
            tokens.configure({'textSize': size})
            for width in (420, 900, 1300):
                with self.subTest(size=size, width=width):
                    root.setWidth(width); window.resize(width, 300)
                    QTest.qWait(30)
                    specs = [(groups[0].implicitWidth(), groups[0].height(), 120, 'start'),
                             (groups[1].width(), groups[1].height(), groups[1].width(), 'start'),
                             (groups[2].width(), groups[2].height(), groups[2].width(), 'end'),
                             (20, 20, 20, 'tail')]
                    oracle.items = [(Hint(w, h, least), align) for w, h, least, align in specs]
                    matching = dict(zip([item for item, _align in oracle.items], groups, strict=True))
                    placed, _ = oracle.plan(round(tools.width()), 0, 28)
                    for hint, rect in placed:
                        quick = matching[hint]
                        self.assertLessEqual(abs(rect.x()-quick.x()), 2)
                        self.assertLessEqual(abs(rect.y()-quick.y()), 1)
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
        widget = ChecksPage()
        self.addCleanup(lambda: delete(widget))
        self.assertEqual(self.backend.labels['phaseTip'], widget.phase_button.toolTip())
        self.assertEqual(self.backend.labels['objectTip'], widget.object_button.toolTip())
        self.assertEqual(self.backend.labels['copyNotesTip'], widget.copy_button.toolTip())
        for row in self.backend.rows:
            if not row['header']:
                self.assertEqual(row['eyeTip'], widget._eye_tip(self.backend.items[row['itemIndex']]))

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
        line = colour(left+8, top+10)
        card = colour(left+12, top+10)
        self.assertGreater(abs(line.lightness()-card.lightness()), 5)
        for y in range(round(top+8), round(bottom-8)):
            self.assertLessEqual(abs(colour(left+8, y).lightness()-line.lightness()), 3, f'Broken border at y={y}')

    def test_scroll_fades_follow_the_viewport_and_only_cover_hidden_content(self):
        self.backend.show_items([checks.Item('fail', 'layout', f'Verifica {n}') for n in range(24)])
        root, window, _ = self.scene(900, 260)
        view = visual_item(root, 'checks-list')
        top = visual_item(root, 'scroll-fade-top')
        bottom = visual_item(root, 'scroll-fade-bottom')
        view.setProperty('contentY', 0)
        _setup.wait_for(lambda: not top.isVisible() and bottom.isVisible(), 5000)
        self.assertFalse(top.isVisible())
        self.assertTrue(bottom.isVisible())
        anchor = bottom.mapToScene(QPointF())
        view.setProperty('contentY', 80)
        _setup.wait_for(lambda: top.isVisible() and bottom.isVisible(), 5000)
        self.assertTrue(top.isVisible())
        self.assertTrue(bottom.isVisible())
        self.assertEqual(bottom.mapToScene(QPointF()), anchor, 'Fade stays over the viewport, not its scrolling content')
        shown = window.grabWindow()
        top.setVisible(False)
        QTest.qWait(20)
        bare = window.grabWindow()
        dpr = shown.devicePixelRatio()
        y = top.mapToScene(QPointF()).y()
        strip = (0, round(y*dpr), round(view.width()*dpr), round(top.height()*dpr))
        self.assertNotEqual(shown.copy(*strip), bare.copy(*strip), 'The visible fade must alter clipped row pixels')
        view.setProperty('contentY', view.property('contentHeight') - view.height())
        _setup.wait_for(lambda: not bottom.isVisible(), 5000)
        self.assertFalse(bottom.isVisible())

    @unittest.skipUnless(os.environ.get("MERIDIANA_CHECKS_PHOTOS"), "Explicit native screenshot matrix")
    def test_native_screenshots(self):
        from meridiana.config import Config
        from meridiana.ui import sections
        from meridiana.ui.theme import Theme
        old_title = sections._TITLE[0]
        self.addCleanup(lambda: sections._TITLE.__setitem__(0, old_title))
        folder = Path("build/quick-foto/proprieta")
        folder.mkdir(parents=True, exist_ok=True)
        for dark in (False, True):
            look = Theme(Config(theme="dark" if dark else "light", accent="indigo", backgrounds="grey",
                                font="plex"), app=self.app)
            self.addCleanup(lambda look=look: delete(look))
            sections.set_colours(look.tokens)
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
                    widget = ChecksPage()
                    widget.set_colours(look.tokens)
                    widget.show_items(self.backend.items, self.backend.extras, self.backend.names)
                    widget.resize(width, height)
                    widget.setMinimumSize(width, height)
                    widget.show()
                    widget.resize(width, height)
                    widget.rows[0].setExpanded(self.backend._memory(self.backend.items[0]) in self.backend._opened)
                    QTest.qWait(100)
                    self.assertTrue(widget.grab().save(str(folder / (name + "-widgets.png"))))
                    widget.close()
                    delete(widget)
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
                QTest.qWait(chance.choice((0, 5, 40)))
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
