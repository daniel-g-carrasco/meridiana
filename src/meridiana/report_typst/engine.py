"""The compilation of the report with Typst (the `typst` wheel, Apache-2.0): a temporary folder that is the root of the
compilation and all Typst can read, with the look (template.typ), the data (data.json) and the images copied in; the
fonts from the program's own folder, no font of the system, so the PDF comes out the same on every machine.

The texts of the user reach Typst only inside data.json, as JSON strings the template shows as text. Nothing here or
in the template evaluates a string as markup."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .. import log, paths, symbol_shapes
from ..i18n import _

TEMPLATE = Path(__file__).resolve().parent / "template.typ"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")
LOGO_FORMATS = (("png", b"\x89PNG"), ("jpg", b"\xff\xd8"), ("gif", b"GIF8"))


class EngineMissing(RuntimeError):
    """The typst package is not installed here."""


def available() -> bool:
    try:
        import typst  # noqa: F401
    except ImportError:
        return False
    return True


def _typst():
    try:
        import typst
    except ImportError as error:
        raise EngineMissing(_("The typst library is missing: install the program's requirements")) from error
    return typst


def font_folder() -> Path | None:
    """The fonts the program carries (Titillium Web and Inter, OFL)."""
    return paths.shipped("fonts")


def fonts():
    """The fonts of a compilation: the program's, then those inside Typst for what they lack; the system's never."""
    typst = _typst()
    folder = font_folder()
    return typst.Fonts(include_system_fonts=False, include_embedded_fonts=True,
                       font_paths=[str(folder)] if folder is not None else [])


def image_format(data: bytes) -> str | None:
    """The extension of an image Typst reads, from its first bytes; None for anything else."""
    head = data[:256]
    for ext, magic in LOGO_FORMATS:
        if head.startswith(magic):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if b"<svg" in data[:2048] or head.lstrip().startswith(b"<?xml"):
        return "svg"
    return None


@dataclass
class Result:
    pdf: bytes
    after: dict = field(default_factory=dict)         # attachment's number -> the page (from 1) of its separator
    warnings: list = field(default_factory=list)


class Build:
    """One report's folder: images are added, then compile. A context manager: the folder goes with it."""

    def __init__(self):
        self.folder = tempfile.TemporaryDirectory(prefix="meridiana-report-")
        self.root = Path(self.folder.name)
        self.pdf_path = self.root / "report.pdf"

    def __enter__(self) -> Build:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.folder.cleanup()

    def add(self, name: str, data: bytes) -> None:
        if not SAFE_NAME.match(name):
            raise ValueError(f"not a name for the report's folder: {name!r}")
        (self.root / name).write_bytes(data)

    def usable_image(self, name: str) -> bool:
        """Whether Typst can read the image `name` of the folder: a file of the user (the logo) may be anything."""
        typst = _typst()
        try:
            typst.compile(f'#image("{name}")'.encode(), root=str(self.root), font_paths=fonts())
        except RuntimeError as error:
            log.complain("report image", error)
            return False
        return True

    def compile(self, document: dict) -> Result:
        """The PDF of `document` (compose.py), its pages and where each attachment's separator fell."""
        typst = _typst()
        # the marks of the results are the window's symbols (symbol_shapes.py, without Qt): their tracks go in the data
        document = {**document, "marks": symbol_shapes.report_marks()}
        (self.root / "data.json").write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        main = self.root / "main.typ"
        main.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
        compiler = typst.Compiler(root=str(self.root), font_paths=fonts())
        try:
            pdf, warnings = compiler.compile_with_warnings(str(main), format="pdf")
        except typst.TypstError as error:
            # the whole diagnostic to the log: where in the template, with Typst's hints
            log.complain("report", RuntimeError(getattr(error, "diagnostic", "") or str(error)))
            raise
        for w in warnings:
            log.complain("report", RuntimeError(getattr(w, "message", str(w))))
        separators = json.loads(compiler.query("<meridiana-attachment>", field="value", format="json"))
        self.pdf_path.write_bytes(pdf)
        return Result(pdf, {int(s["k"]): int(s["page"]) for s in separators},
                      [getattr(w, "message", str(w)) for w in warnings])


def self_check() -> tuple[bool, str]:
    """Typst and the fonts here: a short document in both families and the marks of the checks, compiled without the
    system's fonts; for the bundle's self-test."""
    if not available():
        return False, "the typst package is missing"
    typst = _typst()
    with Build() as b:
        src = ('#set text(font: "Titillium Web", lang: "it")\n#table(columns: 2, [Prova °C], '
               '[#text(font: "Inter")[kWh/m²]])').encode()
        pdf = typst.compile(src, root=str(b.root), font_paths=fonts())
    if not pdf.startswith(b"%PDF"):
        return False, "typst wrote something that is not a PDF"
    missing = {"Titillium Web", "Inter"} - set(fonts().families())
    if missing:
        return False, f"fonts not found: {', '.join(sorted(missing))}"
    return True, f"typst, {len(pdf)} bytes"
