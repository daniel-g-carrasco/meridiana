"""The report as a DOCX (python-docx): real styles (Normal, Heading 1-4 with the vertical scale of look.py in points,
Caption, and the report's own), a TOC field pre-filled with the titles so it reads before it is updated, PAGE and NUMPAGES
fields in the footer, a header with the logo and the three lines, tables with thin grey rules, a grey head and fixed
column widths, decimal tab stops, the formulas as OMML (omml.py), the Plex fonts embedded (obfuscated), no blue anywhere
(python-docx's template carries blue theme colours and «Accent» styles: they are rewritten in the look's grey).

The PDF's two columns are a table without rules (the gutter as the left cell's margin), the symbols are text (Plex Sans
in its italic, real subscripts), the contents' field is marked dirty so Word updates it when the file opens, its result
written already with LibreOffice's page numbers when a LibreOffice measured the file (office.py, apply). A table is
followed by its space as the next paragraph's space before, not by an empty paragraph; only two tables one after the
other keep a paragraph of one point between them (Word would join them).

Called by editable.export; nothing here is imported until a DOCX is asked for. w:updateFields is never set: it opens a
modal dialog in Word."""

from __future__ import annotations

import colorsys
import io
import re
import shutil
import zipfile
from pathlib import Path

from . import embed_fonts
from .editable import (GUTTER_MM, Context, Item, Picture, TableSpec, clean, facts_spec, font_files, hex_rgb, runs,
                       step_spec, table_spec)

PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
             "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
             "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
             "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
TCPR_ORDER = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar", "textDirection",
              "tcFitText", "vAlign", "hideMark"]
THEME_FONT_ATTRS = ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme")
LANGUAGES = {"it": "it-IT", "en": "en-GB", "de": "de-DE", "fr": "fr-FR", "es": "es-ES"}
NUMBER_TAB = {1: 1.05, 2: 0.9}    # cm: where a heading's title starts after its number, room for «11», «9.10»
CONTENTS_TAB = 1.4                 # cm: the contents' column of the numbers, the PDF's 14 mm
TEXT_WIDTH = 17.4


def twips(cm: float) -> int:
    return int(round(cm * 567))


class DocxWriter:
    def __init__(self, ctx: Context):
        from docx import Document
        from docx.enum.style import WD_STYLE_TYPE
        from docx.enum.table import WD_ALIGN_VERTICAL
        from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Cm, Pt, RGBColor
        self.ctx, self.look = ctx, ctx.look
        self.doc = Document()
        self.STYLE, self.VALIGN, self.ALIGN, self.TAB, self.LEADER = WD_STYLE_TYPE, WD_ALIGN_VERTICAL, WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
        self.new, self.qn, self.Cm, self.Pt, self.RGB = OxmlElement, qn, Cm, Pt, RGBColor
        self.decimal_styles: dict = {}
        self.befores: dict = {}    # each paragraph style's space before, points
        self.box = None            # where the blocks go: the document, or a cell of two columns
        self.after_table = 0.0     # the space below the table that was the last block (points): the next paragraph's

    # ---- low level ----

    def place(self, parent, child, order: list) -> None:
        """Appends `child` to `parent` where the schema's order wants it (Word is strict about the order)."""
        name = self.local(child)
        later = order[order.index(name) + 1:] if name in order else []
        for existing in parent:
            if self.local(existing) in later:
                existing.addprevious(child)
                return
        parent.append(child)

    @staticmethod
    def local(element) -> str:
        return element.tag.split("}")[-1]

    def attrs(self, element, **values):
        for key, value in values.items():
            element.set(self.qn("w:" + key), str(value))
        return element

    def colour(self, hex_: str):
        return self.RGB.from_string(hex_rgb(hex_))

    def set_fonts(self, rpr, family: str) -> None:
        fonts = rpr.get_or_add_rFonts()
        for attr in THEME_FONT_ATTRS:
            fonts.attrib.pop(self.qn("w:" + attr), None)
        for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(self.qn("w:" + attr), family)

    # ---- styles (set by id: python-docx's own lookups scan every style each time and cost seconds) ----

    def add_p(self, style: str, container=None):
        """A paragraph of `style` in `container`, or in the box the blocks go to; after a table it takes the table's
        space below as its space before (no empty paragraph for it)."""
        if container is None and self.box is not None:
            p = self.box.add_paragraph()
            if self.after_table:
                space, self.after_table = float(self.after_table), 0.0
                if style != "Heading 1" and self.befores.get(style, 0.0) < space:
                    p.paragraph_format.space_before = self.Pt(space)
        else:
            p = (container or self.doc).add_paragraph()
        p._p.style = self.sid[style]
        return p

    def use(self, p, style: str) -> None:
        p._p.style = self.sid[style]

    def run(self, p, text: str, style: str):
        r = p.add_run(text)
        r._r.style = self.sid[style]
        return r

    def remember_styles(self) -> None:
        self.sid = {s.name: s.style_id for s in self.doc.styles}

    def style(self, name, kind="paragraph", base="Normal", font=None, size=None, colour=None, before=None, after=None,
              keep=False, align=None, page_break=False, tabs=(), border=None, fill=None, upper=False, spacing=None,
              keep_together=False, outline=None, line=None):
        styles = self.doc.styles
        if kind == "paragraph":
            self.befores[name] = float(before or 0.0)
        existing = [s.name for s in styles]
        if name in existing:
            st = styles[name]
        else:
            st = styles.add_style(name, self.STYLE.PARAGRAPH if kind == "paragraph" else self.STYLE.CHARACTER)
        if base and name != "Normal" and base in existing + ["Normal"]:
            st.base_style = styles[base]
        st.quick_style = True
        rpr = st.element.get_or_add_rPr()
        if font:
            self.set_fonts(rpr, font)
        f = st.font
        f.bold = False
        f.italic = False
        if size:
            f.size = self.Pt(size)
        if colour:
            f.color.rgb = self.colour(colour)
        if upper:
            f.all_caps = True
        if spacing:
            sp = self.new("w:spacing")
            sp.set(self.qn("w:val"), str(spacing))
            self.place(rpr, sp, ["rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
                                 "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color",
                                 "spacing", "w", "kern", "position", "sz", "szCs"])
        if kind == "paragraph":
            pf = st.paragraph_format
            if before is not None:
                pf.space_before = self.Pt(before)
            if after is not None:
                pf.space_after = self.Pt(after)
            pf.keep_with_next = keep
            pf.keep_together = keep_together
            pf.page_break_before = page_break
            pf.widow_control = True
            if line:
                pf.line_spacing = line
            if align:
                pf.alignment = align
            for position, alignment in tabs:
                pf.tab_stops.add_tab_stop(self.Cm(position), alignment, self.LEADER.DOTS if alignment == self.TAB.RIGHT and name.startswith("toc") else self.LEADER.SPACES)
            ppr = st.element.get_or_add_pPr()
            self.border_and_shade(ppr, border, fill)
            if outline is not None:
                lvl = self.new("w:outlineLvl")
                lvl.set(self.qn("w:val"), str(outline))
                for old in ppr.findall(self.qn("w:outlineLvl")):
                    ppr.remove(old)
                self.place(ppr, lvl, PPR_ORDER)
        return st

    def border_and_shade(self, ppr, border, fill) -> None:
        """`border`: {"left": (size in eighths of a point, "single", colour)} or {"box": (...)}; `fill`: a hex colour."""
        if border:
            for old in ppr.findall(self.qn("w:pBdr")):
                ppr.remove(old)
            box = self.new("w:pBdr")
            sides = ("top", "left", "bottom", "right") if "box" in border else tuple(border)
            spec = border.get("box")
            for side in sides:
                size, value, colour, space = spec or border[side]
                e = self.new("w:" + side)
                self.attrs(e, val=value, sz=size, space=space, color=hex_rgb(colour))
                box.append(e)
            self.place(ppr, box, PPR_ORDER)
        if fill:
            for old in ppr.findall(self.qn("w:shd")):
                ppr.remove(old)
            shd = self.new("w:shd")
            self.attrs(shd, val="clear", color="auto", fill=hex_rgb(fill))
            self.place(ppr, shd, PPR_ORDER)

    def define_styles(self) -> None:
        lk, doc = self.look, self.doc
        A, T = self.ALIGN, self.TAB
        justify = A.JUSTIFY if lk.justify else None
        # no theme fonts and no theme colours anywhere in the styles
        for fonts in doc.styles.element.iter(self.qn("w:rFonts")):
            for attr in THEME_FONT_ATTRS:
                fonts.attrib.pop(self.qn("w:" + attr), None)
        defaults = doc.styles.element.find(self.qn("w:docDefaults"))
        if defaults is not None:
            for fonts in defaults.iter(self.qn("w:rFonts")):
                for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
                    fonts.set(self.qn("w:" + attr), lk.body)
            for rpr in defaults.iter(self.qn("w:rPr")):
                language = self.new("w:lang")
                code = LANGUAGES.get(self.ctx.lang.split("-")[0], self.ctx.lang)
                self.attrs(language, val=code, eastAsia=code, bidi=code)
                for old in rpr.findall(self.qn("w:lang")):
                    rpr.remove(old)
                rpr.append(language)
        normal = self.style("Normal", base=None, font=lk.body, size=lk.size, colour=lk.ink, before=0, after=0)
        normal.paragraph_format.line_spacing = 1.0
        S = self.style
        S("Body", font=lk.body, size=lk.size, colour=lk.ink, after=lk.sp("par"), align=justify)
        S("Lead", size=10.5, before=4, after=8, align=justify)
        S("Muted", size=8.6, colour=lk.txt2, before=4, after=6)
        S("Source", font=lk.table, size=7, colour=lk.faint, before=3, after=7)
        S("Caption", font=lk.body, size=7.6, colour=lk.txt2, before=lk.sp("capa"), after=lk.sp("capb"), keep_together=True)
        S("Picture", before=lk.sp("figa"), after=3, keep=True)
        # a chapter always opens a page, where Typst drops the space above: none here either
        S("Heading 1", font=lk.strong, size=17, colour=lk.ink, before=0, after=lk.sp("h1b"), keep=True,
          page_break=True, outline=0, tabs=[(NUMBER_TAB[1], T.LEFT)])
        # Word adds the space after of a paragraph to the space before of the next, Typst takes the larger: a heading
        # comes after text, whose space after is the scale's «par», so its space before is less that
        S("Heading 2", font=lk.strong, size=11, colour=lk.ink, before=lk.sp("h2a") - lk.sp("par"), after=lk.sp("h2b"), keep=True,
          outline=1, tabs=[(NUMBER_TAB[2], T.LEFT)])
        S("Heading 3", font=lk.strong, size=9.6, colour=lk.ink, before=lk.sp("h3a") - lk.sp("par"), after=lk.sp("h3b"), keep=True, outline=2)
        S("Heading 4", font=lk.strong, size=8.8, colour=lk.txt2, before=lk.sp("h4a") - lk.sp("par"), after=lk.sp("h4b"), keep=True, outline=3)
        S("ContentsTitle", font=lk.strong, size=17, before=0, after=lk.sp("h1b"), keep=True)
        # the contents as the PDF's: the number in a column of 14 mm, dots up to the page
        S("toc 1", font=lk.strong, size=lk.size, before=9, after=0, keep=True, line=0.9,
          tabs=[(CONTENTS_TAB, T.LEFT), (TEXT_WIDTH, T.RIGHT)])
        S("toc 2", size=lk.size, before=0, after=0, line=0.9, tabs=[(CONTENTS_TAB, T.LEFT), (TEXT_WIDTH, T.RIGHT)])
        S("Equation", size=lk.size, before=lk.sp("eqa"), after=lk.sp("eqb"), keep_together=True,
          tabs=[(TEXT_WIDTH / 2, T.CENTER), (TEXT_WIDTH, T.RIGHT)])
        S("Label", font=lk.table, size=8, colour=lk.txt2, before=lk.sp("par"), after=2, keep=True)
        S("Values", font=lk.table, size=8, colour=lk.txt2, before=lk.sp("par"), after=3, keep=True)
        S("ResultLine", font=lk.table, size=9, before=3, after=lk.sp("par"), fill=lk.tint,
          border={"left": (11, "single", lk.accent, 8)})
        S("Gap", size=1, before=0, after=lk.sp("tabb") - 1)     # only between two tables: Word would join them
        S("Column", size=1, before=0, after=0)
        S("Reference", font=lk.table, size=7.4, colour=lk.faint, before=2, after=lk.sp("capb"))
        S("List Bullet", font=lk.body, size=9, after=lk.sp("lista"), align=justify)
        S("LogoBox", size=6.5, colour=lk.faint, align=A.CENTER, spacing=14,
          border={"box": (4, "dashed", lk.rule, 4)})
        S("Cell", font=lk.table, size=lk.table_size, line=0.9)
        S("CellRight", base="Cell", align=A.RIGHT)
        S("CellHead", base="Cell", size=7.8, colour=lk.head_text)
        S("CellHeadRight", base="CellHead", align=A.RIGHT)
        S("CellLabel", base="Cell", size=8.5, colour=lk.txt2)
        S("CellFact", base="Cell", size=8.5)
        S("CellFactRight", base="CellFact", align=A.RIGHT)
        S("CellSource", font=lk.mono, size=6.6, colour=lk.faint)
        S("CellSourceRight", base="CellSource", align=A.RIGHT)
        S("CellSmall", base="Cell", size=7.4, colour=lk.txt2)
        for name, align in (("Left", A.LEFT), ("Centre", A.CENTER), ("Right", A.RIGHT)):
            S(f"Strong{name}", font=lk.strong, size=7, before=0, after=2, align=align)
            S(f"Plain{name}", font=lk.body, size=7, colour=lk.txt2, before=0, after=2, align=align)
        S("HeaderTitle", font=lk.strong, size=8, before=0, after=2, align=A.RIGHT)
        S("Tiny", size=1, before=0, after=0)
        S("CoverTitle", size=24, before=0, after=6)
        S("CoverSub", size=11, colour=lk.txt2, before=0, after=6)
        S("CoverLabel", font=lk.strong, size=7.5, colour=lk.accent, before=17, after=4, upper=True, spacing=16)
        S("CoverPlant", font=lk.medium, size=15, before=0, after=6)
        S("CoverPlantSub", size=9.5, colour=lk.txt2, before=0, after=0)
        S("CoverMetaLabel", font=lk.strong, size=6.6, colour=lk.txt2, before=10, after=0, upper=True, spacing=8, keep=True)
        S("CoverMeta", size=8.4, before=0, after=0)
        S("CoverImage", before=22, after=0, keep=True)
        S("CoverMade", size=7, colour=lk.faint, before=17, after=0, align=A.RIGHT, border={"top": (4, "single", lk.ink, 4)})
        S("Kicker", font=lk.strong, size=7.6, colour=lk.accent, after=4, upper=True, spacing=14, keep=True)
        S("HeadTitle", size=21, after=8, keep=True)
        S("HeadSub", size=9.6, colour=lk.txt2, before=3, after=3)
        for name, font, size, colour in (("StrongText", lk.strong, None, None), ("StrongCell", lk.table_strong, None, None),
                                         ("MutedText", None, None, lk.txt2), ("CodeText", lk.mono, 8, lk.accent),
                                         ("NumberText", lk.table, 8, lk.txt2), ("MediumText", lk.table, None, lk.txt2),
                                         ("SymbolText", lk.symbol, None, None), ("TocPage", None, None, None)):
            self.style(name, kind="character", base=None, font=font, size=size, colour=colour)
        self.doc.styles["SymbolText"].font.italic = True
        self.style("SymbolUprightText", kind="character", base=None, font=lk.symbol)
        self.remember_styles()
        settings = doc.settings.element
        stop = settings.find(self.qn("w:defaultTabStop"))
        if lk.hyphenate and stop is not None:
            stop.addnext(self.new("w:autoHyphenation"))
        # the page: A4, the margins of the template; the first page (the cover) without header and footer
        sec = doc.sections[0]
        sec.page_width, sec.page_height = self.Cm(21), self.Cm(29.7)
        sec.left_margin, sec.right_margin = self.Cm(lk.margin_left / 10), self.Cm(1.6)
        sec.top_margin, sec.bottom_margin = self.Cm(2.5), self.Cm(1.9)
        sec.header_distance, sec.footer_distance = self.Cm(1.0), self.Cm(0.7)
        sec.different_first_page_header_footer = bool(self.ctx.document.get("cover"))

    # ---- text ----

    def field(self, p, code: str, placeholder: str = "") -> None:
        for kind, value in (("begin", None), ("instr", code), ("separate", None), ("text", placeholder), ("end", None)):
            r = p.add_run()
            if kind == "instr":
                e = self.new("w:instrText")
                e.set(self.qn("xml:space"), "preserve")
                e.text = f" {value} "
                r._r.append(e)
            elif kind == "text":
                if value:
                    r.text = value
            else:
                e = self.new("w:fldChar")
                e.set(self.qn("w:fldCharType"), kind)
                r._r.append(e)

    def field_part(self, p, kind: str) -> None:
        e = self.new("w:fldChar")
        e.set(self.qn("w:fldCharType"), kind)
        p.add_run()._r.append(e)

    def picture_run(self, p, picture: Picture):
        run = p.add_run()
        run.add_picture(io.BytesIO(picture.data), width=self.Cm(picture.width), height=self.Cm(picture.height))
        self.ctx.stats["images"] += 1
        return run

    def formula(self, p, tex: str) -> None:
        element = self.ctx.omml(tex)
        if element is None:
            p.add_run(tex)
            return
        self.ctx.stats["formulas"] += 1
        p._p.append(element)

    def symbol(self, p, tex: str) -> bool:
        """A symbol as text runs (Plex Sans, the letters italic, real subscripts); False when it stays a formula."""
        pieces = self.ctx.symbol(tex)
        if pieces is None:
            return False
        for piece in pieces:
            r = self.run(p, piece.text, "SymbolText" if piece.italic else "SymbolUprightText")
            if piece.pos:
                r.font.subscript = piece.pos == "sub"
                r.font.superscript = piece.pos == "sup"
        return True

    def fill(self, p, content, cell: bool = False, strong: bool = False) -> None:
        for r in runs(content):
            if r.kind == "mark":
                picture = self.ctx.mark(r.text)
                if picture is not None:
                    self.picture_run(p, picture)
                    p.add_run(" ")
            elif r.kind == "formula":
                tex = self.ctx.tex_of(r.text)
                if tex and not self.symbol(p, tex):
                    self.formula(p, tex)
            elif r.kind == "b" or (strong and r.kind != "m"):
                self.run(p, r.text, "StrongCell" if cell else "StrongText")
            elif r.kind == "m":
                self.run(p, r.text, "MutedText")
            else:
                p.add_run(r.text)

    def paragraph(self, content, style="Body"):
        p = self.add_p(style)
        self.fill(p, content)
        return p

    def heading(self, level: int, text: str, extra=None):
        p = self.add_p(f"Heading {min(level, 4)}")
        if extra:
            self.run(p, extra, "CodeText")
            p.add_run("  ")
        p.add_run(text)
        return p

    # ---- tables ----

    def cell_border(self, tc_pr, sides: dict) -> None:
        box = self.new("w:tcBorders")
        for side in ("top", "left", "bottom", "right"):
            if side in sides:
                size, value, colour = sides[side]
                e = self.new("w:" + side)
                self.attrs(e, val=value, sz=size, space=0, color=hex_rgb(colour))
                box.append(e)
        self.place(tc_pr, box, TCPR_ORDER)

    def cell_fill(self, tc_pr, fill: str) -> None:
        shd = self.new("w:shd")
        self.attrs(shd, val="clear", color="auto", fill=hex_rgb(fill))
        self.place(tc_pr, shd, TCPR_ORDER)

    def fix_table(self, t, widths: list, grid: bool = True, margins=(72, 80)) -> None:
        """A fixed layout, the grid and every cell's width the same numbers (the symbol column of the steps came out wide
        with python-docx's own widths), thin grey rules between all the cells."""
        tbl = t._tbl
        t.autofit = False
        pr = tbl.tblPr
        total = sum(twips(w) for w in widths)
        width = pr.find(self.qn("w:tblW"))
        if width is None:
            width = self.new("w:tblW")
            self.place(pr, width, ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
                                   "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd",
                                   "tblLayout", "tblCellMar", "tblLook"])
        self.attrs(width, type="dxa", w=total)
        layout = pr.find(self.qn("w:tblLayout"))
        layout.set(self.qn("w:type"), "fixed")
        borders = self.new("w:tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = self.new("w:" + side)
            if grid:
                self.attrs(e, val="single", sz=3, space=0, color=hex_rgb(self.look.grid))
            else:
                self.attrs(e, val="nil")
            borders.append(e)
        layout.addprevious(borders)
        cell_margins = self.new("w:tblCellMar")
        for side, value in (("top", margins[0]), ("left", margins[1]), ("bottom", margins[0]), ("right", margins[1])):
            e = self.new("w:" + side)
            self.attrs(e, w=value, type="dxa")
            cell_margins.append(e)
        layout.addnext(cell_margins)
        for gridcol, w in zip(tbl.tblGrid.findall(self.qn("w:gridCol")), widths, strict=False):
            gridcol.set(self.qn("w:w"), str(twips(w)))

    def cell_width(self, cell, width: int) -> None:
        """The cell's width in twips, the very numbers of the grid."""
        from docx.shared import Twips
        cell.width = Twips(width)

    def decimal_style(self, width: float, share: float) -> str:
        position = round(share * (width - 0.28), 2)
        if position not in self.decimal_styles:
            name = f"CellDecimal{len(self.decimal_styles) + 1}"
            st = self.style(name, base="Cell", font=self.look.table, size=self.look.table_size)
            st.paragraph_format.tab_stops.add_tab_stop(self.Cm(position), self.TAB.DECIMAL)
            self.decimal_styles[position] = name
            self.sid[name] = st.style_id
        return self.decimal_styles[position]

    def cell_style(self, cell, width: float, share: float, facts: bool = False) -> str:
        if cell.kind == "head":
            return "CellHeadRight" if cell.align == "right" else "CellHead"
        if cell.kind == "label":
            return "CellLabel"
        if cell.kind == "source":
            return "CellSourceRight" if cell.align == "right" else "CellSource"
        if cell.kind == "small":
            return "CellSmall"
        if cell.align == "decimal":
            return self.decimal_style(width, share)
        if facts:
            return "CellFactRight" if cell.align == "right" else "CellFact"
        return "CellRight" if cell.align == "right" else "Cell"

    def new_table(self, rows: int, cols: int, widths: list):
        """A table in the box the blocks go to; after another table, a paragraph of one point between (Word joins two
        tables that touch)."""
        if self.after_table:
            self.after_table = 0.0
            self.add_p("Gap")
        box = self.box if self.box is not None else self.doc
        if box is self.doc:
            return box.add_table(rows=rows, cols=cols)
        t = box.add_table(rows=rows, cols=cols)
        # python-docx puts an empty paragraph after a table in a cell: it goes, the cell gets its last one at the end
        after = t._tbl.getnext()
        if after is not None and self.local(after) == "p" and not after.xpath(".//w:t"):
            after.getparent().remove(after)
        return t

    def table(self, spec: TableSpec, container=None, grid: bool = True, facts: bool = False, after=None):
        lk = self.look
        self.ctx.stats["tables"] += 1
        n = len(spec.widths)
        t = self.new_table(0, n, spec.widths)
        self.fix_table(t, spec.widths, grid, (34, 80) if not facts else (34, 72))
        for r, row in enumerate(spec.rows):
            tr = t.add_row()
            cells = tr.cells
            trpr = tr._tr.get_or_add_trPr()
            trpr.append(self.new("w:cantSplit"))
            if r < spec.head_rows:
                trpr.append(self.new("w:tblHeader"))
            column = 0
            for cell in row:
                target = cells[column]
                if cell.span > 1:
                    target = target.merge(cells[column + cell.span - 1])
                width = sum(spec.widths[column:column + cell.span])
                self.cell_width(target, sum(twips(w) for w in spec.widths[column:column + cell.span]))
                fill = lk.head_fill if cell.kind == "head" else lk.tint if cell.fill == "tint" or cell.span > 1 else None
                if fill:
                    self.cell_fill(target._tc.get_or_add_tcPr(), fill)
                p = target.paragraphs[0]
                self.use(p, self.cell_style(cell, width, spec.share, facts))
                if cell.kind == "head":
                    target.vertical_alignment = self.VALIGN.BOTTOM
                if cell.tex:
                    if not self.symbol(p, cell.tex):
                        self.formula(p, cell.tex)
                else:
                    self.fill(p, cell.content, cell=True, strong=cell.strong)
                column += cell.span
        self.after_table = self.look.sp("tabb") if after is None else after
        return t

    def columns(self, widths: list, fill, gutter: float = GUTTER_MM / 10, rule: bool = False) -> None:
        """Side by side, as the template's grid: a table of one row without rules, the gutter as the left cell's right
        margin; fill(i) writes column i (the box is its cell meanwhile), each cell ending in its own paragraph. With
        `rule`, the last column has the accent's rule on its left (the cover's data)."""
        cm_widths = [widths[0] + gutter] + list(widths[1:])
        t = self.new_table(1, len(widths), cm_widths)
        self.fix_table(t, cm_widths, grid=False, margins=(0, 0))
        outer = self.box
        for i, cell in enumerate(t.rows[0].cells):
            self.cell_width(cell, twips(cm_widths[i]))
            margins = {"right": gutter} if i == 0 else {"left": 0.5} if rule else {}
            if margins:
                mar = self.new("w:tcMar")
                for side, value in margins.items():
                    e = self.new("w:" + side)
                    self.attrs(e, w=twips(value), type="dxa")
                    mar.append(e)
                self.place(cell._tc.get_or_add_tcPr(), mar, TCPR_ORDER)
            if rule and i == len(widths) - 1:
                self.bordered(cell, {"left": (10, "single", self.look.accent)})
            first = cell.paragraphs[0]._p
            self.box, self.after_table = cell, False
            fill(i)
            self.tidy(cell, first)
            top = cell._tc.find(self.qn("w:p"))
            if top is not None and top is cell._tc[1 if self.local(cell._tc[0]) == "tcPr" else 0]:
                from docx.text.paragraph import Paragraph
                Paragraph(top, cell).paragraph_format.space_before = self.Pt(0)   # as a block at the top of Typst's grid
        # No paragraph of the columns keeps with the next: a heading in a cell already stays with what follows it in
        # the cell, and a row holding such a paragraph is bound to what comes after the table. The sintesi's second
        # pair of columns, bound to the 3D view after it (too tall for the rest of the page), went whole to the next
        # page and left the bottom of page 3 empty (Rho, 07/11/2026). The row itself may break between pages.
        from docx.text.paragraph import Paragraph
        for p in t._tbl.iter(self.qn("w:p")):
            Paragraph(p, None).paragraph_format.keep_with_next = False
        self.box, self.after_table = outer, self.look.sp("par")

    def tidy(self, cell, first) -> None:
        """A cell written: the empty paragraph it was made with goes; it ends in a paragraph (Word wants one), of one
        point when what comes before is a table."""
        tc = cell._tc
        if len(tc.findall(self.qn("w:p"))) + len(tc.findall(self.qn("w:tbl"))) > 1 and not first.xpath(".//w:t"):
            tc.remove(first)
        last = tc[-1]
        if self.local(last) != "p":
            self.use(cell.add_paragraph(), "Column")
        elif self.local(last) == "p" and last.getprevious() is not None and self.local(last.getprevious()) == "tbl" \
                and not last.xpath(".//w:t"):
            last.style = self.sid["Column"]

    # ---- the page: header, footer, cover ----

    def logo_paragraph(self, cell, height=10.0, room=40.0, box=(3.6, 0.9)):
        """The logo (or the dashed «LOGO» box) in the cell's first paragraph; the width the cell needs, in cm."""
        picture = self.ctx.logo(height, room)
        p = cell.paragraphs[0]
        if picture is not None:
            self.use(p, "PlainLeft")
            self.picture_run(p, picture)
            return picture.width + 0.3
        if self.ctx.wants_logo_placeholder():
            self.use(p, "LogoBox")
            p.add_run("LOGO")
            return box[0] + 0.3
        self.use(p, "PlainLeft")
        return 0.6

    def bordered(self, cell, sides: dict, valign=None) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        self.cell_border(tc_pr, sides)
        if valign is not None:
            cell.vertical_alignment = valign

    def row_table(self, container, widths, border_side, colour_size):
        if container is self.doc:
            t = container.add_table(rows=1, cols=len(widths))
        else:
            t = container.add_table(rows=1, cols=len(widths), width=self.Cm(sum(widths)))
        self.fix_table(t, widths, grid=False, margins=(0, 0))
        for cell, w in zip(t.rows[0].cells, widths, strict=False):
            self.cell_width(cell, twips(w))
            size, value, colour = colour_size
            self.bordered(cell, {border_side: (size, value, colour)}, self.VALIGN.BOTTOM if border_side == "bottom" else None)
        return t

    def tail(self, container) -> None:
        """A header or footer ends with a paragraph: the one it started with goes after the table, one point high."""
        first = container.paragraphs[0]
        container._element.append(first._p)
        self.use(first, "Tiny")

    def header_footer(self) -> None:
        ctx, lk = self.ctx, self.look
        width = 21.0 - lk.margin_left / 10 - 1.6
        rule = (int(lk.hf_rule * 8), "single", lk.hf_colour)
        header = self.doc.sections[0].header
        header.is_linked_to_previous = False
        probe = ctx.logo()
        left = (probe.width + 0.3) if probe is not None else (3.9 if ctx.wants_logo_placeholder() else 0.6)
        t = self.row_table(header, [left, width - left], "bottom", rule)
        self.logo_paragraph(t.rows[0].cells[0])
        right = t.rows[0].cells[1]
        first = True
        for text, kind in ctx.header_lines():
            if not text:
                continue
            p = right.paragraphs[0] if first else right.add_paragraph()
            first = False
            self.use(p, "HeaderTitle" if kind == "strong" else "PlainRight")
            p.add_run(text)
        self.tail(header)
        footer = self.doc.sections[0].footer
        footer.is_linked_to_previous = False
        t = self.row_table(footer, [width / 3] * 3, "top", rule)
        for i, cells in enumerate(ctx.footer_cells()):
            align = ("Left", "Centre", "Right")[i]
            cell = t.rows[0].cells[i]
            first = True
            for text, kind in cells:
                if kind == "page":
                    p = cell.paragraphs[0] if first else cell.add_paragraph()
                    self.use(p, "PlainRight")
                    for part in ctx.page_line():
                        if part == "{n}":
                            self.field(p, "PAGE", "1")
                        elif part == "{total}":
                            self.field(p, "NUMPAGES", "1")
                        else:
                            p.add_run(clean(part))
                elif text:
                    p = cell.paragraphs[0] if first else cell.add_paragraph()
                    self.use(p, f"{'Strong' if kind == 'strong' else 'Plain'}{align}")
                    p.add_run(text)
                else:
                    continue
                first = False
        self.tail(footer)

    def cover(self, c: dict) -> None:
        ctx, lk = self.ctx, self.look
        d = ctx.doc
        width = 21.0 - lk.margin_left / 10 - 1.6
        probe = ctx.logo(14.0, 60.0)
        left = (probe.width + 0.3) if probe is not None else (5.9 if ctx.wants_logo_placeholder() else 0.6)
        t = self.row_table(self.doc, [left, width - left], "bottom", (4, "single", lk.ink))
        self.logo_paragraph(t.rows[0].cells[0], 14.0, 60.0, (5.6, 1.4))
        right = t.rows[0].cells[1]
        first = True
        for text, style in ((clean(d.get("foot_left", "")), "StrongRight"), (clean(d.get("foot_left2", "")), "PlainRight")):
            if text:
                p = right.paragraphs[0] if first else right.add_paragraph()
                first = False
                self.use(p, style)
                p.add_run(text)
        self.after_table = self.look.sp("tabb")

        def column(i):
            if i == 0:
                self.paragraph(clean(d.get("doc_title") or ctx.word("report")), "CoverTitle")
                if d.get("doc_sub"):
                    self.paragraph(clean(d["doc_sub"]), "CoverSub")
                self.paragraph(ctx.word("plant"), "CoverLabel")
                self.paragraph(clean(c.get("title", "")), "CoverPlant")
                if c.get("sub"):
                    self.paragraph(clean(c["sub"]), "CoverPlantSub")
                return
            for k, m in enumerate(c.get("meta") or []):
                p = self.paragraph(clean(m.get("t", "")), "CoverMetaLabel")
                if k == 0:
                    p.paragraph_format.space_before = self.Pt(0)
                for line in m.get("lines") or []:
                    self.paragraph(clean(line), "CoverMeta")
        # the title and the plant on the left, the data in a column of 60 mm with a rule on its left, as the PDF's
        self.columns([width - 7.0, 6.0], column, gutter=1.0, rule=True)
        self.after_table = 0.0
        if c.get("image"):
            picture = ctx.figure({"image": c["image"], "max_h": 112.0, "tint": c.get("tint"), "inset": c.get("inset", 0)},
                                 174.0, 112.0)
            if picture is not None:
                self.picture_paragraph(picture)
        if c.get("made"):
            self.paragraph(clean(c["made"]), "CoverMade")

    def compact_head(self, h: dict) -> None:
        self.paragraph(clean(h.get("kicker", "")).upper(), "Kicker")
        self.paragraph(clean(h.get("title", "")), "HeadTitle")
        if h.get("sub"):
            self.paragraph(clean(h["sub"]), "HeadSub")
        if h.get("lines"):
            self.paragraph(" · ".join(clean(x) for x in h["lines"]), "Muted")
        if h.get("made"):
            self.paragraph(clean(h["made"]), "Source")

    def contents(self) -> None:
        """The TOC field (two levels, from the headings), marked dirty so Word updates it when the file opens, its
        result already written as the PDF's contents: the number in its column, the title, dots up to the page (the
        page numbers LibreOffice's when it measured the file, apply)."""
        title = self.paragraph(self.ctx.word("contents"), "ContentsTitle")
        title.paragraph_format.page_break_before = bool(self.ctx.document.get("cover"))
        entries = self.ctx.toc_entries()
        for i, (level, text) in enumerate(entries):
            p = self.add_p(f"toc {min(level, 2)}")
            if i == 0:
                self.field_part(p, "begin")
                p._p[-1][-1].set(self.qn("w:dirty"), "true")
                instr = p.add_run()
                e = self.new("w:instrText")
                e.set(self.qn("xml:space"), "preserve")
                e.text = ' TOC \\o "1-2" \\h \\z \\u '
                instr._r.append(e)
                self.field_part(p, "separate")
            number, tab, title_text = text.partition("\t")
            p.add_run((number + ("." if level == 1 else "") + "\t" + title_text) if tab else "\t" + text)
            p.add_run("\t")
            self.run(p, "", "TocPage")
            if i == len(entries) - 1:
                self.field_part(p, "end")

    # ---- blocks ----

    def picture_paragraph(self, picture: Picture):
        p = self.add_p("Picture")
        self.picture_run(p, picture)
        return p

    def write_items(self, items) -> None:
        for item in items:
            if item.kind in ("bars", "waterfall", "balance", "cash", "carpet", "dash", "tiles", "badge", "chips"):
                self.do_drawn(item)
            else:
                handler = getattr(self, "do_" + item.kind, None)
                if handler is not None:
                    handler(item)

    def do_two(self, item: Item) -> None:
        columns = item.columns or []
        self.columns([w / 10 for w, _items in columns], lambda i: self.write_items(columns[i][1]))

    def do_chapter(self, item: Item) -> None:
        self.heading(1, item.text)

    def do_attachment(self, item: Item) -> None:
        from ..i18n import _
        self.heading(1, item.text)
        self.paragraph(_("This attachment is a separate file: {title}").format(title=item.text), "Body")

    def do_section(self, item: Item) -> None:
        self.heading(2, item.text)

    def do_sub(self, item: Item) -> None:
        self.heading(item.level if item.level in (3, 4) else 3, item.text)

    def do_p(self, item: Item) -> None:
        b = item.block
        style = {"caption": "Caption", "muted": "Muted", "source": "Source", "lead": "Lead"}.get(b.get("style", ""), "Body")
        self.paragraph(b.get("t"), style)

    def do_list(self, item: Item) -> None:
        for x in item.block.get("items") or []:
            self.paragraph(x, "List Bullet")

    def do_facts(self, item: Item) -> None:
        self.table(facts_spec(item.block, item.width), facts=True)

    def do_table(self, item: Item) -> None:
        self.table(table_spec(item.block, item.width))

    def do_figure(self, item: Item, tall: float = 118.0) -> None:
        picture = self.ctx.figure(item.block, item.width, tall)
        if picture is not None:
            self.picture_paragraph(picture)
            if item.block.get("caption") is not None:
                self.paragraph(item.block["caption"], "Caption")

    def do_fill_figure(self, item: Item) -> None:
        self.do_figure(item, 185.0)

    def do_drawn(self, item: Item) -> None:
        picture = self.ctx.drawn(item)
        if picture is not None:
            self.picture_paragraph(picture)

    def do_formula(self, item: Item) -> None:
        b = item.block
        tex = clean(b.get("tex") or self.ctx.tex_of(b.get("image", "")))
        if tex:
            p = self.add_p("Equation")
            p.add_run("\t")
            self.formula(p, tex)

    def do_pagebreak(self, item: Item) -> None:
        p = self.add_p("Tiny")
        p.paragraph_format.page_break_before = True

    def do_step(self, item: Item) -> None:
        ctx, b = self.ctx, item.block
        self.heading(3, clean(b.get("title", "")), extra=clean(b.get("code", "")) or None)
        if b.get("explanation"):
            self.paragraph(b["explanation"], "Body")
        if b.get("tex"):
            p = self.add_p("Equation")
            p.add_run("\t")
            self.formula(p, clean(b["tex"]))
            p.add_run("\t")
            self.run(p, f"({clean(b.get('eq', ''))})", "NumberText")
        if b.get("inputs") or b.get("result"):
            self.paragraph(ctx.word("where"), "Label")
            self.table(step_spec(b, ctx.step_words(), item.width), after=self.look.sp("par"))
        # the hour of the example, then the formula with the numbers ending in the result, in evidence (R479)
        if b.get("worked"):
            if b.get("example"):
                self.run(self.add_p("Values"), clean(b["example"]), "MutedText")
            for tex in b["worked"]:
                self.formula(self.add_p("ResultLine"), clean(tex))
        if b.get("reference"):
            self.paragraph(f"{ctx.word('reference')}: {clean(b['reference'])}", "Reference")

    # ---- the whole ----

    def build(self) -> None:
        ctx = self.ctx
        self.box = self.doc
        self.define_styles()
        self.header_footer()
        d = ctx.document
        if d.get("cover"):
            self.cover(d["cover"])
        elif d.get("head"):
            self.compact_head(d["head"])
        if ctx.has_contents():
            self.contents()
        self.write_items(ctx.items)
        props = self.doc.core_properties
        props.title = clean(ctx.doc.get("title", ""))
        props.author = clean(ctx.doc.get("author", ""))

    def save(self, target: Path) -> None:
        self.doc.save(str(target))
        rewrite_without_blue(target, self.look)
        self.ctx.stats["fonts"] = embed_fonts.embed_docx(target, font_files(self.look))


def bluish(hex_: str) -> bool:
    """True for a blue, light blue, teal or blue-grey: hue between 170 and 275 degrees, saturation above 0.08."""
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return 170 / 360 <= h <= 275 / 360 and s > 0.08 and v > 0.08


COLOUR = re.compile(r'((?:<w:color [^>]*?w:val="|w:fill="|w:color="|srgbClr val="|lastClr="))([0-9A-Fa-f]{6})(")')
THEME_REF = re.compile(r' w:theme(?:Color|Shade|Tint|Fill|FillShade|FillTint)="[^"]*"')


def rewrite_without_blue(path: Path, look_) -> int:
    """Rewrites word/*.xml of the DOCX: every bluish colour (python-docx's template has many, in its theme and in the
    styles nobody uses) becomes the look's anthracite, the styles no longer point at the theme's colours, and the theme's
    fonts are the report's. Returns how many colours it changed."""
    grey = hex_rgb(look_.accent)
    changed = 0

    def swap(m):
        nonlocal changed
        if bluish(m.group(2)):
            changed += 1
            return m.group(1) + grey + m.group(3)
        return m.group(0)

    tmp = path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.startswith("word/") and info.filename.endswith(".xml"):
                text = COLOUR.sub(swap, data.decode("utf-8"))
                if "/theme/" in info.filename:
                    text = re.sub(r'(<a:majorFont>\s*<a:latin typeface=")[^"]*', lambda m: m.group(1) + look_.strong, text)
                    text = re.sub(r'(<a:minorFont>\s*<a:latin typeface=")[^"]*', lambda m: m.group(1) + look_.body, text)
                else:
                    text = THEME_REF.sub("", text)
                data = text.encode("utf-8")
            zout.writestr(info, data)
    shutil.move(str(tmp), str(path))
    return changed


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def apply(target: Path, found: dict) -> None:
    """The contents' page numbers LibreOffice found (office.measure) written into the TOC field's result, entry by
    entry; Word updates the field anyway when it opens the file (it is marked dirty)."""
    from lxml import etree
    pages = [page for _text, page in found.get("toc") or []]
    with zipfile.ZipFile(target) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    w = f"{{{W_NS}}}"
    slots = [r for r in root.iter(w + "r")
             if r.find(f"{w}rPr/{w}rStyle") is not None and r.find(f"{w}rPr/{w}rStyle").get(w + "val") == "TocPage"]
    if not pages or len(slots) != len(pages):
        return
    for r, page in zip(slots, pages, strict=True):
        t = r.find(w + "t")
        if t is None:
            t = etree.SubElement(r, w + "t")
        t.text = page
    data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = target.with_suffix(".tmp.docx")
    with zipfile.ZipFile(target) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zout.writestr(info, data if info.filename == "word/document.xml" else zin.read(info.filename))
    shutil.move(str(tmp), str(target))


def write(ctx: Context, target: Path) -> None:
    writer = DocxWriter(ctx)
    writer.build()
    writer.save(target)
