"""Compare semantic outputs and every vector with immutable Italian references."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from profili.snapshot import BANKS, REFERENCE, ROOT
from profili.reference_storage import document, differences, unpack


class ItalianParity(unittest.TestCase):
    pass


def legacy_metadata(value):
    """Project format metadata is checked separately by the format contract tests (31 added the profile and the
    timezone; 32 only an obstacle's base, written when it is not zero; 33 only the names given to the imported
    models, written when set)."""
    if isinstance(value, list):
        return [legacy_metadata(v) for v in value]
    if not isinstance(value, dict):
        return value
    out = {k: legacy_metadata(v) for k, v in value.items()}
    if "ring" in out and "kind" in out and out.get("base") == 0.0:
        out.pop("base")                 # format 32: an exclusion's base, 0 for all of these banks (as before it)
    if out.get("format") == "meridiana-project":
        if out.get("regulatory_profile") != "it" or out.get("version") not in (31, 32, 33):
            raise AssertionError("Legacy banks must remain Italian projects in format 31, 32 or 33")
        if "model_names" in out:
            raise AssertionError("Legacy banks name no imported model")
        if out["site"].get("timezone") not in ("", "Europe/Rome"):
            raise AssertionError("Legacy banks must retain the original timezone")
        out.pop("regulatory_profile", None)
        out["version"] = 30
        out["site"].pop("timezone", None)
    return out


def check_bank(bank, lang):
    def check(self):
        path = REFERENCE / f"{bank}-{lang}.json.gz"
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run([sys.executable, "-m", "profili.worker", bank, lang, folder], cwd=ROOT,
                                  capture_output=True, text=True, encoding="utf-8", timeout=300)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            actual_path = Path(folder) / f"{bank}-{lang}.json"
            actual = json.loads(actual_path.read_text(encoding="utf-8"))
            if "renderer_missing" in actual:
                self.skipTest("Renderer unavailable: " + actual["renderer_missing"])
            expected = unpack(path.read_bytes())
            vectors = {}
            if actual_path.with_suffix(".npz").exists():
                with np.load(actual_path.with_suffix(".npz"), allow_pickle=False) as arrays:
                    vectors = dict(arrays)
            if bank == "persistence":
                # the formats frozen after the bank (32: an obstacle's base) are checked by tests/formati
                actual = {k: v for k, v in actual.items() if not k.startswith("progetto-v")
                          or not k.removeprefix("progetto-v").split(".")[0].isdigit()
                          or int(k.removeprefix("progetto-v").split(".")[0]) <= 31}
            result = document(legacy_metadata(actual), vectors, compact=expected["compact_lists"])
            delta = differences(expected, result)
            if delta:
                saved = Path(tempfile.mkdtemp(prefix=f"meridiana-{bank}-{lang}-"))
                for output in Path(folder).iterdir():
                    shutil.copy2(output, saved / output.name)
                self.fail(f"{bank}/{lang}: reference changed\n" + "\n".join(delta)
                          + f"\nComplete actual JSON/NPZ: {saved}"
                          + f"\nRegenerate in a NEW temporary folder: python -m profili.worker {bank} {lang} <new-folder>")
    return check


for _bank in BANKS:
    for _lang in ("it", "en"):
        setattr(ItalianParity, f"test_{_bank}_{_lang}", check_bank(_bank, _lang))
