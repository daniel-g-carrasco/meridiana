"""The years kept in the cache after the modules moved to the layers (study 43, risk R1): a year written before the
move (version 1, its classes named by their old modules) is not read, it is computed again; nothing breaks. Since
version 3 (R598) a year is two frames, the near shading of the first pass apart: one of version 2 is computed again,
the year read whole is the one written, and the window's light one is it without that near shading."""

import dataclasses
import gzip
import io
import pickle
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401
from _fixtures import differences

from meridiana.data import frames, year_store


@dataclasses.dataclass
class _Near:
    table: np.ndarray
    keys: list


@dataclasses.dataclass
class _ArrayPass:
    a: str
    g_eff: np.ndarray
    near: object


@dataclasses.dataclass
class _First:
    weights: np.ndarray
    per_array: list


@dataclasses.dataclass
class _Sim:
    energy_kwh: float
    parts: object


def _year():
    per = [_ArrayPass(f"s{i}.0", np.arange(8760, dtype=float) * (i + 1),
                      _Near(np.full((10, 36), 0.25 * i), [("s", str(k)) for k in range(3)])) for i in range(2)]
    return {"sim": _Sim(425352.8506294732, _First(np.array([0.4, 0.6]), per)), "notes": ["n"]}


class AfterTheMove(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.cache = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def put(self, raw: bytes, fingerprint="f"):
        path = year_store.path_of(self.cache, fingerprint)
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wb") as stream:
            stream.write(raw)

    def test_the_version_changed_with_the_frames(self):
        self.assertEqual(year_store.VERSION, 3)

    def test_a_year_of_version_2_is_not_read(self):
        self.put(pickle.dumps(dict(version=2, key="k", energy={}, results={}, layout_keys={})))
        self.assertIsNone(year_store.read(self.cache, "f", "k"))
        self.assertIsNone(year_store.read_light(self.cache, "f"))
        self.assertIsNone(year_store.light_of(year_store.read_light(self.cache, "f"), "k"))

    def test_a_year_of_version_1_is_not_read(self):
        self.put(pickle.dumps(dict(version=1, key="k", energy={}, results={}, layout_keys={})))
        self.assertIsNone(year_store.read(self.cache, "f", "k"))

    def test_a_year_that_names_a_module_no_longer_there_is_not_read(self):
        # protocol 0 by hand: {"version": 2, "key": "k", "results": a class of energy/simulate.py, its path before C1}
        raw = (b"(dp0\nVversion\np1\nI2\nsVkey\np2\nVk\np3\nsVresults\np4\n"
               b"cmeridiana.energy.simulate\nYearResult\np5\ns.")
        self.put(raw)
        self.assertIsNone(year_store.read(self.cache, "f", "k"))

    def test_a_year_written_now_is_read_back(self):
        year_store.write(self.cache, "g", "k", {"a": 1}, {"b": 2}, {})
        self.assertEqual(year_store.read(self.cache, "g", "k")["results"], {"b": 2})

    def test_the_year_read_whole_is_the_one_written_and_the_light_one_lacks_only_the_near_shading(self):
        energy = _year()
        year_store.write(self.cache, "g", "k", energy, {"s0": "layout"}, {"s0": "key"})
        whole = year_store.read(self.cache, "g", "k")
        self.assertEqual(differences(whole["energy"], energy), [])
        self.assertEqual((whole["results"], whole["layout_keys"]), ({"s0": "layout"}, {"s0": "key"}))
        light = year_store.light_of(year_store.read_light(self.cache, "g"), "k")
        self.assertEqual(light["results"], {"s0": "layout"})
        self.assertEqual([ap.near for ap in light["energy"]["sim"].parts.per_array], [None, None])
        self.assertEqual(differences(light["energy"], energy, skip=(".near",)), [])
        self.assertEqual(pickle.dumps(year_store.join(*year_store.split(energy))), pickle.dumps(energy))
        self.assertTrue(all(ap.near is not None for ap in energy["sim"].parts.per_array), "the year given untouched")
        self.assertIsNone(year_store.light_of(year_store.read_light(self.cache, "g"), "other key"))
        self.assertIsNone(year_store.read(self.cache, "g", "other key"))

    def test_corrupt_or_truncated_gzip_is_absent_for_both_readers(self):
        # Stored DEFLATE blocks make the flipped array bit independent of compression.
        first, second = io.BytesIO(), io.BytesIO()
        frames.dump(dict(version=3, key="k", energy={"a": np.ones(4096)}, results={}, layout_keys={}), first)
        frames.dump(np.ones(4096), second)
        a, b = first.getvalue(), second.getvalue()
        raw = gzip.compress(a + b, compresslevel=0)
        cases = {}
        for name, offset in (("first", 15 + len(a) - 20),
                             ("second", 15 + len(a) + len(b) - 20), ("tail", len(raw) - 8)):
            damaged = bytearray(raw)
            damaged[offset] ^= 1
            cases[name] = damaged
        for name, offset in (("half first", 15 + len(a) // 2), ("between", 15 + len(a)),
                             ("half second", 15 + len(a) + len(b) // 2)):
            cases[name] = raw[:offset]
        path = year_store.path_of(self.cache, "f")
        path.parent.mkdir(parents=True, exist_ok=True)
        for name, damaged in cases.items():
            path.write_bytes(damaged)
            for reader in (lambda: year_store.read(self.cache, "f", "k"),
                           lambda: year_store.read_light(self.cache, "f")):
                with self.subTest(damage=name, reader=reader):
                    self.assertTrue(reader() is None, "damaged year accepted")

    def test_a_year_cut_short_is_not_read(self):
        year_store.write(self.cache, "g", "k", _year(), {}, {})
        path = year_store.path_of(self.cache, "g")
        raw = gzip.decompress(path.read_bytes())
        with gzip.open(path, "wb") as stream:
            stream.write(raw[:len(raw) // 2])
        self.assertIsNone(year_store.read(self.cache, "g", "k"))
        self.assertIsNone(year_store.light_of(year_store.read_light(self.cache, "g"), "k"))


class Frames(unittest.TestCase):
    def test_an_object_comes_back_with_its_arrays_on_the_bytes_read_writable_and_equal(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "x.bin"
            obj = {"a": np.linspace(0, 1, 1001), "b": [np.arange(7, dtype=np.int16), "t"], "c": np.zeros((3, 4)).T}
            frames.write(path, obj)
            back = frames.loads(frames.read(path))
        self.assertEqual(differences(back, obj), [])
        self.assertTrue(back["a"].flags.writeable)
        back["a"][0] = 5.0                  # as an array of before: whoever has it may change it
        self.assertEqual(back["a"][0], 5.0)

    def test_what_is_not_a_frame_is_said(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "x.bin"
            path.write_bytes(pickle.dumps({"a": 1}))
            self.assertIsNone(frames.read(path))
        with self.assertRaises(ValueError):
            frames.loads(bytearray(b"not a frame at all"))


if __name__ == "__main__":
    unittest.main()
