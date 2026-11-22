"""Historical files stay immutable while migrations and copies are exercised."""

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = Path(__file__).parent / "riferimenti" / "historical-sha256.json"


def digest(path):
    raw = path.read_bytes()
    if not raw.startswith(b"PK\x03\x04"):
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


class HistoricalFiles(unittest.TestCase):
    def test_frozen_input_bytes_are_unchanged(self):
        wanted = json.loads(REFERENCE.read_text(encoding="utf-8"))
        actual = {p.name: digest(p)
                  for p in sorted((ROOT / "tests/formati/file").iterdir()) if p.is_file()}
        # New versions may add a fixture; existing files must never be rewritten.
        self.assertEqual({name: actual.get(name) for name in wanted}, wanted)
