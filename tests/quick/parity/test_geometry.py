"""R389: logical geometry contracts and narrowly scoped visual differences."""
import copy
import tempfile
import unittest
from pathlib import Path

from PySide6.QtGui import QImage, QColor

from quick.parity.geometry import compare_snapshots, write_comparison


def snapshot():
    return {'schema': 1, 'meta': {'scenario': 'model'}, 'widgets': [{
        'id': 'name', 'name': 'name', 'class': 'Field', 'rect': [20, 30, 80, 24],
        'margins': [4, 4, 4, 4], 'font': {'family': 'IBM Plex Sans', 'pixel_size': 13,
                                        'point_size': 9.75, 'weight': 400, 'italic': False},
        'colors': {'text': '#112233'}, 'text': 'Nome'}]}


class GeometryTest(unittest.TestCase):
    def test_incomplete_matching_rows_do_not_silently_pass(self):
        incomplete = {'schema': 1, 'widgets': [{'id': 'a'}]}
        with self.assertRaisesRegex(ValueError, 'rect'):
            compare_snapshots(incomplete, incomplete, {'a': 'a'})
        for field in ('rect', 'margins', 'colors', 'font'):
            with self.subTest(field=field):
                incomplete = snapshot()
                del incomplete['widgets'][0][field]
                with self.assertRaisesRegex(ValueError, field):
                    compare_snapshots(incomplete, incomplete, {'name': 'name'})

    def test_malformed_measurements_fail_on_either_or_both_sides(self):
        invalid = [None, [], [1, 2, 3], [1, 2, 3, 4, 5], '1234',
                   [1, 2, '3', 4], [1, 2, True, 4], [1, 2, float('nan'), 4],
                   [1, 2, float('inf'), 4]]
        for field in ('rect', 'margins'):
            for value in invalid:
                for side in ('reference', 'actual', 'both'):
                    with self.subTest(field=field, value=value, side=side):
                        reference, actual = snapshot(), snapshot()
                        if side != 'actual':
                            reference['widgets'][0][field] = value
                        if side != 'reference':
                            actual['widgets'][0][field] = value
                        with self.assertRaisesRegex(ValueError, field):
                            compare_snapshots(reference, actual, {'name': 'name'})

    def test_invalid_colors_and_fonts_cannot_pass_when_equal(self):
        for field, value in [('colors', None), ('colors', []), ('colors', {'text': None}),
                             ('colors', {'text': 'not-a-color'}), ('font', None), ('font', {}),
                             ('font', {'family': 'Arial'})]:
            with self.subTest(field=field, value=value):
                invalid = snapshot()
                invalid['widgets'][0][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    compare_snapshots(invalid, invalid, {'name': 'name'})
        for key, value in [('pixel_size', float('nan')), ('point_size', -1), ('weight', 'bold'),
                           ('italic', 'false'), ('family', '')]:
            with self.subTest(font_key=key):
                invalid = snapshot()
                invalid['widgets'][0]['font'][key] = value
                with self.assertRaisesRegex(ValueError, 'font'):
                    compare_snapshots(invalid, invalid, {'name': 'name'})

    def test_non_text_items_can_omit_fonts_but_one_sided_font_remains_a_difference(self):
        reference, actual = snapshot(), snapshot()
        for row in (reference['widgets'][0], actual['widgets'][0]):
            row.pop('font')
            row.pop('text')
        self.assertEqual(compare_snapshots(reference, actual, {'name': 'name'}), [])
        reference['widgets'][0]['font'] = snapshot()['widgets'][0]['font']
        self.assertEqual(compare_snapshots(reference, actual, {'name': 'name'})[0]['field'], 'font')

    def test_logical_tolerance_includes_one_but_rejects_more(self):
        reference, actual = snapshot(), snapshot()
        actual['widgets'][0]['rect'][0] += 1
        self.assertEqual(compare_snapshots(reference, actual, {'name': 'name'}), [])
        actual['widgets'][0]['rect'][0] += .01
        self.assertEqual(compare_snapshots(reference, actual, {'name': 'name'})[0]['field'], 'rect')

    def test_missing_duplicate_and_unmapped_elements_fail(self):
        reference, actual = snapshot(), snapshot()
        actual['widgets'] = []
        self.assertEqual(compare_snapshots(reference, actual, {'name': 'name'})[0]['field'], 'missing')
        self.assertEqual(compare_snapshots(reference, actual, {'nonexistent': 'absent'})[0]['field'], 'missing')
        actual = snapshot()
        actual['widgets'].append(copy.deepcopy(actual['widgets'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            compare_snapshots(reference, actual, {'name': 'name'})
        with self.assertRaisesRegex(ValueError, 'mapping'):
            compare_snapshots(reference, snapshot(), {})

    def test_missing_color_roles_cannot_pass_when_both_are_missing(self):
        mapping = {'name': {'id': 'name', 'colors': {'absent': 'alsoAbsent'}}}
        with self.assertRaisesRegex(ValueError, 'color role'):
            compare_snapshots(snapshot(), snapshot(), mapping)

    def test_mapping_scope_ignores_unmapped_duplicate_implementation_items(self):
        actual = snapshot()
        actual['widgets'].extend([{'id': 'internalHandle'}, {'id': 'internalHandle'}])
        self.assertEqual(compare_snapshots(snapshot(), actual, {'name': 'name'}), [])

    def test_font_color_and_margins_are_compared(self):
        for field, changed in [('font', dict(snapshot()['widgets'][0]['font'], family='Arial')),
                               ('colors', {'text': '#112234'}), ('margins', [6, 4, 4, 4])]:
            with self.subTest(field=field):
                actual = snapshot()
                actual['widgets'][0][field] = changed
                self.assertEqual(compare_snapshots(snapshot(), actual, {'name': 'name'})[0]['field'], field)

    def test_difference_requires_exact_scenario_element_field_and_values(self):
        actual = snapshot()
        actual['widgets'][0]['text'] = 'Altezza'
        rule = {'scenario': 'model', 'reference': 'name', 'quick': 'name', 'field': 'text',
                'before': 'Nome', 'after': 'Altezza', 'request': 'R389', 'reason': 'Test fixture only'}
        self.assertEqual(compare_snapshots(snapshot(), actual, {'name': 'name'}, [rule]), [])
        for field, value in [('scenario', 'other'), ('after', 'wrong'), ('reference', 'other')]:
            altered = dict(rule, **{field: value})
            self.assertTrue(compare_snapshots(snapshot(), actual, {'name': 'name'}, [altered]))
        for field in ('reason', 'request'):
            altered = dict(rule, **{field: ''})
            with self.assertRaises(ValueError):
                compare_snapshots(snapshot(), actual, {'name': 'name'}, [altered])

    def test_report_has_self_contained_images_and_device_pixel_diff(self):
        a = QImage(8, 8, QImage.Format.Format_RGB32)
        a.fill(QColor('white'))
        b = a.copy()
        b.setPixelColor(3, 4, QColor('black'))
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'report.html'
            result = write_comparison(a, b, target, title='<model>', differences=[])
            html = target.read_text(encoding='utf-8')
        self.assertEqual(result['changed_pixels'], 1)
        self.assertEqual(result['total_pixels'], 64)
        self.assertEqual(html.count('data:image/png;base64,'), 3)
        self.assertIn('&lt;model&gt;', html)
        self.assertIn('Differenza pixel', html)
