"""The tolerant reader of PVsyst's text format: one item per line, nested objects, lists, typed records,
groups and circuit nodes, each closed by its own marker. The indentation is not reliable (PVsyst writes some
keys of its 3D objects two columns to the left), so the tree is built from the markers alone, with a stack;
anomalies (a closer without its opener, an object never closed) are noted with their line and do not stop
the reading. Values stay text: the readers of project.py convert them, key by key, as PVsyst's units want.

Markers (docs/studio/10-pvsyst-formati-file.md, 2.2):
- object      PVObject_=<type> | PVObject_<role>=<type>   ...  End of PVObject <type>
- list        <Name>, list of=<n> <TItem>                  ...  End of <Name> | End of (the) List <Name>
- counted     <Name>, Count=<n>                            ...  End of <Name>
- record      <Key>=T<Type> (with deeper lines)            ...  End of T<Type> | EndTags
- group       <Key>=Start                                  ...  <Key>=End | EndTags
- circuit     <Node> Start;                                ...  <Node> End;
- variable    VarSimul_<i>=<name>                          ...  End of VarSimul=vi<name> ("End of Data" inside)
- list item   <Item>=<i> inside a list, deeper lines below ...  EndTags | End of T<Item>
Long values are split on <Key>_contd= lines and joined here."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# closers PVsyst writes that do not name what they close
IRREGULAR = {"TInterpolenD": "TInterpole2D", "TSimulFich": "pvSimulFile", "TOrientGroup": "pvOrient",
             "TAgeing": "pvAgeing"}
_LIST = re.compile(r"^(?P<name>[^,=]+), list of=(?P<n>\d+)\s*(?P<item>\S*)$")
_COUNT = re.compile(r"^(?P<name>[^,=]+), Count=(?P<n>\d+)$")
_NODE = re.compile(r"^(?P<name>.+?) (?P<what>Start|End);$")
_RECORD = re.compile(r"^T[A-Z]\w*$")
_VAR = re.compile(r"^VarSimul_\d+$")


@dataclass
class Node:
    kind: str                   # "root", "object", "list", "count", "record", "group", "circuit", "var"
    name: str                   # the role, key or list name ("" for an anonymous object)
    type: str = ""              # pvSite, TCubicProfile, TShdObject...
    attrs: list = field(default_factory=list)          # (key, value) in the file's order
    children: list = field(default_factory=list)
    line: int = 0

    def get(self, key: str, default=None):
        for k, v in self.attrs:
            if k == key:
                return v
        return default

    def all(self, key: str) -> list[str]:
        return [v for k, v in self.attrs if k == key]

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def find(self, *, type: str | None = None, name: str | None = None) -> Node | None:
        return next((n for n in self.walk() if n is not self and (type is None or n.type == type)
                     and (name is None or n.name == name)), None)

    def findall(self, *, type: str | None = None, name: str | None = None) -> list[Node]:
        return [n for n in self.walk() if n is not self and (type is None or n.type == type)
                and (name is None or n.name == name)]


@dataclass
class Document:
    root: Node
    anomalies: list = field(default_factory=list)      # (line, text)
    encoding: str = "utf-8"

    @property
    def top(self) -> Node | None:
        """The file's own object (pvProject, pvVCalcul, pvSite, pvMeteo...)."""
        return next((c for c in self.root.children if c.kind == "object"), None)


class FormatError(ValueError):
    pass


def decode(data: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1"), "latin-1"


def read(path: Path) -> Document:
    """Read a PVsyst file. Files before 6.40 are binary and refused."""
    data = Path(path).read_bytes()
    text, enc = decode(data)
    head = text.lstrip()[:64]
    if not head.startswith("PVObject_"):
        raise FormatError(f"{Path(path).name}: not a PVsyst text file (PVsyst wrote binary files up to 6.39)")
    doc = parse(text)
    doc.encoding = enc
    return doc


def parse(text: str) -> Document:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    root = Node("root", "", line=0)
    stack = [root]
    anomalies = []
    indents = [len(x) - len(x.lstrip(" ")) for x in lines]

    def open_(node):
        stack[-1].children.append(node)
        stack.append(node)

    def close(pred, what, number):
        for i in range(len(stack) - 1, 0, -1):
            if pred(stack[i]):
                if i != len(stack) - 1:
                    anomalies.append((number, f"{what} closes {len(stack) - 1 - i} element(s) left open"))
                del stack[i:]
                return True
        anomalies.append((number, f"{what} without its opener"))
        return False

    last_key = None
    for n, raw in enumerate(lines, start=1):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("PVObject_") and "=" in s:
            role, _sep, typ = s.partition("=")
            open_(Node("object", role[len("PVObject_"):], typ.strip(), line=n))
            last_key = None
            continue
        if s.startswith("End of PVObject "):
            typ = s[len("End of PVObject "):].strip()
            close(lambda x, t=typ: x.kind == "object" and x.type == t, s, n)
            continue
        if s == "EndTags":
            close(lambda x: x.kind in ("record", "group"), s, n)
            continue
        m = _NODE.match(s)
        if m and "=" not in s:
            if m["what"] == "Start":
                open_(Node("circuit", m["name"], line=n))
            else:
                close(lambda x, nm=m["name"]: x.kind == "circuit" and x.name == nm, s, n)
            continue
        if s == "End of Data":
            continue                                  # the end of a variable's records, inside it
        if s.startswith("End of VarSimul="):
            close(lambda x: x.kind == "var" or x.type == "TVarSimul", s, n)
            continue
        if s.startswith("End of "):
            what = s[len("End of "):].strip().partition("=")[0].strip()
            for prefix in ("the List ", "List "):
                if what.startswith(prefix):
                    what = what[len(prefix):]
            target = IRREGULAR.get(what, what)
            close(lambda x, w=what, t=target: x.name == w or x.type == t or x.type == w, s, n)
            continue
        m = _LIST.match(s)
        if m:
            open_(Node("list", m["name"].strip(), m["item"], line=n))
            continue
        m = _COUNT.match(s)
        if m:
            open_(Node("count", m["name"].strip(), line=n))
            continue
        key, sep, value = s.partition("=")
        if not sep:
            stack[-1].attrs.append((s, ""))          # an empty remark that lost its "="
            continue
        key, value = key.strip(), value.strip()
        if value == "Start":
            open_(Node("group", key, line=n))
            continue
        if value == "End":
            close(lambda x, k=key: x.kind == "group" and x.name == k, s, n)
            continue
        if _VAR.match(key):
            open_(Node("var", key, value, line=n))
            last_key = None
            continue
        if stack[-1].kind == "list" and value.isdigit() and _deeper(lines, indents, n):
            open_(Node("record", key, "T" + key[:1].upper() + key[1:], line=n))
            last_key = None
            continue
        if key.endswith("_contd") and last_key == key[: -len("_contd")]:
            k, v = stack[-1].attrs[-1]
            stack[-1].attrs[-1] = (k, _join(v, value))
            continue
        if _RECORD.match(value) and _deeper(lines, indents, n, empty_ok=True):
            # a typed record when deeper lines follow it (or EndTags at once); else a value that starts with T
            open_(Node("record", key, value, line=n))
            last_key = None
            continue
        stack[-1].attrs.append((key, value))
        last_key = key
    for left in stack[1:]:
        anomalies.append((left.line, f"{left.kind} {left.name or left.type} never closed"))
    return Document(root, anomalies)


def _deeper(lines, indents, n: int, empty_ok: bool = False) -> bool:
    """Whether the next line that is not empty is indented deeper than line n (1-based)."""
    following = next((j for j in range(n, len(lines)) if lines[j].strip()), None)
    if following is None:
        return False
    return indents[following] > indents[n - 1] or (empty_ok and lines[following].strip() == "EndTags")


def _join(first: str, more: str) -> str:
    for mark in ("+contd+", "contd,", "contd"):
        if first.endswith(mark):
            first = first[: -len(mark)]
            break
    return first + more


def numbers(value: str | None) -> list[float]:
    """A comma list of numbers (PVsyst ends it with a comma); the unit some values carry is dropped."""
    if not value:
        return []
    out = []
    for part in value.split(","):
        part = part.strip().split(" ")[0]
        if part:
            try:
                out.append(float(part))
            except ValueError:
                continue
    return out


def number(value: str | None, default: float | None = None) -> float | None:
    got = numbers(value)
    return got[0] if got else default
