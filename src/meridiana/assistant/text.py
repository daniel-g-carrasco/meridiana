"""Meridio's words on the way out: the little Markdown a model writes (bold, italics, code, lists, headings) as the
HTML of the speech bubble, and as plain sentences for his spoken voice, cut where a sentence ends while the answer
is still coming (ui/voice.py reads each one as soon as it is whole). No Qt."""

from __future__ import annotations

import html as _html
import re

INLINE = ((re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"), (re.compile(r"__(.+?)__"), r"<b>\1</b>"),
          (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), r"<i>\1</i>"),
          (re.compile(r"`([^`]+)`"), r"<code>\1</code>"))
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
HEADING = re.compile(r"^\s*#{1,6}\s+")


def _inline(text: str) -> str:
    text = _html.escape(text, quote=False)
    for pattern, replacement in INLINE:
        text = pattern.sub(replacement, text)
    return text


def html(text: str) -> str:
    """The answer as HTML: paragraphs, lists (numbered or not), headings in bold, fenced code as it is."""
    out: list[str] = []
    listing = ""                    # "ul", "ol" or ""
    fenced = False
    code: list[str] = []
    paragraph: list[str] = []

    def close_paragraph() -> None:
        if paragraph:
            out.append("<p>" + "<br>".join(_inline(x) for x in paragraph) + "</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal listing
        if listing:
            out.append(f"</{listing}>")
            listing = ""
    for line in text.replace("\r", "").split("\n"):
        if line.strip().startswith("```"):
            if fenced:
                out.append("<pre>" + _html.escape("\n".join(code), quote=False) + "</pre>")
                code.clear()
            else:
                close_paragraph()
                close_list()
            fenced = not fenced
            continue
        if fenced:
            code.append(line)
            continue
        if not line.strip():
            close_paragraph()
            close_list()
            continue
        bullet = BULLET.match(line)
        if bullet:
            close_paragraph()
            kind = "ol" if bullet.group(0).strip()[0].isdigit() else "ul"
            if listing != kind:
                close_list()
                out.append(f"<{kind}>")
                listing = kind
            out.append(f"<li>{_inline(line[bullet.end():])}</li>")
            continue
        if HEADING.match(line):
            close_paragraph()
            close_list()
            out.append(f"<p><b>{_inline(HEADING.sub('', line))}</b></p>")
            continue
        if listing:
            close_list()
        paragraph.append(line.strip())
    if fenced and code:
        out.append("<pre>" + _html.escape("\n".join(code), quote=False) + "</pre>")
    close_paragraph()
    close_list()
    return "".join(out)


def plain(text: str) -> str:
    """The answer as it is read aloud: no marks of Markdown, no code, the list items as sentences."""
    lines = []
    fenced = False
    for line in text.replace("\r", "").split("\n"):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        line = HEADING.sub("", BULLET.sub("", line))
        line = re.sub(r"[*_`#>|]", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line).strip()
        if line:
            lines.append(line if line[-1] in ".!?:;" else line + ".")
    return " ".join(lines)


END = re.compile(r"(?<=[.!?:;])\s+(?=\S)|\n\s*\n|\n(?=\s*(?:[-*•]|\d+[.)])\s)")


def sentences(buffer: str, final: bool = False) -> tuple[list[str], str]:
    """The whole sentences at the head of `buffer`, and what is left of it (a sentence still being written). With
    `final`, what is left is a sentence too. A number such as «1.043» or «0,5» is not the end of a sentence: the
    cut wants a space after the stop."""
    parts = END.split(buffer)
    done, rest = (parts, "") if final else (parts[:-1], parts[-1])
    said = [plain(p) for p in done]
    return [s for s in said if s.strip(" .")], rest
