"""Embeds fonts in the files: ODT (Fonts/ folder in the zip, svg:font-face-src in styles.xml, manifest) and DOCX
(obfuscated word/fonts/*.odttf, fontTable.xml with embedRegular/embedBold, settings.xml with embedTrueTypeFonts).
Both return how many font files went in; the fonts are the OFL ones of data/fonts/ibm-plex.

    embed_odt(path, {"IBM Plex Sans Light": [(file, "normal", "normal")], "IBM Plex Sans": [(file, "normal", "normal"), (file, "bold", "normal")]})
    embed_docx(path, same)
"""

from __future__ import annotations

import re
import uuid
import zipfile
from pathlib import Path

LOEXT = "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0"


def _rezip(path: Path, changes: dict[str, bytes], extra: dict[str, bytes]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = changes.get(item.filename, zin.read(item.filename))
            if item.filename == "mimetype":
                zout.writestr(item, data, compress_type=zipfile.ZIP_STORED)
            else:
                zout.writestr(item.filename, data)
        present = set(zin.namelist())
        for name, data in changes.items():            # new files (for example word/_rels/fontTable.xml.rels)
            if name not in present:
                zout.writestr(name, data)
        for name, data in extra.items():
            zout.writestr(name, data)
    tmp.replace(path)


def embed_odt(path: Path, fonts: dict[str, list[tuple[Path, str, str]]]) -> int:
    with zipfile.ZipFile(path) as z:
        styles = z.read("styles.xml").decode("utf-8")
        manifest = z.read("META-INF/manifest.xml").decode("utf-8")
    if "xmlns:loext" not in styles:
        styles = styles.replace("<office:document-styles ", f'<office:document-styles xmlns:loext="{LOEXT}" ', 1)
    extra: dict[str, bytes] = {}
    entries = ""
    for family, files in fonts.items():
        src = "<svg:font-face-src>"
        for file, weight, style in files:
            name = f"Fonts/{file.name}"
            extra[name] = file.read_bytes()
            entries += f'<manifest:file-entry manifest:full-path="{name}" manifest:media-type="application/x-font-ttf"/>'
            src += (f'<svg:font-face-uri xlink:href="{name}" xlink:type="simple" loext:font-style="{style}" '
                    f'loext:font-weight="{weight}"><svg:font-face-format svg:string="truetype"/></svg:font-face-uri>')
        src += "</svg:font-face-src>"
        pattern = re.compile(r'<style:font-face style:name="' + re.escape(family) + r'"([^>]*?)/>')
        if pattern.search(styles):
            styles = pattern.sub(lambda m, family=family, src=src: f'<style:font-face style:name="{family}"{m.group(1)}>{src}</style:font-face>', styles, count=1)
        else:
            decl = (f'<style:font-face style:name="{family}" svg:font-family="&apos;{family}&apos;" '
                    f'style:font-family-generic="swiss" style:font-pitch="variable">{src}</style:font-face>')
            if "<office:font-face-decls>" in styles:
                styles = styles.replace("<office:font-face-decls>", "<office:font-face-decls>" + decl, 1)
            elif "<office:font-face-decls/>" in styles:
                styles = styles.replace("<office:font-face-decls/>", "<office:font-face-decls>" + decl + "</office:font-face-decls>", 1)
            else:
                styles = styles.replace("<office:styles>", "<office:font-face-decls>" + decl + "</office:font-face-decls><office:styles>", 1)
    manifest = manifest.replace("</manifest:manifest>", entries + "</manifest:manifest>")
    _rezip(path, {"styles.xml": styles.encode("utf-8"), "META-INF/manifest.xml": manifest.encode("utf-8")}, extra)
    return len(extra)


def _obfuscate(data: bytes, guid: str) -> bytes:
    key = bytes.fromhex(guid.replace("{", "").replace("}", "").replace("-", ""))
    out = bytearray(data)
    for i in range(min(32, len(out))):
        out[i] ^= key[15 - (i % 16)]
    return bytes(out)


def embed_docx(path: Path, fonts: dict[str, list[tuple[Path, str, str]]]) -> int:
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        table = z.read("word/fontTable.xml").decode("utf-8")
        settings = z.read("word/settings.xml").decode("utf-8")
        types = z.read("[Content_Types].xml").decode("utf-8")
        rels = z.read("word/_rels/fontTable.xml.rels").decode("utf-8") if "word/_rels/fontTable.xml.rels" in names else \
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
    if "xmlns:r=" not in table:
        table = table.replace("<w:fonts ", f'<w:fonts xmlns:r="{R}" ', 1)
    extra: dict[str, bytes] = {}
    n = 0
    for family, files in fonts.items():
        parts = ""
        for file, weight, style in files:
            n += 1
            guid = "{" + str(uuid.uuid4()).upper() + "}"
            name = f"word/fonts/font{n}.odttf"
            extra[name] = _obfuscate(file.read_bytes(), guid)
            rid = f"rIdFont{n}"
            rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{R}/font" Target="fonts/font{n}.odttf"/></Relationships>')
            tag = {("normal", "normal"): "embedRegular", ("bold", "normal"): "embedBold",
                   ("normal", "italic"): "embedItalic", ("bold", "italic"): "embedBoldItalic"}[(weight, style)]
            parts += f'<w:{tag} r:id="{rid}" w:fontKey="{guid}"/>'
        pattern = re.compile(r'<w:font w:name="' + re.escape(family) + r'">(.*?)</w:font>', re.S)
        if pattern.search(table):
            table = pattern.sub(lambda m, family=family, parts=parts: f'<w:font w:name="{family}">{m.group(1)}{parts}</w:font>', table, count=1)
        else:
            table = table.replace("</w:fonts>", f'<w:font w:name="{family}"><w:family w:val="swiss"/><w:pitch w:val="variable"/>{parts}</w:font></w:fonts>')
    if "embedTrueTypeFonts" not in settings:
        if "<w:zoom" in settings:
            settings = re.sub(r"(<w:zoom[^>]*/>)", r"\1<w:embedTrueTypeFonts/>", settings, count=1)
        else:
            settings = re.sub(r"(<w:settings[^>]*>)", r"\1<w:embedTrueTypeFonts/>", settings, count=1)
    if 'Extension="odttf"' not in types:
        types = types.replace("</Types>", '<Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/></Types>')
    _rezip(path, {"word/fontTable.xml": table.encode("utf-8"), "word/settings.xml": settings.encode("utf-8"),
                  "[Content_Types].xml": types.encode("utf-8"), "word/_rels/fontTable.xml.rels": rels.encode("utf-8")}, extra)
    return n
