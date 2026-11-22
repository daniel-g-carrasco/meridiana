"""Recorded answers of the Quick, where a test once compared them with the Widgets window (r30, phase B).

Until 10/11/2026 these tests asked the Widgets for the expected value and the Quick for the actual one, and they were
green: the Quick gave what the Widgets gave. When the Widgets went, the Quick's answer of that day was recorded here,
one gzipped JSON file per check, beside the test (`<group>/riferimenti/<test module>.<test>.<n>.json.gz`). A test now
compares the Quick with that record, with the tolerances of `differential.compare`.

A record is never rewritten by a normal run. A new check (or one changed on purpose) writes its file only when asked:
    MERIDIANA_RIFERIMENTI=scrivi python -m unittest quick.<group>.<module>
and the new file is reviewed and committed like code.
"""
import gzip
import json
import os
from pathlib import Path

from quick.aiuti.differential import canonical_project, compare, normalized

WRITE = os.environ.get("MERIDIANA_RIFERIMENTI") == "scrivi"


def project(project):
    """A project's snapshot for a record: canonical_project without what a new project gets by itself each time
    (its BIM identity and when it was made), so that a fixture made again compares with the one recorded."""
    data = canonical_project(project)
    data.pop("bim_id", None)
    data.pop("created", None)
    # These records predate explicit project policies. Check their new metadata separately,
    # then compare every legacy field against the immutable format-30 capture.
    # Format 32 adds only an obstacle's base, written when set: a project without one is format 31's.
    # Format 33 adds only the names given to the imported models, written when set.
    if data.get("version") in (31, 32, 33):
        if data.get("regulatory_profile") != "it" or data["site"].get("timezone") not in ("", "Europe/Rome"):
            raise AssertionError("Legacy Quick references require the original Italian policy and timezone")
        if any("base" in e for e in data.get("exclusions") or []):
            raise AssertionError("Legacy Quick references hold no raised obstacle")
        if "model_names" in data:
            raise AssertionError("Legacy Quick references hold no imported model's name")
        data.pop("regulatory_profile")
        data["site"].pop("timezone")
        data["version"] = 30
    return data


def _plain(value):
    return json.loads(json.dumps(normalized(value), allow_nan=False, sort_keys=True))


def check(test, value, *, name=None, relative=1e-9, absolute=1e-9, glyph_paths=(), wrap_paths=()):
    """`value` against its record: the n-th unnamed check of a test method has the n-th record, a named one its
    name. `glyph_paths`: the paths (prefixes, as `$.projected`) of the numbers that come from the drawing of a font,
    in pixels: those are allowed quick/aiuti/caratteri.GLYPH_PX outside Windows, the others keep `absolute`.
    `wrap_paths`: the numbers that follow where a font wraps a text (a line more or less moves them by a line): not
    compared outside Windows, where the record's wrap was DirectWrite's; the test asserts what it can of them."""
    source = Path(__import__(type(test).__module__, fromlist=["_"]).__file__)   # also a module run as __main__
    group = source.parent
    if name is None:
        counts = test.__dict__.setdefault("_recorded", {})
        name = counts[test._testMethodName] = counts.get(test._testMethodName, 0) + 1
    path = group / "riferimenti" / f"{source.stem}.{test._testMethodName}.{name}.json.gz"
    actual = _plain(value)
    if not path.exists():
        if not WRITE:
            test.fail(f"no record {path.name}: MERIDIANA_RIFERIMENTI=scrivi writes it (then review it)")
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(actual, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with path.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
            stream.write(text.encode("utf-8"))
        return actual
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        expected = json.load(stream)
    differences = compare(expected, actual, relative=relative, absolute=absolute)
    if wrap_paths:
        from quick.aiuti.caratteri import GLYPH_PX
        if GLYPH_PX:
            differences = [d for d in differences if not d["path"].startswith(tuple(wrap_paths))]
    if glyph_paths:
        from quick.aiuti.caratteri import glyph
        differences = [d for d in differences
                       if not (d["path"].startswith(tuple(glyph_paths)) and isinstance(d.get("left"), (int, float))
                               and isinstance(d.get("right"), (int, float))
                               and abs(d["left"] - d["right"]) <= glyph(absolute))]
    test.assertEqual(differences, [], f"{path.name}: {differences[:5]}")
    return actual
