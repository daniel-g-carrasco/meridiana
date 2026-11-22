"""Pre-extraction rule coverage; profile registry contracts are added in step 2."""

import unittest

import _setup  # noqa: F401
from profili.fixtures import fact_cases
from meridiana.core.rules import rules


class LegacyCoverage(unittest.TestCase):
    def test_every_existing_rule_is_active_in_the_frozen_matrix(self):
        active = {r.id for _name, f in fact_cases() for r in rules.applying(f)}
        self.assertEqual(active, {r.id for r in rules.RULES})
        # The baseline has 26 rules: no N17 exists. Do not invent it during extraction.
        self.assertEqual(active, {f"N{i:02d}" for i in range(1, 28)} - {"N17"})
