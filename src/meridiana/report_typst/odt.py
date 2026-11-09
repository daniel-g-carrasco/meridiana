"""The report as an ODT (odfpy): real styles named after what they are (Body, Heading 1-3, Caption, Source, Muted, Cell,
CellHead, CellDecimal...), the vertical scale of look.py in cm, headings that keep with the next paragraph, a page break
before each chapter, a header with the logo and the three lines, a footer with «page n of total», a table of contents
LibreOffice updates (text:table-of-content from the headings' outline, two levels, the numbers in a column, dots up to
the page), the PDF's two columns as a table without rules, the symbols as text (italic, real subscripts), the formulas
in display and the lines with the numbers as ODF Formula objects (MathML) at the size Typst gives them (or LibreOffice,
office.py), the Plex fonts embedded.

Called by editable.export; nothing here is imported until an ODT is asked for."""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

from . import embed_fonts
from .editable import (GUTTER_MM, Context, Item, Picture, TableSpec, clean, facts_spec, font_files, runs, step_spec,
                       table_spec)

UPPER = "uppercase"
COUNTRIES = {"it": "IT", "en": "GB", "de": "DE", "fr": "FR", "es": "ES"}
TEXT_STYLES = {"b": "Strong", "m": "Muted"}
CONTENTS_TAB = 1.4                 # cm: the contents' column of the numbers, the PDF's 14 mm
FORMULA_PT = {"display": 9.5, "numbers": 9.0, "inline": 9.0}   # the formulas' text, as the PDF's
FORMULA_BASE = {"display": 10, "numbers": 9, "inline": 9}      # LibreOffice Math's base size: whole points
SYMBOL_STYLES = {("", True): "Symbol", ("", False): "SymbolUpright", ("sub", True): "SymbolSub",
                 ("sub", False): "SymbolSubUpright", ("sup", True): "SymbolSup", ("sup", False): "SymbolSupUpright"}
TEXT_WIDTH = 17.4
# a row of a table as high as the PDF's: Typst sets a line from the cap height to the baseline, LibreOffice and Word from
# the ascender to the descender (a third more), so the line a little tighter and the cell's padding a little less
CELL_LINE = 90
CELL_PAD = 0.06


def cm(value: float) -> str:
    return f"{value:.3f}cm"


def pt(value: float) -> str:
    return f"{value:g}pt"


class OdtWriter:
    def __init__(self, ctx: Context):
        from odf import draw, style, table, text
        from odf.opendocument import OpenDocumentText
        self.ctx = ctx
        self.look = ctx.look
        self.S, self.T, self.TB, self.DR = style, text, table, draw
        self.doc = OpenDocumentText()
        self.formulas: list[tuple[str, str, str]] = []  # (object name, MathML, kind)
        self.frames: list = []                          # (frame, TeX, kind): their size set once all are known
        self.pictures: dict = {}                       # sha1 of the bytes -> href: a picture is stored once
        self.styles: dict = {}                         # automatic styles made on demand
        self.tables = 0
        self.out = None                                # where the blocks go: the text, or a column of a «two»

    # ---- styles ----

    def fonts(self) -> None:
        for family in self.look.families():
            generic = "modern" if "Mono" in family else "swiss"
            self.doc.fontfacedecls.addElement(self.S.FontFace(name=family, fontfamily=f"'{family}'",
                                                              fontfamilygeneric=generic, fontpitch="variable"))

    def paragraph_style(self, name, font=None, size=None, colour=None, before=0.0, after=0.0, keep=False, align=None,
                        parent="Standard", display=None, outline=None, tabs=(), automatic=False, hyphenate=False,
                        spacing=None, upper=False, master=None, break_before=False, border_left=None, border=None,
                        fill=None, padding=None, keep_together=False, indent=None, border_top=None, paddings=None, line=None):
        S = self.S
        args = {"name": name, "family": "paragraph"}
        if name != "Standard":
            args["parentstylename"] = parent
        if display:
            args["displayname"] = display
        if outline:
            args["defaultoutlinelevel"] = str(outline)
        if master:
            args["masterpagename"] = master
        st = S.Style(**args)
        tp = {}
        if font:
            tp["fontname"] = font
        if size:
            tp["fontsize"] = pt(size)
        if colour:
            tp["color"] = colour
        if hyphenate:
            tp["hyphenate"] = "true"
        elif name != "Standard":
            tp["hyphenate"] = "false"
        if spacing:
            tp["letterspacing"] = spacing
        if upper:
            tp["texttransform"] = UPPER
        if tp:
            st.addElement(S.TextProperties(**tp))
        pp = {}
        if name != "Standard":
            pp["margintop"] = cm(before)
            if after is not None:
                pp["marginbottom"] = cm(after)
        if keep:
            pp["keepwithnext"] = "always"
        if keep_together:
            pp["keeptogether"] = "always"
        if align:
            pp["textalign"] = align
        if break_before:
            pp["breakbefore"] = "page"
        if border_left:
            pp["borderleft"] = border_left
        if border_top:
            pp["bordertop"] = border_top
        if border:
            pp["border"] = border
        if fill:
            pp["backgroundcolor"] = fill
        if padding is not None:
            pp["padding"] = cm(padding)
        for side, value in (paddings or {}).items():
            pp["padding" + side] = cm(value)
        if indent is not None:
            pp["textindent"] = cm(indent)
        if line:
            pp["lineheight"] = f"{line}%"
        if pp or tabs:
            para = S.ParagraphProperties(**pp)
            if tabs:
                stops = S.TabStops()
                for position, kind, extra in tabs:
                    stops.addElement(S.TabStop(position=cm(position), type=kind, **extra))
                para.addElement(stops)
            st.addElement(para)
        (self.doc.automaticstyles if automatic else self.doc.styles).addElement(st)
        return name

    def text_style(self, name, font=None, size=None, colour=None, italic=False, position=None):
        tp = {}
        if font:
            tp["fontname"] = font
        if size:
            tp["fontsize"] = pt(size)
        if colour:
            tp["color"] = colour
        if italic:
            tp["fontstyle"] = "italic"
        if position:
            tp["textposition"] = position
        st = self.S.Style(name=name, family="text")
        st.addElement(self.S.TextProperties(**tp))
        self.doc.styles.addElement(st)

    def define_styles(self) -> None:
        S, lk = self.S, self.look
        language = self.ctx.lang.split("-")[0].split("_")[0]
        base = {"fontname": lk.body, "fontsize": pt(lk.size), "color": lk.ink, "language": language}
        if language in COUNTRIES:
            base["country"] = COUNTRIES[language]
        standard = S.Style(name="Standard", family="paragraph", displayname="Standard")
        standard.addElement(S.TextProperties(**base))
        standard.addElement(S.ParagraphProperties(margintop="0cm", marginbottom="0cm"))
        self.doc.styles.addElement(standard)
        P = self.paragraph_style
        justify = "justify" if lk.justify else None
        P("Body", after=lk.cm("par"), align=justify, display="Body", hyphenate=lk.hyphenate)
        P("Lead", size=10.5, before=0.14, after=0.28, align=justify, display="Lead")
        P("Muted", size=8.6, colour=lk.txt2, before=0.14, after=0.21, display="Muted")
        P("Source", font=lk.table, size=7, colour=lk.faint, before=0.1, after=0.25, display="Source")
        P("Caption", size=7.6, colour=lk.txt2, before=lk.cm("capa"), after=lk.cm("capb"), display="Caption", keep_together=True)
        P("Picture", before=lk.cm("figa"), after=0.1, keep=True, display="Picture")
        # a chapter always opens a page, where Typst drops the space above: none here either
        P("Heading_20_1", font=lk.strong, size=17, before=0, after=lk.cm("h1b"), keep=True, outline=1,
          display="Heading 1", break_before=True)
        P("Heading_20_2", font=lk.strong, size=11, before=lk.cm("h2a"), after=lk.cm("h2b"), keep=True, outline=2,
          display="Heading 2")
        P("Heading_20_3", font=lk.strong, size=9.6, before=lk.cm("h3a"), after=lk.cm("h3b"), keep=True, outline=3,
          display="Heading 3")
        P("Heading_20_4", font=lk.strong, size=8.8, colour=lk.txt2, before=lk.cm("h4a"), after=lk.cm("h4b"), keep=True,
          outline=4, display="Heading 4")
        P("Contents_20_Heading", font=lk.strong, size=17, before=0, after=lk.cm("h1b"), keep=True, display="Contents Heading",
          master="Standard", break_before=True)
        # the contents as the PDF's: the number in a column of 14 mm, dots up to the page (ink for the chapters,
        # faint for the sections)
        P("Contents_20_1", font=lk.strong, size=lk.size, before=0.32, after=0, display="Contents 1", keep=True, line=90,
          tabs=[(CONTENTS_TAB, "left", {}), (TEXT_WIDTH, "right", {"leaderstyle": "dotted", "leadertext": ".",
                                                                    "leadercolor": lk.ink})])
        P("Contents_20_2", size=lk.size, before=0, after=0, display="Contents 2", line=90,
          tabs=[(CONTENTS_TAB, "left", {}), (TEXT_WIDTH, "right", {"leaderstyle": "dotted", "leadertext": ".",
                                                                    "leadercolor": lk.faint})])
        P("AfterCover", size=1, master="Standard", break_before=True, display="After cover")
        P("Equation", size=lk.size, before=lk.cm("eqa"), after=lk.cm("eqb"), display="Equation", keep_together=True,
          tabs=[(TEXT_WIDTH / 2, "center", {}), (TEXT_WIDTH, "right", {})])
        P("Label", font=lk.table, size=8, colour=lk.txt2, before=lk.cm("par"), after=0.07, keep=True, display="Label")
        P("Values", font=lk.table, size=8, colour=lk.txt2, before=lk.cm("par"), after=0.1, display="Values", keep=True)
        P("ResultLine", font=lk.table, size=9, before=0.1, after=lk.cm("par"), display="Result line", fill=lk.tint,
          border_left=f"1.4pt solid {lk.accent}", paddings={"left": 0.28, "right": 0.28, "top": 0.18, "bottom": 0.18})
        P("Reference", font=lk.table, size=7.4, colour=lk.faint, before=0.07, after=lk.cm("capb"), display="Reference")
        P("ListItem", size=9, after=lk.cm("lista"), display="List Item", align=justify)
        P("PageBreak", size=1, break_before=True, display="Page break")
        P("LogoBox", size=6.5, colour=lk.faint, align="center", spacing="0.06cm", border=f"0.5pt dashed {lk.rule}",
          padding=0.2, display="Logo box")
        P("Cell", font=lk.table, size=lk.table_size, display="Cell", line=CELL_LINE)
        P("CellRight", align="end", display="Cell Right", parent="Cell")
        P("CellHead", size=7.8, colour=lk.head_text, display="Cell Head", parent="Cell")
        P("CellHeadRight", size=7.8, colour=lk.head_text, align="end", display="Cell Head Right", parent="Cell")
        P("CellLabel", size=8.5, colour=lk.txt2, display="Cell Label", parent="Cell")
        P("CellFact", size=8.5, display="Cell Fact", parent="Cell")
        P("CellFactRight", size=8.5, align="end", display="Cell Fact Right", parent="Cell")
        P("CellSource", font=lk.mono, size=6.6, colour=lk.faint, display="Cell Source", parent="Cell")
        P("CellSourceRight", font=lk.mono, size=6.6, colour=lk.faint, align="end", display="Cell Source Right",
          parent="Cell")
        P("CellSmall", size=7.4, colour=lk.txt2, display="Cell Small", parent="Cell")
        P("Column", size=1, display="Column")        # the empty paragraph a column of a «two» must hold
        for name, align in (("Left", "start"), ("Centre", "center"), ("Right", "end")):
            P(f"Strong{name}", font=lk.strong, size=7, before=0, after=0.08, align=align, display=f"Strong {name}")
            P(f"Plain{name}", font=lk.body, size=7, colour=lk.txt2, before=0, after=0.08, align=align,
              display=f"Plain {name}")
        P("HeaderTitle", font=lk.strong, size=8, before=0, after=0.08, align="end", display="Header Title")
        P("CoverTitle", size=24, before=0, after=0.2, display="Cover Title")
        P("CoverSub", size=11, colour=lk.txt2, before=0, after=0.2, display="Cover Sub")
        P("CoverLabel", font=lk.strong, size=7.5, colour=lk.accent, before=0.6, after=0.15, upper=True, spacing="0.05cm",
          display="Cover Label")
        P("CoverPlant", font=lk.medium, size=15, before=0, after=0.2, display="Cover Plant")
        P("CoverPlantSub", size=9.5, colour=lk.txt2, before=0, after=0, display="Cover Plant Sub")
        P("CoverMetaLabel", font=lk.strong, size=6.6, colour=lk.txt2, before=0.35, after=0, upper=True, spacing="0.03cm",
          display="Cover Meta Label", keep=True)
        P("CoverMeta", size=8.4, before=0, after=0, display="Cover Meta")
        P("CoverImage", before=0.8, after=0, keep=True, display="Cover Image")
        P("CoverMade", font=lk.body, size=7, colour=lk.faint, before=0.6, after=0, align="end", display="Cover Made",
          border_top=f"0.5pt solid {lk.ink}", paddings={"top": 0.18})
        P("Kicker", font=lk.strong, size=7.6, colour=lk.accent, upper=True, spacing="0.05cm", after=0.14, display="Kicker",
          keep=True)
        P("HeadTitle", size=21, after=0.28, display="Head Title", keep=True)
        P("HeadSub", size=9.6, colour=lk.txt2, before=0.1, after=0.1, display="Head Sub")
        # text styles
        self.text_style("Strong", font=lk.strong)
        self.text_style("StrongCell", font=lk.table_strong)
        self.text_style("Muted", colour=lk.txt2)
        self.text_style("Code", font=lk.mono, size=8, colour=lk.accent)
        self.text_style("Number", font=lk.table, size=8, colour=lk.txt2)
        self.text_style("Medium", font=lk.table, colour=lk.txt2)
        # the symbols as text: Plex Sans, the letters in its italic, the scripts as real sub- and superscripts
        for (pos, italic), name in SYMBOL_STYLES.items():
            self.text_style(name, font=lk.symbol, italic=italic,
                            position={"": None, "sub": "sub 66%", "sup": "super 66%"}[pos])
        # the chapters' numbers as LibreOffice's outline numbering (Tools > Heading Numbering): «9», «9.1» as the
        # PDF's, the levels below without; a heading the PDF does not number is a list header
        outline = self.T.OutlineStyle(name="Outline")
        for level in range(1, 11):
            args = {"level": level, "numformat": "1" if level <= 2 else ""}
            if level == 2:
                args["displaylevels"] = 2
            ols = self.T.OutlineLevelStyle(**args)
            props = S.ListLevelProperties(listlevelpositionandspacemode="label-alignment")
            props.addElement(S.ListLevelLabelAlignment(labelfollowedby="space", textindent="0cm", marginleft="0cm"))
            ols.addElement(props)
            outline.addElement(ols)
        self.doc.styles.addElement(outline)
        # the bullet list
        ls = self.T.ListStyle(name="Bullets")
        level = self.T.ListLevelStyleBullet(level=1, bulletchar="–", numsuffix=" ")
        level.addElement(S.ListLevelProperties(spacebefore="0.2cm", minlabelwidth="0.5cm"))
        level.addElement(S.TextProperties(color=lk.accent))
        ls.addElement(level)
        self.doc.styles.addElement(ls)
        # the page: header and footer on the pages, nothing on the cover
        left, right = cm(lk.margin_left / 10), "1.6cm"
        pl = S.PageLayout(name="PageLayout")
        pl.addElement(S.PageLayoutProperties(pagewidth="21cm", pageheight="29.7cm", printorientation="portrait",
                                             margintop="1.0cm", marginbottom="0.9cm", marginleft=left, marginright=right))
        header_style, footer_style = S.HeaderStyle(), S.FooterStyle()
        header_style.addElement(S.HeaderFooterProperties(minheight="1.3cm", marginbottom="0.4cm"))
        footer_style.addElement(S.HeaderFooterProperties(minheight="0.9cm", margintop="0.3cm"))
        pl.addElement(header_style)
        pl.addElement(footer_style)
        self.doc.automaticstyles.addElement(pl)
        cover = S.PageLayout(name="CoverLayout")
        cover.addElement(S.PageLayoutProperties(pagewidth="21cm", pageheight="29.7cm", printorientation="portrait",
                                                margintop="2.0cm", marginbottom="1.8cm", marginleft=left, marginright=right))
        self.doc.automaticstyles.addElement(cover)
        self.page_layout, self.cover_layout = pl, cover
        # graphic styles: the pictures set on the baseline; the formulas without a border or a padding, on the
        # baseline of the text (MathBaselineAlignment in the settings)
        frame = S.Style(name="Inline", family="graphic")
        frame.addElement(S.GraphicProperties(wrap="none", verticalpos="top", verticalrel="baseline",
                                             marginleft="0cm", marginright="0cm"))
        self.doc.automaticstyles.addElement(frame)
        self.frame_style = frame
        formula = S.Style(name="FormulaFrame", family="graphic")
        formula.addElement(S.GraphicProperties(wrap="none", verticalpos="top", verticalrel="baseline", border="none",
                                               padding="0cm", margin="0cm", stroke="none", fill="none",
                                               oledrawaspect="1"))
        self.doc.automaticstyles.addElement(formula)
        self.formula_style = formula

    def settings(self) -> None:
        """The document's settings: the formulas on the baseline of the text, between two paragraphs the larger of the
        two spaces and none above the first paragraph of a page (as Typst), the fonts embedded on a save."""
        from odf.config import ConfigItem, ConfigItemSet
        items = ConfigItemSet(name="ooo:configuration-settings")
        # AddParaTableSpacing false: between two paragraphs the larger of the two spaces, as Typst's weak spacing;
        # PropLineSpaceShrinksFirstLine: a line spacing under 100 % (the tables' cells) holds for a first line too
        for name, kind, value in (("MathBaselineAlignment", "boolean", "true"),
                                  ("AddParaTableSpacing", "boolean", "false"),
                                  ("AddParaTableSpacingAtStart", "boolean", "false"),
                                  ("PropLineSpaceShrinksFirstLine", "boolean", "true"),
                                  ("EmbedFonts", "boolean", "true")):
            item = ConfigItem(name=name, type=kind)
            item.addText(value)
            items.addElement(item)
        self.doc.settings.addElement(items)

    def table_style(self, width: float, master=None, before=None, after=None) -> str:
        lk = self.look
        before = lk.cm("taba") if before is None else before
        after = lk.cm("tabb") if after is None else after
        key = ("table", round(width, 2), master, before, after)
        if key not in self.styles:
            name = f"Table{len(self.styles)}"
            st = self.S.Style(name=name, family="table", **({"masterpagename": master} if master else {}))
            st.addElement(self.S.TableProperties(width=cm(width), align="left", margintop=cm(before),
                                                 marginbottom=cm(after)))
            self.doc.automaticstyles.addElement(st)
            self.styles[key] = name
        return self.styles[key]

    def column_style(self, width: float) -> str:
        key = ("column", round(width, 3))
        if key not in self.styles:
            name = f"Column{len(self.styles)}"
            st = self.S.Style(name=name, family="table-column")
            st.addElement(self.S.TableColumnProperties(columnwidth=cm(width)))
            self.doc.automaticstyles.addElement(st)
            self.styles[key] = name
        return self.styles[key]

    def cell_style(self, fill=None, border="grid", pad=None, valign="top") -> str:
        """The look of a table cell: the thin grey grid, a rule on one side (header and footer), or nothing; `pad`
        (cm: left, right, top, bottom) instead of the grid's."""
        key = ("cell", fill, border, pad, valign)
        if key not in self.styles:
            lk = self.look
            name = f"Cell{len(self.styles)}"
            y = cm(CELL_PAD)
            props = {"paddingleft": "0.14cm", "paddingright": "0.14cm", "paddingtop": y, "paddingbottom": y,
                     "verticalalign": valign}
            if border == "grid":
                props["border"] = f"0.4pt solid {lk.grid}"
            elif border == "bottom":
                props.update(border="none", borderbottom=f"{lk.hf_rule}pt solid {lk.hf_colour}", paddingleft="0cm",
                             paddingright="0cm", paddingtop="0cm", paddingbottom="0.15cm", verticalalign="bottom")
            elif border == "top":
                props.update(border="none", bordertop=f"{lk.hf_rule}pt solid {lk.hf_colour}", paddingleft="0cm",
                             paddingright="0cm", paddingtop="0.15cm", paddingbottom="0cm")
            elif border == "ink":
                props.update(border="none", borderbottom=f"0.5pt solid {lk.ink}", paddingleft="0cm", paddingright="0cm",
                             paddingtop="0cm", paddingbottom="0.15cm", verticalalign="bottom")
            elif border == "accent":
                props.update(border="none", borderleft=f"1.2pt solid {lk.accent}", paddingleft="0.5cm",
                             paddingright="0cm", paddingtop="0.1cm", paddingbottom="0.1cm")
            else:
                props.update(border="none", paddingleft="0cm", paddingright="0cm", paddingtop="0cm", paddingbottom="0cm")
            if pad is not None:
                props.update(paddingleft=cm(pad[0]), paddingright=cm(pad[1]), paddingtop=cm(pad[2]),
                             paddingbottom=cm(pad[3]))
            if fill:
                props["backgroundcolor"] = fill
            st = self.S.Style(name=name, family="table-cell")
            st.addElement(self.S.TableCellProperties(**props))
            self.doc.automaticstyles.addElement(st)
            self.styles[key] = name
        return self.styles[key]

    def decimal_style(self, width: float, share: float) -> str:
        """A cell paragraph whose digits fall on the comma: a tab stop of type char, where the template puts it."""
        position = round(share * (width - 0.28), 2)
        key = ("decimal", position)
        if key not in self.styles:
            name = f"CellDecimal{len(self.styles)}"
            self.paragraph_style(name, font=self.look.table, size=self.look.table_size, parent="Cell", automatic=True,
                                 tabs=[(position, "char", {"char": ","})], display=name)
            self.styles[key] = name
        return self.styles[key]

    # ---- text ----

    def put_text(self, parent, value: str) -> None:
        """Text with its tabs, line breaks and runs of spaces as ODF writes them (it collapses plain spaces)."""
        for part in re.split(r"(\t|\n| {2,})", clean(value)):
            if part == "\t":
                parent.addElement(self.T.Tab())
            elif part == "\n":
                parent.addElement(self.T.LineBreak())
            elif part.startswith("  "):
                parent.addText(" ")
                parent.addElement(self.T.S(c=len(part) - 1))
            elif part:
                parent.addText(part)

    def picture_href(self, picture: Picture) -> str:
        # by its bytes: a Picture's id is reused once it is gone, and the same picture made twice is stored once
        key = hashlib.sha1(picture.data).hexdigest()
        if key not in self.pictures:
            self.pictures[key] = self.doc.addPictureFromString(picture.data, picture.mime)
        return self.pictures[key]

    def frame_for_picture(self, picture: Picture, name: str):
        frame = self.DR.Frame(stylename=self.frame_style, anchortype="as-char", width=cm(picture.width),
                              height=cm(picture.height), name=name)
        frame.addElement(self.DR.Image(href=self.picture_href(picture)))
        self.ctx.stats["images"] += 1
        return frame

    def formula(self, tex: str, kind: str = "inline"):
        """A draw:frame with the formula as an ODF Formula object (its size set at the end, from Typst); the TeX as
        plain text when it cannot be converted."""
        ml = self.ctx.mathml(tex)
        if not ml:
            return self.T.Span(text=tex)
        if kind == "display":
            ml = ml.replace('display="inline"', 'display="block"', 1)
        n = len(self.formulas) + 1
        self.formulas.append((f"Object {n}", ml, kind))
        self.ctx.stats["formulas"] += 1
        frame = self.DR.Frame(stylename=self.formula_style, anchortype="as-char", width="1cm", height="0.5cm",
                              name=f"Formula{n}")
        frame.addElement(self.DR.Object(href=f"./Object {n}", type="simple", show="embed", actuate="onLoad"))
        self.frames.append((frame, tex, kind))
        return frame

    def size_frames(self) -> None:
        """Each formula's frame at the size Typst gives the formula (the PDF's), so LibreOffice draws it unscaled;
        a guess from its characters when Typst cannot."""
        sizes = self.ctx.formula_sizes([(tex, FORMULA_PT[kind], "numbers" if kind == "numbers" else "display")
                                        for _f, tex, kind in self.frames])
        for (frame, tex, _kind), size in zip(self.frames, sizes, strict=True):
            if size is None:
                characters = len(re.sub(r"\\[A-Za-z]+|[{}_^]", "", tex))
                size = (max(0.4, min(15.0, 0.19 * characters)), 0.5)
            frame.setAttribute("width", cm(size[0]))
            frame.setAttribute("height", cm(size[1]))

    def symbol(self, parent, tex: str) -> bool:
        """A symbol as text in `parent` (italic letters, real subscripts); False when it has to stay a formula."""
        pieces = self.ctx.symbol(tex)
        if pieces is None:
            return False
        for piece in pieces:
            span = self.T.Span(stylename=SYMBOL_STYLES[(piece.pos, piece.italic)])
            span.addText(piece.text)
            parent.addElement(span)
        return True

    def fill(self, parent, content, cell: bool = False, strong: bool = False) -> None:
        """Runs into a paragraph: bold and muted spans, the marks as small pictures, the symbols as text."""
        for r in runs(content):
            if r.kind == "mark":
                picture = self.ctx.mark(r.text)
                if picture is not None:
                    parent.addElement(self.frame_for_picture(picture, "Mark"))
                    parent.addText(" ")
            elif r.kind == "formula":
                tex = self.ctx.tex_of(r.text)
                if tex and not self.symbol(parent, tex):
                    parent.addElement(self.formula(tex))
            elif r.kind == "b" or (strong and r.kind != "m"):
                parent.addElement(self.T.Span(stylename="StrongCell" if cell else "Strong", text=r.text))
            elif r.kind == "m":
                parent.addElement(self.T.Span(stylename="Muted", text=r.text))
            else:
                self.put_text(parent, r.text)

    def paragraph(self, content, style="Body"):
        p = self.T.P(stylename=style)
        self.fill(p, content)
        self.out.addElement(p)
        return p

    def heading(self, level: int, text: str, extra=None):
        """A heading on its outline level; the number of a chapter or a section is the outline numbering's (the text
        has it before a tab: «9.1<tab>Title»), a heading of level 1 or 2 without one is a list header."""
        number, tab, title = text.partition("\t")
        args = {"outlinelevel": level, "stylename": f"Heading_20_{min(level, 4)}"}
        if level <= 2:
            if tab:
                text = title
            else:
                args["islistheader"] = "true"
        h = self.T.H(**args)
        if extra:
            h.addElement(self.T.Span(stylename="Code", text=extra))
            h.addText(" ")
            h.addElement(self.T.S(c=1))
        self.put_text(h, text)
        self.out.addElement(h)

    # ---- tables ----

    def cell_paragraph(self, cell, width: float, share: float, facts: bool = False):
        if cell.kind == "head":
            style = "CellHeadRight" if cell.align == "right" else "CellHead"
        elif cell.kind == "label":
            style = "CellLabel"
        elif cell.kind == "source":
            style = "CellSourceRight" if cell.align == "right" else "CellSource"
        elif cell.kind == "small":
            style = "CellSmall"
        elif cell.align == "decimal":
            style = self.decimal_style(width, share)
        elif facts:
            style = "CellFactRight" if cell.align == "right" else "CellFact"
        elif cell.align == "right":
            style = "CellRight"
        else:
            style = "Cell"
        p = self.T.P(stylename=style)
        if cell.tex:
            if not self.symbol(p, cell.tex):
                p.addElement(self.formula(cell.tex))
        else:
            self.fill(p, cell.content, cell=True, strong=cell.strong)
        return p

    def table(self, spec: TableSpec, facts: bool = False, before=None, after=None) -> None:
        lk = self.look
        self.ctx.stats["tables"] += 1
        self.tables += 1
        total = sum(spec.widths)
        t = self.TB.Table(stylename=self.table_style(total, before=before, after=after), name=f"Table{self.tables}")
        for width in spec.widths:
            t.addElement(self.TB.TableColumn(stylename=self.column_style(width)))
        header = self.TB.TableHeaderRows() if spec.head_rows else None
        pad = (0.127, 0.127, CELL_PAD, CELL_PAD) if facts else None
        for r, row in enumerate(spec.rows):
            tr = self.TB.TableRow()
            column = 0
            for cell in row:
                width = sum(spec.widths[column:column + cell.span])
                fill = lk.head_fill if cell.kind == "head" else lk.tint if cell.fill == "tint" or cell.span > 1 else None
                args = {"stylename": self.cell_style(fill, pad=pad,
                                                     valign="bottom" if cell.kind == "head" else "top"),
                        "valuetype": "string"}
                if cell.span > 1:
                    args["numbercolumnsspanned"] = cell.span
                c = self.TB.TableCell(**args)
                c.addElement(self.cell_paragraph(cell, width, spec.share, facts))
                tr.addElement(c)
                for _ in range(cell.span - 1):
                    tr.addElement(self.TB.CoveredTableCell())
                column += cell.span
            if r < spec.head_rows:
                header.addElement(tr)
            else:
                if header is not None:
                    t.addElement(header)
                    header = None
                t.addElement(tr)
        if header is not None:
            t.addElement(header)
        self.out.addElement(t)

    def columns(self, widths: list, fill) -> None:
        """Side by side, as the template's grid: a table of one row without rules, a column for each part, the gutter
        as the left column's padding; fill(i) writes column i (self.out is its cell meanwhile)."""
        self.tables += 1
        gutter = GUTTER_MM / 10
        cm_widths = [widths[0] + gutter] + list(widths[1:])
        t = self.TB.Table(stylename=self.table_style(sum(cm_widths), before=0, after=0), name=f"Columns{self.tables}")
        for w in cm_widths:
            t.addElement(self.TB.TableColumn(stylename=self.column_style(w)))
        tr = self.TB.TableRow()
        outer = self.out
        for i in range(len(widths)):
            c = self.TB.TableCell(stylename=self.cell_style(None, "none", pad=(0, gutter if i == 0 else 0, 0, 0)),
                                  valuetype="string")
            self.out = c
            fill(i)
            if not c.childNodes:
                c.addElement(self.T.P(stylename="Column"))
            self.flush_top(c)
            tr.addElement(c)
        self.out = outer
        t.addElement(tr)
        self.out.addElement(t)

    def flush_top(self, cell) -> None:
        """The first paragraph of a column without its space above, as a block at the top of Typst's grid cell."""
        first = cell.childNodes[0] if cell.childNodes else None
        if first is None or first.qname[1] not in ("p", "h"):
            return
        parent = first.getAttribute("stylename")
        key = ("flush", parent)
        if key not in self.styles:
            name = f"{parent}_Top"
            self.paragraph_style(name, parent=parent, automatic=True, before=0, after=None)
            self.styles[key] = name
        first.setAttribute("stylename", self.styles[key])

    # ---- the page: header, footer, cover ----

    def logo_cell(self, height=10.0, room=40.0, box=(3.6, 0.9)):
        """The logo as a paragraph, or the dashed «LOGO» box, or None; and the width it needs (cm)."""
        picture = self.ctx.logo(height, room)
        if picture is not None:
            p = self.T.P(stylename="PlainLeft")
            p.addElement(self.frame_for_picture(picture, "Logo"))
            return p, picture.width + 0.3
        if self.ctx.wants_logo_placeholder():
            p = self.T.P(stylename="LogoBox")
            p.addText("LOGO")
            return p, box[0] + 0.3
        return None, 0.6

    def side_table(self, columns, border, name, master=None):
        """A table of one row for the header, the footer and the cover's first line: columns = [(width, [paragraphs])]."""
        t = self.TB.Table(stylename=self.table_style(sum(w for w, _p in columns), master, 0, 0), name=name)
        for w, _p in columns:
            t.addElement(self.TB.TableColumn(stylename=self.column_style(w)))
        tr = self.TB.TableRow()
        for _w, paragraphs in columns:
            c = self.TB.TableCell(stylename=self.cell_style(None, border), valuetype="string")
            if not paragraphs:
                paragraphs = [self.T.P(stylename="PlainLeft")]
            for p in paragraphs:
                c.addElement(p)
            tr.addElement(c)
        t.addElement(tr)
        return t

    def master_pages(self) -> None:
        S, ctx = self.S, self.ctx
        logo, logo_width = self.logo_cell()
        right = []
        for text, kind in ctx.header_lines():
            if text:
                p = self.T.P(stylename="HeaderTitle" if kind == "strong" else "PlainRight")
                p.addText(text)
                right.append(p)
        width = 21.0 - self.look.margin_left / 10 - 1.6
        header = S.Header()
        header.addElement(self.side_table([(logo_width, [logo] if logo is not None else []), (width - logo_width, right)],
                                          "bottom", "HeaderTable"))
        footer = S.Footer()
        columns = []
        for i, cells in enumerate(ctx.footer_cells()):
            align = ("Left", "Centre", "Right")[i]
            paragraphs = []
            for text, kind in cells:
                if kind == "page":
                    p = self.T.P(stylename="PlainRight")
                    for part in ctx.page_line():
                        if part == "{n}":
                            number = self.T.PageNumber(selectpage="current")
                            number.addText("1")
                            p.addElement(number)
                        elif part == "{total}":
                            count = self.T.PageCount()
                            count.addText("1")
                            p.addElement(count)
                        else:
                            p.addText(clean(part))
                    paragraphs.append(p)
                elif text:
                    p = self.T.P(stylename=f"{'Strong' if kind == 'strong' else 'Plain'}{align}")
                    p.addText(text)
                    paragraphs.append(p)
            columns.append((width / 3, paragraphs))
        footer.addElement(self.side_table(columns, "top", "FooterTable"))
        standard = S.MasterPage(name="Standard", pagelayoutname=self.page_layout)
        standard.addElement(header)
        standard.addElement(footer)
        self.doc.masterstyles.addElement(standard)
        self.doc.masterstyles.addElement(S.MasterPage(name="Cover", pagelayoutname=self.cover_layout,
                                                      nextstylename="Standard"))

    def cover(self, c: dict) -> None:
        """The cover as the PDF's: the logo's row, then the title and the plant on the left and the data in a column of
        60 mm with a rule on its left, the 3D view large, the line of who made it at the foot."""
        ctx, lk = self.ctx, self.look
        d = ctx.doc
        logo, logo_width = self.logo_cell(14.0, 60.0, (5.6, 1.4))
        right = []
        for text, style in ((clean(d.get("foot_left", "")), "StrongRight"), (clean(d.get("foot_left2", "")), "PlainRight")):
            if text:
                p = self.T.P(stylename=style)
                p.addText(text)
                right.append(p)
        width = 21.0 - lk.margin_left / 10 - 1.6
        # the first element of the body names the master page of the cover (no header, no footer)
        first = self.side_table([(logo_width, [logo] if logo is not None else []), (width - logo_width, right)], "ink",
                                "CoverTable", master="Cover")
        self.out.addElement(first)
        t = self.TB.Table(stylename=self.table_style(width, before=1.0, after=0), name="CoverColumns")
        for w in (width - 6.0, 6.0):
            t.addElement(self.TB.TableColumn(stylename=self.column_style(w)))
        tr = self.TB.TableRow()
        left = self.TB.TableCell(stylename=self.cell_style(None, "none", pad=(0, 1.0, 0, 0)), valuetype="string")
        right_cell = self.TB.TableCell(stylename=self.cell_style(None, "accent"), valuetype="string")
        outer = self.out
        self.out = left
        self.paragraph(clean(d.get("doc_title") or ctx.word("report")), "CoverTitle")
        if d.get("doc_sub"):
            self.paragraph(clean(d["doc_sub"]), "CoverSub")
        self.paragraph(ctx.word("plant"), "CoverLabel")
        self.paragraph(clean(c.get("title", "")), "CoverPlant")
        if c.get("sub"):
            self.paragraph(clean(c["sub"]), "CoverPlantSub")
        self.out = right_cell
        for i, m in enumerate(c.get("meta") or []):
            p = self.paragraph(clean(m.get("t", "")), "CoverMetaLabel")
            if i == 0:
                p.setAttribute("stylename", self.first_meta_style())
            for line in m.get("lines") or []:
                self.paragraph(clean(line), "CoverMeta")
        if not right_cell.childNodes:
            right_cell.addElement(self.T.P(stylename="Column"))
        self.out = outer
        tr.addElement(left)
        tr.addElement(right_cell)
        t.addElement(tr)
        self.out.addElement(t)
        if c.get("image"):
            picture = ctx.figure({"image": c["image"], "max_h": 112.0, "tint": c.get("tint"), "inset": c.get("inset", 0)},
                                 174.0, 112.0)
            if picture is not None:
                self.picture_paragraph(picture, "CoverImage", "CoverImage")
        if c.get("made"):
            self.paragraph(clean(c["made"]), "CoverMade")

    def first_meta_style(self) -> str:
        if "first_meta" not in self.styles:
            self.styles["first_meta"] = self.paragraph_style("CoverMetaFirst", parent="CoverMetaLabel", automatic=True,
                                                             before=0)
        return self.styles["first_meta"]

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
        """A table of contents LibreOffice updates (Tools > Update): from the headings' outline, two levels, each entry
        the heading's text («9.1<tab>Title», the number in its column), dots up to the page number. Written already
        filled: the page numbers are LibreOffice's when it measured the file (apply), else they come at the first
        update."""
        ctx, T = self.ctx, self.T
        link = self.S.Style(name="Index_20_Link", displayname="Index Link", family="text")
        link.addElement(self.S.TextProperties(color=self.look.ink))
        self.doc.styles.addElement(link)
        toc = T.TableOfContent(name="Contents", protected="true")
        source = T.TableOfContentSource(outlinelevel=int(self.look.style.get("toc_levels", 2)), useoutlinelevel="true",
                                        useindexmarks="false")
        title = T.IndexTitleTemplate(stylename="Contents_20_Heading")
        title.addText(ctx.word("contents"))
        source.addElement(title)
        for level in (1, 2):
            template = T.TableOfContentEntryTemplate(outlinelevel=level, stylename=f"Contents_20_{level}")
            template.addElement(T.IndexEntryLinkStart(stylename="Index_20_Link"))
            template.addElement(T.IndexEntryChapter(display="number"))
            if level == 1:
                template.addElement(T.IndexEntrySpan(text="."))
            template.addElement(T.IndexEntryTabStop(type="left", position=cm(CONTENTS_TAB)))
            template.addElement(T.IndexEntryText())
            template.addElement(T.IndexEntryTabStop(type="right", leaderchar="."))
            template.addElement(T.IndexEntryPageNumber())
            template.addElement(T.IndexEntryLinkEnd())
            source.addElement(template)
        toc.addElement(source)
        body = T.IndexBody()
        index_title = T.IndexTitle(name="ContentsTitle")
        index_title.addElement(T.P(stylename="Contents_20_Heading", text=ctx.word("contents")))
        body.addElement(index_title)
        for level, text in ctx.toc_entries():
            p = T.P(stylename=f"Contents_20_{min(level, 2)}")
            number, tab, title = text.partition("\t")
            self.put_text(p, (number + ("." if level == 1 else "") + "\t" + title) if tab else "\t" + text)
            p.addElement(T.Tab())
            body.addElement(p)
        toc.addElement(body)
        self.out.addElement(toc)

    # ---- blocks ----

    def picture_paragraph(self, picture: Picture, name: str, style: str = "Picture"):
        p = self.T.P(stylename=style)
        p.addElement(self.frame_for_picture(picture, name))
        self.out.addElement(p)

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
        self.heading(1, item.text)
        from ..i18n import _
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
        lst = self.T.List(stylename="Bullets")
        for x in item.block.get("items") or []:
            li = self.T.ListItem()
            p = self.T.P(stylename="ListItem")
            self.fill(p, x)
            li.addElement(p)
            lst.addElement(li)
        self.out.addElement(lst)

    def do_facts(self, item: Item) -> None:
        self.table(facts_spec(item.block, item.width), facts=True)

    def do_table(self, item: Item) -> None:
        self.table(table_spec(item.block, item.width))

    def do_figure(self, item: Item, tall: float = 118.0) -> None:
        picture = self.ctx.figure(item.block, item.width, tall)
        if picture is not None:
            self.picture_paragraph(picture, "Figure")
            if item.block.get("caption") is not None:
                self.paragraph(item.block["caption"], "Caption")

    def do_fill_figure(self, item: Item) -> None:
        self.do_figure(item, 185.0)

    def do_drawn(self, item: Item) -> None:
        picture = self.ctx.drawn(item)
        if picture is not None:
            self.picture_paragraph(picture, item.kind.capitalize())

    def do_formula(self, item: Item) -> None:
        b = item.block
        tex = clean(b.get("tex") or self.ctx.tex_of(b.get("image", "")))
        if tex:
            p = self.T.P(stylename="Equation")
            p.addElement(self.T.Tab())
            p.addElement(self.formula(tex, "display"))
            self.out.addElement(p)

    def do_pagebreak(self, item: Item) -> None:
        self.out.addElement(self.T.P(stylename="PageBreak"))

    def do_step(self, item: Item) -> None:
        ctx, b = self.ctx, item.block
        self.heading(3, clean(b.get("title", "")), extra=clean(b.get("code", "")) or None)
        if b.get("explanation"):
            self.paragraph(b["explanation"], "Body")
        if b.get("tex"):
            p = self.T.P(stylename="Equation")
            p.addElement(self.T.Tab())
            p.addElement(self.formula(clean(b["tex"]), "display"))
            p.addElement(self.T.Tab())
            p.addElement(self.T.Span(stylename="Number", text=f"({clean(b.get('eq', ''))})"))
            self.out.addElement(p)
        if b.get("inputs") or b.get("result"):
            self.paragraph(ctx.word("where"), "Label")
            self.table(step_spec(b, ctx.step_words(), item.width), before=0.07, after=self.look.cm("par"))
        # the hour of the example, then the formula with the numbers ending in the result, in evidence (R479)
        if b.get("worked"):
            if b.get("example"):
                self.out.addElement(self.T.P(stylename="Values", text=clean(b["example"])))
            for tex in b["worked"]:
                p = self.T.P(stylename="ResultLine")
                p.addElement(self.formula(clean(tex), "numbers"))
                self.out.addElement(p)
        if b.get("reference"):
            self.paragraph(f"{ctx.word('reference')}: {clean(b['reference'])}", "Reference")

    # ---- the whole ----

    def build(self) -> None:
        ctx = self.ctx
        self.out = self.doc.text
        self.fonts()
        self.define_styles()
        self.settings()
        self.master_pages()
        d = ctx.document
        if d.get("cover"):
            self.cover(d["cover"])
        elif d.get("head"):
            self.compact_head(d["head"])
        if ctx.has_contents():
            self.contents()
        elif d.get("cover"):
            self.out.addElement(self.T.P(stylename="AfterCover"))
        self.write_items(ctx.items)
        self.size_frames()
        from odf.dc import Creator, Title
        title, author = clean(ctx.doc.get("title", "")), clean(ctx.doc.get("author", ""))
        if title:
            self.doc.meta.addElement(Title(text=title))
        if author:
            self.doc.meta.addElement(Creator(text=author))

    def save(self, target: Path) -> None:
        self.doc.save(str(target))
        if self.formulas:
            add_objects(target, [(name, ml, object_settings(self.look, kind)) for name, ml, kind in self.formulas])
        self.ctx.stats["fonts"] = embed_fonts.embed_odt(target, font_files(self.look))


def object_settings(look, kind: str = "inline") -> str:
    """The settings of a formula object (LibreOffice Math): the base size of the text, the report's sans for the
    letters (in italic, as the PDF's), the numbers and the words."""
    font = look.symbol
    items = [("BaseFontHeight", "short", str(FORMULA_BASE.get(kind, 9)))]
    for name in ("FontNameVariables", "FontNameFunctions", "FontNameNumbers", "FontNameText"):
        items.append((name, "string", font))
    items += [("FontVariablesIsItalic", "boolean", "true"), ("FontFunctionsIsItalic", "boolean", "false"),
              ("FontNumbersIsItalic", "boolean", "false"), ("FontTextIsItalic", "boolean", "false"),
              ("IsScaleAllBrackets", "boolean", "true")]
    body = "".join(f'<config:config-item config:name="{n}" config:type="{t}">{v}</config:config-item>' for n, t, v in items)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<office:document-settings '
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0" office:version="1.2"><office:settings>'
            f'<config:config-item-set config:name="ooo:configuration-settings">{body}</config:config-item-set>'
            '</office:settings></office:document-settings>')


def add_objects(target: Path, objects: list) -> None:
    """The formula objects: a folder «Object n» with its content.xml and settings.xml in the zip and their entries in
    the manifest. `objects`: (name, MathML, settings)."""
    tmp = target.with_suffix(".tmp")
    with zipfile.ZipFile(target) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == "META-INF/manifest.xml":
                extra = "".join(
                    f'<manifest:file-entry manifest:full-path="{n}/" manifest:media-type="application/vnd.oasis.opendocument.formula"/>'
                    f'<manifest:file-entry manifest:full-path="{n}/content.xml" manifest:media-type="text/xml"/>'
                    f'<manifest:file-entry manifest:full-path="{n}/settings.xml" manifest:media-type="text/xml"/>'
                    for n, _ml, _s in objects)
                data = data.decode("utf-8").replace("</manifest:manifest>", extra + "</manifest:manifest>").encode("utf-8")
            if info.filename == "mimetype":
                zout.writestr(info, data, compress_type=zipfile.ZIP_STORED)
            else:
                zout.writestr(info.filename, data)
        for name, xml, settings in objects:
            zout.writestr(name + "/content.xml", '<?xml version="1.0" encoding="UTF-8"?>\n' + xml)
            zout.writestr(name + "/settings.xml", settings)
    tmp.replace(target)


TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
DRAW_NS = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
SVG_NS = "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"


def apply(target: Path, found: dict) -> None:
    """What LibreOffice measured (office.measure) written into the ODT: each formula's frame at LibreOffice's size,
    the contents' entries with their page numbers."""
    from lxml import etree
    with zipfile.ZipFile(target) as z:
        content = z.read("content.xml")
    root = etree.fromstring(content)
    sizes = found.get("formulas") or {}
    for frame in root.iter(f"{{{DRAW_NS}}}frame"):
        size = sizes.get(frame.get(f"{{{DRAW_NS}}}name"))
        if size and size[0] > 0 and size[1] > 0:
            frame.set(f"{{{SVG_NS}}}width", f"{size[0] / 1000:.3f}cm")
            frame.set(f"{{{SVG_NS}}}height", f"{size[1] / 1000:.3f}cm")
    pages = [page for _text, page in found.get("toc") or []]
    for body in root.iter(f"{{{TEXT_NS}}}index-body"):
        entries = [p for p in body if p.tag == f"{{{TEXT_NS}}}p"]
        if len(entries) == len(pages):
            for p, page in zip(entries, pages, strict=True):
                tabs = p.findall(f"{{{TEXT_NS}}}tab")
                if tabs:
                    tabs[-1].tail = (tabs[-1].tail or "") + page
        break
    rewrite(target, {"content.xml": etree.tostring(root, xml_declaration=True, encoding="UTF-8")})


def rewrite(target: Path, changes: dict) -> None:
    tmp = target.with_suffix(".tmp")
    with zipfile.ZipFile(target) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = changes.get(info.filename, zin.read(info.filename))
            if info.filename == "mimetype":
                zout.writestr(info, data, compress_type=zipfile.ZIP_STORED)
            else:
                zout.writestr(info, data)
    tmp.replace(target)


def write(ctx: Context, target: Path) -> None:
    writer = OdtWriter(ctx)
    writer.build()
    writer.save(target)
