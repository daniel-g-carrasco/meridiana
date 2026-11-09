"""The editable exports of the report (report_typst/editable.py, odt.py, word.py): a document written by hand, written as an
ODT and as a DOCX and read back from the zip. Real headings with outline levels, the contents, the formulas (ODF objects
and OMML), the Plex fonts embedded, no blue in any XML or picture, the texts of the user written as they are, the time.
Skipped when a library of the exports (odfpy, python-docx, lxml, latex2mathml) or Typst is missing."""

import colorsys
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

NEEDED = ("odf", "docx", "lxml", "latex2mathml", "typst", "PIL")
MISSING = [m for m in NEEDED if importlib.util.find_spec(m) is None]
STRANGE = r'#set text(red) $x^2$ *bold* _it_ \n [link] @ref <label> #read("../secret.txt") `raw` // c'
TEXTS = {"page_of": "page {n} of {total}", "contents": "Contents", "report": "Technical report", "attachment": "Attachment",
         "where": "where:", "with_values": "With the values:", "result": "result", "reference": "Reference",
         "symbol": "Symbol", "quantity": "Quantity", "value": "Value", "source": "Source", "plant": "Plant"}
HEX = re.compile(r'(?:color|fill|val|lastClr|fo:background-color|fo:color|svg:stroke-color|draw:fill-color)="#?([0-9A-Fa-f]{6})"')


def bluish(rgb) -> bool:
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    return 170 / 360 <= h <= 275 / 360 and s > 0.08 and v > 0.08


def document() -> dict:
    step = {"k": "step", "code": "R-010.01", "title": "Energy", "explanation": ["The ", {"b": "energy"}, " of the year."],
            "tex": r"E = P \cdot t", "eq": "9.1",
            "inputs": [{"symbol": r"\eta_{STC}", "label": "efficiency", "value": "21,0 %", "int": "21", "rest": ",0 %",
                        "source": ""},
                       {"symbol": "P", "label": "power", "value": "12,5 kW", "int": "12", "rest": ",5 kW",
                        "source": [{"b": "given"}, ": by the user"]},
                       {"symbol": "t", "label": "hours", "value": "1.200 h", "int": "1.200", "rest": " h", "source": ""}],
            "result": {"symbol": "E", "label": "energy", "value": "15.000,0 kWh", "int": "15.000", "rest": ",0 kWh", "source": ""},
            # R479: the hour of the example and the formula again with the numbers, ending in the result
            "example": "Example: 14 July, 13:00 standard time (UTC+1).",
            "worked": [r"E = 12{,}5\,\mathrm{kW} \cdot 1.200\,\mathrm{h} = \mathbf{15.000{,}0}\,\mathrm{kWh}",
                       r"E = 15{,}0\,\mathrm{MWh}"], "reference": "IEC 61724"}
    body = [
        {"k": "chapter", "title": "1. First chapter", "id": "summary", "break": True},
        {"k": "section", "t": "The first section", "c": "acc"},
        {"k": "p", "t": ["Plain, ", {"b": "bold"}, " and ", {"m": "muted"}, " words."], "style": ""},
        {"k": "p", "t": STRANGE, "style": ""},
        {"k": "table", "head": ["Month", "Energy, kWh"], "rows": [["jan", "1.234,5"], ["feb", "12,25"], {"group": "Total"},
                                                                  ["all", "1.246,75"]],
         "right": [1], "widths": [1.0, 1.0], "result": 3, "source": False},
        {"k": "facts", "rows": [["Peak power", "358,56 kWp"], ["Energy", "425.353 kWh"]], "strong": True, "ratio": [5, 6]},
        {"k": "section", "t": "The calculation", "c": "sun"},
        step,
        {"k": "bars", "labels": ["jan", "feb", "mar"], "h": 30.0,
         "series": [{"name": "Calculated", "color": "sun", "values": [1.0, 2.0, 3.0], "texts": None}]},
        {"k": "figure", "image": "plain.png", "caption": [{"b": "Figure 1.1."}, " A small picture"], "max_h": 60.0,
         "tint": False, "inset": 0, "chips": None},
        {"k": "figure", "image": "view_small.png", "caption": None, "max_h": 60.0, "tint": False, "inset": 0, "chips": None},
        {"k": "list", "items": ["first point", ["second ", {"b": "point"}]]},
        # R506: two columns side by side, as the PDF's grid: a section and facts on the left, a table on the right
        {"k": "two", "ratio": [5, 6],
         "left": [{"k": "section", "t": "Left column", "c": "acc"},
                  {"k": "facts", "rows": [["Left fact", "1,0 kW"]], "strong": False, "ratio": [5, 6]}],
         "right": [{"k": "section", "t": "Right column", "c": "acc"},
                   {"k": "table", "head": ["A", "B"], "rows": [["x", "1,5"]], "right": [1], "widths": [1.0, 1.0],
                    "result": -1, "source": False}]},
        {"k": "chapter", "title": "2. Second chapter", "id": "plant", "break": True},
        {"k": "p", "t": "Closing words.", "style": "muted"},
    ]
    head = {"title": "Test", "author": "A. Author", "logo": None, "logo_file": "", "head_title": "Head title",
            "head_sub": "Client", "revision": "Rev. 1", "date": "06/11/2026", "foot_left": "Studio", "foot_left2": "Address",
            "foot_centre": "Test", "foot_centre2": "Rev. 1", "foot_right2": "phone", "doc_title": "Technical report",
            "doc_sub": "Sub", "doc_short": "Report", "logo_placeholder": True}
    return {"lang": "en", "accent": "#1c6e8c", "missing": [], "attachments": [], "texts": TEXTS, "doc": head, "cover": None,
            "head": None, "toc": "page", "body": body, "tex": {}}


def picture(path: Path, colour=(120, 110, 100)) -> None:
    from PIL import Image
    Image.new("RGB", (120, 80), colour).save(path)


@unittest.skipIf(MISSING, "missing: " + ", ".join(MISSING))
class EditableExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.report_typst import editable, engine
        try:
            cls.build = engine.Build()
        except engine.EngineMissing as error:
            raise unittest.SkipTest(str(error)) from error
        cls.folder = tempfile.TemporaryDirectory()
        picture(cls.build.root / "plain.png")
        picture(cls.build.root / "view_small.png", (200, 195, 185))
        cls.stats, cls.path = {}, {}
        for kind in ("odt", "docx"):
            cls.path[kind] = Path(cls.folder.name) / f"report.{kind}"
            # without LibreOffice's measure: the files as the program writes them (test_libreoffice_measure has it)
            cls.stats[kind] = editable.export(document(), cls.build.root, cls.path[kind], kind, measure=False)

    @classmethod
    def tearDownClass(cls):
        cls.build.close()
        cls.folder.cleanup()

    def zip(self, kind):
        z = zipfile.ZipFile(self.path[kind])
        self.addCleanup(z.close)
        self.assertIsNone(z.testzip())
        return z

    def test_stats_and_time(self):
        for kind in ("odt", "docx"):
            stats = self.stats[kind]
            # R506: formula objects only for the step's equation and its 2 lines with the numbers; the symbols are text
            self.assertEqual(stats["formulas"], 3, kind)
            self.assertGreaterEqual(stats["images"], 3, kind)     # the chart and the two figures
            self.assertEqual(stats["tables"], 5, kind)            # the table, the facts, the step's, the two columns'
            self.assertFalse(stats["measured"], kind)
            self.assertGreaterEqual(stats["fonts"], 5, kind)
            self.assertLess(stats["seconds"], 10, kind)

    def test_odt_structure(self):
        z = self.zip("odt")
        self.assertEqual(z.read("mimetype"), b"application/vnd.oasis.opendocument.text")
        manifest = z.read("META-INF/manifest.xml").decode("utf-8")
        formulas = manifest.count('media-type="application/vnd.oasis.opendocument.formula"')
        self.assertEqual(formulas, self.stats["odt"]["formulas"])
        for n in range(1, formulas + 1):
            self.assertIn(f"Object {n}/content.xml", z.namelist())
        content = z.read("content.xml").decode("utf-8")
        self.assertRegex(content, r'<text:h [^>]*text:outline-level="1"')
        self.assertRegex(content, r'<text:h [^>]*text:outline-level="2"')
        self.assertIn("<text:table-of-content", content)
        self.assertIn("The first section", content)
        fonts = [n for n in z.namelist() if n.startswith("Fonts/")]
        self.assertEqual(len(fonts), self.stats["odt"]["fonts"])
        self.assertIn("IBMPlexSans-SemiBold.ttf", " ".join(fonts))
        styles = z.read("styles.xml").decode("utf-8")
        for name in ("Heading_20_1", "Body", "Caption", "Source", "Muted", "Cell", "CellHead"):
            self.assertIn(f'style:name="{name}"', styles)
        self.assertIn('fo:break-before="page"', styles)
        self.assertIn('fo:keep-with-next="always"', styles)
        self.assertIn("text:page-count", z.read("styles.xml").decode("utf-8"))

    def test_odt_text_as_written(self):
        content = self.zip("odt").read("content.xml")
        root = ElementTree.fromstring(content)
        text = " ".join("".join(root.itertext()).split())
        self.assertIn(STRANGE, text)
        self.assertIn("1.234,5", text)
        self.assertIn("(9.1)", text)
        self.assertNotIn("With the values:", text)
        self.assertIn("Example: 14 July, 13:00 standard time (UTC+1).", text)

    def test_docx_structure(self):
        z = self.zip("docx")
        document_xml = z.read("word/document.xml").decode("utf-8")
        self.assertEqual(document_xml.count("<m:oMath>") + document_xml.count("<m:oMath "), self.stats["docx"]["formulas"])
        self.assertIn('w:pStyle w:val="Heading1"', document_xml)
        self.assertIn('w:pStyle w:val="Heading2"', document_xml)
        self.assertIn('TOC \\o "1-2" \\h \\z \\u', document_xml)
        self.assertIn("The first section", document_xml)     # the contents are pre-filled
        self.assertIn(" PAGE ", z.read("word/footer1.xml").decode("utf-8"))
        self.assertIn(" NUMPAGES ", z.read("word/footer1.xml").decode("utf-8"))
        self.assertNotIn("updateFields", z.read("word/settings.xml").decode("utf-8"))
        self.assertIn("embedTrueTypeFonts", z.read("word/settings.xml").decode("utf-8"))
        fonts = [n for n in z.namelist() if n.endswith(".odttf")]
        self.assertEqual(len(fonts), self.stats["docx"]["fonts"])
        styles = z.read("word/styles.xml").decode("utf-8")
        self.assertNotRegex(styles, r"w:(?:ascii|hAnsi|eastAsia|cs)Theme")
        heading = re.search(r'<w:style [^>]*w:styleId="Heading1".*?</w:style>', styles, re.S).group(0)
        self.assertIn('w:ascii="IBM Plex Sans SmBld"', heading)
        self.assertIn("w:outlineLvl", heading)

    def test_docx_tables_fixed(self):
        from lxml import etree
        root = etree.fromstring(self.zip("docx").read("word/document.xml"))
        w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        tables = list(root.iter(w + "tbl"))              # in the order of the document, the ones in the columns too
        self.assertEqual(len(tables), 6)                 # 5 tables and the one that holds the two columns
        for tbl in tables:
            self.assertEqual(tbl.find(f"{w}tblPr/{w}tblLayout").get(w + "type"), "fixed")
            grid = [int(g.get(w + "w")) for g in tbl.find(w + "tblGrid")]
            self.assertEqual(sum(grid), int(tbl.find(f"{w}tblPr/{w}tblW").get(w + "w")))
            cells = [int(tc.find(f"{w}tcPr/{w}tcW").get(w + "w")) for tc in tbl.find(w + "tr").findall(w + "tc")]
            self.assertEqual(cells, grid)
        step = tables[2]
        self.assertLess(int(step.find(w + "tblGrid")[0].get(w + "w")), 1200)   # the symbol column is narrow

    def test_symbols_as_text(self):
        """R506: a symbol is text in the cell (italic letters, real subscripts, Greek), not a formula object."""
        from meridiana.report_typst.editable import symbol_pieces
        pieces = [(p.text, p.italic, p.pos) for p in symbol_pieces(r"\eta_{200}/\eta_{STC}")]
        self.assertEqual(pieces, [("η", True, ""), ("200", False, "sub"), ("/", False, ""), ("η", True, ""),
                                  ("STC", True, "sub")])
        self.assertEqual([(p.text, p.pos) for p in symbol_pieces(r"U_{OC\,MAX}")], [("U", ""), ("OC", "sub"),
                                                                                    (" ", "sub"), ("MAX", "sub")])
        self.assertEqual(symbol_pieces(r"\bar{f_s}")[0].text, "f̄")
        self.assertIsNone(symbol_pieces(r"\frac{a}{b}"))         # a fraction stays a formula
        content = self.zip("odt").read("content.xml").decode("utf-8")
        self.assertRegex(content, r'<text:span text:style-name="Symbol">η</text:span>'
                                  r'<text:span text:style-name="SymbolSub">STC</text:span>')
        styles = self.zip("odt").read("styles.xml").decode("utf-8")
        self.assertRegex(styles, r'style:name="SymbolSub".*?style:text-position="sub')
        self.assertRegex(styles, r'style:name="Symbol".*?fo:font-style="italic"')
        document_xml = self.zip("docx").read("word/document.xml").decode("utf-8")
        self.assertRegex(document_xml, r'<w:rStyle w:val="SymbolText"/><w:vertAlign w:val="subscript"/></w:rPr>'
                                       r'<w:t>STC</w:t>')

    def test_two_columns_side_by_side(self):
        """R506: the PDF's two columns are a table of one row without rules, the left column's items in the first
        cell, the right column's in the second, at the widths of the template's grid."""
        from lxml import etree
        ns = {"table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
              "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
        root = etree.fromstring(self.zip("odt").read("content.xml"))
        columns = [t for t in root.iter("{%s}table" % ns["table"]) if t.get("{%s}name" % ns["table"]).startswith("Columns")]
        self.assertEqual(len(columns), 1)
        cells = columns[0].findall("table:table-row/table:table-cell", ns)
        self.assertEqual(len(cells), 2)
        self.assertIn("Left column", "".join(cells[0].itertext()))
        self.assertIn("Left fact", "".join(cells[0].itertext()))
        self.assertIn("Right column", "".join(cells[1].itertext()))
        self.assertEqual(len(cells[1].findall("table:table", ns)), 1)
        w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        body = etree.fromstring(self.zip("docx").read("word/document.xml")).find(w + "body")
        outer = [t for t in body.findall(w + "tbl") if t.find(f".//{w}tc/{w}tbl") is not None]
        self.assertEqual(len(outer), 1)
        self.assertEqual(outer[0].find(f"{w}tblPr/{w}tblBorders/{w}top").get(w + "val"), "nil")
        cells = outer[0].find(w + "tr").findall(w + "tc")
        self.assertIn("Left column", "".join(cells[0].itertext()))
        self.assertIn("Right column", "".join(cells[1].itertext()))
        for tc in cells:                                    # Word wants a cell to end in a paragraph
            self.assertEqual(tc[-1].tag, w + "p")

    def test_docx_columns_are_not_bound_to_what_follows(self):
        """The sintesi's second pair of columns went whole to the next page and left the bottom of page 3 empty
        (Rho, LibreOffice, 07/11/2026): a heading inside a cell keeps with the next, and a row with a paragraph that
        keeps with the next is bound to what follows the table (the 3D view, too tall for what was left). In the
        columns' cells no paragraph keeps with the next, and the row may break between pages."""
        from lxml import etree
        w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        z = self.zip("docx")
        styles = {}
        for s in etree.fromstring(z.read("word/styles.xml")).iter(w + "style"):
            ppr, based = s.find(w + "pPr"), s.find(w + "basedOn")
            keep = None if ppr is None or ppr.find(w + "keepNext") is None else ppr.find(w + "keepNext").get(w + "val", "on")
            styles[s.get(w + "styleId")] = (keep, None if based is None else based.get(w + "val"))

        def style_keeps(name):
            while name:
                keep, name_up = styles.get(name, (None, None))
                if keep is not None:
                    return keep not in ("0", "false")
                name = name_up
            return False

        body = etree.fromstring(z.read("word/document.xml")).find(w + "body")
        outer = [t for t in body.findall(w + "tbl") if t.find(f".//{w}tc/{w}tbl") is not None][0]
        keeping = []
        for p in outer.iter(w + "p"):
            direct = p.find(f"{w}pPr/{w}keepNext")
            style = p.find(f"{w}pPr/{w}pStyle")
            keeps = direct.get(w + "val", "on") not in ("0", "false") if direct is not None \
                else style_keeps(style.get(w + "val") if style is not None else "Normal")
            if keeps:
                keeping.append("".join(p.itertext())[:30])
        self.assertEqual(keeping, [])
        self.assertIsNone(outer.find(f"{w}tr/{w}trPr/{w}cantSplit"))

    def test_contents_real(self):
        """R506: the contents are an index the programs update: ODT from the outline numbering (the number in its
        column, dots, the page), DOCX a TOC field marked dirty, both already filled."""
        content = self.zip("odt").read("content.xml").decode("utf-8")
        self.assertIn("<text:index-entry-chapter", content)
        self.assertIn('text:outline-level="2"', content)
        self.assertNotIn(">1.1\tThe first section<", content)    # the number is the outline's, not text
        self.assertRegex(content, r'<text:p text:style-name="Contents_20_2">1\.1<text:tab/>The first section<text:tab/>')
        styles = self.zip("odt").read("styles.xml").decode("utf-8")
        self.assertRegex(styles, r'<text:outline-level-style text:level="2" [^>]*style:num-format="1"')
        self.assertIn('style:leader-text="."', styles)
        document_xml = self.zip("docx").read("word/document.xml").decode("utf-8")
        self.assertIn('w:fldCharType="begin" w:dirty="true"', document_xml)
        self.assertIn('<w:t>1.1</w:t><w:tab/><w:t>The first section</w:t>', document_xml)
        self.assertNotRegex(document_xml, r'w:val="Heading1"/><w:spacing w:before="[1-9]')   # a chapter opens a page
        self.assertEqual(document_xml.count('<w:rStyle w:val="TocPage"/>'), 6)   # 2 chapters, 4 sections

    def test_libreoffice_measure(self):
        """With a LibreOffice on the computer, the ODT's formulas get its size and both files the contents' pages."""
        from meridiana.report_typst import editable, office
        if office.found() is None:
            self.skipTest("no LibreOffice")
        # a profile of its own (07/11/2026: a soffice.bin left by a run of the night held the shared one, and this
        # test failed until it was closed), and no LibreOffice of it left at the end
        profile = tempfile.mkdtemp(prefix="meridiana-libreoffice-test-")
        self.addCleanup(shutil.rmtree, profile, True)
        before = os.environ.get("MERIDIANA_LIBREOFFICE_PROFILE")
        os.environ["MERIDIANA_LIBREOFFICE_PROFILE"] = profile
        self.addCleanup(lambda: os.environ.pop("MERIDIANA_LIBREOFFICE_PROFILE") if before is None
                        else os.environ.__setitem__("MERIDIANA_LIBREOFFICE_PROFILE", before))
        for kind in ("odt", "docx"):
            path = Path(self.folder.name) / f"measured.{kind}"
            stats = editable.export(document(), self.build.root, path, kind)
            self.assertTrue(stats["measured"], kind)
            with zipfile.ZipFile(path) as z:
                xml = z.read("content.xml" if kind == "odt" else "word/document.xml").decode("utf-8")
            if kind == "odt":
                self.assertRegex(xml, r"The first section<text:tab/>[0-9]+</text:p>")
            else:
                self.assertRegex(xml, r'<w:rStyle w:val="TocPage"/></w:rPr><w:t>[0-9]+</w:t>')
        if sys.platform == "win32":
            listed = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Process -Filter "
                                     "\"Name like 'soffice%'\").CommandLine"],
                                    capture_output=True, text=True, timeout=60,
                                    creationflags=subprocess.CREATE_NO_WINDOW).stdout
            self.assertNotIn(Path(profile).name, listed)        # its LibreOffice went with its measure

    def test_docx_text_as_written(self):
        root = ElementTree.fromstring(self.zip("docx").read("word/document.xml"))
        text = " ".join("".join(root.itertext()).split())
        self.assertIn(STRANGE, text)
        self.assertIn("1.234,5", text)

    def test_no_blue_anywhere(self):
        for kind in ("odt", "docx"):
            z = self.zip(kind)
            for name in z.namelist():
                if name.endswith(".xml") or name.endswith(".rels"):
                    for found in HEX.findall(z.read(name).decode("utf-8", "replace")):
                        rgb = tuple(int(found[i:i + 2], 16) / 255 for i in (0, 2, 4))
                        self.assertFalse(bluish(rgb), f"{kind}: {name} has #{found}")
                elif name.lower().endswith(".png"):
                    from PIL import Image
                    image = Image.open(io.BytesIO(z.read(name))).convert("RGB")
                    image.thumbnail((300, 300))
                    raw = image.tobytes()
                    pixels = list(zip(raw[0::3], raw[1::3], raw[2::3], strict=True))
                    share = sum(1 for p in pixels if bluish(tuple(c / 255 for c in p))) / max(1, len(pixels))
                    self.assertLess(share, 0.001, f"{kind}: {name} has blue pixels")

    def test_missing_library_says_which(self):
        from meridiana.report_typst import editable
        self.assertEqual(editable.missing_libraries("odt"), [])
        self.assertEqual(editable.missing_libraries("docx"), [])
        with self.assertRaises(ValueError):
            editable.require("pdf")


if __name__ == "__main__":
    unittest.main()
