"""The report's engine without Qt (report_typst/engine.py and template.typ, R314): documents written by hand, compiled by
Typst and read back with pypdf. A row of a table never split between two pages and its header on every page; the texts
of the user printed as they are, never read as markup; nothing read outside the report's folder; the program's fonts
and no font of the system; the logo in the header's corner or nothing in its place; the time of a compilation."""

import copy
import io
import time
import unittest

TEXTS = {"page_of": "page {n} of {total}", "contents": "Contents", "report": "Technical report",
         "attachment": "Attachment"}
STRANGE = r'#set text(red) $x^2$ *bold* _it_ \n [link] @ref <label> #read("../secret.txt") `raw` // c'


def document(body: list, **doc) -> dict:
    head = {"title": "Prova", "author": "", "logo": None, "logo_file": "", "head_title": "Head title",
            "head_sub": "", "revision": "Rev. 0", "date": "02/11/2026", "foot_left": "", "foot_left2": "",
            "foot_centre": "", "foot_centre2": "", "foot_right2": ""}
    return {"lang": "en", "accent": "#1c6e8c", "missing": [], "attachments": [], "texts": TEXTS,
            "doc": {**head, **doc}, "cover": None, "head": None, "toc": "none", "body": body}


def pages_text(pdf: bytes) -> list[str]:
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]


def squeeze(text: str) -> str:
    return "".join(text.split())


class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.report_typst import engine
        if not engine.available():
            raise unittest.SkipTest("the typst package is not installed")
        cls.engine = engine

    def compile(self, doc: dict, images: dict | None = None):
        with self.engine.Build() as build:
            for name, data in (images or {}).items():
                build.add(name, data)
            return build.compile(doc)

    def test_a_row_is_never_split_between_two_pages_and_the_header_is_on_every_page(self):
        from meridiana.report_typst import blocks
        long = "a long description that takes a few lines of the cell, " * 7       # 6 lines: a paragraph that can split
        rows = [(f"Start{k:02d}", f"{long} End{k:02d}", f"{k},5") for k in range(50)]
        result = self.compile(document([blocks.table(rows, ["Column", "What", "Value"], right=(2,))]))
        texts = pages_text(result.pdf)
        self.assertGreaterEqual(len(texts), 3)
        for k in range(50):
            start = [i for i, t in enumerate(texts) if f"Start{k:02d}" in t]
            end = [i for i, t in enumerate(texts) if f"End{k:02d}" in squeeze(t)]
            self.assertEqual(len(start), 1, k)
            self.assertEqual(start, end, f"row {k} split between pages")
        for i, t in enumerate(texts):
            with self.subTest(page=i + 1):
                self.assertIn("ColumnWhatValue", squeeze(t))            # the header again on every page
                self.assertIn(f"page {i + 1} of {len(texts)}", t)

    def test_the_users_texts_are_printed_as_they_are_never_read_as_markup(self):
        from meridiana.report_typst import blocks
        doc = document([blocks.para(STRANGE), blocks.table([(STRANGE, "1")], [STRANGE, "n"]),
                        blocks.facts([(STRANGE, STRANGE)]), blocks.section(STRANGE)],
                       head_title=STRANGE, head_sub=STRANGE, foot_left=STRANGE, title=STRANGE)
        result = self.compile(doc)
        text = squeeze("".join(pages_text(result.pdf)))
        self.assertGreaterEqual(text.count(squeeze(STRANGE)), 6, text[:400])   # header, footer and the body's five

    def test_nothing_outside_the_reports_folder_is_read(self):
        import tempfile
        from pathlib import Path

        import typst
        outside = Path(tempfile.mkdtemp()) / "secret.txt"
        outside.write_text("secret", encoding="utf-8")
        with self.engine.Build() as build:
            for source in (f'#read("../{outside.parent.name}/secret.txt")', f'#read("{outside.as_posix()}")',
                           f'#image("{outside.as_posix()}")'):
                with self.subTest(source=source), self.assertRaises(typst.TypstError):
                    typst.compile(source.encode(), root=str(build.root), font_paths=self.engine.fonts())
            with self.assertRaises(ValueError):
                build.add("../escape.png", b"x")                       # the names are the program's, checked

    def test_the_programs_fonts_and_none_of_the_system(self):
        from pypdf import PdfReader

        from meridiana.report_typst import blocks
        families = set(self.engine.fonts().families())
        self.assertLessEqual({"IBM Plex Sans", "IBM Plex Math", "IBM Plex Mono"}, families)
        # the fonts inside Typst may stay (for a letter neither of ours has); the system's are never asked
        self.assertFalse({f for f in families if not f.startswith("IBM Plex")} -
                         {"DejaVu Sans Mono", "Libertinus Serif", "New Computer Modern", "New Computer Modern Math"})
        doc = document([blocks.para("Potenza 310,50 kWp, 86,0 %, 1.893 kWh/m², −10 °C, ±2 %, γ, Ω"),
                        blocks.para([blocks.mark("ok"), " ", blocks.mark("warn"), " ", blocks.mark("fail"), " ",
                                     blocks.mark("info")])])
        result = self.compile(doc)
        self.assertEqual(result.warnings, [])
        used = set()
        for page in PdfReader(io.BytesIO(result.pdf)).pages:
            for font in page["/Resources"]["/Font"].values():
                used.add(str(font.get_object()["/BaseFont"]).split("+")[-1])
        self.assertTrue(any("IBMPlexSans-Light" in f for f in used), used)      # the text, light (R460)
        self.assertTrue(any(f.startswith("IBMPlexSans") and "Light" not in f for f in used), used)   # the footer
        self.assertFalse([f for f in used if not f.startswith("IBMPlex")], used)

    def test_the_logo_is_in_the_corner_of_every_header_and_without_it_the_header_closes_up(self):
        from pypdf import PdfReader

        from meridiana.report_typst import blocks, figures
        png = figures._png([b"\x10\x60\x80" * 40] * 20, 40)
        body = [blocks.para("Testo")] + [{"k": "pagebreak"}, blocks.para("Ancora")]
        with_logo = self.compile(document(copy.deepcopy(body), logo="logo.png"), {"logo.png": png})
        without = self.compile(document(copy.deepcopy(body)))

        def images(pdf):
            out = []
            for page in PdfReader(io.BytesIO(pdf)).pages:
                xobjects = page["/Resources"].get("/XObject") or {}
                out.append(sum(1 for k in xobjects if xobjects[k].get_object()["/Subtype"] == "/Image"))
            return out
        self.assertEqual(images(with_logo.pdf), [1, 1])
        self.assertEqual(images(without.pdf), [0, 0])
        self.assertIn("Head title", pages_text(without.pdf)[0])

    def test_a_file_that_is_no_image_is_not_taken_for_one(self):
        from meridiana.report_typst import engine
        self.assertEqual(engine.image_format(b"\x89PNG\r\n\x1a\n...."), "png")
        self.assertEqual(engine.image_format(b"\xff\xd8\xff\xe0"), "jpg")
        self.assertIsNone(engine.image_format(b"%PDF-1.7"))
        with self.engine.Build() as build:
            build.add("logo.png", b"\x89PNG\r\n\x1a\nbroken")
            self.assertFalse(build.usable_image("logo.png"))           # a broken file: the report goes on without

    def test_the_attachments_separators_say_their_pages_and_the_pages_count_them(self):
        doc = document([{"k": "p", "t": "Corpo", "style": ""},
                        {"k": "attachment", "n": 1, "id": "attachment:1", "title": "Allegato uno", "pages": 3, "items": []},
                        {"k": "attachment", "n": 2, "id": "attachment:2", "title": "Allegato due", "pages": 2, "items": []}])
        doc["attachments"] = [{"k": 1, "title": "Allegato uno", "pages": 3}, {"k": 2, "title": "Allegato due", "pages": 2}]
        result = self.compile(doc)
        self.assertEqual(result.after, {1: 2, 2: 3})
        texts = pages_text(result.pdf)
        self.assertIn("page 1 of 8", texts[0])                      # 3 of the report, 5 of the attachments
        self.assertIn("page 2 of 8", texts[1])
        self.assertIn("page 6 of 8", texts[2])                      # after the three pages of the first

    def test_a_document_compiles_in_well_under_a_second(self):
        from meridiana.report_typst import blocks
        rows = [(f"Riga {k}", f"{k * 1.5:.1f}", f"{k},0") for k in range(40)]
        body = [blocks.section("Prova"), blocks.table(rows, ["A", "B", "C"], right=(1, 2)), blocks.facts(rows[:8])] * 3
        self.compile(document(body))                                  # the fonts read once
        t = time.perf_counter()
        self.compile(document(body))
        self.assertLess(time.perf_counter() - t, 1.5)


class Register(unittest.TestCase):
    def test_codes_follow_the_groups_and_a_step_is_found_by_the_end_of_its_key(self):
        from meridiana.energy.pedigree import Quantity, Record, Step
        from meridiana.report_typst.register import Register as R
        rec = Record("Produzione", [Step("sun", "Sole", "", ""), Step("s1.0.poa", "Piano", "", "",
                                                                     result=Quantity("", "G", 3.0, "kWh/m²"))])
        reg = R(True, [rec])
        self.assertEqual(reg.step("poa"), ("R-010.02", "Piano"))
        self.assertEqual(reg.code("poa", "Tabella", "x", "y"), "R-010.02")
        self.assertEqual(reg.code("dal progetto", "Tabella", "Riga", "1"), "R-020.01")
        self.assertEqual(reg.groups[1].rows, [("R-020.01", "Riga", "1", "dal progetto")])
        off = R(False, [rec])
        self.assertEqual(off.code("poa", "Tabella", "x", "y"), "")
        self.assertEqual(off.words("poa"), "Piano")


class Steps(unittest.TestCase):
    """R460: a step as the report and the window lay it out (report_typst/steps.py), one source for both."""

    def test_a_step_numbered_on_with_its_values_split_on_the_comma_and_the_numbers_put_in(self):
        from meridiana.energy.pedigree import Quantity, Record, Source, Step
        from meridiana.i18n import setup
        from meridiana.report_typst import steps
        setup("it")
        try:
            worked = [r"E = 10{,}25\,\mathrm{kW} \cdot 2{,}1\,\mathrm{h} = \mathbf{21{,}5}\,\mathrm{kWh}"]
            rec = [Record("A", [Step("a", "Uno", r"E = P \cdot t", "", [Quantity("P", "Potenza", 10.25, "kW",
                                                                              Source("data", "Scheda", "p. 2"))],
                                     Quantity("E", "Energia", 21.5, "kWh", decimals=1), worked=worked,
                                     example="Esempio: 14 luglio")]),
                   Record("B", [Step("b", "Scelta", "", ""), Step("c", "Due", "x = 1", "")])]
            first, second = steps.numbered(rec, 9)
            self.assertEqual([s["eq"] for s in first + second], ["9.1", "", "9.2"])
            q = first[0]["inputs"][0]
            self.assertEqual((q["value"], q["int"], q["rest"]), ("10,25 kW", "10", ",25 kW"))
            # R479: the formula again with the numbers, after the hour of the example; no list «symbol = value»
            self.assertNotIn("values", first[0])
            self.assertEqual((first[0]["worked"], first[0]["example"]), (worked, "Esempio: 14 luglio"))
            self.assertEqual((second[0]["worked"], second[1]["worked"]), ([], []))
            self.assertEqual(first[0]["result"]["value"], "21,5 kWh")
            self.assertEqual(steps.parts("–"), ("", ""))
            plain = [{"title": "A", "steps": [{"key": "a", "title": "Uno", "formula": "E", "explanation": "",
                                               "inputs": [{"symbol": "P", "label": "Potenza", "value": 3,
                                                           "unit": "kW", "decimals": 0,
                                                           "source": {"kind": "data", "label": "Scheda", "ref": ""}}],
                                               "result": None, "reference": ""}]}]
            view = steps.for_window(plain)[0][0]
            self.assertEqual((view["eq"], view["inputs"][0]["value"], view["inputs"][0]["source"]),
                             ("1", "3 kW", "dato: Scheda"))
        finally:
            setup("en")


class NoPlant(unittest.TestCase):
    def test_a_project_without_modules_is_said_not_stopped_on_a_division_by_zero_r459(self):
        from _fixtures import capannone

        from meridiana.report_typst.compose import NoPlant, compose, no_plant
        problem = no_plant({"results": {}})
        self.assertIn("no module is laid", problem)
        with self.assertRaises(NoPlant) as caught:
            compose(capannone(), {"results": {}})
        self.assertEqual(str(caught.exception), problem)


if __name__ == "__main__":
    unittest.main()
