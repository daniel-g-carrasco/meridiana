"""MathML (presentation, as latex2mathml writes it) to OMML (Office Math) with lxml, without Office's XSL sheet (which
cannot be redistributed). It covers what the report's formulas use: identifiers, numbers, operators, subscripts and
superscripts, fractions, roots, sums and integrals with limits, stretchy fences, accents (bar), text, spaces and
simple tables.

    element = omml(mathml_string, inline=False)   # lxml Element m:oMathPara (m:oMath when inline)
"""

from __future__ import annotations

try:
    from lxml import etree
except ImportError:            # without lxml the module still imports: the DOCX export says what is
    etree = None               # missing before it is asked for a formula (editable.require)

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MML = "http://www.w3.org/1998/Math/MathML"
NS = {"m": M, "w": W}
NARY = {"∑": "∑", "∏": "∏", "∫": "∫", "∬": "∬", "∮": "∮", "⋃": "⋃", "⋂": "⋂"}
ACCENTS = {"¯": "¯", "‾": "¯", "^": "̂", "˙": "̇", "→": "⃗", "~": "̃", "̄": "̄"}


def _m(tag: str, parent=None, text: str | None = None):
    e = etree.SubElement(parent, f"{{{M}}}{tag}") if parent is not None else etree.Element(f"{{{M}}}{tag}", nsmap=NS)
    if text is not None:
        e.text = text
    return e


def _local(e) -> str:
    return etree.QName(e).localname if isinstance(e.tag, str) else ""


def _run(parent, text: str, upright: bool = False):
    if text == "":
        return
    r = _m("r", parent)
    if upright:
        rpr = _m("rPr", r)
        _m("sty", rpr).set(f"{{{M}}}val", "p")
    t = _m("t", r, text)
    if text != text.strip() or "  " in text:
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def _text(e) -> str:
    return "".join(e.itertext()).strip()


def _is_fence(e, form: str) -> bool:
    return _local(e) == "mo" and (e.get("fence") == "true" or e.get("stretchy") == "true") and \
        e.get("form", form) == form and _text(e) in "()[]{}|‖⟨⟩⌊⌋⌈⌉"


def _children(e):
    return [c for c in e if isinstance(c.tag, str)]


def convert(e, parent) -> None:
    """Writes into `parent` (an OMML container) the equivalent of the MathML element `e`."""
    tag = _local(e)
    kids = _children(e)
    if tag in ("math", "mstyle", "mpadded", "mphantom", "semantics"):
        if tag == "semantics":
            kids = kids[:1]
        _sequence(kids, parent)
    elif tag == "mrow":
        # stretchy fences: ( ... ) -> m:d
        if len(kids) >= 2 and _is_fence(kids[0], "prefix") and _is_fence(kids[-1], "postfix"):
            d = _m("d", parent)
            dpr = _m("dPr", d)
            _m("begChr", dpr).set(f"{{{M}}}val", _text(kids[0]))
            _m("endChr", dpr).set(f"{{{M}}}val", _text(kids[-1]))
            inner = _m("e", d)
            for c in kids[1:-1]:
                convert(c, inner)
            return
        _sequence(kids, parent)
    elif tag in ("mi", "mn", "mo", "mtext", "ms"):
        text = "".join(e.itertext())
        if tag == "mo":
            text = text.strip() or text
            if e.get("stretchy") == "true" and text in "()[]{}":
                pass
        upright = tag in ("mtext", "mn") or (tag == "mi" and (e.get("mathvariant") == "normal" or len(text) > 1))
        _run(parent, text if tag != "mtext" else " " + text.strip() + " ", upright)
    elif tag == "mspace":
        _run(parent, " ")
    elif tag in ("msub", "msup", "msubsup") and _nary_char(e):
        # \sum_{a}^{b} written as a subscript and a superscript: in OMML it is an operator with limits
        _m("e", _nary(e, parent))
    elif tag in ("msub", "msup", "msubsup"):
        kind = {"msub": "sSub", "msup": "sSup", "msubsup": "sSubSup"}[tag]
        box = _m(kind, parent)
        convert(kids[0], _m("e", box))
        if tag in ("msub", "msubsup"):
            convert(kids[1], _m("sub", box))
        if tag == "msup":
            convert(kids[1], _m("sup", box))
        if tag == "msubsup":
            convert(kids[2], _m("sup", box))
    elif tag == "mfrac":
        f = _m("f", parent)
        if e.get("linethickness") in ("0", "0pt", "0px"):
            fpr = _m("fPr", f)
            _m("type", fpr).set(f"{{{M}}}val", "noBar")
        convert(kids[0], _m("num", f))
        convert(kids[1], _m("den", f))
    elif tag == "msqrt":
        rad = _m("rad", parent)
        rpr = _m("radPr", rad)
        _m("degHide", rpr).set(f"{{{M}}}val", "1")
        _m("deg", rad)
        body = _m("e", rad)
        for c in kids:
            convert(c, body)
    elif tag == "mroot":
        rad = _m("rad", parent)
        convert(kids[1], _m("deg", rad))
        convert(kids[0], _m("e", rad))
    elif tag in ("munder", "mover", "munderover"):
        if _nary_char(e):
            nary = _nary(e, parent)
            _m("e", nary)
            return
        base, scripts = kids[0], kids[1:]
        if tag == "mover" and len(scripts) == 1 and (scripts[0].get("accent") == "true" or _text(scripts[0]) in ACCENTS):
            acc = _m("acc", parent)
            apr = _m("accPr", acc)
            _m("chr", apr).set(f"{{{M}}}val", ACCENTS.get(_text(scripts[0]), _text(scripts[0])))
            convert(base, _m("e", acc))
            return
        if tag == "munderover":
            low = _m("limLow", parent)
            upp = _m("limUpp", _m("e", low))
            convert(base, _m("e", upp))
            convert(scripts[1], _m("lim", upp))
            convert(scripts[0], _m("lim", low))
            return
        lim = _m("limLow" if tag == "munder" else "limUpp", parent)
        convert(base, _m("e", lim))
        convert(scripts[0], _m("lim", lim))
    elif tag == "mfenced":
        d = _m("d", parent)
        dpr = _m("dPr", d)
        _m("begChr", dpr).set(f"{{{M}}}val", e.get("open", "("))
        _m("endChr", dpr).set(f"{{{M}}}val", e.get("close", ")"))
        for c in kids:
            convert(c, _m("e", d))
    elif tag == "menclose":
        bar = _m("bar", parent)
        bpr = _m("barPr", bar)
        _m("pos", bpr).set(f"{{{M}}}val", "top")
        body = _m("e", bar)
        for c in kids:
            convert(c, body)
    elif tag == "mtable":
        mat = _m("m", parent)
        for row in kids:
            mr = _m("mr", mat)
            for cell in _children(row):
                convert(cell, _m("e", mr))
    else:
        for c in kids:
            convert(c, parent)


def _sequence(kids, parent) -> None:
    """The children of a row one after the other; a sum or integral takes what follows it (up to a comma, an equals sign
    or a semicolon) as its operand, inside m:e."""
    i = 0
    while i < len(kids):
        c = kids[i]
        if _local(c) in ("munderover", "munder", "mover", "msub", "msup", "msubsup", "mo") and _nary_char(c):
            nary = _nary(c, parent)
            body = _m("e", nary)
            i += 1
            while i < len(kids) and not (_local(kids[i]) == "mo" and _text(kids[i]) in (",", "=", ";")):
                convert(kids[i], body)
                i += 1
            continue
        convert(c, parent)
        i += 1


def _nary_char(e) -> str:
    tag = _local(e)
    if tag == "mo":
        return NARY.get(_text(e), "")
    if tag in ("munder", "mover", "munderover", "msub", "msup", "msubsup"):
        kids = _children(e)
        return NARY.get(_text(kids[0]), "") if kids and _local(kids[0]) == "mo" else ""
    return ""


def _nary(e, parent):
    nary = _m("nary", parent)
    npr = _m("naryPr", nary)
    _m("chr", npr).set(f"{{{M}}}val", _nary_char(e))
    _m("limLoc", npr).set(f"{{{M}}}val", "undOvr")
    kids = _children(e)
    tag = _local(e)
    sub = _m("sub", nary)
    sup = _m("sup", nary)
    if tag in ("munder", "munderover", "msub", "msubsup") and len(kids) > 1:
        convert(kids[1], sub)
    if tag in ("mover", "msup") and len(kids) > 1:
        convert(kids[1], sup)
    if tag in ("munderover", "msubsup") and len(kids) > 2:
        convert(kids[2], sup)
    # a limit that is not there is hidden, or Word draws an empty box in its place
    if len(sub) == 0:
        _m("subHide", npr).set(f"{{{M}}}val", "1")
    if len(sup) == 0:
        _m("supHide", npr).set(f"{{{M}}}val", "1")
    return nary


def omml(mathml: str, inline: bool = False):
    root = etree.fromstring(mathml.encode("utf-8") if isinstance(mathml, str) else mathml)
    math = _m("oMath")
    convert(root, math)
    if inline:
        return math
    para = _m("oMathPara")
    para.append(math)
    return para


if __name__ == "__main__":
    import sys
    import latex2mathml.converter
    tex = sys.argv[1] if len(sys.argv) > 1 else r"T_c = T_a + \frac{\alpha\,G_{inc}\,(1 - \eta(T_c))}{U_c + U_v\,v}"
    print(etree.tostring(omml(latex2mathml.converter.convert(tex)), pretty_print=True).decode())
