"""The lightweight representation must detect changes outside its readable samples."""

import unittest

import numpy as np

from profili import reference_storage as storage


class ReferenceStorage(unittest.TestCase):
    def test_middle_of_long_list_is_checked(self):
        expected = {"hourly": list(range(8760))}
        actual = {"hourly": list(range(8760))}
        actual["hourly"][4000] += 1
        before = storage.document(expected, {}, compact=True)
        after = storage.document(actual, {}, compact=True)
        self.assertNotEqual(before, after)
        self.assertIn("$/data/hourly/$snapshot_list/sha256", storage.differences(before, after)[0])

    def test_array_middle_dtype_and_shape_are_checked(self):
        original = np.arange(8760, dtype=np.float64)
        changed = original.copy()
        changed[4000] += 0.01
        before = storage.document({}, {"hourly": original})
        for array in (changed, original.astype(np.float32), original.reshape(24, 365)):
            with self.subTest(dtype=array.dtype, shape=array.shape):
                self.assertNotEqual(before, storage.document({}, {"hourly": array}))

    def test_text_order_and_tariff_are_checked(self):
        before = storage.document({"text": "Check", "tariff": 0.3, "order": [1, 2]}, {})
        for key, value in (("text", "Changed"), ("tariff", 0.31), ("order", [2, 1])):
            actual = {"text": "Check", "tariff": 0.3, "order": [1, 2], key: value}
            after = storage.document(actual, {})
            self.assertIn(f"$/data/{key}", storage.differences(before, after)[0])

    def test_gzip_is_deterministic_and_roundtrips(self):
        value = storage.document({"z": "Text", "a": [1, 2]}, {})
        first = storage.pack(value)
        self.assertEqual(first, storage.pack(value))
        self.assertEqual(first[4:8], bytes(4))
        self.assertEqual(first[9], 255)  # Stable gzip OS byte on Windows and Linux.
        self.assertEqual(storage.unpack(first), value)

    def test_no_list_order_or_numeric_value_is_discarded(self):
        original = [float(n) for n in range(100)]
        before = storage.document(original, {}, compact=True)
        for actual in (original[::-1], original[:-1], original[:50] + [50.01] + original[51:]):
            self.assertNotEqual(before, storage.document(actual, {}, compact=True))

    def test_sources_in_the_middle_of_hashed_lists_remain_available_to_inventory(self):
        values = [{} for _ in range(100)]
        values[50] = {"source": "Frozen source", "reference": "Frozen reference"}
        result = storage.document(values, {}, compact=True)
        self.assertEqual(result["source_fields"], [{"reference": "Frozen reference"}, {"source": "Frozen source"}])
