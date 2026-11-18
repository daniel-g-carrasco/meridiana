"""Opt-in native consumption resize budget with the actual calculated Rho year."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ResizeBudgetTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MERIDIANA_RHO_YEAR'), 'Needs the local calculated Rho fixture and an idle PC')
    @unittest.expectedFailure
    def test_consumption_right_border_never_blocks_over_30_ms(self):
        # Intermittent after integration: one full run passes, the repeat reaches 30.64 ms.
        # Keep the budget unchanged until it is reliable on the native workbench.
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'resize.json'
            subprocess.run([sys.executable, '-m', 'quick.grafici.resize_consumption',
                            os.environ['MERIDIANA_RHO_YEAR'], str(output)], check=True)
            result = json.loads(output.read_text(encoding='utf8'))
            self.assertFalse(result['warnings'], result['warnings'])
            self.assertEqual(result['hours'], 8760)
            self.assertEqual(len(result['rows']), 6)
            for row in result['rows']:
                self.assertGreater(row['samples'], 200)
                self.assertGreater(row['handle_moved'], 50)
                self.assertLessEqual(row['worst_ms'], 30, row)
