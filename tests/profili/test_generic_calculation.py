"""The generic profile is a calculation scope, never a national conformity verdict."""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import _setup  # noqa: F401
from meridiana.core.rules import registry
from meridiana.core.model.model import Project
from meridiana.core.energy import consumption, economics, simulate, stringing
from profili.fixtures import module as module_spec, inverter as inverter_spec


class GenericCalculation(unittest.TestCase):
    def test_registries_and_closed_scope(self):
        from meridiana.app.profiles import registry as app
        from meridiana.gui.backend.profiles import registry as gui
        self.assertEqual(registry.ids(), ('it', 'generic'))
        self.assertEqual(registry.ids(), app.ids())
        self.assertEqual(registry.ids(), gui.ids())
        p = registry.get('generic')
        self.assertEqual(p.rules(), ())
        self.assertEqual(p.activities(), [])
        self.assertIsNone(p.minimum(p.facts(Project(regulatory_profile='generic'))))
        self.assertEqual(p.design(p.facts(Project(regulatory_profile='generic'))), 'unknown')
        self.assertEqual((p.auto_level(99999), p.region_of('Lombardia'), p.technical_rule(SimpleNamespace(voltage_v=15000))), ('', '', ''))
        self.assertTrue(all(ref.status == 'reference_only' for ref in p.standards()))
        self.assertEqual(len(p.standards()), 4)
        self.assertEqual(p.fields('building'), ())

    def test_calendar_is_one_band_without_national_dates(self):
        p = Project(regulatory_profile='generic')
        self.assertEqual(registry.effective_timezone(p), 'UTC')
        c = registry.for_project(p).calendar()
        index = simulate._local_index(timezone='UTC')
        self.assertEqual(c.holidays(2026), set())
        self.assertEqual(c.codes, ('ALL',))
        np.testing.assert_array_equal(c.band_of(index, 'Pacific/Auckland'), np.full(len(index), 'ALL'))
        p.site.timezone = 'Pacific/Auckland'
        self.assertEqual(registry.effective_timezone(p), 'Pacific/Auckland')

    def test_consumption_uses_only_declared_data_and_preserves_legacy_values(self):
        load = consumption.build(consumption.Consumption.from_dict({}, profile_id='generic'), profile_id='generic')
        self.assertEqual(load.annual_kwh, 0.0)
        self.assertIn('zero', load.record.steps[-1].inputs[-1].source.label.lower())
        c = consumption.Consumption.from_dict({'annual_kwh': 8760}, profile_id='generic')
        load = consumption.build(c, consumption.Context(1000, 999999), profile_id='generic')
        np.testing.assert_array_equal(load.hourly.to_numpy(), np.ones(8760))
        self.assertEqual(load.by_band(), {'ALL': 8760.0})
        raw = {'bands_kwh': {'F1': 100, 'F2': 200, 'F3': 300},
               'monthly_bands_kwh': [{'F1': m, 'F2': m+1, 'F3': m+2} for m in range(12)]}
        saved = deepcopy(raw)
        c = consumption.Consumption.from_dict(raw, profile_id='generic')
        result = consumption.build(c, profile_id='generic')
        np.testing.assert_allclose([row['ALL'] for row in result.monthly_by_band()], [3*m+3 for m in range(12)], rtol=0, atol=1e-12)
        self.assertEqual(raw, saved)
        self.assertEqual(c.monthly_bands_kwh, saved['monthly_bands_kwh'])

    def test_hourly_curve_is_preserved(self):
        index = consumption._index(profile_id='generic')
        values = np.arange(len(index), dtype=float)
        c = consumption.Consumption.from_dict({'measured': {'start': index[0].isoformat(), 'values': values.tolist()}}, profile_id='generic')
        result = consumption.build(c, profile_id='generic')
        np.testing.assert_array_equal(result.hourly.to_numpy(), values)
        np.testing.assert_array_equal(result.hourly.index.asi8, index.asi8)

    def test_economy_ignores_incentives_and_other_legacy_band_prices(self):
        settings = economics.Settings.from_dict({}, profile_id='generic')
        self.assertEqual((settings.buy_f1, settings.sell, settings.capex_per_kwp, settings.battery_cost_per_kwh), (0, 0, 0, 0))
        values = {'buy_f1': .2, 'sell': .1, 'years': 3, 'degradation': 0., 'escalation': 0., 'community': True,
                  'deduction_pct': 110., 'grant_pct': 40., 'trase': 999., 'pz': 99999., 'buy_f2': 999., 'buy_f3': 999.}
        s = economics.Settings.from_dict(values, profile_id='generic')
        index = consumption._index(profile_id='generic')
        prod, load = pd.Series(np.ones(len(index)), index=index), pd.Series(np.full(len(index), .5), index=index)
        result = economics.evaluate(prod, load, 1., 1., s, profile_id='generic')
        np.testing.assert_array_equal(result.years.incentive, np.zeros(3))
        np.testing.assert_array_equal(result.years.deduction, np.zeros(3))
        np.testing.assert_array_equal(result.years.saving, np.full(3, 876.))
        self.assertEqual((result.kpi['zone'], result.kpi['tip']), ('', 0))
        self.assertNotIn('community', [step.key for step in result.record.steps])
        self.assertEqual(set(result.hourly.band), {'ALL'})

    def test_manual_electrical_checks_have_no_inferred_factors_or_positive_conformity(self):
        m, inv = module_spec(), inverter_spec()
        result = stringing.plan(m, inv, 10, [1, 0], None, 65, profile_id='generic')
        scope = next(c for c in result.checks if c.key == 'generic_scope')
        missing = next(c for c in result.checks if c.key == 'generic_missing_data')
        self.assertFalse(scope.ok)
        self.assertEqual(scope.level, 'info')
        self.assertFalse(missing.ok)
        self.assertFalse(result.ok)
        self.assertFalse(any(c.key.startswith(('selv', 'fuse')) for c in result.checks))
        self.assertIsNone(stringing.ku(m, None, profile_id='generic'))
        self.assertIsNone(stringing.voltage_limit(replace(m, max_system_voltage=None), replace(inv, vdc_max=None), profile_id='generic'))
        explicit = stringing.plan(m, inv, 10, [1, 0], -10, 65, ki=1.1, profile_id='generic')
        self.assertEqual(explicit.uoc_max, 10*m.voc*(1+m.beta_voc/100*(-10-25)))
        self.assertTrue(any(c.key.startswith('imp') for c in explicit.checks))
        self.assertIsNone(stringing.suggest(m, inv, 100, -10, 65, profile_id='generic'))

    def test_missing_record_coefficients_are_not_checked_using_typical_values(self):
        from meridiana.core.energy.components import ModuleSpec
        m = ModuleSpec.from_record({'manufacturer': 'Synthetic', 'model': 'Declared', 'pmax': 400,
                                   'vmp': 30, 'imp': 13, 'voc': 40, 'isc': 14})
        result = stringing.plan(m, inverter_spec(), 10, [1, 0], -10, 65, ki=1.1, profile_id='generic')
        self.assertNotIn('inverter_voltage', [c.key for c in result.checks])
        self.assertIn('generic_missing_data', [c.key for c in result.checks])
        self.assertIn('imp0', [c.key for c in result.checks])

    def test_persistence_switch_and_legacy_data_are_lossless(self):
        p = Project()
        p.rules = {'public': True, 'permit_2027': True}
        p.economics = {'community': True, 'trase': 999, 'deduction_pct': 99}
        original = p.to_json()
        p.regulatory_profile = 'generic'
        restored = Project.from_json(p.to_json())
        self.assertEqual(restored.regulatory_profile, 'generic')
        registry.for_project(restored).facts(restored)
        restored.regulatory_profile = 'it'
        self.assertEqual(restored.to_json(), original)

    def test_scoped_assistant_tools_manual_and_gui(self):
        from meridiana.app.assistant import tools, context, design_rules
        from meridiana.app.profiles import registry as app
        from meridiana.gui.backend.profiles import registry as gui
        from meridiana.gui.backend.properties_schema import build_schema
        p = Project(regulatory_profile='generic')
        host = SimpleNamespace(project=p, rules_facts=lambda: registry.for_project(p).facts(p))
        self.assertNotIn('vvf_activities', [row['name'] for row in tools.specs(profile_id='generic')])
        self.assertTrue(tools.run('vvf_activities', {}, host, tools.State()).error)
        self.assertIn('scope', tools.read_rules(host, tools.State()).content)
        self.assertTrue(tools.read_rules(host, tools.State(), 'N15').error)
        self.assertNotIn('DPR 151', context.system(profile_id='generic'))
        self.assertFalse(any(row['id'].startswith('fire.') for row in design_rules.passages(profile_id='generic')))
        self.assertTrue(all(app.get('generic').manual_section_allowed(*key) is False for key in app.get('generic').national_manual_sections))
        self.assertEqual(gui.get('generic').bill_columns(p), ('ALL',))
        schema = build_schema(SimpleNamespace(project=p), 'site', None)
        self.assertFalse(any(field['id'].startswith('rules.') for section in schema for field in section['fields']))

    def test_fresh_generic_imports_do_not_query_italian_services(self):
        import subprocess, sys
        code = """
from contextlib import ExitStack
from unittest.mock import patch
from meridiana.core.rules import registry
profile = registry.get('it')
def reject(*args, **kwargs): raise AssertionError('Italian service called during generic import or construction')
with ExitStack() as stack:
    for name in ('facts','rules','fire','defaults','calendar','consumption','electrical','economics','text','check_call'):
        stack.enter_context(patch.object(type(profile), name, side_effect=reject))
    from meridiana.core.energy import consumption, economics, stringing
    from meridiana.core.model.model import Project
    p = Project(regulatory_profile='generic')
    Project.from_json(p.to_json())
    consumption.build(consumption.Consumption.from_dict({}, profile_id='generic'), profile_id='generic')
    economics.Settings.from_dict({}, profile_id='generic')
    from meridiana.app.assistant import tools
    tools.specs(profile_id='generic')
"""
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])

    @staticmethod
    def manual_project(profile_id):
        from _fixtures import capannone
        from meridiana.app import jobs
        p = capannone()
        p.regulatory_profile, p.site.timezone = profile_id, 'UTC'
        sf = p.subfields[0]
        sf.filled = True
        p.modules[sf.module].update(manufacturer='Synthetic', model='Declared module', pmax=450.,
                                   vmp=34., imp=13.2, voc=41., isc=14.1, beta_voc=-.27, alpha_isc=.05,
                                   gamma_pmax=-.35, max_system_voltage_v=1500, cells=108)
        p.energy = {'losses': {'use_horizon': False, 'use_near': False}, 't_min': -10.,
                    'inverters': [{'record': {'manufacturer': 'Synthetic', 'model': 'Declared inverter',
                                  'ac_power_nominal_w': 5000., 'dc_voltage_max_v': 1000.,
                                  'mppt_voltage_min_v': 100., 'mppt_voltage_max_v': 900., 'mppt_count': 1,
                                  'dc_current_max_per_mppt_a': [30.], 'dc_isc_max_per_mppt_a': [40.],
                                  'inputs_per_mppt': [2], 'dc_current_max_per_input_a': [20.],
                                  'dc_isc_max_per_input_a': [25.], 'phases': 3}, 'count': 1}]}
        p.consumption, p.economics = {'annual_kwh': 8760.}, {'years': 2}
        results, _keys, _laid = jobs.layout_of(p)
        p.energy['strings'] = {'auto': False, 'runs': [{'inverter': 1, 'mppt': 1,
            'modules': [f'{sf.id}/{module.key}' for module in results[sf.id].modules[:10]]}]}
        return p, results

    def test_generic_pipeline_report_and_assistant_run_with_italian_sentinels(self):
        import tempfile
        from pathlib import Path
        from _fixtures import clear_sky_meteo, write_cache
        from meridiana.app import jobs, pipeline
        from meridiana.app.report.compose import compose
        from meridiana.core.rules import checks, rules
        from meridiana.app.assistant import tools, design_rules
        from meridiana.gui.backend.properties_schema import build_schema
        p, _ = self.manual_project('generic')
        p.rules.update(public=True, permit_2027=True, obligation='new')
        p.economics.update(community=True, trase=999., deduction_pct=110., grant_pct=40.)
        before = deepcopy(p.to_json())
        def reject(*args, **kwargs): raise AssertionError('An Italian operative service was called')
        with tempfile.TemporaryDirectory() as folder:
            write_cache(clear_sky_meteo(p.site.lat, p.site.lon), Path(folder))
            with ExitStack() as stack:
                profile = registry.get('it')
                for name in ('facts','rules','minimum','design','fire','fire_group_items','layout_note','defaults',
                             'calendar','consumption','electrical','economics','text','check_call','rule_call',
                             'activity_call','activity','activities','market_rules','partial_fixed_check'):
                    stack.enter_context(patch.object(type(profile), name, side_effect=reject))
                layouts, _keys, _laid = jobs.layout_of(p)
                result = pipeline.compute(p, layouts, Path(folder), fetch=False)
                self.assertFalse(result.error_sim)
                self.assertGreater(result.sim.energy_kwh, 0)
                self.assertEqual(result.load.profile_id, 'generic')
                facts = rules.facts(p, layouts, result.as_dict())
                items = checks.gather(p, layouts, result.as_dict())
                document = compose(p, {**result.as_dict(), 'results': layouts, 'rules_facts': facts, 'checks': items})
                self.assertIn(registry.get('generic').text('scope'), str(document.document))
                host = SimpleNamespace(project=p, rules_facts=lambda: facts)
                self.assertFalse(tools.read_rules(host, tools.State()).error)
                self.assertNotIn('fire.', str(design_rules.search('subfield', profile_id='generic')))
                build_schema(SimpleNamespace(project=p), 'site', None)
                self.assertEqual(p.to_json(), before)

    def test_it_generic_it_physical_results_and_geometry_are_equal_with_explicit_timezone(self):
        import tempfile
        from pathlib import Path
        from _fixtures import clear_sky_meteo, write_cache
        from meridiana.app import jobs, pipeline
        p, _ = self.manual_project('it')
        results = []
        with tempfile.TemporaryDirectory() as folder:
            write_cache(clear_sky_meteo(p.site.lat, p.site.lon), Path(folder))
            for profile_id in ('it', 'generic', 'it'):
                p.regulatory_profile = profile_id
                layouts, _keys, _laid = jobs.layout_of(p)
                result = pipeline.compute(p, layouts, Path(folder), fetch=False)
                self.assertFalse(result.error_sim)
                self.assertGreater(result.sim.energy_kwh, 0)
                results.append((result, [module.corners for module in layouts[p.subfields[0].id].modules]))
        for candidate in results[1:]:
            np.testing.assert_array_equal(candidate[0].sim.hourly.to_numpy(), results[0][0].sim.hourly.to_numpy())
            np.testing.assert_array_equal(candidate[0].sim.hourly.index.asi8, results[0][0].sim.hourly.index.asi8)
            np.testing.assert_array_equal(candidate[1], results[0][1])
        self.assertEqual(results[0][0].sim.energy_kwh, results[2][0].sim.energy_kwh)

    def test_worked_hour_handles_timezones_without_daylight_saving(self):
        from meridiana.core.energy.worked import hour_text
        text = hour_text(pd.date_range("2001-01-01", periods=24, freq="h", tz="UTC"), 0)
        self.assertIn("UTC+0", text)
        self.assertIn("00:00", text)

    def test_optimizer_checks_skip_unknown_cold_voltage(self):
        from meridiana.core.energy import optimizers, optimizer_strings
        m = module_spec()
        record = {"manufacturer": "SolarEdge", "model": "S500", "rated_input_power_w": 500.,
                  "max_input_voltage_v": 80., "max_input_isc_a": 18., "max_input_current_a": 15.,
                  "max_output_current_a": 15., "modules_per_unit": 1}
        opt = optimizers.Optimizer.from_record(record)
        checks = optimizers.module_checks(m, opt, 1, None, None, profile_id='generic')
        self.assertNotIn('opt_voc', [c.key for c in checks])
        self.assertIn('generic_missing_data', [c.key for c in checks])
        record.update(manufacturer='Tigo', model='TS4-A-O')
        setup = optimizer_strings.setup({'optimizer': record}, {'manufacturer': 'Synthetic', 'model': 'Declared', 'mppt_count': 1})
        self.assertIsNotNone(setup)
        checks = optimizer_strings.module_checks(setup, m, 1, None, profile_id='generic')
        self.assertNotIn('mlpe_voc', [c.key for c in checks])
        self.assertIn('generic_missing_data', [c.key for c in checks])

    def test_national_market_configuration_is_unavailable_while_global_table_is_retained(self):
        from meridiana.core.energy import optimizers
        inv = optimizers.fixed_voltage({'manufacturer': 'SolarEdge', 'model': 'SE33.3K', 'ac_power_nominal_w': 33300., 'phases': 3})
        self.assertIsNotNone(inv)
        record = {'manufacturer': 'SolarEdge', 'model': 'S1200', 'rated_input_power_w': 1200.,
                  'max_input_voltage_v': 125., 'max_input_isc_a': 15., 'max_output_current_a': 20., 'modules_per_unit': 2}
        rules, reason = optimizers.rules_for(optimizers.Optimizer.from_record(record), inv, profile_id='generic')
        self.assertIsNone(rules)
        self.assertTrue(reason)
        record['model'] = 'S1000'
        rules, reason = optimizers.rules_for(optimizers.Optimizer.from_record(record), inv, profile_id='generic')
        self.assertIsNotNone(rules)

    def test_automatic_plant_and_inverter_proposals_are_unavailable(self):
        from meridiana.core.energy import plant, sizing
        p = Project(regulatory_profile='generic')
        self.assertTrue(sizing.choose(p, [], [], 1.1).reason)
        self.assertTrue(sizing.choose_free(p, [], [], 1.1).reason)
        result = plant.proposal(p)
        self.assertFalse(result.search_complete)
        self.assertTrue(result.search_reason)
        self.assertEqual(result.strings, [])

    def test_two_sessions_undo_and_stale_workers_keep_profile_identity(self):
        from meridiana.app.session import ProjectSession
        a, b = ProjectSession(Project()), ProjectSession(Project(regulatory_profile='generic'))
        raw = deepcopy(a.project.to_json())
        year, layout = a.energy_asked(), a.generation
        a.edit('Profile', lambda p: setattr(p, 'regulatory_profile', 'generic'))
        self.assertFalse(a.energy_done(year, {'stale': True}))
        self.assertFalse(a.layout_done(layout, {}, {}))
        self.assertEqual(b.project.regulatory_profile, 'generic')
        a.undo.undo()
        self.assertEqual(a.project.to_json(), raw)
        a.undo.redo()
        self.assertEqual(a.project.regulatory_profile, 'generic')
        self.assertEqual(b.project.regulatory_profile, 'generic')

    def test_editor_aggregates_legacy_bills_preserving_raw_values_and_invalidates_import(self):
        from meridiana.app.session import ProjectSession
        from meridiana.gui.backend.charts_editor import ResultEditor, CurveJob
        _setup.qt_or_skip()
        from pathlib import Path
        p = Project(regulatory_profile='generic', consumption={'monthly_bands_kwh': [{'F1': 10., 'F2': 20., 'F3': 30.}]})
        session = ProjectSession(p)
        editor = ResultEditor(session, 'consumption')
        self.addCleanup(editor.close)
        self.assertEqual(editor.billColumns, ['ALL'])
        self.assertEqual(editor.bills[0], {'F1': 10., 'F2': 20., 'F3': 30., 'ALL': 60.})
        self.assertTrue(editor.setBill(0, 'ALL', 70.))
        self.assertEqual(session.project.consumption['monthly_bands_kwh'][0]['F2'], 20.)
        job = CurveJob(Path('unused.csv'), 'kWh', editor.epoch)
        editor._import, editor._imports = job, {job}
        session.edit('Profile', lambda p: setattr(p, 'regulatory_profile', 'it'))
        editor._curve_done(job, [[0, 1]], '')
        self.assertNotIn('measured', session.project.consumption)
        self.assertEqual(editor.billColumns, ['F1', 'F2', 'F3'])

    def test_catalogue_does_not_substitute_stc_for_unknown_cold_voltage(self):
        from meridiana.app import catalog_compat
        self.assertIsNone(catalog_compat._voc_at_cold({'voc': 40.}, None, profile_id='generic'))
        self.assertEqual(catalog_compat._voc_at_cold({'voc': 40.}, None, profile_id='it'), 40.)

    def test_variant_switch_preserves_project_scope_and_explicit_timezone(self):
        p = Project(regulatory_profile='generic')
        p.site.timezone = 'Pacific/Auckland'
        first = p.variant
        p.add_variant('Synthetic alternative')
        p.switch_variant(first)
        self.assertEqual((p.regulatory_profile, p.site.timezone), ('generic', 'Pacific/Auckland'))

    def test_separate_generic_reference_bank(self):
        import json
        from pathlib import Path
        expected = json.loads((Path(__file__).parent / 'riferimenti/generic/declared.json').read_text(encoding='utf8'))
        p = Project(regulatory_profile=expected['profile_id'])
        policy = registry.for_project(p)
        self.assertEqual(policy.revision, expected['revision'])
        self.assertEqual(registry.effective_timezone(p), expected['timezone'])
        self.assertEqual(list(policy.calendar().codes), expected['bands'])
        self.assertEqual(list(policy.calendar().holidays(2026)), expected['holidays'])
        data = consumption.Consumption.from_dict({'annual_kwh': expected['uniform_annual_kwh']}, profile_id=p.regulatory_profile)
        load = consumption.build(data, profile_id=p.regulatory_profile)
        np.testing.assert_array_equal(load.hourly.to_numpy(), np.full(8760, expected['uniform_hourly_kwh']))
        settings = economics.Settings.from_dict({'buy_f1': expected['purchase_price'], 'sell': expected['sale_price'],
            'years': 1, 'degradation': 0.0, 'escalation': 0.0}, profile_id=p.regulatory_profile)
        result = economics.evaluate(load.hourly, load.hourly / 2, 1., 1., settings, profile_id=p.regulatory_profile)
        self.assertEqual(result.kpi['saving_1'], expected['saving_first_year'])
        self.assertEqual(result.years.incentive.iloc[0], expected['incentive_first_year'])
        self.assertEqual(result.years.deduction.iloc[0], expected['deduction_first_year'])

    def test_catalogue_discards_verdicts_from_previous_profile(self):
        from meridiana.app.session import ProjectSession
        from meridiana.gui.backend.catalog import CatalogBackend
        _setup.qt_or_skip()
        session = ProjectSession(Project())
        with patch('meridiana.gui.backend.catalog.QThreadPool'):
            backend = CatalogBackend(session, records={'modules': []})
            self.addCleanup(backend.dispose)
            old = backend._generation
            session.edit('Profile', lambda p: setattr(p, 'regulatory_profile', 'generic'))
            self.assertGreater(backend._generation, old)
            backend._done(old, ([{'id': 'stale'}], {}, {}), '')
            self.assertEqual(backend._all, [])
            self.assertEqual(backend._profile_id(), 'generic')

    def test_language_changes_text_without_changing_generic_numbers(self):
        from meridiana import i18n
        old = i18n.language()
        results = []
        try:
            for lang in ('it', 'en', 'it'):
                i18n.setup(lang)
                c = consumption.Consumption.from_dict({'annual_kwh': 8760.}, profile_id='generic')
                load = consumption.build(c, profile_id='generic')
                results.append((registry.get('generic').text('scope'), load.hourly.to_numpy()))
        finally:
            i18n.setup(old)
        self.assertNotEqual(results[0][0], results[1][0])
        self.assertEqual(results[0][0], results[2][0])
        for _text, values in results[1:]:
            np.testing.assert_array_equal(values, results[0][1])

    def test_manual_plant_before_weather_has_missing_data_instead_of_design_temperatures(self):
        from meridiana.core.energy import plant
        p, layouts = self.manual_project('generic')
        p.energy.pop('t_min', None)
        result = plant.build(p, layouts)
        self.assertIsNone(result.t_cell_max)
        self.assertIsNone(result.t_min)
        self.assertTrue(result.strings)
        self.assertTrue(all(run.state != 'ok' for run in result.strings))
        self.assertTrue(any(c.key == 'generic_missing_data' for run in result.strings for c in run.plan.checks))

    def test_inferred_national_optimizer_parallel_rule_is_not_a_generic_maker_rule(self):
        from meridiana.core.energy import optimizer_strings
        setup = optimizer_strings.setup({'optimizer': {'manufacturer': 'Sungrow', 'model': 'SP600S',
            'rated_input_power_w': 600., 'modules_per_unit': 1}}, {'manufacturer': 'Sungrow', 'model': 'SG10RT-P2'})
        self.assertIsNotNone(setup)
        items, _settled = optimizer_strings.input_checks(setup, [10, 12], [(0, 0), (0, 0)], profile_id='generic')
        self.assertFalse(any(c.key == 'mlpe_lengths' for c in items))
        self.assertFalse(any('CEI' in c.source for c in items))
        self.assertTrue(any(c.key == 'generic_missing_data' and not c.ok for c in items))

    def test_optimizer_unknown_limits_and_typical_module_data_do_not_become_comparisons(self):
        from meridiana.core.energy import optimizers
        from meridiana.core.energy.components import ModuleSpec
        module = ModuleSpec.from_record({'pmax': 400.})
        optimizer = optimizers.Optimizer.from_record({'manufacturer': 'SolarEdge', 'model': 'S500', 'rated_input_power_w': 500.})
        items = optimizers.module_checks(module, optimizer, 1, -10, None, profile_id='generic')
        self.assertEqual([c.key for c in items if c.key.startswith('opt_')], ['opt_power'])
        self.assertTrue(any(c.key == 'generic_missing_data' and not c.ok for c in items))

    def test_legacy_replacement_values_are_not_marked_as_declared_electrical_inputs(self):
        from meridiana.core.energy.components import ModuleSpec
        partial = ModuleSpec.from_record({'pmax': 400., 'voc': 40., 'isc': 14.})
        self.assertNotIn('voc', partial.declared_inputs)
        zero = ModuleSpec.from_record({'pmax': 400., 'vmp': 30., 'imp': 13., 'voc': 40., 'isc': 14., 'beta_voc': 0.})
        self.assertNotIn('beta_voc', zero.declared_inputs)
        self.assertIsNone(stringing.ku(zero, -10., profile_id='generic'))

    def test_string_plan_cache_separates_profile_revision_and_declared_input_provenance(self):
        from meridiana.core.energy import plant
        from meridiana.core.energy.pedigree import Source
        module = module_spec()
        unit = plant.Unit(1, 0, inverter_spec(), 'Synthetic')
        source = Source('input', 'Synthetic declared conditions')
        cond = plant.Conditions(65., -10., -10., True, source, source)
        with patch.dict(plant._PLANS, clear=True):
            original = plant._plan(module, unit, 1, 10, 1, cond, profile_id='it')
            generic = plant._plan(module, unit, 1, 10, 1, cond, profile_id='generic')
            self.assertTrue(any(c.key == 'generic_scope' for c in generic.checks))
            self.assertIs(plant._plan(module, unit, 1, 10, 1, cond, profile_id='it'), original)
            unknown = replace(module, declared_inputs=frozenset({'pmax'}))
            self.assertIsNot(plant._plan(unknown, unit, 1, 10, 1, cond, profile_id='generic'), generic)
            with patch.dict(registry._PROFILES, generic=replace(registry.get('generic'), revision=2)):
                self.assertIsNot(plant._plan(module, unit, 1, 10, 1, cond, profile_id='generic'), generic)
