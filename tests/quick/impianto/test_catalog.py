"""Catalogue behaviour: no truncation, physical filters and explicit safe writes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtTest import QSignalSpy

from quick.impianto.catalog_fixtures import module, required_values, settle
from meridiana.quick.backend.catalog import CatalogBackend


class CatalogueTest(unittest.TestCase):
    def test_no_row_is_selected_at_random_and_the_only_result_is(self):
        backend = self.make([module(0), module(1)])
        self.assertEqual(backend.selectedCount, 0)      # R421: the first row used to look like a proposal
        backend.setFilter('text', 'Panel 1')
        settle(backend)
        self.assertEqual(backend.selectedRecord['model'], 'Panel 1')

    def make(self, records, **kwargs):
        backend = CatalogBackend(records={'modules': records}, **kwargs)
        settle(backend)
        self.addCleanup(backend.deleteLater)
        return backend

    def test_all_rows_sort_numerically_and_selection_is_a_copy(self):
        backend = self.make([module(n, pmax=n + 1) for n in range(17000)])
        self.assertEqual(backend.model.rowCount(), 17000)
        backend.sortBy('pmax', True)
        settle(backend)
        self.assertEqual(backend.model.record(0)['pmax'], 17000)
        backend.select(16999, False)
        chosen = QSignalSpy(backend.chosen)
        backend.choose()
        self.assertEqual(chosen.count(), 1)
        copy = backend.selectedRecord
        copy['pmax'] = -1
        self.assertEqual(backend.selectedRecord['pmax'], 1)

    def test_filters_use_all_words_exact_brand_and_unknowns_are_excluded(self):
        backend = self.make([module(0), module(1, manufacturer='Elsewhere', efficiency_pct=None),
                             module(2, length=None), module(3, source='cec', bifacial=False)])
        backend.setFilter('text', 'example panel')
        backend.setFilter('efficiency_min', 20)
        backend.setFilter('length_max', 2)
        backend.setFilter('bifacial', 'yes')
        settle(backend)
        self.assertEqual(backend.model.rowCount(), 1)
        backend.setFilter('manufacturer', 'Exam')
        settle(backend)
        self.assertEqual(backend.model.rowCount(), 0)
        backend.clearFilters()
        settle(backend)
        self.assertEqual(backend.model.rowCount(), 4)

    def test_stale_search_does_not_replace_latest_filter(self):
        backend = self.make([module(n) for n in range(1000)])
        backend.setFilter('text', 'nothing')
        backend.setFilter('text', 'Panel 999')
        settle(backend)
        self.assertEqual(backend.model.rowCount(), 1)
        self.assertEqual(backend.model.record(0)['id'], '999')

    def test_editor_roundtrip_unknown_complex_fields_and_duplicate_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = self.make([module(extra_table={'3': [1, 2]})], safe_root=directory)
            backend.select(0, False)
            backend.beginEdit(True)
            backend.setEditorField('model', 'Revision B')
            self.assertFalse(backend.saveEditor())
            self.assertTrue(backend.error)
            destination = Path(directory) / 'personal.json'
            self.assertTrue(backend.setDestination(str(destination)))
            self.assertTrue(backend.saveEditor(), backend.error)
            saved = json.loads(destination.read_text(encoding='utf-8'))
            self.assertEqual(saved[0]['extra_table'], {'3': [1, 2]})
            original = destination.read_bytes()
            self.assertFalse(backend.saveEditor())
            self.assertEqual(destination.read_bytes(), original)

    def test_validation_and_destination_reject_without_touching_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = self.make([module()], safe_root=directory)
            self.assertFalse(backend.setDestination(str(Path(directory).parent / 'outside.json')))
            backend.select(0, False)
            backend.beginEdit(True)
            backend.setEditorField('voc', '10')
            self.assertTrue(backend.setDestination(str(Path(directory) / 'personal.json')))
            self.assertFalse(backend.saveEditor())
            self.assertFalse((Path(directory) / 'personal.json').exists())

    def test_all_five_kinds_offer_required_editor_fields_and_keep_filters(self):
        from meridiana.catalog import KINDS, personal
        backend = self.make([module()])
        backend.setFilter('text', 'remember')
        for kind in KINDS:
            backend.setKind(kind)
            settle(backend)
            backend.beginEdit(False)
            keys = {field['key'] for field in backend.editorFields}
            self.assertTrue(set(personal.REQUIRED[kind]) <= keys)
        backend.setKind('modules')
        settle(backend)
        self.assertEqual(backend.filters['text'], 'remember')

    def test_editor_saves_each_kind_complex_values_and_stays_independent_of_project(self):
        from meridiana.catalog import KINDS, personal
        with tempfile.TemporaryDirectory() as directory:
            backend = self.make([], safe_root=directory)
            backend.setDestination(str(Path(directory) / 'all.json'))
            for kind in KINDS:
                backend.setKind(kind)
                settle(backend)
                backend.beginEdit(False)
                for field, value in required_values(kind).items():
                    backend.setEditorField(field, str(value))
                backend._anchors = {'pmax': {'verified': True, 'page': 2, 'source': 'sheet.pdf'}}
                self.assertTrue(backend.saveEditor(), backend.error)
                settle(backend)
            saved = json.loads((Path(directory) / 'all.json').read_text(encoding='utf8'))
            self.assertEqual({r['kind'] for r in saved}, set(KINDS))
            self.assertFalse(any('verified' in r['field_sources']['pmax'] for r in saved))
            self.assertEqual({r['field_sources']['pmax']['status'] for r in saved}, {'unverified_personal'})

    def test_invalid_numeric_fields_cannot_replace_existing_catalogue(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = self.make([module()], safe_root=directory)
            destination = Path(directory) / 'personal.json'
            destination.write_text('[]', encoding='utf8')
            backend.setDestination(str(destination))
            backend.select(0, False)
            backend.beginEdit(True)
            backend.setEditorField('pmax', 'NaN')
            self.assertFalse(backend.saveEditor())
            backend.setEditorField('pmax', 'quattrocento')
            self.assertFalse(backend.saveEditor())
            self.assertIn('quattrocento', backend.error)
            self.assertEqual(destination.read_text(encoding='utf8'), '[]')

    def test_comparison_ranges_and_sort_keep_selected_product(self):
        backend = self.make([module(n, pmax=500 - n) for n in range(20)])
        backend.select(0, False)
        backend.select(2, True)
        self.assertEqual(backend.selectedIds, ['0', '2'])
        backend.selectRange(3)
        self.assertEqual(backend.selectedIds, ['0', '1', '2', '3'])
        self.assertTrue(all(len(field['values']) == 4 for field in backend.details))
        backend.sortBy('pmax', False)
        settle(backend)
        self.assertEqual(backend.selectedRecord['id'], '0')

    def test_inconsistent_record_is_not_emitted_as_chosen(self):
        backend = self.make([module(vmp=100, voc=10)])
        backend.select(0, False)
        chosen = QSignalSpy(backend.chosen)
        backend.choose()
        self.assertEqual(chosen.count(), 0)
        self.assertTrue(backend.error)

    def test_personal_destination_is_confined_and_cannot_be_a_shipped_catalogue(self):
        backend = self.make([])
        from meridiana.catalog import DATA
        self.assertFalse(backend.setDestination(str(DATA / 'modules_curated.json')))

    def test_italian_editor_formats_numbers_and_preserves_the_original_precision(self):
        from meridiana import i18n
        previous = i18n.language()
        try:
            i18n.setup('it')
            backend = self.make([module(vmp=29.753456789)])
            backend.select(0, False)
            backend.beginEdit(True)
            field = next(f for f in backend.editorFields if f['key'] == 'vmp')
            self.assertEqual(field['value'], '29,753456789')
        finally:
            i18n.setup(previous)

    def test_unknown_optional_ratings_accept_a_stated_number(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = self.make([module(max_system_voltage_v=None)], safe_root=directory)
            backend.select(0, False)
            backend.beginEdit(True)
            backend.setEditorField('max_system_voltage_v', '1000')
            backend.setDestination(str(Path(directory) / 'catalogue.json'))
            self.assertTrue(backend.saveEditor(), backend.error)

    def test_source_link_opens_documents_and_rejects_executable_schemes(self):
        backend = self.make([])
        with patch('PySide6.QtGui.QDesktopServices.openUrl', return_value=True) as opened:
            self.assertTrue(backend.openSource('https://example.org/sheet.pdf'))
            self.assertEqual(opened.call_args.args[0].toString(), 'https://example.org/sheet.pdf')
            self.assertFalse(backend.openSource('javascript:alert(1)'))
            self.assertFalse(backend.openSource('file:///C:/Windows/notepad.exe'))
            self.assertEqual(opened.call_count, 1)

    def test_large_range_selection_is_reported_by_the_virtual_model_role(self):
        backend = self.make([module(n) for n in range(17000)])
        backend.select(0, False)
        backend.selectRange(16999)
        self.assertEqual(backend.selectedCount, 17000)
        role = next(role for role, name in backend.model.roleNames().items() if name == b'selected')
        self.assertTrue(backend.model.data(backend.model.index(16999), role))
        self.assertEqual(len(backend.details[0]['values']), 4)

    def test_existing_non_catalogue_json_cannot_be_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = self.make([module()], safe_root=directory)
            backend.select(0, False)
            backend.beginEdit(True)
            target = Path(directory) / 'unrelated.json'
            backend.setDestination(str(target))
            for text in ('["not a product"]', '[{"unrelated":"data"}]'):
                target.write_text(text, encoding='utf8')
                self.assertFalse(backend.saveEditor())
                self.assertEqual(target.read_text(encoding='utf8'), text)
