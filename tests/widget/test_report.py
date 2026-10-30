"""The report (ui/report.py, ui/report_chapters.py, reports.py) of a whole project, without the window: an inverter
from the list, the strings it proposes on the modules, the consumption, the economics, the checks and the notes of
the rules; the chapters of each template there and in their order, the contents with their pages, a chapter left
out when it is turned off or has no data; the author's profile only where it is chosen; what the model leaves
out; the values still at their default; the PDF and the preview; the attachments after the last chapter, in the
contents and in the PDF where the contents say, a missing or protected one; the register of the calculations
beside the PDF; the 3D pictures in the Summary and in the Overview. The year is computed once for the class from
the synthetic weather of _energy, with no network. Qt for the PDF (offscreen will do: there Qt writes the text as
outlines, so the pages are told apart by their sizes, not by their words)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

from meridiana import checks, jobs, model, rules
from meridiana.energy import pipeline, system

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def sample_pdf(path: Path, pages: int, size_mm: tuple[float, float]) -> Path:
    """A PDF of `pages` pages `size_mm` wide and high, a frame on each: an attachment told apart by its size."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QSizeF(*size_mm), QPageSize.Unit.Millimeter, "", QPageSize.SizeMatchPolicy.ExactMatch))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    for i in range(pages):
        if i:
            writer.newPage()
        painter.drawRect(50, 50, writer.width() - 100, writer.height() - 100)
    painter.end()
    return path


def sizes_mm(path: Path) -> list[tuple[int, int]]:
    """Each page's width and height in millimetres, rounded."""
    from pypdf import PdfReader
    return [(round(float(pg.mediabox.width) * 25.4 / 72), round(float(pg.mediabox.height) * 25.4 / 72))
            for pg in PdfReader(str(path)).pages]


def project() -> model.Project:
    p = model.Project(name="Prova")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
    b = model.Building(id=p.new_id("b"), name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
    p.buildings.append(b)
    p.subfields.append(model.SubField(id=p.new_id("s"), name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]],
                                      building=b.id, params={"tilt": 15.0}, filled=True))
    p.energy["inverters"] = [{"record": {
        "manufacturer": "Acme", "model": "AC-20K", "ac_power_nominal_w": 20000, "efficiency_euro_pct": 97.5,
        "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180, "mppt_voltage_max_v": 1000, "mppt_count": 2,
        "dc_current_max_per_mppt_a": [26, 26], "dc_isc_max_per_mppt_a": [40, 40]}, "count": 2, "name": ""}]
    p.energy["strings"] = {"auto": True}            # Meridiana's proposal, as a project of before format 14 had it
    p.rules = {"obligation": "new"}
    return p


class Report(unittest.TestCase):
    PROFILE = {"name": "Prova", "signer": "Firmatario di prova", "register": "Albo di prova", "firm": "Studio di prova",
               "address": "", "phone": "", "email": "", "web": "", "logo": ""}

    @classmethod
    def setUpClass(cls):
        from _fixtures import clear_sky_meteo, write_cache
        cls.app = _setup.qt_or_skip()
        cls.cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cls.cache)
        cls.p = project()
        cls.results, _keys, _laid = jobs.layout_of(cls.p)
        energy = pipeline.compute(cls.p, cls.results, cls.cache, fetch=False).as_dict()
        arrays = system.arrays_of(cls.p, cls.results)
        inverter = system.combined(system.inverters_of(cls.p, sum(a.p_stc for a in arrays)))
        # what the window hands to the report (MainWindow._report_data): the year, the checks, the plant, the facts,
        # the layouts
        energy["checks"] = checks.gather(cls.p, cls.results, energy, inverter, True) + checks.plant_items(energy["plant"])
        energy["rules_facts"] = rules.facts(cls.p, cls.results, energy, inverter)
        energy["results"] = cls.results
        cls.energy = energy

    def setUp(self):
        self.p.report = {}

    def html(self, energy=None, profile=None):
        from meridiana.ui.report import build_html
        images = []
        text = build_html(self.p, energy or self.energy, lambda name, png, ratio=1.0: images.append(name) or name,
                          profile)
        return text, images

    def test_every_chapter_of_the_complete_template_is_there_in_its_order_with_the_contents(self):
        from meridiana import reports
        text, _images = self.html()
        titles = [reports.chapters()[c].title for c in reports.templates()["complete"].chapters]
        order = ["<h2 style='page-break-before: always'>Contents</h2>"]
        order += [f"<h2 style='page-break-before: always'>{n}. {t}</h2>" for n, t in enumerate(titles, 1)]
        where = [text.find(h) for h in order]
        self.assertNotIn(-1, where, [h for h, w in zip(order, where, strict=True) if w < 0])
        self.assertEqual(where, sorted(where))
        for h in ("<h3>Strings (CEI 64-8/7)</h3>", "<td align='left'>Inverter 1: Acme AC-20K</td>",
                  "<td align='left'>Inverter 2: Acme AC-20K</td>", "<h4>Checks of the strings</h4>",
                  "<h4>Checks of the inverters</h4>", "<h4>The strings on the modules</h4>",
                  "<h3>Notes for the technical report</h3>", "<h3>Values still at their default</h3>"):
            self.assertIn(h, text)
        for n, t in enumerate(titles, 1):                                  # the contents list them all
            self.assertIn(f"<td class='toc'>{n}. {t}</td>", text)

    def test_the_compact_template_writes_its_five_chapters_without_contents_with_the_author_when_chosen(self):
        from meridiana import reports
        self.p.report = {"template": "compact"}
        text, images = self.html(profile=self.PROFILE)
        titles = [reports.chapters()[c].title for c in reports.templates()["compact"].chapters]
        where = [text.find(f"<h2>{n}. {t}</h2>") for n, t in enumerate(titles, 1)]
        self.assertNotIn(-1, where)
        self.assertEqual(where, sorted(where))
        self.assertNotIn("Contents", text)
        self.assertIn("<h1>Prova</h1>", text)
        for value in ("Studio di prova", "Firmatario di prova", "Albo di prova"):
            self.assertIn(value, text)
        for name in ("plan", "plan_strings", "monthly"):
            self.assertIn(name, images)
        bare, _images = self.html()                                         # no profile: none of it
        for value in ("Studio di prova", "Firmatario di prova", "Albo di prova", "Designer"):
            self.assertNotIn(value, bare)

    def test_a_chapter_turned_off_or_without_its_data_is_left_out(self):
        self.p.report = {"off": ["economics", "annexes"]}
        text, _images = self.html()
        self.assertNotIn(". Economics</", text)
        self.assertNotIn(". Component data</", text)
        self.assertIn("7. Checks and standards", text)                     # the numbers follow what is written
        bare = {k: v for k, v in self.energy.items() if k not in ("plant", "rules_facts", "checks", "load", "econ")}
        self.p.report = {}
        text, _images = self.html(bare)
        for h in ("Electrical system", "Strings (CEI 64-8/7)", "Notes for the technical report", "Checks and standards",
                  "Consumption and balance"):
            self.assertNotIn(h, text)
        self.assertIn("4. Energy yield", text)

    def test_the_strings_are_listed_by_inverter_and_input_with_their_checks_and_modules(self):
        from meridiana.ui.report import _keys_text
        plant = self.energy["plant"]
        self.assertEqual(len(plant.units), 2)
        self.assertTrue(plant.strings)
        text, _images = self.html()
        self.assertIn(f"{len(plant.strings)} strings on ", text)
        self.assertIn("proposed by Meridiana", text)
        self.assertIn("Checked at the hottest cell of the typical year", text)     # the year is there: its cells
        for s in plant.strings:
            self.assertIn(f"<td align='left'>{s.label}</td><td align='left'>Sud</td><td align='right'>{len(s.modules)}"
                          "</td>", text)
            self.assertIn(_keys_text([k for _sf, k, _c in s.modules]), text)
        self.assertIn("Modules in series within the range the input takes", text)   # the checks of each input
        self.assertIn("modules in series", text)
        # their marks the window's symbols, pictures of the report (R138: they were the characters ✔ ⚠ ✘ ℹ)
        self.assertIn("symbol-check", _images)
        self.assertIn("<img src='symbol-check'", text)
        self.assertNotIn("✔", text)
        from meridiana.ui import report_chapters
        self.assertIsNone(report_chapters._IMAGE[0])                                # no report left behind
        self.assertTrue(report_chapters._symbol_png("check").startswith(b"\x89PNG"))
        self.assertEqual(_keys_text(["0:0", "0:1", "0:2", "1:2", "1:1", "1:0", "3:5"]), "0:0-2, 1:2-0, 3:5")
        self.assertEqual(_keys_text(["0:0", "0:2", "0:3:1"]), "0:0, 0:2, 0:3:1")

    # the look of the report (R291, 30/10/2026): one hierarchy of headings, the units in the headers, nothing twice

    def test_the_headings_are_one_hierarchy_and_the_plan_is_drawn_once(self):
        """Chapters are the only h2 (the records of the methods come in a level down); the plan is in the summary
        and not again in the layout; the strings' checks are written once for each kind of string."""
        from meridiana import reports
        text, images = self.html()
        chapters = reports.plan(self.p, self.energy)
        self.assertEqual(text.count("<h2"), 1 + len(chapters))                # the contents, then the chapters
        self.assertEqual([c.id for c in chapters], ["summary", "site", "layout", "plant", "production",
                                                    "consumption", "economics", "checks", "methods", "annexes"])
        self.assertEqual(images.count("plan"), 1)
        self.assertEqual(images.count("plan_strings"), 1)
        self.assertIn("<h3>What the model does not include</h3>", text)       # was an h2 inside chapter 9
        self.assertIn("Strings of 25 modules in series, on the inputs 1.1, 1.2, 2.1, 2.2.", text)
        self.assertEqual(text.count("Modules in series within the range the input takes"), 1)
        self.assertEqual(text.count("Figure 1. "), 1)                          # the figures numbered through
        self.assertIn("Figure 2. ", text)
        self.p.report = {"off": ["summary"]}
        _text, images = self.html()
        self.assertEqual(images.count("plan"), 1)                              # without the summary, the layout's

    def test_the_numbers_of_a_table_are_bare_with_the_unit_in_the_header(self):
        """A right-aligned cell holds a number (or a dash, or «free»): «0°», «66,3 %» and «46.613 €» carried their
        unit in every row; the checks of the chapter are grouped by area in group rows."""
        import re
        from meridiana import i18n
        for template in ("complete", "compact"):
            self.p.report = {"template": template}
            text, _images = self.html()
            mine = [t for t in text.split("<table") if t.startswith(" class='grid' width='100%' cellspacing='0' "
                                                                   "cellpadding='0'")]       # report_chapters.table
            cells = [c for t in mine for c in re.findall(r"<td align='right'>(.*?)</td>", t)]
            self.assertGreater(len(cells), 20)
            for cell in cells:
                plain = re.sub(r"<[^>]+>", "", cell).replace("&#x27;", "'")
                self.assertRegex(plain, rf"^(-?[\d.,]+|–|{i18n._('free')})$", cell)
            for head in ("Azimuth, °", "Tilt, °"):
                self.assertIn(f">{head}</th>", text)
        self.p.report = {}
        text, _images = self.html()
        self.assertIn("PR, %", text)
        self.assertIn("<td class='group' colspan='3'>Rules and report notes</td>", text)
        self.assertEqual(text.count("Rules and report notes"), 1)              # once as a group, not on every row

    def test_no_table_is_wider_than_the_page_and_the_tables_cells_are_a_point_smaller(self):
        from PySide6.QtGui import QTextTable
        from meridiana.ui import report
        for template in ("complete", "compact"):
            self.p.report = {"template": template}
            steps = report._document(self.p, self.energy, self.PROFILE)
            while True:
                try:
                    next(steps)
                except StopIteration as done:
                    doc, page, margin, _chrome = done.value
                    break
            layout = doc.documentLayout()

            def walk(frame, found):
                for child in frame.childFrames():
                    if isinstance(child, QTextTable):
                        found.append(child)
                    walk(child, found)
                return found
            tables = walk(doc.rootFrame(), [])
            self.assertGreater(len(tables), 5)
            for t in tables:
                with self.subTest(template=template, table=t.firstCursorPosition().block().text()[:30]):
                    self.assertLessEqual(layout.frameBoundingRect(t).width(), page.width() - 2 * margin + 2)
            grid = next(t for t in tables if t.format().headerRowCount() == 1)
            size = grid.cellAt(1, 0).firstCursorPosition().charFormat().fontPointSize()
            self.assertAlmostEqual(size, 9.5, places=1)

    def test_the_checks_and_the_notes_of_the_rules_carry_their_sources(self):
        text, _images = self.html()
        self.assertIn("4. Minimum renewable capacity obligation", text)            # obligation "new" (D.Lgs. 199/2021)
        self.assertIn("N24", text)                                                  # the rule's id beside its source
        notes = rules.notes(self.energy["rules_facts"])
        for _title, chosen in notes:
            for r, _paragraphs in chosen:
                self.assertIn(r.source(), text.replace("&#x27;", "'"))
        for it in self.energy["checks"]:
            if it.source:
                self.assertIn(it.source, text.replace("&#x27;", "'"))

    def test_the_report_says_what_the_model_leaves_out_and_draws_its_charts_plans_and_formulas(self):
        text, images = self.html()
        for name in ("monthly", "chain", "plan", "plan_strings", "balance", "carpet", "cash"):
            self.assertIn(name, images)
        self.assertTrue(any(n.startswith("f_") for n in images))          # the formulas, drawn
        self.assertIn("What the model does not include", text)
        self.assertIn("Bifacial modules", text)
        self.assertLess(text.index("9. Parameters and methods"), text.index("What the model does not include"))
        self.assertLess(text.index("What the model does not include"), text.index("Values still at their default"))

    def test_before_the_year_the_strings_are_said_checked_at_pvsyst_design_conditions(self):
        """The plant as the Plant phase has it before the year is computed (it was a window test, Stringing)."""
        from meridiana.energy import plant as plants
        from meridiana.ui.report import _keys_text
        early = plants.build(self.p, self.results)
        self.assertFalse(early.year)
        self.assertTrue(early.strings)
        text, _images = self.html({"plant": early, "results": self.results})
        self.assertIn("Electrical system", text)
        self.assertIn("Inverter 1: Acme AC-20K", text)
        self.assertIn("PVsyst&#x27;s design conditions", text)                # the conditions, said
        self.assertIn("The strings on the modules", text)
        for s in early.strings:
            self.assertIn(f"<td align='left'>{s.label}</td>", text)
        first = _keys_text([k for _sf, k, _c in early.strings[0].modules])
        self.assertRegex(first, r":\d+-\d+")                               # the modules, a row by its ends
        self.assertIn(first, text)
        self.assertIn("Modules in series within the range the input takes", text)     # the checks of each input
        self.assertNotIn("Energy yield", text)                             # no year, no chapter of the year

    def test_the_optimizers_of_a_solaredge_inverter_with_their_checks_and_sources(self):
        """Task 22: the Electrical system writes the optimizers, the strings' optimizers and power and SolarEdge's
        checks with their documents; the annexes the optimizer's data; the compact template its sentence."""
        import copy

        from meridiana import catalog
        from meridiana.energy import plant as plants
        p = copy.deepcopy(self.p)
        se = next(r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None) if r["model"] == "SE50K")
        p.energy["inverters"] = [{"record": se, "count": 1, "name": ""}]
        early = plants.build(p, self.results)
        self.assertTrue(early.optimized and early.strings)
        from meridiana.ui.report import build_html

        def html(project):
            return build_html(project, {**self.energy, "plant": early}, lambda name, png, ratio=1.0: name, None)
        text = html(p)
        self.assertIn("Power optimizers SolarEdge S1000, 2 modules on each", text)
        self.assertIn("DS-000105-IT", text)                                   # SolarEdge's table, cited
        self.assertIn("Synergy unit 2", text)
        self.assertIn("Optimizers in the string within SolarEdge&#x27;s range", text)
        self.assertTrue(all(s.state == "ok" for s in early.strings), [s.why for s in early.strings])
        self.assertIn("Power optimizer: SolarEdge S1000", text)              # the annex
        p.report = {"template": "compact"}
        self.assertIn("Power optimizers SolarEdge S1000", html(p))

    def test_the_contents_say_the_pages_the_chapters_fall_on(self):
        from meridiana import reports
        from meridiana.ui import report
        steps = report._document(self.p, self.energy, None)
        while True:
            try:
                next(steps)
            except StopIteration as done:
                doc, page, _margin, chrome = done.value
                break
        chosen = reports.plan(self.p, report._with_notes(self.energy))
        pages = report._chapter_pages(doc, page, chosen)
        self.assertEqual(list(pages), [c.id for c in chosen])
        self.assertGreaterEqual(min(pages.values()), 3)                    # the cover, the contents, then the chapters
        self.assertEqual(list(pages.values()), sorted(pages.values()))
        plain = doc.toPlainText()
        for n, c in enumerate(chosen, 1):
            self.assertRegex(plain, rf"{n}\. {c.title}\s*{pages[c.id]}\b")
        self.assertEqual(chrome["left"], "")                                # no profile: nobody in the header
        self.assertNotIn("Designer", [a for a, _b in chrome["cover"]["rows"]])
        self.assertEqual(chrome["cover"]["firm"], [])

    # the attachments

    def attachments(self, *specs) -> list[dict]:
        """Sample PDFs in a folder of the test: (name, pages, size in mm) each, or (name, None) for a file not there."""
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [f.unlink() for f in folder.iterdir()])
        out = []
        for name, pages, *size in specs:
            path = folder / f"{name}.pdf"
            if pages:
                sample_pdf(path, pages, size[0])
            out.append({"path": str(path), "title": ""})
        return out

    def test_the_attachments_follow_the_last_chapter_each_behind_a_page_and_in_the_contents_with_its_page(self):
        from meridiana.ui import report
        items = self.attachments(("Scheda modulo", 2, (148, 210)), ("Manca", None), ("Scheda inverter", 3, (200, 100)))
        items[0]["title"] = "Modulo di prova"
        self.p.report = {"attachments": items}
        read = report.attachments(self.p)
        self.assertEqual([(a.title, a.pages, bool(a.problem)) for a in read],
                         [("Modulo di prova", 2, False), ("Manca", 0, True), ("Scheda inverter", 3, False)])
        self.assertIn("not found", read[1].problem)
        path = Path(tempfile.mkdtemp()) / "relazione.pdf"
        report.export_pdf(self.p, self.energy, path)
        sizes = sizes_mm(path)
        a4 = (210, 297)
        first = sizes.index((148, 210))
        self.assertEqual(sizes[first:first + 2], [(148, 210)] * 2)
        self.assertEqual(sizes[first + 2:], [a4, (200, 100), (200, 100), (200, 100)])   # the second, behind its page
        self.assertEqual(sizes[:first], [a4] * first)                    # the report before: cover to annexes
        self.assertEqual(len(sizes), first + 6)
        # the contents say the pages of the PDF: the page before each attachment
        steps = report._document(self.p, self.energy, None)
        while True:
            try:
                next(steps)
            except StopIteration as done:
                doc, _page, _margin, chrome = done.value
                break
        plain = doc.toPlainText()
        self.assertRegex(plain, rf"Attachment 1: Modulo di prova\s*{first}\b")       # the separator before page `first`
        self.assertRegex(plain, rf"Attachment 2: Scheda inverter\s*{first + 3}\b")
        self.assertNotIn("Manca", plain)                                               # left out, not listed
        pages = doc.pageCount()
        self.assertEqual(report._numbers(chrome, pages - 1, pages), (len(sizes) - 3, len(sizes)))   # its footer
        self.assertEqual(report._numbers(chrome, 1, pages), (2, len(sizes)))
        # the compact template: no contents, the attachments at the end all the same
        self.p.report = {"template": "compact", "attachments": items}
        report.export_pdf(self.p, self.energy, path)
        sizes = sizes_mm(path)
        self.assertEqual(sizes[-7:], [a4, (148, 210), (148, 210), a4, (200, 100), (200, 100), (200, 100)])

    def test_the_preview_shows_the_attachments_pages_the_first_few_and_says_how_many_more(self):
        from meridiana.ui import report
        self.p.report = {"template": "compact", "attachments": self.attachments(("Lunga", 5, (148, 210)))}
        pages: list = []
        with mock.patch.object(report, "PREVIEW_ATTACHMENT_PAGES", 2):
            steps = report.preview_steps(self.p, self.energy, 300, pages)
            while True:
                try:
                    next(steps)
                except StopIteration as done:
                    total = done.value
                    break
        numbers = [int(im.text("page")) for im in pages]
        self.assertEqual(total, numbers[-1] + 2)                    # the PDF has two more pages than the last shown
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertAlmostEqual(pages[-3].height() / pages[-3].width(), 210 / 148, delta=0.02)   # the attachment's
        self.assertAlmostEqual(pages[-1].height() / pages[-1].width(), 297 / 210, delta=0.02)   # «3 more pages»
        self.assertEqual(len(pages), total - 2)

    def test_a_protected_attachment_goes_in_drawn_and_a_file_that_is_no_pdf_is_left_out(self):
        from pypdf import PdfReader

        from meridiana.ui import report
        items = self.attachments(("Protetta", 2, (148, 210)), ("Rotta", None))
        Path(items[1]["path"]).write_text("not a pdf", encoding="utf-8")
        self.p.report = {"template": "compact", "attachments": items}
        read = report.attachments(self.p)
        self.assertIn("not a PDF that can be read", read[1].problem)
        real = report._read
        with mock.patch.object(report, "_read", side_effect=lambda path: (2, True, "") if "Protetta" in path
                               else real(path)):                 # as pypdf without the cryptography package
            path = Path(tempfile.mkdtemp()) / "relazione.pdf"
            report.export_pdf(self.p, self.energy, path)
        reader = PdfReader(str(path))
        self.assertEqual(sizes_mm(path)[-2:], [(148, 210), (148, 210)])
        xobjects = reader.pages[-1]["/Resources"]["/XObject"]
        self.assertTrue(any(xobjects[k].get_object()["/Subtype"] == "/Image" for k in xobjects))   # drawn
        self.assertFalse(list(path.parent.glob("*.drawn")))         # what was drawn for it, taken away

    def test_the_attachments_are_kept_relative_to_the_project_file_and_absolute_on_another_drive(self):
        from meridiana import reports
        folder = Path(tempfile.mkdtemp())
        sheet = folder / "schede" / "modulo.pdf"
        p = model.Project(name="Percorsi")
        p.report = {"attachments": [{"path": str(sheet), "title": "Modulo"}, {"path": 7}]}
        p.save(folder / "progetto.meridiana")
        import json
        kept = json.loads((folder / "progetto.meridiana").read_text(encoding="utf-8"))["report"]["attachments"]
        self.assertEqual(kept[0], {"path": "schede/modulo.pdf", "title": "Modulo"})
        again, _notice = model.Project.load(folder / "progetto.meridiana")
        self.assertEqual(Path(again.report["attachments"][0]["path"]), sheet)
        self.assertEqual(reports.settings(again)["attachments"], [{"path": str(sheet), "title": "Modulo"}])
        with mock.patch("os.path.relpath", side_effect=ValueError("path is on mount 'D:', start on mount 'C:'")):
            self.assertEqual(reports.portable(p.report, folder)["attachments"][0]["path"], str(sheet))
        self.assertEqual(reports.attachment_title({"path": str(sheet), "title": ""}), "modulo")

    # the register of the calculations

    def test_the_register_has_the_typical_year_hour_by_hour_with_its_balance(self):
        from meridiana.energy import register
        e = self.energy
        table = register.frame(e["sim"], e.get("load"), e.get("econ"))
        self.assertEqual(len(table), 8760)
        self.assertEqual(list(table.columns), ["ghi", "poa", "temp_air", "t_cell", "production",
                                               "inverter_1_dc", "inverter_1_ac", "inverter_2_dc", "inverter_2_ac", "consumption",
                                               "self", "export", "import"])
        self.assertAlmostEqual(float(table["production"].sum()), e["sim"].energy_kwh, places=3)
        self.assertLess(float((table["inverter_1_ac"] + table["inverter_2_ac"] - table["production"]).abs().max()), 1e-9)
        self.assertAlmostEqual(float(table["consumption"].sum()), e["load"].annual_kwh, places=3)
        self.assertTrue(((table["self"] + table["import"] - table["consumption"]).abs() < 1e-9).all())
        self.assertLessEqual(float((table["self"] + table["export"] - table["production"]).max()), 1e-9)
        sunny = table["poa"] > 600
        self.assertTrue((table["t_cell"][sunny] > table["temp_air"][sunny]).all())    # the cells hotter in the sun
        self.assertAlmostEqual(float(table["t_cell"].max()), max(a["t_cell_max"] for a in e["sim"].arrays), places=6)
        bare = register.frame(e["sim"])
        self.assertEqual(list(bare.columns), ["ghi", "poa", "temp_air", "t_cell", "production",
                                             "inverter_1_dc", "inverter_1_ac", "inverter_2_dc", "inverter_2_ac"])

    def test_the_register_is_written_beside_the_report_as_the_language_reads_it_with_its_header(self):
        import pandas as pd

        from meridiana import i18n
        from meridiana.ui import report
        path = Path(tempfile.mkdtemp()) / "Relazione.pdf"
        for _f, _w in report.register_steps(self.p, self.energy, path):
            pass
        csv, pdf = report.register_paths(path)
        self.assertEqual((csv.name, pdf.name), ("Relazione - register of the calculations.csv",
                                                "Relazione - how it is computed.pdf"))
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
        self.assertFalse(path.exists())                               # the register alone: no report made
        text = csv.read_text(encoding="utf-8-sig")
        head = [line for line in text.splitlines() if line.startswith("#")]
        self.assertIn("register of the calculations of «Prova», variant «Base»", head[0])
        self.assertTrue(any("Europe/Rome" in line for line in head))
        self.assertTrue(any(line.startswith("#   Cells (°C): cells' temperature, PVsyst") for line in head))
        self.assertTrue(any(line.startswith("# Weather: ") for line in head))
        table = pd.read_csv(csv, comment="#", encoding="utf-8-sig")
        self.assertEqual(list(table.columns)[:4], ["Local time", "UTC", "Global horizontal (W/m²)", "On the plane (W/m²)"])
        self.assertEqual(len(table), 8760)
        self.assertEqual(table["Local time"].iloc[0], "2026-01-01 01:00")
        self.assertEqual(table["UTC"].iloc[0], "+01:00")
        self.assertEqual(table["UTC"].iloc[4000], "+02:00")                       # summer time
        self.assertAlmostEqual(float(table["Produced (kWh)"].sum()), self.energy["sim"].energy_kwh, delta=0.5)
        if not (Path(_setup.ROOT) / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo").exists():
            return
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        for _f, _w in report.register_steps(self.p, self.energy, path):
            pass
        csv = report.register_paths(path)[0]
        self.assertEqual(csv.name, "Relazione - registro dei calcoli.csv")
        italian = pd.read_csv(csv, sep=";", decimal=",", comment="#", encoding="utf-8-sig")
        self.assertEqual(len(italian), 8760)
        self.assertAlmostEqual(float(italian.iloc[:, 6].sum()), self.energy["sim"].energy_kwh, delta=0.5)

    def test_how_it_is_computed_is_the_chapter_of_the_methods_alone_with_its_formulas(self):
        from meridiana.ui import report
        images = []
        text, chosen = report._compose(self.p, self.energy, lambda name, make, ratio=1.0: images.append(name) or name,
                                       only="methods")
        self.assertEqual([c.id for c in chosen], ["methods"])
        self.assertIn("REGISTER OF THE CALCULATIONS", text)
        self.assertIn("<h2>Parameters and methods</h2>", text)
        self.assertIn("What the model does not include", text)
        self.assertTrue(images and all(n.startswith("f_") for n in images))       # the formulas, nothing else
        for other in ("Contents", "1. Summary", "Attachment 1"):
            self.assertNotIn(other, text)

    # the 3D pictures

    def test_the_3d_pictures_are_in_the_summary_and_in_the_overview_when_qt_quick_3d_can_draw_them(self):
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QColor, QImage

        from meridiana.ui import report_3d
        image = QImage(110, 72, QImage.Format.Format_RGB32)
        image.fill(QColor("#2f4f7f"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        png = bytes(data.data())
        asked = []
        with mock.patch.object(report_3d, "available", return_value=True), \
                mock.patch.object(report_3d, "picture", side_effect=lambda p, r, vid: asked.append(vid) or png):
            text, images = self.html()
            self.assertEqual([n for n in images if n.startswith("view_")], ["view_south_east", "view_south_west"])
            summary = text[text.index("1. Summary</h2>"):text.index("2. Site and climate data</h2>")]
            self.assertIn("From the south-east", summary)
            self.assertIn("From the south-west", summary)
            self.assertLess(summary.index("view_south_east"), summary.index("'plan'"))    # before the plan
            self.p.report = {"template": "compact"}
            text, images = self.html()
            overview = text[text.index("1. System overview and results</h2>"):text.index("2. Estimated monthly")]
            self.assertIn("view_south_west", overview)
        self.assertEqual(asked, ["south_east", "south_west"] * 2)
        with mock.patch.object(report_3d, "available", return_value=False):          # the software renderer
            text, images = self.html()
        self.assertFalse([n for n in images if n.startswith("view_")])
        self.assertNotIn("From the south-east", text)

    def test_the_pdf_is_written_whole_and_the_preview_has_its_pages(self):
        from meridiana.ui.report import export_pdf, preview_steps
        for template in ("complete", "compact"):
            with self.subTest(template=template):
                self.p.report = {"template": template}
                path = Path(tempfile.mkdtemp()) / "relazione.pdf"
                export_pdf(self.p, self.energy, path, self.PROFILE)
                data = path.read_bytes()
                self.assertTrue(data.startswith(b"%PDF"))
                self.assertIn(b"%%EOF", data[-1024:])
                self.assertGreater(len(data), 20000)
                pages: list = []
                for _f, _w in preview_steps(self.p, self.energy, 400, pages, self.PROFILE):
                    pass
                self.assertGreater(len(pages), 2 if template == "complete" else 1)
                self.assertEqual(pages[0].width(), 400)
                self.assertAlmostEqual(pages[0].height() / pages[0].width(), 297 / 210, delta=0.01)   # A4


class Settings(unittest.TestCase):
    """The project's choices for its report and the author's profiles (reports.py), without Qt."""

    def test_the_defaults_and_what_is_not_a_choice(self):
        from meridiana import reports
        p = model.Project()
        self.assertEqual(reports.settings(p), {"template": "complete", "off": [], "profile": None, "client": "",
                                               "address": True, "revision": "", "attachments": [],
                                               "register": False})
        p.report = {"template": "nonsense", "off": ["site", 3], "profile": 7, "address": False}
        s = reports.settings(p)
        self.assertEqual((s["template"], s["off"], s["profile"], s["address"]), ("complete", ["site"], None, False))

    def test_the_profile_is_the_projects_or_the_preferences_and_nobody_when_chosen(self):
        from meridiana import reports
        p = model.Project()
        profiles = [{"name": "A", "signer": "Uno"}, {"name": "B", "signer": "Due"}, {"name": ""}, "x"]
        self.assertEqual(reports.profile_for(p, profiles, "B")["signer"], "Due")       # the preferences' default
        self.assertIsNone(reports.profile_for(p, profiles, ""))
        p.report = {"profile": "A"}
        self.assertEqual(reports.profile_for(p, profiles, "B")["signer"], "Uno")
        p.report = {"profile": ""}                                          # nobody, whatever the default
        self.assertIsNone(reports.profile_for(p, profiles, "B"))
        p.report = {"profile": "gone"}
        self.assertIsNone(reports.profile_for(p, profiles, "B"))
        self.assertEqual(set(reports.clean_profile({"name": "A", "other": 1})), set(reports.PROFILE_KEYS))

    def test_every_chapter_of_every_template_has_a_writer(self):
        from meridiana import reports
        from meridiana.ui.report_chapters import BUILDERS
        for t in reports.templates().values():
            for c in t.chapters:
                self.assertIn(c, reports.chapters())
                self.assertIn(c, BUILDERS)


class Formulas(unittest.TestCase):
    """The formulas of the pages and of the report, drawn by matplotlib's mathtext (ui/pedigree.formula_png)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_formula_is_drawn_once(self):
        from meridiana.ui.pedigree import formula_png
        formula_png.cache_clear()
        first = formula_png(r"E = P \cdot t", "#000000", 100.0, 13.0)
        again = formula_png(r"E = P \cdot t", "#000000", 100.0, 13.0)
        self.assertIs(first, again)
        self.assertEqual(formula_png.cache_info().hits, 1)


if __name__ == "__main__":
    unittest.main()
