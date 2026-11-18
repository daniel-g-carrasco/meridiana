"""R415, R416, R421 and the market filter in the Quick catalogue, with the real data where it decides."""
import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtTest import QSignalSpy

from quick.impianto.catalog_fixtures import module, required_values, settle
from meridiana import catalog
from meridiana.catalog import compat, schema
from meridiana.i18n import number
from meridiana.quick.backend.catalog import CatalogBackend


class Real(unittest.TestCase):
    def make(self, kind='modules', **kwargs):
        backend = CatalogBackend(**kwargs)
        settle(backend)
        if kind != 'modules':
            backend.setKind(kind)
            settle(backend)
        self.addCleanup(backend.deleteLater)
        return backend

    def test_each_class_has_its_own_values_never_scaled(self):
        rows = {r['model']: r for r in catalog.search('modules', manufacturer='Jinko Solar', source='curated', limit=None)}
        # JKM460-485N-48QL6-DV-F4-EU, the table of the sheet
        self.assertEqual((rows['JKM475N-48QL6-DV']['vmp'], rows['JKM475N-48QL6-DV']['imp']), (31.11, 15.27))
        self.assertEqual((rows['JKM460N-48QL6-DV']['vmp'], rows['JKM460N-48QL6-DV']['isc']), (30.57, 15.72))
        self.assertEqual((rows['JKM485N-48QL6-DV']['voc'], rows['JKM485N-48QL6-DV']['efficiency_pct']), (36.92, 24.27))
        self.assertEqual(rows['JKM485N-48QL6-DV']['pmax'], 485)

    def test_the_row_as_written_keeps_its_id_and_values(self):
        row = next(r for r in catalog.load('modules') if r['id'] == 'cur:Jinko Solar:JKM475N-48QL6-DB')
        self.assertEqual((row['pmax'], row['vmp'], row['imp'], row['voc'], row['isc']), (475, 31.13, 15.26, 36.44, 15.85))
        self.assertFalse(row.get('class_of'))

    def test_one_row_per_family_opens_on_its_classes_and_the_central_one_is_chosen(self):
        backend = self.make()
        backend.setFilter('manufacturer', 'Jinko Solar')
        settle(backend)
        rows = backend.model.rows
        head = next(n for n, r in enumerate(rows) if r.get('family_row') and 'DV' in r['model'] and '48QL6' in r['model'])
        self.assertEqual(rows[head]['model'], 'JKM460-485N-48QL6-DV')
        self.assertEqual(rows[head]['range'], (460.0, 485.0))
        backend.select(head, False)
        self.assertEqual(backend.selectedRecord['pmax'], 475)  # the upper of the two in the middle of six
        backend.toggleFamily(head)
        settle(backend)
        members = [r for r in backend.model.rows if r.get('member_of') and '48QL6-DV' in r['model']]
        self.assertEqual([r['pmax'] for r in members], [460, 465, 470, 475, 480, 485])
        chosen = QSignalSpy(backend.chosen)
        at = backend.model.index_of('cur:Jinko Solar:JKM480N-48QL6-DV')
        backend.select(at, False)
        backend.choose()
        self.assertEqual(chosen.count(), 1)
        self.assertEqual(chosen.at(0)[1]['model'], 'JKM480N-48QL6-DV')
        self.assertEqual(chosen.at(0)[1]['vmp'], 31.30)

    def test_the_search_still_finds_the_exact_model(self):
        backend = self.make()
        backend.setFilter('text', 'JKM480N-48QL6-DV')
        settle(backend)
        self.assertEqual([r['model'] for r in backend.model.rows], ['JKM480N-48QL6-DV'])
        self.assertEqual(backend.selectedRecord['model'], 'JKM480N-48QL6-DV')

    def test_a_class_without_values_cannot_be_chosen_and_says_why(self):
        base = module(0, id='cur:Example:P470', model='P470', pmax=470, vmp=35, imp=13.43, voc=42, isc=14,
                      classes=[dict(pmax=470, vmp=35, imp=13.43, voc=42, isc=14)], power_classes_w=[470, 475])
        rows = catalog.expand_classes(dict(base, classes=[dict(pmax=470, vmp=35, imp=13.43, voc=42, isc=14),
                                                          dict(pmax=465, vmp=34.8, imp=13.36, voc=41.8, isc=13.9)]))
        backend = CatalogBackend(records={'modules': rows})
        settle(backend)
        self.addCleanup(backend.deleteLater)
        backend.toggleFamily(0)
        settle(backend)
        at = next(n for n, r in enumerate(backend.model.rows) if r.get('unread_class'))
        backend.select(at, False)
        self.assertFalse(backend.canChoose)
        chosen = QSignalSpy(backend.chosen)
        backend.choose()
        self.assertEqual(chosen.count(), 0)
        self.assertTrue(backend.selectedState['unread'])

    def test_it_opens_current_for_europe_and_show_all_brings_every_product(self):
        # R434, Daniel 06/11/2026 (after R458 voce 7): the catalogue opens on what is current and sold for Europe,
        # with «Show all (n)» beside the filters, n the products left out; one click shows every product (2.474
        # inverters, as the Widgets list), «Clear» goes back to the opening filters. Each kind the same.
        from meridiana.quick.backend import catalog as quick_catalog
        quick_catalog._REMEMBERED.clear()                   # the filters a test before left in this process
        self.addCleanup(quick_catalog._REMEMBERED.clear)
        for kind in ('inverters', 'modules', 'optimizers'):
            with self.subTest(kind=kind):
                backend = self.make(kind)
                shown = lambda: [r for row in backend.model.rows for r in row.get('members', [row])]   # noqa: E731
                narrow, everything = shown(), backend._all
                self.assertTrue(narrow)
                self.assertTrue(all(catalog.lifecycle_state(r) == catalog.CURRENT for r in narrow))
                self.assertFalse([r for r in narrow if r.get('markets') == ['US']])
                self.assertFalse([r for r in narrow if r.get('source') == 'cec'])
                self.assertEqual(backend.hiddenCount, len(everything) - len(narrow))
                self.assertGreater(backend.hiddenCount, 0)
                self.assertIn(number(backend.hiddenCount, 0, grouping=True), backend.showAllText)
                if kind == 'inverters':
                    self.assertGreater(len(everything), 2000)
                    self.assertIn('(', backend.hiddenText)                  # how many in each state, as before
                backend.showAll()
                settle(backend)
                self.assertEqual(len(shown()), len(everything))
                self.assertEqual((backend.hiddenCount, backend.showAllText), (0, ''))
                self.assertTrue([r for r in shown() if catalog.lifecycle_state(r) != catalog.CURRENT])
                backend.clearFilters()
                settle(backend)
                self.assertEqual(len(shown()), len(narrow))
                backend.setFilter('market', 'US')
                backend.setFilter('state', '')
                settle(backend)
                usa = shown()
                self.assertTrue(all('US' in (r.get('markets') or []) for r in usa))
                quick_catalog._REMEMBERED.clear()

    def test_opens_on_the_proposed_optimizer_and_hides_what_does_not_fit(self):
        module_row = catalog.search('modules', 'JKM475N-48QL6-DB')[0]
        inverter = catalog.search('inverters', 'SE25K', source='curated')[0]
        backend = self.make()
        backend.setContext('optimizers', dict(module=module_row, inverter=inverter, t_min=-10), '')
        settle(backend)
        self.assertEqual(backend.selectedRecord['model'], 'S1000')         # energy.optimizers.suggest, not the first row
        models = [r['model'] for row in backend.model.rows for r in row.get('members', [row])]
        self.assertNotIn('P401', models)
        self.assertTrue(backend.hiddenText)
        # R458 voce 8: the line says what is hidden and why, naming the models and what they do not go with.
        self.assertIn('JKM475N-48QL6-DB', backend.hiddenText)
        named = backend._hidden['names']
        self.assertEqual(len(named), 4)
        self.assertTrue(all(n in backend.hiddenText and n not in models for n in named), backend.hiddenText)
        backend.setFilter('state', '')
        backend.setFilter('fitting', 'all')
        settle(backend)
        at = backend.model.index_of('cur:SolarEdge:P401')
        if at < 0:
            family = next(n for n, r in enumerate(backend.model.rows) if r.get('family_row') and any(m['model'] == 'P401' for m in r['members']))
            backend.toggleFamily(family)
            settle(backend)
            at = backend.model.index_of('cur:SolarEdge:P401')
        backend.select(at, False)
        chosen = QSignalSpy(backend.chosen)
        backend.choose()
        self.assertEqual(chosen.count(), 0)                                # OK does not pass in silence
        self.assertIn('420', backend.confirmation)
        backend.chooseAnyway()
        self.assertEqual(chosen.count(), 1)

    def test_opens_on_the_component_in_use(self):
        backend = self.make()
        backend.setContext('optimizers', {}, 'cur:SolarEdge:S500')
        settle(backend)
        self.assertEqual(backend.selectedRecord['model'], 'S500')


class Window(unittest.TestCase):
    def make(self, **kwargs):
        backend = CatalogBackend(records={k: [] for k in catalog.KINDS}, **kwargs)
        settle(backend)
        self.addCleanup(backend.deleteLater)
        return backend

    def test_no_json_and_fields_with_names_units_and_groups_for_every_kind(self):
        backend = self.make()
        for kind in catalog.KINDS:
            backend.setKind(kind)
            settle(backend)
            backend.beginEdit(False)
            groups = backend.editorGroups
            self.assertGreaterEqual(len(groups), 3)
            for group in groups:
                self.assertTrue(group['title'])
                for field in group['fields']:
                    self.assertNotEqual(field['type'], 'json')
                    self.assertNotIn('_', field['label'], field)

    def test_the_calculations_decide_what_is_required(self):
        needed = {f.key for f in schema.fields('optimizers') if f.required}
        self.assertTrue({'max_input_voltage_v', 'max_input_isc_a', 'max_output_current_a'} <= needed)
        needed = {f.key for f in schema.fields('inverters') if f.required}
        self.assertTrue({'mppt_count', 'dc_current_max_per_mppt_a', 'phases'} <= needed)
        backend = self.make(safe_root=tempfile.gettempdir())
        backend.setKind('optimizers')
        settle(backend)
        backend.beginEdit(False)
        backend.setEditorField('manufacturer', 'Maker')
        backend.setEditorField('model', 'O1')
        backend.setEditorField('datasheet_url', 'sheet.pdf')
        backend.setEditorField('rated_input_power_w', '600')
        self.assertEqual(backend.editorChecks[0]['level'], 'required')
        backend.setDestination(str(Path(tempfile.gettempdir()) / 'not-written.json'))
        self.assertFalse(backend.saveEditor())
        self.assertIn('Maximum input voltage', backend.error)

    def test_coherence(self):
        said = lambda record: [c['text'] for c in schema.coherence('modules', record)]
        self.assertTrue([t for t in said(dict(pmax=475, vmp=31, imp=15.3, voc=30, isc=15.9)) if t.startswith('Voc must')])
        self.assertTrue([t for t in said(dict(pmax=600, vmp=31, imp=15.3, voc=36, isc=15.9)) if 'Vmp × Imp' in t])
        self.assertFalse([t for t in said(dict(pmax=475, vmp=31.11, imp=15.27, voc=36.42, isc=15.86)) if 'Vmp × Imp' in t])
        self.assertTrue([t for t in said(dict(length=1.1, width=1.9)) if 'width' in t])

    def test_a_module_saved_with_its_classes_comes_back_as_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = self.make(safe_root=directory)
            backend.setDestination(str(Path(directory) / 'p.json'))
            backend.beginEdit(False)
            for key, value in required_values('modules').items():
                backend.setEditorField(key, str(value))
            backend.addEditorClass()
            for key, value in dict(pmax='420', vmp='35', imp='12', voc='42', isc='13').items():
                backend.setEditorClass(0, key, value)
            backend.addEditorClass()
            for key, value in dict(pmax='425', vmp='35,2', imp='12,08', voc='42,2', isc='13,1').items():
                backend.setEditorClass(1, key, value)
            self.assertTrue(backend.saveEditor(), backend.error)
            saved = json.loads((Path(directory) / 'p.json').read_text(encoding='utf8'))
            self.assertEqual([c['pmax'] for c in saved[0]['classes']], [420, 425])
            self.assertEqual(saved[0]['classes'][1]['vmp'], 35.2)
            rows = catalog.expand_classes(catalog.personal.validate('modules', saved[0]))
            self.assertEqual(sorted(r['pmax'] for r in rows), [420, 425])

    def test_a_sheet_fills_the_window_with_page_and_sureness_and_saves_nothing(self):
        from meridiana.catalog import datasheet
        with tempfile.TemporaryDirectory() as directory:
            sheet = Path(directory) / 'sheet.txt'
            sheet.write_text("""JinkoLike JK460-470N
Maximum Power - Pmax [Wp]     460    465    470
Maximum Power Voltage - Vmp [V]    30.57  30.74  30.93
Maximum Power Current - Imp [A]    15.05  15.13  15.20
Open-circuit Voltage - Voc [V]     35.67  35.92  36.17
Short-circuit Current - Isc [A]    15.72  15.77  15.82
Temperature Coefficient of Pmax    -0.26 %/C
Dimensions 1762x1134x30 mm
""", encoding='utf8')
            reading = datasheet.read(sheet, 'modules')
            self.assertEqual([c['pmax'] for c in reading.proposals[0].record['classes']], [460, 465, 470])
            backend = self.make()
            backend.beginEdit(False)
            backend.readDatasheet(str(sheet))
            settle(backend)
            fields = {f['key']: f for group in backend.editorGroups for f in group['fields']}
            self.assertEqual(fields['pmax']['value'], '465')
            self.assertEqual(fields['pmax']['confidence'], 'high')
            self.assertTrue(fields['pmax']['sourceText'])
            self.assertEqual(len(backend.editorClasses), 3)
            self.assertTrue(backend.editing)                    # nothing was saved: it waits for the designer

    def test_pan_import_fills_the_same_window(self):
        with tempfile.TemporaryDirectory() as directory:
            pan = Path(directory) / 'm.PAN'
            pan.write_text('PVObject_=pvModule\nManufacturer=Acme\nModel=A1\nPNom=450\nVoc=40\nIsc=14\nVmp=33.6\nImp=13.4\nHeight=1.9\nWidth=1.1\n', encoding='utf8')
            backend = self.make()
            backend.beginEdit(False)
            backend.importPvsystInto(str(pan))
            settle(backend)
            fields = {f['key']: f for group in backend.editorGroups for f in group['fields']}
            self.assertEqual(fields['model']['value'], 'A1')
            self.assertEqual(fields['voc']['value'], '40')

    def test_meridio_fills_the_same_window_and_is_told_the_outcome(self):
        backend = self.make()
        finished = QSignalSpy(backend.reviewFinished)
        backend.reviewProposal('card-1', 'modules', dict(manufacturer='Acme', model='A1', pmax_w=450, length_mm=1762))
        self.assertTrue(backend.editing)
        fields = {f['key']: f for group in backend.editorGroups for f in group['fields']}
        self.assertEqual(fields['pmax']['value'], '450')
        self.assertEqual(fields['length']['value'], '1,762' if ',' in fields['length']['value'] else '1.762')
        backend.cancelEdit()
        self.assertEqual(finished.count(), 1)
        self.assertEqual((finished.at(0)[0], finished.at(0)[1]), ('card-1', False))


class OptimizerLine(unittest.TestCase):
    def test_every_inverter_with_optimizers_says_which(self):
        from types import SimpleNamespace as NS
        from meridiana.quick.backend.plant_presenter import optimizer_line
        choice = NS(optimizer=NS(name='SolarEdge S1400'), per=2, suggested=True)
        self.assertIn('S1400', optimizer_line(NS(optimized=True, choice=choice)))
        self.assertTrue(optimizer_line(NS(optimized=True, choice=None)))
        self.assertEqual(optimizer_line(NS(optimized=False, choice=None)), '')


class Names(unittest.TestCase):
    def test_a_family_is_not_named_after_one_of_its_models(self):
        rows = [dict(model='P401', pmax=0), dict(model='P505', pmax=0)]
        self.assertEqual(catalog.family_name(rows), 'P401 / P505')
        self.assertEqual(catalog.family_name([dict(model='SE25K', series='Commercial', pmax=0), dict(model='SE30K', series='Commercial', pmax=0)]), 'Commercial')
        self.assertEqual(catalog.family_name([dict(model='MERC-1100W-P', pmax=0), dict(model='MERC-1300W-P', pmax=0)]), 'MERC-1100W-P / MERC-1300W-P')
        self.assertEqual(catalog.family_name([dict(model='TS4-A-F (versione 20 A Isc)', pmax=0), dict(model='TS4-A-F (versione 25 A Isc)', pmax=0)]), 'TS4-A-F')


class Compat(unittest.TestCase):
    def test_r421_a_420_w_optimizer_is_not_for_a_475_w_module(self):
        module_row = catalog.search('modules', 'JKM475N-48QL6-DB')[0]
        inverter = catalog.search('inverters', 'SE25K', source='curated')[0]
        p401 = next(r for r in catalog.load('optimizers') if r['model'] == 'P401')
        verdict = compat.check('optimizers', p401, dict(module=module_row, inverter=inverter, t_min=-10))
        self.assertEqual(verdict.state, compat.NOT_OK)
        self.assertIn('420', ' '.join(verdict.reasons))

    def test_a_solaredge_optimizer_is_not_for_another_makers_inverter(self):
        s1000 = next(r for r in catalog.load('optimizers') if r['model'] == 'S1000')
        huawei = catalog.search('inverters', 'SUN2000-20K-MB0')[0]
        self.assertEqual(compat.check('optimizers', s1000, dict(inverter=huawei)).state, compat.NOT_OK)

    def test_nothing_in_hand_nothing_said(self):
        s1000 = next(r for r in catalog.load('optimizers') if r['model'] == 'S1000')
        self.assertEqual(compat.check('optimizers', s1000, {}).state, compat.UNKNOWN)


class Rules(unittest.TestCase):
    """R423, with cases from the sheets."""
    def huawei(self, optimizer, inverter):
        from meridiana.catalog import rules
        return rules.rule(dict(manufacturer='Huawei', model=optimizer), dict(manufacturer='Huawei', model=inverter))

    def test_huawei_merc_on_a_50ktl_is_shorter_than_on_a_40ktl(self):
        self.assertEqual((self.huawei('MERC-1100W-P', 'SUN2000-40KTL-M3').minimum, self.huawei('MERC-1100W-P', 'SUN2000-40KTL-M3').maximum), (8, 25))
        self.assertEqual((self.huawei('MERC-1100W-P', 'SUN2000-50KTL-M3').minimum, self.huawei('MERC-1100W-P', 'SUN2000-50KTL-M3').maximum), (8, 20))
        self.assertEqual(self.huawei('MERC-1300W-P', 'SUN2000-50KTL-M3').p_string_w, 20000)

    def test_huawei_small_optimizers_by_family(self):
        self.assertEqual(self.huawei('SUN2000-600W-P', 'SUN2000-5KTL-L1').maximum, 25)
        self.assertEqual(self.huawei('SUN2000-600W-P', 'SUN2000-10KTL-M1').minimum, 6)
        self.assertEqual(self.huawei('SUN2000-600W-PA0', 'SUN2000-5KTL-L1').maximum, 20)
        self.assertEqual(self.huawei('SUN2000-600W-PA0', 'SUN2000-20K-MB0').p_string_w, 12000)

    def test_what_a_sheet_does_not_say_stays_unknown(self):
        from meridiana.catalog import rules
        self.assertEqual(self.huawei('SUN2000-600W-P', 'SUN2000-20K-MB0').state, rules.UNKNOWN)
        tigo = rules.rule(dict(manufacturer='Tigo', model='TS4-A-O'), dict(manufacturer='SMA', model='STP 20-50'))
        self.assertEqual(tigo.state, rules.UNKNOWN)
        self.assertTrue(tigo.source)

    def test_another_makers_inverter_is_refused_by_its_sheets(self):
        from meridiana.catalog import rules
        self.assertEqual(rules.rule(dict(manufacturer='Huawei', model='MERC-1100W-P'), dict(manufacturer='SMA', model='STP 20-50')).state, rules.NO)
        self.assertEqual(rules.rule(dict(manufacturer='Sungrow', model='SP600S'), dict(manufacturer='Sungrow', model='SH10RT-20')).state, rules.NO)
        self.assertEqual(rules.rule(dict(manufacturer='Sungrow', model='SP600S'), dict(manufacturer='Sungrow', model='SH5.0RS')).state, rules.UNKNOWN)

    def test_solaredge_tables_as_printed(self):
        from meridiana.energy import optimizers
        table = optimizers.COM_S
        self.assertEqual(table['S1000']['SE33.3K'], (14, 27, 30, 60, 13500.0, 15750.0, 18500.0, 3))     # DS-000105-IT p. 3
        self.assertEqual(table['S1200']['SE30K'], (15, 29, 30, 60, 17000.0, 19250.0, 23000.0, 2))
        self.assertEqual(table['S1400']['SE20K'], (14, 27, 30, 60, 18000.0, 20250.0, 28000.0, 2))       # DS-000205-EU p. 3
        self.assertEqual(optimizers.SYNERGY['SE66.6K'], (2, 'SE33.3K'))
        self.assertEqual(optimizers.RES_S['three_phase_400'][:4], (16, 14, 50, 11250.0))                # DS-000091-IT p. 3

    def test_compat_says_the_maker_rule(self):
        module_row = catalog.search('modules', 'JKM475N-48QL6-DB')[0]
        merc = next(r for r in catalog.load('optimizers') if r['model'] == 'MERC-1100W-P')
        verdict = compat.check('optimizers', merc, dict(module=module_row, inverter=dict(manufacturer='Huawei', model='SUN2000-50KTL-M3')))
        self.assertIn('20', ' '.join(verdict.passed))
        verdict = compat.check('optimizers', merc, dict(module=module_row, inverter=dict(manufacturer='SMA', model='STP 20-50')))
        self.assertEqual(verdict.state, compat.NOT_OK)


class Saved(unittest.TestCase):
    def test_a_project_keeps_the_copy_it_was_designed_with(self):
        """A project that names a US inverter or a row of before the classes opens the same: nothing looks it up."""
        from meridiana import model
        project = model.Project(name='Prova')
        record = dict(next(r for r in catalog.load('inverters') if 'US' in (r.get('markets') or [])))
        project.energy = {'inverters': [dict(record=record, count=1, name='')]}
        again = model.Project.from_json(project.to_json(), check=False)
        self.assertEqual(again.energy['inverters'][0]['record'], json.loads(json.dumps(record)))


if __name__ == '__main__':
    unittest.main()
