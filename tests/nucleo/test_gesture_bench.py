"""Known streams pin down the meaning of the gesture benchmark, without Qt."""
import importlib.util
from pathlib import Path
import sys
import unittest

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))


class Analysis(unittest.TestCase):
    def core(self):
        self.assertIsNotNone(importlib.util.find_spec('gesture_bench_core'), 'analysis module missing')
        import gesture_bench_core
        return gesture_bench_core

    def test_statistics_and_refresh_budgets(self):
        core = self.core()
        result = core.frame_stats([8, 8, 16, 24], 125)
        self.assertEqual(result['median_ms'], 12)
        self.assertAlmostEqual(result['p95_ms'], 22.8)
        self.assertEqual(result['over_1_period'], 2)
        self.assertEqual(result['over_1_5_periods'], 2)
        self.assertEqual(result['over_2_periods'], 1)
        self.assertEqual(result['missed_frames'], 3)
        self.assertEqual(sum(row['count'] for row in result['histogram']), 4)
        self.assertIsNone(core.describe([])['p95_ms'])

    def test_latency_requires_a_frame_showing_the_requested_state(self):
        core = self.core()
        rows = [dict(record='event', t_ns=0, started_ns=0, camera_after={'zoom': 2}),
                dict(record='frame', t_ns=8_000_000, camera={'zoom': 1}),
                dict(record='frame', t_ns=16_000_000, camera={'zoom': 2})]
        result = core.analyze(rows, 120)
        self.assertEqual(result['latency']['median_ms'], 16)
        self.assertEqual(result['latency_unmatched'], 0)
        self.assertEqual(core.analyze(rows[:2], 120)['latency_unmatched'], 1)

    def test_deferred_scroll_reports_a_labeled_state_change_latency(self):
        core = self.core()
        rows = [dict(record='event', t_ns=0, started_ns=0, deferred_state=True, expected_direction=1,
                     camera_before={'contentY': 0}, camera_after={'contentY': 0}),
                dict(record='frame', t_ns=8_000_000, camera={'contentY': 0}),
                dict(record='frame', t_ns=16_000_000, camera={'contentY': 20})]
        result = core.analyze(rows, 120)
        self.assertEqual(result['latency']['median_ms'], 16)
        self.assertEqual(result['latency_estimated'], 1)
        self.assertTrue(result['valid_motion'])

    def test_deferred_scroll_does_not_claim_a_later_inputs_response(self):
        core = self.core()
        rows = [dict(record='event', t_ns=0, deferred_state=True, expected_direction=1,
                     camera_before={'contentY': 0}, camera_after={'contentY': 0}),
                dict(record='event', t_ns=10_000_000, camera_before={'contentY': 0}, camera_after={'contentY': 30}),
                dict(record='frame', t_ns=20_000_000, camera={'contentY': 30})]
        result = core.analyze(rows)
        self.assertEqual(result['latency']['count'], 1)
        self.assertEqual(result['latency_estimated'], 0)
        self.assertEqual(result['latency_unmatched'], 1)

    def test_swap_before_after_frame_end_is_the_same_frame(self):
        core = self.core()
        rows = [dict(record='event', t_ns=0, camera_after={'zoom': 2}),
                dict(record='swap', t_ns=17_000_000),
                dict(record='frame', t_ns=18_000_000, sync_ns=14_000_000, camera={'zoom': 2}),
                dict(record='swap', t_ns=34_000_000)]
        self.assertEqual(core.analyze(rows)['latency']['median_ms'], 17)

    def test_post_gesture_camera_jump_and_pixels(self):
        core = self.core()
        rows = [dict(record='event', t_ns=0, camera_after={'zoom': 1}),
                dict(record='frame', t_ns=1_000_000, camera={'zoom': 1}),
                dict(record='frame', t_ns=20_000_000, camera={'zoom': 1.5})]
        self.assertEqual(core.analyze(rows, 60)['settlement']['camera_changes'], 1)
        self.assertEqual(core.pixel_difference([0, 0, 0, 0], [0, 255, 0, 0])['changed_fraction'], .25)

    def test_trace_v1_and_swaps_share_the_analyzer(self):
        core = self.core()
        rows = [dict(version=1, record='frame', t_ns=1, camera={'zoom': 1}),
                dict(version=1, record='swap', t_ns=2),
                dict(version=1, record='frame', t_ns=10_000_001, camera={'zoom': 1}),
                dict(version=1, record='swap', t_ns=10_000_002)]
        result = core.analyze(rows, 100)
        self.assertEqual(result['frames'], 2)
        self.assertEqual(result['cadence']['median_ms'], 10)
        self.assertIsNone(result['gpu']['median_ms'])

    def test_benchmark_mixed_stream_stays_one_case_when_reanalyzed(self):
        core = self.core()
        rows = [dict(record='session', t_ns=0, version=2, case='mixed-case'),
                dict(record='event', t_ns=1, gesture='move'), dict(record='event', t_ns=2, gesture='wheel')]
        cases = core.trace_cases(rows)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]['id'], 'mixed-case')

    def test_pending_target_is_not_a_rendered_frame(self):
        core = self.core()
        rows = [dict(record='event', t_ns=0, camera_after={'panX': 0, 'panY': 0, 'zoom': 1,
                        'goal': {'x': 0, 'y': 0, 'zoom': 2}}),
                dict(record='frame', t_ns=8_000_000, camera={'panX': 0, 'panY': 0, 'zoom': 1,
                        'goal': {'x': 0, 'y': 0, 'zoom': 2}}),
                dict(record='frame', t_ns=16_000_000, camera={'panX': 0, 'panY': 0, 'zoom': 2})]
        self.assertEqual(core.analyze(rows)['latency']['median_ms'], 16)

    def test_native_qsg_log_distinguishes_gpu_and_gui_phases(self):
        core = self.core()
        self.assertTrue(hasattr(core, 'parse_qsg_message'), 'native Qt timing parser missing')
        self.assertEqual(core.parse_qsg_message('last retrieved GPU frame time was 3.1250 ms'), {'gpu_ms': 3.125})
        result = core.parse_qsg_message('Frame prepared, polish=2 ms, lock=1 ms, blockedForSync=3 ms, animations=4 ms')
        self.assertEqual(result['polish_ms'], 2)
        self.assertEqual(result['animation_ms'], 4)
        self.assertNotIn('gpu_ms', result)

    def test_comparison_attempts_every_pair_when_workers_fail(self):
        import tempfile
        from gesture_bench import compare, parser
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'comparison.json'
            args = parser().parse_args([str(Path(folder)/'missing.meridiana'), '--out', str(out),
                                       '--compare-root', folder, '--seeds', '1', '2', '3'])
            result = compare(args)
            self.assertEqual(len(result['runs']), 6)
            self.assertTrue(all('error' in row for row in result['runs']))
            self.assertEqual(result['comparisons'], [])

    def test_scenario_matrix_finishes_even_when_a_worker_fails(self):
        import json
        import tempfile
        from unittest.mock import patch
        from types import SimpleNamespace
        from gesture_bench import matrix, parser
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'scenarios.json'
            source.write_text(json.dumps([{'modules': 100}, {'modules': 200}]), encoding='utf-8')
            args = parser().parse_args(['--out', str(Path(folder)/'matrix.json'), '--scenarios', str(source)])
            with patch('gesture_bench.subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='', stderr='failed')) as run:
                result = matrix(args)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(len(result['runs']), 2)
            self.assertTrue(all('error' in row for row in result['runs']))

    def test_seeded_sequences_cover_devices_and_momentum(self):
        core = self.core()
        a = core.gesture_steps('random', 23, 120, .4)
        self.assertEqual(a, core.gesture_steps('random', 23, 120, .4))
        self.assertNotEqual(a, core.gesture_steps('random', 24, 120, .4))
        scroll = core.gesture_steps('scroll', 3, 240, .5)
        self.assertIn('momentum', [s.get('phase') for s in scroll])
        self.assertEqual(scroll[-1]['phase'], 'end')
        self.assertTrue(all(b['at_ms'] >= a['at_ms'] for a, b in zip(scroll, scroll[1:], strict=False)))

    def test_bootstrap_and_pairing_do_not_mix_cases(self):
        core = self.core()
        result = core.paired_comparison([10, 20, 30], [20, 40, 60], seed=4)
        self.assertEqual(result['change_pct'], 100)
        self.assertEqual(result['ci95_pct'], [100, 100])
        self.assertTrue(result['regression'])
        self.assertRaises(ValueError, core.paired_comparison, [1], [1, 2])

    def test_comparison_keeps_different_generated_sizes_and_durations_separate(self):
        core = self.core()
        self.assertTrue(hasattr(core, 'scenario_key'), 'scenario comparison key missing')
        case = dict(phase='plant', view='plan', gesture='pinch', modules=100, duration_s=1)
        self.assertNotEqual(core.scenario_key(case), core.scenario_key(case | {'modules': 5000}))
        self.assertNotEqual(core.scenario_key(case), core.scenario_key(case | {'duration_s': 2}))

    def test_project_generator_is_deterministic_and_meets_module_count(self):
        self.assertIsNotNone(importlib.util.find_spec('gesture_projects'), 'project generator missing')
        from gesture_projects import generate
        a, b = generate(100, 3), generate(100, 3)
        self.assertEqual(a.to_json(), b.to_json())
        self.assertEqual(sum(len(a.fill(sf).modules) for sf in a.subfields), 100)
        self.assertTrue(a.exclusions)

    def test_open_manifest_pins_checksums_and_licenses(self):
        self.assertIsNotNone(importlib.util.find_spec('open_ifc'), 'open IFC downloader missing')
        from open_ifc import MODELS
        self.assertEqual(len(MODELS), 2)
        for item in MODELS:
            self.assertEqual(len(item['sha256']), 64)
            self.assertIn('CC BY 4.0', item['attribution'])
            self.assertTrue(item['url'].startswith('https://researchdata.tuwien.ac.at/'))

    def test_synthetic_ifc_is_seeded_and_contains_varied_real_geometry(self):
        self.assertIsNotNone(importlib.util.find_spec('make_test_ifc'), 'synthetic IFC generator missing')
        import tempfile
        import ifcopenshell
        from make_test_ifc import generate as make_ifc
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/'a.ifc', Path(folder)/'b.ifc'
            make_ifc(a, 200_000, 7)
            make_ifc(b, 200_000, 7)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertGreaterEqual(a.stat().st_size, 200_000)
            model = ifcopenshell.open(str(a))
            self.assertEqual(len(model.by_type('IfcProject')), 1)
            for kind in ('IfcWall', 'IfcSlab', 'IfcRoof', 'IfcPipeSegment', 'IfcDuctSegment', 'IfcFurnishingElement', 'IfcCurtainWall'):
                self.assertTrue(model.by_type(kind), kind)
            gids = [e.GlobalId for e in model.by_type('IfcRoot')]
            self.assertEqual(len(gids), len(set(gids)))

    def test_raw_viewer_reference_has_a_valid_anchor_and_a_persistent_mesh(self):
        import tempfile
        import gesture_projects
        from meridiana.app.exchange.ifc_export import frame_of
        self.assertTrue(hasattr(gesture_projects, 'viewer_project'), 'viewer project helper missing')
        with tempfile.TemporaryDirectory() as output, tempfile.TemporaryDirectory() as temporary:
            mesh = Path(temporary)/'geometry.npz'
            mesh.write_bytes(b'synthetic mesh bytes')
            project = gesture_projects.viewer_project({'context': {'mesh': str(mesh), 'triangles': 12}})
            self.assertIsNotNone(frame_of(project)[0])
            target = Path(output)/'viewer.meridiana'
            gesture_projects.preserve_mesh(project, target)
            kept = Path(project.resources['ifc_reference']['context']['mesh'])
            self.assertEqual(kept.read_bytes(), b'synthetic mesh bytes')
            self.assertRaises(FileExistsError, gesture_projects.preserve_mesh, project, target)


if __name__ == '__main__':
    unittest.main()
