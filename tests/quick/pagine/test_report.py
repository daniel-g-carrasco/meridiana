"""R61/R314/R329: real report edits, asynchronous PDFs, and the choices as the Widgets made them."""
import io
import os
from pathlib import Path
import tempfile
import time
import unittest

import _setup
from _fixtures import capannone
from meridiana.app.platform.config import Config
from meridiana.app.session import ProjectSession
from quick.aiuti.differential import undo_snapshot


setUpModule = _setup.keep_global_state


def report_pages_drawn():
    from meridiana.gui.backend import report_pages
    return list(report_pages.drawn)


def pdf_content_bytes(path):
    """Drop only volatile XMP timestamps/IDs: content, resources, fonts and page trees remain."""
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(path)
    reader.trailer["/Root"].pop("/Metadata", None)
    reader.trailer.pop("/ID", None)
    for key in ("/CreationDate", "/ModDate", "/MeridianaFingerprint", "/MeridianaExported"):
        reader.trailer["/Info"].pop(key, None)
    writer = PdfWriter(clone_from=reader)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class ReportBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.gui.backend.report import ReportBackend
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.session = ProjectSession(capannone())
        self.backend = ReportBackend(self.session, Config(), paths={"cache": self.temp.name})
        self.addCleanup(self.backend.close)

    def test_report_choices_match_widgets_and_undo_keeps_unknown_fields(self):
        # after every choice, the project and the undo the Widgets had for the same choices (recorded on 10/11/2026)
        from quick.aiuti import riferimenti
        self.session.project.report = {"future": {"keep": True}}
        for key, value in [("template", "compact"), ("client", "Cliente prova"), ("revision", "Rev. 2"),
                           ("address", False), ("register", True), ("profile", ""), ("off", ["monthly"])]:
            self.backend.setSetting(key, value)
            riferimenti.check(self, {"project": riferimenti.project(self.session.project),
                                     "undo": undo_snapshot(self.session)})
        self.session.undo.undo()
        self.assertEqual(self.backend.settings["off"], [])
        self.assertEqual(self.session.project.report["future"], {"keep": True})

    def test_invalid_template_and_chapter_do_not_mutate_project(self):
        before = self.session.snapshot()
        self.backend.setSetting("template", "unknown")
        self.assertTrue(self.backend.error)
        self.backend.setChapter("unknown", False)
        self.assertEqual(self.session.snapshot(), before)

    def test_attachment_order_title_removal_and_missing_reason(self):
        from pypdf import PdfWriter
        a = Path(self.temp.name) / "first.pdf"
        with a.open("wb") as stream:
            writer = PdfWriter()
            writer.add_blank_page(120, 200)
            writer.write(stream)
        missing = str(Path(self.temp.name) / "missing.pdf")
        self.backend.addAttachments([str(a), missing, str(a)])
        self.assertTrue(_setup.wait_until(self.app, lambda: len(self.backend.attachments) == 2
                                         and self.backend.attachments[0]["pages"] == 1))
        self.assertTrue(self.backend.attachments[1]["problem"])
        self.backend.retitleAttachment(0, "Scheda modulo")
        self.backend.moveAttachment(0, 1)
        self.assertEqual(self.backend.settings["attachments"][1]["title"], "Scheda modulo")
        self.backend.removeAttachment(0)
        self.assertEqual(len(self.backend.settings["attachments"]), 1)
        self.session.undo.undo()
        self.assertEqual(len(self.backend.settings["attachments"]), 2)

    def test_process_export_matches_widgets_pdf_and_preview_is_not_partial(self):
        from _fixtures import clear_sky_meteo, write_cache
        from meridiana.core.rules import checks, rules
        from meridiana.app import jobs
        from meridiana.app import pipeline
        from meridiana.core.energy import system
        from meridiana.gui.paper import report
        from pypdf import PdfReader
        from quick.aiuti.differential import connected_fixture, compare, normalized
        from meridiana.app.report.compose import compose
        self.session.project = connected_fixture()
        if os.environ.get("MERIDIANA_REPORT_CAPTURE"):
            from meridiana import i18n
            i18n.setup("it")
        cache = Path(self.temp.name) / "weather"
        write_cache(clear_sky_meteo(), cache)
        self.session.results, _, _ = jobs.layout_of(self.session.project)
        self.session.energy = pipeline.compute(self.session.project, self.session.results, cache, fetch=False).as_dict()
        self.session.energy_key_computed = self.session.expected_key()    # as a year computed
        arrays = system.arrays_of(self.session.project, self.session.results)
        inverter = system.combined(system.inverters_of(self.session.project, sum(a.p_stc for a in arrays)))
        items = checks.gather(self.session.project, self.session.results, self.session.energy, inverter, True)
        items += checks.plant_items(self.session.energy["plant"])
        items.sort(key=lambda item: checks.LEVELS.index(item.level))
        supplied = {"checks": items, "plant": self.session.energy["plant"],
                    "rules_facts": rules.facts(self.session.project, self.session.results, self.session.energy, inverter)}
        # The Quick window sends only the year and the layouts: the worker makes the checks and the facts as the
        # Widgets window does (the Rho trial wrote 30 pages instead of 31 without them, 05/11/2026).
        from meridiana.gui.backend.report_worker import supplied as made_by_worker
        made = made_by_worker(self.session.project, {**self.session.energy, "results": self.session.results})
        self.assertEqual([(i.level, i.area, i.text) for i in made["checks"]], [(i.level, i.area, i.text) for i in items])
        self.assertEqual(made["rules_facts"], supplied["rules_facts"])
        self.assertEqual(made_by_worker(self.session.project, {**self.session.energy, **supplied}), {})
        self.backend.setReportData(supplied)
        legacy_data = {**self.session.energy, **supplied, "results": self.session.results}
        for template in ("complete", "compact", "client", "electrical", "energy"):
            self.backend.setSetting("template", template)
            legacy = compose(self.session.project, legacy_data)
            quick = compose(self.session.project, self.backend.report_data())
            self.assertEqual(compare(normalized(legacy.document), normalized(quick.document)), [], template)
        self.backend.setSetting("template", "compact")
        if not os.environ.get("MERIDIANA_REPORT_CAPTURE"):
            self.backend.setSetting("register", True)
        attachment = Path(self.temp.name) / "scheda.pdf"
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(160, 220)
        writer.write(attachment)
        self.backend.addAttachments([str(attachment)])
        self.backend.retitleAttachment(0, "Scheda tecnica di prova")
        reference = Path(self.temp.name) / "in-process.pdf"
        target = Path(self.temp.name) / "quick.pdf"
        report.export_pdf(self.session.project, self.backend.report_data(), reference)
        start = time.monotonic()
        self.backend.exportPdf(str(target))
        self.assertLess(time.monotonic() - start, 0.1)
        self.assertTrue(self.backend.busy)
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=90),
                        self.backend.status + self.backend.error)
        self.assertFalse(self.backend.error, self.backend.error)
        left, right = PdfReader(reference), PdfReader(target)
        self.assertEqual(right.metadata['/MeridianaFingerprint'], self.session.year_fingerprint())     # R437
        self.assertTrue(right.metadata['/MeridianaExported'])
        self.assertEqual([p.extract_text() for p in left.pages], [p.extract_text() for p in right.pages])
        self.assertEqual([p.mediabox for p in left.pages], [p.mediabox for p in right.pages])
        # Typst itself timestamps each compile; no engine change to force byte-identical metadata.
        self.assertEqual(pdf_content_bytes(reference), pdf_content_bytes(target))
        if self.backend.settings["register"]:
            csv, methods = report.register_paths(target)
            expected_csv = Path(self.temp.name) / "expected.csv"
            report.write_register_csv(self.session.project, legacy_data, expected_csv)
            self.assertEqual(csv.read_bytes(), expected_csv.read_bytes())
            self.assertGreater(len(PdfReader(methods).pages), 0)
        self.backend.setActive(True)
        self.backend.requestPreview()
        self.assertTrue(self.backend.busy)
        self.assertEqual(self.backend.pages, [])
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=90))
        self.assertFalse(self.backend.error, self.backend.error)
        self.assertEqual(self.backend.pageCount, len(right.pages))
        self.assertTrue(all(Path(p["path"]).is_file() for p in self.backend.pages))
        _setup.turn_events(self.app, 250)
        self.assertFalse(self.backend.busy, 'A manual preview must consume its scheduled automatic request')
        self.assertFalse(self.backend._timer.isActive())
        if os.environ.get("MERIDIANA_REPORT_CAPTURE"):
            self.capture_preview()

    def capture_preview(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtQuick import QQuickView
        from meridiana.gui.backend.controls import install_controls
        view = QQuickView()
        self.addCleanup(view.close)
        theme = install_controls(view.engine())
        view.setInitialProperties({"backend": self.backend})
        view.setSource(QUrl.fromLocalFile(str(_setup.ROOT / "src/meridiana/gui/qml/Meridiana/Report/ReportPage.qml")))
        self.assertEqual(view.status(), QQuickView.Status.Ready, [e.toString() for e in view.errors()])
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        # Existing preview stays visible while edits are made; don't start a second compilation for a photograph.
        self.backend.setActive(False)
        folder = _setup.ROOT / "build/quick-foto/pagine"
        folder.mkdir(parents=True, exist_ok=True)
        for mode in ("light", "dark"):
            theme.configure({"theme": mode})
            for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
                view.resize(width, height)
                view.show()
                self.assertTrue(_setup.wait_until(self.app, lambda: view.isExposed()))
                _setup.turn_events(self.app, 300)
                image = view.grabWindow()
                self.assertFalse(image.isNull())
                scale = os.environ.get("QT_SCALE_FACTOR", "1")
                self.assertTrue(image.save(str(folder / f"report-preview-{mode}-{width}x{height}-s{scale}.png")))

    def test_export_error_is_visible_and_does_not_start_a_job(self):
        self.backend.exportPdf(str(Path(self.temp.name) / "not-there" / "report.pdf"))
        self.assertFalse(self.backend.busy)
        self.assertTrue(self.backend.error)

    def test_a_pdf_asked_during_the_preview_is_said_and_written_when_it_ends(self):
        # 05/11/2026: asked while the Report page prepared its preview, the PDF was dropped without a word.
        target = Path(self.temp.name) / "chiesta-durante-anteprima.pdf"
        self.backend.setActive(True)
        self.backend.requestPreview()
        self.assertTrue(self.backend.busy, self.backend.error)
        self.backend.exportPdf(str(target))
        self.assertTrue(self.backend._export_queued)
        self.assertIn(self.backend._queued_note, self.backend.status)
        self.assertFalse(self.backend.error, self.backend.error)
        # The fixture has no year: the PDF itself would not compose, what counts is that it starts, for that file.
        self.assertTrue(_setup.wait_until(self.app, lambda: self.backend._mode == "export" and self.backend.busy,
                                          seconds=90), self.backend.status + self.backend.error)
        self.assertEqual(self.backend._target, target)
        self.assertEqual(self.backend._export_queued, "")
        self.assertNotIn(self.backend._queued_note, self.backend.status)
        self.backend.cancel()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=20))

    def test_the_year_computed_for_a_pdf_during_a_preview_lets_the_preview_end_first(self):
        # r17-unita, 06/11/2026: «Compute and then export», the year came back while a preview was being made; the
        # preview was killed and the PDF started at once, so the end of the killed preview was taken for the PDF's
        # (PDF lost, AttributeError in _read_output). Now the PDF waits for the preview to end, then goes.
        target = Path(self.temp.name) / "dopo-il-calcolo.pdf"
        self.backend.setActive(True)
        self.backend.requestPreview()
        self.assertTrue(self.backend.busy, self.backend.error)
        preview = self.backend._handle
        self.backend._export_waiting, self.backend._export_after_year = str(target), True
        self.backend._session_changed({"energy"})          # the fixture has no year: never outdated, it goes
        self.assertTrue(_setup.wait_until(self.app, lambda: self.backend._mode == "export" and self.backend.busy,
                                          seconds=90), self.backend.status + self.backend.error)
        self.assertIsNot(self.backend._handle, preview)
        self.assertEqual(self.backend._target, target)
        self.assertFalse(self.backend.error, self.backend.error)
        _setup.wait_until(self.app, lambda: False, seconds=1.5)      # the killed preview's end, had it been pending
        # the PDF still being made, its job in hand; or, on a fast machine, already ended: then by the PDF's own job
        # (still the export, and the fixture's own refusal at most: it has no module laid), not by the killed
        # preview's end, which was read as the PDF's (AttributeError in _read_output)
        if self.backend.busy:
            self.assertIsNotNone(self.backend._handle, "the PDF's job must be in hand")
            self.assertEqual((self.backend._mode, self.backend.error), ("export", ""))
            self.backend.cancel()
            self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=20))
        else:
            self.assertEqual(self.backend._mode, "export")
            self.assertNotIn("AttributeError", self.backend.error)
            self.assertTrue(target.is_file() or "no module is laid" in self.backend.error, self.backend.error)

    def test_r509_r510_pages_drawn_in_device_pixels_again_after_a_zoom_and_the_number_in_a_fixed_bar(self):
        from _fixtures import clear_sky_meteo, write_cache
        from PySide6.QtCore import QObject, QPointF, QUrl
        from PySide6.QtQuick import QQuickView
        from meridiana.app import jobs
        from meridiana.app import pipeline
        from meridiana.gui.backend.controls import install_controls
        from quick.aiuti.differential import connected_fixture
        self.session.project = connected_fixture()
        cache = Path(self.temp.name) / "weather"
        write_cache(clear_sky_meteo(), cache)
        self.session.results, _, _ = jobs.layout_of(self.session.project)
        self.session.energy = pipeline.compute(self.session.project, self.session.results, cache, fetch=False).as_dict()
        self.session.energy_key_computed = self.session.expected_key()
        self.backend.setActive(True)
        self.backend.requestPreview()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=90))
        self.assertFalse(self.backend.error, self.backend.error)
        view = QQuickView()
        self.addCleanup(view.close)
        install_controls(view.engine())
        view.setInitialProperties({"backend": self.backend})
        view.setSource(QUrl.fromLocalFile(str(_setup.ROOT / "src/meridiana/gui/qml/Meridiana/Report/ReportPage.qml")))
        self.assertEqual(view.status(), QQuickView.Status.Ready, [e.toString() for e in view.errors()])
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.resize(1366, 900)
        view.show()
        self.assertTrue(_setup.wait_until(self.app, lambda: view.isExposed()))
        root = view.rootObject()
        dpr = view.devicePixelRatio()

        def visual(name):                   # the Repeater's pages are children of the Column, not of the root
            pending, found = [root], []
            while pending:
                current = pending.pop()
                pending.extend(current.childItems())
                if current.objectName() == name:
                    found.append(current)
            return sorted(found, key=lambda o: o.mapToScene(QPointF(0, 0)).y())

        def pages():
            return visual("reportPreviewPage")

        def images():
            return visual("reportPreviewImage")

        def drawn_as_shown():
            # each page near the view holds a drawing as wide as it is, in device pixels: none of a fixed width
            near = [i for i in images() if i.property("want")]
            return bool(near) and all(i.property("source").toString().endswith(i.property("want"))
                                      and round(i.property("implicitWidth")) == round((i.width()) * dpr) for i in near)
        self.assertTrue(_setup.wait_until(self.app, lambda: len(pages()) == self.backend.pageCount and drawn_as_shown(),
                                          seconds=20), (len(pages()), self.backend.pageCount, len(self.backend.pages),
                                                        self.backend.busy, [(i.width(), i.property("implicitWidth"),
                                                        i.property("want")) for i in images()[:3]]))
        # far from the view a page is not drawn: 38 pages at 2.000 px would be about a gigabyte
        self.assertTrue(any(not i.property("source").toString() for i in images()))
        width = pages()[0].width()
        self.assertTrue(_setup.wait_until(self.app, lambda: any(w == round((width - 2) * dpr) for _i, w, _h in report_pages_drawn())))
        bar = root.findChild(QObject, "reportPreviewBar")
        number = root.findChild(QObject, "reportPageNumber")
        self.assertTrue(bar.property("visible"))
        total = self.backend.pageCount
        self.assertEqual(number.property("text"), self.backend.labels["pageOf"].format(n=1, total=total))
        # no tip rides on the pages (R510)
        riding = [o.metaObject().className() for page in pages() for o in page.findChildren(QObject)
                  if any(word in o.metaObject().className() for word in ("ToolTip", "HoverHandler"))]
        self.assertFalse(riding)
        zoom_in = root.findChild(QObject, "reportZoomIn")
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        centre = zoom_in.mapToScene(QPointF(zoom_in.width() / 2, zoom_in.height() / 2)).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
        _setup.turn_events(self.app, 40)
        self.assertEqual(root.findChild(QObject, "reportZoom").property("text"), "125 %")
        self.assertEqual(pages()[0].width(), round(width * 1.25))
        # while the zoom settles the pages keep the drawing they had, scaled: never a blank page
        self.assertTrue(all(i.property("source").toString() for i in images() if i.property("want")))
        self.assertTrue(_setup.wait_until(self.app, lambda: drawn_as_shown()
                                          and any(w == round((round(width * 1.25) - 2) * dpr) for _i, w, _h in report_pages_drawn())))
        # scrolled to the third page, the bar says it and stays where it was
        preview = root.findChild(QObject, "reportPreview")
        flick = preview.property("contentItem")
        y0 = bar.mapToScene(QPointF(0, 0)).y()
        flick.setProperty("contentY", pages()[2].y())
        _setup.turn_events(self.app, 40)
        self.assertEqual(number.property("text"), self.backend.labels["pageOf"].format(n=3, total=total))
        self.assertEqual(bar.mapToScene(QPointF(0, 0)).y(), y0)

    def test_first_preview_creates_its_cache_directory(self):
        cache = Path(self.temp.name) / 'first-start' / 'cache'
        self.backend.paths = {'cache': cache}
        self.backend.requestPreview()
        self.assertTrue(self.backend.busy, self.backend.error)
        # Directory creation belongs to the worker; the request never waits on disk.
        self.assertTrue(_setup.wait_until(self.app, cache.is_dir, seconds=20), self.backend.error)
        self.backend.cancel()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=20))
        self.assertFalse(self.backend.error)

    def test_study41_the_preview_asked_off_the_thread_from_a_worker_kept_warm(self):
        # Study 41 (08/11/2026), R598: entering the page starts the report's job process, which imports and waits;
        # the request is the photo and the options, the pages come from the job, and the job keeps a report's
        # process warm for the next one.
        from meridiana.app import report_job
        from meridiana.core.compute import procmem
        center = self.backend.center
        self.backend.setActive(True)
        self.assertTrue(_setup.wait_until(self.app, lambda: any(p.name == report_job.NAME and p.pid
                                                                  for p in center.runner.processes()), seconds=20))
        self.backend.requestPreview()
        self.assertTrue(self.backend.busy)
        self.assertTrue(self.backend._handle.active)
        self.assertEqual([r["slot"] for r in center.rows()], ["report"])
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=90), self.backend.status)
        # the fixture has no modules laid: the worker answers that, in words (R459), and is not a traceback
        self.assertIn("no module is laid", self.backend.error)
        # the year was written once, for this preview and the next ones, until another year or layout comes
        first = self.backend._year_spec()["file"]
        self.assertEqual(self.backend._year_spec()["file"], first)
        self.session.results = dict(self.session.results)
        self.assertNotEqual(self.backend._year_spec()["file"], first)
        # a report's process kept warm under the job's process, for the next preview
        job = next(p for p in center.runner.processes() if p.name == report_job.NAME)
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(procmem.children(job.pid)), seconds=10))
        # Cancel at once: the job dropped, its row gone, the page not busy
        self.backend.requestPreview()
        self.backend.cancel()
        self.assertFalse(self.backend.busy)
        self.assertEqual(center.rows(), [])

    def test_no_stale_preview_is_published_after_project_change(self):
        self.backend.setActive(True)
        self.backend.requestPreview()
        self.backend.setSetting("client", "A new snapshot")
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=30))
        self.assertEqual(self.backend.pages, [])
        self.assertFalse(self.backend.error)

    def test_r548_the_preview_made_ahead_once_the_year_is_ready_and_shown_at_once(self):
        # R548: with memory to spare, the preview is made while the page is not shown, a moment after the year; the
        # page entered then shows it without asking another; a change makes it stale and the page asks again.
        from unittest import mock
        from _fixtures import clear_sky_meteo, write_cache
        from meridiana.app import jobs
        from meridiana.app import pipeline
        from quick.aiuti.differential import connected_fixture
        from meridiana.gui.backend import activity
        self.addCleanup(self.backend.setActive, False)
        activity._last[0] = time.monotonic() - 60          # r27: the designer still (activity.py)
        self.session.project = connected_fixture()
        cache = Path(self.temp.name) / "weather"
        write_cache(clear_sky_meteo(), cache)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "0"}):
            self.backend._ahead.setInterval(50)
            self.session.results, _, _ = jobs.layout_of(self.session.project)
            self.session.energy = pipeline.compute(self.session.project, self.session.results, cache,
                                                   fetch=False).as_dict()
            self.session.energy_key_computed = self.session.expected_key()
            self.session.changed("energy")
            self.assertFalse(self.backend._ahead.isActive())        # «Risparmia», or a PC short of memory: nothing
            with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
                self.session.changed("energy")
                self.assertTrue(self.backend._ahead.isActive())
                self.assertTrue(_setup.wait_until(self.app, lambda: self.backend.busy, seconds=5))
                self.assertTrue(self.backend._ahead_run)
                self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=120),
                                self.backend.status)
                self.assertFalse(self.backend.error)
                self.assertGreater(self.backend.pageCount, 0)
                self.assertFalse(self.backend._ahead.isActive())    # made once: nothing changed since
                made = self.backend.pages
                self.backend.setActive(True)                        # the page entered: the pages at once
                self.assertFalse(self.backend.busy)
                self.assertFalse(self.backend._timer.isActive())
                self.assertIs(self.backend.pages, made)
                self.backend.setActive(False)
                self.backend.setSetting("client", "Another client")  # a change: stale, the page asks again
                self.assertTrue(self.backend._stale)
                self.backend._ahead.stop()
                self.backend.setActive(True)
                self.assertTrue(self.backend._timer.isActive())
                self.backend.setActive(False)

    def _year_for_ahead(self):
        from _fixtures import clear_sky_meteo, write_cache
        from meridiana.app import jobs
        from meridiana.app import pipeline
        from quick.aiuti.differential import connected_fixture
        self.session.project = connected_fixture()
        cache = Path(self.temp.name) / "weather"
        write_cache(clear_sky_meteo(), cache)
        self.session.results, _, _ = jobs.layout_of(self.session.project)
        self.session.energy = pipeline.compute(self.session.project, self.session.results, cache,
                                               fetch=False).as_dict()
        self.session.energy_key_computed = self.session.expected_key()

    def test_r27_the_preview_made_ahead_only_while_the_designer_is_still(self):
        # r27 (confronto-r27-dell.md): the phases walked in a row paid for the preview made ahead in r25; it starts
        # only after activity.IDLE_S without a key, a button, the wheel or a change of phase.
        from unittest import mock
        from meridiana.gui.backend import activity
        self.addCleanup(self.backend.setActive, False)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.backend._ahead.setInterval(50)
            self._year_for_ahead()
            activity.touch()                                    # the designer at work
            self.session.changed("energy")
            self.assertTrue(self.backend._ahead.isActive())
            self.assertGreater(self.backend._ahead.remainingTime(), 3000)   # the quiet waited for, not 50 ms
            self.backend._preview_ahead()                       # its time come while the designer works
            self.assertFalse(self.backend.busy)
            self.assertTrue(self.backend._ahead.isActive())     # asked again at the next quiet
            self.backend._ahead.stop()

    def test_r27_the_designer_back_suspends_the_preview_made_ahead_and_the_page_lets_it_go_on(self):
        from unittest import mock
        from meridiana.app import report_job
        from meridiana.gui.backend import activity
        self.addCleanup(self.backend.setActive, False)
        center = self.backend.center
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.backend._ahead.setInterval(50)
            activity._last[0] = time.monotonic() - 60
            self._year_for_ahead()
            self.session.changed("energy")
            self.assertTrue(_setup.wait_until(self.app, lambda: self.backend._handle is not None, seconds=10))
            self.assertTrue(self.backend._ahead_run)
            self.assertIs(self.backend._handle.kind, report_job.AHEAD)
            handle = self.backend._handle
            # the quiet set above again: on a loaded machine something of the window had told the activity during the
            # wait for the job, and the touch below was no return after a quiet (no pause)
            activity._last[0] = time.monotonic() - 60
            if not self.backend._ahead_going():
                # the preview made ahead had already ended (the CI's runner): there is nothing left to suspend
                self.skipTest('the preview made ahead ended before the designer came back')
            activity.touch()                                    # back after the quiet: its process waits
            self.assertTrue(self.backend._paused)
            self.assertTrue(self.backend._pause_file().is_file())
            self.assertTrue(self.backend._ahead.isActive())
            # the job has suspended its report's process: its row says so
            self.assertTrue(_setup.wait_until(self.app, lambda: any(r["phase"] == report_job.PAUSED
                                                                      for r in center.rows()), seconds=60),
                            center.rows())
            self.assertTrue(self.backend.busy)                  # suspended, not ended
            self.assertIs(self.backend._handle, handle)
            self.backend.setActive(True)                        # the page entered: it goes on, for the page
            self.assertFalse(self.backend._paused)
            self.assertFalse(self.backend._pause_file().exists())
            self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=120),
                            self.backend.status)
            self.assertFalse(self.backend.error)
            self.assertGreater(self.backend.pageCount, 0)

    def test_r27_a_change_ends_the_preview_made_ahead_on_its_way(self):
        from unittest import mock
        from meridiana.gui.backend import activity
        self.addCleanup(self.backend.setActive, False)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.backend._ahead.setInterval(50)
            activity._last[0] = time.monotonic() - 60
            self._year_for_ahead()
            self.session.changed("energy")
            self.assertTrue(_setup.wait_until(self.app, lambda: self.backend._handle is not None, seconds=10))
            activity.touch()                                    # the designer back (its process suspended)
            self.backend.setSetting("client", "Another client")    # and a change: its pages would never be shown
            self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, seconds=10))
            self.assertIsNone(self.backend._handle)             # the suspended job ended, not left waiting
            self.assertEqual(self.backend.center.rows(), [])
            self.assertFalse(self.backend._pause_file().exists())
            self.assertEqual(self.backend.pages, [])
            self.assertFalse(self.backend.error)
            self.backend._ahead.stop()

    def test_qml_page_loads_and_client_keyboard_edit_is_undoable(self):
        from PySide6.QtCore import QUrl, Qt, QObject, QCoreApplication, QEvent
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtQuick import QQuickView
        from PySide6.QtTest import QTest
        from meridiana.gui.backend.controls import install_controls
        view = QQuickView()
        self.addCleanup(view.close)
        theme = install_controls(view.engine())
        view.setInitialProperties({"backend": self.backend})
        view.setSource(QUrl.fromLocalFile(str(_setup.ROOT / "src/meridiana/gui/qml/Meridiana/Report/ReportPage.qml")))
        self.assertEqual(view.status(), QQuickView.Status.Ready, [e.toString() for e in view.errors()])
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.resize(1366, 900)
        view.show()
        self.assertTrue(_setup.wait_until(self.app, lambda: view.isExposed()))
        choice = view.rootObject().findChild(QObject, "reportTemplate")
        self.assertIsNotNone(choice)
        from meridiana.app.report import reports
        self.assertEqual(choice.property("displayText"), reports.templates()["complete"].name)
        choice.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Down)
        self.assertEqual(self.backend.settings["template"], "compact")
        self.session.undo.undo()
        self.assertEqual(choice.property("displayText"), reports.templates()["complete"].name)
        for mode in ("light", "dark"):
            theme.configure({"theme": mode})
            _setup.turn_events(self.app, 50)
            image = view.grabWindow()
            from PySide6.QtGui import QColor
            self.assertEqual(image.pixelColor(1, 1), QColor(theme.colors["panel"]))
        field = view.rootObject().findChild(QObject, "reportClient")
        self.assertIsNotNone(field)
        field.forceActiveFocus()
        for character in "Cliente ":
            QCoreApplication.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, character))
        self.backend.refresh()
        for character in "Quick":
            QCoreApplication.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, character))
        QTest.keyClick(view, Qt.Key.Key_Tab)
        self.assertEqual(self.session.project.report["client"], "Cliente Quick")
        self.session.undo.undo()
        self.assertEqual(self.backend.settings["client"], "")
        self.assertEqual(field.property("text"), "")

    def test_cancel_does_not_replace_existing_file_or_leave_parts(self):
        target = Path(self.temp.name) / "kept.pdf"
        target.write_bytes(b"original")
        self.backend.exportPdf(str(target))
        self.backend.cancel()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy))
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual(list(Path(self.temp.name).glob("*.part")), [])

    @unittest.skipUnless(os.name == "nt", "Windows virtualenv launcher lifecycle")
    def test_windows_cancel_does_not_leave_the_virtualenv_child_running(self):
        import ctypes
        from ctypes import wintypes
        class Entry(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        def processes():
            snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
            entry = Entry()
            entry.dwSize = ctypes.sizeof(Entry)
            result = {}
            try:
                more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
                while more:
                    result[entry.th32ProcessID] = entry.th32ParentProcessID
                    more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
                return result
            finally:
                kernel.CloseHandle(snapshot)
        from meridiana.app import report_job
        target = Path(self.temp.name) / "cancel.pdf"
        self.backend.exportPdf(str(target))
        runner = self.backend.center.runner
        self.assertTrue(_setup.wait_until(self.app, lambda: any(p.name == report_job.NAME and p.pid
                                                                  for p in runner.processes()), seconds=20))
        parent = next(p.pid for p in runner.processes() if p.name == report_job.NAME)
        self.assertTrue(_setup.wait_until(self.app, lambda: any(owner == parent for owner in processes().values()),
                                          seconds=20))
        _setup.turn_events(self.app, 500)
        children = [pid for pid, owner in processes().items() if owner == parent]
        children += [pid for pid, owner in processes().items() if owner in children]
        self.backend.cancel()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy))
        self.assertTrue(_setup.wait_until(self.app, lambda: not set(children).intersection(processes()), seconds=5),
                        f"Report descendants survived cancellation: {children}")

    def test_close_unsubscribes_and_ignores_future_session_changes(self):
        self.backend.close()
        self.assertEqual(self.session.listeners, [])
        self.session.changed("project:report")
