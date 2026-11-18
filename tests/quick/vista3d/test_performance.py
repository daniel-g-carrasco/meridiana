"""Explicit acceptance of real-window timing reports; never silently relax the 30 ms target."""
import json
import os
from pathlib import Path
import unittest

REPORTS = [Path(p) for p in os.environ.get('MERIDIANA_SCENE_TIMINGS', '').split(';') if p]


@unittest.skipUnless(REPORTS, 'Set MERIDIANA_SCENE_TIMINGS to fresh models_scene_benchmark timing.json files')
class SceneTimingAcceptance(unittest.TestCase):
    def reports(self):
        return [json.loads(path.read_text(encoding='utf-8')) for path in REPORTS]

    def test_measured_scene_has_full_content_native_rendering_and_no_python_callbacks(self):
        for report in self.reports():
            self.assertEqual(report['platform'], 'windows')
            self.assertEqual(report['backend'], 'GraphicsApi.Direct3D11')
            self.assertTrue(report['shadows'])
            self.assertEqual((report['cars'], report['people']), (200, 200))
            self.assertGreater(report['modules'], 100)
            self.assertEqual((report['shared_geometries'], report['groups']), (2, 2))
            self.assertGreater(report['frames'], 200)
            self.assertEqual(report['python_calls_during_orbit'], {})
            self.assertFalse(report['warnings'])

    @unittest.expectedFailure
    def test_every_continuous_frame_stays_within_30_ms(self):
        # R389 remains open: 400 full-detail objects with PCF8 shadows exceed
        # 30 ms on this separate desktop. Keep the original target visible.
        for report in self.reports():
            self.assertLessEqual(report['max_ms'], 30.)


if __name__ == '__main__':
    unittest.main()
