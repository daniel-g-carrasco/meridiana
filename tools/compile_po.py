#!/usr/bin/env python3
"""Compile po/*.po into GNU gettext catalogues, with msgfmt (GNU gettext: on Linux, in the Flatpak SDK, in MSYS2)
or, where there is none (Windows with python.org's Python, the Windows runner of the CI), with the compiler below:
the same .mo for what Meridiana's catalogues use (contexts, plurals, the header; fuzzy and untranslated entries left
out, as msgfmt does), and a check of the {placeholders} a translation may not add (a KeyError at run time).

  python3 tools/compile_po.py                 -> locale/<lang>/LC_MESSAGES/<domain>.mo
  python3 tools/compile_po.py --dest /app/share/locale
  python3 tools/compile_po.py --python        the compiler below even when msgfmt is there
  python3 tools/compile_po.py --update        refresh po/<domain>.pot and merge it into po/*.po
  python3 tools/compile_po.py --check         broken encoding, keys twice, placeholders, entries src does not use

--update on Windows: MSYS2's xgettext writes location comments differently
from Linux's, so it rewrites thousands of lines of the .po files; run it on
Linux, or add the new entries to it.po by hand (docs of the template).
"""

import argparse
import ast
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from meridiana import TEXTDOMAIN as DOMAIN  # noqa: E402

PACKAGE = ROOT / "src" / "meridiana"
FIELD = re.compile(r"(?<!\{)\{([^{}!:]*)[^{}]*\}(?!\})")       # {name}, {name:.1f}; not {{ }}


class PoError(ValueError):
    pass


def update() -> None:
    pot = ROOT / "po" / f"{DOMAIN}.pot"
    sources = sorted(p.relative_to(ROOT).as_posix() for p in PACKAGE.rglob("*.py"))
    subprocess.run(["xgettext", "--language=Python", "--keyword=_", "--keyword=ngettext:1,2",
                    "--keyword=pgettext:1c,2", "--keyword=N_", "--from-code=UTF-8", f"--package-name={DOMAIN}",
                    "--add-comments=TRANSLATORS", "--output", str(pot), *sources], cwd=ROOT, check=True)
    for po in sorted((ROOT / "po").glob("*.po")):
        subprocess.run(["msgmerge", "--quiet", "--update", "--backup=none", str(po), str(pot)], check=True)


def parse(text: str, name: str = "po") -> list[dict]:
    """The entries of a .po file: {"msgctxt"?, "msgid", "msgid_plural"?, "msgstr" or "msgstr[n]"..., "fuzzy"};
    obsolete entries (#~) are left out."""
    entries: list[dict] = []
    entry: dict = {}
    key = None

    def close() -> None:
        nonlocal entry, key
        if "msgid" in entry:
            entries.append(entry)
        elif entry.get("msgctxt") is not None or len(entry) > 1:
            raise PoError(f"{name}: an entry without msgid")
        entry, key = {"fuzzy": False}, None

    close()
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.startswith("#,") and "fuzzy" in (f.strip() for f in line[2:].split(",")):
                if "msgid" in entry:
                    close()
                entry["fuzzy"] = True
            elif "msgid" in entry and key is not None and key.startswith("msgstr"):
                close()
            continue
        word, _space, rest = line.partition(" ")
        if line.startswith('"'):
            if key is None:
                raise PoError(f"{name}:{n}: a string outside an entry")
            entry[key] += _string(line, name, n)
            continue
        if word in ("msgctxt", "msgid") and "msgid" in entry and key is not None and key.startswith("msgstr"):
            close()
        if word == "msgctxt" or word == "msgid" or word == "msgid_plural" or re.fullmatch(r"msgstr(\[\d+\])?", word):
            if word in entry:
                raise PoError(f"{name}:{n}: {word} twice in an entry")
            key = word
            entry[key] = _string(rest.strip(), name, n)
            continue
        raise PoError(f"{name}:{n}: what is this? {line[:40]}")
    close()
    return entries


def _string(quoted: str, name: str, n: int) -> str:
    if not (len(quoted) >= 2 and quoted[0] == quoted[-1] == '"'):
        raise PoError(f"{name}:{n}: not a quoted string")
    try:
        return ast.literal_eval(quoted)          # C's escapes are Python's: \n \t \" \\
    except (SyntaxError, ValueError) as error:
        raise PoError(f"{name}:{n}: {error}") from None


def check(entries: list[dict], name: str = "po") -> None:
    """A translation that names a {field} its source does not have would raise KeyError when it is formatted."""
    for e in entries:
        source = set(FIELD.findall(e["msgid"])) | set(FIELD.findall(e.get("msgid_plural", "")))
        for k, v in e.items():
            if k.startswith("msgstr") and v and e["msgid"]:
                extra = set(FIELD.findall(v)) - source
                if extra:
                    raise PoError(f"{name}: «{e['msgid'][:50]}» translated with {sorted(extra)} it does not have")


BROKEN = re.compile(r"[^\W\d_]\?[^\W\d_]|\s\?\s|�|Ã.|â€|Â")     # «un?immagine», «non ? disponibile», mojibake
PRINTF = re.compile(r"%(?:\([A-Za-z_]\w*\))?[sdifr]|%\d")                 # %s, %(name)s, Qt's %1
SOURCES = {".py", ".qml", ".js", ".json", ".txt", ".toml", ".yaml", ".yml", ".csv", ".html"}


def _literals(root: Path) -> tuple[set, str]:
    """Every string written in src: Python's constants (implicit concatenations joined), the QML's and the JSON's
    quoted strings; and the raw text of the files, for what is written another way."""
    found, raw = set(), []
    for p in sorted((root / "src").rglob("*")):
        if not p.is_file() or p.suffix.lower() not in SOURCES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        raw.append(text)
        if p.suffix == ".py":
            try:
                found.update(n.value for n in ast.walk(ast.parse(text))
                             if isinstance(n, ast.Constant) and isinstance(n.value, str))
            except SyntaxError:
                pass
            continue
        for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'', text):
            s = m.group(1) if m.group(1) is not None else m.group(2)
            if "\\" in s:
                try:
                    s = s.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
                except UnicodeError:
                    pass
            found.add(s)
    return found, "\n".join(raw)


def problems(po: Path, used: tuple[set, str] | None = None) -> list[str]:
    """What --check refuses in one catalogue: broken encoding, keys twice, placeholders that differ between msgid
    and msgstr, entries no line of src asks for (used: the literals of src, _literals(ROOT))."""
    name = po.relative_to(ROOT).as_posix() if po.is_relative_to(ROOT) else po.name
    try:
        text = po.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        return [f"{name}: not UTF-8 ({error})"]
    try:
        entries = parse(text, name)
    except PoError as error:
        return [str(error)]
    out, seen = [], set()
    for e in entries:
        msgid, label = e["msgid"], e["msgid"][:60].replace("\n", " ")
        key = (e.get("msgctxt"), msgid)
        if key in seen:
            out.append(f"{name}: key twice: {key[0] or ''}|{label}")
        seen.add(key)
        if not msgid:
            continue
        forms = {k: v for k, v in e.items() if k.startswith("msgstr") and v}
        source = msgid + e.get("msgid_plural", "")
        for k, v in forms.items():
            if BROKEN.search(v) and not BROKEN.search(source):
                out.append(f"{name}: broken encoding in «{label}»: {v[:60]}")
            mine, theirs = set(FIELD.findall(source)), set(FIELD.findall(v))
            pm, pt = sorted(PRINTF.findall(source)), sorted(PRINTF.findall(v))
            if "msgid_plural" in e:
                bad = not theirs <= mine or not set(pt) <= set(pm)
            else:
                bad = mine != theirs or pm != pt
            if bad:
                out.append(f"{name}: placeholders differ in «{label}»: {sorted(mine | set(pm))} / {sorted(theirs | set(pt))}")
        if used is not None and msgid not in used[0] and msgid not in used[1]:
            out.append(f"{name}: no line of src uses «{label}»")
    return out


def check_all(root: Path = ROOT) -> list[str]:
    """--check on every catalogue: one catalogue per language, directly in po/."""
    used = _literals(root)
    out = [f"{p.relative_to(root).as_posix()}: a second catalogue; its entries go in po/{p.name}"
           for p in sorted((root / "po").rglob("*.po")) if p.parent != root / "po"]
    for po in sorted((root / "po").glob("*.po")):
        out += problems(po, used)
    return out


def mo(entries: list[dict]) -> bytes:
    """The catalogue as GNU's .mo (little endian, no hash table: gettext reads it so)."""
    table = {}
    for e in entries:
        if e["fuzzy"] and e["msgid"]:
            continue
        key = e["msgid"] if "msgctxt" not in e else e["msgctxt"] + "\x04" + e["msgid"]
        if "msgid_plural" in e:
            forms = [e[k] for k in sorted((k for k in e if k.startswith("msgstr[")), key=lambda k: int(k[7:-1]))]
            if not any(forms):
                continue
            table[key + "\x00" + e["msgid_plural"]] = "\x00".join(forms)
        elif e.get("msgstr"):
            table[key] = e["msgstr"]
    if "" in table:                     # as msgfmt: the header without the date of the template (a build repeatable)
        table[""] = "".join(line for line in table[""].splitlines(keepends=True)
                            if not line.startswith("POT-Creation-Date:"))
    keys = sorted(table, key=lambda k: k.encode("utf-8"))
    ids = [k.encode("utf-8") for k in keys]
    strs = [table[k].encode("utf-8") for k in keys]
    n = len(keys)
    start = 7 * 4 + 16 * n
    offsets, blob = [], b""
    for data in ids + strs:
        offsets.append((len(data), start + len(blob)))
        blob += data + b"\x00"
    header = struct.pack("<7I", 0x950412DE, 0, n, 7 * 4, 7 * 4 + 8 * n, 0, start)
    return header + b"".join(struct.pack("<2I", *o) for o in offsets) + blob


def compile_python(po: Path, out: Path) -> None:
    entries = parse(po.read_text(encoding="utf-8"), po.name)
    check(entries, po.name)
    out.write_bytes(mo(entries))


def compile_all(dest: Path, python: bool = False) -> list[Path]:
    msgfmt = None if python else shutil.which("msgfmt")
    written = []
    for po in sorted((ROOT / "po").glob("*.po")):
        out = dest / po.stem / "LC_MESSAGES" / f"{DOMAIN}.mo"
        out.parent.mkdir(parents=True, exist_ok=True)
        if msgfmt:
            subprocess.run([msgfmt, "--check", "--output-file", str(out), str(po)], check=True)
        else:
            compile_python(po, out)
        written.append(out)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, default=ROOT / "locale")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--python", action="store_true", help="the compiler of this file, not msgfmt")
    parser.add_argument("--check", action="store_true",
                        help="refuse broken encoding, keys twice, placeholders that differ, entries src does not use")
    args = parser.parse_args()
    if args.check:
        found = check_all()
        print("\n".join(found) or "po: every catalogue is in order")
        return 1 if found else 0
    if args.update:
        update()
    for out in compile_all(args.dest, args.python):
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
