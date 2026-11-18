"""The hourly register keeps physical inverter outputs separate and traceable."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import _setup  # noqa: F401
import numpy as np
import pandas as pd
from meridiana.energy import register

setUpModule = _setup.keep_global_state


class InverterRegister(unittest.TestCase):
    def test_free_inverter_names_roundtrip_csv_in_both_languages(self):
        import csv
        from meridiana import i18n
        index = pd.date_range('2025-01-01', periods=2, freq='h', tz='Europe/Rome')
        hourly = pd.DataFrame({'ghi': [0, 900], 'poa': [0, 1000], 'temp_air': [10, 20],
                               'e_kwh': [0, 4]}, index=index)
        for language, separator in (('en', ','), ('it', ';')):
            i18n.setup(language)
            for name in ('Roof, east', 'Inverter; est', '"Quoted"\nroof'):
                with self.subTest(language=language, name=name), tempfile.TemporaryDirectory() as folder:
                    sim = SimpleNamespace(hourly=hourly, inverters=[{
                        'number': 1, 'name': name, 'p_dc': np.array([0, 5000]), 'p_ac': np.array([0, 4000])}])
                    table = register.frame(sim)
                    cols = [c for c in register.columns(table.attrs['inverters']) if c.id in table.columns]
                    lines = register.header('Project', 'Base', 'test', [], cols, rows=len(table))
                    path = Path(folder) / 'register.csv'
                    register.write_csv(path, table, lines)
                    with path.open(encoding='utf-8-sig', newline='') as stream:
                        while True:
                            position = stream.tell()
                            line = stream.readline()
                            if not line.startswith('#'):
                                stream.seek(position)
                                break
                        rows = list(csv.reader(stream, delimiter=separator))
                    self.assertEqual(len(rows), 3)
                    self.assertEqual([len(row) for row in rows], [8, 8, 8])
                    self.assertEqual(rows[0][-2:], [f'1 · {name} DC (kWh)', f'1 · {name} AC (kWh)'])
                    self.assertEqual(float(rows[2][-1].replace(',', '.')), 4)

    def test_each_inverter_has_its_own_hourly_columns_and_csv_header(self):
        index = pd.date_range('2025-01-01', periods=2, freq='h', tz='Europe/Rome')
        hourly = pd.DataFrame({'ghi': [0, 900], 'poa': [0, 1000], 'temp_air': [10, 20],
                               'e_kwh': [0, 6]}, index=index)
        inverters = [{'number': 1, 'name': 'A', 'p_dc': np.array([0, 5000]), 'p_ac': np.array([0, 4000])},
                     {'number': 2, 'name': 'B', 'p_dc': np.array([0, 2200]), 'p_ac': np.array([0, 2000])}]
        table = register.frame(SimpleNamespace(hourly=hourly, inverters=inverters))
        self.assertEqual(table['inverter_1_dc'].tolist(), [0, 5])
        self.assertEqual(table['inverter_2_ac'].tolist(), [0, 2])
        np.testing.assert_allclose(table['inverter_1_ac'] + table['inverter_2_ac'], table.production)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'register.csv'
            register.write_csv(path, table, [])
            text = path.read_text(encoding='utf-8-sig')
            self.assertIn('1 · A', text)
            self.assertIn('2 · B', text)
