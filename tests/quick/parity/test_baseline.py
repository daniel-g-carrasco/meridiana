"""R389: the checked-in native reference must be complete and internally sound."""
import gzip
import hashlib
import json
import unittest

import _setup


class BaselineTest(unittest.TestCase):
    def test_all_native_matrix_cases_states_and_widget_schemas_are_present(self):
        from tools.quick_rif import RHO, capture_matrix, state_names
        root = _setup.ROOT / 'docs/quick/compat/riferimento/baseline-v1'
        expected_states = set(state_names())
        expected_hash = hashlib.sha256(RHO.read_bytes()).hexdigest()
        self.assertEqual(expected_hash, '40d342e81e6314ee5462aa181b6947a218372186dbe7b23013a11cd12005ec13')
        for case in capture_matrix():
            name = f'{case["fixture"]}-{case["theme"]}-s{case["scale"]}-{case["size"][0]}x{case["size"][1]}'
            with self.subTest(case=name):
                folder = root / name
                manifest = json.loads(gzip.decompress((folder / 'manifest.json.gz').read_bytes()))
                self.assertEqual({r['state'] for r in manifest['captures']}, expected_states)
                self.assertEqual(len(manifest['captures']), len(expected_states))
                self.assertEqual(manifest['platform'], 'windows')
                self.assertEqual(manifest['graphics_api'], 'Direct3D11')
                self.assertFalse(manifest['offscreen'])
                for state in expected_states:
                    snap = json.loads(gzip.decompress((folder / f'{state}.json.gz').read_bytes()))
                    self.assertEqual(snap['schema'], 1)
                    meta = snap['meta']
                    self.assertEqual(meta['size'], case['size'])
                    self.assertEqual(meta['scale'], case['scale'])
                    self.assertEqual(meta['device_pixel_ratio'], case['scale'])
                    self.assertEqual(meta['theme'], case['theme'])
                    self.assertEqual(meta['fixture'], case['fixture'])
                    self.assertEqual(meta['state'], state)
                    self.assertEqual(meta['language'], 'it')
                    self.assertEqual(len(meta['png_sha256']), 64)
                    self.assertGreater(len(snap['widgets']), 20)
                    self.assertEqual(len({w['id'] for w in snap['widgets']}), len(snap['widgets']))
                    for row in snap['widgets']:
                        self.assertEqual(len(row['rect']), 4)
                        self.assertEqual(len(row['margins']), 4)
                        self.assertTrue(row['font']['family'], (name, state, row['id']))
                        self.assertIn('WindowText', row['colors'])
                    if case['fixture'] == 'rho':
                        self.assertEqual(meta['source']['sha256'], expected_hash)
                        self.assertTrue(meta['year_computed'])
                        self.assertGreater(meta['module_count'], 0)
                        self.assertEqual(meta['inverters'], 7)
                        self.assertEqual(meta['strings'], 57)

    def test_supplementary_full_charts_are_explicitly_distinct_from_original_rho(self):
        from tools.quick_rif import capture_matrix
        root = _setup.ROOT / 'docs/quick/compat/riferimento/popolati-v1'
        states = {'phase-consumption', 'phase-economics', 'plant-storage'}
        for case in capture_matrix():
            if case['fixture'] != 'rho':
                continue
            name = f'rho-{case["theme"]}-s{case["scale"]}-{case["size"][0]}x{case["size"][1]}'
            with self.subTest(case=name):
                folder = root / name
                manifest = json.loads(gzip.decompress((folder / 'manifest.json.gz').read_bytes()))
                self.assertEqual({r['state'] for r in manifest['captures']}, states)
                edits = manifest['source']['fixture_edits']
                self.assertEqual(edits['consumption']['annual_kwh'], 400000.)
                self.assertEqual(edits['economics']['capex_total'], 450000.)
                self.assertEqual(edits['economics']['battery']['usable_energy_kwh'], 200.)
                for state in states:
                    snapshot = json.loads(gzip.decompress((folder / f'{state}.json.gz').read_bytes()))
                    self.assertTrue(snapshot['meta']['year_computed'])
                    self.assertEqual(snapshot['meta']['device_pixel_ratio'], case['scale'])
                    self.assertEqual(snapshot['meta']['size'], case['size'])

    def test_rho_string_diagram_is_visible_in_every_corrected_reference(self):
        from tools.quick_rif import capture_matrix
        root = _setup.ROOT / 'docs/quick/compat/riferimento/stringhe-v3'
        for case in capture_matrix():
            if case['fixture'] != 'rho':
                continue
            name = f'rho-{case["theme"]}-s{case["scale"]}-{case["size"][0]}x{case["size"][1]}'
            with self.subTest(case=name):
                snapshot = json.loads(gzip.decompress((root / name / 'plant-strings.json.gz').read_bytes()))
                self.assertTrue(snapshot['meta']['year_computed'])
                self.assertEqual(snapshot['meta']['strings'], 57)
                self.assertTrue(any(row['class'] == 'MiniDiagram' for row in snapshot['widgets']))
                self.assertEqual(snapshot['meta']['device_pixel_ratio'], case['scale'])
