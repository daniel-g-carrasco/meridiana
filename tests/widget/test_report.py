"""The report (report_typst/, ui/report.py, reports.py) of a whole project, without the window: an inverter from the list,
the strings it proposes on the modules, the consumption, the economics, the checks and the notes of the rules; the
chapters of each template there and in their order, the contents with their pages, a chapter left out when it is
turned off or has no data; the author's profile only where it is chosen; what the model leaves out; the values still
at their default; the register of the calculations with a code for every number; the PDF and the preview drawn from
it; the attachments after the last chapter, in the contents and in the PDF where the contents say, a missing or
protected one; the register beside the PDF; the 3D pictures on the cover, in the summary and in the layout. The year
is computed once for the class from the synthetic weather of _energy, with no network. The document is data (JSON) for
Typst: what it says is read there; the PDF is read back with pypdf."""

import io
import json
import re
import tempfile
import time
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


def texts(path: Path) -> list[str]:
    from pypdf import PdfReader
    return [pg.extract_text() or "" for pg in PdfReader(str(path)).pages]


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


def blocks_of(doc: dict, kind: str) -> list[dict]:
    """Every block of `kind` in the document, inside the columns, the floats and the separators too."""
    out = []

    def walk(items):
        for b in items:
            if not isinstance(b, dict):
                continue
            if b.get("k") == kind:
                out.append(b)
            for key in ("left", "right", "items"):
                if isinstance(b.get(key), list):
                    walk(b[key])
    walk(doc["body"])
    return out


class Report(unittest.TestCase):
    PROFILE = {"name": "Prova", "signer": "Firmatario di prova", "register": "Albo di prova", "firm": "Studio di prova",
               "address": "", "phone": "", "email": "", "web": "", "logo": "", "accent": ""}

    @classmethod
    def setUpClass(cls):
        from _fixtures import clear_sky_meteo, write_cache
        cls.app = _setup.qt_or_skip()
        from meridiana.report_typst import engine
        if not engine.available():
            raise unittest.SkipTest("the typst package is not installed")
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

    def composed(self, energy=None, profile=None, **kw):
        from meridiana.report_typst import compose
        made = compose(self.p, energy or self.energy, profile=profile, **kw)
        return made, json.dumps(made.document, ensure_ascii=False)

    def chapters(self, made) -> list[str]:
        return [b["title"] for b in made.document["body"] if b.get("k") == "chapter"]

    def test_every_chapter_of_the_complete_template_is_there_in_its_order_with_the_contents(self):
        from meridiana import reports
        made, text = self.composed()
        titles = [reports.chapters()[c].title for c in reports.templates()["complete"].chapters]
        self.assertEqual(self.chapters(made), [f"{n}. {t}" for n, t in enumerate(titles, 1)])
        self.assertEqual(made.document["toc"], "cover")                  # the contents on the cover, its pages Typst's
        self.assertIsNotNone(made.document["cover"])
        for h in ("Strings (CEI 64-8/7)", "Inverter 1: Acme AC-20K", "Inverter 2: Acme AC-20K", "Checks of the strings",
                  "Checks of the inverters", "The strings on the modules", "Notes for the technical report",
                  "Values still at their default", "Register of the calculations"):
            self.assertIn(h, text)
        breaks = [b["id"] for b in made.document["body"] if b.get("k") == "chapter" and b["break"]]
        self.assertEqual(breaks, ["summary"])                            # the rest flows: no page two thirds empty

    def test_the_compact_template_writes_its_five_chapters_without_contents_with_the_author_when_chosen(self):
        from meridiana import reports
        self.p.report = {"template": "compact"}
        made, text = self.composed(profile=self.PROFILE)
        titles = [reports.chapters()[c].title for c in reports.templates()["compact"].chapters]
        self.assertEqual(self.chapters(made), [f"{n}. {t}" for n, t in enumerate(titles, 1)])
        self.assertEqual(made.document["toc"], "none")
        self.assertIsNone(made.document["cover"])
        self.assertEqual(made.document["head"]["title"], "Prova")
        for value in ("Studio di prova", "Firmatario di prova", "Albo di prova"):
            self.assertIn(value, text)
        for name in ("plan.svg", "plan_strings.svg"):
            self.assertIn(name, made.makers)
        self.assertTrue(blocks_of(made.document, "bars"))                # the energy month by month, drawn by Typst
        self.assertNotIn("R-0", text)                                    # no register in this template: no codes
        self.assertIn("Source: ", text)                                  # but the sources in words
        bare, text = self.composed()                                     # no profile: none of it
        for value in ("Studio di prova", "Firmatario di prova", "Albo di prova", "Designer"):
            self.assertNotIn(value, text)

    def test_a_chapter_turned_off_or_without_its_data_is_left_out(self):
        self.p.report = {"off": ["economics", "annexes"]}
        made, _text = self.composed()
        chapters = self.chapters(made)
        self.assertNotIn("Economics", " ".join(chapters))
        self.assertNotIn("Component data", " ".join(chapters))
        self.assertIn("7. Checks and standards", chapters)              # the numbers follow what is written
        bare = {k: v for k, v in self.energy.items() if k not in ("plant", "rules_facts", "checks", "load", "econ")}
        self.p.report = {}
        made, text = self.composed(bare)
        for h in ("Electrical system", "Strings (CEI 64-8/7)", "Notes for the technical report", "Checks and standards",
                  "Consumption and balance"):
            self.assertNotIn(h, text)
        self.assertIn("4. Energy yield", self.chapters(made))

    def test_the_strings_are_listed_by_inverter_and_input_with_their_checks_and_modules(self):
        from meridiana.ui.report import _keys_text
        plant = self.energy["plant"]
        self.assertEqual(len(plant.units), 2)
        self.assertTrue(plant.strings)
        made, text = self.composed()
        self.assertIn(f"{len(plant.strings)} strings on ", text)
        self.assertIn("proposed by Meridiana", text)
        self.assertIn("Checked at the hottest cell of the typical year", text)     # the year is there: its cells
        rows = [r for t in blocks_of(made.document, "table") for r in t["rows"] if isinstance(r, list)]
        for s in plant.strings:
            keys = _keys_text([k for _sf, k, _c in s.modules])
            self.assertIn([s.label, "Sud", str(len(s.modules)), {"m": keys}], [r[:4] for r in rows])
        self.assertIn("Modules in series within the range the input takes", text)   # the checks of each input
        self.assertIn("modules in series", text)
        # their marks drawn by the template (R138 wanted the window's symbols, not the characters ✔ ⚠ ✘ ℹ)
        self.assertIn('{"mark": "ok"}', text)
        for character in "✔⚠✘ℹ":
            self.assertNotIn(character, text)
        self.assertEqual(_keys_text(["0:0", "0:1", "0:2", "1:2", "1:1", "1:0", "3:5"]), "0:0-2, 1:2-0, 3:5")
        self.assertEqual(_keys_text(["0:0", "0:2", "0:3:1"]), "0:0, 0:2, 0:3:1")

    def test_the_plan_is_drawn_once_wide_and_the_checks_of_a_kind_of_string_once(self):
        """The plan in the layout at the whole width, not again in the summary; the strings' checks written once for
        each kind of string; the figures numbered by chapter."""
        made, text = self.composed()
        self.assertEqual([n for n in made.makers if n.startswith("plan")], ["plan.svg", "plan_strings.svg"])
        figures = blocks_of(made.document, "figure")
        plan = next(f for f in figures if f["image"] == "plan.svg")
        self.assertTrue(plan["tint"])
        self.assertGreaterEqual(plan["max_h"], 170)                       # «ampia, come in C»
        floats = blocks_of(made.document, "float")
        self.assertTrue(any(f["items"][-1].get("image") == "plan.svg" for f in floats))   # never a half empty page
        self.assertIn("What the model does not include", text)
        self.assertIn("Strings of 25 modules in series, on the inputs 1.1, 1.2, 2.1, 2.2.", text)
        self.assertEqual(text.count("Modules in series within the range the input takes"), 1)
        self.assertIn('"Figure 3.1."', text)                              # by chapter, as the sketch has them
        self.p.report = {"off": ["layout"]}
        made, _text = self.composed()
        self.assertEqual([n for n in made.makers if n.startswith("plan")], ["plan.svg", "plan_strings.svg"])

    def test_the_numbers_of_a_table_are_bare_with_the_unit_in_the_header(self):
        """A right-aligned cell holds a number (or a dash, or «free»); the checks of the chapter are grouped by area in
        group rows."""
        from meridiana import i18n
        from meridiana.report_typst.blocks import plain
        for template in ("complete", "compact"):
            self.p.report = {"template": template}
            made, text = self.composed()
            cells = []
            for t in blocks_of(made.document, "table"):
                if t["head"] and i18n._("Value and unit") in t["head"]:
                    continue                        # the steps of the methods: a value with its unit, as the window
                for row in t["rows"]:
                    if isinstance(row, list):
                        cells += [plain(row[i]) for i in t["right"]]
            self.assertGreater(len(cells), 20)
            for cell in cells:
                self.assertRegex(cell, rf"^(-?[\d.,]+|–|{i18n._('free')})$", template)
            for head in ("Azimuth, °", "Tilt, °"):
                self.assertIn(f'"{head}"', text)
        self.p.report = {}
        made, text = self.composed()
        self.assertIn("PR, %", text)
        self.assertEqual(text.count('{"group": "Rules and report notes"}'), 1)      # once, as a group

    def test_every_table_is_ruled_and_every_number_has_a_line_in_the_register(self):
        """The codes in the tables and on the cards are lines of the register's chapter (study 24: «R-040.07» leads
        to one line); the steps of the calculations keep their codes in the methods."""
        made, text = self.composed()
        register = next(b for b in made.document["body"] if b.get("id") == "register")
        self.assertTrue(register)
        index = made.document["body"].index(register)
        listed = set()
        for t in blocks_of({"body": made.document["body"][index:]}, "table"):
            listed |= {r[0] for r in t["rows"] if isinstance(r, list)}
        used = set()
        for t in blocks_of({"body": made.document["body"][:index]}, "table"):
            if t["source"]:
                used |= {r[-1] for r in t["rows"] if isinstance(r, list)}
        for f in blocks_of({"body": made.document["body"][:index]}, "facts"):
            used |= {r[2] for r in f["rows"] if len(r) > 2 and r[2]}
        self.assertGreater(len(used), 50)
        self.assertLessEqual(used, listed)
        self.assertTrue(all(re.fullmatch(r"R-\d{3}\.\d{2}", c) for c in used), sorted(used)[:5])
        self.assertIn("R-010.01", text)                                   # the first step, «Position of the sun»

    def test_the_checks_and_the_notes_of_the_rules_carry_their_sources(self):
        _made, text = self.composed()
        text = json.loads(json.dumps(text))
        self.assertIn("4. Minimum renewable capacity obligation", text)            # obligation "new" (D.Lgs. 199/2021)
        self.assertIn("N24", text)                                                  # the rule's id beside its source
        notes = rules.notes(self.energy["rules_facts"])
        for _title, chosen in notes:
            for r, _paragraphs in chosen:
                self.assertIn(json.dumps(r.source(), ensure_ascii=False)[1:-1], text)
        for it in self.energy["checks"]:
            if it.source:
                self.assertIn(json.dumps(it.source, ensure_ascii=False)[1:-1], text)

    def test_the_report_says_what_the_model_leaves_out_and_draws_its_charts_plans_and_formulas(self):
        made, text = self.composed()
        for kind in ("bars", "waterfall", "balance", "cash", "carpet"):
            self.assertTrue(blocks_of(made.document, kind), kind)
        for name in ("plan.svg", "plan_strings.svg", "carpet.png"):
            self.assertIn(name, made.makers)
        self.assertTrue(any(n.startswith("f_") and n.endswith(".svg") for n in made.makers))   # the formulas
        self.assertIn("Bifacial modules", text)
        self.assertLess(text.index("9. Parameters and methods"), text.index("What the model does not include"))
        self.assertLess(text.index("What the model does not include"), text.index("Values still at their default"))
        # every step of the chain in the waterfall, the poa written on its total
        chain = [s for s in self.energy["sim"].chain]
        items = blocks_of(made.document, "waterfall")[0]["items"]
        self.assertEqual(len(items), len(chain) + 1)                     # and the energy delivered at the end
        self.assertTrue(items[1]["extra"].startswith("+"))

    def test_before_the_year_the_strings_are_said_checked_at_pvsyst_design_conditions(self):
        from meridiana.energy import plant as plants
        from meridiana.ui.report import _keys_text
        early = plants.build(self.p, self.results)
        self.assertFalse(early.year)
        self.assertTrue(early.strings)
        made, text = self.composed({"plant": early, "results": self.results})
        self.assertIn("Electrical system", text)
        self.assertIn("Inverter 1: Acme AC-20K", text)
        self.assertIn("PVsyst's design conditions", text)                    # the conditions, said
        self.assertIn("The strings on the modules", text)
        first = _keys_text([k for _sf, k, _c in early.strings[0].modules])
        self.assertRegex(first, r":\d+-\d+")                               # the modules, a row by its ends
        self.assertIn(first, text)
        self.assertIn("Modules in series within the range the input takes", text)
        self.assertNotIn("Energy yield", text)                             # no year, no chapter of the year

    def test_the_optimizers_of_a_solaredge_inverter_with_their_checks_and_sources(self):
        """Task 22: the Electrical system writes the optimizers, the strings' optimizers and power and SolarEdge's
        checks with their documents; the annexes the optimizer's data; the compact template its sentence."""
        import copy

        from meridiana import catalog
        from meridiana.energy import plant as plants
        from meridiana.report_typst import compose
        p = copy.deepcopy(self.p)
        se = next(r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None) if r["model"] == "SE50K")
        p.energy["inverters"] = [{"record": se, "count": 1, "name": ""}]
        early = plants.build(p, self.results)
        self.assertTrue(early.optimized and early.strings)

        def text(project):
            return json.dumps(compose(project, {**self.energy, "plant": early}).document, ensure_ascii=False)
        found = text(p)
        self.assertIn("Power optimizers SolarEdge S1000, 2 modules on each", found)
        self.assertIn("DS-000105-IT", found)                                   # SolarEdge's table, cited
        self.assertIn("Synergy unit 2", found)
        self.assertIn("Optimizers in the string within SolarEdge's range", found)
        self.assertTrue(all(s.state == "ok" for s in early.strings), [s.why for s in early.strings])
        self.assertIn("Power optimizer: SolarEdge S1000", found)              # the annex
        p.report = {"template": "compact"}
        self.assertIn("Power optimizers SolarEdge S1000", text(p))

    def export(self, profile=None) -> Path:
        from meridiana.ui import report
        path = Path(tempfile.mkdtemp()) / "relazione.pdf"
        report.export_pdf(self.p, self.energy, path, profile)
        return path

    def test_the_contents_say_the_pages_the_chapters_fall_on(self):
        from meridiana import reports
        from meridiana.ui import report
        path = self.export()
        pages = texts(path)
        chosen = reports.plan(self.p, report._with_notes(self.energy))
        found = {}
        for n, c in enumerate(chosen, 1):
            m = re.search(rf"{n}\. {re.escape(c.title)}\s*(\d+)", pages[0])
            self.assertIsNotNone(m, c.title)
            found[c.id] = int(m.group(1))
        self.assertEqual(found["summary"], 2)                              # the cover, then the summary
        self.assertEqual(list(found.values()), sorted(found.values()))
        for n, c in enumerate(chosen, 1):
            page = pages[found[c.id] - 1]
            self.assertIn(f"{n}. {c.title}", page, c.id)                   # the heading on the page the contents say
        for i, t in enumerate(pages):
            self.assertIn(f"page {i + 1} of {len(pages)}", t)
        self.assertNotIn("Designer", pages[0])                             # no profile: nobody on the cover

    def test_the_users_texts_go_into_the_pdf_as_they_are(self):
        import copy
        strange = r'Studio #1 $5 *a* _b_ \c [d] @e <f> #read("../x")'
        p = copy.deepcopy(self.p)
        p.name = strange
        p.report = {"client": strange, "revision": strange}
        p.subfields[0].name = strange
        from meridiana.ui import report
        path = Path(tempfile.mkdtemp()) / "strano.pdf"
        profile = {**self.PROFILE, "firm": strange, "signer": strange}
        report.export_pdf(p, self.energy, path, profile)
        flat = "".join("".join(t.split()) for t in texts(path))
        self.assertGreater(flat.count("".join(strange.split())), 10)       # cover, headers, footers, tables

    def test_the_logo_is_in_the_corner_of_the_header_and_a_broken_one_is_left_out(self):
        from pypdf import PdfReader
        from PySide6.QtGui import QColor, QImage
        folder = Path(tempfile.mkdtemp())
        image = QImage(120, 40, QImage.Format.Format_RGB32)
        image.fill(QColor("#2b3440"))
        logo = folder / "logo.png"
        image.save(str(logo))
        broken = folder / "rotto.png"
        broken.write_bytes(b"\x89PNG\r\n\x1a\nnot really")
        self.p.report = {"template": "compact", "off": ["electrical"]}

        def logos(path):
            out = []
            for page in PdfReader(str(path)).pages:
                xo = page["/Resources"].get("/XObject") or {}
                out.append(sum(1 for k in xo if xo[k].get_object()["/Subtype"] == "/Image"
                               and xo[k].get_object()["/Width"] == 120))
            return out
        with_logo = self.export({**self.PROFILE, "logo": str(logo)})
        self.assertTrue(all(n == 1 for n in logos(with_logo)), logos(with_logo))
        for profile in ({**self.PROFILE, "logo": str(broken)}, {**self.PROFILE, "logo": str(folder / "gone.png")}):
            path = self.export(profile)
            self.assertTrue(all(n == 0 for n in logos(path)))
            self.assertIn("Studio di prova", texts(path)[0])                 # the report made all the same

    def test_the_accent_comes_from_the_profile_and_is_blue_by_default(self):
        from meridiana import reports
        made, _text = self.composed(profile={**self.PROFILE, "accent": "#A0522D"})
        self.assertEqual(made.document["accent"], "#a0522d")
        made, _text = self.composed(profile={**self.PROFILE, "accent": "not a colour"})
        self.assertEqual(made.document["accent"], reports.ACCENT)
        self.assertEqual(reports.ACCENT, "#1c6e8c")

    def test_in_italian_the_numbers_have_the_decimal_comma(self):
        if not (Path(_setup.ROOT) / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo").exists():
            self.skipTest("the catalogues are not compiled (tools/compile_po.py)")
        from meridiana import i18n
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        made, text = self.composed()
        self.assertEqual(made.document["lang"], "it")
        sim = self.energy["sim"]
        self.assertIn(i18n.number(100 * sim.pr, 1), text)
        self.assertIn(",", i18n.number(100 * sim.pr, 1))
        self.assertIn("1. Sintesi", self.chapters(made))

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
        path = self.export()
        sizes = sizes_mm(path)
        a4 = (210, 297)
        first = sizes.index((148, 210))
        self.assertEqual(sizes[first:first + 2], [(148, 210)] * 2)
        self.assertEqual(sizes[first + 2:], [a4, (200, 100), (200, 100), (200, 100)])   # the second, behind its page
        self.assertEqual(sizes[:first], [a4] * first)                    # the report before: cover to register
        pages = texts(path)
        # the contents say the pages of the PDF: the page before each attachment
        self.assertRegex(pages[0], rf"Attachment 1: Modulo di prova\s*{first}\b")
        self.assertRegex(pages[0], rf"Attachment 2: Scheda inverter\s*{first + 3}\b")
        self.assertNotIn("Manca", pages[0])                                             # left out, not listed
        self.assertIn(f"page {first} of {len(sizes)}", pages[first - 1])                # the separator's footer
        self.assertIn(f"page {first + 3} of {len(sizes)}", pages[first + 2])             # counted past the first
        # the compact template: no contents, the attachments at the end all the same
        self.p.report = {"template": "compact", "attachments": items}
        sizes = sizes_mm(self.export())
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
        made, text = self.composed(only="methods")
        self.assertEqual([c.id for c in made.chosen], ["methods"])
        self.assertEqual(made.document["head"]["kicker"], "REGISTER OF THE CALCULATIONS")
        self.assertIn('"Parameters and methods"', text)
        self.assertIn("What the model does not include", text)
        self.assertTrue(made.makers and all(n.startswith("f_") for n in made.makers))   # the formulas, nothing else
        body = json.dumps(made.document["body"], ensure_ascii=False)
        for other in ("Contents", "1. Summary", "Attachment 1"):
            self.assertNotIn(other, body)
        self.assertIsNone(made.document["cover"])

    # the 3D pictures

    def test_the_3d_pictures_are_on_the_cover_in_the_summary_and_in_the_layout_when_qt_quick_3d_can_draw_them(self):
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QColor, QImage

        from meridiana.ui import report, report_3d
        image = QImage(220, 144, QImage.Format.Format_RGB32)
        image.fill(QColor("#2f4f7f"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        png = bytes(data.data())
        asked = []
        with mock.patch.object(report_3d, "available", return_value=True), \
                mock.patch.object(report_3d, "picture", side_effect=lambda p, r, vid, size=None: asked.append(vid) or png):
            pictures = report._pictures(self.p, self.energy)
            made, text = self.composed(pictures=pictures)
            self.assertEqual(made.document["cover"]["image"], "view_south_east.png")
            fill = blocks_of(made.document, "fill_figure")
            self.assertEqual([f["image"] for f in fill], ["view_south_west.png"])      # the summary's, the page's rest
            self.assertIn("From the south-west", text)
            views = [f for f in blocks_of(made.document, "figure") if f["image"].startswith("view_")]
            self.assertEqual([f["image"] for f in views], ["view_south_east.png"])     # the layout's, whole width
            self.p.report = {"template": "compact"}
            made, text = self.composed(pictures=pictures)
            views = [f["image"] for f in blocks_of(made.document, "figure") if f["image"].startswith("view_")]
            self.assertEqual(views, ["view_south_east.png"])
            self.assertEqual([f["image"] for f in blocks_of(made.document, "fill_figure")], ["view_south_west.png"])
            self.p.report = {"template": "compact", "off": ["electrical"]}
            self.export()
        self.assertEqual(sorted(asked), ["south_east", "south_west"])                    # each made once for the PDF
        with mock.patch.object(report_3d, "available", return_value=False):          # the software renderer
            self.assertEqual(report._pictures(self.p, self.energy), {})
            self.p.report = {}
            made, text = self.composed(pictures={})
        self.assertFalse([n for n in made.makers if n.startswith("view_")])
        self.assertNotIn("From the south-east", text)
        self.assertEqual(made.document["cover"]["image"], "plan.svg")                  # the cover not left empty

    def test_the_white_around_a_3d_picture_is_trimmed(self):
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QColor, QImage

        from meridiana.ui import report_3d
        image = QImage(400, 300, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        for x in range(100, 300):
            for y in range(120, 180):
                image.setPixelColor(x, y, QColor("#2f4f7f"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        cut = QImage.fromData(report_3d.trimmed(bytes(data.data())))
        self.assertEqual((cut.width(), cut.height()), (212, 72))         # the scene and 3 % of it around

    def test_the_pdf_is_written_whole_quickly_and_the_preview_has_its_pages(self):
        from meridiana.ui.report import export_pdf, preview_steps
        for template in ("complete", "compact"):
            with self.subTest(template=template):
                self.p.report = {"template": template}
                path = Path(tempfile.mkdtemp()) / "relazione.pdf"
                export_pdf(self.p, self.energy, path, self.PROFILE)            # the formulas drawn once
                t = time.perf_counter()
                export_pdf(self.p, self.energy, path, self.PROFILE)
                took = time.perf_counter() - t
                self.assertLess(took, 6.0)                                     # some 0,5-1,5 s here, offscreen
                data = path.read_bytes()
                self.assertTrue(data.startswith(b"%PDF"))
                self.assertIn(b"%%EOF", data[-1024:])
                self.assertGreater(len(data), 20000)
                self.assertFalse(path.with_name(path.name + ".part").exists())
                pages: list = []
                for _f, _w in preview_steps(self.p, self.energy, 400, pages, self.PROFILE):
                    pass
                self.assertEqual(len(pages), len(sizes_mm(path)))
                self.assertEqual(pages[0].width(), 400)
                self.assertAlmostEqual(pages[0].height() / pages[0].width(), 297 / 210, delta=0.01)   # A4
                from pypdf import PdfReader
                info = PdfReader(io.BytesIO(data)).metadata
                self.assertTrue(str(info.get("/Creator", "")).startswith("Meridiana"))
                self.assertEqual(info.get("/Author"), "Firmatario di prova")


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
        # a profile written before the accent (R314) reads with it empty: the blue of the report
        old = reports.clean_profile({"name": "A", "logo": "x.png"})
        self.assertEqual((old["accent"], reports.accent_of(old)), ("", reports.ACCENT))

    def test_every_chapter_of_every_template_has_a_writer(self):
        from meridiana import reports
        from meridiana.report_typst.chapters import BUILDERS
        for t in reports.templates().values():
            for c in t.chapters:
                self.assertIn(c, reports.chapters())
                self.assertIn(c, BUILDERS)


class Formulas(unittest.TestCase):
    """The formulas of the pages and of the report, drawn by matplotlib's mathtext (ui/pedigree.formula_png, and as
    SVG for the report: report_typst/figures.formula_svg)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_formula_is_drawn_once(self):
        from meridiana.report_typst.figures import formula_svg
        from meridiana.ui.pedigree import formula_png
        formula_png.cache_clear()
        first = formula_png(r"E = P \cdot t", "#000000", 100.0, 13.0)
        again = formula_png(r"E = P \cdot t", "#000000", 100.0, 13.0)
        self.assertIs(first, again)
        self.assertEqual(formula_png.cache_info().hits, 1)
        svg = formula_svg(r"E = P \cdot t", 12.0)
        self.assertIs(svg, formula_svg(r"E = P \cdot t", 12.0))
        self.assertIn(b"<svg", svg[:400])


if __name__ == "__main__":
    unittest.main()
